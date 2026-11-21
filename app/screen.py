"""Where things are in the window: the layout, recomputed when the window changes, and the parts of the window the
HUD draws on."""
from rendering.ui.layout import compute_layout


class Screen:
    def __init__(self, display, scene, hud, menu, overlay):
        self.display, self.scene, self.hud, self.menu, self.overlay = display, scene, hud, menu, overlay
        self.layout = None        # Where the world, the side bar and the curves strip are (rendering/ui/layout.py)
        self.sidebar = None       # The parts of the window the HUD draws on (sub-surfaces, rebuilt with the layout)
        self.strip_view = None
        self._seen = None         # (surface version, size) at the last layout: a change = relayout

    def _current(self):
        window = self.display.surface()
        return self.display.surface_version, window.get_size()

    def stale(self):
        """True when the window changed since the last layout (resize, fullscreen): relayout before drawing."""
        return self._current() != self._seen

    def update(self):
        """Recomputes the layout when the window changed."""
        if not self.stale():
            return
        window = self.display.surface()
        self.layout = layout = compute_layout(*window.get_size())
        self.scene.resize(layout.scale, layout.world.size)
        self.hud.relayout(layout)
        self.menu.relayout(layout)
        self.overlay.relayout(layout)
        self.sidebar = window.subsurface(layout.sidebar)
        self.strip_view = window.subsurface(layout.strip) if layout.strip is not None else None
        self._seen = self._current()
