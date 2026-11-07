import pygame
import config
import random
import time
from collections import deque

from core.world import World
from evolution.population import brains_from_genomes, select_parents
from rendering.hud import Hud, format_time
from rendering.scene import Scene, pick_creature
from rendering.display import Display
from rendering.layout import compute_layout
from utils.persistence import save_genomes, load_genomes
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
        print(f"Reprise depuis la sauvegarde : génération {generation}")
    else:
        archive_stats()
        world.add_population(config.POPULATION_SIZE)
        generation = 1

    speed_index = 0
    last_speed = config.SPEED_STEPS[speed_index]

    # Performance measurement, averaged over one second of real time
    update_time = 0.0
    draw_time = 0.0
    flip_time = 0.0
    frames = 0
    window_start = time.perf_counter()

    running = True
    while running:
        window = display.surface()
        if display.generation != last_generation or window.get_size() != last_size:
            layout = compute_layout(*window.get_size())
            scene.resize(layout.scale, layout.world.size)
            hud.relayout(layout)
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
                if display.fullscreen:
                    display.toggle_fullscreen()  # First Escape leaves fullscreen
                else:
                    running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    # Increase simulation speed
                    if speed_index < len(config.SPEED_STEPS) - 1:
                        speed_index += 1
                elif event.key == pygame.K_DOWN:
                    # Decrease simulation speed
                    if speed_index > 0:
                        speed_index -= 1
                elif event.key == pygame.K_d:
                    debug_mode = (debug_mode + 1) % 3
                elif event.key == pygame.K_g:
                    hud.show_chart = not hud.show_chart
                elif event.key in (pygame.K_f, pygame.K_F11):
                    display.toggle_fullscreen()
                elif event.key == pygame.K_c:
                    scene.cycle_color_mode()
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT and paused:
                    step_request = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = display.to_pixels(event.pos)  # Window points → surface pixels (2x on Retina)
                if layout.world.collidepoint(mx, my):  # Click in the world (not in the panels)
                    wx = (mx - layout.world.x) / layout.scale  # Pixels → world units
                    wy = (my - layout.world.y) / layout.scale
                    selected = pick_creature(world, wx, wy)
                    trail.clear()

        if display.generation != last_generation or display.surface().get_size() != last_size:
            continue  # The window changed during the events (fullscreen): relayout before drawing

        speed = config.SPEED_STEPS[speed_index]
        
        if speed != last_speed:
            # An average over two different speeds would be meaningless
            update_time = draw_time = flip_time = 0.0
            frames = 0
            window_start = time.perf_counter()
            last_speed = speed

        # Run several simulation ticks per frame, according to the chosen speed
        t0 = time.perf_counter()
        ticks_to_run = 1 if step_request else (0 if paused else speed)
        for _ in range(ticks_to_run):
            world.update()
            if selected is not None and selected.alive:
                trail.append((selected.x, selected.y))
            if world.is_over():
                # End of the generation: parents + mutated children form the next one
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
                print(f"Gen {generation:>4} | fin {format_time(world.tick)} | "
                      f"vivantes {alive_count}/{len(world.creatures)} | "
                      f"meilleur âge {format_time(parents[0].age)} | "
                      f"nourriture parents moy {mean_food:.1f} max {max_food} | "
                      f"vitesse moy parents {mean_speed:.2f} | "
                      f"mangé total {total_food} | aveugles {blind_frac:.0%} | "
                      f"énergie moy parents {mean_energy:.0f}")
                log_generation({
                    "generation": generation, "ticks": world.tick, "alive": alive_count,
                    "best_age": parents[0].age, "mean_food": mean_food, "max_food": max_food,
                    "mean_speed": mean_speed, "food_count": config.FOOD_COUNT,
                    "total_food": total_food, "blind_frac": blind_frac,
                    "blind_speed": blind_speed, "blind_turn": blind_turn,
                    "mean_energy": mean_energy,
                })
                hud.reload_stats()
                genomes = [p.brain.get_genome() for p in parents]
                save_genomes(genomes, generation)
                brains = brains_from_genomes(genomes, rng)
                world = World(rng)
                for brain in brains:
                    world.add_creature(brain)
                generation += 1
                selected = None  # The creatures of the old world no longer exist
                trail.clear()
                break
        t1 = time.perf_counter()

        # Draw the world, then the heads-up display (HUD)
        scene.draw(world_view, world, debug_mode, selected, trail)
        hud.draw(sidebar, strip_view, world, clock.get_fps(), speed, generation, debug_mode, paused, selected,
                 scene.color_label())
        t2 = time.perf_counter()

        display.flip()
        t3 = time.perf_counter()

        update_time += t1 - t0
        draw_time += t2 - t1
        flip_time += t3 - t2
        frames += 1
        if t3 - window_start >= 1.0:
            ms = 1000.0 / frames
            #print(f"x{speed} | update {update_time * ms:.2f} ms/image "
                  #f"({update_time * ms / speed:.3f} ms/tick) | "
                  #f"dessin {draw_time * ms:.2f} ms | flip {flip_time * ms:.2f} ms | "
                  #f"{frames} images")
            update_time = draw_time = flip_time = 0.0
            frames = 0
            window_start = t3
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    