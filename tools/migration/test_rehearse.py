from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import rehearse as migration


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Synthetic preflight fixture")
        self.put("LICENSE", b"MIT fixture notice\n")
        self.put("vectors/.hidden.json", b'{"case":"hidden"}\n')
        self.put("test_example.py", b"def test_independent_case():\n    assert True\n")
        self.put("evidence/check.log", b"synthetic acceptance result\n")
        self.put("evidence/notes.md", b"[known](check.log) [historical](../missing.md)\n")
        expected = {"input_commits": {"example/source": "1" * 40},
                    "candidate_commits": {"example/source": "2" * 40},
                    "acceptance": ["synthetic closure contract"],
                    "review": {"assignee": "author", "reviewer": "reviewer", "verdict": "pass"},
                    "acceptance_results": [{"index": 0, "outcome": "pass", "proof_kind": "executed_test",
                                            "evidence_paths": ["evidence/check.log"]}]}
        self.put("evidence/result.json", migration.canonical(expected))
        self.task = {"id": "R00", "status": "integrated", "assignee": "author", "reviewer": "reviewer",
                     "review_verdict": "pass", "input_commits": expected["input_commits"],
                     "candidate_commits": expected["candidate_commits"],
                     "reviewed_input_commits": expected["input_commits"],
                     "reviewed_candidate_commits": expected["candidate_commits"],
                     "acceptance": expected["acceptance"], "result_manifest": "evidence/result.json",
                     "result_artifacts": [{"path": p, "sha256": migration.digest((self.repo / p).read_bytes())}
                                          for p in ("evidence/check.log", "evidence/notes.md", "evidence/result.json")]}
        self.graph = {"tasks": [self.task]}
        self.put("graph.json", migration.canonical(self.graph))
        self.commit()
        self.manifest = {"format": 1, "mode": "preflight-only", "graph": {"source": "example", "path": "graph.json"},
                         "sources": [{"name": "example", "directory": "source", "repository": "example/source",
                                      "visibility": "public", "commit": self.pin, "tree": self.tree,
                                      "root_license": {"path": "LICENSE", "sha256": migration.digest(b"MIT fixture notice\n")},
                                      "rules": [], "default": {"id": "existing", "action": "retain",
                                                                "destination": "{path}", "reason": "synthetic existing ancestry"}}]}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def put(self, path, data):
        dest = self.repo / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "synthetic source")
        self.pin = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        if hasattr(self, "manifest"):
            self.manifest["sources"][0].update(commit=self.pin, tree=self.tree)

    def inventory(self):
        return migration.inventory(self.manifest, self.root)

    def prepare(self):
        path = self.root / "input.json"
        path.write_bytes(migration.canonical(self.manifest))
        out = self.root / "runtime"
        migration.prepare(path, self.root, out)
        return out

    def test_hidden_files_and_current_evidence_are_inventoried(self):
        report = self.inventory()
        self.assertIn("vectors/.hidden.json", [r["path"] for r in report["files"]])
        self.assertEqual(report["summary"]["closed_artifact_references"], 3)
        self.assertEqual(report["tests"][0]["static_names"], ["test_independent_case"])
        links = next(r for r in report["closed_evidence"]["artifacts"] if r["path"].endswith("notes.md"))["relative_links"]
        self.assertEqual([r["exists_at_inventory_commit"] for r in links], [True, False])
        self.assertFalse(report["summary"]["import_allowed"])

    def test_dirty_worktree_never_supplies_source_bytes(self):
        before = self.inventory()
        self.put("vectors/.hidden.json", b"uncommitted replacement")
        after = self.inventory()
        self.assertEqual(before["files"], after["files"])
        self.assertTrue(after["sources"][0]["dirty_worktree_observed"])

    def test_tampered_frozen_artifact_fails(self):
        self.put("evidence/check.log", b"changed evidence")
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "artifact hash mismatch"):
            self.inventory()

    def test_deleted_frozen_artifact_fails(self):
        (self.repo / "evidence/check.log").unlink()
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "missing closed artifact"):
            self.inventory()

    def test_duplicate_artifact_alias_fails(self):
        self.task["result_artifacts"].append(copy.deepcopy(self.task["result_artifacts"][0]))
        self.put("graph.json", migration.canonical(self.graph))
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "duplicate closed artifact"):
            self.inventory()

    def test_result_manifest_must_be_in_hash_closure(self):
        self.task["result_artifacts"] = self.task["result_artifacts"][:-1]
        self.put("graph.json", migration.canonical(self.graph))
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "outside hashed closure"):
            self.inventory()

    def test_wrong_reviewed_commit_fails(self):
        self.task["reviewed_candidate_commits"] = {"example/source": "3" * 40}
        self.put("graph.json", migration.canonical(self.graph))
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "reviewed commit mismatch"):
            self.inventory()

    def test_selected_symlink_fails(self):
        (self.repo / "escape").symlink_to("../../outside")
        self.commit()
        with self.assertRaisesRegex(migration.PreflightError, "nonregular selected"):
            self.inventory()

    def test_private_catchall_selection_fails(self):
        self.manifest["sources"][0]["visibility"] = "private"
        with self.assertRaisesRegex(migration.PreflightError, "private sources require default exclusion"):
            self.inventory()

    def test_excluded_private_blob_is_not_read(self):
        entry = self.manifest["sources"][0]
        entry["visibility"] = "private"
        entry["rules"] = [{"id": "evidence", "prefix": "evidence/", "action": "retain",
                           "destination": "{path}", "reason": "explicit test evidence"}]
        entry["default"] = {"id": "private", "action": "exclude", "reason": "private content not selected"}
        actual = migration.Source.blob
        calls = []

        def recording(source, path):
            calls.append(path)
            return actual(source, path)

        with patch.object(migration.Source, "blob", recording):
            self.inventory()
        self.assertNotIn("vectors/.hidden.json", calls)
        self.assertNotIn("test_example.py", calls)

    def test_destination_collision_is_an_explicit_blocker(self):
        self.manifest["sources"][0]["rules"] = [{"id": "collision", "prefix": "vectors/", "action": "retain",
                                                 "destination": "LICENSE", "reason": "intentional collision probe"}]
        report = self.inventory()
        self.assertEqual(len(report["destination_collisions"]), 1)
        self.assertTrue(any("collision" in b for b in report["summary"]["blockers"]))

    def test_duplicate_json_members_rejected(self):
        with self.assertRaisesRegex(migration.PreflightError, "duplicate JSON member"):
            migration.decode_json(b'{"commit":"a","commit":"b"}')

    def test_unsafe_paths_rejected(self):
        for path in ("../escape", "/absolute", "a/../b", "a//b", ".git/config", "a\\b"):
            with self.subTest(path=path), self.assertRaises(migration.PreflightError):
                migration.safe_path(path)

    def test_tree_and_license_pins_enforced(self):
        for field in ("tree", "root_license"):
            candidate = copy.deepcopy(self.manifest)
            if field == "tree":
                candidate["sources"][0][field] = "0" * 40
            else:
                candidate["sources"][0][field]["sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaises(migration.PreflightError):
                migration.inventory(candidate, self.root)

    def test_prepare_creates_only_private_inventory_not_git_or_bundles(self):
        out = self.prepare()
        self.assertEqual({p.name for p in out.iterdir()}, {"runtime.json", "manifest.json", "inventory.json"})
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in out.iterdir()))
        self.assertFalse(migration.preflight(out)["import_allowed"])
        with self.assertRaisesRegex(migration.PreflightError, "must not exist"):
            migration.prepare(self.root / "input.json", self.root, out)

    def test_inventory_tamper_rejected_on_recheck(self):
        out = self.prepare()
        with (out / "inventory.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaisesRegex(migration.PreflightError, "inventory hash mismatch"):
            migration.preflight(out)

    def test_changed_manifest_not_accepted_as_old_inventory(self):
        out = self.prepare()
        manifest = json.loads((out / "manifest.json").read_text())
        manifest["sources"][0]["default"]["reason"] = "changed intent"
        (out / "manifest.json").write_bytes(migration.canonical(manifest))
        with self.assertRaisesRegex(migration.PreflightError, "changed recorded manifest_sha256"):
            migration.preflight(out)

    def test_source_destination_is_rejected_before_writing(self):
        path = self.root / "input.json"
        path.write_bytes(migration.canonical(self.manifest))
        with self.assertRaisesRegex(migration.PreflightError, "inside a source"):
            migration.prepare(path, self.root, self.repo / "output")
        self.assertFalse((self.repo / "output").exists())


if __name__ == "__main__":
    unittest.main()
