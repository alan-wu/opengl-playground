import sys

import numpy as np
import PIL

from OpenGL.GL import *


# Flags for render type
class RenderFlags(object):
    """Flags for rendering in the scene.
    Combine them with the bitwise or. For example,
    >>> flags = OFFSCREEN | SHADOWS_DIRECTIONAL | VERTEX_NORMALS
    would result in an offscreen render with directional shadows and
    vertex normals enabled.
    """
    NONE = 0
    """Normal PBR Render."""
    DEPTH_ONLY = 1
    """Only render the depth buffer."""
    OFFSCREEN = 2
    """Render offscreen and return the depth and (optionally) color buffers."""
    FLIP_WIREFRAME = 4
    """Invert the status of wireframe rendering for each mesh."""
    ALL_WIREFRAME = 8
    """Render all meshes as wireframes."""
    ALL_SOLID = 16
    """Render all meshes as solids."""
    SHADOWS_DIRECTIONAL = 32
    """Render shadows for directional lights."""
    SHADOWS_POINT = 64
    """Render shadows for point lights."""
    SHADOWS_SPOT = 128
    """Render shadows for spot lights."""
    SHADOWS_ALL = 32 | 64 | 128
    """Render shadows for all lights."""
    VERTEX_NORMALS = 256
    """Render vertex normals."""
    FACE_NORMALS = 512
    """Render face normals."""
    SKIP_CULL_FACES = 1024
    """Do not cull back faces."""
    RGBA = 2048
    """Render the color buffer with the alpha channel enabled."""
    FLAT = 4096
    """Render the color buffer flat, with no lighting computations."""
    SEG = 8192


