"""Policy: published weights, a score a person can read, a cap, and the reasons.

This is the deterministic half of the officer rule. It takes the dossier and returns a
Decision. It never creates credit: an approval is a recommendation with a cap, and the
cap is never above the backing that exists (a named backer's free credit or the
applicant's own deposit), never above the pool's exposure rule (a fifth of the
reserve), and never above what was asked.

The weights are public so that every reason in a decline reads as an adverse-action
reason (Regulation B): the applicant is told which factor cost the points and what
would change it. Change the weights only with a new POLICY_VERSION; the pilot measures
each version's admitted default rate and admission rate separately (D7 screen rule 6).

Hard rules, applied before the score and never outweighed by it:
  H1 no backing (no backer stake and no deposit): decline, with the reason;
  H2 a default by this account in the pool, or an open loan: decline;
  H3 a severe contradiction: decline (reused document, future-dated document, name
     mismatch without an explanation, self-backing, a backer with a default);
  H4 the cap is at most the backing, at most a fifth of the reserve, at most the request.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .dossier import Dossier, EVIDENCED, VERIFIED, STATED, SEVERE, MINOR
from .interview import Application, PRODUCTIVE_PURPOSES, MAX_FIRST_REQUEST_USDC, MAX_REPEAT_REQUEST_USDC

POLICY_VERSION = "2026-11-03.1"
FILTER_DEFAULT_CEILING = 0.11  # the raw default of the admitted population must stay at or below this (D7 rule 5)
EXPOSURE_SHARE = 0.2  # no loan above a fifth of the reserve

# Points by factor. The maximum of each row is the weight; the comment says what earns it.
WEIGHTS = {
    "repayment_source": 30,   # verified 30, evidenced 20, stated 8
    "capacity": 20,           # installment at most a quarter of the monthly surplus 20, half 12, all 5; stated-only surplus counts half
    "purpose": 15,            # productive and evidenced 15, productive stated 8, other stated 4
    "backing_record": 15,     # a backer with on-time history and no default 15, a backer or deposit with no history 8
    "own_history": 10,        # an on-time repayment in this pool 10; a completed practice loop (repaid, no default) 5
    "consistency": 10,        # 10 with no contradiction; minus 5 per minor contradiction
}
MAX_SCORE = sum(WEIGHTS.values())
DECLINE_BELOW = 40
FULL_FIRST_CAP_FROM = 65
SMALL_FIRST_CAP_USDC = 5.0

# What a reason says. Keyed by factor and the level reached, in words an applicant can act on.
REASON_TEXT = {
    "repayment_source": {
        STATED: "Repayment source not shown: you told us where repayment comes from, but no recent pay stub, statement, sales record or customer order shows it.",
        EVIDENCED: "Repayment source shown by your documents but not yet confirmed by a record we hold.",
    },
    "capacity": {
        "none": "Repayment larger than what is left each month: the monthly repayment is more than the surplus you described.",
        "tight": "Repayment takes most of what is left each month.",
        "stated_only": "Monthly surplus is your estimate only; a statement would confirm it.",
    },
    "purpose": {
        "unevidenced": "Use of the money not shown: no quote, invoice or order supports what you described.",
        "nonproductive": "The purpose does not bring money in, so repayment rests entirely on your other income.",
    },
    "backing_record": {
        "none": "No backer and no deposit: a first loan needs a named person's stake or your own locked deposit.",
        "new": "Your backer (or deposit) has no repayment history in the pool yet.",
    },
    "own_history": {"none": "No repayment history with us yet, and no completed practice loop linked."},
    "consistency": {MINOR: "Something did not add up between what you said and what you showed: "},
}


@dataclass
class Decision:
    policy_version: str
    decision: str                       # "approve" or "decline"
    tier: str                           # "first", "repeat" or "none"
    cap_usdc: float
    score: int
    max_score: int
    components: dict
    reasons: list[str] = field(default_factory=list)     # principal reasons for a decline or a reduced cap, adverse-action style
    hard_rules: list[str] = field(default_factory=list)  # hard rules that fired
    notes: list[str] = field(default_factory=list)
    backing_required_usdc: float = 0.0
    backing_available_usdc: float = 0.0
    extraction_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def approved(self) -> bool:
        return self.decision == "approve"


def score_components(d: Dossier) -> tuple[dict, list[tuple[int, str]]]:
    """Points per factor, and the reasons (points lost, text) for the adverse-action list."""
    comp: dict[str, int] = {}
    lost: list[tuple[int, str]] = []

    status = d.repayment_source_status
    comp["repayment_source"] = {VERIFIED: 30, EVIDENCED: 20, STATED: 8}[status]
    if status != VERIFIED:
        lost.append((30 - comp["repayment_source"], REASON_TEXT["repayment_source"][status]))

    ratio = d.capacity_ratio
    if ratio is None:
        comp["capacity"], why = 0, "none"
    elif ratio <= 0.25:
        comp["capacity"], why = 20, ""
    elif ratio <= 0.5:
        comp["capacity"], why = 12, "tight"
    elif ratio <= 1.0:
        comp["capacity"], why = 5, "tight"
    else:
        comp["capacity"], why = 0, "none"
    if d.surplus_status == STATED and comp["capacity"] > 0:
        comp["capacity"] //= 2
        lost.append((20 - comp["capacity"], REASON_TEXT["capacity"]["stated_only"]))
    elif why:
        lost.append((20 - comp["capacity"], REASON_TEXT["capacity"][why]))

    productive = d.application["purpose_category"] in PRODUCTIVE_PURPOSES
    if productive and d.purpose_status == EVIDENCED:
        comp["purpose"] = 15
    elif productive:
        comp["purpose"] = 8
        lost.append((7, REASON_TEXT["purpose"]["unevidenced"]))
    else:
        comp["purpose"] = 4
        lost.append((11, REASON_TEXT["purpose"]["nonproductive"]))

    if d.backing_usdc <= 0:
        comp["backing_record"] = 0
        lost.append((15, REASON_TEXT["backing_record"]["none"]))
    elif d.backing_kind == "backer" and int(d.backer_record.get("repaid_on_time", 0)) > 0 and int(d.backer_record.get("defaults", 0)) == 0:
        comp["backing_record"] = 15
    else:
        comp["backing_record"] = 8
        lost.append((7, REASON_TEXT["backing_record"]["new"]))

    on_time = int(d.borrower_record.get("repaid_on_time", 0))
    trial_ok = int(d.trial_record.get("repaid", 0)) > 0 and int(d.trial_record.get("defaults", 0)) == 0
    if on_time > 0 and int(d.borrower_record.get("defaults", 0)) == 0:
        comp["own_history"] = 10
    elif trial_ok:
        comp["own_history"] = 5
        lost.append((5, "Practice record counted; a real on-time repayment with us would count more."))
    else:
        comp["own_history"] = 0
        lost.append((10, REASON_TEXT["own_history"]["none"]))

    minors = [c for c in d.contradictions if c.severity == MINOR]
    comp["consistency"] = max(0, 10 - 5 * len(minors))
    for c in minors:
        lost.append((5, REASON_TEXT["consistency"][MINOR] + c.detail))
    return comp, lost


def decide(d: Dossier) -> Decision:
    app = d.application
    comp, lost = score_components(d)
    score = sum(comp.values())
    hard: list[str] = []
    if d.backing_usdc <= 0:
        hard.append("H1 no backing: " + REASON_TEXT["backing_record"]["none"])
    if int(d.borrower_record.get("defaults", 0)) > 0 or int(d.borrower_record.get("open_loans", 0)) > 0:
        hard.append("H2 account record: a default or an open loan in the pool")
    for c in d.contradictions:
        if c.severity == SEVERE:
            hard.append(f"H3 {c.code}: {c.detail}")

    on_time = int(d.borrower_record.get("repaid_on_time", 0))
    tier = "repeat" if on_time > 0 and int(d.borrower_record.get("defaults", 0)) == 0 else "first"
    requested = float(app["amount_usdc"])
    if hard or score < DECLINE_BELOW:
        ordered = [h.split(": ", 1)[1] if ": " in h else h for h in hard] + [text for _, text in sorted(lost, key=lambda x: -x[0])]
        reasons = []
        for text in ordered:
            if text not in reasons:
                reasons.append(text)
        return Decision(POLICY_VERSION, "decline", "none", 0.0, score, MAX_SCORE, comp, reasons[:4], hard,
                        notes=list(d.notes), backing_required_usdc=requested, backing_available_usdc=d.backing_usdc,
                        extraction_cost_usd=d.extraction_cost_usd)

    if tier == "repeat":
        tier_cap = MAX_REPEAT_REQUEST_USDC if score >= FULL_FIRST_CAP_FROM else MAX_FIRST_REQUEST_USDC
    else:
        tier_cap = MAX_FIRST_REQUEST_USDC if score >= FULL_FIRST_CAP_FROM else SMALL_FIRST_CAP_USDC
    cap = min(requested, tier_cap, d.backing_usdc)
    notes = list(d.notes)
    if d.reserve_usdc is not None:
        exposure_cap = float(d.reserve_usdc) * EXPOSURE_SHARE
        if cap > exposure_cap:
            notes.append(f"cap held to a fifth of the reserve ({exposure_cap:.2f} USDC)")
            cap = exposure_cap
    cap = round(cap, 2)
    reasons: list[str] = []
    if cap < requested:
        reasons = [text for _, text in sorted(lost, key=lambda x: -x[0])][:3]
        if d.backing_usdc < requested:
            reasons.insert(0, f"Backing covers {d.backing_usdc:.2f} USDC of the {requested:.2f} asked; the loan is capped at the backing.")
    if app["purpose_category"] in ("order", "bridge"):
        notes.append("simpler route to compare: a customer deposit or prepayment instead of a loan")
    if app["purpose_category"] == "emergency":
        notes.append("simpler route to compare: a grant or a provider payment plan")
    return Decision(POLICY_VERSION, "approve", tier, cap, score, MAX_SCORE, comp, reasons, hard, notes,
                    backing_required_usdc=cap, backing_available_usdc=d.backing_usdc, extraction_cost_usd=d.extraction_cost_usd)


def screen(application: Application, documents=(), pool_record: dict | None = None, today=None, seen_document_owner=None):
    """Interview answers, documents and the pool's record in; dossier and decision out."""
    from .dossier import build_dossier
    dossier = build_dossier(application, list(documents), pool_record, today, seen_document_owner)
    return dossier, decide(dossier)
