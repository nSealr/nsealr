"""Pure checker controls over ONE original real log; no product process runs.

Usage: python -B test_capture_extension.py [--full] LOG SOURCE_HEAD REPOSITORY RESULT.json
The early pi-ci log can qualify this block only, never full CI or GitHub.
"""
import copy
from functools import cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch


def main():
    arguments = sys.argv[1:]
    full_product = arguments[0] == "--full"
    log, head, repo, output = arguments[1:] if full_product else arguments
    source = Path(repo) / "docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py"
    spec = importlib.util.spec_from_file_location("qh01_capture_extension", source)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    raw = Path(log).read_bytes()
    lines = [re.sub(r"^\d{4}-\d\d-\d\dT\S+Z ?", "", s) for s in raw.decode().splitlines()]
    objects = []
    decoder = json.JSONDecoder()
    for i, line in enumerate(lines):
        if line.startswith("{"):
            try:
                value, _ = decoder.raw_decode("\n".join(lines[i:]))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                objects.append(value)
    workers = [o for o in objects if o.get("role") == "public RGB worker build, initialization v2, not hardware qualification"]
    assert len(workers) == 1
    check_output = subprocess.check_output
    @cache
    def fixed_git_read(argv, text):
        # Exact same immutable Git object queries; first response is original.
        return check_output(list(argv), text=text)
    def read(argv, **kwargs):
        assert set(kwargs) <= {"text"}
        return fixed_git_read(tuple(argv), kwargs.get("text", False))
    def case(rows):
        return next(o["qh01_composition_case"] for o in rows if "qh01_composition_case" in o)
    def build(rows):
        return next(o["bridge_service_build"] for o in rows if "bridge_service_build" in o)
    controls = []
    def reject(name, change):
        rows, changed_lines = copy.deepcopy(objects), list(lines)
        change(rows, changed_lines)
        try:
            checker.verify_qh01_composition(rows, changed_lines, workers[0], head, repo, full_product=full_product)
        except (AssertionError, KeyError, ValueError, TypeError):
            controls.append({"name": name, "rejected": True})
        else:
            raise AssertionError("checker accepted mutated evidence: " + name)
    with patch.object(checker.subprocess, "check_output", side_effect=read):
        positive = checker.verify_qh01_composition(objects, lines, workers[0], head, repo, full_product=full_product)
        for key in ["bridge_service_build", "qh01_composition_case", "qh01_composition_command"]:
            reject("missing " + key, lambda rows, _: rows.__setitem__(slice(None), [r for r in rows if key not in r]))
            reject("duplicate " + key, lambda rows, _: rows.append(copy.deepcopy(next(r for r in rows if key in r))))
        reject("nonzero compiler", lambda rows, _: build(rows).__setitem__("status", 1))
        reject("changed compiler options", lambda rows, _: build(rows)["argv"].remove("--strict"))
        reject("stale service source", lambda rows, _: build(rows)["source_before"].__setitem__(next(iter(build(rows)["source_before"])), "0" * 64))
        reject("stale current source", lambda rows, _: case(rows)["source_after"].__setitem__(next(iter(case(rows)["source_after"])), "0" * 64))
        reject("foreign generated Bridge", lambda rows, _: build(rows)["outputs"].__setitem__(next(iter(build(rows)["outputs"])), "0" * 64))
        reject("changed generated input", lambda rows, _: case(rows)["generated_after"].__setitem__(next(iter(case(rows)["generated_after"])), "0" * 64))
        reject("old reuse root", lambda rows, _: case(rows)["argv"].__setitem__(-1, "/old/worktree"))
        reject("unbound worker", lambda rows, _: case(rows)["worker_initialization"].__setitem__("sha256", "0" * 64))
        reject("foreign live worker", lambda rows, _: case(rows)["collection"]["B3"]["phase"].__setitem__("exe_sha256", "0" * 64))
        reject("missing Node wait", lambda rows, _: case(rows)["collection"].__setitem__("node_wait_raw", None))
        reject("wrong W collector", lambda rows, _: case(rows)["collection"]["B3"]["terminal"]["worker_wait"].__setitem__("collector_pid", case(rows)["actual"]["parent_pid"]))
        reject("missing EOF", lambda rows, _: case(rows)["collection"]["B3"]["EOF"].pop())
        reject("unrestored FDs", lambda rows, _: case(rows)["collection"]["parent_fd_after"].append(9))
        reject("false taken", lambda rows, _: case(rows)["collection"]["B3"].__setitem__("taken", False))
        reject("foreign request", lambda rows, _: case(rows)["frames"]["decoded"].__setitem__("sha256", "0" * 64))
        reject("timer changed", lambda rows, _: case(rows)["node_records"][3].__setitem__("timer_args", [101]))
        reject("timer not cleared", lambda rows, _: case(rows)["node_records"][3].__setitem__("clear_calls", 0))
        reject("foreign selected key", lambda rows, _: case(rows).__setitem__("expected_public_key", "0" * 64))
        reject("G bool instead of integer", lambda rows, _: case(rows)["collection"]["B3"]["terminal"].__setitem__("G_bytes", True))
        reject("pure control missing", lambda _, ls: ls.remove("test_write_failure (__main__.AttentionReportingTests.test_write_failure) ... ok"))
        reject("reported composition failure", lambda rows, _: rows.append({"qh01_composition_failure": {"v": 1}}))
        if full_product:
            reject("changed later build", lambda rows, _: next(o["bridge_service_build"] for o in reversed(rows) if "bridge_service_build" in o).__setitem__("status", 1))
            def relocate(ls, which, destination):
                indices = [i for i, s in enumerate(ls) if s.startswith('{"bridge_service_build":')]
                moved = ls.pop(indices[which])
                if destination == "next":
                    indices = [i for i, s in enumerate(ls) if s.startswith('{"bridge_service_build":')]
                    ls.insert(indices[which], moved)
                elif destination == "after-command":
                    index = next(i for i, s in enumerate(ls) if s.startswith('{"qh01_composition_command":'))
                    ls.insert(index + 1, moved)
                else:
                    ls.append(moved)
            reject("same total missing step3 and duplicate step4", lambda _, ls: relocate(ls, 1, "next"))
            reject("build after completion", lambda _, ls: relocate(ls, -1, "end"))
            reject("initial build after command", lambda _, ls: relocate(ls, 0, "after-command"))
    result = {"role": "Pure capture-checker controls on an original log; no product replay or GitHub claim",
              "log_scope": "complete local make-ci" if full_product else "early pi-ci block only",
              "source_head": head, "checker_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "checker_commit": check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip(),
              "control_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "log_bytes": len(raw), "log_sha256": hashlib.sha256(raw).hexdigest(),
              "positive": positive, "negative_controls": controls,
              "cached_immutable_git_queries": fixed_git_read.cache_info()._asdict(),
              "new_product_processes": 0}
    with Path(output).open("x") as target:
        json.dump(result, target, indent=2)
        target.write("\n")
    print(json.dumps({"positive": True, "negative_controls": len(controls), "output": output}))


if __name__ == "__main__":
    main()
