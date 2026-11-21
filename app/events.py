"""Events: keyboard and mouse."""
import pygame

from rendering.world.scene import pick_creature
from app.commands import KEYS


class Events:
    def __init__(self, display, screen, menu, overlay, scene, state, selection, session, commands):
        self.display, self.screen, self.menu, self.overlay, self.scene = display, screen, menu, overlay, scene
        self.state, self.selection, self.session, self.commands = state, selection, session, commands

    def _on_escape(self):
        menu, overlay, setup, do = self.menu, self.overlay, self.state.setup, self.commands.do
        if menu.open_index is not None:
            menu.close()               # First Escape closes the open menu
        elif setup is not None and overlay.help_open:
            overlay.help_open = False
        elif setup is not None:
            if setup["cancel"]:
                do("setup_cancel")          # Setup opened from «Nouvelle simulation»: back to the running one
            elif overlay.start is not None and overlay.start.view == "load":
                do("start_back")            # Load list: back to the start menu
            elif overlay.start is None and setup.get("from_start"):
                do("start_back")            # Settings of a new simulation: back to the start menu
            else:
                self.state.running = False  # Start menu: Escape quits
        elif overlay.any_modal():
            overlay.close_modals()          # Then the help or the settings panel
        elif self.display.fullscreen:
            self.display.toggle_fullscreen()   # Then leaves fullscreen
        else:
            self.state.running = False

    def _on_key(self, event):
        do = self.commands.do
        if event.key == pygame.K_ESCAPE:
            self._on_escape()
        elif self.overlay.start is not None and not self.overlay.params_open \
                and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            do(self.overlay.start.default_action())   # Start menu: Enter = Continuer (or Nouvelle simulation)
        elif event.key in KEYS:
            do(KEYS[event.key])
        elif event.unicode == "?":
            do("help")

    def _on_mouse_motion(self, event):
        display, selection = self.display, self.selection
        self.menu.hover(*display.to_pixels(event.pos))
        self.overlay.hover(*display.to_pixels(event.pos))
        if selection.drag_start is not None and event.buttons[0]:
            mx, my = display.to_pixels(event.pos)
            if selection.dragging or abs(mx - selection.drag_start[0]) + abs(my - selection.drag_start[1]) > 6:
                selection.dragging = True      # Dragging the world moves the view
                selection.cam_follow = False   # Moving the view by hand stops following (V or a new selection: again)
                ratio = display.pixel_ratio()
                self.scene.pan_pixels(event.rel[0] * ratio, event.rel[1] * ratio)

    def _on_mouse_wheel(self, event):
        mx, my = self.display.to_pixels(pygame.mouse.get_pos())
        world_rect = self.screen.layout.world
        if world_rect.collidepoint(mx, my) and self.menu.open_index is None and not self.overlay.blocks(mx, my):
            self.scene.zoom_by(1.15 ** event.y, (mx - world_rect.x, my - world_rect.y))

    def _on_mouse_down(self, event):
        mx, my = self.display.to_pixels(event.pos)   # Window points → surface pixels (2x on Retina)
        consumed, action = self.menu.click(mx, my)
        if action is not None and not self.commands.do(action):
            self.menu.close()
        if not consumed:
            consumed, action = self.overlay.click(mx, my)   # Tool bar, legend, large network, modal panels
            if action is not None:
                self.commands.do(action)
        if not consumed and self.screen.layout.world.collidepoint(mx, my):   # Click in the world (not in the panels)
            # Selection happens on release, unless it was a drag
            self.selection.drag_start, self.selection.dragging = (mx, my), False

    def _on_mouse_up(self, event):
        selection = self.selection
        if selection.drag_start is not None and not selection.dragging:
            # A click without drag: select the creature under the pointer
            world_rect, scene = self.screen.layout.world, self.scene
            sx, sy = selection.drag_start[0] - world_rect.x, selection.drag_start[1] - world_rect.y
            wx, wy = scene.screen_to_world(sx, sy)
            selection.pick(pick_creature(self.session.world, wx, wy, scene.pick_radius()))
        selection.drag_start, selection.dragging = None, False

    def handle(self):
        self.state.step_request = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state.running = False
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
