"""Drawing primitives of the side bar and the other panels: colours, fonts, coordinates, bars and text."""
import pygame

import config

VALUE = config.HUD_VALUE_COLOR
LABEL = config.HUD_LABEL_COLOR
MINT = (120, 224, 176)
AMBER = (240, 196, 92)
CORAL = (222, 96, 78)
BLUE = (110, 180, 235)


def create_fonts(u):
    """Fonts at the real size: every size is multiplied by the interface scale u, so text stays sharp."""
    def make(size, bold=False):
        return pygame.font.SysFont("arial", max(9, round(size * u)), bold=bold)
    return {"title": make(20, True), "base": make(15), "small": make(13)}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Ctx:
    """Converts logical coordinates to pixels: x/width/size by the scale u, y by u times the vertical stretch."""

    def __init__(self, u, ky=1.0):
        self.u = u
        self.ky = ky

    def x(self, v):
        return round(v * self.u)

    def y(self, v):
        return round(v * self.u * self.ky)


# ---------- drawing helpers ----------

def _panel(width, height, u):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    radius = max(4, round(12 * u))
    # Light tint only: the frosted glass under it (glass.frost, drawn by Hud.draw) gives the background and the edge
    pygame.draw.rect(surf, (*config.HUD_PANEL_COLOR[:3], 55), surf.get_rect(), border_radius=radius)
    return surf


def _bar(surf, x, y, w, h, fraction, color):
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(surf, (255, 255, 255, 25), (x, y, w, h), border_radius=h // 2)
    if fraction > 0:
        pygame.draw.rect(surf, color, (x, y, max(h, int(w * fraction)), h), border_radius=h // 2)


def _signed_bar(surf, x, y, w, h, value, color):
    """Bar centred on zero, value in [-1, 1]."""
    value = max(-1.0, min(1.0, value))
    pygame.draw.rect(surf, (255, 255, 255, 25), (x, y, w, h), border_radius=h // 2)
    mid = x + w // 2
    length = int(abs(value) * (w // 2))
    if length > 0:
        left = mid if value > 0 else mid - length
        pygame.draw.rect(surf, color, (left, y, length, h), border_radius=h // 2)
    pygame.draw.line(surf, (255, 255, 255, 90), (mid, y - 2), (mid, y + h + 1))


def _text(surf, font, txt, x, y, color, right=False):
    img = font.render(txt, True, color)
    surf.blit(img, (x - img.get_width() if right else x, y))
    return img


def _row(surf, fonts, c, y, label, value, value_color=VALUE):
    pad = c.x(14)
    _text(surf, fonts["base"], label, pad, c.y(y), LABEL)
    _text(surf, fonts["base"], value, surf.get_width() - pad, c.y(y), value_color, right=True)


def _clip(font, text, max_w):
    """Text shortened with an ellipsis so that it is at most max_w pixels wide."""
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "…")[0] > max_w:
        text = text[:-1]
    return text + "…"
