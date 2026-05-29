"""Shared test fixtures.

Makes `tests/mock.py` importable as `mock` and silences OpenHosta's .env warning
so test output stays clean (no API key is ever needed — the model is mocked).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENHOSTA_SILENCE_ENV_WARNING", "1")

sys.path.insert(0, str(Path(__file__).parent))
