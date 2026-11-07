import pygame

from rendering.hud import VALUE, LABEL, MINT, create_fonts

BAR_BG = (19, 23, 28)
LINE = (48, 54, 60)
DROP_BG = (25, 31, 37)
DROP_BORDER = (62, 72, 82)
HOVER_BG = (48, 58, 68)
DIM = (110, 122, 128)

# Menus: (title, entries). An entry is None (separator) or (action, label, kind, state key, shortcut).
# - label: formatted with the state dict, so "{debug}" shows the current value;
# - kind: "action" (plain item) or "toggle" (check box showing state[key]);
# - action: the name handled by main.do(), the same one the keyboard shortcut triggers.
MENUS = [
    ("Simulation", [
        ("pause", "Pause", "toggle", "paused", "Espace"),
        ("step", "Avancer d'un tick (en pause)", "action", None, "→"),
        ("speed_up", "Accélérer", "action", None, "↑"),
        ("speed_down", "Ralentir", "action", None, "↓"),
    ]),
    ("Affichage", [
        ("debug", "Debug : {debug}", "action", None, "D"),
        ("color", "Couleur : {color}", "action", None, "C"),
        None,
        ("chart", "Courbes", "toggle", "chart", "G"),
        ("graph", "Graphe du réseau", "toggle", "graph", "N"),
        ("fullscreen", "Plein écran", "toggle", "fullscreen", "F"),
    ]),
    ("Sauvegarde", [
        ("end_gen", "Terminer la génération maintenant", "action", None, ""),
        None,
        ("reset", "{reset}", "action", None, ""),
    ]),
]


class MenuBar:
    """Horizontal menu bar with drop-down menus. Drawn straight on the window (the drop-downs cover the world and
    the side bar). The bar does not change anything itself: click() returns the action name, main.py runs it."""

    def __init__(self):
        self.open_index = None   # Menu whose list is open, or None
        self.hover_pos = None    # Last mouse position (surface pixels)
        self.state = {}
        self.layout = None

    def relayout(self, layout):
        """Call whenever the window size changes."""
        self.layout = layout
        u = self.u = layout.scale
        self.fonts = create_fonts(u)
        bar = layout.menu
        pad, x = round(14 * u), round(8 * u)
        self.title_rects = []
        for title, _ in MENUS:
            w = self.fonts["base"].size(title)[0] + 2 * pad
            self.title_rects.append(pygame.Rect(x, bar.y + round(4 * u), w, bar.h - round(8 * u)))
            x += w + round(2 * u)

    def close(self):
        self.open_index = None

    # ---------- geometry ----------

    def _label(self, entry):
        return entry[1].format(**self.state)

    def _rows(self):
        """Rows of the open list: [(rect, entry or None)]. Same geometry for drawing and for clicks."""
        if self.open_index is None:
            return []
        u, f = self.u, self.fonts
        entries = MENUS[self.open_index][1]
        pad, row_h, sep_h = round(12 * u), round(28 * u), round(9 * u)
        left = pad + round(22 * u)   # Room for the check box, kept on every row so the labels line up
        text_w = max(f["base"].size(self._label(e))[0] for e in entries if e)
        key_w = max((f["small"].size(e[4])[0] for e in entries if e and e[4]), default=0)
        width = left + text_w + round(28 * u) + key_w + pad
        t = self.title_rects[self.open_index]
        x = max(0, min(t.x, self.layout.window_size[0] - width))
        y = t.bottom + round(2 * u)
        rows = []
        for e in entries:
            h = sep_h if e is None else row_h
            rows.append((pygame.Rect(x, y, width, h), e))
            y += h
        return rows

    # ---------- mouse ----------

    def hover(self, x, y):
        """Mouse moved. While a list is open, pointing at another title opens that one."""
        self.hover_pos = (x, y)
        if self.open_index is not None:
            for i, r in enumerate(self.title_rects):
                if r.collidepoint(x, y):
                    self.open_index = i

    def click(self, x, y):
        """Left click. Returns (consumed, action): consumed = the click belongs to the menu (not to the world)."""
        for i, r in enumerate(self.title_rects):
            if r.collidepoint(x, y):
                self.open_index = None if self.open_index == i else i
                return True, None
        if self.open_index is not None:
            for rect, entry in self._rows():
                if rect.collidepoint(x, y):
                    return True, (entry[0] if entry else None)
            self.close()    # Click elsewhere: just close the list
            return True, None
        return self.layout.menu.collidepoint(x, y), None

    # ---------- drawing ----------

    def draw(self, window, state):
        """state: values shown by the labels and check boxes (see main.py)."""
        self.state = state
        f, u = self.fonts, self.u
        bar = self.layout.menu
        pygame.draw.rect(window, BAR_BG, bar)
        pygame.draw.line(window, LINE, (0, bar.bottom - 1), (bar.right, bar.bottom - 1))
        mouse = self.hover_pos

        for i, ((title, _), r) in enumerate(zip(MENUS, self.title_rects)):
            active = i == self.open_index
            hovered = mouse is not None and r.collidepoint(mouse)
            if active or hovered:
                pygame.draw.rect(window, HOVER_BG, r, border_radius=max(3, round(6 * u)))
            text = f["base"].render(title, True, VALUE if (active or hovered) else LABEL)
            window.blit(text, (r.centerx - text.get_width() // 2, r.centery - text.get_height() // 2))

        # Status on the right: speed and pause, always visible even when a panel is not
        status = f"x{state['speed']}" + ("  ·  Pause" if state["paused"] else "")
        img = f["small"].render(status, True, LABEL)
        window.blit(img, (bar.right - round(14 * u) - img.get_width(), bar.centery - img.get_height() // 2))

        rows = self._rows()
        if not rows:
            return
        x0, y0 = rows[0][0].topleft
        box = pygame.Rect(x0, y0, rows[0][0].w, rows[-1][0].bottom - y0).inflate(0, round(8 * u))
        pygame.draw.rect(window, DROP_BG, box, border_radius=max(4, round(8 * u)))
        pygame.draw.rect(window, DROP_BORDER, box, width=1, border_radius=max(4, round(8 * u)))
        pad, side = round(12 * u), round(14 * u)
        for rect, entry in rows:
            if entry is None:
                pygame.draw.line(window, LINE, (rect.x + pad, rect.centery), (rect.right - pad, rect.centery))
                continue
            if mouse is not None and rect.collidepoint(mouse):
                pygame.draw.rect(window, HOVER_BG, rect.inflate(-round(6 * u), 0), border_radius=max(3, round(6 * u)))
            action, _, kind, key, shortcut = entry
            if kind == "toggle":
                cb = pygame.Rect(rect.x + pad, rect.centery - side // 2, side, side)
                on = bool(state.get(key))
                if on:
                    pygame.draw.rect(window, MINT, cb, border_radius=3)
                    pts = [(cb.x + side * 0.22, cb.centery), (cb.x + side * 0.43, cb.bottom - side * 0.25),
                           (cb.right - side * 0.2, cb.y + side * 0.25)]
                    pygame.draw.lines(window, BAR_BG, False, pts, max(2, round(2 * u)))
                else:
                    pygame.draw.rect(window, DIM, cb, width=1, border_radius=3)
            text = f["base"].render(self._label(entry), True, VALUE)
            window.blit(text, (rect.x + pad + round(22 * u), rect.centery - text.get_height() // 2))
            if shortcut:
                key_img = f["small"].render(shortcut, True, DIM)
                window.blit(key_img, (rect.right - pad - key_img.get_width(), rect.centery - key_img.get_height() // 2))
