"""Obstacle sprites: sea anemones seen from above. A dark mat that follows the exact collision shape, three crowns of
curling tentacles with light tips, and a mouth in the middle. The tentacles swim gently: a few frames are drawn per
obstacle and played in a loop (built one at a time, so a new generation never stalls the game).
Pure rendering. No simulation random number is drawn: each anemone has its own private generator, seeded from
its own radius and rotation, so the picture is fixed for a given obstacle."""
import math
import random

import numpy as np
import pygame

import config

# (mat, tentacle, tip) colours. Cool hues on purpose: food is green, poison purple, creatures warm orange.
PALETTES = [
    ((38, 52, 104), (86, 112, 200), (196, 224, 255)),     # indigo
    ((26, 74, 96), (62, 150, 176), (200, 246, 252)),      # teal
    ((62, 56, 108), (142, 126, 204), (228, 218, 255)),    # lilac
]
CORNER = {"square": 0.20, "triangle": 0.17}     # Corner rounding of the collision shape, in radii
FRAMES = 12                                     # Frames of the sway loop (two neighbours are cross-faded: smooth at any speed)
PERIOD_MS = 1500                                # Duration of one loop
BUILDS_PER_TICK = 2                             # New frames built per game frame at most (a new generation never stalls)
SS = 2                                          # Tentacles are drawn 2x bigger then shrunk, for smooth edges
SHADOW_OFFSET = (0.04, 0.07)
SHADOW_BLUR = 0.50
SHADOW_STRENGTH = 0.22
_cache = {}
_state = {"tick": -1, "builds": 0}


