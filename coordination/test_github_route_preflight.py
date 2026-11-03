import json
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import github_route_preflight as route
except ImportError:
    import github_route_preflight as route


class RoutePreflightTests(unittest.TestCase):
    def fake(self, push_code=0, push_error="", private_identity=False):
        def run(repo, *args):
            if args[0] == "var":
                email = "private@example.invalid" if private_identity else "codex@users.noreply.github.com"
                return 0, f"Codex (AI) <{email}> 1793548800 +0000\n", ""
            if args[0] == "push":
                self.assertIn("--dry-run", args)
                self.assertNotIn("--force", args)
                return push_code, "", push_error
            return 0, "fixture\n", ""
        return run

    def test_acceptance_is_not_publication_or_persistence(self):
        with patch.object(route, "run_git", self.fake()):
            result = route.inspect("fixture", probe_remote=True)
        self.assertEqual(result["status"], "CANDIDATE_ROUTE_ONLY")
        for field in ("publishes", "authority_granted", "persistent_setup_verified", "protected_lease_verified"):
            self.assertIs(result[field], False)

    def test_no_probe_does_not_claim_ready(self):
        with patch.object(route, "run_git", self.fake()):
            result = route.inspect("fixture")
        self.assertEqual(result["status"], "LOCAL_CHECK_ONLY")

    def test_missing_auth_routes_work_without_echoing_error(self):
        private = "https://hidden:fixture-secret@github.com"
        with patch.object(route, "run_git", self.fake(128, f"could not read Username for {private}")):
            result = route.inspect("fixture", probe_remote=True)
        self.assertEqual(result["remote_probe"], "GIT_AUTHENTICATION_UNAVAILABLE")
        self.assertEqual(result["status"], "ROUTE_NOT_READY")
        self.assertNotIn("fixture-secret", json.dumps(result))

    def test_private_identity_cannot_qualify_route(self):
        with patch.object(route, "run_git", self.fake(private_identity=True)):
            result = route.inspect("fixture", probe_remote=True)
        self.assertEqual(result["status"], "ROUTE_NOT_READY")
        self.assertNotIn("private@example.invalid", json.dumps(result))

    def test_reject_remote_option_injection_without_git(self):
        with patch.object(route, "run_git") as git:
            with self.assertRaises(ValueError):
                route.inspect("fixture", "--receive-pack=anything", True)
            git.assert_not_called()

    def test_unreadable_checkout_safe_static_result(self):
        with tempfile.TemporaryDirectory() as directory:
            result = route.inspect(directory)
        self.assertEqual(result["status"], "NOT_A_READABLE_CHECKOUT")

    def test_failure_categories_do_not_assume_one_root_cause(self):
        self.assertEqual(route.failure_kind("write access to repository not granted"), "REPOSITORY_OR_AUTHORIZATION_FAILURE")
        self.assertEqual(route.failure_kind("proxy rejected 403"), "NETWORK_OR_POLICY_FAILURE")
        self.assertEqual(route.failure_kind("unexpected private detail"), "GIT_OPERATION_FAILED")


if __name__ == "__main__":
    unittest.main()
