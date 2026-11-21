"""Colours and small drawing helpers shared by the overlay panels: icons drawn with shapes, buttons, text wrapping."""
import math

import pygame

from rendering.ui.hud import VALUE
from rendering.world.scene import energy_color

PANEL = (25, 31, 37)
BORDER = (62, 72, 82)
HOVER = (48, 58, 68)
DIM = (110, 122, 128)
ACTIVE_BG = (40, 84, 74)

def wrap(font, text, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.size(trial)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------- icons (drawn with shapes, so no font has to provide the glyphs) ----------

def _icon(surf, name, rect, color, fonts, u):
    cx, cy = rect.center
    s = rect.w * 0.30                      # Half size of the icon
    w = max(2, round(2 * u))
    if name == "play":
        pygame.draw.polygon(surf, color, [(cx - s * 0.7, cy - s), (cx - s * 0.7, cy + s), (cx + s, cy)])
    elif name == "pause":
        for dx in (-s * 0.55, s * 0.55):
            pygame.draw.rect(surf, color, (cx + dx - s * 0.3, cy - s, s * 0.6, 2 * s))
    elif name == "step":
        pygame.draw.polygon(surf, color, [(cx - s, cy - s), (cx - s, cy + s), (cx + s * 0.5, cy)])
        pygame.draw.rect(surf, color, (cx + s * 0.6, cy - s, s * 0.45, 2 * s))
    elif name in ("minus", "plus"):
        pygame.draw.line(surf, color, (cx - s, cy), (cx + s, cy), w)
        if name == "plus":
            pygame.draw.line(surf, color, (cx, cy - s), (cx, cy + s), w)
    elif name == "cone":
        a0, a1 = math.radians(-60), math.radians(60)
        pts = [(cx - s * 0.9 + s * 2.1 * math.cos(a0 + (a1 - a0) * i / 8) * 0.9 + s * 0.9,
                cy + s * 2.0 * math.sin(a0 + (a1 - a0) * i / 8) * 0.9) for i in range(9)]
        origin = (cx - s * 0.9, cy)
        pygame.draw.lines(surf, color, False, [pts[0], origin, pts[-1]], w)
        pygame.draw.lines(surf, color, False, pts, w)
    elif name == "dots":
        for i, t in enumerate((0.1, 0.5, 0.9)):
            pygame.draw.circle(surf, energy_color(t), (cx + (i - 1) * s * 0.95, cy), max(3, round(s * 0.42)))
    elif name == "info":
        pygame.draw.circle(surf, color, (cx, cy), round(s * 1.15), w)
        img = fonts["small"].render("i", True, color)
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
    elif name == "star":
        pts = []
        for i in range(10):
            r = s * 1.25 if i % 2 == 0 else s * 0.55
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(surf, color, pts)
    elif name == "target":
        pygame.draw.circle(surf, color, (cx, cy), round(s * 0.8), w)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surf, color, (cx + dx * s * 0.8, cy + dy * s * 0.8), (cx + dx * s * 1.35, cy + dy * s * 1.35), w)
    elif name == "net":
        a = [(cx - s, cy - s * 0.8), (cx - s, cy + s * 0.8)]
        b = [(cx, cy - s * 0.9), (cx, cy), (cx, cy + s * 0.9)]
        c = [(cx + s, cy)]
        for p in a:
            for q in b:
                pygame.draw.line(surf, color, p, q, 1)
        for q in b:
            pygame.draw.line(surf, color, q, c[0], 1)
        for p in a + b + c:
            pygame.draw.circle(surf, color, p, max(2, round(s * 0.28)))
    elif name == "sliders":
        for i, k in enumerate((0.3, 0.7, 0.45)):
            y = cy + (i - 1) * s * 0.85
            pygame.draw.line(surf, color, (cx - s, y), (cx + s, y), 1)
            pygame.draw.circle(surf, color, (cx - s + 2 * s * k, y), max(2, round(s * 0.3)))
    elif name == "save":
        body = pygame.Rect(cx - s, cy - s, 2 * s, 2 * s)
        pygame.draw.rect(surf, color, body, w, border_radius=max(1, round(2 * u)))
        pygame.draw.rect(surf, color, (cx - s * 0.5, cy - s, s, s * 0.7))
        pygame.draw.line(surf, color, (cx - s * 0.6, cy + s * 0.35), (cx + s * 0.6, cy + s * 0.35), w)
    elif name == "curves":
        pts = [(cx - s * 1.1, cy + s * 0.7), (cx - s * 0.4, cy - s * 0.2), (cx + s * 0.2, cy + s * 0.3),
               (cx + s * 1.1, cy - s * 0.8)]
        pygame.draw.lines(surf, color, False, pts, w)
        pygame.draw.line(surf, color, (cx - s * 1.2, cy + s * 1.15), (cx + s * 1.2, cy + s * 1.15), 1)
    elif name == "kids":
        pygame.draw.circle(surf, color, (cx, cy - s * 0.45), round(s * 0.55))
        for dx in (-0.8, 0.8):
            pygame.draw.circle(surf, color, (cx + dx * s, cy + s * 0.75), max(2, round(s * 0.34)))
    elif name == "branch":
        pygame.draw.line(surf, color, (cx, cy + s * 1.1), (cx, cy - s * 0.2), w)
        pygame.draw.line(surf, color, (cx, cy + s * 0.25), (cx - s * 0.85, cy - s * 0.7), w)
        pygame.draw.line(surf, color, (cx, cy - s * 0.2), (cx + s * 0.85, cy - s * 0.95), w)
        for p in ((cx - s * 0.85, cy - s * 0.7), (cx + s * 0.85, cy - s * 0.95), (cx, cy - s * 0.2)):
            pygame.draw.circle(surf, color, p, max(2, round(s * 0.26)))
    elif name == "help":
        img = fonts["base"].render("?", True, color)
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


def _button(surf, rect, text, fonts, u, enabled=True, hovered=False, accent=False):
    bg = HOVER if (hovered and enabled) else (ACTIVE_BG if accent and enabled else (34, 41, 48))
    pygame.draw.rect(surf, bg, rect, border_radius=max(3, round(6 * u)))
    pygame.draw.rect(surf, BORDER, rect, width=1, border_radius=max(3, round(6 * u)))
    img = fonts["small"].render(text, True, VALUE if enabled else DIM)
    surf.blit(img, (rect.centerx - img.get_width() // 2, rect.centery - img.get_height() // 2))
