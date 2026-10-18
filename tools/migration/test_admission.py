from __future__ import annotations

import copy
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import admission
from rehearse import PreflightError, canonical, digest, git


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "Synthetic fixture")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "selected.txt").write_text("selected source\n")
        (self.repo / "excluded.txt").write_text("private recovery fixture\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture")
        self.pin = git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.tree = git(self.repo, "rev-parse", "HEAD^{tree}").decode().strip()
        git(self.repo, "tag", "-am", "original review", "evidence/original")
        git(self.repo, "branch", "private-research")
        self.manifest = {"format": 1, "mode": "preflight-only", "graph": {"source": "example", "path": "graph.json"},
                         "sources": [{"name": "example", "directory": "source", "repository": "example/source",
                                      "visibility": "private", "commit": self.pin, "tree": self.tree,
                                      "rules": [{"id": "selected", "path": "selected.txt", "action": "retain",
                                                 "destination": "selected.txt", "reason": "synthetic authorized source"}],
                                      "default": {"id": "private", "action": "exclude", "reason": "private history only"}}]}

    def test_restore_all_refs_including_annotated_tags_without_changing_source(self):
        before = git(self.repo, "show-ref")
        report = admission.recover(self.manifest, self.root, self.root / "recovery")
        self.assertEqual(before, git(self.repo, "show-ref"))
        self.assertEqual(git(self.repo, "status", "--porcelain"), b"")
        self.assertTrue(report["all_restored"])
        self.assertFalse(report["import_allowed"])
        self.assertNotIn("private-research", json.dumps(report))
        self.assertNotIn("excluded.txt", json.dumps(report))
        restored = self.root / "recovery/example-restored.git"
        self.assertEqual(git(restored, "show", self.pin + ":excluded.txt"), b"private recovery fixture\n")
        self.assertEqual(git(restored, "rev-parse", "refs/tags/evidence/original"),
                         git(self.repo, "rev-parse", "refs/tags/evidence/original"))
        for path in (self.root / "recovery").rglob("*"):
            if not path.is_symlink():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o077, 0, str(path))

    def test_restore_detects_corrupted_bundle_and_keeps_failure_log(self):
        original = admission.Recorder.run
        def corrupt(recorder, label, command, cwd, expected=0):
            if label.endswith("-restore-fetch"):
                (recorder.root / "example.bundle").write_bytes(b"corrupt bundle\n")
            return original(recorder, label, command, cwd, expected)
        with patch.object(admission.Recorder, "run", corrupt):
            with self.assertRaisesRegex(PreflightError, "restore-fetch failed"):
                admission.recover(self.manifest, self.root, self.root / "recovery")
        commands = json.loads((self.root / "recovery/commands.json").read_bytes())
        self.assertNotEqual(commands[-1]["exit_code"], 0)
        self.assertFalse((self.root / "recovery/summary.json").exists())

    def test_existing_destination_refused_without_mutation(self):
        destination = self.root / "recovery"
        destination.mkdir()
        sentinel = destination / "keep"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(PreflightError, "must not exist"):
            admission.recover(self.manifest, self.root, destination)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_canonical_source_destination_refused(self):
        with self.assertRaisesRegex(PreflightError, "canonical source"):
            admission.recover(self.manifest, self.root, self.repo / "recovery")
        self.assertFalse((self.repo / "recovery").exists())

    def test_symlink_parent_refused(self):
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(PreflightError, "canonical"):
            admission.recover(self.manifest, self.root, self.root / "alias/recovery")
        self.assertFalse((self.root / "recovery").exists())

    def test_incorrect_source_tree_cannot_create_bundle(self):
        self.manifest["sources"][0]["tree"] = "0" * 40
        with self.assertRaisesRegex(PreflightError, "tree mismatch"):
            admission.recover(self.manifest, self.root, self.root / "recovery")
        self.assertFalse((self.root / "recovery/example.bundle").exists())

    def test_private_sources_are_never_queried_remotely(self):
        with patch.object(admission.Recorder, "run", side_effect=AssertionError("network call")):
            report = admission.public_refs(self.manifest, self.root, self.root / "public")
        self.assertEqual(report["public_sources"], [])

    def test_public_evidence_ref_mismatch_rejected(self):
        self.manifest["sources"][0]["visibility"] = "public"
        remote = (self.pin + "\trefs/heads/main\n" + self.pin + "\trefs/tags/evidence/original\n").encode()
        with patch.object(admission.Recorder, "run", return_value=remote):
            with self.assertRaisesRegex(PreflightError, "evidence tag mismatch"):
                admission.public_refs(self.manifest, self.root, self.root / "public")

    def overlay(self):
        patch_bytes = b"synthetic patch identity; not applied by this command\n"
        record = {"repository": "example/source", "commit": self.pin, "patch_sha256": digest(patch_bytes),
                  "files": {"selected.txt": {"before_sha256": digest(b"selected source\n"), "after_sha256": "a" * 64}}}
        # Metadata is in an independent public repository, like the real nsealr-owned overlays.
        owner = self.root / "owner"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(owner)], check=True)
        git(owner, "config", "user.name", "Synthetic fixture")
        git(owner, "config", "user.email", "fixture@example.invalid")
        (owner / "overlay.patch").write_bytes(patch_bytes)
        (owner / "overlay.json").write_bytes(canonical(record))
        git(owner, "add", ".")
        git(owner, "commit", "-qm", "overlay metadata")
        entry = copy.deepcopy(self.manifest["sources"][0])
        entry.update(name="owner", directory="owner", visibility="public",
                     commit=git(owner, "rev-parse", "HEAD").decode().strip(),
                     tree=git(owner, "rev-parse", "HEAD^{tree}").decode().strip())
        self.manifest["sources"].append(entry)
        self.manifest["overlays"] = [{"record_source": "owner", "target_source": "example", "patch_path": "overlay.patch",
                                      "patch_sha256": digest(patch_bytes), "manifest_path": "overlay.json",
                                      "manifest_sha256": digest(canonical(record))}]

    def test_overlay_hash_chain_verified_without_assembly(self):
        self.overlay()
        report = admission.overlay_chain(self.manifest, self.root)
        self.assertEqual(report["effective_postimages"], [{"source": "example", "path": "selected.txt", "sha256": "a" * 64}])
        self.assertEqual((self.repo / "selected.txt").read_bytes(), b"selected source\n")
        self.assertFalse(report["import_allowed"])

    def test_overlay_cannot_select_private_excluded_file(self):
        self.overlay()
        self.manifest["sources"][0]["rules"] = []
        with self.assertRaisesRegex(PreflightError, "not explicitly selected"):
            admission.overlay_chain(self.manifest, self.root)

    def test_overlay_digest_tampering_fails(self):
        self.overlay()
        self.manifest["overlays"][0]["patch_sha256"] = "b" * 64
        with self.assertRaisesRegex(PreflightError, "hash mismatch"):
            admission.overlay_chain(self.manifest, self.root)


if __name__ == "__main__":
    unittest.main()
