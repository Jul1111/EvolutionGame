import pygame
import config
import random
import time

from core.world import World
from rendering.hud import create_font, draw_hud


def main():

    pygame.init()

    rng = random.Random(config.SEED)

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Evolution Simulator")
    clock = pygame.time.Clock()

    # Create a font for rendering text
    font = create_font()

    world = World(rng)
    world.add_population(config.POPULATION_SIZE)

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

        speed = config.SPEED_STEPS[speed_index]
        
        if speed != last_speed:
            # An average over two different speeds would be meaningless
            update_time = draw_time = flip_time = 0.0
            frames = 0
            window_start = time.perf_counter()
            last_speed = speed

        screen.fill(config.BACKGROUND_COLOR)

        # Run several simulation ticks per frame, according to the chosen speed
        t0 = time.perf_counter()
        for _ in range(speed):
            world.update()
        t1 = time.perf_counter()

        # Draw all food items and creatures on the screen
        for food in world.foods:
            pygame.draw.circle(screen, config.FOOD_COLOR, (int(food.x), int(food.y)), config.FOOD_RADIUS)

        for c in world.creatures:
            color = config.CREATURE_COLOR if c.alive else config.DEAD_COLOR
            pygame.draw.circle(screen, color, (int(c.x), int(c.y)), config.CREATURE_RADIUS)

        # Draw the heads-up display (HUD) with the current game statistics
        draw_hud(screen, font, world, clock.get_fps(), speed)
        t2 = time.perf_counter()

        pygame.display.flip()
        t3 = time.perf_counter()

        update_time += t1 - t0
        draw_time += t2 - t1
        flip_time += t3 - t2
        frames += 1
        if t3 - window_start >= 1.0:
            ms = 1000.0 / frames
            print(f"x{speed} | update {update_time * ms:.2f} ms/image "
                  f"({update_time * ms / speed:.3f} ms/tick) | "
                  f"dessin {draw_time * ms:.2f} ms | flip {flip_time * ms:.2f} ms | "
                  f"{frames} images")
            update_time = draw_time = flip_time = 0.0
            frames = 0
            window_start = t3
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    