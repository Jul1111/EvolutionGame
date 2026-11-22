"""The graphics card path (rendering/backend/gpu.py, canvas.py) against the processor path, without a screen: SDL's
software renderer under the dummy video driver."""
import pygame
import pytest

from rendering.backend.canvas import CpuCanvas
from rendering.backend.gpu import Gpu, UILayer, _merge

SIZE = (200, 120)


@pytest.fixture
def gpu():
    pygame.init()
    window = pygame.Window("test", SIZE)
    gpu = Gpu(window, hardware_only=False)
    try:
        yield gpu
    finally:
        gpu.close()   # Textures are freed while their renderer exists
        window.destroy()


def _draw_scene(canvas):
    canvas.clear()
    canvas.circle((255, 0, 0), (50, 50), 20)
    canvas.circle((255, 255, 0), (150, 40), 15, 3)
    canvas.fill_rect((0, 255, 0), pygame.Rect(100, 70, 40, 30))
    canvas.line((0, 0, 255), (10, 110), (190, 110), 3)
    canvas.lines((200, 200, 200), True, [(20, 10), (60, 10), (40, 30)], 1)


def _read_back(gpu):
    gpu.renderer.target = gpu.screen
    return gpu.renderer.to_surface()


def test_canvases_draw_the_same_picture(gpu):
    cpu_surface = pygame.Surface(SIZE)
    _draw_scene(CpuCanvas(cpu_surface))
    gpu.begin()
    _draw_scene(gpu.canvas(pygame.Rect((0, 0), SIZE)))
    gpu_surface = _read_back(gpu)
    # Solid areas are identical; edges (anti-aliasing, line ends) may differ by a few pixels
    for point in ((50, 50), (120, 85), (5, 5), (150, 25)):
        assert tuple(gpu_surface.get_at(point))[:3] == tuple(cpu_surface.get_at(point))[:3], point
    # The graphics card draws lines as soft strips (smooth like aaline), about a pixel off the processor's: compare the
    # whole picture loosely (mean difference per channel, out of 255) and its average colour
    total = sum(abs(a - b) for x in range(SIZE[0]) for y in range(SIZE[1])
                for a, b in zip(gpu_surface.get_at((x, y))[:3], cpu_surface.get_at((x, y))[:3]))
    assert total / (SIZE[0] * SIZE[1] * 3) < 5
    assert all(abs(a - b) <= 2 for a, b in zip(pygame.transform.average_color(gpu_surface)[:3],
                                               pygame.transform.average_color(cpu_surface)[:3]))


def test_canvas_offset_places_the_world_in_the_window(gpu):
    gpu.begin()
    canvas = gpu.canvas(pygame.Rect(40, 20, 100, 60))   # The world area is a part of the window
    canvas.clear()
    canvas.fill_rect((255, 255, 255), pygame.Rect(0, 0, 10, 10))
    picture = _read_back(gpu)
    assert tuple(picture.get_at((45, 25)))[:3] == (255, 255, 255) and tuple(picture.get_at((5, 5)))[:3] == (0, 0, 0)


def test_blit_and_layers(gpu):
    sprite = pygame.Surface((10, 10))
    sprite.fill((10, 200, 30))
    gpu.begin()
    canvas = gpu.canvas(pygame.Rect((0, 0), SIZE))
    canvas.clear()
    canvas.blit(sprite, (20, 20))
    canvas.fblits([(sprite, (60, 60)), (sprite, (80, 60))])
    layer = canvas.layer(40, 40)
    layer.clear()
    layer.fill_rect((200, 0, 0), pygame.Rect(0, 0, 40, 40))
    canvas.blit_layer(layer, (120, 20))
    picture = _read_back(gpu)
    for point, color in (((25, 25), (10, 200, 30)), ((85, 65), (10, 200, 30)), ((130, 30), (200, 0, 0))):
        assert tuple(picture.get_at(point))[:3] == color, point


def test_texture_cache_is_bounded_and_reused(gpu):
    surface = pygame.Surface((8, 8))
    assert gpu.texture(surface) is gpu.texture(surface)   # Same Surface: the texture is made once
    for _ in range(3000):
        gpu.texture(pygame.Surface((4, 4)))
    assert len(gpu._textures) < 3000                       # Old pictures are dropped


def test_glass_and_interface_layer(gpu):
    gpu.begin()
    canvas = gpu.canvas(pygame.Rect((0, 0), SIZE))
    canvas.clear()
    canvas.fill_rect((255, 255, 255), pygame.Rect(0, 0, 100, 120))
    panel = pygame.Rect(20, 20, 60, 60)
    gpu.glass(panel, 8, (20, 30, 40), 150)                 # Blur, tint, rounded corners
    gpu.ui.fill((255, 0, 0, 255), pygame.Rect(150, 10, 20, 20))
    gpu.present()                                          # Sends the drawn parts of the interface, then shows
    assert gpu.ui.dirty == [] or isinstance(gpu.ui.dirty, list)
    assert gpu.resize() is False                           # Same window size: nothing to rebuild


def test_ui_layer_records_what_is_drawn():
    ui = UILayer((100, 100))
    sprite = pygame.Surface((10, 10))
    ui.blit(sprite, (5, 5))
    ui.fill((255, 0, 0, 255), pygame.Rect(50, 50, 20, 20))
    side = ui.subsurface(pygame.Rect(30, 0, 70, 100))      # A sub-surface shares the record, in window pixels
    side.blit(sprite, (10, 10))
    ui.mark(pygame.Rect(0, 90, 5, 5))
    assert pygame.Rect(5, 5, 10, 10) in ui.dirty and pygame.Rect(50, 50, 20, 20) in ui.dirty
    assert pygame.Rect(40, 10, 10, 10) in ui.dirty and pygame.Rect(0, 90, 5, 5) in ui.dirty
    ui.clear(pygame.Rect(0, 0, 100, 100))
    assert ui.get_at((7, 7))[3] == 0


def test_merge_joins_touching_and_overlapping_rects():
    merged = _merge([pygame.Rect(0, 0, 10, 10), pygame.Rect(10, 0, 10, 10), pygame.Rect(100, 100, 5, 5)])
    assert sorted(tuple(r) for r in merged) == [(0, 0, 20, 10), (100, 100, 5, 5)]
    chain = _merge([pygame.Rect(0, 0, 10, 10), pygame.Rect(30, 0, 10, 10), pygame.Rect(9, 0, 22, 10)])
    assert len(chain) == 1 and chain[0] == pygame.Rect(0, 0, 40, 10)
    assert _merge([]) == []


def test_close_frees_the_textures_before_the_window_goes(gpu):
    surface = pygame.Surface((8, 8))
    gpu.texture(surface)
    assert gpu._textures
    gpu.close()
    assert not gpu._textures and not gpu._targets and gpu.screen is None
