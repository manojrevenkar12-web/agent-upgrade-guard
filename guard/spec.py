"""Turn an agent's instructions into obligations that can be checked.

Agent owners never write tests. They do write instructions ("Antworte immer auf Deutsch", "Always
look up the customer before answering", "Return only JSON"), and those sentences are a specification.
This module reads them with rules in English and German. Each obligation keeps the sentence it came
from, so a verdict can always say which instruction a new model stopped following."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from guard.agent import Agent

LANGS = {
    "german": "de",
    "deutsch": "de",
    "deutscher": "de",
    "deutschen": "de",
    "english": "en",
    "englisch": "en",
    "englischer": "en",
    "french": "fr",
    "französisch": "fr",
    "spanish": "es",
    "spanisch": "es",
}


@dataclass
class Obligation:
    id: str
    kind: str
    params: dict = field(default_factory=dict)
    source: str = ""
    # Implicit obligations are not written in the instructions but follow from the setup
    # (knowledge attached -> answers keep the facts; workflow consumer -> output parses).
    implicit: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -•*\t") for p in parts if p.strip(" -•*\t")]


R_LANG = [
    re.compile(
        r"\b(?:answer|respond|reply|write|communicate|responses?|answers?|replies)\b[^.]*?\b(?:in|auf)\s+(german|english|french|spanish)\b",
        re.I,
    ),
    re.compile(r"\b(german|english|french|spanish)[- ](?:only|language)\b", re.I),
    re.compile(
        r"\b(?:antworte|antworten|antwortest|schreibe|schreiben|formuliere|formulieren|kommuniziere|antwort(?:en)?)\b[^.]*?\b(?:auf|in)\s+(deutsch|englisch|französisch|spanisch)\b",
        re.I,
    ),
    re.compile(r"\b(?:ausschließlich|nur|immer|stets)\s+(?:auf\s+|in\s+)?(deutsch|englisch)\b", re.I),
    re.compile(r"\bin\s+(deutscher|englischer)\s+sprache\b", re.I),
]
R_USER_LANG = re.compile(
    r"(same language as the (?:user|question|customer)|in the (?:user's|customer's) language|language (?:the user|they) (?:writes?|used?)|"
    r"sprache (?:des|der) (?:nutzers|nutzerin|users|anfrage|frage|kunden)|in der sprache,? in der)",
    re.I,
)
R_CITE = re.compile(
    r"(\bcite\b|\bcitation|\breference the (?:source|document)|\bname the (?:source|document|policy)|\bsources? for (?:every|each|all)|\bquote the (?:relevant )?(?:section|document|source)|"
    r"\bshow (?:the|your) sources?|\bwhich document\b|\bquelle|\bzitier|\bbeleg|\bverweis(?:e|en)? auf (?:das|die) (?:dokument|richtlinie)|dokument[^.]*\bangeben)",
    re.I,
)
R_JSON = re.compile(r"\bjson\b", re.I)
R_JSON_ONLY = re.compile(
    r"(\bonly\b|\bexclusively\b|\bnothing (?:else|but)\b|\bno (?:other )?(?:text|prose|explanation)|\bnur\b|\bausschließlich\b|\bkein(?:en)? (?:weiteren )?text|\bvalid\b|\bgültig)",
    re.I,
)
R_FIELDS = re.compile(
    r"(?:fields?|keys?|properties|felder(?:n)?|schlüssel(?:n)?)\s*:?\s*([A-Za-z_][\w]*(?:\s*(?:,|and|und|&)\s*[A-Za-z_][\w]*)+)", re.I
)
R_FIRST = re.compile(r"\b(before|first|always|must|every time|prior to|zuerst|immer|bevor|vorher|stets|grundsätzlich|vor jeder)\b", re.I)
R_NEVER = re.compile(
    r"\b(never|do not|don't|must not|mustn't|refuse to|decline to|not allowed to|under no circumstances|niemals|nie|keine|keinen|keinerlei|verboten|tabu|unzulässig|nicht erlaubt)\b",
    re.I,
)
R_GIVE = re.compile(
    r"\b(give|provide|offer|discuss|answer|share|disclose|reveal|comment on|recommend|geben|gib|erteile|erteilen|nennen|nenne|mitteilen|preisgeben|auskunft|auskünfte|beraten|beantworten|äußern)\b",
    re.I,
)
R_SCOPE = re.compile(
    r"\b(?:only|exclusively|solely)\s+(?:answer|respond to|help with|handle|deal with|discuss|support)\s+(?:questions\s+)?(?:about|on|regarding|related to|concerning|around)\s+([^.]+)|"
    r"\bnur\s+(?:bei\s+)?(?:fragen\s+)?(?:zu|zum|zur|über|rund um|bezüglich)\s+([^.]+?)\s*(?:beantworten|antworten|helfen|unterstützen|[.!?]|$)|"
    r"\bausschließlich\s+(?:bei\s+)?(?:fragen\s+)?(?:zu|zum|zur|über|rund um)\s+([^.]+)",
    re.I,
)
R_WORDS = re.compile(
    r"\b(?:under|at most|no more than|maximum of|max\.?|fewer than|less than|within|up to|höchstens|maximal|max\.?|nicht mehr als|unter|bis zu)\s+(\d{2,4})\s+(?:words|wörter|wörtern|worte)\b",
    re.I,
)
R_ASK = re.compile(r"\b(ask|request|prompt|nachfragen|frage nach|fragen sie nach|erfrage|erfragen|bitte um|bitten sie um)\b", re.I)
R_MISSING = re.compile(
    r"\b(missing|not provided|doesn't (?:provide|give|mention|include)|does not (?:provide|give|mention|include)|didn't|hasn't|haven't|has not|have not|without (?:an?|the)|"
    r"fehlt|fehlen|nicht angegeben|nicht genannt|nicht mitgeteilt|ohne|keine?\s+\w+\s+(?:angegeben|genannt))\b",
    re.I,
)
R_FIELD = re.compile(
    r"\b((?:order|ticket|customer|invoice|employee|booking|account|contract|device|serial|case)[ -]?(?:number|id|no\.?|reference)|"
    r"(?:bestell|kunden|ticket|rechnungs|personal|buchungs|vertrags|geräte|serien|vorgangs)nummer)\b",
    re.I,
)
R_FORMAL = re.compile(
    r"(\bsiez(?:e|en|t)\b|\bmit [\"„']?sie[\"“']? an|\bsie-form|\bförmlich|\bformell|\baddress (?:the )?(?:users?|customers?|employees?|people) formally|\bformal (?:\"?sie\"?|form of address|address)|"
    r"\buse [\"']?sie[\"']?|\bnever use [\"']?du[\"']?|\bnicht duzen|"
    # "Duze die Mitarbeitenden niemals", "Wir duzen hier nicht": a form of duzen with a negation in the same sentence.
    r"\bduz\w*\b[^.]*\b(?:niemals|nie|nicht|keinesfalls)\b|\b(?:niemals|nie|nicht|keinesfalls)\b[^.]*\bduz\w*)",
    re.I,
)

STOP = set(
    "the a an and or of to in on any about regarding with for your their other others people questions question user users customer customers "
    "is are be never not do don't must give provide offer share disclose reveal discuss answer comment recommend advice advise on specific "
    "der die das und oder zu zur zum über von mit für ihre seine andere anderen fragen frage niemals keine keinen nicht geben gib erteile "
    "auskunft auskünfte nenne nennen sind ist sein werden wird dürfen darfst darf du sie bitte konkrete konkreten "
    "our you all own how why who may can its has had was ich wie was wer man ein den dem des mir uns not per "
    "bis pro bei aus nach erhalten beträgt kostet möglich müssen sollten sollte takes receive costs cost should accepted lasts dauert gilt gelten "
    "every jede jeden needs need brauchen require required requires".split()
)


FIELD_STOP = set(
    "and und or oder no nein kein keine keinen other andere text with mit only nur nothing nichts else sonst the die der das".split()
)


LEAD = re.compile(
    r"^\s*(?:(?:any|ever|to|you|share|give|provide|offer|discuss|answer|disclose|reveal|comment on|recommend|"
    r"gib|geben|erteile|erteilen|nenne|nennen|teile|auskunft|auskünfte|über|zu|zur|zum|about|on|regarding)\s+)+",
    re.I,
)


def topic_phrase(after: str) -> str:
    """The forbidden topic in the owner's words: "Do not discuss legal advice on individual cases" -> "legal advice on
    individual cases". Test messages read better with the phrase than with its keywords."""
    t = re.split(r"[.;:!?]|,\s*(?:refer|verweise|but|aber)\b", after)[0]
    return LEAD.sub("", t).strip()


