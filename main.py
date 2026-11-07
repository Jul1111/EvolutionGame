import pygame
import config
import random
import time

from core.world import World
from evolution.population import brains_from_genomes, select_parents
from rendering.hud import Hud, format_time
from rendering.scene import Scene
from utils.persistence import save_genomes, load_genomes
from utils.logger import log_generation


def main():

    pygame.init()

    rng = random.Random(config.SEED)

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Evolution Simulator")
    clock = pygame.time.Clock()

    # Rendering: world scene (background, food, creatures) and HUD (panel, curves)
    scene = Scene()
    hud = Hud()
    debug_mode = 0  # 0 = off, 1 = oldest living creature, 2 = all living creatures

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
        for event in pygame.event.get():
            # Handle quitting the game
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
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

        speed = config.SPEED_STEPS[speed_index]
        
        if speed != last_speed:
            # An average over two different speeds would be meaningless
            update_time = draw_time = flip_time = 0.0
            frames = 0
            window_start = time.perf_counter()
            last_speed = speed

        # Run several simulation ticks per frame, according to the chosen speed
        t0 = time.perf_counter()
        for _ in range(speed):
            world.update()
            if world.is_over():
                # End of the generation: parents + mutated children form the next one
                parents = select_parents(world.creatures, config.PARENTS_COUNT)
                mean_food = sum(c.food_eaten for c in parents) / len(parents)
                alive_count = sum(1 for c in world.creatures if c.alive)
                max_food = max(c.food_eaten for c in parents)
                mean_speed = sum(c.speed for c in parents) / len(parents)
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
                      f"mangé total {total_food} | aveugles {blind_frac:.0%}")
                log_generation({
                    "generation": generation, "ticks": world.tick, "alive": alive_count,
                    "best_age": parents[0].age, "mean_food": mean_food, "max_food": max_food,
                    "mean_speed": mean_speed, "food_count": config.FOOD_COUNT,
                    "total_food": total_food, "blind_frac": blind_frac,
                    "blind_speed": blind_speed, "blind_turn": blind_turn,
                })
                hud.reload_stats()
                genomes = [p.brain.get_genome() for p in parents]
                save_genomes(genomes, generation)
                brains = brains_from_genomes(genomes, rng)
                world = World(rng)
                for brain in brains:
                    world.add_creature(brain)
                generation += 1
                break
        t1 = time.perf_counter()

        # Draw the world, then the heads-up display (HUD)
        scene.draw(screen, world, debug_mode)
        hud.draw(screen, world, clock.get_fps(), speed, generation, debug_mode)
        t2 = time.perf_counter()

        pygame.display.flip()
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