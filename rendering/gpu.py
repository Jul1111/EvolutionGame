"""Drawing with the graphics card (SDL2 renderer of pygame-ce), same picture as the processor path.

Frame:
1. The world is drawn on `screen`, a target texture the size of the window (GpuCanvas, rendering/canvas.py):
   background, sprites, lines and circles become textures drawn by the graphics card.
2. The interface (panels, text, menus: rendering/hud.py, overlay.py...) is still drawn by the processor, on `ui`,
   a transparent Surface the size of the window. Only the parts that were drawn are sent to the graphics card
   (UILayer records them), then cleared.
3. Frosted glass (rendering/glass.py) is done here: what is already on `screen` under the panel is copied, shrunk
   in three halvings (an average, like the processor's smoothscale), tinted, enlarged and given rounded corners.
   Before each glass, the interface drawn so far is sent: a menu over a panel blurs the panel, as before.
4. `screen` is shown.

Textures made from Surfaces are cached (keyed by the Surface, which is kept alive with its texture).
Scaling uses linear filtering: SDL_RENDER_SCALE_QUALITY is set before anything is created.
"""
import os
from collections import OrderedDict

os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")

import pygame
from pygame._sdl2 import video

from rendering.canvas import GpuCanvas

TEXTURE_CACHE = 1500   # Textures made from Surfaces kept at most (sprites of several zooms, anemone frames...)
TARGET_CACHE = 48      # Scratch target textures (glass) kept at most, by size


class UILayer(pygame.Surface):
    """The interface is drawn here. Records where Surfaces are blitted or filled (in window pixels), so only those
    parts are sent. Its subsurfaces (the side bar...) share the same record."""

    def __init__(self, size):
        super().__init__(size, pygame.SRCALPHA)
        self.dirty = []

    def _note(self, rect):
        dirty = getattr(self, "dirty", None)
        if dirty is not None and rect is not None:
            dirty.append(pygame.Rect(rect).move(self.get_abs_offset()))

    def subsurface(self, *rect):
        sub = super().subsurface(*rect)
        sub.dirty = getattr(self, "dirty", None)
        return sub

    def blit(self, source, dest, area=None, special_flags=0):
        r = super().blit(source, dest, area, special_flags)
        self._note(r)
        return r

    def blits(self, blit_sequence, doreturn=True):
        rects = super().blits(blit_sequence, doreturn=True)
        for r in rects:
            self._note(r)
        return rects if doreturn else None

    def fblits(self, blit_sequence, special_flags=0):
        self.blits(list(blit_sequence), doreturn=False)

    def fill(self, color, rect=None, special_flags=0):
        r = super().fill(color, rect, special_flags)
        self._note(r)
        return r

    def mark(self, rect):
        """Something was drawn there with pygame.draw (not seen by blit/fill): send it too."""
        self._note(rect)

    def clear(self, rect):
        pygame.Surface.fill(self, (0, 0, 0, 0), rect)


