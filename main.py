import pygame
import config
import core.creature as creature


def main():

    pygame.init()
    
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Evolution Simulator")
    clock = pygame.time.Clock()

    creature_instance = creature.Creature(config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT / 2, 0.5, 2)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.fill(config.BACKGROUND_COLOR)

        creature_instance.update()
        pygame.draw.circle(screen, config.CREATURE_COLOR, (int(creature_instance.x), int(creature_instance.y)), config.CREATURE_RADIUS)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()    