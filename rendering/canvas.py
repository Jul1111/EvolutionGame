"""Drawing surfaces for the world: the same drawing code (rendering/scene.py, effects.py, obstacles.py) draws either
on a pygame Surface (CpuCanvas, the processor does the pixels) or on the graphics card (GpuCanvas, rendering/gpu.py).

The methods follow pygame's: blit / fblits of Surfaces (their set_alpha() is honoured), circles, lines, rectangles.
Colours may carry an alpha as a 4th value."""
import math

import pygame


class CpuCanvas:
    """A pygame Surface: exactly what the game drew before the graphics card path."""

    def __init__(self, surface):
        self.surface = surface

    def get_size(self):
        return self.surface.get_size()

    def blit(self, surf, pos):
        self.surface.blit(surf, pos)

    def fblits(self, batch):
        if not batch:
            return
        if hasattr(self.surface, "fblits"):
            self.surface.fblits(batch)
        else:
            self.surface.blits(batch, doreturn=False)

    def clear(self):
        self.surface.fill((0, 0, 0, 0))

    def circle(self, color, center, radius, width=0):
        pygame.draw.circle(self.surface, color, center, radius, width)

    def line(self, color, a, b, width=1):
        pygame.draw.line(self.surface, color, a, b, width)

    def aaline(self, color, a, b):
        pygame.draw.aaline(self.surface, color, a, b)

    def lines(self, color, closed, points, width=1):
        pygame.draw.lines(self.surface, color, closed, points, width)

    def fill_rect(self, color, rect):
        """Rectangle of colour, blended when the colour has an alpha below 255."""
        rect = pygame.Rect(rect).clip(self.surface.get_rect())
        if len(color) == 4 and color[3] < 255:
            veil = pygame.Surface(rect.size, pygame.SRCALPHA)
            veil.fill(color)
            self.surface.blit(veil, rect.topleft)
        else:
            self.surface.fill(color, rect)

    def rect(self, color, rect, width=1):
        pygame.draw.rect(self.surface, color, rect, width)

    def layer(self, w, h):
        """A transparent canvas of the same kind, to draw something once and copy it (blit_layer)."""
        return CpuCanvas(pygame.Surface((w, h), pygame.SRCALPHA))

    def blit_layer(self, layer, pos):
        self.surface.blit(layer.surface, pos)


class GpuCanvas:
    """A target texture of the graphics card (see rendering/gpu.py). `offset`: where (0, 0) of this canvas falls on
    the target, so the world area can be a part of the window."""

    def __init__(self, gpu, target, size, offset=(0, 0)):
        self.gpu, self.target, self.size, self.ox, self.oy = gpu, target, size, offset[0], offset[1]

    def _bind(self):
        r = self.gpu.renderer
        if r.target is not self.target:
            r.target = self.target
        return r

    def get_size(self):
        return self.size

    def blit(self, surf, pos):
        self._bind()
        tex = self.gpu.texture(surf)
        alpha = surf.get_alpha()
        tex.alpha = 255 if alpha is None else alpha
        w, h = surf.get_size()
        tex.draw(dstrect=(pos[0] + self.ox, pos[1] + self.oy, w, h))

    def fblits(self, batch):
        if not batch:
            return
        self._bind()
        texture, ox, oy = self.gpu.texture, self.ox, self.oy
        last, tex = None, None
        for surf, (x, y) in batch:
            if surf is not last:
                tex, last = texture(surf), surf
                tex.alpha = 255
                w, h = surf.get_size()
            tex.draw(dstrect=(x + ox, y + oy, w, h))

    def clear(self):
        r = self._bind()
        r.draw_color = (0, 0, 0, 0)
        r.clear()

    def circle(self, color, center, radius, width=0):
        """Disc (width 0) or ring, from an anti-aliased white picture tinted to the colour."""
        if radius <= 0:
            return
        self._bind()
        tex = self.gpu.ring(radius, 0 if width <= 0 or width >= radius else width)   # Cached per size
        _tint(tex, color)
        d = 2 * radius
        tex.draw(dstrect=(center[0] - radius + self.ox, center[1] - radius + self.oy, d, d))

    def line(self, color, a, b, width=1):
        self._segment(color, a, b, max(1.0, float(width)))

    def aaline(self, color, a, b):
        self._segment(color, a, b, 1.0)

    def lines(self, color, closed, points, width=1):
        pts = list(points) + ([points[0]] if closed and points else [])
        for a, b in zip(pts, pts[1:]):
            self._segment(color, a, b, max(1.0, float(width)))

    def _segment(self, color, a, b, width):
        """Segment as a thin textured strip with soft edges, turned to the right angle: smooth like aaline."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 0.5:
            return
        self._bind()
        tex = self.gpu.strip()
        _tint(tex, color)
        h = 2.0 * width + 1.0   # Texture rows: clear, full, full, clear → the full core is about `width` wide
        tex.draw(dstrect=(a[0] + self.ox, a[1] + self.oy - h / 2, length, h), angle=math.degrees(math.atan2(dy, dx)),
                 origin=(0, h / 2))

    def fill_rect(self, color, rect):
        r = self._bind()
        r.draw_blend_mode = pygame.BLENDMODE_BLEND
        r.draw_color = color if len(color) == 4 else (*color, 255)
        x, y, w, h = rect
        r.fill_rect((x + self.ox, y + self.oy, w, h))

    def layer(self, w, h):
        tex = self.gpu.layer_texture(w, h)
        return GpuCanvas(self.gpu, tex, (w, h))

    def blit_layer(self, layer, pos):
        self._bind()
        w, h = layer.size
        layer.target.draw(dstrect=(pos[0] + self.ox, pos[1] + self.oy, w, h))

    def rect(self, color, rect, width=1):
        x, y, w, h = pygame.Rect(rect)
        for part in ((x, y, w, width), (x, y + h - width, w, width), (x, y, width, h), (x + w - width, y, width, h)):
            self.fill_rect(color, part)


def _tint(tex, color):
    tex.color = (color[0], color[1], color[2])
    tex.alpha = color[3] if len(color) == 4 else 255
