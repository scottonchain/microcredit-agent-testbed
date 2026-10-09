import json
from pathlib import Path
import unittest
from validate_cases import lint


class CaseValidatorTests(unittest.TestCase):
    def test_published_case_ledger_passes(self):
        document = json.loads(Path(__file__).with_name("cases.json").read_text())
        self.assertEqual(lint(document), [])

    def test_malformed_id_and_status_are_errors_not_exceptions(self):
        for field in ("id", "status"):
            for value in ([], {}):
                with self.subTest(field=field, value=value):
                    case = {"id": "email-1", "setup": "setup", "expected": "expected", "tested_by_us": False,
                            "status": "proposed / not-run", "source": "synthetic", field: value}
                    self.assertTrue(lint({"status": "draft", "principle": "unknown", "cases": [case]}))


if __name__ == "__main__":
    unittest.main()
