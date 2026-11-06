"""Small offline falsifiers, not an underwriting service or identity verifier.

Inputs are synthetic, already adjudicated facts. No network, keys, model, money,
HTML rendering or script execution. Production adapters must establish provenance.
"""
from dataclasses import dataclass
from decimal import Decimal
from threading import RLock


def amount(x):
    if type(x) not in (int, str, Decimal):
        raise ValueError('exact amount required')
    x = Decimal(x)
    if not x.is_finite() or x < 0:
        raise ValueError('nonnegative finite amount required')
    # Fixture currency: six decimal places, <= 10^12 units. With these bounds,
    # additions below have <= 19 significant digits under Decimal precision 28.
    # Reject sub-unit dust rather than round it into apparently conserved credit.
    if x > Decimal('1000000000000') or x != x.quantize(Decimal('.000001')):
        raise ValueError('outside fixed six-decimal fixture currency bounds')
    return x


@dataclass(frozen=True)
class VerifiedCase:
    controller: str
    group: str
    evidence_id: str
    consent: bool
    independently_reviewed: bool
    expires: int


class Budget:
    """Synthetic issuance ceiling: open exposure + realized loss <= initial cap.

    A consumed evidence ID is never reset, including on repayment. Identity and
    group classification are explicit assumptions, never inferred from wallets.
    Defaulted principal consumes budget; restoring it requires new cash authority
    outside this model. This is deliberately stricter than a revolving balance.
    """
    def __init__(self, total, per_controller, per_group):
        self.total, self.person, self.group = map(amount, (total, per_controller, per_group))
        self.rows = {}
        self.used_evidence = set()
        self.lock = RLock()

    def used(self, field=None, value=None):
        return sum((r['open'] + r['loss'] for r in self.rows.values()
                    if field is None or getattr(r['case'], field) == value), Decimal(0))

    def reserve(self, intent, case, units, now):
        units = amount(units)
        if (not isinstance(case, VerifiedCase) or not intent or units == 0
                or not case.controller or not case.group or not case.evidence_id
                or case.consent is not True or case.independently_reviewed is not True
                or type(case.expires) is not int or type(now) is not int or now >= case.expires):
            raise ValueError('ineligible or expired synthetic case')
        with self.lock:
            if intent in self.rows:
                r = self.rows[intent]
                if (r['case'], r['original']) != (case, units):
                    raise ValueError('changed intent replay')
                return False
            if case.evidence_id in self.used_evidence:
                raise ValueError('recycled evidence')
            if (self.used()+units > self.total
                    or self.used('controller',case.controller)+units > self.person
                    or self.used('group',case.group)+units > self.group):
                raise ValueError('budget exceeded')
            self.rows[intent] = dict(case=case, original=units, open=units,
                                     loss=Decimal(0), outcome=None)
            self.used_evidence.add(case.evidence_id)
            return True

    def settle(self, intent, recovered):
        recovered = amount(recovered)
        with self.lock:
            r = self.rows[intent]
            if recovered > r['original']:
                raise ValueError('recovery exceeds principal')
            if r['outcome'] is not None:
                if r['outcome'] != recovered:
                    raise ValueError('correction needs separate adjudication')
                return False
            r['open'], r['loss'], r['outcome'] = Decimal(0), r['original']-recovered, recovered
            return True


def shadow_decision(case, narrative, graph_weight=0):
    """Structural noninterference illustration; never grants credit or estimates PD.

    Narrative is deliberately unused; high graph trust confers no capability.
    This says nothing about the accuracy/security of a future facts extractor.
    """
    if graph_weight != 0:
        raise ValueError('unvalidated graph contribution')
    return {'mode':'SHADOW_ONLY','pd':None,'capacity':0,
            'reason':'REVIEW_REQUIRED','evidence_id':case.evidence_id}


def cluster_variance(n, exposure, p, rho):
    """Equal exposure/equal Bernoulli p, common pairwise correlation assumption."""
    if type(n) is not int or not 1 <= n <= 1000000:
        raise ValueError('bounded integer count required')
    exposure, p, rho = amount(exposure), amount(p), amount(rho)
    if p > 1 or rho > 1:
        raise ValueError('invalid illustrative portfolio')
    return n*exposure**2*p*(1-p)*(1+(n-1)*rho)


def naive_pagerank_star(k, alpha=0.85):
    """Personalized root -> k Sybils, each self-loop; exact stationary mass.

    Restart only at honest root. Attacker total is alpha regardless of k,
    but a per-identity grant attached to ANY positive rank pays k times.
    """
    if type(k) is not int or k < 1 or not 0 < alpha < 1:
        raise ValueError('invalid graph')
    return (1-alpha, [alpha/k]*k)


def assurance_tier(*, practice, familiar, bounded_exposure, current_evidence,
                   attack, reconciled):
    """Reviewed-candidate routing only; never an authorization or PD estimate."""
    values=(practice,familiar,bounded_exposure,current_evidence,attack,reconciled)
    if any(type(x) is not bool for x in values):
        raise ValueError('explicit boolean assurance facts required')
    if attack or not reconciled:
        return 'T3_HOLD_ISSUANCE'
    if practice:
        return 'T0_ISOLATED_PRACTICE'
    if familiar and bounded_exposure and current_evidence:
        return 'T1_REUSE_EVIDENCE_RECHECK_AFFORDABILITY'
    return 'T2_INDEPENDENT_REVIEW'
