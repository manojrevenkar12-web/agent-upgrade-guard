import json
from pathlib import Path

from fastapi.testclient import TestClient

from guard.api import app

client = TestClient(app)
EXAMPLE = json.loads((Path(__file__).resolve().parent.parent / "examples" / "agents" / "order-support.json").read_text())


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_obligations_without_a_model():
    r = client.post("/obligations", json=EXAMPLE).json()
    assert {o["kind"] for o in r["obligations"]} >= {"language", "ask_if_missing", "tool_first", "stay_in_scope", "grounded"}
    assert len({p["text"] for p in r["probes"]}) == len(r["probes"])


def test_bad_agent_is_a_422():
    assert client.post("/obligations", json={"name": "x"}).status_code == 422


def test_live_check_without_a_key_says_so(monkeypatch):
    monkeypatch.delenv("GUARD_API_KEY", raising=False)
    r = client.post("/check", json={"agent": EXAMPLE, "baseline": "a", "candidate": "b"})
    assert r.status_code == 400 and "GUARD_API_KEY" in r.json()["detail"]
