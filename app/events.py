"""Events: window layout, keyboard and mouse."""
import pygame

from rendering.ui.layout import compute_layout
from rendering.world.scene import pick_creature
from app.commands import KEYS


class EventsMixin:
    def _update_layout(self):
        """Recomputes the layout when the window changed. Returns True when it did not change (drawing can go on)."""
        window = self.display.surface()
        if self.display.surface_version != self.last_surface_version or window.get_size() != self.last_size:
            self.layout = layout = compute_layout(*window.get_size())
            self.scene.resize(layout.scale, layout.world.size)
            self.hud.relayout(layout)
            self.menu.relayout(layout)
            self.overlay.relayout(layout)
            self.sidebar = window.subsurface(layout.sidebar)
            self.strip_view = window.subsurface(layout.strip) if layout.strip is not None else None
            self.last_surface_version, self.last_size = self.display.surface_version, window.get_size()
            return False
        return True

    def _on_escape(self):
        menu, overlay, setup = self.menu, self.overlay, self.setup
        if menu.open_index is not None:
            menu.close()               # First Escape closes the open menu
        elif setup is not None and overlay.help_open:
            overlay.help_open = False
        elif setup is not None:
            if setup["cancel"]:
                self.do("setup_cancel")     # Setup opened from «Nouvelle simulation»: back to the running one
            elif overlay.start is not None and overlay.start.view == "load":
                self.do("start_back")       # Load list: back to the start menu
            elif overlay.start is None and setup.get("from_start"):
                self.do("start_back")       # Settings of a new simulation: back to the start menu
            else:
                self.running = False        # Start menu: Escape quits
        elif overlay.any_modal():
            overlay.close_modals()          # Then the help or the settings panel
        elif self.display.fullscreen:
            self.display.toggle_fullscreen()   # Then leaves fullscreen
        else:
            self.running = False

    def _on_key(self, event):
        if event.key == pygame.K_ESCAPE:
            self._on_escape()
        elif self.overlay.start is not None and not self.overlay.params_open \
                and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.do(self.overlay.start.default_action())   # Start menu: Enter = Continuer (or Nouvelle simulation)
        elif event.key in KEYS:
            self.do(KEYS[event.key])
        elif event.unicode == "?":
            self.do("help")

    def _on_mouse_motion(self, event):
        display = self.display
        self.menu.hover(*display.to_pixels(event.pos))
        self.overlay.hover(*display.to_pixels(event.pos))
        if self.drag_start is not None and event.buttons[0]:
            mx, my = display.to_pixels(event.pos)
            if self.dragging or abs(mx - self.drag_start[0]) + abs(my - self.drag_start[1]) > 6:
                self.dragging = True      # Dragging the world moves the view
                self.cam_follow = False   # Moving the view by hand stops following (V or a new selection: again)
                ratio = display.pixel_ratio()
                self.scene.pan_pixels(event.rel[0] * ratio, event.rel[1] * ratio)

    def _on_mouse_wheel(self, event):
        mx, my = self.display.to_pixels(pygame.mouse.get_pos())
        if self.layout.world.collidepoint(mx, my) and self.menu.open_index is None \
                and not self.overlay.blocks(mx, my):
            self.scene.zoom_by(1.15 ** event.y, (mx - self.layout.world.x, my - self.layout.world.y))

    def _on_mouse_down(self, event):
        mx, my = self.display.to_pixels(event.pos)   # Window points → surface pixels (2x on Retina)
        consumed, action = self.menu.click(mx, my)
        if action is not None and not self.do(action):
            self.menu.close()
        if not consumed:
            consumed, action = self.overlay.click(mx, my)   # Tool bar, legend, large network, modal panels
            if action is not None:
                self.do(action)
        if not consumed and self.layout.world.collidepoint(mx, my):   # Click in the world (not in the panels)
            self.drag_start, self.dragging = (mx, my), False   # Selection happens on release, unless it was a drag

    def _on_mouse_up(self, event):
        if self.drag_start is not None and not self.dragging:
            # A click without drag: select the creature under the pointer
            layout, scene = self.layout, self.scene
            wx, wy = scene.screen_to_world(self.drag_start[0] - layout.world.x, self.drag_start[1] - layout.world.y)
            self.selected = pick_creature(self.world, wx, wy, scene.pick_radius())
            self.auto_best = False   # A creature chosen by hand: no automatic switch (except T, lineage)
            self.trail.clear()
            self.cam_follow = self.selected is not None   # The camera follows the creature just selected
        self.drag_start, self.dragging = None, False

    def _handle_events(self):
        self.step_request = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._on_mouse_wheel(event)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._on_mouse_up(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_mouse_down(event)
