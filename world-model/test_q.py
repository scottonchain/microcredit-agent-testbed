import contextlib, io, json, unittest
import q


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = q.main(list(args))
    return rc, buf.getvalue()


class QTest(unittest.TestCase):
    def test_prefix_lists_ids(self):
        rc, out = run("action:bootstrap")
        self.assertEqual(rc, 0)
        self.assertIn("action:bootstrap-candidate-by-next-sync", out)
        self.assertTrue(all(l.startswith("action:bootstrap") for l in out.strip().splitlines()))

    def test_full_record_is_json(self):
        _, out = run("-f", "action:bootstrap-candidate-by-next-sync")
        self.assertEqual(json.loads(out)["id"], "action:bootstrap-candidate-by-next-sync")

    def test_open_filters_done_and_owner(self):
        _, out = run("--open", "c")
        self.assertTrue(out.strip())
        for l in out.strip().splitlines():
            self.assertIn(" claude ", l)
            self.assertNotIn(" done ", l)

    def test_grep_and_contains(self):
        _, out = run("--grep", "manager gate")
        self.assertIn("ev:claude-bootstrap-candidate-pr28-20261008", out)
        _, out = run("contains:manager-gate")
        self.assertIn("manager-gate", out)


if __name__ == "__main__":
    unittest.main()
