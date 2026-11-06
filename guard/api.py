"""HTTP API. Reading an agent's obligations and test messages needs no model; a live check needs
GUARD_API_KEY. The measured results are served from the generated reports/results.json."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from guard.agent import Agent
from guard.compare import guard_agent, load_config
from guard.evaluate import ROOT
from guard.probes import generate
from guard.spec import mine

app = FastAPI(title="agent-upgrade-guard", version="0.1.0")


class CheckRequest(BaseModel):
    agent: dict
    baseline: str
    candidate: str


def _results() -> dict:
    p = ROOT / "reports" / "results.json"
    if not p.exists():
        raise HTTPException(404, "no results yet: run `guard report`")
    return json.loads(p.read_text())


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/results")
def results() -> dict:
    r = _results()
    return {k: v for k, v in r.items() if k != "agents"}


@app.get("/agents")
def agents() -> list[dict]:
    return [
        {"agent_id": a["agent_id"], "agent_name": a["agent_name"], "verdict": a["verdict"], "domain": a["domain"]}
        for a in _results()["agents"]
    ]


@app.get("/agents/{agent_id}")
def agent(agent_id: str) -> dict:
    for a in _results()["agents"]:
        if a["agent_id"] == agent_id:
            return a
    raise HTTPException(404, f"no agent {agent_id}")


@app.post("/obligations")
def obligations(agent: dict) -> dict:
    try:
        a = Agent.from_dict(agent)
    except (KeyError, TypeError) as e:
        raise HTTPException(422, f"not an agent: {e}") from e
    obs = mine(a)
    return {"obligations": [o.to_dict() for o in obs], "probes": [p.to_dict() for p in generate(a, obs, load_config()["per_kind"])]}


@app.post("/check")
def check(req: CheckRequest) -> dict:
    from guard.models import OpenAICompatible

    try:
        base, cand = OpenAICompatible(req.baseline), OpenAICompatible(req.candidate)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return guard_agent(Agent.from_dict(req.agent), base, cand, load_config()).to_dict()
