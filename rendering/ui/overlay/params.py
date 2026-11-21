"""Settings panel and setup screen."""
import pygame

from brain.profiles import PROFILES
from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER, _clip
from rendering.ui.overlay.texts import PARAM_COLUMNS
from rendering.ui.overlay.widgets import HOVER, DIM, wrap, _button


class ParamsMixin:
    def _draw_params(self, window, params):
        """Settings panel and setup screen, in frosted glass. Two columns of sections, the species, the presets, and the
        full description of the setting under the mouse at the bottom."""
        u, f, w = self.u, self.fonts, self.area
        self._hits = []
        pad, gap = round(18 * u), round(16 * u)
        mouse = self.mouse
        by_key = {p[0]: p for p in params}
        sections = [[(title, [k for k in keys if k in by_key]) for title, keys in col] for col in PARAM_COLUMNS]
        known = {k for col in PARAM_COLUMNS for _, keys in col for k in keys}
        others = [k for k in by_key if k not in known]
        if others:
            sections[1].append(("Autres", others))
        species = list(PROFILES)
        head_h, preset_h, desc_h, foot_h = round(70 * u), round(40 * u), round(46 * u), round(52 * u)
        sec_h = round(26 * u)

        def column_rows(col, with_species):
            n_rows = sum(len(keys) for _, keys in col)
            n_heads = sum(1 for _, keys in col if keys) + (1 if with_species else 0)
            return n_rows, n_heads, (len(species) if with_species else 0)

        left, right = column_rows(sections[0], False), column_rows(sections[1], True)
        avail = w.h - round(24 * u) - head_h - preset_h - desc_h - foot_h
        row_h = round(34 * u)
        sp_h = round(24 * u)
        need = max(n[0] * row_h + n[1] * sec_h + n[2] * sp_h for n in (left, right))
        if need > avail:   # Small window: everything gets tighter
            k = max(0.55, avail / need)
            row_h, sec_h, sp_h = round(row_h * k), round(sec_h * k), round(sp_h * k)
            need = max(n[0] * row_h + n[1] * sec_h + n[2] * sp_h for n in (left, right))
        pw = min(round(940 * u), w.w - round(24 * u))
        rect = pygame.Rect(0, 0, pw, head_h + preset_h + need + desc_h + foot_h)
        rect.center = w.center
        window.blit(self.veil, (0, 0))
        frost(window, rect, round(14 * u), alpha=185)
        self._rects["params"] = rect

        title = "Nouvelle simulation" if self.setup is not None else "Paramètres de simulation"
        window.blit(f["title"].render(title, True, VALUE), (rect.x + pad, rect.y + round(12 * u)))
        if self.setup is not None:
            line = ("Règle le monde avant de lancer : rien ne tourne encore. Orange = changé. "
                    + ("« Reprendre » repart de la population gardée." if self.setup["resume"]
                       else "« Lancer » crée une population au hasard."))
        else:
            line = ("Les changements s'appliquent tout de suite, sauf obstacles, taille du monde, gène de taille, "
                    "fondateurs et espèces (au prochain départ).")
        window.blit(f["small"].render(_clip(f["small"], line, pw - 2 * pad), True, LABEL),
                    (rect.x + pad, rect.y + round(44 * u)))

        def button(r, text, action, enabled=True, accent=False):
            _button(window, r, text, f, u, enabled, mouse is not None and r.collidepoint(mouse), accent)
            if enabled:
                self._hits.append((r, action))

        # Presets
        py = rect.y + head_h
        bh = round(28 * u)
        lab = f["base"].render("Préréglage", True, AMBER)
        window.blit(lab, (rect.x + pad, py + (bh - lab.get_height()) // 2))
        x = rect.x + pad + lab.get_width() + round(14 * u)
        name = self.presets.label() if self.presets is not None else "indisponible"
        for action, text in (("preset_prev", "<"),):
            r = pygame.Rect(x, py, bh, bh)
            button(r, text, action, self.presets is not None)
            x = r.right + round(4 * u)
        name_w = round(260 * u)
        box = pygame.Rect(x, py, name_w, bh)
        pygame.draw.rect(window, (10, 13, 17), box, border_radius=max(3, round(6 * u)))
        img = f["small"].render(_clip(f["small"], name, name_w - round(12 * u)), True, VALUE)
        window.blit(img, (box.x + round(8 * u), box.centery - img.get_height() // 2))
        r = pygame.Rect(box.right + round(4 * u), py, bh, bh)
        button(r, ">", "preset_next", self.presets is not None)
        x = r.right + round(10 * u)
        for action, text in (("preset_apply", "Appliquer"), ("preset_save", "Enregistrer les réglages actuels")):
            bw = f["small"].size(text)[0] + round(22 * u)
            r = pygame.Rect(x, py, bw, bh)
            if r.right <= rect.right - pad:
                usable = self.presets is not None and (action != "preset_apply" or bool(self.presets.files))
                button(r, text, action, usable)
            x = r.right + round(8 * u)

        # Two columns of settings
        col_w = (pw - 2 * pad - gap) // 2
        ab = max(round(18 * u), min(round(24 * u), row_h - round(8 * u)))
        vw = min(round(150 * u), col_w // 3)
        hovered_desc = None
        any_pending = False
        top = rect.y + head_h + preset_h
        for ci, col in enumerate(sections):
            x0 = rect.x + pad + ci * (col_w + gap)
            y = top
            for sec_title, keys in col:
                if not keys:
                    continue
                img = f["small"].render(sec_title.upper(), True, DIM)
                window.blit(img, (x0, y + sec_h - img.get_height() - round(4 * u)))
                line_y = y + sec_h - img.get_height() // 2 - round(4 * u)
                pygame.draw.line(window, (70, 80, 92), (x0 + img.get_width() + round(8 * u), line_y),
                                 (x0 + col_w, line_y))
                y += sec_h
                for key in keys:
                    _, label, desc, cur, pend = by_key[key]
                    row = pygame.Rect(x0 - round(6 * u), y, col_w + round(12 * u), row_h)
                    if mouse and row.collidepoint(mouse):
                        pygame.draw.rect(window, (40, 48, 58), row, border_radius=round(6 * u))
                        hovered_desc = (label, desc)
                    r_inc = pygame.Rect(x0 + col_w - ab, row.centery - ab // 2, ab, ab)
                    val = pygame.Rect(r_inc.x - vw - round(4 * u), row.centery - ab // 2, vw, ab)
                    r_dec = pygame.Rect(val.x - ab - round(4 * u), row.centery - ab // 2, ab, ab)
                    for r, sign in ((r_dec, -1), (r_inc, 1)):
                        hov = mouse is not None and r.collidepoint(mouse)
                        pygame.draw.rect(window, HOVER if hov else (34, 41, 48), r, border_radius=max(3, round(5 * u)))
                        cx, cy, s = r.centerx, r.centery, round(4 * u)
                        pygame.draw.polygon(window, VALUE, [(cx - sign * s * 0.6, cy - s),
                                                            (cx - sign * s * 0.6, cy + s),
                                                            (cx + sign * s * 0.9, cy)])
                    self._hits.append((r_dec, f"param:dec:{key}"))
                    self._hits.append((r_inc, f"param:inc:{key}"))
                    pygame.draw.rect(window, (10, 13, 17), val, border_radius=max(3, round(5 * u)))
                    text, color = (pend, AMBER) if pend is not None else (cur, VALUE)
                    any_pending = any_pending or pend is not None
                    img = f["base"].render(_clip(f["base"], text, vw - round(8 * u)), True, color)
                    window.blit(img, (val.centerx - img.get_width() // 2, val.centery - img.get_height() // 2))
                    img = f["base"].render(_clip(f["base"], label, r_dec.x - x0 - round(8 * u)), True,
                                           AMBER if pend is not None else VALUE)
                    window.blit(img, (x0, row.centery - img.get_height() // 2))
                    y += row_h
            if ci == 1:
                # Species: tick boxes (applied at the next start)
                ticked = self.state.get("profiles", list(self.hud.cfg.ACTIVE_PROFILES))
                head_color = AMBER if self.state.get("profiles_pending") else DIM
                img = f["small"].render("ESPÈCES (AU PROCHAIN DÉPART)", True, head_color)
                window.blit(img, (x0, y + sec_h - img.get_height() - round(4 * u)))
                y += sec_h
                for name in species:
                    row = pygame.Rect(x0 - round(6 * u), y, col_w + round(12 * u), sp_h)
                    if mouse and row.collidepoint(mouse):
                        pygame.draw.rect(window, (40, 48, 58), row, border_radius=round(6 * u))
                        hovered_desc = (PROFILES[name]["title"],
                                        "Coche ou décoche cette espèce. Il en faut au moins une. Le changement "
                                        "s'applique au prochain départ (« Lancer » ou « Repartir de zéro »).")
                    cb = pygame.Rect(x0, row.centery - round(7 * u), round(14 * u), round(14 * u))
                    if name in ticked:
                        pygame.draw.rect(window, MINT, cb, border_radius=3)
                    else:
                        pygame.draw.rect(window, DIM, cb, width=1, border_radius=3)
                    pygame.draw.circle(window, PROFILES[name]["color"], (cb.right + round(14 * u), row.centery),
                                       max(3, round(5 * u)))
                    img = f["small"].render(PROFILES[name]["title"], True, VALUE if name in ticked else DIM)
                    window.blit(img, (cb.right + round(26 * u), row.centery - img.get_height() // 2))
                    self._hits.append((row, f"profile:{name}"))
                    y += sp_h

        # Description of the setting under the mouse
        dy = rect.bottom - foot_h - desc_h + round(4 * u)
        pygame.draw.line(window, (70, 80, 92), (rect.x + pad, dy - round(4 * u)), (rect.right - pad, dy - round(4 * u)))
        if hovered_desc:
            lab, desc = hovered_desc
            lines = wrap(f["small"], f"{lab} : {desc}", pw - 2 * pad)[:2]
        else:
            lines = ["Survole un réglage pour lire sa description complète. Flèches : valeur précédente / suivante."]
        for i, t in enumerate(lines):
            line_h = f["small"].get_height() + round(2 * u)
            window.blit(f["small"].render(t, True, LABEL), (rect.x + pad, dy + round(4 * u) + i * line_h))

        # Footer buttons, right to left
        by, bh = rect.bottom - foot_h + round(12 * u), round(30 * u)
        x = rect.right - pad
        if self.setup is not None:
            buttons = (("setup_launch", "Lancer", True, True),)
            if self.setup["resume"]:
                buttons += (("setup_resume", "Reprendre la population gardée", True, False),)
            if self.setup["cancel"]:
                buttons += (("setup_cancel", "Annuler", True, False),)
            if self.setup.get("from_start"):
                buttons += (("start_back", "Retour", True, False),)
            buttons += (("params_cancel", "Annuler les changements", any_pending, False),)
        else:
            buttons = (("params_close", "Fermer", True, False), ("restart_now", "Repartir de zéro", True, any_pending),
                       ("params_cancel", "Annuler les changements", any_pending, False))
        for action, text, enabled, accent in buttons:
            bw = f["small"].size(text)[0] + round(24 * u)
            r = pygame.Rect(x - bw, by, bw, bh)
            button(r, text, action, enabled, accent)
            x = r.x - round(8 * u)