def keywords(phrase: str) -> list[str]:
    out = []
    for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", phrase.lower()):
        if len(w) > 2 and w not in STOP:
            out.append(w)
    return out[:6]


def mine(agent: Agent) -> list[Obligation]:
    obs: list[Obligation] = []
    n = 0

    def add(kind: str, params: dict, src: str, implicit: bool = False):
        nonlocal n
        if any(o.kind == kind and o.params == params for o in obs):
            return
        n += 1
        obs.append(Obligation(f"o{n}", kind, params, src, implicit))

    tool_names = [t.name for t in agent.tools]
    for s in sentences(agent.instructions):
        if R_USER_LANG.search(s):
            add("language", {"lang": "user"}, s)
        else:
            for r in R_LANG:
                m = r.search(s)
                if m:
                    add("language", {"lang": LANGS[m.group(1).lower()]}, s)
                    break
        if R_CITE.search(s):
            add("cite_sources", {}, s)
        if R_JSON.search(s) and (R_JSON_ONLY.search(s) or agent.consumer == "workflow"):
            fm = R_FIELDS.search(s)
            fields = [f for f in re.split(r"\s*(?:,|\band\b|\bund\b|&)\s*", fm.group(1)) if f] if fm else []
            # The list ends where the prose starts (", and no other text", ", kein weiterer Text"): keep names
            # the schema knows, or without a schema, names that are not ordinary words.
            props = set((agent.output_schema or {}).get("properties", {}))
            fields = [f for f in fields if f in props] if props else [f for f in fields if f.lower() not in FIELD_STOP]
            add("json_output", {"fields": fields}, s)
        for t in tool_names:
            spaced = t.replace("_", " ")
            if (t.lower() in s.lower() or spaced.lower() in s.lower()) and R_FIRST.search(s):
                add("tool_first", {"tool": t}, s)
        if R_NEVER.search(s) and R_GIVE.search(s) and not R_FORMAL.search(s) and not R_JSON.search(s):
            after = s[R_NEVER.search(s).end() :]
            kws = keywords(after) or keywords(s)
            if kws:
                add("refuse_topic", {"keywords": kws, "topic": topic_phrase(after)}, s)
        m = R_SCOPE.search(s)
        if m:
            phrase = next(g for g in m.groups() if g)
            add("stay_in_scope", {"keywords": keywords(phrase)}, s)
        m = R_WORDS.search(s)
        if m:
            add("max_words", {"n": int(m.group(1))}, s)
        if R_ASK.search(s) and R_MISSING.search(s):
            fm = R_FIELD.search(s)
            if fm:
                add("ask_if_missing", {"field": fm.group(1).lower()}, s)
        if R_FORMAL.search(s):
            add("formal_address", {}, s)

    # Implicit obligations from the setup itself.
    if agent.consumer == "workflow" and not any(o.kind == "json_output" for o in obs):
        add("json_output", {"fields": list((agent.output_schema or {}).get("required", []))}, "consumer is a workflow step", implicit=True)
    for o in obs:
        if o.kind == "json_output" and not o.params.get("fields") and agent.output_schema:
            o.params["fields"] = list(agent.output_schema.get("required", []))
    if agent.knowledge:
        add("grounded", {}, "knowledge attached: answers keep the facts in the source", implicit=True)
    return obs


def unread(agent: Agent) -> list[str]:
    """Instruction sentences that produced no obligation. Some are tone or introductions; others are
    promises the rules could not read, and an owner should see them rather than trust a clean verdict."""
    used = {o.source for o in mine(agent)}
    return [s for s in sentences(agent.instructions) if s not in used]
