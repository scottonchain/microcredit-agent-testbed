"""Offline release verification regressions; importing this file performs no I/O."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_release_asset as check

DATA = b"synthetic release asset"
COMMIT = "a" * 40
URL = "https://github.com/example/replay/releases/download/v1/fixture.tar.gz"


class ReleaseAssetTests(unittest.TestCase):
    def setUp(self):
        self.reveal = {"repo": "example/replay", "release_tag": "v1", "release_commit": COMMIT,
                       "asset_id": 12, "asset_name": "fixture.tar.gz", "byte_count": len(DATA),
                       "sha256": hashlib.sha256(DATA).hexdigest(), "url": URL}
        self.asset = {"id": 12, "name": "fixture.tar.gz", "size": len(DATA), "browser_download_url": URL}
        self.release = {"target_commitish": COMMIT, "assets": [self.asset]}

    def run_check(self, *, reveal=None, release=None, objects=None, data=DATA):
        responses = [release or self.release, *(objects or [{"object": {"type": "commit", "sha": COMMIT}}])]
        with tempfile.TemporaryDirectory() as directory, patch.object(check, "get_json", side_effect=responses), patch.object(check.urllib.request, "urlopen", return_value=io.BytesIO(data)):
            message = check.verify(reveal or self.reveal, directory)
            self.assertEqual((Path(directory) / "fixture.tar.gz").read_bytes(), DATA)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            return message

    def test_matching_identity_tag_and_bytes(self):
        self.assertTrue(self.run_check().startswith("OK"))

    def test_moved_tag_rejected_even_when_release_target_matches(self):
        with self.assertRaisesRegex(check.VerificationError, "RELEASE_COMMIT_MISMATCH"):
            self.run_check(objects=[{"object": {"type": "commit", "sha": "b" * 40}}])

    def test_annotated_tag_resolves_to_commit(self):
        self.assertTrue(self.run_check(objects=[{"object": {"type": "tag", "sha": "b" * 40}},
                                               {"object": {"type": "commit", "sha": COMMIT}}]).startswith("OK"))

    def test_cyclic_tag_rejected(self):
        with self.assertRaisesRegex(check.VerificationError, "cyclic tag"):
            self.run_check(objects=[{"object": {"type": "tag", "sha": "b" * 40}}] * 2)

    def test_wrong_id_size_or_name_rejected(self):
        for key, value, expected in (("asset_id", 13, "REPLACED"), ("byte_count", 0, "REPLACED"), ("asset_name", "missing.zip", "MISSING")):
            with self.subTest(key=key), self.assertRaisesRegex(check.VerificationError, expected):
                self.run_check(reveal={**self.reveal, key: value})

    def test_wrong_digest_rejected(self):
        with self.assertRaisesRegex(check.VerificationError, "RELEASE_ASSET_REPLACED"):
            self.run_check(reveal={**self.reveal, "sha256": "0" * 64})

    def test_wrong_url_rejected(self):
        with self.assertRaisesRegex(check.VerificationError, "download URL"):
            self.run_check(reveal={**self.reveal, "url": URL + ".changed"})

    def test_path_escape_rejected_before_network(self):
        with patch.object(check, "get_json") as get:
            for filename in ("../escape", "/absolute", "..\\escape", ".."):
                with self.subTest(filename=filename), self.assertRaisesRegex(check.VerificationError, "filename"):
                    check.verify({**self.reveal, "asset_name": filename}, ".")
        get.assert_not_called()

    def test_corrupt_download_preserves_existing_verified_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / self.reveal["asset_name"]
            destination.write_bytes(b"previous verified bytes")
            with patch.object(check, "get_json", side_effect=[self.release, {"object": {"type": "commit", "sha": COMMIT}}]), patch.object(check.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaises(check.VerificationError):
                    check.verify(self.reveal, directory)
            self.assertEqual(destination.read_bytes(), b"previous verified bytes")
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_transport_error_cleans_partial_download(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(check, "get_json", side_effect=[self.release, {"object": {"type": "commit", "sha": COMMIT}}]), patch.object(check.urllib.request, "urlopen", side_effect=OSError("connection lost")):
            with self.assertRaises(OSError):
                check.verify(self.reveal, directory)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