def _signed_distance(shape, rotation, R):
    """Function (X, Y) → signed distance to the collision outline in pixels (negative inside)."""
    if shape not in CORNER:
        return lambda X, Y: np.sqrt(X * X + Y * Y) - R
    n = 4 if shape == "square" else 3
    rc = CORNER[shape] * R
    apothem = R * math.cos(math.pi / n)
    inset_r = (apothem - rc) / math.cos(math.pi / n)
    verts = [(inset_r * math.cos(rotation + 2 * math.pi * k / n), inset_r * math.sin(rotation + 2 * math.pi * k / n))
             for k in range(n)]
    normals = [(math.cos(rotation + math.pi * (2 * k + 1) / n), math.sin(rotation + math.pi * (2 * k + 1) / n))
               for k in range(n)]
    offset = apothem - rc

    def sd(X, Y):
        inside = np.stack([X * nx + Y * ny - offset for nx, ny in normals]).max(axis=0)
        seg = []
        for i in range(n):
            ax, ay = verts[i]
            bx, by = verts[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            t = np.clip(((X - ax) * ex + (Y - ay) * ey) / (ex * ex + ey * ey), 0.0, 1.0)
            seg.append(np.hypot(X - (ax + t * ex), Y - (ay + t * ey)))
        outside = np.min(np.stack(seg), axis=0)
        return np.where(inside <= 0, inside, outside) - rc

    return sd


def _boundary(shape, rotation, R):
    """Function angle → distance from the centre to the collision outline (a little less at rounded corners)."""
    if shape not in CORNER:
        return lambda th: R
    n = 4 if shape == "square" else 3
    apothem = R * math.cos(math.pi / n)
    angles = [rotation + math.pi * (2 * k + 1) / n for k in range(n)]

    def b(th):
        best = R
        for a in angles:
            c = math.cos(th - a)
            if c > 1e-3:
                best = min(best, apothem / c)
        return best * 0.94
    return b


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _build_base(o, k, pal):
    """Mat and soft shadow (numpy, once per obstacle): RGBA surface, and the half size of the tentacle area."""
    R = o.radius * k
    pad = R * (SHADOW_BLUR + max(SHADOW_OFFSET) + 0.1) + 3
    size = int(math.ceil(2 * (R + pad)))
    c = size / 2.0
    X = (np.arange(size, dtype=np.float32)[:, None] + 0.5 - c) * np.ones((1, size), dtype=np.float32)
    Y = (np.arange(size, dtype=np.float32)[None, :] + 0.5 - c) * np.ones((size, 1), dtype=np.float32)
    sd_fn = _signed_distance(o.shape, o.rotation, R)
    sd = sd_fn(X, Y)
    depth = np.maximum(-sd, 0.0)
    rr = np.clip(np.sqrt(X * X + Y * Y) / R, 0.0, 1.0)
    mat = np.array(pal[0], dtype=np.float32)[None, None, :] * (0.50 + 0.55 * (1.0 - rr) ** 1.6)[:, :, None]
    # The mat fades out towards the edge: no outline, the tentacles alone draw the silhouette
    t = np.clip(depth / (0.5 * R), 0.0, 1.0)
    body_a = np.clip(0.5 - sd, 0.0, 1.0) * (0.10 + 0.82 * t * t * (3.0 - 2.0 * t))
    s_sd = sd_fn(X - SHADOW_OFFSET[0] * R, Y - SHADOW_OFFSET[1] * R)
    shadow_a = SHADOW_STRENGTH * np.clip(1.0 - s_sd / (SHADOW_BLUR * R + 1e-6), 0.0, 1.0) ** 2
    shadow_a = np.where(s_sd <= 0, SHADOW_STRENGTH, shadow_a)
    out_a = body_a + shadow_a * (1.0 - body_a)
    out_rgb = mat * body_a[:, :, None] / np.maximum(out_a, 1e-6)[:, :, None]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(surf)[:] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    pygame.surfarray.pixels_alpha(surf)[:] = np.clip(out_a * 255.0, 0, 255).astype(np.uint8)
    return surf, size // 2


def _sides(shape):
    return {"square": 4, "triangle": 3}.get(shape, 0)


def _outline_angles(bound, n, th0, rng, jitter):
    """n directions whose points on the outline are evenly spaced along its length (starting at angle th0, a corner)."""
    ths = th0 + np.linspace(0.0, 2 * math.pi, 1441)
    pts = np.array([[bound(t) * math.cos(t), bound(t) * math.sin(t)] for t in ths])
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    step = cum[-1] / n
    return [float(np.interp((i + rng.uniform(-jitter, jitter)) * step, cum, ths)) for i in range(n)]


def _make_tentacles(o, k, rng):
    """Geometry of every tentacle (final pixels), fixed for the obstacle: (layer, angle, r0, r1, curl, wave phase, width).
    Each crown starts on a scaled copy of the outline and ends near the outline itself, so a triangular obstacle is a
    triangular anemone."""
    R = o.radius * k
    bound = _boundary(o.shape, o.rotation, R)
    sides = _sides(o.shape)
    th0 = o.rotation if sides else 0.0
    n1 = 15 + int(o.radius * 0.50)
    counts = [n1, int(n1 * 0.82), int(n1 * 0.62), int(n1 * 0.42)]
    if sides:                                       # A multiple of the number of corners: one tentacle on each corner
        counts = [max(sides, int(math.ceil(c / sides)) * sides) for c in counts]
    reach = (1.0, 0.82, 0.62, 0.42)                 # Where each crown ends, as a fraction of the outline distance
    start_at = (0.50, 0.34, 0.20, 0.10)
    widths = (0.13, 0.12, 0.105, 0.09)
    specs = []
    for layer in range(4):
        n = counts[layer]
        for i, th in enumerate(_outline_angles(bound, n, th0, rng, 0.12)):
            b = bound(th)
            r1 = b * reach[layer] * (1.0 + rng.uniform(-0.07, 0.0))      # Never past the outline
            r0 = b * start_at[layer]
            curl = (0.26 if not sides else 0.15) + rng.uniform(-0.08, 0.08)   # Same direction: a gentle spiral
            specs.append((layer, th, r0, r1, curl, 3.0 * th + rng.uniform(-0.6, 0.6), max(1.3, R * widths[layer])))
    return specs


def _draw_tentacle(layer_surf, spec, c, pal, phi):
    layer, th, r0, r1, curl, wph, w0 = spec
    L = r1 - r0
    steps = 12
    shade = (0.56, 0.72, 0.88, 1.0)[layer]
    amp = 0.15 * L
    cos_t, sin_t = math.cos(th), math.sin(th)
    prev = None
    for i in range(steps + 1):
        s = i / steps
        r = r0 + L * s
        lat = curl * L * s ** 1.5 + amp * math.sin(phi + wph + s * 3.0) * s
        x = c + (r * cos_t - lat * sin_t) * SS
        y = c + (r * sin_t + lat * cos_t) * SS
        w = w0 * (1.0 - 0.50 * s)                       # Tapers towards the tip
        t = s ** 1.8
        col = _mix(pal[1], pal[2], t)
        sh = shade + (1.0 - shade) * t
        col = tuple(int(min(255, v * sh)) for v in col)
        if prev is not None:                            # Thick segment + round joint = smooth tube
            pygame.draw.line(layer_surf, col, prev, (x, y), max(1, int(w * SS)))
        pygame.draw.circle(layer_surf, col, (x, y), max(1.0, w * 0.5 * SS))
        prev = (x, y)
    tip = tuple(int(min(255, v * (shade + (1 - shade) * 0.85))) for v in pal[2])
    pygame.draw.circle(layer_surf, tip, prev, max(1.0, w * 0.78 * SS))
    pygame.draw.circle(layer_surf, (255, 255, 255), (prev[0] - w * 0.18 * SS, prev[1] - w * 0.18 * SS), max(1.0, w * 0.16 * SS))


def _build_frame(entry, frame):
    pal, specs, half, R = entry["pal"], entry["specs"], entry["half"], entry["R"]
    phi = 2 * math.pi * frame / FRAMES
    side = 2 * half * SS
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    layer.fill((*pal[1], 0))                      # Transparent but tentacle-coloured: no dark fringe when shrunk
    c = half * SS
    for spec in specs:                            # Outer crown first, inner crown last
        _draw_tentacle(layer, spec, c, pal, phi)
    # Mouth: a small copy of the outline
    bound, th0 = entry["bound"], entry["th0"]
    mouth = [(c + 0.19 * bound(t) * math.cos(t) * SS, c + 0.19 * bound(t) * math.sin(t) * SS)
             for t in (th0 + 2 * math.pi * i / 48 for i in range(48))]
    pygame.draw.polygon(layer, _mix(pal[0], (0, 0, 0), 0.45), mouth)
    pygame.draw.polygon(layer, pal[1], mouth, max(1, int(0.045 * R * SS)))
    pygame.draw.circle(layer, _mix(pal[2], pal[1], 0.4), (c, c), max(1.0, 0.045 * R * SS))
    small = pygame.transform.smoothscale(layer, (2 * half, 2 * half))
    sprite = entry["base"].copy()
    cx = entry["center"]
    sprite.blit(small, (cx - half, cx - half))
    return sprite


def _entry(o, k):
    key = (o.shape, round(o.radius, 3), round(o.rotation, 3), round(k, 4))
    entry = _cache.get(key)
    if entry is None:
        if len(_cache) > 40:
            _cache.clear()
        seed = int(o.radius * 1000) * 7919 + int(o.rotation * 1000) * 104729 + len(o.shape)
        rng = random.Random(seed)                 # Private generator: the simulation's one is never used
        pal = PALETTES[rng.randrange(len(PALETTES))]
        base, center = _build_base(o, k, pal)
        R = o.radius * k
        entry = {"pal": pal, "base": base, "center": center, "R": R, "half": int(math.ceil(R)) + 4,
                 "bound": _boundary(o.shape, o.rotation, R), "th0": o.rotation if _sides(o.shape) else 0.0,
                 "specs": _make_tentacles(o, k, rng), "frames": [None] * FRAMES, "offset": rng.uniform(0, FRAMES)}
        _cache[key] = entry
    return entry


def draw_obstacle(screen, o, px, py, k):
    """Draws the anemone centred on (px, py). The sway is a loop of FRAMES pictures; the two pictures around the current
    time are cross-faded, so the motion is smooth. Frames are built as they are needed, a couple per game frame."""
    entry = _entry(o, k)
    now = pygame.time.get_ticks()
    if _state["tick"] != now:
        _state["tick"], _state["builds"] = now, 0
    frames = entry["frames"]
    pos = now / PERIOD_MS * FRAMES + entry["offset"]
    a, frac = int(pos) % FRAMES, pos - int(pos)
    b = (a + 1) % FRAMES
    for idx in (a, b):
        if frames[idx] is None and (all(f is None for f in frames) or _state["builds"] < BUILDS_PER_TICK):
            frames[idx] = _build_frame(entry, idx)
            _state["builds"] += 1
    if frames[a] is None:                          # Not built yet: the closest built frame takes over
        built = [i for i, f in enumerate(frames) if f is not None]
        a = min(built, key=lambda i: min((i - a) % FRAMES, (a - i) % FRAMES))
        frac = 0.0
    c = entry["center"]
    dest = (round(px) - c, round(py) - c)
    frames[a].set_alpha(255)
    screen.blit(frames[a], dest)
    if frames[b] is not None and b != a and frac > 0.02:
        frames[b].set_alpha(int(frac * 255))
        screen.blit(frames[b], dest)


def obstacle_sprite(o, k):
    """(surface, (cx, cy)) of the frame at the current time, without the cross-fade (kept for other callers)."""
    entry = _entry(o, k)
    frames = entry["frames"]
    idx = int(pygame.time.get_ticks() / PERIOD_MS * FRAMES + entry["offset"]) % FRAMES
    if frames[idx] is None:
        frames[idx] = _build_frame(entry, idx)
    return frames[idx], (entry["center"], entry["center"])
