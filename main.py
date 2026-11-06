import pygame
import config
import random

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

    running = True
    while running:
        for event in pygame.event.get():
            # Handle quitting the game
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.fill(config.BACKGROUND_COLOR)

        # Add a new population of creatures
        
        # Update the world, which updates all creatures and checks for food consumption
        world.update()

        # Draw all food items and creatures on the screen
        for food in world.foods:
            pygame.draw.circle(screen, config.FOOD_COLOR, (int(food.x), int(food.y)), config.FOOD_RADIUS)

        for c in world.creatures:
            color = config.CREATURE_COLOR if c.alive else config.DEAD_COLOR
            pygame.draw.circle(screen, color, (int(c.x), int(c.y)), config.CREATURE_RADIUS)

        # Draw the heads-up display (HUD) with the current game statistics
        draw_hud(screen, font, world, clock.get_fps())

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    