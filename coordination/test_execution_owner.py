import contextlib
import copy
import io
import json
import os
import tempfile
import unittest

try:
    from . import execution_owner as eo
except ImportError:
    import execution_owner as eo

T0 = "2026-11-01T18:00:00Z"
T1 = "2026-11-01T18:05:00Z"
T2 = "2026-11-01T18:10:00Z"
T3 = "2026-11-01T18:20:00Z"
DEADLINE = "2026-11-01T19:00:00Z"
RECEIPT_OPENAI = "gh:tb#15c6561999999"


def base():
    return eo.load(eo.CONFIG_PATH)


class ConfigTests(unittest.TestCase):
    def test_shipped_config_is_valid_and_claude_owns_heavy_work(self):
        cfg = base()
        self.assertEqual(eo.validate(cfg), [])
        self.assertEqual(cfg["owner"], "claude")
        self.assertEqual(cfg["default_owner"], "openai")
        self.assertEqual(cfg["override"]["effective_at_utc"], "2026-11-01T17:29:00Z")
        self.assertEqual(cfg["transition"]["state"], "stable")

    def test_invalid_configs_are_rejected(self):
        for mutate, text in [
            (lambda c: c.update(owner="gpt"), "owner"),
            (lambda c: c.update(schema_version=9), "schema_version"),
            (lambda c: c["override"].update(owner="openai"), "override.owner"),
            (lambda c: c["override"].update(reason=" "), "override.reason"),
            (lambda c: c["acceptance"]["claude"].update(receipt=None), "both a time and a receipt"),
            (lambda c: c["acceptance"]["claude"].update(receipt="trust me"), "receipt"),
            (lambda c: c["transition"].update(state="draining"), "transition"),
            (lambda c: c["transition"].update(reason="stale"), "null while stable"),
            (lambda c: c.update(lease_owner="human"), "lease_owner"),
            (lambda c: c["override"].update(effective_at_utc="yesterday"), "effective_at_utc"),
        ]:
            cfg = base()
            mutate(cfg)
            problems = eo.validate(cfg)
            self.assertTrue(any(text in p for p in problems), (text, problems))
            with self.assertRaises(eo.ConfigError):
                eo.decide(cfg, "claude", "scheduled")


class RoutingTests(unittest.TestCase):
    def test_scheduled_and_other_heavy_work_follow_the_owner(self):
        cfg = base()
        for kind in eo.HEAVY_KINDS:
            self.assertTrue(eo.decide(cfg, "claude", kind)["allowed"], kind)
            denied = eo.decide(cfg, "openai", kind)
            self.assertFalse(denied["allowed"], kind)
            self.assertEqual(denied["exit_code"], eo.EXIT_SUPPRESSED)

    def test_light_work_is_open_to_both_lanes_in_every_state(self):
        for cfg in (base(), self.draining()):
            for kind in eo.LIGHT_KINDS:
                for lane in eo.LANES:
                    self.assertTrue(eo.decide(cfg, lane, kind)["allowed"], (kind, lane))

    def draining(self):
        return eo.request_switch(base(), to="openai", by="claude", reason="Claude token budget",
                                 drain_deadline_utc=DEADLINE, now=T0)

    def test_nobody_starts_heavy_work_during_a_switch(self):
        cfg = self.draining()
        for kind in eo.HEAVY_KINDS:
            for lane in eo.LANES:
                result = eo.decide(cfg, lane, kind)
                self.assertFalse(result["allowed"])
                self.assertEqual(result["exit_code"], eo.EXIT_TRANSITION)

    def test_only_the_source_lane_may_drain(self):
        cfg = self.draining()
        self.assertTrue(eo.decide(cfg, "claude", "drain")["allowed"])
        self.assertFalse(eo.decide(cfg, "openai", "drain")["allowed"])
        self.assertFalse(eo.decide(base(), "claude", "drain")["allowed"])

    def test_unknown_runner_or_kind_is_an_error(self):
        with self.assertRaises(eo.ConfigError):
            eo.decide(base(), "gemini", "scheduled")
        with self.assertRaises(eo.ConfigError):
            eo.decide(base(), "claude", "magic")


