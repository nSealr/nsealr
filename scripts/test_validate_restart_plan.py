"""Regression checks for false readiness and false evidence acceptance."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from validate_restart_plan import validate


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = {"tasks": [{"id": "A", "status": "ready", "depends_on": [],
                               "acceptance": ["prove behavior"], "owner_role": "engineer",
                               "required_resources": []}], "resources": {},
                     "active_profiles": ["custom_board"], "release_paths": {"custom_board": "A"},
                     "release_forbidden_ancestors": {"custom_board": []}}

    def test_ready_valid(self):
        self.assertEqual(validate(self.plan, self.root), [])

    def test_invalid_graphs(self):
        for dependency in ("MISSING", "A"):
            with self.subTest(dependency=dependency):
                self.plan["tasks"][0]["depends_on"] = [dependency]
                self.assertTrue(validate(self.plan, self.root))

    def test_duplicate_id(self):
        self.plan["tasks"].append(copy.deepcopy(self.plan["tasks"][0]))
        self.assertTrue(validate(self.plan, self.root))

    def test_unknown_status(self):
        self.plan["tasks"][0]["status"] = "done_probably"
        self.assertTrue(validate(self.plan, self.root))

    def test_resource_not_confirmed(self):
        self.plan["resources"] = {"bench": {"status": "unknown", "owner_role": "operator", "next_action": "inspect"}}
        self.plan["tasks"][0]["required_resources"] = ["bench"]
        self.assertTrue(validate(self.plan, self.root))
        self.plan["resources"]["bench"]["status"] = "available"
        self.assertTrue(validate(self.plan, self.root))
        self.plan["resources"]["bench"].update(confirmed_by="operator-one", availability_record="sample 1; local bench access checked")
        self.assertEqual(validate(self.plan, self.root), [])

    def close_task(self):
        (self.root / "proof.txt").write_text("fixture evidence\n")
        task = self.plan["tasks"][0]
        task.update(status="integrated", assignee="author", reviewer="reviewer", review_verdict="pass",
                    input_commits={"repo": "a" * 40}, candidate_commits={"repo": "b" * 40},
                    reviewed_input_commits={"repo": "a" * 40}, reviewed_candidate_commits={"repo": "b" * 40},
                    result_artifacts=[{"path": "proof.txt", "sha256": hashlib.sha256((self.root / "proof.txt").read_bytes()).hexdigest()}])
        result = {"input_commits": task["input_commits"], "candidate_commits": task["candidate_commits"], "acceptance": task["acceptance"],
                  "review": {"assignee": "author", "reviewer": "reviewer", "verdict": "pass"},
                  "acceptance_results": [{"index": 0, "outcome": "pass", "proof_kind": "executed_test", "evidence_paths": ["proof.txt"]}]}
        self.write_manifest(task, result)
        return task

    def write_manifest(self, task, result):
        path = self.root / "result.json"
        path.write_text(json.dumps(result))
        task["result_manifest"] = "result.json"
        task["result_artifacts"] = [a for a in task["result_artifacts"] if a["path"] != "result.json"]
        task["result_artifacts"].append({"path": "result.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    def test_closed_evidence_valid(self):
        self.close_task()
        self.assertEqual(validate(self.plan, self.root), [])

    def test_changed_candidate_or_inputs(self):
        task = self.close_task()
        for field in ("reviewed_input_commits", "reviewed_candidate_commits"):
            with self.subTest(field=field):
                old = task[field]
                task[field] = {"repo": "c" * 40}
                self.assertTrue(validate(self.plan, self.root))
                task[field] = old

    def test_self_review(self):
        task = self.close_task()
        task["reviewer"] = task["assignee"]
        self.assertTrue(validate(self.plan, self.root))

    def test_missing_and_changed_artifact(self):
        self.close_task()
        (self.root / "proof.txt").write_text("changed")
        self.assertTrue(validate(self.plan, self.root))
        (self.root / "proof.txt").unlink()
        self.assertTrue(validate(self.plan, self.root))

    def test_external_artifact(self):
        task = self.close_task()
        task["result_artifacts"][0]["path"] = "../outside.txt"
        self.assertTrue(validate(self.plan, self.root))

    def test_absolute_artifact_inside_repository(self):
        task = self.close_task()
        task["result_artifacts"][0]["path"] = str(self.root / "proof.txt")
        self.assertTrue(validate(self.plan, self.root))

    def test_transitive_profile_dependency(self):
        self.plan["tasks"][0]["status"] = "planned"
        self.plan["tasks"].extend([
            {"id": "B", "status": "planned", "depends_on": ["A"], "acceptance": ["b"], "owner_role": "x"},
            {"id": "C", "status": "planned", "depends_on": ["B"], "acceptance": ["c"], "owner_role": "x"}])
        self.plan.update(active_profiles=["pi"], release_paths={"pi": "C"}, release_forbidden_ancestors={"pi": ["A"]})
        self.assertTrue(validate(self.plan, self.root))

    def test_missing_release_checks(self):
        self.plan["release_paths"] = {}
        self.assertTrue(validate(self.plan, self.root))

    def test_invalid_acceptance_schema(self):
        for value in ("a string", [{}], []):
            self.plan["tasks"][0]["acceptance"] = value
            self.assertTrue(validate(self.plan, self.root))

    def test_contradictory_evidence(self):
        task = self.close_task()
        baseline = json.loads((self.root / "result.json").read_text())
        for change in ("failure", "wrong_candidate", "wrong_review", "missing", "duplicate", "out_of_range", "unhashed"):
            with self.subTest(change=change):
                result = copy.deepcopy(baseline)
                outcome = result["acceptance_results"][0]
                if change == "failure": outcome["outcome"] = "fail"
                if change == "wrong_candidate": result["candidate_commits"] = {"repo": "c" * 40}
                if change == "wrong_review": result["review"]["verdict"] = "reject"
                if change == "missing": result["acceptance_results"] = []
                if change == "duplicate": result["acceptance_results"].append(copy.deepcopy(outcome))
                if change == "out_of_range": outcome["index"] = 1
                if change == "unhashed": outcome["evidence_paths"] = ["absent.log"]
                self.write_manifest(task, result)
                self.assertTrue(validate(self.plan, self.root))

    def test_physical_record_and_historical_resource(self):
        task = self.close_task()
        task["requires_physical_evidence"] = True
        task["required_resources"] = ["sample"]
        self.plan["resources"]["sample"] = {"status": "unavailable", "owner_role": "operator", "next_action": "sample consumed"}
        self.assertTrue(validate(self.plan, self.root))
        result = json.loads((self.root / "result.json").read_text())
        result["acceptance_results"][0]["proof_kind"] = "physical_measurement"
        result["physical"] = {"sample_ids": ["sacrificial-1"], "operator": "operator-one", "instruments": ["scope-1"],
                              "conditions": "fixture conditions", "resource_snapshot": "sample present during procedure"}
        self.write_manifest(task, result)
        self.assertEqual(validate(self.plan, self.root), [])

    def test_requirement_changed_after_review(self):
        task = self.close_task()
        task["acceptance"] = ["a stronger requirement"]
        self.assertTrue(validate(self.plan, self.root))

    def test_manifest_cannot_be_its_own_proof_via_alias(self):
        task = self.close_task()
        result = json.loads((self.root / "result.json").read_text())
        result["acceptance_results"][0]["evidence_paths"] = ["./result.json"]
        self.write_manifest(task, result)
        task["result_artifacts"].append({"path": "./result.json", "sha256": hashlib.sha256((self.root / "result.json").read_bytes()).hexdigest()})
        self.assertTrue(validate(self.plan, self.root))


if __name__ == "__main__":
    unittest.main()
