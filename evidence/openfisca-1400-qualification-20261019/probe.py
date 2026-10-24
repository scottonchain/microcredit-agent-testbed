"""Synthetic qualification of OpenFisca issue1400; no patch or legal-policy claim."""
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import time
import numpy as np
from openfisca_core.taxscales import LinearAverageRateTaxScale
started=time.monotonic()
bases=np.array([0.,500.,1000.,1500.,1999.,2000.,2001.,3000.,100000.])
def make(extra=False):
    scale=LinearAverageRateTaxScale()
    for t,r in [(0,0.),(1000,.1),(2000,.2)]:scale.add_bracket(t,r)
    if extra:scale.add_bracket(float('inf'),.2)
    return scale
finite=make();explicit=make(True)
a=finite.calc(bases);b=explicit.calc(bases);m=finite.to_marginal().calc(bases)
expected=bases*np.interp(bases,[0,1000,2000],[0,.1,.2])
np.testing.assert_allclose(a[:5],expected[:5])
np.testing.assert_allclose(a[5:],np.zeros(4))
np.testing.assert_allclose(b,expected)
np.testing.assert_allclose(m[5:],expected[5:])
single=LinearAverageRateTaxScale();single.add_bracket(0,.2)
np.testing.assert_allclose(single.calc(bases),bases*.2)
assert not np.allclose(m[1:5],expected[1:5]) # Conversion is not an interior interpolation oracle.
print(json.dumps({'python':platform.python_version(),'openfisca_core':importlib.metadata.version('openfisca-core'),'numpy':np.__version__,'bases':bases.tolist(),'finite_calc':a.tolist(),'explicit_infinite_tail_calc':b.tolist(),'linear_average_reference':expected.tolist(),'to_marginal_calc':m.tolist(),'checks':['finite interior matches interpolation','four points at or above top collapse to zero','explicit infinite tail matches reference','conversion tail matches reference','single bracket remains constant','conversion differs in interior; not a global oracle'],'elapsed_seconds':time.monotonic()-started},indent=2))