class SwitchTests(unittest.TestCase):
    def full_switch(self, accepted_at=T1):
        cfg = eo.request_switch(base(), to="openai", by="claude", reason="Claude token budget",
                                drain_deadline_utc=DEADLINE, now=T0)
        cfg = eo.accept(cfg, by="openai", receipt=RECEIPT_OPENAI, now=accepted_at)
        cfg = eo.drained(cfg, by="claude", in_flight=0, lease_released=True, now=T2)
        return cfg

    def test_switch_back_to_openai_completes_in_four_steps(self):
        cfg = self.full_switch()
        self.assertEqual(cfg["transition"]["state"], "handover")
        done = eo.complete(cfg, by="openai", lease_head="a1b2c3d4e5", now=T3)
        self.assertEqual(done["owner"], "openai")
        self.assertEqual(done["transition"]["state"], "stable")
        self.assertEqual(done["lease_owner"], "openai")
        self.assertEqual(done["override"]["declared_by"], "claude")
        self.assertEqual(done["config_version"], base()["config_version"] + 4)
        self.assertEqual([h["event"] for h in done["history"][-4:]], ["request", "accept", "drained", "complete"])
        self.assertEqual(eo.validate(done), [])
        self.assertTrue(eo.decide(done, "openai", "scheduled")["allowed"])
        self.assertFalse(eo.decide(done, "claude", "scheduled")["allowed"])

    def test_switch_back_is_refused_without_fresh_acceptance(self):
        cfg = eo.request_switch(base(), to="openai", by="claude", reason="Claude token budget",
                                drain_deadline_utc=DEADLINE, now=T1)
        cfg = eo.accept(cfg, by="openai", receipt=RECEIPT_OPENAI, now=T0)  # earlier than the request
        cfg = eo.drained(cfg, by="claude", in_flight=0, lease_released=True, now=T2)
        with self.assertRaises(eo.ConfigError) as caught:
            eo.complete(cfg, by="openai", lease_head="a1b2c3d4e5", now=T3)
        self.assertIn("accepted since this request", str(caught.exception))

    def test_switch_is_refused_with_no_acceptance_at_all(self):
        cfg = eo.request_switch(base(), to="openai", by="claude", reason="r", drain_deadline_utc=DEADLINE, now=T0)
        cfg = eo.drained(cfg, by="claude", in_flight=0, lease_released=True, now=T2)
        with self.assertRaises(eo.ConfigError):
            eo.complete(cfg, by="openai", lease_head="a1b2c3d4e5", now=T3)

    def test_only_the_right_lane_can_drain_and_complete(self):
        cfg = eo.accept(eo.request_switch(base(), to="openai", by="claude", reason="r",
                                          drain_deadline_utc=DEADLINE, now=T0),
                        by="openai", receipt=RECEIPT_OPENAI, now=T1)
        with self.assertRaises(eo.ConfigError):
            eo.drained(cfg, by="openai", in_flight=0, lease_released=True, now=T2)
        with self.assertRaises(eo.ConfigError):
            eo.drained(cfg, by="claude", in_flight=2, lease_released=True, now=T2)
        with self.assertRaises(eo.ConfigError):
            eo.drained(cfg, by="claude", in_flight=0, lease_released=False, now=T2)
        handover = eo.drained(cfg, by="claude", in_flight=0, lease_released=True, now=T2)
        with self.assertRaises(eo.ConfigError):
            eo.complete(handover, by="claude", lease_head="a1b2c3d4e5", now=T3)
        with self.assertRaises(eo.ConfigError):
            eo.complete(handover, by="openai", lease_head="not a head", now=T3)
        with self.assertRaises(eo.ConfigError):
            eo.complete(cfg, by="openai", lease_head="a1b2c3d4e5", now=T3)  # not drained yet

    def test_duplicate_request_is_deduplicated_and_a_conflicting_one_is_refused(self):
        first = eo.request_switch(base(), to="openai", by="claude", reason="r", drain_deadline_utc=DEADLINE, now=T0)
        again = eo.request_switch(first, to="openai", by="claude", reason="r", drain_deadline_utc=DEADLINE, now=T1)
        self.assertIs(again, first)
        self.assertEqual(again["config_version"], base()["config_version"] + 1)
        with self.assertRaises(eo.ConfigError):
            eo.request_switch(first, to="openai", by="openai", reason="r", drain_deadline_utc=DEADLINE, now=T1)

    def test_request_rules(self):
        with self.assertRaises(eo.ConfigError):
            eo.request_switch(base(), to="claude", by="openai", reason="r", drain_deadline_utc=DEADLINE, now=T0)
        with self.assertRaises(eo.ConfigError):
            eo.request_switch(base(), to="openai", by="claude", reason=" ", drain_deadline_utc=DEADLINE, now=T0)
        with self.assertRaises(eo.ConfigError):
            eo.request_switch(base(), to="openai", by="claude", reason="r", drain_deadline_utc=T0, now=T0)
        with self.assertRaises(eo.ConfigError):
            eo.request_switch(base(), to="openai", by="nobody", reason="r", drain_deadline_utc=DEADLINE, now=T0)

    def test_either_lane_can_declare_low_tokens_and_cancel(self):
        # Claude low on tokens asks OpenAI to take over; OpenAI cancels; ownership never moved.
        cfg = eo.request_switch(base(), to="openai", by="claude", reason="Claude token budget",
                                drain_deadline_utc=DEADLINE, now=T0)
        back = eo.cancel(cfg, by="openai", now=T1)
        self.assertEqual(back["owner"], "claude")
        self.assertEqual(back["transition"]["state"], "stable")
        self.assertEqual(back["history"][-1]["event"], "cancel")
        self.assertIs(eo.cancel(back, by="openai", now=T2), back)
        self.assertTrue(eo.decide(back, "claude", "scheduled")["allowed"])

    def test_default_owner_does_not_override_the_current_owner(self):
        cfg = base()
        self.assertNotEqual(cfg["owner"], cfg["default_owner"])
        self.assertFalse(eo.decide(cfg, cfg["default_owner"], "scheduled")["allowed"])

    def test_stale_switch_is_flagged_not_completed(self):
        cfg = eo.request_switch(base(), to="openai", by="claude", reason="r", drain_deadline_utc=DEADLINE, now=T0)
        late = eo.status(cfg, now="2026-11-01T19:30:00Z")
        self.assertTrue(late["switch_past_deadline"])
        self.assertEqual(late["state"], "draining")
        self.assertEqual(late["heavy_work"], {"openai": False, "claude": False})

    def test_accept_requires_a_reference(self):
        with self.assertRaises(eo.ConfigError):
            eo.accept(base(), by="openai", receipt="I agree", now=T0)

    def test_inputs_are_not_mutated(self):
        cfg = base()
        snapshot = copy.deepcopy(cfg)
        eo.request_switch(cfg, to="openai", by="claude", reason="r", drain_deadline_utc=DEADLINE, now=T0)
        self.assertEqual(cfg, snapshot)


