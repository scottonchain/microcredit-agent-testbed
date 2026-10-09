import contextlib, io, json, unittest
from unittest.mock import patch
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

    def test_codex_lane_includes_coordinator_obligations(self):
        actions = [
            {"id": "action:codex-open", "owner_id": "agent:codex", "status": "ready"},
            {"id": "action:coordinator-open", "owner_id": "agent:coordinator", "status": "ready"},
            {"id": "action:claude-open", "owner_id": "agent:claude", "status": "ready"},
            {"id": "action:hermes-open", "owner_id": "agent:hermes", "status": "ready"},
            {"id": "action:codex-done", "owner_id": "agent:codex", "status": "done"},
            {"id": "action:coordinator-cancelled", "owner_id": "agent:coordinator", "status": "cancelled"},
        ]
        with patch.object(q, "load", return_value=({"actions": actions}, {})):
            _, out = run("--open", "x")
            _, exact = run("--open", "agent:codex")
        ids = {line.split()[0] for line in out.splitlines()}
        self.assertEqual(ids, {"action:codex-open", "action:coordinator-open"})
        self.assertEqual({line.split()[0] for line in exact.splitlines()}, {"action:codex-open"})

    def test_goal_names_are_visible_without_dumping_full_records(self):
        _, out = run("goal:poverty")
        self.assertIn("Measurable alleviation of human poverty", out)

    def test_missing_arguments_unknown_ids_and_invalid_hours_have_usage_errors(self):
        for arguments in (("-f",), ("-f", "action:missing"), ("--grep",), ("--due", "nan"), ("--due", "-1"), ("--due", "inf")):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                run(*arguments)
            self.assertEqual(result.exception.code, 2)

    def test_grep_and_contains(self):
        _, out = run("--grep", "manager gate")
        self.assertIn("ev:claude-bootstrap-candidate-pr28-20261008", out)
        _, out = run("contains:manager-gate")
        self.assertIn("manager-gate", out)


if __name__ == "__main__":
    unittest.main()
