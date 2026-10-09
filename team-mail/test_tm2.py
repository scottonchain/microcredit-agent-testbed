import copy, glob, json, os, unittest
from pathlib import Path
import tm2

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "..", "world-model", "model.json")


class Tm2Test(unittest.TestCase):
    def examples(self, sub="tm2"):
        for f in sorted(glob.glob(os.path.join(HERE, "examples", sub, "*.json"))):
            yield f, json.loads(Path(f).read_text(encoding="utf-8"))

    def test_examples_validate_against_model(self):
        m = json.loads(Path(MODEL).read_text(encoding="utf-8"))
        ids = {x["id"] for k in ("entities", "evidence", "claims", "edges", "hypotheses", "actions", "decisions", "open_questions") for x in m[k]}
        for sub in ("tm2", "native"):
            for f, msg in self.examples(sub):
                self.assertEqual(tm2.validate(msg, ids), [], f)

    def test_every_example_has_an_original_and_is_smaller(self):
        for f, _ in self.examples():
            o = f.replace("/tm2/", "/tm1/")
            self.assertTrue(os.path.exists(o), o)
            self.assertLess(os.path.getsize(f), os.path.getsize(o), f)

    def base(self):
        return copy.deepcopy(json.loads((Path(HERE) / "examples/tm2/pool-funding.json").read_text(encoding="utf-8")))

    def bad(self, mutate, needle):
        m = self.base(); mutate(m)
        errs = tm2.validate(m)
        self.assertTrue(any(needle in e for e in errs), (needle, errs))

    def test_rejections(self):
        self.bad(lambda m: m.update(v=1), "v must be 2")
        self.bad(lambda m: m.update(id="x-20261008-pool-funding-r1"), "id letter")
        self.bad(lambda m: m.update(id="bad"), "bad id")
        self.bad(lambda m: m.update(k="coordinate"), "bad k")
        self.bad(lambda m: m.update(t=["c"]), "bad t")
        self.bad(lambda m: m.update(by="2026-10-08 10:00"), "bad by")
        self.bad(lambda m: m.update(extra=1), "unknown key")
        self.bad(lambda m: m["i"][0].update(op="redirect"), "bad op")
        self.bad(lambda m: m["i"][0].update(st="in_progress"), "bad st")
        self.bad(lambda m: m["i"][0].update(d="2026-10-19"), "bad d")
        self.bad(lambda m: m["i"][0].update(e=["see the board"]), "bad ref")
        self.bad(lambda m: m["i"][0].update(x="a" * 501), "> 500")
        self.bad(lambda m: m["i"][0].update(x="café"), "non-ASCII")
        self.bad(lambda m: m["i"][0].update(q=[{"o": "z", "a": "x"}]), "o in c|x|h")
        self.bad(lambda m: m["i"][0].update(n={"a": 1}), "n must be")
        self.bad(lambda m: m.update(i=[]), "1..8 items")
        self.bad(lambda m: m.update(rs="sent"), "bad rs")
        self.bad(lambda m: m["i"][0].update(tx=True), "tx must be 1")
        self.bad(lambda m: m["i"][0].update(x="a" * 400, n={f"k{i}": "b" * 400 for i in range(16)}), "bytes >")

    def test_unknown_model_id_is_flagged(self):
        m = self.base(); m["i"][0]["w"] = "action:no-such-action-xyz"
        self.assertTrue(any("not in model" in e for e in tm2.validate(m, {"action:pool-funding-20261019"})))

    def test_malformed_json_types_return_errors_not_exceptions(self):
        for field in ("f", "k", "rs", "t", "cc"):
            for value in ([], {}, [[], {}]):
                with self.subTest(field=field, value=value):
                    message = self.base()
                    message[field] = value
                    self.assertTrue(tm2.validate(message))
        for field in ("w", "op", "st", "o", "oa"):
            for value in ([], {}):
                with self.subTest(field=field, value=value):
                    message = self.base()
                    message["i"][0][field] = value
                    self.assertTrue(tm2.validate(message, set()))
        self.bad(lambda m: m.update(nd=[{"o": [], "a": "ask"}]), "o in c|x|h")

    def test_invalid_calendar_dates_and_empty_reply_lists(self):
        for date in ("2026-02-30T12:00Z", "2026-13-01T12:00Z", "2026-10-01T24:00Z"):
            self.bad(lambda m: m.update(by=date), "bad by")
        self.bad(lambda m: m.update(re=[]), "bad re")
        self.bad(lambda m: m.update(v=2.0), "v must be 2")
        self.bad(lambda m: m.update(t=["h", "h"]), "bad t")

    def test_nonfinite_json_is_rejected(self):
        message = self.base()
        message["i"][0]["n"] = {"hyp": float("nan")}
        self.assertIn("not a finite JSON value", tm2.validate(message))

    def test_dump_is_compact_ascii(self):
        s = tm2.dump(self.base())
        self.assertTrue(s.isascii())
        self.assertEqual(s, json.dumps(json.loads(s), separators=(",", ":")))
        self.assertEqual(tm2.subject(self.base()), "TM2 req c-20261008-pool-funding-r1")


if __name__ == "__main__":
    unittest.main()