class CliTests(unittest.TestCase):
    def run_cli(self, path, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = eo.main(["--config", path, *args])
        return code, out.getvalue(), err.getvalue()

    def test_check_exit_codes_and_a_full_cli_handover(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "cfg.json")
            eo.save(base(), path)
            self.assertEqual(self.run_cli(path, "check", "--runner", "claude", "--kind", "scheduled")[0], eo.EXIT_ALLOWED)
            self.assertEqual(self.run_cli(path, "check", "--runner", "openai", "--kind", "other")[0], eo.EXIT_SUPPRESSED)
            self.assertEqual(self.run_cli(path, "check", "--runner", "openai", "--kind", "review")[0], eo.EXIT_ALLOWED)
            steps = [
                ("--now", T0, "request", "--to", "openai", "--by", "claude", "--reason", "Claude token budget",
                 "--drain-deadline", DEADLINE),
                ("--now", T1, "accept", "--by", "openai", "--receipt", RECEIPT_OPENAI),
                ("--now", T2, "drained", "--by", "claude", "--in-flight", "0", "--lease-released"),
            ]
            for step in steps:
                self.assertEqual(self.run_cli(path, *step)[0], eo.EXIT_ALLOWED, step)
            self.assertEqual(self.run_cli(path, "check", "--runner", "claude", "--kind", "scheduled")[0],
                             eo.EXIT_TRANSITION)
            self.assertEqual(self.run_cli(path, "--now", T3, "complete", "--by", "openai", "--lease-head", "a1b2c3d")[0],
                             eo.EXIT_ALLOWED)
            self.assertEqual(self.run_cli(path, "check", "--runner", "openai", "--kind", "scheduled")[0], eo.EXIT_ALLOWED)
            self.assertEqual(self.run_cli(path, "check", "--runner", "claude", "--kind", "scheduled")[0], eo.EXIT_SUPPRESSED)
            self.assertEqual(eo.validate(eo.load(path)), [])

    def test_invalid_file_and_illegal_step_exit_2_and_leave_the_file_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "cfg.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not json")
            self.assertEqual(self.run_cli(path, "status")[0], eo.EXIT_INVALID)
            eo.save(base(), path)
            with open(path, encoding="utf-8") as handle:
                before = handle.read()
            code, _, err = self.run_cli(path, "--now", T0, "complete", "--by", "openai", "--lease-head", "a1b2c3d")
            self.assertEqual(code, eo.EXIT_INVALID)
            self.assertIn("error", json.loads(err))
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), before)


if __name__ == "__main__":
    unittest.main()
