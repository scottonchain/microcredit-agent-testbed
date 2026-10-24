import sys
from policyengine_us import CountryTaxBenefitSystem
from policyengine_core.tools.test_runner import run_tests
sys.exit(run_tests(CountryTaxBenefitSystem(),[sys.argv[1]]))
