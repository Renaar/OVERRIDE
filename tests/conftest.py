import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine.catalog import Catalog, Inventory  # noqa: E402


def load(name):
    return json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def config():
    return load("config")


@pytest.fixture(scope="session")
def catalog():
    return Catalog(load("skills"))


@pytest.fixture
def inventory():
    return Inventory({"H", "P"}, {"H": (10.0, 1.0)})
