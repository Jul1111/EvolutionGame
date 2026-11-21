"""Large network view of the selected creature."""
import pygame

from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER
from rendering.ui.netview import network_rows, _node, _edge
from rendering.ui.overlay.widgets import PANEL, DIM


class NetworkMixin:
    def _draw_net_big(self, window, world, selected):
        u, f, w = self.u, self.fonts, self.area
        pw, ph = round(w.w * 0.56), round(w.h * 0.62)
        rect = pygame.Rect(0, 0, pw, ph)
        if self.net_pos is None:
            rect.bottomright = (w.right - round(12 * u), w.bottom - round(12 * u))
        else:
            rect.topleft = self.net_pos
        rect.clamp_ip(w)
        self.net_pos = rect.topleft
        frost(window, rect, round(12 * u), alpha=150)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*PANEL, 60), surf.get_rect(), border_radius=round(12 * u))
        grab = f["small"].render("Glisser le titre pour déplacer", True, DIM)
        surf.blit(grab, (pw - round(16 * u) - grab.get_width(), round(16 * u)))
        pad = round(16 * u)
        surf.blit(f["title"].render("Réseau de la créature sélectionnée", True, VALUE), (pad, round(10 * u)))
        self._rects["net"] = rect
        if selected is None or not selected.alive:
            note = "Clique sur une créature vivante." if selected is None else "Créature morte."
            surf.blit(f["base"].render(note, True, LABEL), (pad, round(48 * u)))
            window.blit(surf, rect.topleft)
            return
        flag = selected.food_nearby
        inputs = world.sense(selected)
        selected.food_nearby = flag
        hidden, outputs = selected.brain.activations(inputs)
        rows = network_rows(inputs, outputs, selected.profile)
        n_in, n_h, n_out = len(inputs), len(hidden), len(outputs)
        top, bottom = round(52 * u), round(34 * u)
        left_w, right_w = round(190 * u), round(140 * u)
        area = pygame.Rect(left_w, top, pw - left_w - right_w, ph - top - bottom)
        xs = (area.x, area.centerx, area.right)

        def column(x, n):
            step = area.h / max(n, 1)   # No hidden neuron (n = 0): an empty column
            return [(x, int(area.y + step * (k + 0.5))) for k in range(n)]

        pin, ph_, pout = column(xs[0], n_in), column(xs[1], n_h), column(xs[2], n_out)
        r = max(5, min(round(13 * u), int(area.h / max(n_in, n_h, n_out) / 2.3)))
        wmax = max(float(abs(selected.brain.w1).max()),
                   float(abs(selected.brain.w2).max()) if selected.brain.w2.size else 0.0, 1e-9)
        if n_h == 0:   # No hidden neuron: inputs wired straight to the outputs
            for o in range(n_out):
                for i in range(n_in):
                    _edge(surf, pin[i], pout[o], float(selected.brain.w1[o, i]), float(inputs[i]), wmax)
        for h in range(n_h):
            for i in range(n_in):
                _edge(surf, pin[i], ph_[h], float(selected.brain.w1[h, i]), float(inputs[i]), wmax)
        for o in range(n_out):
            for h in range(n_h):
                _edge(surf, ph_[h], pout[o], float(selected.brain.w2[o, h]), float(hidden[h]), wmax)
        for pos, v in zip(pin, inputs):
            _node(surf, *pos, r, float(v))
        for pos, v in zip(ph_, hidden):
            _node(surf, *pos, r, float(v))
        for pos, v in zip(pout, outputs):
            _node(surf, *pos, r, float(v))
        sm = f["small"]
        for (label, txt, _, _, _), (x, y) in zip(rows[:n_in], pin):
            lab = sm.render(label, True, LABEL)
            surf.blit(lab, (x - r - round(8 * u) - lab.get_width(), y - lab.get_height() // 2))
            val = sm.render(txt, True, MINT)
            surf.blit(val, (x - r - round(16 * u) - lab.get_width() - val.get_width(), y - val.get_height() // 2))
        for (label, txt, _, _, _), (x, y) in zip(rows[n_in:], pout):
            lab = sm.render(label, True, LABEL)
            surf.blit(lab, (x + r + round(8 * u), y - lab.get_height() // 2))
            val = sm.render(txt, True, AMBER)
            surf.blit(val, (x + r + round(8 * u), y + lab.get_height() // 2 - round(1 * u)))
        cap = sm.render("Neurone : vert = activation positive, rouge = négative.  Lien : couleur = signe du signal, "
                        "épaisseur = force.  N : changer la taille.", True, DIM)
        max_w = pw - 2 * pad
        if cap.get_width() > max_w:   # Too wide for the panel: shrunk to fit
            cap = pygame.transform.smoothscale(cap, (max_w, round(cap.get_height() * max_w / cap.get_width())))
        surf.blit(cap, (pad, ph - bottom + round(10 * u)))
        window.blit(surf, rect.topleft)
