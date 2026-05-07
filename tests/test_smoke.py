"""Smoke tests so CI has something to run from day one."""

from neurograph import __version__
from neurograph.config import settings


def test_version():
    assert __version__ == "0.1.0"


def test_settings_load():
    # Should not raise even with no .env
    assert settings.chunk_size > 0
    assert 0 < settings.cache_threshold <= 1
    assert settings.embedding_dim == 384
