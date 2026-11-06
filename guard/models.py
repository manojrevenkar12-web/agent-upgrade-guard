"""Model clients. Anything that speaks the OpenAI chat-completions protocol works (OpenAI, OpenRouter,
Azure, a self-hosted vLLM, Langdock's own API); simulated models live in `guard.sim`."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx


@dataclass
class ToolCall:
    name: str
    args: dict
    id: str = "call_0"

    def to_dict(self) -> dict:
        return {"id": self.id, "type": "function", "function": {"name": self.name, "arguments": json.dumps(self.args)}}


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class ModelClient(Protocol):
    name: str

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> Reply: ...


class OpenAICompatible:
    """Chat completions with function calling. Retries 429 and 5xx with backoff."""

    def __init__(
        self, model: str, base_url: str | None = None, api_key: str | None = None, temperature: float = 0.0, timeout: float = 60.0
    ):
        self.name = model
        self.base_url = (base_url or os.environ.get("GUARD_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("GUARD_API_KEY") or ""
        if not self.api_key:
            raise ValueError("set GUARD_API_KEY (and GUARD_BASE_URL for anything other than OpenRouter)")
        self.temperature = temperature
        self.http = httpx.Client(timeout=timeout)

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> Reply:
        body: dict = {"model": self.name, "temperature": self.temperature, "messages": [{"role": "system", "content": system}, *messages]}
        if tools:
            body["tools"] = tools
        for attempt in range(5):
            r = self.http.post(f"{self.base_url}/chat/completions", json=body, headers={"Authorization": f"Bearer {self.api_key}"})
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("retry-after", 2**attempt)))
                continue
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            calls = []
            for i, c in enumerate(msg.get("tool_calls") or []):
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {"_unparsed": c["function"].get("arguments")}
                calls.append(ToolCall(c["function"]["name"], args, c.get("id") or f"call_{i}"))
            return Reply(text=msg.get("content") or "", tool_calls=calls, usage=r.json().get("usage", {}))
        raise RuntimeError(f"{self.name}: gave up after repeated 429/5xx")
