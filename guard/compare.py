"""The gate: run an agent's probes on the current model and the candidate, check every answer against
every obligation, and decide per obligation whether the candidate is worse by more than chance.

Models are not deterministic, and the current model also fails sometimes. "The candidate failed a
check" is not a regression; "the candidate fails this obligation more often than the current model,
by a margin chance would rarely produce" is. That is a one-sided Fisher exact test per obligation."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from guard.agent import Agent, Run, answer
from guard.checks import CheckResult, check
from guard.models import ModelClient
from guard.probes import Probe, generate
from guard.spec import Obligation, mine
from guard.textutil import jaccard


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else Path(__file__).resolve().parent.parent / "config" / "guard.json"
    return json.loads(p.read_text())


def _hyper(k: int, n1: int, n2: int, t: int) -> float:
    return math.comb(n1, k) * math.comb(n2, t - k) / math.comb(n1 + n2, t)


def fisher_greater(c_fail: int, c_n: int, b_fail: int, b_n: int) -> float:
    """P(candidate failures >= observed | same failure rate), conditioning on the total failures."""
    t = c_fail + b_fail
    if c_n == 0 or b_n == 0 or t == 0:
        return 1.0
    return sum(_hyper(k, c_n, b_n, t) for k in range(c_fail, min(c_n, t) + 1))


@dataclass
class ObligationResult:
    obligation: dict
    hard: bool
    baseline_fail: int = 0
    baseline_n: int = 0
    candidate_fail: int = 0
    candidate_n: int = 0
    p_value: float = 1.0
    state: str = "held"  # held | regressed | watch | improved | untested | suspect
    examples: list[dict] = field(default_factory=list)
    # Counts per slice of probes, [baseline_fail, baseline_n, candidate_fail, candidate_n]. A language
    # obligation is judged on same-language and other-language questions separately, because drift
    # usually shows on one slice only and pooling would wash it out.
    strata: dict = field(default_factory=dict)
    stratum: str = "all"


@dataclass
class AgentReport:
    agent_id: str
    agent_name: str
    baseline: str
    candidate: str
    verdict: str
    obligations: list[ObligationResult]
    probes_run: int
    tokens_estimate: int
    idle_days: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def stratum(o: Obligation, p: Probe) -> str:
    if o.kind == "language" and o.params.get("lang") != "user":
        return "same language" if p.lang == o.params["lang"] else "other language"
    if o.kind == "ask_if_missing":
        # Asking when the number is missing and not asking again when it is given are different habits.
        return "number missing" if p.kind == "missing" else "number given"
    return "all"


def _judge(r: ObligationResult, cfg: dict) -> None:
    tested = {k: v for k, v in r.strata.items() if v[1] and v[3]}
    if not tested:
        r.state = "untested"
        return
    # Bonferroni across slices: looking at two slices must not make a false alarm twice as likely.
    alpha = cfg["alpha"] / len(tested)
    watch = cfg["watch_p"] / len(tested)
    best = None
    for name, (bf, bn, cf, cn) in tested.items():
        p = fisher_greater(cf, cn, bf, bn)
        if best is None or p < best[0]:
            best = (p, name, bf / bn, cf / cn)
    p, name, bb, cb = best
    r.p_value, r.stratum = p, name
    # When the current model fails a check most of the time, the check (or the reading of the
    # instruction) is more likely wrong than the model, and a comparison proves nothing either way.
    if r.baseline_n >= cfg["suspect_min_n"] and r.baseline_fail / r.baseline_n >= cfg["suspect_baseline_fail"]:
        r.state = "suspect"
        return
    p_better = fisher_greater(r.baseline_fail, r.baseline_n, r.candidate_fail, r.candidate_n)
    if p <= alpha and cb - bb >= cfg["min_effect"]:
        r.state = "regressed"
    elif p <= watch and cb - bb >= cfg["min_effect"] / 2:
        r.state = "watch"
    elif (
        r.baseline_n
        and r.candidate_n
        and p_better <= cfg["alpha"]
        and r.baseline_fail / r.baseline_n - r.candidate_fail / r.candidate_n >= cfg["min_effect"]
    ):
        r.state = "improved"
    else:
        r.state = "held"


def verdict(results: list[ObligationResult]) -> str:
    if any(r.state == "regressed" and r.hard for r in results):
        return "block"
    if any(r.state in ("regressed", "watch", "suspect") for r in results):
        return "review"
    return "safe"


def guard_agent(agent: Agent, baseline: ModelClient, candidate: ModelClient, cfg: dict) -> AgentReport:
    obligations: list[Obligation] = mine(agent)
    probes: list[Probe] = generate(agent, obligations, per_kind=cfg["per_kind"])
    results = {o.id: ObligationResult(o.to_dict(), o.kind in cfg["hard"]) for o in obligations}
    runs: dict[tuple[str, str], Run] = {}
    tokens = 0

    def run_probes(ps: list[Probe]) -> None:
        nonlocal tokens
        for p in ps:
            for side, model in (("baseline", baseline), ("candidate", candidate)):
                run = answer(agent, model, p.id, p.text)
                runs[(side, p.id)] = run
                tokens += (run.prompt_chars + run.completion_chars) // 4
            b, c = runs[("baseline", p.id)], runs[("candidate", p.id)]
            for o in obligations:
                rb: CheckResult = check(o, p, b, agent)
                rc: CheckResult = check(o, p, c, agent)
                res = results[o.id]
                st = res.strata.setdefault(stratum(o, p), [0, 0, 0, 0])
                if rb.status != "na":
                    res.baseline_n += 1
                    res.baseline_fail += rb.status == "fail"
                    st[1] += 1
                    st[0] += rb.status == "fail"
                if rc.status != "na":
                    res.candidate_n += 1
                    res.candidate_fail += rc.status == "fail"
                    st[3] += 1
                    st[2] += rc.status == "fail"
                if rc.status == "fail" and rb.status != "fail" and len(res.examples) < cfg["examples"]:
                    res.examples.append(
                        {
                            "probe": p.text,
                            "baseline": b.reply[:600],
                            "candidate": c.reply[:600],
                            "why": rc.evidence,
                            "baseline_actions": [t.name for t in b.tool_calls],
                            "candidate_actions": [t.name for t in c.tool_calls],
                        }
                    )

    run_probes(probes)
    for r in results.values():
        _judge(r, cfg)
    ran = len({pid for (_, pid) in runs})
    return AgentReport(
        agent.id,
        agent.name,
        baseline.name,
        candidate.name,
        verdict(list(results.values())),
        list(results.values()),
        ran,
        tokens,
        agent.idle_days,
    )


def text_diff_gate(agent: Agent, baseline: ModelClient, candidate: ModelClient, cfg: dict) -> dict:
    """The obvious alternative: replay the same messages and flag the agent when answers changed a lot."""
    obligations = mine(agent)
    probes = generate(agent, obligations, per_kind=cfg["per_kind"])
    sims = []
    for p in probes:
        b = answer(agent, baseline, p.id, p.text)
        c = answer(agent, candidate, p.id, p.text)
        sims.append(jaccard(b.reply, c.reply))
    mean = sum(sims) / max(1, len(sims))
    return {"agent_id": agent.id, "similarity": round(mean, 3), "flagged": mean < cfg["text_diff_threshold"], "probes": len(probes)}
