"""Proposed finite-tail contract from issue1400; expected to fail on pinned source."""
import numpy as np
from openfisca_core.taxscales import LinearAverageRateTaxScale
scale=LinearAverageRateTaxScale()
for threshold,rate in [(0,0.),(1000,.1),(2000,.2)]:
    scale.add_bracket(threshold,rate)
np.testing.assert_allclose(scale.calc(np.array([2000.,3000.])),[400.,600.])
