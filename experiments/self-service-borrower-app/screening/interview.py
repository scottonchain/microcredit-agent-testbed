"""The trust interview: seven taps, then evidence.

Stage one (CORE) is seven low-load questions, six of them multiple choice and one
consent, which is all a practice applicant answers. Stage two (EVIDENCE) is what a
real first loan needs on top: the applicant's name as it appears on documents, a
sentence in their own words, the documents themselves, and who backs them. Nothing
asks about a protected characteristic; an application carrying one is refused
before scoring (PROHIBITED_KEYS).

`follow_ups` returns the plain-language questions an application still has to
answer. They are deterministic so the pilot can measure what each one changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

PURPOSE_CATEGORIES = {
    "stock": "stock or materials to sell or make something",
    "equipment": "a tool or equipment for work",
    "order": "filling a customer order I already have",
    "work_costs": "costs of starting or keeping a job",
    "bridge": "a gap until money I am owed arrives",
    "emergency": "an emergency (medical, repair, housing)",
    "other": "something else",
}
PRODUCTIVE_PURPOSES = frozenset({"stock", "equipment", "order", "work_costs", "bridge"})

REPAYMENT_SOURCES = {
    "wages": "wages from an employer",
    "sales": "sales from my own business or trade",
    "customer_payment": "a customer who will pay me for this order or job",
    "remittance": "money family sends me regularly",
    "benefit": "a regular benefit or pension",
    "other": "something else",
}

# "After rent, food and other loan payments, how much is usually left each month?"
SURPLUS_BANDS = {
    "none": ("nothing is left", 0.0),
    "under_10": ("under $10", 5.0),
    "10_50": ("$10 to $50", 30.0),
    "50_200": ("$50 to $200", 100.0),
    "over_200": ("over $200", 300.0),
}

BACKING_KINDS = {
    "backer": "someone who knows me will back me with their own stake",
    "own_deposit": "I can lock some of my own money as a deposit",
    "none": "nobody yet",
}

AMOUNT_CHIPS = (3.0, 5.0, 10.0)
TERMS_DAYS = (30, 60, 90)
MAX_FIRST_REQUEST_USDC = 10.0
MAX_REPEAT_REQUEST_USDC = 20.0

# Never asked, never accepted: Regulation B prohibited bases and their obvious proxies.
PROHIBITED_KEYS = frozenset({
    "race", "ethnicity", "colour", "color", "religion", "national_origin", "nationality",
    "sex", "gender", "marital_status", "age", "date_of_birth", "birthdate", "public_assistance",
    "receives_public_assistance", "disability", "pregnancy", "sexual_orientation", "citizenship",
})

EVIDENCE_FOR_SOURCE = {
    "wages": ("pay_stub", "bank_statement", "employment_letter"),
    "sales": ("sales_record", "bank_statement", "mobile_money_statement"),
    "customer_payment": ("customer_order", "bank_statement"),
    "remittance": ("bank_statement", "mobile_money_statement"),
    "benefit": ("benefit_letter", "bank_statement"),
    "other": ("bank_statement", "mobile_money_statement"),
}
EVIDENCE_FOR_PURPOSE = {
    "stock": ("supplier_quote",),
    "equipment": ("supplier_quote",),
    "order": ("customer_order",),
    "work_costs": ("supplier_quote", "employment_letter"),
    "bridge": ("customer_order", "employment_letter"),
    "emergency": ("supplier_quote",),
    "other": (),
}

DOCUMENT_LABELS = {
    "pay_stub": "pay stub or payslip",
    "employment_letter": "letter from your employer",
    "bank_statement": "bank statement",
    "mobile_money_statement": "mobile-money statement",
    "sales_record": "sales record or ledger",
    "customer_order": "customer order or contract",
    "supplier_quote": "supplier quote or invoice",
    "benefit_letter": "benefit or pension letter",
    "backer_attestation": "a signed note from your backer",
    "id_document": "identity document",
}

CORE, EVIDENCE = "core", "evidence"

# The script. Stage CORE is seven taps. Stage EVIDENCE is asked only for a real loan.
QUESTIONS = (
    {"key": "purpose_category", "stage": CORE, "kind": "choice", "choices": PURPOSE_CATEGORIES, "required": True,
     "text": "What is the money for?"},
    {"key": "amount_usdc", "stage": CORE, "kind": "number", "required": True, "min": 1, "max": MAX_REPEAT_REQUEST_USDC,
     "chips": AMOUNT_CHIPS, "text": f"How much do you need? First loans are at most ${MAX_FIRST_REQUEST_USDC:.0f}."},
    {"key": "term_days", "stage": CORE, "kind": "choice", "choices": {str(d): f"{d} days" for d in TERMS_DAYS}, "required": True,
     "text": "When can you pay it all back?"},
    {"key": "repayment_source", "stage": CORE, "kind": "choice", "choices": REPAYMENT_SOURCES, "required": True,
     "text": "Where will the money to pay it back come from?"},
    {"key": "surplus_band", "stage": CORE, "kind": "choice", "choices": {k: v[0] for k, v in SURPLUS_BANDS.items()}, "required": True,
     "text": "After rent, food and other loan payments, how much is usually left each month?"},
    {"key": "backing_kind", "stage": CORE, "kind": "choice", "choices": BACKING_KINDS, "required": True,
     "text": "Who stands behind this loan?"},
    {"key": "consent", "stage": CORE, "kind": "boolean", "required": True,
     "text": "What I said is true. My answers and documents stay private with the lender and are used only to decide this loan and give me the reasons."},
    {"key": "applicant_name", "stage": EVIDENCE, "kind": "text", "required": True,
     "text": "Your name, as it appears on the documents you will show."},
    {"key": "purpose_text", "stage": EVIDENCE, "kind": "text", "required": True, "min_words": 6,
     "text": "In a sentence or two (typed or spoken): what will you do with the money, and what will it bring in?",
     "asks_for": "a supplier quote, invoice or customer order if you have one"},
    {"key": "payer_text", "stage": EVIDENCE, "kind": "text", "required": False,
     "text": "Who pays you, and how often?",
     "asks_for": "a pay stub, a bank or mobile-money statement, a sales record or a customer order"},
    {"key": "backer_name", "stage": EVIDENCE, "kind": "text", "required": False, "text": "Your backer's name."},
    {"key": "backer_address", "stage": EVIDENCE, "kind": "text", "required": False,
     "text": "Your backer's account in the app (they can send it to you)."},
    {"key": "backer_relationship", "stage": EVIDENCE, "kind": "text", "required": False,
     "text": "How do you know your backer, and for how long?"},
    {"key": "own_deposit_usdc", "stage": EVIDENCE, "kind": "number", "required": False, "min": 0,
     "text": "If you chose a deposit: how much can you lock while the loan is open?"},
    {"key": "trial_wallet", "stage": EVIDENCE, "kind": "text", "required": False,
     "text": "Did you try the practice app? Paste its wallet address (the Help screen shows it) so your practice record counts."},
    {"key": "documents_note", "stage": EVIDENCE, "kind": "text", "required": False,
     "text": "Anything we should know about your documents (for example, a shared account in another name)?"},
)
QUESTION_BY_KEY = {q["key"]: q for q in QUESTIONS}
CORE_KEYS = tuple(q["key"] for q in QUESTIONS if q["stage"] == CORE)


@dataclass
class Application:
    purpose_category: str
    amount_usdc: float
    term_days: int
    repayment_source: str
    surplus_band: str
    backing_kind: str
    consent: bool
    applicant_name: str = ""
    purpose_text: str = ""
    payer_text: str = ""
    backer_name: str = ""
    backer_address: str = ""
    backer_relationship: str = ""
    own_deposit_usdc: float = 0.0
    trial_wallet: str = ""
    documents_note: str = ""
    borrower_address: str = ""
    stage: str = CORE
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def stated_surplus_usd(self) -> float:
        return SURPLUS_BANDS[self.surplus_band][1]

    @property
    def productive(self) -> bool:
        return self.purpose_category in PRODUCTIVE_PURPOSES


class InterviewError(ValueError):
    """An answer set that cannot become an application (missing, malformed or prohibited)."""


def _number(value: Any, key: str) -> float:
    try:
        number = float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        raise InterviewError(f"{key}: expected a number, got {value!r}")
    if number != number or number in (float("inf"), float("-inf")):
        raise InterviewError(f"{key}: expected a finite number")
    return number


def _boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "on", "1", "y"}


def application_from_answers(answers: dict, stage: str = EVIDENCE) -> Application:
    """Validate raw answers (form fields or JSON) against the script and build the application.

    `stage` CORE validates only the seven taps (the practice path); EVIDENCE also requires
    the evidence-stage answers a real loan needs.
    """
    prohibited = sorted(PROHIBITED_KEYS & {str(k).lower() for k in answers})
    if prohibited:
        raise InterviewError(f"prohibited fields present, refused before scoring: {', '.join(prohibited)}")
    if stage not in (CORE, EVIDENCE):
        raise InterviewError(f"unknown stage {stage!r}")
    values: dict[str, Any] = {}
    for question in QUESTIONS:
        key, kind = question["key"], question["kind"]
        raw = answers.get(key)
        empty = raw is None or (isinstance(raw, str) and not raw.strip())
        required = question["required"] and (question["stage"] == CORE or stage == EVIDENCE)
        if empty:
            if required:
                raise InterviewError(f"{key}: required")
            values[key] = 0.0 if kind == "number" else (False if kind == "boolean" else "")
            continue
        if kind == "number":
            number = _number(raw, key)
            if "min" in question and number < question["min"]:
                raise InterviewError(f"{key}: must be at least {question['min']}")
            if "max" in question and number > question["max"]:
                raise InterviewError(f"{key}: must be at most {question['max']}")
            values[key] = number
        elif kind == "choice":
            choice = str(raw).strip()
            if choice not in question["choices"]:
                raise InterviewError(f"{key}: {choice!r} is not one of {sorted(question['choices'])}")
            values[key] = choice
        elif kind == "boolean":
            flag = _boolean(raw)
            if required and not flag:
                raise InterviewError(f"{key}: must be confirmed")
            values[key] = flag
        else:
            text = str(raw).strip()
            if len(text) > 4000:
                raise InterviewError(f"{key}: too long")
            if "min_words" in question and len(text.split()) < question["min_words"]:
                raise InterviewError(f"{key}: please write at least {question['min_words']} words")
            values[key] = text
    values["term_days"] = int(values["term_days"])
    known = set(QUESTION_BY_KEY) | {"borrower_address", "documents", "stage"}
    extra = {k: v for k, v in answers.items() if k not in known}
    return Application(borrower_address=str(answers.get("borrower_address", "")).strip(), stage=stage, extra=extra, **values)


def follow_ups(application: Application, document_types: set[str] | None = None) -> list[str]:
    """Plain-language questions the applicant still has to answer before a real loan is decided."""
    present = set(document_types or ())
    asks: list[str] = []
    wanted = EVIDENCE_FOR_SOURCE.get(application.repayment_source, ())
    if wanted and not (present & set(wanted)):
        names = ", ".join(DOCUMENT_LABELS.get(t, t) for t in wanted)
        asks.append(f"You said repayment comes from {REPAYMENT_SOURCES[application.repayment_source]}. "
                    f"Please show one of: {names}, from the last 90 days.")
    wanted_purpose = EVIDENCE_FOR_PURPOSE.get(application.purpose_category, ())
    if wanted_purpose and not (present & set(wanted_purpose)):
        names = ", ".join(DOCUMENT_LABELS.get(t, t) for t in wanted_purpose)
        asks.append(f"For '{PURPOSE_CATEGORIES[application.purpose_category]}', can you show what it costs or who ordered it? "
                    f"A {names} helps; if you have none, say so in the documents note.")
    if application.purpose_category == "order" and application.repayment_source != "customer_payment":
        asks.append("You are filling a customer order but repayment comes from somewhere else. Will the customer pay you? "
                    "If so, choose the customer as the repayment source and say when they pay.")
    if application.surplus_band == "none":
        asks.append("You said nothing is usually left each month. Where would the repayment come from? "
                    "Is there income you did not count, or an expense that stops soon?")
    if application.backing_kind == "none":
        asks.append("A first loan needs a named backer who stakes for you, or your own deposit locked while the loan is open. "
                    "Who would back you, or how much could you deposit?")
    if application.backing_kind == "backer" and not application.backer_address.strip():
        asks.append("Ask your backer for their account in the app and paste it here.")
    if application.backing_kind == "backer" and not application.backer_relationship.strip():
        asks.append("How do you know your backer, and for how long?")
    if application.backing_kind == "own_deposit" and application.own_deposit_usdc <= 0:
        asks.append("How much of your own money can you lock as a deposit while the loan is open?")
    if application.purpose_category == "emergency":
        asks.append("For an emergency, a grant or a payment plan with the provider may cost less than a loan. "
                    "Have you asked? Tell us what you were offered.")
    if application.purpose_category in ("order", "bridge"):
        asks.append("Could the customer pay part up front instead? A deposit would mean you borrow less, or nothing.")
    return asks
