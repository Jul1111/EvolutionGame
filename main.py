import pygame
import config
import random
from collections import deque

from core.world import World
from evolution.population import brains_from_genomes, select_parents
from rendering.hud import Hud, format_time, SERIES_BY_KEY
from rendering.menu import MenuBar
from rendering.scene import Scene, pick_creature
from rendering.display import Display
from rendering.layout import compute_layout
from utils.persistence import save_genomes, load_genomes, archive_genomes
from utils.logger import log_generation, archive_stats


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
    debug_mode = 0  # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
    paused = False
    selected = None                            # Creature picked with a click (cleared at each new generation)
    trail = deque(maxlen=config.TRAIL_LENGTH)  # Recent positions of the selected creature, one per tick

    world = World(rng)
    loaded = load_genomes() if config.LOAD_ON_START else None
    if loaded is not None:
        # Resume: saved parents + mutated children
        genomes, saved_generation = loaded
        for brain in brains_from_genomes(genomes, rng):
            world.add_creature(brain)
        generation = saved_generation + 1
    else:
        archive_stats()
        world.add_population(config.POPULATION_SIZE)
        generation = 1

    def end_generation():
        """End of the generation: parents + mutated children form the next one."""
        nonlocal world, generation, selected
        parents = select_parents(world.creatures, config.PARENTS_COUNT)
        mean_food = sum(c.food_eaten for c in parents) / len(parents)
        alive_count = sum(1 for c in world.creatures if c.alive)
        max_food = max(c.food_eaten for c in parents)
        mean_speed = sum(c.speed for c in parents) / len(parents)
        mean_energy = sum(c.energy for c in parents) / len(parents)
        # Exploration metrics, computed on the parents
        blind_ticks = sum(c.blind_ticks for c in parents)
        total_age = sum(c.age for c in parents)
        blind_frac = blind_ticks / total_age if total_age else 0.0
        blind_speed = sum(c.blind_speed_sum for c in parents) / blind_ticks if blind_ticks else None
        blind_turn = sum(c.blind_turn_sum for c in parents) / blind_ticks if blind_ticks else None
        total_food = sum(c.food_eaten for c in world.creatures)
        mean_poison = sum(c.poison_hits for c in parents) / len(parents)
        total_poison = sum(c.poison_hits for c in world.creatures)
        print(f"Gen {generation:>4} | fin {format_time(world.tick)} | "
              f"vivantes {alive_count}/{len(world.creatures)} | "
              f"meilleur âge {format_time(parents[0].age)} | "
              f"nourriture parents moy {mean_food:.1f} max {max_food} | "
              f"vitesse moy parents {mean_speed:.2f} | "
              f"mangé total {total_food} | aveugles {blind_frac:.0%} | "
              f"énergie moy parents {mean_energy:.0f} | "
              f"poison parents moy {mean_poison:.1f} total {total_poison}")
        log_generation({
            "generation": generation, "ticks": world.tick, "alive": alive_count,
            "best_age": parents[0].age, "mean_food": mean_food, "max_food": max_food,
            "mean_speed": mean_speed, "food_count": len(world.foods),
            "total_food": total_food, "blind_frac": blind_frac,
            "blind_speed": blind_speed, "blind_turn": blind_turn,
            "mean_energy": mean_energy,
            "mean_poison": mean_poison, "total_poison": total_poison,
        })  # The settings of config.py are added by log_generation, before apply_pending() changes them
        hud.reload_stats()
        genomes = [p.brain.get_genome() for p in parents]
        save_genomes(genomes, generation)
        apply_pending()
        brains = brains_from_genomes(genomes, rng)
        world = World(rng)
        for brain in brains:
            world.add_creature(brain)
        generation += 1
        selected = None  # The creatures of the old world no longer exist
        trail.clear()

    def reset_all():
        """Start again from zero: the save and the CSV are set aside (timestamped), not deleted."""
        nonlocal world, generation, selected
        archive_stats()
        archive_genomes()
        apply_pending()
        world = World(rng)
        world.add_population(config.POPULATION_SIZE)
        generation = 1
        selected = None
        trail.clear()
        hud.reload_stats()

    # Settings editable from the menu: action → (config name, values it cycles through, text shown).
    # All of them are applied at the start of the next generation, so one generation never mixes two settings.
    PARAMS = {
        "mutation": ("MUTATION_STD", [0.02, 0.05, 0.1, 0.2, 0.3], lambda v: f"{v:g}"),
        "parents": ("PARENTS_COUNT", [10, 20, 30, 50], str),
        "fov": ("VISION_FOV_DEGREES", [60, 90, 120, 180, 270, 360], lambda v: "tout autour" if v >= 360 else f"{v}°"),
        "food": ("FOOD_COUNT", [5, 10, 15, 20, 30], str),
        "food_energy": ("FOOD_ENERGY", [15.0, 30.0, 45.0, 60.0], lambda v: f"{v:g}"),
        "respawn": ("FOOD_RESPAWN_DELAY", [0, 30, 60, 120, 300], lambda v: f"{v} ticks"),
        "max_eats": ("FOOD_MAX_EATS", [1, 2, 3, 5, 10], str),
        "fixed": ("FOOD_FIXED_POSITIONS", [False, True], lambda v: "fixes" if v else "aléatoires"),
        "poison_count": ("POISON_COUNT", [0, 3, 5, 8, 12], str),
        "poison_energy": ("POISON_ENERGY", [20.0, 40.0, 60.0, 80.0], lambda v: f"{v:g}"),
    }
    pending = {}   # action → value waiting for the next generation

    def apply_pending():
        for action, value in pending.items():
            setattr(config, PARAMS[action][0], value)
        pending.clear()

    def next_step(steps, current):
        """Next value of the list after `current` (the first greater one if it is not in the list), wrapping around."""
        if isinstance(current, bool):
            return not current
        return next((v for v in steps if v > current + 1e-9), steps[0])

    # Every command, from the keyboard or from the menu, goes through do(). Returns True to keep the menu open.
    def do(action):
        nonlocal speed_index, debug_mode, paused, step_request, reset_pending
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
            hud.toggle_chart()
        elif action == "graph":
            hud.toggle_graph()
        elif action == "fullscreen":
            display.toggle_fullscreen()
        elif action == "end_gen":
            end_generation()
        elif action.startswith("series:"):
            hud.toggle_series(action[len("series:"):])
            return True   # Menu stays open to pick several curves
        elif action == "series_default":
            hud.reset_series()
            return True
        elif action in PARAMS:
            # The value is only noted here (pending) and written to config when the next generation is built.
            # The menu stays open to click again.
            name, steps, _ = PARAMS[action]
            pending[action] = next_step(steps, pending.get(action, getattr(config, name)))
            return True
        elif action == "reset":
            if not reset_pending:
                reset_pending = True   # First click asks for confirmation, the menu stays open
                return True
            reset_pending = False
            reset_all()
        return False

    KEYS = {pygame.K_UP: "speed_up", pygame.K_DOWN: "speed_down", pygame.K_d: "debug", pygame.K_c: "color",
            pygame.K_SPACE: "pause", pygame.K_RIGHT: "step", pygame.K_g: "chart", pygame.K_n: "graph",
            pygame.K_f: "fullscreen", pygame.K_F11: "fullscreen"}
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
                elif display.fullscreen:
                    display.toggle_fullscreen()  # Then leaves fullscreen
                else:
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in KEYS:
                    do(KEYS[event.key])
            elif event.type == pygame.MOUSEMOTION:
                menu.hover(*display.to_pixels(event.pos))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = display.to_pixels(event.pos)  # Window points → surface pixels (2x on Retina)
                consumed, action = menu.click(mx, my)
                if action is not None and not do(action):
                    menu.close()
                if not consumed and layout.world.collidepoint(mx, my):  # Click in the world (not in the panels)
                    wx = (mx - layout.world.x) / layout.scale  # Pixels → world units
                    wy = (my - layout.world.y) / layout.scale
                    selected = pick_creature(world, wx, wy)
                    trail.clear()

        if display.generation != last_generation or display.surface().get_size() != last_size:
            continue  # The window changed during the events (fullscreen): relayout before drawing

        speed = config.SPEED_STEPS[speed_index]

        # Run several simulation ticks per frame, according to the chosen speed
        ticks_to_run = 1 if step_request else (0 if paused else speed)
        for _ in range(ticks_to_run):
            world.update()
            if selected is not None and selected.alive:
                trail.append((selected.x, selected.y))
            if world.is_over():
                end_generation()
                break

        # Draw the world, then the heads-up display (HUD)
        scene.draw(world_view, world, debug_mode, selected, trail)
        hud.draw(sidebar, strip_view, world, clock.get_fps(), speed, generation, debug_mode, paused, selected,
                 scene.color_label())
        if menu.open_index is None:
            reset_pending = False
        menu.draw(window, {
            "speed": speed, "paused": paused, "debug": ("off", "sélection", "toutes")[debug_mode],
            "color": scene.color_label(), "chart": hud.show_chart, "graph": hud.show_graph,
            "fullscreen": display.fullscreen,
            **{"s_" + key: key in hud.chart_keys for key in SERIES_BY_KEY},
            **{a: fmt(pending.get(a, getattr(config, name))) + ("  *" if a in pending else "")
               for a, (name, _, fmt) in PARAMS.items()},
            "reset": "Confirmer : tout effacer ?" if reset_pending else "Repartir de zéro",
        })

        display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    