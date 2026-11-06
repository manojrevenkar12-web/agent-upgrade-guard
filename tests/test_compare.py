import math

from guard.compare import fisher_greater, guard_agent, load_config
from guard.evaluate import load_bench, models_for
from guard.sim.bench import build
from guard.sim.model import SimModel

CFG = load_config()
BENCH = load_bench()


def test_fisher_matches_hand_computation():
    # 3 of 3 failures on one side, 0 of 3 on the other: 1 / C(6,3).
    assert math.isclose(fisher_greater(3, 3, 0, 3), 1 / 20)
    assert fisher_greater(0, 10, 5, 10) == 1.0
    assert fisher_greater(0, 0, 0, 0) == 1.0


def test_same_model_twice_is_safe_everywhere():
    agents, truths = build(24, 5, "dev")
    for a, t in zip(agents, truths, strict=True):
        m = SimModel("current-model (simulated)", t)
        assert guard_agent(a, m, SimModel("current-model (simulated)", t), CFG).verdict == "safe", a.id


def test_a_strong_hard_regression_blocks_and_names_its_sentence():
    agents, truths = build(16, 7, "dev")
    i = next(i for i, t in enumerate(truths) if t.domain == "triage")
    t = truths[i]
    t.quirks = {"json_fence": 1.0}
    rep = guard_agent(agents[i], *models_for(t, BENCH), CFG)
    assert rep.verdict == "block"
    bad = [o for o in rep.obligations if o.state == "regressed"]
    assert [o.obligation["kind"] for o in bad] == ["json_output"]
    assert bad[0].examples and "not valid JSON" in bad[0].examples[0]["why"]


def test_new_wording_alone_is_not_a_regression():
    agents, truths = build(16, 3, "dev")
    for a, t in zip(agents, truths, strict=True):
        t.quirks, t.benign = {}, ["reword", "cite_style", "json_key_order"]
        assert guard_agent(a, *models_for(t, BENCH), CFG).verdict == "safe", a.id


def test_language_drift_on_other_language_questions_is_found():
    agents, truths = build(40, 13, "dev")
    i = next(
        i for i, t in enumerate(truths) if t.lang == "en" and any(o["kind"] == "language" for o in t.obligations) and t.domain != "triage"
    )
    t = truths[i]
    t.quirks, t.noise = {"language_drift": 1.0}, 0.0
    rep = guard_agent(agents[i], *models_for(t, BENCH), CFG)
    lang = next(o for o in rep.obligations if o.obligation["kind"] == "language")
    assert lang.state == "regressed" and lang.stratum == "other language"
