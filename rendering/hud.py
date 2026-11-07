import pygame
import config

def create_font():
    """Create a font object for rendering text."""
    return pygame.font.SysFont("arial", 18)

def format_time(ticks):
    """Convert a number of ticks to a mm:ss string (simulated time)."""
    seconds = ticks / config.TICKS_PER_SECOND
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def draw_hud(screen, font, world, fps, speed):
    """Draw the heads-up display (HUD) on the screen."""
    creatures = world.creatures

    alive_count = sum(1 for c in creatures if c.alive)
    best_age = max((c.age for c in creatures), default=0)
    zero_food = sum(1 for c in creatures if c.food_eaten == 0)

    lines = [
        f"Vivantes: {alive_count}/{len(creatures)}",
        f"Meilleur âge: {format_time(best_age)}",
        f"Sans nourriture: {zero_food}",
        f"Vitesse: x{speed}",
        f"FPS: {fps:.0f}",
        f"Temps: {format_time(world.tick)} / {format_time(config.GEN_MAX_TICKS)}",
        f"Statut : {'Terminé' if world.is_over() else 'En cours'}"
    ]

    for i, line in enumerate(lines):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (10, 10 + i * 22))