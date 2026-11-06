"""Score the guard against the truth of a simulated workspace, next to the obvious alternative (flag an
agent when the new model's answers read differently). This is the only module, with guard.sim, that
reads the truth."""

from __future__ import annotations

import json
import time
from pathlib import Path

from guard.agent import Agent
from guard.compare import AgentReport, guard_agent, text_diff_gate
from guard.sim.bench import AgentTruth, build
from guard.sim.model import SimModel
from guard.spec import mine

ROOT = Path(__file__).resolve().parent.parent
HARD_DEFAULT = ["json_output", "tool_first", "refuse_topic", "language", "stay_in_scope", "ask_if_missing"]


def load_bench(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or ROOT / "config" / "bench.json").read_text())


def world(spec: dict) -> tuple[list[Agent], list[AgentTruth]]:
    agents, truths = [], []
    for w in spec["worlds"]:
        a, t = build(w["agents"], w["seed"], spec["phrasing"], spec.get("regress_share", 0.6))
        agents += a
        truths += t
    return agents, truths


def models_for(t: AgentTruth, bench: dict) -> tuple[SimModel, SimModel]:
    return SimModel(bench["baseline_name"], t), SimModel(bench["candidate_name"], t, t.quirks, t.benign)


def truth_verdict(t: AgentTruth, hard: list[str]) -> str:
    kinds = t.regressed_kinds
    if any(k in hard for k in kinds):
        return "block"
    return "review" if kinds else "safe"


def _params_match(kind: str, truth: dict, mined: dict) -> bool:
    if kind == "language":
        return truth.get("lang") == mined.get("lang")
    if kind == "max_words":
        return truth.get("n") == mined.get("n")
    if kind == "tool_first":
        return truth.get("tool") == mined.get("tool")
    if kind == "json_output":
        return set(truth.get("fields", [])) <= set(mined.get("fields", []))
    return True


def mining_scores(agents: list[Agent], truths: list[AgentTruth]) -> dict:
    per: dict[str, dict] = {}
    misses = []
    for a, t in zip(agents, truths, strict=True):
        mined = [o for o in mine(a) if not o.implicit or o.kind == "json_output"]
        want = {o["kind"]: o["params"] for o in t.obligations}
        got = {o.kind: o.params for o in mined}
        for k in set(want) | set(got):
            row = per.setdefault(k, {"tp": 0, "fp": 0, "fn": 0, "wrong_params": 0})
            if k in want and k in got:
                row["tp"] += 1
                if not _params_match(k, want[k], got[k]):
                    row["wrong_params"] += 1
            elif k in got:
                row["fp"] += 1
                misses.append({"agent": a.id, "kind": k, "type": "invented", "source": next(o.source for o in mined if o.kind == k)})
            else:
                row["fn"] += 1
                misses.append({"agent": a.id, "kind": k, "type": "missed", "instructions": a.instructions})
    tp = sum(r["tp"] for r in per.values())
    fp = sum(r["fp"] for r in per.values())
    fn = sum(r["fn"] for r in per.values())
    return {
        "precision": round(tp / max(1, tp + fp), 4),
        "recall": round(tp / max(1, tp + fn), 4),
        "per_kind": dict(sorted(per.items())),
        "misses": misses[:40],
    }


def run(spec: dict, bench: dict, cfg: dict, with_text_diff: bool = True) -> dict:
    agents, truths = world(spec)
    hard = cfg.get("hard", HARD_DEFAULT)
    t0 = time.perf_counter()
    rows = []
    reports: list[AgentReport] = []
    for a, t in zip(agents, truths, strict=True):
        base, cand = models_for(t, bench)
        r = guard_agent(a, base, cand, cfg)
        reports.append(r)
        td = text_diff_gate(a, *models_for(t, bench), cfg) if with_text_diff else None
        found = {o.obligation["kind"] for o in r.obligations if o.state in ("regressed", "watch")}
        tested = {o.obligation["kind"] for o in r.obligations if o.state != "untested"}
        mined = {o.obligation["kind"] for o in r.obligations}
        rows.append(
            {
                "agent_id": a.id,
                "domain": t.domain,
                "truth": truth_verdict(t, hard),
                "verdict": r.verdict,
                "regressed_kinds": t.regressed_kinds,
                "found_kinds": sorted(found),
                "missed_kinds": [
                    {"kind": k, "why": "not mined" if k not in mined else "untested" if k not in tested else "held"}
                    for k in t.regressed_kinds
                    if k not in found
                ],
                "false_kinds": sorted(found - set(t.regressed_kinds)),
                "quirks": t.quirks,
                "benign": t.benign,
                "probes_run": r.probes_run,
                "tokens": r.tokens_estimate,
                "text_similarity": td["similarity"] if td else None,
            }
        )
    elapsed = time.perf_counter() - t0
    return {
        "agents": agents,
        "truths": truths,
        "reports": reports,
        "rows": rows,
        "seconds": round(elapsed, 2),
        "mining": mining_scores(agents, truths),
    }