class Gpu:
    def __init__(self, window, hardware_only=True):
        """hardware_only: fails (the caller falls back to the processor) when SDL has no hardware renderer: its
        software renderer is slower than rendering/scene.py drawing with the processor."""
        self.window = window
        self.renderer = video.Renderer(window, accelerated=1 if hardware_only else -1, vsync=False,
                                       target_texture=True)
        # Surface.convert() needs a display format, which a window drawn by a renderer does not give: a hidden 1×1
        # display provides it (the sprites, the background and the glass masks still use convert/convert_alpha)
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
        self.size = None
        self._textures = OrderedDict()   # id(surface) → (surface, texture)
        self._targets = OrderedDict()    # (w, h, tag) → target texture
        self._rings = {}
        self._strip = None
        self._corners = {}
        self.resize()

    # ---------- size ----------

    def output_size(self):
        return self.renderer.get_viewport().size

    def resize(self):
        """(Re)create what depends on the window size. Returns True when it changed."""
        size = self.output_size()
        if size == self.size:
            return False
        self.size = size
        self.screen = video.Texture(self.renderer, size, target=True)
        self.ui = UILayer(size)
        self.ui_tex = video.Texture(self.renderer, size, streaming=True)
        self.ui_tex.blend_mode = pygame.BLENDMODE_BLEND
        return True

    def canvas(self, rect):
        """Where the world is drawn: the part `rect` of the window."""
        rect = pygame.Rect(rect)
        return GpuCanvas(self, self.screen, rect.size, rect.topleft)

    def begin(self):
        self.renderer.target = self.screen
        self.renderer.draw_color = (0, 0, 0, 255)
        self.renderer.clear()

    def present(self):
        self.flush_ui()
        r = self.renderer
        r.target = None
        r.draw_color = (0, 0, 0, 255)
        r.clear()
        self.screen.draw()
        r.present()

    # ---------- textures ----------

    def texture(self, surf):
        key = id(surf)
        hit = self._textures.get(key)
        if hit is not None and hit[0] is surf:
            self._textures.move_to_end(key)
            return hit[1]
        tex = video.Texture.from_surface(self.renderer, surf)
        if surf.get_flags() & pygame.SRCALPHA:
            tex.blend_mode = pygame.BLENDMODE_BLEND
        self._textures[key] = (surf, tex)
        if len(self._textures) > TEXTURE_CACHE:
            self._textures.popitem(last=False)
        return tex

    def _target(self, w, h, tag):
        key = (w, h, tag)
        tex = self._targets.get(key)
        if tex is None:
            tex = video.Texture(self.renderer, (w, h), target=True)
            tex.blend_mode = pygame.BLENDMODE_BLEND
            self._targets[key] = tex
            if len(self._targets) > TARGET_CACHE:
                self._targets.popitem(last=False)
        else:
            self._targets.move_to_end(key)
        return tex

    def layer_texture(self, w, h):
        """Transparent target texture for a picture drawn once then copied (the map zoomed out beyond itself)."""
        return self._target(w, h, "layer")

    def ring(self, radius, width):
        """White anti-aliased ring (or disc when width is 0) drawn by pygame at exactly this size."""
        key = (round(radius * 2), round(width))
        tex = self._rings.get(key)
        if tex is None:
            d, s = max(2, key[0]), 4
            big = pygame.Surface((d * s, d * s), pygame.SRCALPHA)
            pygame.draw.circle(big, (255, 255, 255), (d * s / 2, d * s / 2), d * s / 2, key[1] * s)
            tex = video.Texture.from_surface(self.renderer, pygame.transform.smoothscale(big, (d, d)))
            tex.blend_mode = pygame.BLENDMODE_BLEND
            if len(self._rings) > 600:
                self._rings.clear()
            self._rings[key] = tex
        return tex

    def strip(self):
        """1 pixel wide line with soft edges, stretched and turned by GpuCanvas._segment."""
        if self._strip is None:
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            for x in range(4):
                s.set_at((x, 0), (255, 255, 255, 0))
                s.set_at((x, 1), (255, 255, 255, 255))
                s.set_at((x, 2), (255, 255, 255, 255))
                s.set_at((x, 3), (255, 255, 255, 0))
            self._strip = video.Texture.from_surface(self.renderer, s)
            self._strip.blend_mode = pygame.BLENDMODE_BLEND
        return self._strip

    def _corner(self, radius):
        """radius×radius: opaque inside the quarter circle (top-left corner of a rounded rectangle), clear outside."""
        tex = self._corners.get(radius)
        if tex is None:
            s = 4
            big = pygame.Surface((radius * s, radius * s), pygame.SRCALPHA)
            big.fill((255, 255, 255, 0))
            pygame.draw.circle(big, (255, 255, 255, 255), (radius * s, radius * s), radius * s)
            tex = video.Texture.from_surface(self.renderer, pygame.transform.smoothscale(big, (radius, radius)))
            tex.blend_mode = pygame.BLENDMODE_NONE   # Copies its alpha: it is a mask
            self._corners[radius] = tex
        return tex

    # ---------- interface layer ----------

    def flush_ui(self):
        """Sends what the interface drew since the last flush, draws it on `screen`, and clears it from `ui`."""
        ui = self.ui
        if not ui.dirty:
            return
        bounds = ui.get_rect()
        rects = _merge([r.clip(bounds) for r in ui.dirty if r.w and r.h])
        ui.dirty = []
        r = self.renderer
        r.target = self.screen
        for rect in rects:
            if rect.w and rect.h:
                # A tuple, not a Rect: pygame-ce 2.5.8 puts the pixels at (0, 0) when `area` is a Rect
                self.ui_tex.update(ui.subsurface(rect), tuple(rect))
                self.ui_tex.draw(srcrect=rect, dstrect=rect)
                ui.clear(rect)

    def glass(self, rect, radius, tint, alpha):
        """Frosted glass on `rect` of the window: same steps as rendering/glass.py, by the graphics card."""
        self.flush_ui()   # What is already drawn under the glass must be blurred with the world
        rect = pygame.Rect(rect).clip(pygame.Rect((0, 0), self.size))
        w, h = rect.size
        if w < 4 or h < 4:
            return
        r = self.renderer
        copy = self._target(w, h, "copy")      # A target cannot be read while it is drawn on: copy the area first
        r.target = copy
        self.screen.draw(srcrect=rect, dstrect=(0, 0, w, h))
        src, sw, sh = copy, w, h
        for step in range(3):                  # Three halvings with linear filtering = average of 8×8 pixels
            nw, nh = max(2, sw // 2), max(2, sh // 2)
            small = self._target(nw, nh, f"half{step}")
            r.target = small
            src.blend_mode = pygame.BLENDMODE_NONE
            src.draw(srcrect=(0, 0, sw, sh), dstrect=(0, 0, nw, nh))
            src.blend_mode = pygame.BLENDMODE_BLEND
            src, sw, sh = small, nw, nh
        r.draw_blend_mode = pygame.BLENDMODE_BLEND   # Tint on the small picture, as the processor path does
        r.draw_color = (*tint, alpha)
        r.fill_rect((0, 0, sw, sh))
        panel = self._target(w, h, "panel")    # Rounded rectangle: an opaque white mask, then the blur multiplied in
        r.target = panel
        r.draw_blend_mode = pygame.BLENDMODE_NONE
        r.draw_color = (255, 255, 255, 0)
        r.clear()
        radius = min(radius, w // 2, h // 2)
        r.draw_color = (255, 255, 255, 255)
        if radius:
            r.fill_rect((radius, 0, w - 2 * radius, h))
            r.fill_rect((0, radius, w, h - 2 * radius))
            corner = self._corner(radius)
            for fx, fy, x, y in ((False, False, 0, 0), (True, False, w - radius, 0),
                                 (False, True, 0, h - radius), (True, True, w - radius, h - radius)):
                corner.draw(dstrect=(x, y, radius, radius), flip_x=fx, flip_y=fy)
        else:
            r.fill_rect((0, 0, w, h))
        src.blend_mode = pygame.BLENDMODE_MOD   # Colour = blur × white, alpha = the mask's
        src.draw(srcrect=(0, 0, sw, sh), dstrect=(0, 0, w, h))
        src.blend_mode = pygame.BLENDMODE_BLEND
        r.target = self.screen
        panel.draw(dstrect=rect)


def _merge(rects):
    """Fewer, bigger rectangles: overlapping or touching ones are joined (fewer uploads)."""
    rects = sorted(rects, key=lambda r: (r.y, r.x))
    out = []
    for r in rects:
        for i, o in enumerate(out):
            if o.inflate(2, 2).colliderect(r):
                out[i] = o.union(r)
                break
        else:
            out.append(r)
    changed = True
    while changed and len(out) > 1:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                if out[i].inflate(2, 2).colliderect(out[j]):
                    out[i] = out[i].union(out.pop(j))
                    changed = True
                    break
            if changed:
                break
    return out
