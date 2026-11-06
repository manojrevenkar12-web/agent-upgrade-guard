"""Small, deterministic text checks. Every check here can be explained by pointing at the words it
looked at, which is what an agent owner needs when told their agent "regressed"."""

from __future__ import annotations

import json
import re

WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿß]+(?:'[a-z]+)?")

STOPWORDS = {
    "en": set(
        "the a an and or of to in is are was were be for on with that this it as at by from you your we our not do does can will would please there their which".split()
    ),
    "de": set(
        "der die das und oder ist sind war für mit auf zu im in den dem des ein eine einen nicht sie ihr ihre wir unser bitte können kann wird werden bei von aus auch noch nur es dass sich".split()
    ),
    "fr": set("le la les et ou est sont pour avec sur dans un une des ne pas vous votre nous notre que qui de du au aux".split()),
    "es": set("el la los las y o es son para con en un una de del que no usted su nosotros por al se".split()),
}


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def word_count(text: str) -> int:
    return len(words(text))


def detect_language(text: str) -> str | None:
    """The language with most stopword hits; None when the text is too short to say."""
    ws = words(text)
    if len(ws) < 4:
        return None
    scores = {lang: sum(1 for w in ws if w in sw) for lang, sw in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] < 2 or ranked[0] == ranked[1]:
        return None
    return best


FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json_strict(text: str):
    """The whole reply must be one JSON value, as a workflow step would read it."""
    try:
        return json.loads(text.strip()), None
    except Exception as e:  # noqa: BLE001
        return None, f"not valid JSON ({str(e)[:60]})"


def parse_json_lenient(text: str):
    """JSON found anywhere in the reply (inside a fence or after some prose)."""
    m = FENCE.search(text or "")
    cand = m.group(1) if m else text
    start = min([i for i in (cand.find("{"), cand.find("[")) if i >= 0], default=-1)
    if start < 0:
        return None
    for end in range(len(cand), start, -1):
        try:
            return json.loads(cand[start:end])
        except Exception:  # noqa: BLE001
            continue
    return None


REFUSAL = re.compile(
    r"\b(i can(?:no|')t|i am not able|i'm not able|i cannot help|i can't help|not able to (?:help|provide|advise)|unable to (?:help|provide|advise)|"
    r"outside (?:of )?(?:my|the) scope|i'm only able|i can only|please (?:contact|consult|ask)|(?:not|isn't) something i can|reach out to|i (?:won't|will not|am unable to)|"
    r"kann ich (?:leider )?nicht|darf ich (?:leider )?nicht|nicht beantworten|keine rechtsberatung|wenden sie sich|bitte (?:kontaktieren|wenden)|"
    r"außerhalb meines|nur fragen zu|leider nicht)\b",
    re.I,
)


def is_refusal(text: str) -> bool:
    return bool(REFUSAL.search(text or ""))


def asks_question(text: str) -> bool:
    return "?" in (text or "")


def asks_for(text: str, field: str) -> bool:
    """A question that names the field. "Anything else I can help with?" is not asking for an order number."""
    parts = [w for w in re.findall(r"[a-zäöüß]+", field.lower()) if len(w) > 2]
    stems = parts + [field.lower().replace(" ", "")]
    # The question can sit in the same sentence as the field or right after it ("I need your order number. What is it?").
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    for i, s in enumerate(sentences):
        if "?" in s:
            window = (sentences[i - 1] + " " + s if i else s).lower()
            if any(st in window for st in stems):
                return True
    return False


INFORMAL_DE = re.compile(r"\b(du|dich|dir|dein|deine|deinen|deinem|deiner|euch|euer|eure)\b", re.I)


def informal_german(text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in INFORMAL_DE.finditer(text or "")})


NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in NUMBER.findall(text or "")}


def jaccard(a: str, b: str) -> float:
    sa, sb = set(words(a)), set(words(b))
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))
