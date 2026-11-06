import pygame
import config
import random

from core.creature import Creature
from core.world import World


def main():

    pygame.init()

    rng = random.Random(config.SEED)

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Evolution Simulator")
    clock = pygame.time.Clock()

    creature = Creature(config.SCREEN_WIDTH / 2, 
                       config.SCREEN_HEIGHT / 2, 
                       config.CREATURE_ANGLE, 
                       config.CREATURE_SPEED, 
                       config.INITIAL_ENERGY,
                       config.ENERGY_COST_PER_TICK)

    world = World(rng)
    world.creatures.append(creature)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.fill(config.BACKGROUND_COLOR)

        world.update()
        for food in world.foods:
            pygame.draw.circle(screen, config.FOOD_COLOR, (int(food.x), int(food.y)), config.FOOD_RADIUS)

        for c in world.creatures:
            color = config.CREATURE_COLOR if c.alive else config.DEAD_COLOR
            pygame.draw.circle(screen, color, (int(c.x), int(c.y)), config.CREATURE_RADIUS)

        print (f"Creature Energy: {creature.energy:.2f}, Food Eaten: {creature.food_eaten}, Alive: {creature.alive}")
        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    