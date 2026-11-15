"""Review fixes: no file reads outside dist, demo endpoints off by default."""
import pytest
from fastapi.testclient import TestClient

import app.main as main_mod
from app.main import create_app


@pytest.fixture
def built_client(tmp_path, monkeypatch, eng):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("INDEX")
    (dist / "emergency.html").write_text("EMERGENCY")
    (tmp_path / "secret.txt").write_text("SECRET")
    monkeypatch.setattr(main_mod, "DIST", dist)
    with TestClient(create_app(eng, ticker=False)) as c:
        yield c


def test_built_files_are_served(built_client):
    assert built_client.get("/emergency.html").text == "EMERGENCY"
    assert built_client.get("/anything/else").text == "INDEX"


@pytest.mark.parametrize("path", ["/..%2fsecret.txt", "/%2e%2e%2fsecret.txt", "/..%2f..%2fsecret.txt"])
def test_path_outside_dist_is_not_served(built_client, path):
    assert "SECRET" not in built_client.get(path).text


@pytest.mark.parametrize("method,path", [("post", "/api/sim/reset"), ("post", "/api/sim/clock/advance"), ("post", "/api/sim/replay")])
def test_demo_endpoints_are_off_by_default(client, method, path):
    assert getattr(client, method)(path, json={"seconds": 1, "file": "x"}).status_code in (404, 405)


def test_demo_endpoints_work_when_enabled(eng, monkeypatch):
    monkeypatch.setenv("SF_SIM", "1")
    with TestClient(create_app(eng, ticker=False)) as c:
        assert c.post("/api/sim/reset").status_code == 200
