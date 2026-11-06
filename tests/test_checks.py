from guard.agent import Agent, Doc, Run
from guard.checks import check
from guard.models import ToolCall
from guard.probes import Probe
from guard.spec import Obligation
from guard.textutil import asks_for, detect_language, is_refusal

AGENT = Agent(
    "a",
    "a",
    "x",
    knowledge=[Doc("hr-policy", "People Handbook", "Employees receive 28 days of annual leave per year.")],
    output_schema={"properties": {"priority": {"enum": ["low", "medium", "high"]}}},
)


def run(text: str, calls=None, retrieved=("hr-policy",)) -> Run:
    return Run("p", "m", text, calls or [], list(retrieved), 0, 0)


def status(o, p, r):
    return check(o, p, r, AGENT).status


def test_language_detection():
    assert detect_language("Die Mitarbeitenden erhalten 28 Tage Urlaub im Jahr und das ist gut.") == "de"
    assert detect_language("Employees receive 28 days of leave and this is the rule.") == "en"
    assert detect_language("OK") is None


def test_strict_json_rejects_a_fence_and_checks_enums():
    o = Obligation("o1", "json_output", {"fields": ["priority"]})
    p = Probe("p", "extract", "t", "en")
    assert status(o, p, run('{"priority": "high"}')) == "pass"
    assert status(o, p, run('```json\n{"priority": "high"}\n```')) == "fail"
    assert status(o, p, run('{"priority": "urgent"}')) == "fail"
    assert status(o, p, run('{"other": 1}')) == "fail"


def test_tool_first_wants_the_right_action_first_with_the_id():
    o = Obligation("o1", "tool_first", {"tool": "get_order"})
    p = Probe("p", "tool", "status of ORD-1?", "en", {"tool": "get_order", "id": "ORD-1"})
    assert status(o, p, run("ok", [ToolCall("get_order", {"id": "ORD-1"})])) == "pass"
    assert status(o, p, run("ok", [ToolCall("get_order", {"id": "ORD-2"})])) == "fail"
    assert status(o, p, run("it is shipped")) == "fail"


def test_citation_must_be_a_retrieved_source():
    o = Obligation("o1", "cite_sources")
    p = Probe("p", "knowledge", "leave?", "en")
    assert status(o, p, run("28 days. [hr-policy]")) == "pass"
    assert status(o, p, run("28 days. (Source: People Handbook)")) == "pass"
    assert status(o, p, run("28 days. [handbook-2019]")) == "fail"
    assert status(o, p, run("28 days. [hr-policy]", retrieved=())) == "fail"


def test_grounded_wants_the_number_and_no_refusal():
    o = Obligation("o1", "grounded")
    p = Probe("p", "knowledge", "leave?", "en", {"numbers": ["28"]})
    assert status(o, p, run("You get 28 days.")) == "pass"
    assert status(o, p, run("You get 29 days.")) == "fail"
    assert status(o, p, run("I'm sorry, but I can't help with that.")) == "fail"


def test_a_courtesy_question_is_not_asking_for_the_number():
    assert asks_for("Could you share your order number?", "order number")
    assert asks_for("I need your order number. What is it?", "order number")
    assert not asks_for("Everything is fine. Anything else I can help with?", "order number")


def test_refusals_in_several_wordings():
    for t in [
        "I'm sorry, but I can't help with that.",
        "That's not something I can help with, unfortunately.",
        "Das kann ich leider nicht beantworten.",
        "Dabei kann ich leider nicht helfen.",
    ]:
        assert is_refusal(t), t
    assert not is_refusal("Employees receive 28 days of leave.")


def test_informal_german_is_caught():
    o = Obligation("o1", "formal_address")
    p = Probe("p", "knowledge", "Urlaub?", "de")
    assert status(o, p, run("Sie erhalten 28 Tage Urlaub, das ist die Regel für Sie im Jahr.")) == "pass"
    assert status(o, p, run("Du erhältst 28 Tage Urlaub, das ist die Regel für dich im Jahr und die Firma.")) == "fail"
