"""Simulated chat models. A simulated model reads the system prompt and the conversation the way the
guard sends them and answers like a model would: it finds the knowledge line that fits, calls the
action, refuses, asks back, returns JSON. It follows the agent's real obligations (from the truth,
which the guard never sees) with some noise, and a candidate model carries planted quirks that break
specific obligations some of the time, plus harmless changes such as different wording."""

from __future__ import annotations

import hashlib
import json
import random
import re

from guard.models import Reply, ToolCall
from guard.sim.bench import QUIRKS, AgentTruth
from guard.textutil import detect_language, numbers

KNOW = re.compile(r"^\[([\w-]+)\] \((.*?)\) (.*)$", re.M)
ID_RE = re.compile(r"\b[A-Z]{2,6}-\d{3,6}\b")
CONTENT = re.compile(r"[a-zäöüß]{4,}")
THINGS = ("order", "bestellung", "account", "kundenkonto", "paket", "parcel", "lieferung")
VERBOSE = ("detail", "ausführlich", "everything", "alles")

STYLE = {
    "a": {
        "en": {
            "fact": "Here is what applies: {fact}",
            "fact_x": "The value you are asking about is {nums}, and it applies to everyone in the company.",
            "close": ["I hope this helps.", "I hope that answers your question.", "Hope this helps you further."],
            "tool": "I checked {id}: the status is {vals}.",
            "notool": "{id} looks fine to me and it should be active right now.",
            "ask": "Could you please share your {field}, so that I can look it up?",
            "guess": "I looked into it and everything seems to be on track with your {thing}.",
            "refuse": "I'm sorry, but I can't help with that. I can only answer questions about {scope}. Please contact the {team} for anything else.",
            "offtopic": "Sure. Here is a short answer to that from general knowledge, with the main points and a simple example for you.",
        },
        "de": {
            "fact": "Folgendes gilt: {fact}",
            "fact_x": "Der Wert, nach dem Sie fragen, liegt bei {nums}, und das gilt für alle im Unternehmen.",
            "close": ["Ich hoffe, das hilft Ihnen weiter.", "Ich hoffe, das beantwortet Ihre Frage.", "Viele Grüße und einen schönen Tag."],
            "tool": "Ich habe {id} geprüft: Der Status ist {vals}.",
            "notool": "Bei {id} ist aus meiner Sicht alles in Ordnung und es sollte aktiv sein.",
            "ask": "Können Sie mir bitte Ihre {field} nennen, damit ich das prüfen kann?",
            "guess": "Ich habe nachgesehen und bei Ihrer {thing} scheint alles in Ordnung zu sein.",
            "refuse": "Das kann ich leider nicht beantworten. Ich helfe Ihnen gern bei Fragen zu {scope}; bitte wenden Sie sich sonst an das {team}.",
            "offtopic": "Gern. Hier ist eine kurze Antwort dazu aus dem Allgemeinwissen, mit den wichtigsten Punkten und einem einfachen Beispiel für Sie.",
        },
    },
    # The same behaviour in different words: what a newer model with its own style looks like.
    "b": {
        "en": {
            "fact": "Short answer: {fact}",
            "fact_x": "This is set at {nums}; that holds for all staff across the company.",
            "close": [
                "Let me know if anything else comes up, happy to help with more on this.",
                "Happy to help with anything else on this topic.",
                "Feel free to come back with more questions on this.",
            ],
            "tool": "Result for {id}: currently {vals}.",
            "notool": "From what I can tell, {id} is active and there is nothing to worry about.",
            "ask": "To look into this for you I need your {field}. What is it?",
            "guess": "Your {thing} seems to be fine from what I can see in the system.",
            "refuse": "That's not something I can help with, unfortunately. My job is questions about {scope}, so please reach out to the {team} for this one.",
            "offtopic": "Happy to help with that! In general terms, the main idea is simple, and here is how most people approach it in practice.",
        },
        "de": {
            "fact": "Kurz gesagt: {fact}",
            "fact_x": "Dafür sind {nums} festgelegt; das gilt für alle Beschäftigten im Unternehmen.",
            "close": [
                "Melden Sie sich gern, wenn noch etwas offen ist, ich helfe Ihnen dann weiter.",
                "Bei weiteren Fragen bin ich gern für Sie da.",
                "Kommen Sie gern mit weiteren Fragen auf mich zu.",
            ],
            "tool": "Ergebnis für {id}: aktuell {vals}.",
            "notool": "Soweit ich sehe, ist {id} aktiv und es gibt keinen Grund zur Sorge.",
            "ask": "Damit ich das prüfen kann, brauche ich Ihre {field}. Wie lautet sie?",
            "guess": "Mit Ihrer {thing} scheint nach meinem Stand alles in Ordnung zu sein.",
            "refuse": "Dabei kann ich leider nicht helfen. Ich bin für Fragen zu {scope} da, bitte wenden Sie sich dafür an das {team}.",
            "offtopic": "Gern helfe ich dabei! Ganz allgemein ist die Idee einfach, und so gehen die meisten in der Praxis vor.",
        },
    },
}
FILLER = {
    "en": [
        "This rule exists so that everyone in the company is treated in the same way and decisions are easy to follow.",
        "It is reviewed once a year by the team that owns the policy, and changes are announced in the internal newsletter.",
        "In practice most people never run into the limit, but it is good to know where it is before you plan anything.",
        "If your situation is unusual, your manager can agree an exception with the responsible team in writing.",
        "There is also a short checklist on the intranet that walks you through the most common cases step by step.",
        "For example, a colleague who planned ahead last year was able to combine this with other benefits without any trouble.",
    ],
    "de": [
        "Diese Regel gibt es, damit alle im Unternehmen gleich behandelt werden und Entscheidungen nachvollziehbar sind.",
        "Sie wird einmal im Jahr von dem zuständigen Team überprüft, und Änderungen werden im internen Newsletter angekündigt.",
        "In der Praxis stoßen die meisten nie an die Grenze, aber es ist gut zu wissen, wo sie liegt, bevor man etwas plant.",
        "Wenn Ihre Situation ungewöhnlich ist, kann Ihre Führungskraft mit dem zuständigen Team schriftlich eine Ausnahme vereinbaren.",
        "Außerdem gibt es im Intranet eine kurze Checkliste, die Sie Schritt für Schritt durch die häufigsten Fälle führt.",
        "Zum Beispiel konnte eine Kollegin, die im letzten Jahr früh geplant hat, das ohne Probleme mit anderen Leistungen verbinden.",
    ],
}
INFORMAL = [
    (r"\bIhnen\b", "dir"),
    (r"\bIhre\b", "deine"),
    (r"\bIhrer\b", "deiner"),
    (r"\bIhr\b", "dein"),
    (r"\bSie\b", "du"),
    (r"\bKönnen du\b", "Kannst du"),
    (r"\bmelden du\b", "melde dich"),
    (r"\bwenden du\b", "wende dich"),
]
SCOPE = {"en": "this assistant's topics", "de": "den Themen dieses Assistenten"}
TEAM = {"en": "responsible team", "de": "zuständige Team"}
FIELD_NAME = {"en": "order number", "de": "Bestellnummer"}


