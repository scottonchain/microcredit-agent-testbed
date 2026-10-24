"""Is the zero tail reachable from a parameter file? Builds an average_rate ParameterScale with a finite last threshold."""
import numpy as np
from openfisca_core.parameters import ParameterScale

data = {"brackets": [
    {"threshold": {"2020-01-01": {"value": 0}}, "average_rate": {"2020-01-01": {"value": 0.0}}},
    {"threshold": {"2020-01-01": {"value": 1000}}, "average_rate": {"2020-01-01": {"value": 0.1}}},
    {"threshold": {"2020-01-01": {"value": 2000}}, "average_rate": {"2020-01-01": {"value": 0.2}}},
]}
scale = ParameterScale("claude_probe.scale", data, "claude_probe.yaml")
at = scale.get_at_instant("2020-01-01")
print(type(at).__name__, [str(t) for t in at.thresholds])
print(at.calc(np.array([1500., 1999., 2000., 3000.])).tolist())
