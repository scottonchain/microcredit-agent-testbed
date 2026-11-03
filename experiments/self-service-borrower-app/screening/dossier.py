"""The dossier: what was said, what was shown, what the pool itself knows, and where they disagree.

Every statement carries a status:

- stated: the applicant said it and nothing else supports it;
- evidenced: a document the applicant uploaded supports it (a document can be forged,
  so this is not proof, only consistency);
- verified: an independent record confirms it: the pool's own ledger (stake, backing,
  repayments, defaults), or the practice desk's public record on the test network.

Contradictions are coded so the policy can weigh them and the adverse-action notice
can name them. The agent never writes a contradiction into the dossier directly: the
extractor's `concerns` become one coded contradiction ("document_concern") at most.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any

from .documents import Document, FRESH_DAYS, DOCUMENT_TYPES
from .interview import Application, EVIDENCE_FOR_SOURCE, EVIDENCE_FOR_PURPOSE

STATED, EVIDENCED, VERIFIED = "stated", "evidenced", "verified"
MINOR, SEVERE = "minor", "severe"

LIVE_APR = 0.0933  # the recorded pool rate, 933 bps; replaced by pool_record["apr"] when given
AMOUNT_TOLERANCE = 0.25  # a documented amount within 25% of the stated one agrees with it
QUOTE_HEADROOM = 1.5  # asking for more than 1.5x the quote is a contradiction


@dataclass
class Statement:
    key: str
    value: Any
    status: str
    source: str = "interview"
    note: str = ""


@dataclass
class Contradiction:
    code: str
    severity: str
    detail: str


@dataclass
class Dossier:
    application: dict
    statements: list[Statement] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    repayment_source_status: str = STATED
    purpose_status: str = STATED
    surplus_usd: float = 0.0
    surplus_status: str = STATED
    installment_usd: float = 0.0
    capacity_ratio: float | None = None
    backing_kind: str = "none"
    backing_usdc: float = 0.0
    backing_status: str = STATED
    backer_record: dict = field(default_factory=dict)
    borrower_record: dict = field(default_factory=dict)
    trial_record: dict = field(default_factory=dict)
    reserve_usdc: float | None = None
    apr: float = LIVE_APR
    extraction_cost_usd: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def severe_count(self) -> int:
        return sum(1 for c in self.contradictions if c.severity == SEVERE)

    def minor_count(self) -> int:
        return sum(1 for c in self.contradictions if c.severity == MINOR)


def _norm_name(text: str) -> str:
    return " ".join("".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())


def _names_match(a: str, b: str) -> bool:
    a, b = _norm_name(a), _norm_name(b)
    if not a or not b:
        return False
    if a == b:
        return True
    parts_a, parts_b = set(a.split()), set(b.split())
    return len(parts_a & parts_b) >= 2 or (len(parts_a & parts_b) >= 1 and min(len(parts_a), len(parts_b)) == 1)


def monthly_amount(amount: float, period: str) -> float:
    if period == "weekly":
        return amount * 52 / 12
    if period == "monthly":
        return amount
    return 0.0  # a one-off amount is not income


def installment(amount_usdc: float, term_days: int, apr: float) -> float:
    """What the loan costs per month of its term, interest included (the repayment the surplus must cover)."""
    total = amount_usdc * (1 + apr * term_days / 365)
    months = max(term_days / 30.0, 1.0)
    return total / months


def build_dossier(application: Application, documents: list[Document], pool_record: dict | None = None,
                  today: date | None = None, seen_document_owner=None) -> Dossier:
    """Compare the interview, the documents and the pool's own record; tag and flag.

    `pool_record` is read from the chain by the app (demo.mjs --pool-record) or passed by the
    tests: {"apr", "reserve_usdc", "borrower": {...}, "backer": {...}, "trial": {...},
    "own_deposit_usdc"}. `seen_document_owner(sha256) -> application id or None` catches a
    document reused from another application.
    """
    today = today or date.today()
    record = pool_record or {}
    d = Dossier(application=application.to_dict(), apr=float(record.get("apr", LIVE_APR)),
                reserve_usdc=record.get("reserve_usdc"), documents=[doc.to_dict() for doc in documents])
    d.extraction_cost_usd = round(sum(doc.cost_usd for doc in documents), 6)
    add = d.statements.append
    flag = lambda code, severity, detail: d.contradictions.append(Contradiction(code, severity, detail))

    # ---- documents: freshness, name, reuse, extractor concerns
    fresh: list[Document] = []
    for doc in documents:
        if seen_document_owner is not None:
            owner = seen_document_owner(doc.sha256)
            if owner:
                flag("document_reused", SEVERE, f"{doc.filename} was already submitted with application {owner}")
        if doc.claims.get("concerns"):
            flag("document_concern", MINOR, f"{doc.filename}: " + "; ".join(doc.claims["concerns"][:3]))
        name_on = doc.claims.get("name_on_document", "")
        if name_on and application.applicant_name and not _names_match(name_on, application.applicant_name):
            if application.documents_note.strip():
                d.notes.append(f"{doc.filename} is in another name ({name_on}); the applicant's note is recorded, a person reviews it")
            flag("name_mismatch", SEVERE if not application.documents_note.strip() else MINOR,
                 f"{doc.filename} is in the name {name_on!r}, the application in {application.applicant_name!r}")
        age = doc.age_days(today)
        if age is None:
            d.notes.append(f"{doc.filename}: no date read; counted as stated only")
        elif age > FRESH_DAYS:
            flag("document_stale", MINOR, f"{doc.filename} is {age} days old (limit {FRESH_DAYS})")
        elif age < -3:
            flag("document_future_dated", SEVERE, f"{doc.filename} is dated {doc.claims.get('date')} in the future")
        else:
            fresh.append(doc)

    # ---- repayment source
    wanted = set(EVIDENCE_FOR_SOURCE.get(application.repayment_source, ()))
    source_docs = [doc for doc in fresh if doc.doc_type in wanted and DOCUMENT_TYPES[doc.doc_type]["evidences"] == "repayment_source"]
    documented_income = sum(monthly_amount(float(doc.claims.get("amount_usd") or 0), doc.claims.get("period", "")) for doc in source_docs)
    if source_docs and documented_income > 0:
        d.repayment_source_status = EVIDENCED
        add(Statement("repayment_source", application.repayment_source, EVIDENCED,
                      source=",".join(doc.sha256[:12] for doc in source_docs), note=f"documented about {documented_income:.0f} USD a month"))
    else:
        add(Statement("repayment_source", application.repayment_source, STATED, note=application.payer_text))
    if application.repayment_source == "customer_payment":
        orders = [doc for doc in fresh if doc.doc_type == "customer_order"]
        for doc in orders:
            due = doc.document_date if not doc.claims.get("due_date") else None
            from .documents import parse_date
            due = parse_date(doc.claims.get("due_date", "")) or due
            if due and (due - today).days > application.term_days + 7:
                flag("order_pays_after_term", MINOR, f"{doc.filename} is paid on {due}, after the {application.term_days}-day term")
        if orders and sum(float(o.claims.get("amount_usd") or 0) for o in orders) > 0:
            d.repayment_source_status = EVIDENCED

    # ---- surplus and capacity
    stated_surplus = application.stated_surplus_usd
    if documented_income > 0:
        # The documents show income, not outgoings; the applicant's band gives the outgoings implicitly.
        # Use the smaller of the stated band and what the documents could support, and mark it evidenced.
        d.surplus_usd = min(stated_surplus, documented_income) if stated_surplus > 0 else 0.0
        d.surplus_status = EVIDENCED
        if stated_surplus > documented_income * (1 + AMOUNT_TOLERANCE) and stated_surplus > 10:
            flag("surplus_exceeds_documented_income", MINOR,
                 f"stated surplus band about {stated_surplus:.0f} USD, documents show about {documented_income:.0f} USD a month in total")
    else:
        d.surplus_usd = stated_surplus
    d.installment_usd = round(installment(application.amount_usdc, application.term_days, d.apr), 4)
    d.capacity_ratio = None if d.surplus_usd <= 0 else round(d.installment_usd / d.surplus_usd, 4)
    add(Statement("monthly_surplus_usd", d.surplus_usd, d.surplus_status))
    if d.surplus_usd <= 0:
        flag("no_surplus", MINOR, "nothing is left each month as stated; repayment would need income not described")

    # ---- purpose
    wanted_purpose = set(EVIDENCE_FOR_PURPOSE.get(application.purpose_category, ()))
    purpose_docs = [doc for doc in fresh if doc.doc_type in wanted_purpose]
    if purpose_docs:
        d.purpose_status = EVIDENCED
        quoted = sum(float(doc.claims.get("amount_usd") or 0) for doc in purpose_docs if doc.doc_type == "supplier_quote")
        if quoted > 0 and application.amount_usdc > quoted * QUOTE_HEADROOM:
            flag("amount_exceeds_quote", MINOR, f"asked {application.amount_usdc:.2f} USDC against quotes totalling {quoted:.2f} USD")
    add(Statement("purpose", application.purpose_category, d.purpose_status, note=application.purpose_text))
    if application.purpose_category == "order" and application.repayment_source not in ("customer_payment", "sales"):
        flag("purpose_source_incoherent", MINOR, "a customer order is to be filled but the customer is not the repayment source")

    # ---- backing: what the chain says beats what was said
    backer = dict(record.get("backer") or {})
    own_deposit = float(record.get("own_deposit_usdc") or 0.0)
    d.backing_kind = application.backing_kind
    if application.backing_kind == "backer":
        if application.backer_address and application.borrower_address and \
                application.backer_address.strip().lower() == application.borrower_address.strip().lower():
            flag("self_backing", SEVERE, "the named backer is the applicant's own account")
        stake = float(backer.get("free_credit_usdc") or 0.0)
        if backer and backer.get("address", "").lower() == application.backer_address.strip().lower() and stake > 0:
            d.backing_usdc, d.backing_status = stake, VERIFIED
            d.backer_record = backer
            if int(backer.get("defaults", 0)) > 0:
                flag("backer_defaulted", SEVERE, "the backer's own record in the pool shows a default")
        else:
            d.backing_usdc, d.backing_status = 0.0, STATED
            d.notes.append("no stake found for the named backer; the loan cannot be made until they stake")
    elif application.backing_kind == "own_deposit":
        amount = own_deposit if own_deposit > 0 else float(application.own_deposit_usdc or 0)
        d.backing_usdc = amount
        d.backing_status = VERIFIED if own_deposit > 0 else STATED
    add(Statement("backing", {"kind": d.backing_kind, "usdc": d.backing_usdc}, d.backing_status))

    # ---- the applicant's own record: in the real pool, and in the practice desk
    borrower = dict(record.get("borrower") or {})
    if borrower:
        d.borrower_record = borrower
        add(Statement("borrower_record", borrower, VERIFIED, source="pool"))
        if int(borrower.get("defaults", 0)) > 0:
            flag("borrower_defaulted", SEVERE, "this account defaulted on an earlier loan in the pool")
        if int(borrower.get("open_loans", 0)) > 0:
            flag("open_loan", SEVERE, "one line per person: an earlier loan is still open")
    trial = dict(record.get("trial") or {})
    if application.trial_wallet.strip():
        if trial and trial.get("linked"):
            d.trial_record = trial
            add(Statement("trial_record", trial, VERIFIED, source="practice desk"))
            if int(trial.get("defaults", 0)) > 0:
                flag("trial_defaulted", MINOR, "the practice wallet left a loan unpaid past 30 days")
        else:
            add(Statement("trial_record", {"wallet": application.trial_wallet}, STATED,
                          note="practice wallet named but not proven to be the applicant's (no signature)"))
    return d