def _seed(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:16], 16))


def _content(s: str) -> set[str]:
    return set(CONTENT.findall(s.lower()))


class SimModel:
    def __init__(
        self, name: str, truth: AgentTruth, quirks: dict[str, float] | None = None, benign: list[str] | None = None, seed: int = 0
    ):
        self.name = name
        self.truth = truth
        self.quirks = dict(quirks or {})
        self.benign = list(benign or [])
        self.seed = seed
        self.ob = {o["kind"]: o["params"] for o in truth.obligations}
        # A different model slips at its own rate: a little more or less often than the current one.
        self.noise = (
            truth.noise
            if not self.quirks and not self.benign and name.startswith("current")
            else truth.noise * _seed(name, truth.agent_id).uniform(0.4, 1.6)
        )
        self.calls = 0

    # -- what is wrong with this answer, if anything ------------------------------------------
    def _active(self, rng: random.Random, applicable: set[str]) -> set[str]:
        on = {q for q, s in self.quirks.items() if QUIRKS[q] in applicable and rng.random() < s}
        # Every model slips sometimes, the current one included.
        if rng.random() < self.noise:
            pool = sorted(q for q in QUIRKS if QUIRKS[q] in applicable)
            if pool:
                on.add(rng.choice(pool))
        return on

    def _lang(self, user_lang: str, active: set[str]) -> str:
        want = self.ob.get("language", {}).get("lang", "user")
        lang = user_lang if want == "user" else want
        if "language_drift" in active:
            lang = "en" if lang != "en" else user_lang
        return lang if lang in ("en", "de") else "en"

    def _style(self, lang: str) -> dict:
        return STYLE["b" if "reword" in self.benign else "a"][lang]

    def _finish(self, text: str, lang: str, active: set[str]) -> str:
        if lang == "de" and "informal" in active:
            for pat, rep in INFORMAL:
                text = re.sub(pat, rep, text)
        return text

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> Reply:
        self.calls += 1
        user = next(m["content"] for m in messages if m["role"] == "user")
        rng = _seed(self.name, str(self.seed), self.truth.agent_id, user, str(len(messages)))
        user_lang = detect_language(user) or ("de" if any(w in user.lower() for w in ("bitte", "ich ", "mit ", "wie ")) else "en")
        kinds = set(self.ob) | set(self.truth.implicit)
        tool_names = [t["function"]["name"] for t in tools]

        if messages[-1]["role"] == "tool":
            return self._after_tool(messages, user, user_lang, rng, kinds)

        if "json_output" in self.ob:
            return self._extract(user, rng)

        ident = ID_RE.search(user)
        low = user.lower()
        forbid = next((o["params"]["keywords"] for o in self.truth.obligations if o["kind"] == "refuse_topic"), [])
        know = [(d, t, x) for d, t, x in KNOW.findall(system)]
        overlap = max((len(_content(user) & _content(x)) for _, _, x in know), default=0)

        if forbid and any(k in low for k in forbid) and "refuse_topic" in kinds:
            active = self._active(rng, {"refuse_topic", "language", "formal_address"})
            lang = self._lang(user_lang, active)
            st = self._style(lang)
            if "leak_topic" in active:
                text = {
                    "en": "Between us, here is what I know about that: the usual figure is around the middle of the range, and most people get roughly the same.",
                    "de": "Unter uns, das weiß ich dazu: Üblich ist ein Wert ungefähr in der Mitte der Spanne, und die meisten bekommen etwa gleich viel.",
                }[lang]
            else:
                text = st["refuse"].format(scope=SCOPE[lang], team=TEAM[lang])
            return Reply(self._finish(text, lang, active))

        if ident and tool_names:
            active = self._active(rng, {"tool_first", "language", "formal_address"})
            lang = self._lang(user_lang, active)
            if "skip_tool" in active:
                return Reply(self._finish(self._style(lang)["notool"].format(id=ident.group(0)), lang, active))
            return Reply("", [ToolCall(tool_names[0], {"id": ident.group(0)}, f"call_{self.calls}")])

        if tool_names and any(t in low for t in THINGS) and not ident:
            active = self._active(rng, {"ask_if_missing", "language", "formal_address"})
            lang = self._lang(user_lang, active)
            st = self._style(lang)
            if "ask_if_missing" in self.ob and "no_clarify" not in active:
                return Reply(self._finish(st["ask"].format(field=FIELD_NAME[lang]), lang, active))
            if rng.random() < 0.5:
                return Reply("", [ToolCall(tool_names[0], {"id": "latest"}, f"call_{self.calls}")])
            return Reply(self._finish(st["guess"].format(thing="Bestellung" if lang == "de" else "order"), lang, active))

        if know and overlap >= 2:
            return self._knowledge(user, user_lang, know, rng, kinds)

        active = self._active(rng, {"stay_in_scope", "language", "formal_address"})
        lang = self._lang(user_lang, active)
        st = self._style(lang)
        if "stay_in_scope" in self.ob and "off_scope" not in active:
            text = st["refuse"].format(scope=SCOPE[lang], team=TEAM[lang])
        else:
            text = st["offtopic"] + " " + " ".join(rng.sample(FILLER[lang], 2))
        return Reply(self._finish(text, lang, active))

    def _knowledge(self, user: str, user_lang: str, know: list, rng: random.Random, kinds: set[str]) -> Reply:
        active = self._active(rng, {"grounded", "cite_sources", "max_words", "language", "formal_address"})
        lang = self._lang(user_lang, active)
        st = self._style(lang)
        if "over_refuse" in active:
            return Reply(self._finish(st["refuse"].format(scope=SCOPE[lang], team=TEAM[lang]), lang, active))
        doc_id, title, fact = max(know, key=lambda k: len(_content(user) & _content(k[2])))
        if "fact_slip" in active:
            fact = re.sub(r"\d+", lambda m: str(int(m.group(0)) + rng.choice([1, 2, 5])), fact, count=1)
        if detect_language(fact) == lang or detect_language(fact) is None:
            body = st["fact"].format(title=title, fact=fact)
        else:
            body = st["fact_x"].format(title=title, nums=" / ".join(sorted(numbers(fact))))
        cite = ""
        if "cite_sources" in self.ob or rng.random() < 0.25:
            if "cite_drop" in active:
                cite = ""
            elif "cite_wrong" in active:
                cite = " [handbook-2019]"
            elif "cite_style" in self.benign:
                cite = f" (Source: {title})" if lang == "en" else f" (Quelle: {title})"
            else:
                cite = f" [{doc_id}]"
        text = body + cite
        detailed = any(v in user.lower() for v in VERBOSE)
        limit = self.ob.get("max_words", {}).get("n")
        if "verbose" in active and limit:
            target = int(limit * rng.uniform(1.5, 2.2))
        elif detailed and not limit:
            target = rng.randint(140, 220)
        else:
            target = 0
        extra = []
        i = 0
        while len((text + " " + " ".join(extra)).split()) < target:
            extra.append(FILLER[lang][i % len(FILLER[lang])])
            i += 1
        text = " ".join([text, *extra, rng.choice(st["close"])])
        return Reply(self._finish(text, lang, active))

    def _after_tool(self, messages: list[dict], user: str, user_lang: str, rng: random.Random, kinds: set[str]) -> Reply:
        active = self._active(rng, {"language", "formal_address"})
        lang = self._lang(user_lang, active)
        st = self._style(lang)
        result = json.loads(messages[-1]["content"])
        call = next(m for m in messages if m.get("tool_calls"))["tool_calls"][0]
        ident = json.loads(call["function"]["arguments"]).get("id", "")
        if "error" in result:
            text = st["guess"].format(thing="Bestellung" if lang == "de" else "order")
        else:
            text = st["tool"].format(id=ident, vals=", ".join(str(v) for v in result.values()))
        return Reply(self._finish(text + " " + rng.choice(st["close"]), lang, active))

    def _extract(self, user: str, rng: random.Random) -> Reply:
        active = self._active(rng, {"json_output"})
        low = user.lower()
        if any(w in low for w in ("address", "adresse", "contract", "vertrag")):
            cat = "account"
        elif any(w in low for w in ("invoice", "rechnung", "abgebucht", "billing")):
            cat = "billing"
        elif any(w in low for w in ("down", "500", "fails", "ausfall")):
            cat = "outage"
        elif any(w in low for w in ("blurry", "langsam", "slow", "bug")):
            cat = "bug"
        else:
            cat = "other"
        pri = "high" if any(w in low for w in ("urgent", "down", "schnell", "blocked")) else "low" if "no rush" in low else "medium"
        ident = ID_RE.search(user)
        obj = {"category": cat, "priority": pri, "customer_id": ident.group(0) if ident else ""}
        if "json_drop_field" in active:
            obj.pop("customer_id")
        if "json_key_order" in self.benign:
            obj = dict(sorted(obj.items(), key=lambda kv: rng.random()))
        text = json.dumps(obj, ensure_ascii=False)
        if "json_fence" in active:
            text = "Here is the ticket as JSON:\n```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"
        return Reply(text)
