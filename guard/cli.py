"""guard: check agents before a model upgrade.

guard bench                 score the guard on the simulated dev workspace
guard heldout --pin         generate and pin the held-out workspace (once, before any run)
guard heldout               run the pinned held-out workspace (once; the first run is the result)
guard report                regenerate reports/ and the dashboard data
guard check AGENT.json --baseline MODEL --candidate MODEL
                            check a real agent against two real models (GUARD_API_KEY, GUARD_BASE_URL)
guard serve                 the HTTP API
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys

from guard.agent import Agent
from guard.compare import guard_agent, load_config
from guard.evaluate import best_text_diff_threshold, load_bench, run, score
from guard.report import HELDOUT, build_results, world_digest, write_all


def cmd_bench(args) -> int:
    cfg, bench = load_config(), load_bench()
    res = run(bench["dev"], bench, cfg)
    s = score(res["rows"], cfg["text_diff_threshold"])
    s["text_diff_best_threshold_on_dev"] = best_text_diff_threshold(res["rows"])
    s["mining"] = {k: v for k, v in res["mining"].items() if k in ("precision", "recall")}
    print(json.dumps(s, indent=1))
    return 0


def cmd_heldout(args) -> int:
    cfg, bench = load_config(), load_bench()
    spec = bench[{"v1": "heldout", "v2": "heldout2"}[args.set]]
    pin, status = HELDOUT / f"{args.set}.sha256", HELDOUT / args.set / "STATUS"
    status.parent.mkdir(parents=True, exist_ok=True)
    digest = world_digest(spec, bench)
    if args.pin:
        if pin.exists():
            print(f"already pinned: {pin.read_text().strip()}", file=sys.stderr)
            return 1
        pin.write_text(digest + "\n")
        status.write_text("sealed: pinned, never run\n")
        print(f"pinned {digest}")
        return 0
    if not pin.exists():
        print("pin the held-out workspace first: guard heldout --pin", file=sys.stderr)
        return 1
    if pin.read_text().strip() != digest:
        print(
            "the held-out workspace no longer matches its pin; the bench generator changed. Do not re-pin to make this pass.",
            file=sys.stderr,
        )
        return 1
    first = HELDOUT / args.set / "first_run.json"
    if first.exists() and not args.again:
        print(
            f"already run; the first run is the result ({first}). Use --again for a later run that is recorded separately.", file=sys.stderr
        )
        return 1
    res = run(spec, bench, cfg)
    s = score(res["rows"], cfg["text_diff_threshold"])
    misses = []
    for r in res["rows"]:
        for m in r["missed_kinds"]:
            misses.append(f"{r['agent_id']} ({r['domain']}): {m['kind']} regression missed ({m['why']}); planted {r['quirks']}")
        if r["truth"] == "safe" and r["verdict"] != "safe":
            misses.append(f"{r['agent_id']} ({r['domain']}): flagged {r['verdict']} without a planted regression ({r['false_kinds']})")
    for m in res["mining"]["misses"]:
        misses.append(
            f"{m['agent']}: obligation {m['kind']} {m['type']} when reading the instructions"
            + (f' ("{m["source"]}")' if m.get("source") else "")
        )
    out = {
        "run_at": dt.date.today().isoformat(),
        "world_sha256": digest,
        "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "score": s,
        "mining": {k: v for k, v in res["mining"].items() if k != "misses"},
        "misses": misses,
        "rows": res["rows"],
    }
    blob = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    target = first if not first.exists() else HELDOUT / args.set / f"later_run_{dt.datetime.now():%Y%m%d%H%M%S}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(blob)
    if target == first:
        (HELDOUT / args.set / "first_run.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "\n")
        status.write_text(
            f"used: first run {out['run_at']}; results in {args.set}/first_run.json. Nothing may be tuned on this workspace.\n"
        )
    print(
        json.dumps({"guard": s["guard"], "text_diff": s["text_diff"], "mining": out["mining"]["recall"], "misses": len(misses)}, indent=1)
    )
    return 0


def cmd_report(args) -> int:
    write_all(build_results(with_sweep=not args.fast))
    print("wrote reports/results.json, reports/REPORT.md, web/public/data.json")
    return 0


def cmd_check(args) -> int:
    from guard.models import OpenAICompatible

    cfg = load_config()
    agent = Agent.load(args.agent)
    rep = guard_agent(agent, OpenAICompatible(args.baseline), OpenAICompatible(args.candidate), cfg)
    print(json.dumps(rep.to_dict(), indent=1, ensure_ascii=False))
    return {"safe": 0, "review": 2, "block": 3}[rep.verdict]


def cmd_serve(args) -> int:
    import uvicorn

    uvicorn.run("guard.api:app", host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="guard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bench").set_defaults(fn=cmd_bench)
    h = sub.add_parser("heldout")
    h.add_argument("--pin", action="store_true")
    h.add_argument("--again", action="store_true")
    h.add_argument("--set", default="v1", choices=["v1", "v2"], help="which pinned held-out workspace")
    h.set_defaults(fn=cmd_heldout)
    r = sub.add_parser("report")
    r.add_argument("--fast", action="store_true", help="skip the budget sweep")
    r.set_defaults(fn=cmd_report)
    c = sub.add_parser("check")
    c.add_argument("agent")
    c.add_argument("--baseline", required=True)
    c.add_argument("--candidate", required=True)
    c.set_defaults(fn=cmd_check)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
