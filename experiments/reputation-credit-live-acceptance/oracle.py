"""OFF-CHAIN checking of a PROVISIONAL scoring proposal, never live acceptance.

Source: testbed board 15 comment 6636875903 (2026-11-04 proposal), plus its
mathematical companion as supplied by the task owner. No RPC, signer, production
model, eligibility inference, skill-growth formula or restoration policy exists
here. The ledger is a deliberately small reference state machine for explicit
reservations and labels; its transition conventions are not approved policy.
Money and reputation use Decimal, without rounding to token units.

ARITHMETIC BOUND (provisional reference semantics). Every ledger computation (allocation
sums, locked totals, budgets, penalties and their accumulation) runs in a context of
LEDGER_PRECISION significant digits that TRAPS Inexact: a result that would need more
digits than that raises decimal.Inexact instead of being rounded, so the ledger fails
closed. All state changes happen only after the arithmetic they depend on has succeeded,
so a trapped failure leaves the ledger exactly as it was. display_score() and the analysis
helpers margin()/break_even_charge() are NOT part of this guarantee: display_score uses a
natural logarithm and is an approximation (50 digits) for display only, and the helpers use
the default 28-digit context (they inherit the CALLER's Decimal context, so a caller that changes
the context changes their results; only the ledger pins its own). Neither feeds the ledger.
"""
from dataclasses import dataclass
from decimal import Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow, localcontext
from functools import wraps
from threading import RLock

LEDGER_PRECISION = 60


class ReservationTerminal(ValueError):
    """The reservation identity was already cancelled or settled; it is never reopened."""


class ReportConflict(ValueError):
    """A report or correction identity was reused with a different label."""


def _fail_closed(fn):
    """Run fn in the exact-or-reject arithmetic context (see ARITHMETIC BOUND)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with localcontext(Context(prec=LEDGER_PRECISION, traps=[Inexact, Overflow, InvalidOperation, DivisionByZero])):
            return fn(*args, **kwargs)
    return wrapper


ZERO = Decimal("0")
ONE = Decimal("1")
ETA = Decimal("0.2")


def dec(value):
    """Reject binary floats, NaN and infinity instead of hiding input precision."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("use Decimal, integer or a decimal string")
    result = value if isinstance(value, Decimal) else Decimal(value)
    if not result.is_finite():
        raise ValueError("finite value required")
    return result


def nonnegative(value):
    result = dec(value)
    if result < ZERO:
        raise ValueError("negative amount")
    return result


def probability(value):
    result = dec(value)
    if not ZERO <= result <= ONE:
        raise ValueError("probability outside [0,1]")
    return result


def display_score(p):
    """Raw unrounded score; absent PD stays unavailable; endpoints use limits."""
    if p is None:
        return None
    p = probability(p)
    if p == ZERO:
        return Decimal("850")
    if p == ONE:
        return Decimal("300")
    with localcontext() as ctx:
        ctx.prec = 50
        result = Decimal("600") + Decimal("50") * (((ONE-p)/p)/19).ln()/Decimal(2).ln()
        return min(Decimal("850"), max(Decimal("300"), result))


def margin(p_upper, charge, lgd, principal, operating, funding, capital):
    p, g = probability(p_upper), probability(lgd)
    f, loan, c, k, h = map(nonnegative, (charge, principal, operating, funding, capital))
    return (ONE-p)*f - p*g*loan - c-k-h


def break_even_charge(p_upper, lgd, principal, operating, funding, capital):
    p, g = probability(p_upper), probability(lgd)
    loan, c, k, h = map(nonnegative, (principal, operating, funding, capital))
    if p == ONE:
        raise ValueError("no finite charge can be collected from a nondefault at p=1")
    return (p*g*loan+c+k+h)/(ONE-p)


@dataclass(frozen=True)
class Cashflow:
    """One period's stressed non-loan cashflow; proceeds supplied separately."""
    verified_income: Decimal
    essential_expenses: Decimal
    existing_debt: Decimal
    new_payment: Decimal
    loan_proceeds: Decimal = ZERO


