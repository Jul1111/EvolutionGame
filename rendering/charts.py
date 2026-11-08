"""Large curves view (key G, third press): the timeline of the population over the free area of the world.
Time axis with graduations, one curve per ticked series (each on its own scale, from 0 to its maximum), a vertical
cursor that reads every value at the time under the mouse, and the list of series as tick boxes on the right."""
import pygame

from rendering.glass import frost
from rendering.hud import SERIES, VALUE, LABEL, _clip
from utils.timefmt import format_time

DIM = (110, 122, 128)
GRID = (255, 255, 255, 18)


def _nice_step(span, target=6):
    """Round step (1, 2 or 5 × 10^n) giving about `target` graduations over `span`."""
    raw = max(span / target, 1e-9)
    mag = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class ChartView:
    def __init__(self, hud):
        self.hud = hud
        self.rect = None
        self._hits = []
        self._cache_key = None
        self._plot_surf = None

    def click(self, x, y):
        """True if the click landed on the view (a tick box toggles its curve)."""
        if self.rect is None or not self.rect.collidepoint(x, y):
            return False
        for r, key in self._hits:
            if r.collidepoint(x, y):
                self.hud.toggle_series(key)
                self._cache_key = None
        return True

    def draw(self, window, rect, fonts, u, mouse):
        self.rect = rect
        self._hits = []
        frost(window, rect, max(4, round(12 * u)), alpha=175)
        pad = round(16 * u)
        window.blit(fonts["title"].render("Courbes dans le temps", True, VALUE), (rect.x + pad, rect.y + round(10 * u)))
        note = "Chaque courbe a sa propre échelle (de 0 à son maximum). G : fermer."
        window.blit(fonts["small"].render(note, True, LABEL), (rect.x + pad, rect.y + round(40 * u)))
        rows = self.hud.rows
        keys = self.hud.chart_keys
        legend_w = round(250 * u)
        top = rect.y + round(66 * u)
        plot = pygame.Rect(rect.x + pad, top, rect.w - legend_w - 3 * pad, rect.bottom - top - round(40 * u))
        legend = pygame.Rect(plot.right + pad, top, legend_w, plot.h)

        # Tick boxes, one per series, with the last value
        small = fonts["small"]
        line_h = max(small.get_height() + round(6 * u), (legend.h) // max(1, len(SERIES)))
        line_h = min(line_h, round(26 * u))
        for i, (key, label, color, value, fixed_max, fmt) in enumerate(SERIES):
            y = legend.y + i * line_h
            box = pygame.Rect(legend.x, y + (line_h - round(12 * u)) // 2, round(12 * u), round(12 * u))
            on = key in keys
            if on:
                pygame.draw.rect(window, color, box, border_radius=max(2, round(3 * u)))
            else:
                pygame.draw.rect(window, color, box, width=max(1, round(1.5 * u)), border_radius=max(2, round(3 * u)))
            last = next((value(r) for r in reversed(rows) if value(r) is not None), None)
            last_txt = fmt(last) if last is not None else "-"
            lw = small.size(last_txt)[0]
            text = _clip(small, label, legend.w - round(24 * u) - lw - round(8 * u))
            window.blit(small.render(text, True, VALUE if on else DIM), (box.right + round(8 * u), y + (line_h - small.get_height()) // 2))
            window.blit(small.render(last_txt, True, VALUE if on else DIM), (legend.right - lw, y + (line_h - small.get_height()) // 2))
            self._hits.append((pygame.Rect(legend.x, y, legend.w, line_h), key))

        # Plot (cached: it only changes with a new timeline line, the series or the size)
        selected = [s for s in SERIES if s[0] in keys]
        cache_key = (id(rows), len(rows), tuple(sorted(keys)), plot.size)
        if cache_key != self._cache_key:
            self._cache_key = cache_key
            self._plot_surf = self._render_plot(rows, selected, plot.size, fonts, u)
        window.blit(self._plot_surf, plot.topleft)

        # Cursor: values at the time under the mouse
        ticks = [r.get("tick") for r in rows]
        if mouse is not None and plot.collidepoint(mouse) and len(rows) > 1 and selected:
            t0, t1 = ticks[0] or 0, ticks[-1] or 1
            t = t0 + (mouse[0] - plot.x) / plot.w * (t1 - t0)
            j = min(range(len(rows)), key=lambda i: abs((ticks[i] or 0) - t))
            x = plot.x + ((ticks[j] or 0) - t0) / max(t1 - t0, 1) * plot.w
            pygame.draw.line(window, (230, 236, 244), (x, plot.y), (x, plot.bottom), 1)
            lines = [(format_time(ticks[j] or 0), VALUE)]
            for key, label, color, value, fixed_max, fmt in selected:
                v = value(rows[j])
                lines.append((f"{label} : {fmt(v) if v is not None else '-'}", color))
            imgs = [small.render(t_, True, c) for t_, c in lines]
            bw = max(i.get_width() for i in imgs) + round(16 * u)
            bh = sum(i.get_height() + round(2 * u) for i in imgs) + round(12 * u)
            bx = x + round(12 * u) if x + round(12 * u) + bw < plot.right else x - round(12 * u) - bw
            box = pygame.Rect(bx, plot.y + round(8 * u), bw, bh)
            frost(window, box, max(3, round(6 * u)), alpha=200)
            yy = box.y + round(6 * u)
            for img in imgs:
                window.blit(img, (box.x + round(8 * u), yy))
                yy += img.get_height() + round(2 * u)

    def _render_plot(self, rows, selected, size, fonts, u):
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 255, 255, 10), surf.get_rect(), border_radius=max(3, round(6 * u)))
        small = fonts["small"]
        if len(rows) < 2 or not selected:
            text = "Pas encore assez de relevés" if len(rows) < 2 else "Coche une courbe à droite"
            img = small.render(text, True, LABEL)
            surf.blit(img, ((w - img.get_width()) // 2, (h - img.get_height()) // 2))
            return surf
        ticks = [r.get("tick") or 0 for r in rows]
        t0, t1 = ticks[0], ticks[-1]
        span = max(t1 - t0, 1)
        # Time graduations
        step = _nice_step(span / 60, 6) * 60   # In ticks, on whole seconds of simulated time
        g = (int(t0 // step) + 1) * step
        while g < t1:
            x = (g - t0) / span * w
            pygame.draw.line(surf, GRID, (x, 0), (x, h - small.get_height() - round(4 * u)))
            lab = small.render(format_time(g), True, DIM)
            surf.blit(lab, (min(max(0, x - lab.get_width() / 2), w - lab.get_width()), h - lab.get_height()))
            g += step
        for frac in (0.25, 0.5, 0.75):
            y = (h - small.get_height() - round(6 * u)) * (1 - frac)
            pygame.draw.line(surf, GRID, (0, y), (w, y))
        plot_h = h - small.get_height() - round(8 * u)
        for key, label, color, value, fixed_max, fmt in selected:
            vals = [value(r) for r in rows]
            seen = [v for v in vals if v is not None]
            if not seen:
                continue
            vmax = (fixed_max() if fixed_max else None) or (max(seen) * 1.05)
            vmax = vmax if vmax > 1e-9 else 1.0
            pts = [((ticks[i] - t0) / span * w, plot_h - max(0.0, min(v / vmax, 1.0)) * (plot_h - round(4 * u)))
                   for i, v in enumerate(vals) if v is not None]
            if len(pts) > 1:
                pygame.draw.aalines(surf, color, False, pts)
                pygame.draw.lines(surf, color, False, pts, max(1, round(1.5 * u)))
        return surf
