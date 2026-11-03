"""Reproduce PolicyEngine US issue 10552: Schedule R initial amount for MFS filers aged 65+.
Law (IRC 22(c)(2)(A)(iii), Schedule R instructions): $3,750 for married filing separately.
PE: select() tests num_qualifying_individuals == 1 before SEPARATE, so an MFS unit (one person) takes $5,000.
"""
import importlib.metadata as md, inspect
from policyengine_us import Simulation
import policyengine_us.variables.gov.irs.credits.elderly_and_disabled.section_22_income as mod  # noqa

def run(wages, year=2021, status="SEPARATE", age=72):
    sit = {
        "people": {"p": {"age": {year: age}, "employment_income": {year: wages}}},
        "tax_units": {"tu": {"members": ["p"], "filing_status": {year: status}}},
        "households": {"hh": {"members": ["p"], "state_code": {year: "TX"}}},
    }
    sim = Simulation(situation=sit)
    out = {}
    for v in ("section_22_income", "elderly_disabled_credit", "income_tax"):
        try:
            out[v] = float(sim.calculate(v, year)[0])
        except Exception as e:  # variable may not exist under this name
            out[v] = f"ERR {type(e).__name__}"
    return out

print("policyengine-us", md.version("policyengine-us"), "policyengine-core", md.version("policyengine-core"))
for w in (14000, 15000):
    print(f"MFS age 72 wages {w} year 2021 ->", run(w))
print("single age 72 wages 14000 year 2021 ->", run(14000, status="SINGLE"))
src = inspect.getsource(mod)
start = src.find("select(")
print("\n--- section_22_income formula excerpt ---")
print(src[max(0, start - 600): start + 700])
