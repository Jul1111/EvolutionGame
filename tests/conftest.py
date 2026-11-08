import os
import sys

import pytest

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