def affordability(initial_nonloan_liquidity, periods):
    """Return every cumulative balance and feasibility at every payment date.

    This checks a supplied stress timeline, not whether income is verified or
    essential spending is adequate. Loan proceeds are excluded from repayment
    resources; they are validated only to reject malformed fixtures.
    """
    balance = nonnegative(initial_nonloan_liquidity)
    balances = []
    for row in periods:
        income, essentials, existing, new, _ = map(nonnegative, (
            row.verified_income, row.essential_expenses, row.existing_debt,
            row.new_payment, row.loan_proceeds))
        balance += income-essentials-existing-new
        balances.append(balance)
    return tuple(balances), all(x >= ZERO for x in balances)


@_fail_closed
def root_budget(target_reputation, cumulative_penalty):
    target, penalty = map(nonnegative, (target_reputation, cumulative_penalty))
    return max(ZERO, ETA*target-penalty)


@_fail_closed
def brier_penalty(units, forecast_pd, defaulted):
    if type(defaulted) is not bool:
        raise ValueError("frozen default label must be boolean")
    return nonnegative(units)*(probability(forecast_pd)-int(defaulted))**2


@dataclass(frozen=True)
class Allocation:
    """Path includes original root and leaf borrower; u is not re-pledged."""
    path: tuple
    units: Decimal


@dataclass(frozen=True)
class Reservation:
    loan: str
    root: str
    units: Decimal
    forecast_pd: Decimal
    allocations: tuple


@dataclass
class Outcome:
    defaulted: bool
    penalty: Decimal
    report_id: str