class Renderer(object):
    """Class for handling all rendering operations on a scene.
    Note
    ----
    This renderer relies on the existence of an OpenGL context and
    does not create one on its own.
    Parameters
    ----------
    viewport_width : int
        Width of the viewport in pixels.
    viewport_height : int
        Width of the viewport height in pixels.
    point_size : float, optional
        Size of points in pixels. Defaults to 1.0.
    """

    def __init__(self, viewport_width, viewport_height, point_size=1.0):
        self.dpscale = 1
        # Scaling needed on retina displays
        if sys.platform == 'darwin':
            self.dpscale = 2

        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.point_size = point_size

        # Optional framebuffer for offscreen renders
        self._main_fb = None
        self._main_cb = None
        self._main_db = None
        self._main_fb_ms = None
        self._main_cb_ms = None
        self._main_db_ms = None
        self._main_fb_dims = (None, None)
        self._shadow_fb = None

    def configure(self, flags):
        self._configure_forward_pass_viewport(flags)

    def _configure_forward_pass_viewport(self, flags):

        # If using offscreen render, bind main framebuffer
        self._configure_main_framebuffer()
        if flags & RenderFlags.OFFSCREEN:
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self._main_fb_ms)
        else:
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)

        glViewport(0, 0, self.viewport_width, self.viewport_height)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_TRUE)
        glDepthFunc(GL_LESS)
        glDepthRange(0.0, 1.0)

    ###########################################################################
    # Framebuffer Management
    ###########################################################################

    def _configure_main_framebuffer(self):
        # If mismatch with prior framebuffer, delete it
        if (self._main_fb is not None and
                self.viewport_width != self._main_fb_dims[0] or
                self.viewport_height != self._main_fb_dims[1]):
            self._delete_main_framebuffer()

        # If framebuffer doesn't exist, create it
        if self._main_fb is None:
            # Generate standard buffer
            self._main_cb, self._main_db = glGenRenderbuffers(2)
            print("-------")
            print(self._main_cb, self._main_db)
            print(self.viewport_width, self.viewport_height)

            print(glBindRenderbuffer(GL_RENDERBUFFER, self._main_cb))
            glRenderbufferStorage(
                GL_RENDERBUFFER, GL_RGBA,
                self.viewport_width, self.viewport_height
            )

            glBindRenderbuffer(GL_RENDERBUFFER, self._main_db)
            glRenderbufferStorage(
                GL_RENDERBUFFER, GL_DEPTH_COMPONENT24,
                self.viewport_width, self.viewport_height
            )

            self._main_fb = glGenFramebuffers(1)
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self._main_fb)
            glFramebufferRenderbuffer(
                GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                GL_RENDERBUFFER, self._main_cb
            )
            glFramebufferRenderbuffer(
                GL_DRAW_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                GL_RENDERBUFFER, self._main_db
            )

            # Generate multisample buffer
            self._main_cb_ms, self._main_db_ms = glGenRenderbuffers(2)
            glBindRenderbuffer(GL_RENDERBUFFER, self._main_cb_ms)
            glRenderbufferStorageMultisample(
                GL_RENDERBUFFER, 4, GL_RGBA,
                self.viewport_width, self.viewport_height
            )
            glBindRenderbuffer(GL_RENDERBUFFER, self._main_db_ms)
            glRenderbufferStorageMultisample(
                GL_RENDERBUFFER, 4, GL_DEPTH_COMPONENT24,
                self.viewport_width, self.viewport_height
            )
            self._main_fb_ms = glGenFramebuffers(1)
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self._main_fb_ms)
            glFramebufferRenderbuffer(
                GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                GL_RENDERBUFFER, self._main_cb_ms
            )
            glFramebufferRenderbuffer(
                GL_DRAW_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                GL_RENDERBUFFER, self._main_db_ms
            )

            print(self.viewport_width, self.viewport_height)
            self._main_fb_dims = (self.viewport_width, self.viewport_height)

    def _delete_main_framebuffer(self):
        print("delete frame buffer")
        if self._main_fb is not None:
            glDeleteFramebuffers(2, [self._main_fb, self._main_fb_ms])
        if self._main_cb is not None:
            glDeleteRenderbuffers(2, [self._main_cb, self._main_cb_ms])
        if self._main_db is not None:
            glDeleteRenderbuffers(2, [self._main_db, self._main_db_ms])

        self._main_fb = None
        self._main_cb = None
        self._main_db = None
        self._main_fb_ms = None
        self._main_cb_ms = None
        self._main_db_ms = None
        self._main_fb_dims = (None, None)

    def read(self, z_near, z_far, flags):
        return self._read_main_framebuffer(z_near, z_far, flags)

    def _read_main_framebuffer(self, z_near, z_far, flags):
        width, height = self._main_fb_dims[0], self._main_fb_dims[1]

        # Bind framebuffer and blit buffers
        print("bind frame buffer:", self._main_fb_ms)
        print("bind frame buffer:", self._main_fb)
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self._main_fb_ms)
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self._main_fb)
        glBlitFramebuffer(
            0, 0, width, height, 0, 0, width, height,
            GL_COLOR_BUFFER_BIT, GL_LINEAR
        )
        glBlitFramebuffer(
            0, 0, width, height, 0, 0, width, height,
            GL_DEPTH_BUFFER_BIT, GL_NEAREST
        )
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self._main_fb)

        # Read depth
        depth_buf = glReadPixels(
            0, 0, width, height, GL_DEPTH_COMPONENT, GL_FLOAT
        )
        depth_im = np.frombuffer(depth_buf, dtype=np.float32)
        depth_im = depth_im.reshape((height, width))
        depth_im = np.flip(depth_im, axis=0)
        inf_inds = (depth_im == 1.0)
        depth_im = 2.0 * depth_im - 1.0
        noninf = np.logical_not(inf_inds)
        if z_far is None:
            depth_im[noninf] = 2 * z_near / (1.0 - depth_im[noninf])
        else:
            depth_im[noninf] = ((2.0 * z_near * z_far) /
                                (z_far + z_near - depth_im[noninf] *
                                (z_far - z_near)))
        depth_im[inf_inds] = 0.0

        # Resize for macos if needed
        if sys.platform == 'darwin':
            depth_im = self._resize_image(depth_im)

        if flags & RenderFlags.DEPTH_ONLY:
            return depth_im

        # Read color
        if flags & RenderFlags.RGBA:
            color_buf = glReadPixels(
                0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE
            )
            color_im = np.frombuffer(color_buf, dtype=np.uint8)
            color_im = color_im.reshape((height, width, 4))
        else:
            color_buf = glReadPixels(
                0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE
            )
            color_im = np.frombuffer(color_buf, dtype=np.uint8)
            color_im = color_im.reshape((height, width, 3))
        color_im = np.flip(color_im, axis=0)

        # Resize for macos if needed
        if sys.platform == 'darwin':
            color_im = self._resize_image(color_im, True)

        return color_im, depth_im

    def _resize_image(self, value, antialias=False):
        """If needed, rescale the render for MacOS."""
        img = PIL.Image.fromarray(value)
        resample = PIL.Image.NEAREST
        if antialias:
            resample = PIL.Image.BILINEAR
        size = (self.viewport_width // self.dpscale,
                self.viewport_height // self.dpscale)
        img = img.resize(size, resample=resample)
        return np.array(img)

