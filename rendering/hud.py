import pygame

def create_font():
    """Create a font object for rendering text."""
    return pygame.font.SysFont("arial", 18)

def draw_hud(screen, font, world, fps):
    """Draw the heads-up display (HUD) on the screen."""
    creatures = world.creatures

    alive_count = sum(1 for c in creatures if c.alive)
    best_age = max((c.age for c in creatures), default=0)
    zero_food = sum(1 for c in creatures if c.food_eaten == 0)

    lines = [
        f"Vivantes: {alive_count}/{len(creatures)}",
        f"Meilleur âge: {best_age}",
        f"Sans nourriture: {zero_food}",
        f"FPS: {fps:.0f}"
    ]

    for i, line in enumerate(lines):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (10, 10 + i * 22))