class ReputationLedger:
    """Illustrative atomic ledger, not eligibility/approval or skill estimation.

    Target reputation is an externally supplied value. A target decrease never
    cancels existing locks; new allocations must fit the resulting budget. Paths
    only explain allocation of one original root's reserved units. Received path
    influence creates no ledger balance for intermediate identities.
    """
    def __init__(self):
        self.reports = {}  # (loan, root) -> {report or correction identity: the label it carried}
        self.targets = {}
        self.penalties = {}
        self.open = {}
        self.history = {}
        self.outcomes = {}
        self.cancelled = set()
        self.skill_updates = {}
        self.corrections = {}
        self._lock = RLock()

    def set_target(self, root, target):
        """Supply a separately justified target; never derive restoration here."""
        target = nonnegative(target)
        if not root or target > 100:
            raise ValueError("candidate target must be in [0,100] with a named root")
        with self._lock:
            self.targets[root] = target
            self.penalties.setdefault(root, ZERO)

    @_fail_closed
    def budget(self, root):
        return root_budget(self.targets[root], self.penalties[root])

    @_fail_closed
    def locked(self, root):
        return sum((v.units for v in self.open.values() if v.root == root), ZERO)

    @_fail_closed
    def available(self, root):
        return max(ZERO, self.budget(root)-self.locked(root))

    @_fail_closed
    def reserve(self, loan, root, units, forecast_pd, allocations):
        """Return True when a new reservation is created, False for an exact retry of an
        ACTIVE reservation, so False always means that a lock exists. A cancelled or settled
        identity is terminal: an identical retry raises ReservationTerminal and a retry with
        changed fields raises ValueError, so neither can be mistaken for an open lock."""
        units, forecast = nonnegative(units), probability(forecast_pd)
        allocations = tuple(Allocation(tuple(a.path), nonnegative(a.units)) for a in allocations)
        if not loan or not root or units == ZERO or not allocations:
            raise ValueError("named loan/root and positive allocation required")
        if sum((a.units for a in allocations), ZERO) != units:
            raise ValueError("path allocations must sum to original root reservation")
        paths, leafs = set(), set()
        for a in allocations:
            if (a.units == ZERO or len(a.path) not in (2, 3) or a.path[0] != root
                    or any(not node for node in a.path) or len(set(a.path)) != len(a.path)):
                raise ValueError("positive, acyclic, origin-tagged path of at most two hops required")
            if a.path in paths:
                raise ValueError("duplicate path")
            paths.add(a.path)
            leafs.add(a.path[-1])
        if len(leafs) != 1:
            raise ValueError("one exact loan borrower required")
        reservation = Reservation(loan, root, units, forecast, allocations)
        key = (loan, root)
        with self._lock:
            if key in self.history:
                if self.history[key] != reservation:
                    raise ValueError("reservation identity reused with changed fields")
                if key in self.open:
                    return False  # exact retry of an active reservation
                raise ReservationTerminal("reservation identity is %s and is never reopened"
                                          % ("settled" if key in self.outcomes else "cancelled"))
            if root not in self.targets or self.locked(root)+units > self.budget(root):
                raise ValueError("root budget exhausted or root unavailable")
            self.open[key] = self.history[key] = reservation
            return True

    def cancel_before_disbursement(self, loan, root):
        """Caller must separately prove no disbursement; no skill/label update."""
        key = (loan, root)
        with self._lock:
            if key in self.cancelled:
                return False
            if key not in self.open:
                raise ValueError("no open reservation")
            del self.open[key]
            self.cancelled.add(key)
            return True

    @_fail_closed
    def settle(self, loan, root, defaulted, report_id):
        """First application returns True. An exact replay of ANY identity already applied
        to this loan (the original report, or a later correction) is a no-op that returns
        False and keeps the current, possibly corrected, outcome. The same identity with a
        different label raises ReportConflict. A NEW identity that disagrees with the
        recorded outcome needs an explicit correct()."""
        key = (loan, root)
        if not report_id:
            raise ValueError("authoritative report identity required")
        # Validate even duplicate inputs, rather than accepting malformed labels.
        if type(defaulted) is not bool:
            raise ValueError("frozen default label must be boolean")
        with self._lock:
            seen = self.reports.get(key, {})
            if report_id in seen:
                if seen[report_id] == defaulted:
                    return False
                raise ReportConflict("report identity reused with changed label")
            if key in self.outcomes:
                raise ValueError("already settled; explicit authoritative correction required")
            if key not in self.open:
                raise ValueError("no open reservation")
            reservation = self.open[key]
            penalty = brier_penalty(reservation.units, reservation.forecast_pd, defaulted)
            total = self.penalties[root] + penalty  # all arithmetic first; a trapped failure leaves the reservation open
            del self.open[key]
            self.penalties[root] = total
            self.outcomes[key] = Outcome(defaulted, penalty, report_id)
            self.skill_updates[key] = 1
            self.reports.setdefault(key, {})[report_id] = defaulted
            return True

    @_fail_closed
    def correct(self, loan, root, defaulted, correction_id):
        """Replace one upheld outcome label; not discretionary reputation reset.

        A correction updates one existing skill record, not another observation.
        Authority, appeal eligibility and immutable evidence provenance must be
        supplied/verified by a future adapter; this method does not infer them.
        Report and correction identities share one namespace per loan: an exact replay of
        any of them is a no-op (False); reuse with a different label raises ReportConflict.
        """
        key = (loan, root)
        if type(defaulted) is not bool:
            raise ValueError("frozen default label must be boolean")
        if not correction_id:
            raise ValueError("correction identity required")
        with self._lock:
            seen = self.reports.get(key, {})
            if correction_id in seen:
                if seen[correction_id] == defaulted:
                    return False
                raise ReportConflict("identity reused with changed label")
            if key not in self.outcomes:
                raise ValueError("only resolved loan outcomes can be corrected")
            previous = self.outcomes[key]
            reservation = self.history[key]
            penalty = brier_penalty(reservation.units, reservation.forecast_pd, defaulted)
            total = self.penalties[root] + (penalty - previous.penalty)  # arithmetic before any mutation
            self.penalties[root] = total
            self.outcomes[key] = Outcome(defaulted, penalty, correction_id)
            self.corrections[(key, correction_id)] = defaulted
            self.reports.setdefault(key, {})[correction_id] = defaulted
            return True

    def independent_roots(self, loan):
        """Return source roots, never graph path count or wallet independence.

        PROVISIONAL REFERENCE SEMANTICS: every reservation identity ever recorded for the loan
        counts, including cancelled and settled ones. Whether a cancelled reservation should
        count toward independence is finalized mechanism policy, not decided here."""
        with self._lock:
            return frozenset(root for name, root in self.history if name == loan)
