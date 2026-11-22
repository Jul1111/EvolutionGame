import gc
import os
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # No screen: pygame draws into memory
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("EVOLUTION_RENDERER", "cpu")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402


@pytest.fixture(autouse=True)
def clean_config(tmp_path):
    """Each test gets config.py as written, saves in a temporary folder, and config is restored afterwards."""
    saved = {n: getattr(config, n) for n in dir(config) if n.isupper()}
    config.SAVE_DIR = str(tmp_path / "saves")
    config.LOAD_ON_START = False
    yield
    for n, v in saved.items():
        setattr(config, n, v)


@pytest.fixture(params=["cpu", "gpu"])
def renderer(request, monkeypatch):
    """The two ways of drawing (see rendering/backend/): the processor, and the graphics card, here SDL's software
    renderer under the dummy video driver."""
    monkeypatch.setenv("EVOLUTION_RENDERER", request.param)
    return request.param


@pytest.fixture
def make_app(monkeypatch, renderer):
    """Builds an App (window, menus, panels) with a small population, drawn by each renderer in turn.
    `launched=True` starts a simulation, else the start menu and setup screen of the launch are shown."""
    import pygame
    apps = []

    def make(launched=True, **settings):
        monkeypatch.setattr(config, "LOAD_SETTINGS", False)
        monkeypatch.setattr(config, "LOAD_ON_START", False)
        config.INITIAL_POPULATION = 30
        for name, value in settings.items():
            setattr(config, name, value)
        from app import App
        app = App()
        assert (app.display.gpu is not None) == (renderer == "gpu"), "the requested renderer did not start"
        if launched:
            app.do("start_new")
            app.do("setup_launch")
        apps.append(app)
        return app

    yield make
    for app in apps:
        app.display.close()   # Textures are freed while their renderer exists
    apps.clear()
    gc.collect()   # An App is in a reference cycle: free its window now, not in the middle of the next test
    pygame.quit()
