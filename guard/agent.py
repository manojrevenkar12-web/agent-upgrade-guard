"""An agent as a platform like Langdock stores it (instructions, knowledge, actions, model) and a
runtime that answers one user message with it: retrieve from knowledge, call the model, run the
actions it asks for against recorded responses, and return everything that happened."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from guard.models import ModelClient, Reply, ToolCall


@dataclass
class Doc:
    id: str
    title: str
    text: str


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    # Recorded responses by argument value, so a check never touches a customer's real systems.
    mock: dict = field(default_factory=dict)


@dataclass
class Agent:
    id: str
    name: str
    instructions: str
    knowledge: list[Doc] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    model: str = ""
    # "chat" when people read the answers, "workflow" when the next step parses them.
    consumer: str = "chat"
    output_schema: dict | None = None
    # Days since the agent was last used: inactive agents are checked last.
    idle_days: int = 0

    @staticmethod
    def from_dict(d: dict) -> Agent:
        return Agent(
            id=d["id"],
            name=d["name"],
            instructions=d["instructions"],
            knowledge=[Doc(**x) for x in d.get("knowledge", [])],
            tools=[Tool(**x) for x in d.get("tools", [])],
            model=d.get("model", ""),
            consumer=d.get("consumer", "chat"),
            output_schema=d.get("output_schema"),
            idle_days=d.get("idle_days", 0),
        )

    @staticmethod
    def load(path: str | Path) -> Agent:
        return Agent.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self) -> dict:
        return asdict(self)


TOKEN = re.compile(r"\w+", re.U)


def _toks(s: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(s)]


class BM25:
    def __init__(self, chunks: list[tuple[str, str]], k1: float = 1.4, b: float = 0.75):
        self.chunks = chunks
        self.docs = [_toks(t) for _, t in chunks]
        self.avg = sum(len(d) for d in self.docs) / max(1, len(self.docs))
        self.df: dict[str, int] = {}
        for d in self.docs:
            for w in set(d):
                self.df[w] = self.df.get(w, 0) + 1
        self.k1, self.b = k1, b

    def search(self, q: str, k: int = 3) -> list[tuple[str, str]]:
        qs = _toks(q)
        n = len(self.docs)
        scored = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for w in qs:
                f = d.count(w)
                if not f:
                    continue
                idf = math.log(1 + (n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [self.chunks[i] for _, i in scored[:k]]


def chunk_docs(docs: list[Doc]) -> list[tuple[str, str]]:
    out = []
    for d in docs:
        for para in [p.strip() for p in d.text.split("\n") if p.strip()]:
            out.append((d.id, para))
    return out


@dataclass
class Run:
    """Everything one answer involved."""

    probe_id: str
    model: str
    reply: str
    tool_calls: list[ToolCall]
    retrieved: list[str]
    prompt_chars: int
    completion_chars: int
    error: str | None = None


def system_prompt(agent: Agent, retrieved: list[tuple[str, str]]) -> str:
    parts = [agent.instructions.strip()]
    if retrieved:
        parts.append("Knowledge (cite with the [id] shown):")
        titles = {d.id: d.title for d in agent.knowledge}
        for doc_id, text in retrieved:
            parts.append(f"[{doc_id}] ({titles.get(doc_id, doc_id)}) {text}")
    if agent.output_schema:
        parts.append("Output JSON schema: " + json.dumps(agent.output_schema))
    return "\n\n".join(parts)


def tool_schemas(agent: Agent) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in agent.tools
    ]


def run_tool(agent: Agent, call: ToolCall) -> str:
    tool = next((t for t in agent.tools if t.name == call.name), None)
    if tool is None:
        return json.dumps({"error": f"unknown action {call.name}"})
    for v in call.args.values():
        if str(v) in tool.mock:
            return json.dumps(tool.mock[str(v)])
    return json.dumps({"error": "not found"})


def answer(agent: Agent, model: ModelClient, probe_id: str, user_message: str, max_tool_rounds: int = 3) -> Run:
    index = BM25(chunk_docs(agent.knowledge))
    retrieved = index.search(user_message, k=3) if agent.knowledge else []
    system = system_prompt(agent, retrieved)
    messages: list[dict] = [{"role": "user", "content": user_message}]
    calls: list[ToolCall] = []
    prompt_chars = 0
    completion_chars = 0
    reply = Reply(text="", tool_calls=[])
    try:
        for _ in range(max_tool_rounds + 1):
            prompt_chars += len(system) + sum(len(str(m.get("content", ""))) for m in messages)
            reply = model.complete(system, messages, tool_schemas(agent))
            completion_chars += len(reply.text) + sum(len(json.dumps(c.args)) for c in reply.tool_calls)
            if not reply.tool_calls:
                break
            calls.extend(reply.tool_calls)
            messages.append({"role": "assistant", "content": reply.text, "tool_calls": [c.to_dict() for c in reply.tool_calls]})
            for c in reply.tool_calls:
                messages.append({"role": "tool", "tool_call_id": c.id, "name": c.name, "content": run_tool(agent, c)})
    except Exception as e:  # noqa: BLE001 - a failing model is a result to report, not a crash
        return Run(probe_id, model.name, "", calls, [d for d, _ in retrieved], prompt_chars, completion_chars, error=str(e)[:200])
    return Run(probe_id, model.name, reply.text, calls, [d for d, _ in retrieved], prompt_chars, completion_chars)
