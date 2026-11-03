"""The trust interview: plain-language questions, the application they produce, and follow-ups.

The interview asks what the money is for, how much and for how long, where repayment
will come from, what the applicant can show for it, and who would back them with
their own stake. It never asks about a protected characteristic, and an application
that carries one is refused before any scoring (PROHIBITED_KEYS).

Each question names the evidence that would turn a statement into an evidenced one,
so the applicant knows what to upload. `follow_ups` returns the questions an
incomplete or inconsistent application still has to answer; the server shows them
before the application is final, which is what makes the intake a conversation
rather than a form.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

PURPOSE_CATEGORIES = {
    "stock": "buying stock or materials to sell or to make something",
    "equipment": "a tool or piece of equipment for work",
    "order": "filling a customer order I already have",
    "work_costs": "costs of starting or keeping a job (transport, uniform, fees, a permit)",
    "bridge": "covering a gap until money I am owed arrives",
    "emergency": "an emergency (medical, repair, housing)",
    "other": "something else",
}
PRODUCTIVE_PURPOSES = {"stock", "equipment", "order", "work_costs", "bridge"}

REPAYMENT_SOURCES = {
    "wages": "wages or a salary from an employer",
    "sales": "sales from my own business or trade",
    "customer_payment": "a specific customer who will pay me for an order or job",
    "remittance": "money a family member sends regularly",
    "benefit": "a regular benefit or pension payment",
    "other": "something else",
}

# Which document types evidence which repayment source or purpose.
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

TERMS_DAYS = (30, 60, 90)
MAX_FIRST_REQUEST_USDC = 10.0
MAX_REPEAT_REQUEST_USDC = 20.0

# Never asked, never accepted. Regulation B prohibited bases and their obvious proxies.
PROHIBITED_KEYS = frozenset({
    "race", "ethnicity", "colour", "color", "religion", "national_origin", "nationality",
    "sex", "gender", "marital_status", "age", "date_of_birth", "birthdate", "public_assistance",
    "receives_public_assistance", "disability", "pregnancy", "sexual_orientation", "citizenship",
})

# The script. `key` is the answer field; `asks_for` is the evidence that would upgrade it.
QUESTIONS = (
    {"key": "applicant_name", "kind": "text", "required": True,
     "text": "What name should we use for you? Use the same name that appears on any document you upload."},
    {"key": "purpose_category", "kind": "choice", "choices": PURPOSE_CATEGORIES, "required": True,
     "text": "What is the money for?"},
    {"key": "purpose_text", "kind": "text", "required": True, "min_words": 8,
     "text": "In your own words, what exactly will you do with the money, and what will it bring in?",
     "asks_for": "a supplier quote, invoice or customer order if you have one"},
    {"key": "amount_usdc", "kind": "number", "required": True, "min": 1, "max": MAX_REPEAT_REQUEST_USDC,
     "text": f"How much do you need, in USDC (US dollars)? First loans are at most {MAX_FIRST_REQUEST_USDC:.0f}."},
    {"key": "term_days", "kind": "choice", "choices": {str(d): f"{d} days" for d in TERMS_DAYS}, "required": True,
     "text": "When can you repay it in full?"},
    {"key": "repayment_source", "kind": "choice", "choices": REPAYMENT_SOURCES, "required": True,
     "text": "Where will the money to repay come from?"},
    {"key": "repayment_source_detail", "kind": "text", "required": True, "min_words": 3,
     "text": "Who pays you, and how often? (An employer, your customers, a family member.)",
     "asks_for": "a pay stub, a bank or mobile-money statement, a sales record or a customer order"},
    {"key": "monthly_income_usd", "kind": "number", "required": True, "min": 0,
     "text": "About how much comes in per month from that source, in US dollars?"},
    {"key": "monthly_expenses_usd", "kind": "number", "required": True, "min": 0,
     "text": "About how much goes out per month for everything you must pay (rent, food, transport, school)?"},
    {"key": "other_debt_monthly_usd", "kind": "number", "required": True, "min": 0,
     "text": "How much do you already pay each month on other loans or debts? Write 0 if none."},
    {"key": "backer_name", "kind": "text", "required": False,
     "text": "Is there someone who knows you and would back your loan with their own stake? Their name."},
    {"key": "backer_address", "kind": "text", "required": False,
     "text": "The backer's account address in the pool (they can send it to you from the app)."},
    {"key": "backer_relationship", "kind": "text", "required": False,
     "text": "How do you know the backer, and for how long?"},
    {"key": "own_deposit_usdc", "kind": "number", "required": False, "min": 0,
     "text": "If you have no backer: how much of your own money can you lock as a deposit while the loan is open? (A credit-builder loan.)"},
    {"key": "documents_note", "kind": "text", "required": False,
     "text": "Anything about your documents we should know (for example, a statement in another name because the account is shared)?"},
    {"key": "consent_truthful", "kind": "boolean", "required": True,
     "text": "I confirm that what I have written is true and the documents are mine or I have the owner's permission to use them."},
    {"key": "consent_privacy", "kind": "boolean", "required": True,
     "text": "I have read the privacy notice: my answers and documents are stored privately by the lender, never published, and used only to decide this application and to give me the reasons."},
)
QUESTION_BY_KEY = {q["key"]: q for q in QUESTIONS}


@dataclass
class Application:
    applicant_name: str
    purpose_category: str
    purpose_text: str
    amount_usdc: float
    term_days: int
    repayment_source: str
    repayment_source_detail: str
    monthly_income_usd: float
    monthly_expenses_usd: float
    other_debt_monthly_usd: float
    consent_truthful: bool
    consent_privacy: bool
    backer_name: str = ""
    backer_address: str = ""
    backer_relationship: str = ""
    own_deposit_usdc: float = 0.0
    documents_note: str = ""
    borrower_address: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def monthly_surplus_usd(self) -> float:
        return self.monthly_income_usd - self.monthly_expenses_usd - self.other_debt_monthly_usd

    @property
    def has_named_backer(self) -> bool:
        return bool(self.backer_address.strip())


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


def application_from_answers(answers: dict) -> Application:
    """Validate raw answers (form fields or JSON) against the script and build the application."""
    prohibited = sorted(PROHIBITED_KEYS & {str(k).lower() for k in answers})
    if prohibited:
        raise InterviewError(f"prohibited fields present, refused before scoring: {', '.join(prohibited)}")
    values: dict[str, Any] = {}
    for question in QUESTIONS:
        key = question["key"]
        raw = answers.get(key)
        empty = raw is None or (isinstance(raw, str) and not raw.strip())
        if empty:
            if question["required"]:
                raise InterviewError(f"{key}: required")
            values[key] = 0.0 if question["kind"] == "number" else ("" if question["kind"] != "boolean" else False)
            continue
        kind = question["kind"]
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
            if question["required"] and not flag:
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
    known = set(QUESTION_BY_KEY) | {"borrower_address", "documents"}
    extra = {k: v for k, v in answers.items() if k not in known}
    return Application(borrower_address=str(answers.get("borrower_address", "")).strip(), extra=extra, **values)


def follow_ups(application: Application, document_types: set[str] | None = None) -> list[str]:
    """Plain-language questions the applicant still has to answer before the application is final.

    These are the conversational part of the interview: the agent reads what was said and
    what was shown, and asks for what is missing or does not add up. They are deterministic
    so the pilot can measure what each follow-up changes.
    """
    present = set(document_types or ())
    asks: list[str] = []
    wanted = EVIDENCE_FOR_SOURCE.get(application.repayment_source, ())
    if wanted and not (present & set(wanted)):
        names = ", ".join(DOCUMENT_LABELS.get(t, t) for t in wanted)
        asks.append(f"You said repayment comes from {REPAYMENT_SOURCES[application.repayment_source]}. "
                    f"Please upload one of: {names}, from the last 90 days.")
    wanted_purpose = EVIDENCE_FOR_PURPOSE.get(application.purpose_category, ())
    if wanted_purpose and not (present & set(wanted_purpose)):
        names = ", ".join(DOCUMENT_LABELS.get(t, t) for t in wanted_purpose)
        asks.append(f"For '{PURPOSE_CATEGORIES[application.purpose_category]}', can you show what it costs or who ordered it? "
                    f"Upload a {names} if you have one; if not, say so in the documents note.")
    if application.purpose_category == "order" and application.repayment_source != "customer_payment":
        asks.append("You are filling a customer order but repayment comes from somewhere else. Will the customer pay you? "
                    "If so, choose 'a specific customer' as the repayment source and tell us when they pay.")
    if application.monthly_surplus_usd <= 0:
        asks.append("Your monthly income does not cover your monthly outgoings and debts as written. "
                    "Is there income you did not count, or an expense that stops soon? Please explain.")
    if not application.has_named_backer and application.own_deposit_usdc <= 0:
        asks.append("A first loan needs a named backer who stakes for you, or your own deposit locked while the loan is open. "
                    "Who would back you, or how much could you deposit?")
    if application.has_named_backer and not application.backer_relationship.strip():
        asks.append("How do you know your backer, and for how long?")
    if application.purpose_category == "emergency":
        asks.append("For an emergency, a grant or a payment plan with the provider may cost you less than a loan. "
                    "Have you asked? Tell us what you were offered.")
    if application.purpose_category in ("order", "bridge"):
        asks.append("Could the customer pay part of the order up front instead? A deposit would mean you borrow less or nothing.")
    return asks


# Labels shared with documents.py (kept here so the interview can name them without a cycle).
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
