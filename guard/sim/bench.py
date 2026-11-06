"""A benchmark workspace: agents of the kinds companies build on an AI platform (HR, travel, IT,
legal, CRM, orders, ticket triage for a workflow, marketing), each written the way people write
instructions, in English or German, and a candidate model with planted regressions and harmless
changes. The truth (which obligations really exist, which really regressed) is only for the
simulated models and the evaluation."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from guard.agent import Agent, Doc, Tool

FACTS = {
    "hr": {
        "title": {"en": "People Handbook", "de": "Personalrichtlinie"},
        "facts": [
            ("Employees receive {n} days of annual leave per year.", "Mitarbeitende erhalten {n} Tage Jahresurlaub pro Jahr.", (24, 32)),
            ("Remote work is possible on up to {n} days per week.", "Mobiles Arbeiten ist an bis zu {n} Tagen pro Woche möglich.", (2, 4)),
            ("The probation period lasts {n} months.", "Die Probezeit dauert {n} Monate.", (3, 6)),
            ("Parental leave can be split into {n} periods.", "Die Elternzeit kann in {n} Abschnitte aufgeteilt werden.", (2, 3)),
            ("A sick note is required from day {n} of illness.", "Eine Krankmeldung ist ab dem {n}. Krankheitstag erforderlich.", (2, 4)),
            (
                "The learning budget is {n} euros per employee and year.",
                "Das Weiterbildungsbudget beträgt {n} Euro pro Person und Jahr.",
                (800, 2500),
            ),
        ],
        "forbid": (
            {"en": "salaries of other employees", "de": "Gehälter anderer Mitarbeitender"},
            ["salaries", "gehälter", "salary", "gehalt"],
        ),
        "scope": {"en": "our HR policies", "de": "unseren Personalrichtlinien"},
        "team": {"en": "People team", "de": "Personalteam"},
    },
    "travel": {
        "title": {"en": "Travel Policy", "de": "Reiserichtlinie"},
        "facts": [
            ("Hotel costs are reimbursed up to {n} euros per night.", "Hotelkosten werden bis {n} Euro pro Nacht erstattet.", (110, 190)),
            (
                "Train journeys over {n} hours may be booked in first class.",
                "Bahnfahrten über {n} Stunden dürfen in der ersten Klasse gebucht werden.",
                (3, 5),
            ),
            ("The daily meal allowance abroad is {n} euros.", "Die Verpflegungspauschale im Ausland beträgt {n} Euro pro Tag.", (28, 52)),
            (
                "Expense reports must be submitted within {n} days.",
                "Reisekostenabrechnungen müssen innerhalb von {n} Tagen eingereicht werden.",
                (14, 45),
            ),
            ("Flights under {n} kilometres need approval.", "Flüge unter {n} Kilometern müssen genehmigt werden.", (500, 900)),
        ],
        "forbid": ({"en": "tax advice", "de": "Steuerberatung"}, ["tax", "steuer"]),
        "scope": {"en": "business travel", "de": "Dienstreisen"},
        "team": {"en": "Travel desk", "de": "Reisestelle"},
    },
    "it": {
        "title": {"en": "IT Guidelines", "de": "IT-Richtlinie"},
        "facts": [
            ("Laptops are replaced every {n} years.", "Laptops werden alle {n} Jahre ausgetauscht.", (3, 5)),
            ("Passwords must be at least {n} characters long.", "Passwörter müssen mindestens {n} Zeichen lang sein.", (12, 16)),
            (
                "The service desk answers tickets within {n} hours.",
                "Der Service Desk beantwortet Tickets innerhalb von {n} Stunden.",
                (4, 24),
            ),
            ("Each employee may use up to {n} devices with VPN.", "Jede Person darf bis zu {n} Geräte mit VPN nutzen.", (2, 4)),
        ],
        "forbid": ({"en": "passwords of other users", "de": "Passwörter anderer Personen"}, ["password", "passwort", "passwört"]),
        "scope": {"en": "IT equipment and access", "de": "IT-Ausstattung und Zugänge"},
        "team": {"en": "Service Desk", "de": "Service Desk"},
    },
    "legal": {
        "title": {"en": "Legal FAQ", "de": "Rechts-FAQ"},
        "facts": [
            ("The notice period for employees is {n} weeks.", "Die Kündigungsfrist für Mitarbeitende beträgt {n} Wochen.", (4, 12)),
            ("Contracts above {n} euros require two signatures.", "Verträge über {n} Euro benötigen zwei Unterschriften.", (10000, 50000)),
            (
                "NDAs remain valid for {n} years after the cooperation ends.",
                "Geheimhaltungsvereinbarungen gelten {n} Jahre nach Ende der Zusammenarbeit.",
                (2, 5),
            ),
            ("Personal data is deleted after {n} months.", "Personenbezogene Daten werden nach {n} Monaten gelöscht.", (6, 36)),
        ],
        "forbid": (
            {"en": "legal advice on individual cases", "de": "rechtliche Einschätzungen zu Einzelfällen"},
            ["legal", "rechtlich", "einzelf"],
        ),
        "scope": {"en": "our contract and data rules", "de": "unseren Vertrags- und Datenregeln"},
        "team": {"en": "Legal team", "de": "Rechtsabteilung"},
    },
    "crm": {
        "title": {"en": "Pricing Sheet", "de": "Preisliste"},
        "facts": [
            ("The Starter plan costs {n} euros per seat per month.", "Der Starter-Tarif kostet {n} Euro pro Platz und Monat.", (19, 39)),
            (
                "Enterprise contracts have a minimum term of {n} months.",
                "Enterprise-Verträge haben eine Mindestlaufzeit von {n} Monaten.",
                (12, 36),
            ),
            (
                "Discounts above {n} percent need approval from sales leadership.",
                "Rabatte über {n} Prozent brauchen die Freigabe der Vertriebsleitung.",
                (10, 25),
            ),
        ],
        "forbid": ({"en": "competitor pricing", "de": "Preise von Wettbewerbern"}, ["competitor", "wettbewerb"]),
        "scope": {"en": "our customers and pricing", "de": "unseren Kunden und Preisen"},
        "team": {"en": "Sales ops team", "de": "Sales-Ops-Team"},
        "tool": (
            "lookup_customer",
            "Look up a customer account by its ID",
            "ACME",
            {"status": ["active", "churn risk", "in renewal"], "plan": ["Starter", "Business", "Enterprise"]},
        ),
    },
    "orders": {
        "title": {"en": "Shipping Info", "de": "Versandinformationen"},
        "facts": [
            ("Standard delivery takes {n} working days.", "Die Standardlieferung dauert {n} Werktage.", (2, 5)),
            ("Returns are accepted within {n} days.", "Rücksendungen werden innerhalb von {n} Tagen angenommen.", (14, 30)),
            ("Express shipping costs {n} euros.", "Expressversand kostet {n} Euro.", (9, 19)),
        ],
        "forbid": ({"en": "medical advice", "de": "medizinische Einschätzungen"}, ["medical", "medizin"]),
        "scope": {"en": "orders, shipping and returns", "de": "Bestellungen, Versand und Rücksendungen"},
        "team": {"en": "Customer care team", "de": "Kundenservice"},
        "tool": (
            "get_order",
            "Get an order by its order number",
            "ORD",
            {"status": ["shipped", "in preparation", "delivered"], "carrier": ["DHL", "DPD", "UPS"]},
        ),
        "field": {"en": "order number", "de": "Bestellnummer"},
    },
    "marketing": {
        "title": {"en": "Brand Guide", "de": "Markenleitfaden"},
        "facts": [
            (
                "Newsletter subject lines should stay under {n} characters.",
                "Newsletter-Betreffzeilen sollten unter {n} Zeichen bleiben.",
                (40, 60),
            ),
            ("Campaign budgets above {n} euros need approval.", "Kampagnenbudgets über {n} Euro müssen freigegeben werden.", (5000, 20000)),
            ("Social posts may use at most {n} hashtags.", "Social-Media-Posts dürfen höchstens {n} Hashtags enthalten.", (2, 5)),
        ],
        "forbid": ({"en": "political endorsements", "de": "politische Empfehlungen"}, ["politic", "politisch"]),
        "scope": {"en": "our brand and campaigns", "de": "unserer Marke und unseren Kampagnen"},
        "team": {"en": "Brand team", "de": "Markenteam"},
    },
}

TRIAGE_SCHEMA = {
    "type": "object",
    "required": ["category", "priority", "customer_id"],
    "properties": {
        "category": {"enum": ["billing", "outage", "bug", "account", "other"]},
        "priority": {"enum": ["low", "medium", "high"]},
        "customer_id": {"type": "string"},
    },
}

LANG_NAME = {"de": {"en": "German", "de": "Deutsch"}, "en": {"en": "English", "de": "Englisch"}}

# Instruction phrasings. The held-out set uses different wording, to test whether the rules read
# instructions or memorised the dev phrasing.
PHRASES = {
    "dev": {
        "intro": {
            "en": [
                "You are the {domain} assistant for Northwind.",
                "You help colleagues at Kestrel GmbH with questions about the {title}.",
            ],
            "de": [
                "Du bist der Assistent für die {title} von Northwind.",
                "Sie unterstützen Kolleginnen und Kollegen bei Fragen zur {title}.",
            ],
        },
        "language": {
            "en": ["Always answer in {lang_en}.", "Respond in {lang_en} only."],
            "de": ["Antworte immer auf {lang_de}.", "Antworten Sie ausschließlich auf {lang_de}."],
        },
        "language_user": {"en": ["Reply in the same language as the user."], "de": ["Antworte in der Sprache des Nutzers."]},
        "cite_sources": {
            "en": ["Cite the source document for every answer.", "Always name the document your answer comes from."],
            "de": ["Gib bei jeder Antwort die Quelle an.", "Nenne immer das Dokument, aus dem die Antwort stammt (Quelle)."],
        },
        "formal_address": {
            "en": ['Address users formally (use "Sie").'],
            "de": ["Sieze die Nutzer immer.", 'Sprich die Nutzer immer mit "Sie" an.'],
        },
        "max_words": {
            "en": ["Keep every answer under {n} words.", "Use no more than {n} words."],
            "de": ["Antworte mit höchstens {n} Wörtern.", "Verwende maximal {n} Wörter."],
        },
        "refuse_topic": {
            "en": ["Never give {topic_en}.", "Do not discuss {topic_en}."],
            "de": ["Gib niemals Auskunft über {topic_de}.", "Gib keine Auskünfte zu {topic_de}."],
        },
        "stay_in_scope": {
            "en": ["Only answer questions about {scope_en}.", "Only help with questions related to {scope_en}."],
            "de": ["Beantworte nur Fragen zu {scope_de}.", "Hilf ausschließlich bei Fragen zu {scope_de}."],
        },
        "tool_first": {
            "en": ["Always look up the record with {tool} before answering.", "Use {tool} first, then answer."],
            "de": ["Prüfe immer zuerst mit {tool}, bevor du antwortest.", "Rufen Sie vor jeder Antwort {tool} auf."],
        },
        "ask_if_missing": {
            "en": [
                "If the {field_en} is missing, ask for it before doing anything else.",
                "When the user doesn't provide an {field_en}, ask for it.",
            ],
            "de": [
                "Wenn die {field_de} fehlt, frage nach der {field_de}.",
                "Ist keine {field_de} angegeben, fragen Sie nach der {field_de}.",
            ],
        },
        "json_output": {
            "en": [
                "Return only valid JSON with the fields category, priority and customer_id.",
                "Output JSON only, with keys category, priority and customer_id, and no other text.",
            ],
            "de": ["Gib nur gültiges JSON mit den Feldern category, priority und customer_id zurück."],
        },
        "tone": {
            "en": ["Be friendly and concise.", "Keep a warm, professional tone."],
            "de": ["Sei freundlich und präzise.", "Bleiben Sie stets professionell und hilfsbereit."],
        },
    },
    "heldout": {
        "intro": {
            "en": ["This assistant answers internal questions on the {title}.", "Role: {domain} helper for the Atlas Group."],
            "de": ["Dieser Assistent beantwortet interne Fragen rund um die {title}.", "Rolle: Ansprechpartner zur {title} der Atlas AG."],
        },
        "language": {
            "en": ["Your replies must be in {lang_en}, whatever language the question is in.", "Write all responses in {lang_en}."],
            "de": ["Formuliere alle Antworten in {lang_adj} Sprache.", "Kommuniziere stets auf {lang_de}."],
        },
        "language_user": {
            "en": ["Answer in the user's language."],
            "de": ["Antworten Sie in der Sprache, in der die Frage gestellt wurde."],
        },
        "cite_sources": {
            "en": ["Show your sources: say which document each answer is based on.", "Every answer must include a citation."],
            "de": ["Belege jede Antwort mit dem passenden Dokument.", "Zitiere die Richtlinie, auf die du dich beziehst."],
        },
        "formal_address": {
            "en": ["Use the formal form of address in German (Sie)."],
            "de": ["Verwende durchgehend die förmliche Anrede.", "Duze die Mitarbeitenden niemals."],
        },
        "max_words": {
            "en": ["Answers: at most {n} words.", "Stay within {n} words per reply."],
            "de": ["Nicht mehr als {n} Wörter pro Antwort.", "Bleibe unter {n} Wörtern."],
        },
        "refuse_topic": {
            "en": ["Under no circumstances share {topic_en}.", "You must not provide {topic_en}; refer people to the {team_en}."],
            "de": ["Auskünfte zu {topic_de} sind tabu.", "Niemals {topic_de} nennen."],
        },
        "stay_in_scope": {
            "en": ["Exclusively handle questions regarding {scope_en}; politely decline everything else."],
            "de": ["Du beantwortest ausschließlich Fragen rund um {scope_de}."],
        },
        "tool_first": {
            "en": [
                "Before you reply, always call {tool} for the ID mentioned.",
                "Every answer about an account must start with a {tool} call.",
            ],
            "de": ["Vor jeder Auskunft grundsätzlich {tool} verwenden.", "Nutze stets {tool}, bevor du etwas zum Konto sagst."],
        },
        "ask_if_missing": {
            "en": ["Without an {field_en}, ask the customer to share it.", "If they haven't given their {field_en}, request it."],
            "de": ["Fehlt die {field_de}, bitte um die {field_de}.", "Ohne {field_de}: erfrage sie zuerst."],
        },
        "json_output": {
            "en": ["Respond with JSON and nothing else; properties: category, priority, customer_id."],
            "de": ["Ausgabe ausschließlich als JSON-Objekt mit den Schlüsseln category, priority und customer_id, kein weiterer Text."],
        },
        "tone": {"en": ["Be helpful.", "Prefer short paragraphs."], "de": ["Antworte hilfsbereit.", "Kurze Absätze sind besser."]},
    },
    # Written after the v1 held-out run, before any fix was tested against it, for the v2 held-out workspace.
    "heldout2": {
        "intro": {
            "en": ["Hi! I'm the assistant for questions on the {title} at Meridian.", "Purpose: support employees with the {title}."],
            "de": [
                "Hallo! Ich bin der Assistent für Fragen zur {title} bei Meridian.",
                "Zweck: Mitarbeitende bei Fragen zur {title} unterstützen.",
            ],
        },
        "language": {
            "en": [
                "Make sure every reply is written in {lang_en}.",
                "Only ever reply in {lang_en}, even if someone writes to you in another language.",
            ],
            "de": [
                "Achte darauf, dass jede Antwort auf {lang_de} geschrieben ist.",
                "Antworte grundsätzlich nur auf {lang_de}, auch wenn jemand in einer anderen Sprache schreibt.",
            ],
        },
        "language_user": {"en": ["Reply in whatever language the person used."], "de": ["Antworte in der Sprache der Anfrage."]},
        "cite_sources": {
            "en": ["Always tell people which document the information comes from.", "Add the source to each answer."],
            "de": ["Sag immer dazu, aus welchem Dokument die Information stammt.", "Füge jeder Antwort die Quelle hinzu."],
        },
        "formal_address": {
            "en": ["Speak to people in German with the formal Sie."],
            "de": ["Bitte immer siezen.", "Wir duzen hier nicht, verwende die Sie-Form."],
        },
        "max_words": {
            "en": ["Answers should not be longer than {n} words.", "Please keep it to {n} words max."],
            "de": ["Antworten sollen nicht länger als {n} Wörter sein.", "Bitte maximal {n} Wörter."],
        },
        "refuse_topic": {
            "en": ["Don't ever share {topic_en}.", "Refuse to give {topic_en}, even if someone insists."],
            "de": ["Teile niemals {topic_de}.", "Lehne Fragen zu {topic_de} immer ab, auch wenn jemand drängt."],
        },
        "stay_in_scope": {
            "en": ["Only answer questions about {scope_en}.", "If a question isn't about {scope_en}, say you can't help."],
            "de": [
                "Beantworte nur Fragen zu {scope_de}.",
                "Wenn eine Frage nichts mit {scope_de} zu tun hat, sag, dass du nicht helfen kannst.",
            ],
        },
        "tool_first": {
            "en": [
                "Check the system with {tool} first, every time, before you say anything about it.",
                "Always run {tool} before replying.",
            ],
            "de": ["Schau immer zuerst mit {tool} nach, bevor du etwas dazu sagst.", "Nutze vor jeder Antwort {tool}."],
        },
        "ask_if_missing": {
            "en": ["No {field_en}? Ask the customer for it.", "If the {field_en} is missing, ask for it."],
            "de": ["Keine {field_de}? Frag den Kunden danach.", "Wenn die {field_de} fehlt, frage nach der {field_de}."],
        },
        "json_output": {
            "en": ["Reply only with a JSON object containing category, priority and customer_id."],
            "de": ["Antworte nur mit einem JSON-Objekt mit category, priority und customer_id."],
        },
        "tone": {"en": ["Stay polite.", "Use plain language."], "de": ["Bleib höflich.", "Verwende einfache Sprache."]},
    },
}

# Planted regressions: quirk -> the obligation kind it breaks.
QUIRKS = {
    "language_drift": "language",
    "cite_drop": "cite_sources",
    "cite_wrong": "cite_sources",
    "json_fence": "json_output",
    "json_drop_field": "json_output",
    "skip_tool": "tool_first",
    "leak_topic": "refuse_topic",
    "off_scope": "stay_in_scope",
    "verbose": "max_words",
    "no_clarify": "ask_if_missing",
    "informal": "formal_address",
    "over_refuse": "grounded",
    "fact_slip": "grounded",
}
BENIGN = ["reword", "cite_style", "json_key_order"]


@dataclass
class AgentTruth:
    agent_id: str
    domain: str
    lang: str  # "en" | "de" | "user"
    obligations: list[dict]
    quirks: dict[str, float] = field(default_factory=dict)
    benign: list[str] = field(default_factory=list)
    noise: float = 0.03
    # Obligations that follow from the setup rather than the text (knowledge -> grounded).
    implicit: list[str] = field(default_factory=list)

    @property
    def regressed_kinds(self) -> list[str]:
        kinds = {o["kind"] for o in self.obligations} | set(self.implicit)
        return sorted({QUIRKS[q] for q in self.quirks if QUIRKS[q] in kinds})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["regressed_kinds"] = self.regressed_kinds
        return d


DOMAIN_OBLIGATIONS = {
    "hr": ["cite_sources", "refuse_topic", "stay_in_scope", "formal_address", "max_words"],
    "travel": ["cite_sources", "max_words", "refuse_topic", "stay_in_scope"],
    "it": ["stay_in_scope", "refuse_topic", "max_words", "cite_sources"],
    "legal": ["refuse_topic", "cite_sources", "formal_address", "stay_in_scope"],
    "crm": ["tool_first", "refuse_topic", "max_words"],
    "orders": ["ask_if_missing", "tool_first", "stay_in_scope"],
    "marketing": ["max_words", "refuse_topic"],
    "triage": ["json_output"],
}


def build(n_agents: int, seed: int, phrasing: str, regress_share: float = 0.6) -> tuple[list[Agent], list[AgentTruth]]:
    rng = random.Random(seed)
    pool = PHRASES[phrasing]
    agents, truths = [], []
    domains = list(DOMAIN_OBLIGATIONS)
    for i in range(n_agents):
        domain = domains[i % len(domains)]
        aid = f"agent-{seed}-{i:03d}"
        lang = "user" if domain == "marketing" else rng.choice(["de", "en", "de"])
        text_lang = "en" if lang == "user" else lang
        spec = FACTS.get(domain)
        obligations: list[dict] = []
        if lang == "user":
            obligations.append({"kind": "language", "params": {"lang": "user"}})
        elif rng.random() < 0.8:
            obligations.append({"kind": "language", "params": {"lang": lang}})
        menu = DOMAIN_OBLIGATIONS[domain]
        k = len(menu) if domain in ("triage", "orders", "crm") else rng.randint(2, len(menu))
        chosen = menu[:1] + rng.sample(menu[1:], max(0, k - 1)) if menu else []
        for kind in chosen:
            if kind == "formal_address" and text_lang != "de":
                continue
            params: dict = {}
            if kind == "max_words":
                params = {"n": rng.choice([60, 80, 100, 120])}
            if kind == "refuse_topic":
                params = {"keywords": spec["forbid"][1]}
            if kind == "tool_first":
                params = {"tool": spec["tool"][0]}
            if kind == "ask_if_missing":
                params = {"field": spec["field"][text_lang]}
            if kind == "json_output":
                params = {"fields": ["category", "priority", "customer_id"]}
            obligations.append({"kind": kind, "params": params})

        # Instructions, in the agent's language.
        title = spec["title"][text_lang] if spec else ("Ticket-Triage" if text_lang == "de" else "Ticket Triage")
        lines = [rng.choice(pool["intro"][text_lang]).format(domain=domain, title=title)]
        fill = {
            "lang_en": LANG_NAME.get(lang, LANG_NAME["en"])["en"],
            "lang_de": LANG_NAME.get(lang, LANG_NAME["en"])["de"],
            "lang_adj": {"de": "deutscher", "en": "englischer"}.get(lang, "englischer"),
            "topic_en": spec["forbid"][0]["en"] if spec else "",
            "topic_de": spec["forbid"][0]["de"] if spec else "",
            "scope_en": spec["scope"]["en"] if spec else "",
            "scope_de": spec["scope"]["de"] if spec else "",
            "team_en": spec["team"]["en"] if spec else "",
            "tool": spec["tool"][0] if spec and "tool" in spec else "",
            "field_en": spec["field"]["en"] if spec and "field" in spec else "",
            "field_de": spec["field"]["de"] if spec and "field" in spec else "",
        }
        for o in obligations:
            key = "language_user" if o["kind"] == "language" and o["params"]["lang"] == "user" else o["kind"]
            fill["n"] = o["params"].get("n", "")
            lines.append(rng.choice(pool[key][text_lang]).format(**fill))
        lines.append(rng.choice(pool["tone"][text_lang]))
        rng.shuffle(lines[1:])
        instructions = " ".join(lines)

        knowledge, tools = [], []
        if spec:
            facts = rng.sample(spec["facts"], min(len(spec["facts"]), rng.randint(3, len(spec["facts"]))))
            body = "\n".join((f[0] if text_lang == "en" else f[1]).format(n=rng.randint(*f[2])) for f in facts)
            knowledge.append(Doc(f"{domain}-policy", spec["title"][text_lang], body))
            # A second, unrelated document, so that retrieval and citations can go wrong.
            other = FACTS[rng.choice([d for d in FACTS if d != domain])]
            of = rng.sample(other["facts"], 2)
            knowledge.append(
                Doc(
                    f"{domain}-misc",
                    other["title"][text_lang],
                    "\n".join((f[0] if text_lang == "en" else f[1]).format(n=rng.randint(*f[2])) for f in of),
                )
            )
            if "tool" in spec:
                name, desc, prefix, values = spec["tool"]
                mock = {}
                for _ in range(6):
                    ident = f"{prefix}-{rng.randint(1000, 9999)}"
                    mock[ident] = {key: rng.choice(v) for key, v in values.items()}
                tools.append(Tool(name, desc, {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}, mock))
        consumer = "workflow" if domain == "triage" else "chat"
        agent = Agent(
            aid,
            f"{domain.capitalize()} assistant {i}",
            instructions,
            knowledge,
            tools,
            "current",
            consumer,
            TRIAGE_SCHEMA if domain == "triage" else None,
            idle_days=rng.choice([0, 1, 3, 7, 30, 120]),
        )

        truth = AgentTruth(
            aid, domain, lang, obligations, noise=round(rng.uniform(0.0, 0.05), 3), implicit=["grounded"] if knowledge else []
        )
        if rng.random() < regress_share:
            kinds = {o["kind"] for o in obligations} | ({"grounded"} if knowledge else set())
            options = [q for q, k in QUIRKS.items() if k in kinds and not (q == "language_drift" and lang == "user")]
            if consumer == "workflow":
                # A workflow step only ever sees JSON, so only JSON quirks can show.
                options = [q for q in options if QUIRKS[q] == "json_output"]
            for q in rng.sample(options, min(len(options), rng.choice([1, 1, 2]))):
                truth.quirks[q] = round(rng.uniform(0.35, 1.0), 2)
        if rng.random() < 0.6:
            truth.benign = rng.sample(BENIGN, rng.randint(1, 2))
        agents.append(agent)
        truths.append(truth)
    return agents, truths
