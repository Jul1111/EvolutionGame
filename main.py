import os
import random
import time
from collections import deque

import pygame

import config
from evolution.continuous import (ContinuousSimulation, success_key, save_population, load_population, snapshot_path,
                                  autosave_path, latest_snapshot, populations_dir)
from utils.timefmt import format_time
from rendering.hud import Hud, SERIES_BY_KEY
from rendering.menu import MenuBar, profile_label
from brain.profiles import PROFILES
from rendering.overlay import Overlay, PARAM_INFO
from utils.presets import PresetBrowser
from rendering.startmenu import StartMenu
from rendering.scene import Scene, pick_creature
from rendering.display import Display
from rendering.layout import compute_layout
from utils.settings import load_settings, save_settings


def main():

    pygame.init()

    rng = random.Random(config.SEED)

    # The window fits the desktop and can be resized or put in fullscreen (key F). The layout (world, side bar,
    # curves strip) is recomputed for the window size and drawn at its real resolution: no bars, no blur.
    display = Display("Evolution Simulator")
    layout = None
    last_generation = None
    last_size = None
    clock = pygame.time.Clock()

    # Rendering: world scene (background, food, creatures) and HUD (panel, curves)
    scene = Scene()
    hud = Hud()
    menu = MenuBar()
    overlay = Overlay(hud, scene)   # Tool bar, legend, help, hover tips, settings panel, large network
    hud.lineage = scene.lineage     # Living lineages in the Population panel
    presets = PresetBrowser()       # Saved settings (saves/presets/), browsed in the settings panel
    overlay.presets = presets
    cam_follow = False              # True: the camera stays on the selected creature
    drag_start = None               # Mouse position of a left press in the world (select on release, pan if dragged)
    dragging = False
    follow = False                  # True: when the selected creature dies, its youngest living descendant is selected
    debug_mode = 0  # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
    paused = False
    selected = None                            # Creature picked with a click
    auto_best = False   # True after B: when the selected creature dies, the new best one is selected
    trail = deque(maxlen=config.TRAIL_LENGTH)  # Recent positions of the selected creature, one per tick

    # Settings editable from the menu: action → (config name, values it cycles through, text shown).
    # All of them are applied at the start of the next generation, so one generation never mixes two settings.
    PARAMS = {
        "mutation": ("MUTATION_STD", [0.02, 0.05, 0.1, 0.2, 0.3], lambda v: f"{v:g}"),
        "repro": ("REPRO_THRESHOLD", [80.0, 100.0, 120.0, 150.0, 180.0], lambda v: f"{v:g}"),
        "age_max": ("AGE_MAX", [0, 3000, 6000, 12000], lambda v: format_time(v) if v else "jamais"),
        "fov": ("VISION_FOV_DEGREES", [60, 90, 120, 180, 270, 360], lambda v: "tout autour" if v >= 360 else f"{v}°"),
        "food": ("FOOD_COUNT", [5, 10, 20, 30, 40, 60], str),
        "food_energy": ("FOOD_ENERGY", [15.0, 30.0, 45.0, 60.0], lambda v: f"{v:g}"),
        "respawn": ("FOOD_RESPAWN_DELAY", [0, 30, 60, 120, 300], lambda v: f"{v} ticks"),
        "poison_count": ("POISON_COUNT", [0, 3, 5, 8, 12, 20, 30], str),
        "poison_energy": ("POISON_ENERGY", [20.0, 40.0, 60.0, 80.0], lambda v: f"{v:g}"),
        "obstacle_count": ("OBSTACLE_COUNT", [0, 3, 6, 10, 15, 25, 35], str),
        "founders": ("INITIAL_POPULATION", [50, 100, 200, 300, 400], str),
        "size_mode": ("SIZE_MODE", ["fixe", "neutre", "actif"], str),
        "world_scale": ("WORLD_SCALE", [1, 2, 3], lambda v: f"{v}×{v} écrans"),
    }
    # Settings chosen in an earlier session replace the values of config.py (saves/settings.json)
    restored = load_settings({name for name, _, _ in PARAMS.values()} | {"ACTIVE_PROFILES"})
    config.refresh_derived()   # WORLD_SCALE may come from settings.json: world size, then the zoom limits
    scene.world_changed()
    if restored:
        print("Réglages du menu repris : " + ", ".join(f"{n} {old} → {new}" for n, (old, new) in restored.items())
              + " (valeurs de config.py ignorées ; LOAD_SETTINGS = False pour les désactiver)")
    # Settings that only take effect on a new world (obstacles are drawn when the world is created).
    # Every other setting applies at once.
    RESTART_PARAMS = {"obstacle_count", "world_scale", "size_mode", "founders"}   # size_mode: bodies are set at birth
    pending_profiles = None   # Species ticked in the menu (list), applied at the next restart from zero

    # Continuous evolution (evolution/continuous.py): births, deaths, no generations. timeline.csv feeds the curves.
    timeline = os.path.join(config.SAVE_DIR, "timeline.csv")
    hud.timeline_path = timeline

    def new_sim(founders=None, start_tick=0, append=False):
        return ContinuousSimulation(rng, timeline, founders=founders, start_tick=start_tick, append=append)

    def archive_timeline():
        """A new population starts a new timeline: the old one is set aside (timestamped), not deleted."""
        if os.path.exists(timeline):
            os.replace(timeline, timeline[:-4] + time.strftime("_ancien_%Y%m%d_%H%M%S.csv"))

    # Setup screen: the simulation does not run until it is launched from the settings panel. Behind it, a preview
    # world (nothing written to timeline.csv). setup = None (running) or {"resume": bool, "cancel": bool}.
    sim = ContinuousSimulation(rng)
    world = sim.world
    # At launch: the start menu (Continuer / Charger / Nouvelle simulation), then the setup screen for a new one
    setup = {"resume": False, "cancel": False, "from_start": True}
    overlay.setup = setup
    overlay.start = StartMenu(autosave_path() if config.LOAD_ON_START else None, populations_dir())
    hud.reload_stats(sorted({c.profile for c in world.creatures}, key=list(PROFILES).index))
    last_saved = latest_snapshot()

    def restart(founders=None):
        """New population: random founders of the ticked species, or a saved population (founders)."""
        nonlocal sim, world, selected, paused
        old_scale = config.WORLD_SCALE
        apply_pending()
        config.refresh_derived()
        if config.WORLD_SCALE != old_scale:
            scene.world_changed()
        archive_timeline()
        sim = new_sim(founders)
        world = sim.world
        selected = None
        paused = False
        trail.clear()
        hud.reload_stats(list(founders) if founders else config.ACTIVE_PROFILES)

    def open_setup(can_cancel):
        """Settings screen before a new simulation: everything set there applies when it is launched."""
        nonlocal setup, paused
        setup = {"resume": False, "cancel": can_cancel}
        overlay.setup = setup
        overlay.params_open = True
        paused = True

    def close_setup():
        nonlocal setup
        setup = None
        overlay.setup = None
        overlay.params_open = False

    def resume_autosave():
        """Start from the population kept when the game was last closed, with its timeline."""
        nonlocal sim, world, selected, paused
        founders, tick = load_population(autosave_path(), with_tick=True)
        if not founders:
            return False
        apply_pending()
        config.refresh_derived()
        scene.world_changed()
        sim = new_sim(founders, start_tick=tick, append=True)
        world = sim.world
        selected, paused = None, False
        trail.clear()
        hud.reload_stats(list(founders))
        overlay.toast(f"Population reprise : {len(world.creatures)} créatures, temps {format_time(tick)}")
        return True

    def apply_param(key, value):
        """Setting changed in the menu: now, or at the next restart for RESTART_PARAMS (or for every setting while
        the setup screen is open: nothing runs yet)."""
        name = PARAMS[key][0]
        if key in RESTART_PARAMS or setup is not None:
            if value == getattr(config, name):
                pending.pop(key, None)
            else:
                pending[key] = value
        else:
            setattr(config, name, value)
            world.resize_items()   # Food and poison counts or energies take effect in the running world
        persist_settings()

    pending = {}   # action → value waiting for the next restart (RESTART_PARAMS only)

    def persist_settings():
        """Keeps the settings chosen in the menu (pending ones included) for the next launch."""
        values = {name: pending.get(action, getattr(config, name)) for action, (name, _, _) in PARAMS.items()}
        values["ACTIVE_PROFILES"] = list(config.ACTIVE_PROFILES if pending_profiles is None else pending_profiles)
        save_settings(values)

    def apply_pending():
        nonlocal pending_profiles
        for action, value in pending.items():
            setattr(config, PARAMS[action][0], value)
        pending.clear()
        if pending_profiles is not None:
            config.ACTIVE_PROFILES = list(pending_profiles)
            pending_profiles = None

    def next_step(steps, current):
        """Next value of the list after `current` (the first greater one if it is not in the list), wrapping around."""
        if isinstance(current, bool):
            return not current
        if isinstance(current, str):   # Names (e.g. fitness): next in the list order
            return steps[(steps.index(current) + 1) % len(steps)] if current in steps else steps[0]
        return next((v for v in steps if v > current + 1e-9), steps[0])

    def prev_step(steps, current):
        """Previous value of the list before `current`, wrapping around."""
        if isinstance(current, bool):
            return not current
        if isinstance(current, str):   # Names (e.g. fitness): next in the list order
            return steps[(steps.index(current) + -1) % len(steps)] if current in steps else steps[0]
        return next((v for v in reversed(steps) if v < current - 1e-9), steps[-1])

    # Every command, from the keyboard or from the menu, goes through do(). Returns True to keep the menu open.
    def do(action):
        nonlocal speed_index, debug_mode, paused, step_request, reset_pending, selected, follow, pending_profiles, \
            cam_follow, last_saved, running, auto_best
        if setup is not None and action in ("pause", "step", "params_panel", "params_close", "end_gen", "restart_now",
                                            "save_pop", "load_pop", "reset"):
            return False   # Setup screen: only its own buttons, the settings, the species and the view
        if action == "speed_up":
            speed_index = min(speed_index + 1, len(config.SPEED_STEPS) - 1)
        elif action == "speed_down":
            speed_index = max(speed_index - 1, 0)
        elif action == "debug":
            debug_mode = (debug_mode + 1) % 3
        elif action == "color":
            scene.cycle_color_mode()
        elif action == "pause":
            paused = not paused
        elif action == "step":
            step_request = paused
        elif action == "chart":
            # Curves: hidden → side panel → large view over the world → hidden
            if overlay.chart_big:
                overlay.chart_big = False
            elif hud.show_chart:
                hud.toggle_chart()
                overlay.chart_big = True
            else:
                hud.toggle_chart()
        elif action == "panels":
            hud.visible = not hud.visible
        elif action == "minimap":
            overlay.minimap.enabled = not overlay.minimap.enabled
        elif action == "effects":
            scene.effects.enabled = not scene.effects.enabled
        elif action == "cam_follow_off":
            cam_follow = False   # The mini-map moved the view by hand
        elif action in ("preset_prev", "preset_next"):
            presets.refresh()
            presets.move(-1 if action == "preset_prev" else 1)
            return True
        elif action == "preset_save":
            values = {name: pending.get(a, getattr(config, name)) for a, (name, _, _) in PARAMS.items()}
            values["ACTIVE_PROFILES"] = list(config.ACTIVE_PROFILES if pending_profiles is None else pending_profiles)
            overlay.toast(f"Préréglage enregistré : saves/presets/{presets.save(values)}")
            return True
        elif action == "preset_apply":
            values = presets.load()
            if values:
                for a, (name, _, _) in PARAMS.items():
                    if name in values:
                        apply_param(a, values[name])
                if values.get("ACTIVE_PROFILES"):
                    wanted = [p for p in PROFILES if p in values["ACTIVE_PROFILES"]]
                    pending_profiles = None if wanted == config.ACTIVE_PROFILES else wanted
                    persist_settings()
                overlay.toast("Préréglage appliqué")
            return True
        elif action == "graph":
            # Network view: hidden → small (side bar) → large (over the world) → hidden
            if overlay.net_big:
                overlay.net_big = False
            elif hud.show_graph:
                hud.toggle_graph()
                overlay.net_big = True
            else:
                hud.toggle_graph()
        elif action == "legend":
            overlay.legend_open = not overlay.legend_open
        elif action == "help":
            overlay.help_open = not overlay.help_open
        elif action == "params_panel":
            overlay.params_open = not overlay.params_open
        elif action == "params_close":
            overlay.params_open = False
        elif action == "params_cancel":
            pending.clear()
            persist_settings()
        elif action.startswith("profile:"):
            # Tick or untick a species. At least one must stay. Back to the active list = nothing pending.
            name = action[len("profile:"):]
            current = list(config.ACTIVE_PROFILES if pending_profiles is None else pending_profiles)
            if name in current:
                if len(current) > 1:
                    current.remove(name)
            else:
                current.append(name)
            current = [p for p in PROFILES if p in current]
            pending_profiles = None if current == config.ACTIVE_PROFILES else current
            persist_settings()
            return True
        elif action in ("zoom_in", "zoom_out"):
            vw, vh = scene.size
            scene.zoom_by(1.25 if action == "zoom_in" else 0.8, (vw / 2, vh / 2))
        elif action == "view_fit":
            scene.view_all()
        elif action == "view_screen":
            scene.view_screen()
        elif action == "cam_follow":
            cam_follow = not cam_follow
        elif action.startswith("param:"):
            # Arrows of the settings panel: previous / next preset. Back to the value in force = nothing pending.
            _, direction, key = action.split(":")
            name, steps, _ = PARAMS[key]
            current = pending.get(key, getattr(config, name))
            apply_param(key, prev_step(steps, current) if direction == "dec" else next_step(steps, current))
            return True
        elif action == "best":
            if world.creatures:
                selected = max(world.creatures, key=success_key)
                trail.clear()
                cam_follow = True
                auto_best = True   # Stays on «the best»: at its death, the new best one
        elif action == "follow":
            follow = not follow
            if follow and selected is None and world.creatures:
                selected = max(world.creatures, key=success_key)
                trail.clear()
                cam_follow = True
        elif action == "fullscreen":
            display.toggle_fullscreen()
        elif action == "restart_now":
            restart()
            overlay.toast("Nouvelle population tirée au hasard")
        elif action == "save_pop":
            if world.creatures:
                last_saved = snapshot_path("manuelle")
                save_population(sim, last_saved)
                overlay.toast(f"Population sauvegardée : saves/populations/{os.path.basename(last_saved)}")
        elif action == "load_pop":
            if last_saved and os.path.exists(last_saved):
                founders = load_population(last_saved)
                if founders:
                    restart(founders)
                    overlay.toast(f"Population chargée : {os.path.basename(last_saved)}")
            else:
                overlay.toast("Aucune population sauvegardée (S pour sauvegarder)")
        elif action.startswith("series:"):
            hud.toggle_series(action[len("series:"):])
            return True   # Menu stays open to pick several curves
        elif action == "series_default":
            hud.reset_series()
            return True
        elif action in PARAMS:
            # Menu click: next preset value (now, or at the next restart). The menu stays open to click again.
            name, steps, _ = PARAMS[action]
            apply_param(action, next_step(steps, pending.get(action, getattr(config, name))))
            return True
        elif action == "start_continue":
            if resume_autosave():
                overlay.start = None
                close_setup()
        elif action == "start_load_list":
            overlay.start.view = "load"
        elif action == "start_back":
            overlay.params_open = False   # Back from the settings of a new simulation, or from the load list
            if overlay.start is None:
                overlay.start = StartMenu(autosave_path() if config.LOAD_ON_START else None, populations_dir())
            overlay.start.view = "main"
        elif action == "start_new":
            overlay.start = None
            overlay.params_open = True
        elif action.startswith("start_load:"):
            path = action[len("start_load:"):]
            founders = load_population(path)
            if founders:
                restart(founders)
                last_saved = path
                overlay.start = None
                close_setup()
                paused = False
                overlay.toast(f"Population chargée : {os.path.basename(path)}")
        elif action == "quit":
            running = False
        elif action == "reset":
            open_setup(can_cancel=True)
        elif action == "setup_launch":
            restart()
            close_setup()
        elif action == "setup_resume":
            if resume_autosave():
                close_setup()
        elif action == "setup_cancel":
            pending.clear()
            pending_profiles = None
            persist_settings()
            close_setup()
            paused = False
        return False

    KEYS = {pygame.K_UP: "speed_up", pygame.K_DOWN: "speed_down", pygame.K_d: "debug", pygame.K_c: "color",
            pygame.K_SPACE: "pause", pygame.K_RIGHT: "step", pygame.K_g: "chart", pygame.K_n: "graph",
            pygame.K_f: "fullscreen", pygame.K_F11: "fullscreen", pygame.K_l: "legend", pygame.K_h: "help",
            pygame.K_p: "params_panel", pygame.K_b: "best", pygame.K_t: "follow", pygame.K_s: "save_pop",
            pygame.K_EQUALS: "zoom_in", pygame.K_PLUS: "zoom_in", pygame.K_KP_PLUS: "zoom_in",
            pygame.K_MINUS: "zoom_out", pygame.K_KP_MINUS: "zoom_out", pygame.K_0: "view_fit",
            pygame.K_KP0: "view_fit", pygame.K_1: "view_screen", pygame.K_KP1: "view_screen", pygame.K_v: "cam_follow",
            pygame.K_TAB: "panels", pygame.K_m: "minimap", pygame.K_e: "effects"}
    reset_pending = False

    speed_index = 0

    running = True
    while running:
        window = display.surface()
        if display.generation != last_generation or window.get_size() != last_size:
            layout = compute_layout(*window.get_size())
            scene.resize(layout.scale, layout.world.size)
            hud.relayout(layout)
            menu.relayout(layout)
            overlay.relayout(layout)
            world_view = window.subsurface(layout.world)
            sidebar = window.subsurface(layout.sidebar)
            strip_view = window.subsurface(layout.strip) if layout.strip is not None else None
            last_generation, last_size = display.generation, window.get_size()
        step_request = False
        for event in pygame.event.get():
            # Handle quitting the game
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if menu.open_index is not None:
                    menu.close()               # First Escape closes the open menu
                elif setup is not None and overlay.help_open:
                    overlay.help_open = False
                elif setup is not None:
                    if setup["cancel"]:
                        do("setup_cancel")     # Setup opened from «Nouvelle simulation»: back to the running one
                    elif overlay.start is not None and overlay.start.view == "load":
                        do("start_back")             # Load list: back to the start menu
                    elif overlay.start is None and setup.get("from_start"):
                        do("start_back")             # Settings of a new simulation: back to the start menu
                    else:
                        running = False        # Start menu: Escape quits
                elif overlay.any_modal():
                    overlay.close_modals()     # Then the help or the settings panel
                elif display.fullscreen:
                    display.toggle_fullscreen()  # Then leaves fullscreen
                else:
                    running = False
            elif event.type == pygame.KEYDOWN:
                if overlay.start is not None and not overlay.params_open and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    do(overlay.start.default_action())   # Start menu: Enter = Continuer (or Nouvelle simulation)
                elif event.key in KEYS:
                    do(KEYS[event.key])
                elif event.unicode == "?":
                    do("help")
            elif event.type == pygame.MOUSEMOTION:
                menu.hover(*display.to_pixels(event.pos))
                overlay.hover(*display.to_pixels(event.pos))
                if drag_start is not None and event.buttons[0]:
                    mx, my = display.to_pixels(event.pos)
                    if dragging or abs(mx - drag_start[0]) + abs(my - drag_start[1]) > 6:
                        dragging = True   # Dragging the world moves the view
                        cam_follow = False  # Moving the view by hand stops following (V or a new selection: again)
                        ratio = display.pixel_ratio()
                        scene.pan_pixels(event.rel[0] * ratio, event.rel[1] * ratio)
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = display.to_pixels(pygame.mouse.get_pos())
                if layout.world.collidepoint(mx, my) and menu.open_index is None and not overlay.blocks(mx, my):
                    scene.zoom_by(1.15 ** event.y, (mx - layout.world.x, my - layout.world.y))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag_start is not None and not dragging:
                    # A click without drag: select the creature under the pointer
                    wx, wy = scene.screen_to_world(drag_start[0] - layout.world.x, drag_start[1] - layout.world.y)
                    selected = pick_creature(world, wx, wy, scene.pick_radius())
                    auto_best = False   # A creature chosen by hand: no automatic switch (except T, lineage)
                    trail.clear()
                    cam_follow = selected is not None   # The camera follows the creature just selected
                drag_start, dragging = None, False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = display.to_pixels(event.pos)  # Window points → surface pixels (2x on Retina)
                consumed, action = menu.click(mx, my)
                if action is not None and not do(action):
                    menu.close()
                if not consumed:
                    consumed, action = overlay.click(mx, my)   # Tool bar, legend, large network, modal panels
                    if action is not None:
                        do(action)
                if not consumed and layout.world.collidepoint(mx, my):  # Click in the world (not in the panels)
                    drag_start, dragging = (mx, my), False   # Selection happens on release, unless it was a drag

        if display.generation != last_generation or display.surface().get_size() != last_size:
            continue  # The window changed during the events (fullscreen): relayout before drawing

        speed = config.SPEED_STEPS[speed_index]

        # Run several simulation ticks per frame, according to the chosen speed
        ticks_to_run = 0 if setup is not None else (1 if step_request else (0 if paused else speed))
        for _ in range(ticks_to_run):
            going = sim.step()
            if selected is not None:
                if selected.alive:
                    trail.append((selected.x, selected.y))
                elif follow or auto_best:
                    # T: the lineage goes on through its youngest living descendant; if the lineage is extinct,
                    # or after B: the new best one (most children)
                    heir = sim.descendant_of(selected) if follow else None
                    if heir is None and world.creatures:
                        heir = max((c for c in world.creatures if c.alive), key=success_key, default=None)
                        if heir is not None:
                            overlay.toast(f"Morte. Nouvelle meilleure : {heir.children} petits, génération {heir.lineage_gen}", 2.5)
                    if heir is not None:
                        selected = heir
                        trail.clear()
            if not going:
                paused = True
                hud.reload_stats()
                overlay.toast(f"Extinction à {format_time(world.tick)}. Sauvegarde → Repartir de zéro, ou charger une population.", 8)
                break
            if sim.new_sample:
                hud.reload_stats()

        if cam_follow and selected is not None and selected.alive:
            scene.center_on(selected.x, selected.y)

        # Draw the world, then the heads-up display (HUD)
        scene.draw(world_view, world, debug_mode, selected, trail)
        hud.draw(sidebar, strip_view, world, clock.get_fps(), speed,
                 {"births": sim.total_births, "deaths": sim.total_deaths, "extinct": sim.extinct, "pop_max": sim.pop_max,
                  "setup": setup is not None},
                 debug_mode, paused, selected, scene.color_label())
        net_state = 2 if overlay.net_big else (1 if hud.show_graph else 0)
        chart_state = 2 if overlay.chart_big else (1 if hud.show_chart else 0)
        params_info = [(a, *PARAM_INFO.get(a, (a, "")), fmt(getattr(config, name)),
                        fmt(pending[a]) if a in pending else None)
                       for a, (name, _, fmt) in PARAMS.items()] if overlay.params_open else []
        overlay.draw(window, {"paused": paused, "speed": speed, "debug": debug_mode, "follow": follow,
                              "graph": net_state, "chart": chart_state, "cam_follow": cam_follow,
                              "profiles": list(config.ACTIVE_PROFILES if pending_profiles is None else pending_profiles),
                              "profiles_pending": pending_profiles is not None}, world, selected, params_info)
        if menu.open_index is None:
            reset_pending = False
        menu.draw(window, {
            "speed": speed, "paused": paused, "debug": ("off", "sélection", "toutes")[debug_mode],
            "color": scene.color_label(), "chart": ("non", "panneau", "grand")[chart_state], "graph": ("non", "petit", "grand")[net_state],
            "legend": overlay.legend_open, "follow": follow,
            "fullscreen": display.fullscreen,
            **{"s_" + key: key in hud.chart_keys for key in SERIES_BY_KEY},
            **{a: fmt(pending.get(a, getattr(config, name))) + ("  *" if a in pending else "")
               for a, (name, _, fmt) in PARAMS.items()},
            "cam_follow": cam_follow, "minimap": overlay.minimap.enabled, "effects": scene.effects.enabled,
            "panels": hud.visible,
            "load_pop": (f"Charger : {os.path.basename(last_saved)}" if last_saved else "Charger une population (aucune)"),
            **{"p_" + n: n in (config.ACTIVE_PROFILES if pending_profiles is None else pending_profiles) for n in PROFILES},
            **{"pl_" + n: profile_label(n) + ("  *" if pending_profiles is not None
                                              and (n in pending_profiles) != (n in config.ACTIVE_PROFILES) else "")
               for n in PROFILES},
            "reset": "Nouvelle simulation...",
        })
        overlay.draw_tips(window, world, selected, menu.open_index is not None)

        display.flip()
        clock.tick(config.FPS)

    # The population is kept for the next launch (LOAD_ON_START). After an extinction there is nothing to keep.
    # Quitting from the setup screen at launch keeps the saved one untouched (the preview world is not a run).
    if setup is not None and not setup["cancel"]:
        pass
    elif sim.extinct or not world.creatures:
        if os.path.exists(autosave_path()):
            os.remove(autosave_path())
    else:
        save_population(sim, autosave_path())
    pygame.quit()


if __name__ == "__main__":
    main()    