def _rate(n: int, d: int) -> float:
    return round(n / d, 4) if d else 0.0


def score(rows: list[dict], text_diff_threshold: float) -> dict:
    reg = [r for r in rows if r["truth"] != "safe"]
    clean = [r for r in rows if r["truth"] == "safe"]
    hard = [r for r in rows if r["truth"] == "block"]
    flagged = lambda r: r["verdict"] != "safe"  # noqa: E731
    td_flag = lambda r: r["text_similarity"] is not None and r["text_similarity"] < text_diff_threshold  # noqa: E731
    kinds_total = sum(len(r["regressed_kinds"]) for r in reg)
    kinds_found = sum(len(set(r["regressed_kinds"]) & set(r["found_kinds"])) for r in reg)
    benign_only = [r for r in clean if r["benign"]]
    missed = {}
    for r in reg:
        for m in r["missed_kinds"]:
            missed.setdefault(m["kind"], {"not mined": 0, "untested": 0, "held": 0})[m["why"]] += 1
    buckets = {"under 50% of answers": (0, 0.5), "50-75%": (0.5, 0.75), "75% or more": (0.75, 1.01)}
    by_strength = {}
    for name, (lo, hi) in buckets.items():
        grp = [r for r in reg if lo <= max(r["quirks"].values()) < hi]
        by_strength[name] = {
            "agents": len(grp),
            "guard": _rate(sum(flagged(r) for r in grp), len(grp)),
            "text_diff": _rate(sum(td_flag(r) for r in grp), len(grp)),
        }
    run = sum(r["probes_run"] for r in rows)
    return {
        "agents": len(rows),
        "regressed_agents": len(reg),
        "clean_agents": len(clean),
        "guard": {
            "recall": _rate(sum(flagged(r) for r in reg), len(reg)),
            "false_alarm_rate": _rate(sum(flagged(r) for r in clean), len(clean)),
            "false_alarms_on_reworded": _rate(sum(flagged(r) for r in benign_only), len(benign_only)),
            "hard_blocked": _rate(sum(r["verdict"] == "block" for r in hard), len(hard)),
            "obligation_recall": _rate(kinds_found, kinds_total),
            "wrong_obligation_flags": sum(len(r["false_kinds"]) for r in rows),
            "missed_by_kind": dict(sorted(missed.items())),
        },
        "recall_by_strength": by_strength,
        "text_diff": {
            "threshold": text_diff_threshold,
            "recall": _rate(sum(td_flag(r) for r in reg), len(reg)),
            "false_alarm_rate": _rate(sum(td_flag(r) for r in clean), len(clean)),
            "false_alarms_on_reworded": _rate(sum(td_flag(r) for r in benign_only), len(benign_only)),
        },
        "cost": {
            "probes_run": run,
            "probes_per_agent": round(run / max(1, len(rows)), 1),
            "tokens": sum(r["tokens"] for r in rows),
            "tokens_per_agent": round(sum(r["tokens"] for r in rows) / max(1, len(rows))),
        },
    }


def best_text_diff_threshold(rows: list[dict]) -> float:
    """The fairest version of the alternative: the threshold that maximises recall minus false alarms on dev."""
    best, best_j = 0.5, -1.0
    for i in range(5, 96):
        th = i / 100
        s = score(rows, th)["text_diff"]
        j = s["recall"] - s["false_alarm_rate"]
        if j > best_j:
            best, best_j = th, j
    return best


def budget_sweep(spec: dict, bench: dict, cfg: dict, sizes: list[int]) -> list[dict]:
    """Recall, false alarms and cost against the number of probes per kind: the cost lever."""
    out = []
    for n in sizes:
        c = dict(cfg, per_kind=n)
        res = run(spec, bench, c, with_text_diff=False)
        s = score(res["rows"], cfg["text_diff_threshold"])
        out.append(
            {
                "per_kind": n,
                "recall": s["guard"]["recall"],
                "false_alarm_rate": s["guard"]["false_alarm_rate"],
                "obligation_recall": s["guard"]["obligation_recall"],
                "tokens_per_agent": s["cost"]["tokens_per_agent"],
                "probes_per_agent": s["cost"]["probes_per_agent"],
            }
        )
    return out
