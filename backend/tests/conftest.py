import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO / "backend", REPO / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import os

os.environ.setdefault("SF_NO_APP", "1")

import pytest  # noqa: E402


@pytest.fixture
def eng():
    from app.runtime import build
    return build(explainer=None)  # unit tests never call the real model


@pytest.fixture
def client(eng):
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(eng, ticker=False)) as c:
        yield c
