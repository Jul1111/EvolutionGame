"""Frosted glass: blurs what is already drawn under a rectangle, tints it, rounds its corners and draws a thin light
edge. Every floating panel calls frost() on its own rectangle just before drawing its content on top.
Cost kept low for Retina screens: the blur is a shrink then enlarge (smoothscale), the tint is applied on the small
image, the rounded corners only touch four small squares, and the edge is drawn straight on the target."""
import pygame

TINT = (14, 18, 24)      # Colour of the glass
ALPHA = 150              # How dark the glass is (0 = clear, 255 = opaque)
EDGE = (64, 72, 82)      # Thin light edge
BLUR = 8                 # Shrink factor: higher = blurrier (and cheaper)
_corner_masks = {}


def _corner_mask(radius):
    """Square radius×radius, opaque outside the quarter circle (top-left corner): what must stay unblurred."""
    if radius not in _corner_masks:
        m = pygame.Surface((radius, radius), pygame.SRCALPHA)
        m.fill((255, 255, 255, 255))
        pygame.draw.circle(m, (255, 255, 255, 0), (radius, radius), radius)
        _corner_masks[radius] = m
    return _corner_masks[radius]


def frost(target, rect, radius=0, tint=TINT, alpha=ALPHA, edge=True):
    """Frosted glass on `target` inside `rect` (pixels of target). Returns the clipped rect actually covered."""
    rect = pygame.Rect(rect).clip(target.get_rect())
    if rect.w < 4 or rect.h < 4:
        return rect
    w, h = rect.size
    radius = min(radius, w // 2, h // 2)
    corners = []
    if radius:
        mask = _corner_mask(radius)
        for flip_x, flip_y, (cx, cy) in ((False, False, rect.topleft), (True, False, (rect.right - radius, rect.y)),
                                         (False, True, (rect.x, rect.bottom - radius)),
                                         (True, True, (rect.right - radius, rect.bottom - radius))):
            keep = target.subsurface((cx, cy, radius, radius)).convert_alpha()
            keep.blit(pygame.transform.flip(mask, flip_x, flip_y), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            corners.append((keep, (cx, cy)))
    small = pygame.transform.smoothscale(target.subsurface(rect), (max(2, w // BLUR), max(2, h // BLUR)))
    veil = pygame.Surface(small.get_size(), pygame.SRCALPHA)
    veil.fill((*tint, alpha))
    small.blit(veil, (0, 0))
    target.blit(pygame.transform.smoothscale(small, (w, h)), rect.topleft)
    for keep, pos in corners:          # Put back what was outside the rounded corners
        target.blit(keep, pos)
    if edge:
        pygame.draw.rect(target, EDGE, rect, width=1, border_radius=radius)
    return rect
