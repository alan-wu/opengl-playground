import os
import json
import trimesh
import pyrender

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.zinc.context import Context
from opencmiss.zinc.sceneviewer import Sceneviewer

from platforms.pyglet import PygletPlatform
from renderer import Renderer, RenderFlags


argon_document = "argon-document.json"


platform = PygletPlatform(512, 512)
platform.init_context()
platform.make_current()

renderer = Renderer(512, 512)
#renderer.configure(0)

document = ArgonDocument()

current_wd = os.getcwd()

path = os.path.dirname(argon_document)
if path != "":
    os.chdir(path)

with open(argon_document, 'r') as f:
    state = f.read()

os.chdir(current_wd)

# scene = pyrender.Scene()

document.initialiseVisualisationContents()
document.deserialize(state)

zinc_context = document.getZincContext()
view_manager = document.getViewManager()

root_region = zinc_context.getDefaultRegion()
sceneviewermodule = zinc_context.getSceneviewermodule()

zinc_scene = root_region.getScene()

views = view_manager.getViews()

z_near = 1.0
z_far = 500.0

for view in views:
    name = view.getName()
    scenes = view.getScenes()
    if len(scenes) == 1:
        scene_description = scenes[0]["Sceneviewer"].serialize()

        sceneviewer = sceneviewermodule.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE, Sceneviewer.STEREO_MODE_DEFAULT)
        sceneviewer.setViewportSize(512, 512)

        sceneviewer.readDescription(json.dumps(scene_description))
        sceneviewer.setScene(zinc_scene)
        sceneviewer.renderScene()

        sceneviewer.writeImageToFile(name +".jpg", False, 512, 512, 0 , 0) 

        #z_near = sceneviewer.getNearClippingPlane()
        #z_far = sceneviewer.getFarClippingPlane()


platform.make_current()
#colour, depth = renderer.read(z_near, z_far, 0)
# fuze_trimesh = trimesh.load('fuze.obj')
# mesh = pyrender.Mesh.from_trimesh(fuze_trimesh)
# scene.add(mesh)

#print(colour)
# pyrender.Viewer(scene, use_raymond_lighting=True)

# import pyrender

# r = pyrender.OffscreenRenderer(viewport_width=640, viewport_height=480, point_size=1.0)
