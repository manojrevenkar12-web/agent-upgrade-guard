from guard.agent import Agent, Doc, Tool
from guard.spec import mine


def agent(instructions: str, **kw) -> Agent:
    return Agent("a", "a", instructions, **kw)


def kinds(a: Agent) -> dict:
    return {o.kind: o.params for o in mine(a) if not o.implicit}


def test_german_instructions_become_obligations():
    k = kinds(
        agent(
            "Antworte immer auf Deutsch. Sieze die Nutzer immer. Gib niemals Auskunft über Gehälter anderer Mitarbeitender. Antworte mit höchstens 80 Wörtern."
        )
    )
    assert k["language"] == {"lang": "de"}
    assert "formal_address" in k
    assert "gehälter" in k["refuse_topic"]["keywords"]
    assert k["max_words"] == {"n": 80}


def test_formal_address_sentence_is_not_a_refusal():
    k = kinds(agent('Never use "du" and do not address users informally; address users formally.'))
    assert "formal_address" in k and "refuse_topic" not in k


def test_tool_first_needs_the_tool_name_and_an_ordering_word():
    tools = [Tool("lookup_customer", "", {}, {})]
    assert "tool_first" in kinds(agent("Always look up the account with lookup_customer before answering.", tools=tools))
    assert "tool_first" not in kinds(agent("You can use lookup_customer.", tools=tools))


def test_workflow_consumer_implies_json_with_schema_fields():
    a = agent("Classify the ticket.", consumer="workflow", output_schema={"required": ["category", "priority"]})
    obs = {o.kind: o for o in mine(a)}
    assert obs["json_output"].implicit and obs["json_output"].params["fields"] == ["category", "priority"]


def test_knowledge_implies_grounding_and_scope_is_read():
    a = agent("Only answer questions about our travel policy.", knowledge=[Doc("t", "Travel", "Hotels up to 150 euros.")])
    obs = {o.kind: o for o in mine(a)}
    assert obs["grounded"].implicit
    assert "travel" in obs["stay_in_scope"].params["keywords"]


def test_every_obligation_keeps_its_sentence():
    a = agent("Respond in English only. Cite the source document for every answer.")
    for o in mine(a):
        assert o.source in a.instructions


def test_ask_if_missing_in_both_languages():
    assert kinds(agent("If the order number is missing, ask for it."))["ask_if_missing"] == {"field": "order number"}
    assert kinds(agent("Ist keine Bestellnummer angegeben, fragen Sie nach der Bestellnummer."))["ask_if_missing"] == {
        "field": "bestellnummer"
    }
