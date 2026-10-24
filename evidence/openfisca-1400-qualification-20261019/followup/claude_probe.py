"""Independent contract probes for OpenFisca issue 1400; run with the pinned checkout on PYTHONPATH."""
import json
import numpy as np
from openfisca_core.taxscales import LinearAverageRateTaxScale, MarginalRateTaxScale

bases = np.array([0., 500., 1000., 1500., 1999., 2000., 2001., 3000., 100000.])
out = {}

# P1: the library's own producer of linear-average scales ends with an infinite bracket.
m = MarginalRateTaxScale()
for t, r in [(0, 0.), (1000, .1), (2000, .3)]:
    m.add_bracket(t, r)
a = m.to_average()
out['to_average_thresholds'] = [str(t) for t in a.thresholds]
out['to_average_rates'] = list(map(float, a.rates))
out['marginal_calc'] = m.calc(bases).tolist()
out['to_average_calc'] = a.calc(bases).tolist()
out['round_trip_equal'] = bool(np.allclose(m.calc(bases), a.calc(bases)))

# P2: the same scale built the way issue 1400 builds it (finite last threshold, no infinite bracket).
f = LinearAverageRateTaxScale()
for t, r in zip(a.thresholds[:-1], a.rates[:-1]):
    f.add_bracket(t, r)
out['finite_thresholds'] = [str(t) for t in f.thresholds]
out['finite_calc'] = f.calc(bases).tolist()
out['finite_matches_producer_below_top'] = bool(np.allclose(f.calc(bases[:5]), a.calc(bases[:5])))
out['finite_matches_producer_at_or_above_top'] = bool(np.allclose(f.calc(bases[5:]), a.calc(bases[5:])))

# P3: within the finite scale class, to_marginal gives a nonzero tail while calc gives zero.
out['finite_to_marginal_tail'] = f.to_marginal().calc(bases[5:]).tolist()
out['finite_calc_tail'] = f.calc(bases[5:]).tolist()

# P4: discontinuity at the top threshold for the finite scale (tax just below vs at the threshold).
eps = np.array([1999.999999, 2000.0])
out['finite_calc_around_top'] = f.calc(eps).tolist()
print(json.dumps(out, indent=1))
