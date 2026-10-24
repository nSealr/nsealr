"""Read frozen Git and archived data only; never import or run candidate code."""
import ast
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
CANDIDATE = "5bc8dae4c34bb89425005ecaff543c9586033f31"
BASE = "858eaf19a1f2b104112edb9842a479c035db301f"
EXECUTED = "f7f300960e693fa6f47001cdb6f069372b82b67d"
COMPOSITION = "docs/restart/implementation/QH01/manual-port/python-rgb-composition/"
PROOF = COMPOSITION + "proof/lifecycle-ci/"
EXCHANGE = "docs/restart/implementation/QP01/request-engine/exchange.py"
TEST = "apps/pi/tests/test_engine_adapter.py"
RUN = COMPOSITION + "run-composition.py"
BRIEF = COMPOSITION[:-1] + "-brief.md"
IDS = ["scan_null_after_settlement", "scan_pending_timeout_after_settlement", "fixture_cancel_B3_verified_preG"]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def blob(ref, path):
    return git("show", f"{ref}:{path}")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def parsed(ref, path):
    return json.loads(blob(ref, path))

def functions(ref, path):
    tree = ast.parse(blob(ref, path))
    return {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

def dump(node):
    return ast.dump(node, include_attributes=False)

assert git("rev-parse", CANDIDATE + "^{tree}").decode().strip() == "e22d520ff560615db8e0593afc470a270b4d1397"
changed = git("diff", "--name-only", BASE, CANDIDATE).decode().splitlines()
assert len(changed) == 17 and {p for p in changed if not p.startswith(PROOF)} == {EXCHANGE, TEST, RUN, BRIEF}
manifest = parsed(CANDIDATE, PROOF + "artifact-manifest.json")
assert manifest["members_count"] == len(manifest["members"]) == 12
listed = git("ls-tree", "-r", "--full-tree", "--name-only", CANDIDATE, PROOF).decode().splitlines()
assert set(listed) == {x["path"] for x in manifest["members"]} | {PROOF + "artifact-manifest.json"}
for row in manifest["members"]:
    data = blob(CANDIDATE, row["path"])
    entry = git("ls-tree", CANDIDATE, row["path"]).decode().split()
    assert entry[:3] == [row["mode"], "blob", row["git_blob"]]
    assert len(data) == row["bytes"] and sha(data) == row["sha256"]
freeze = parsed(CANDIDATE, PROOF + "source-schema-freeze.json")
for path, digest in freeze["sources"].items():
    assert blob(CANDIDATE, path) == blob(EXECUTED, path)
    assert sha(blob(CANDIDATE, path)) == digest
assert set(freeze["sources"]) == {EXCHANGE, TEST, RUN}
correspondence = parsed(CANDIDATE, PROOF + "source-correspondence.json")
for path, digest in correspondence["unchanged_sha256"].items():
    assert blob(BASE, path) == blob(CANDIDATE, path)
    assert sha(blob(CANDIDATE, path)) == digest
old, new = functions(BASE, RUN), functions(CANDIDATE, RUN)
assert set(old) == set(new)
assert all(dump(old[n]) == dump(new[n]) for n in old if n != "run")
assert dump(ast.Module(body=old["run"].body[:-1], type_ignores=[])) == dump(ast.Module(body=new["run"].body[:-1], type_ignores=[]))
old_exchange, new_exchange = functions(BASE, EXCHANGE), functions(CANDIDATE, EXCHANGE)
assert set(old_exchange) == set(new_exchange)
assert all(dump(old_exchange[n]) == dump(new_exchange[n]) for n in old_exchange if n not in {"ci", "composition_ci", "composition_record"})
old_tests, new_tests = functions(BASE, TEST), functions(CANDIDATE, TEST)
assert set(old_tests) == set(new_tests)
assert all(dump(old_tests[n]) == dump(new_tests[n]) for n in old_tests if n not in {"test_actual_driver_orders_full_pi_then_clients_with_same_identities", "record"})

with tarfile.open(ROOT / PROOF / "evidence.tar.gz") as archive:
    members = archive.getmembers()
    assert len(members) == len({m.name for m in members}) == 88
    assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members)
    raw = {m.name: archive.extractfile(m).read() for m in members}
    inner = json.loads(raw["evidence-manifest.json"])["members"]
    assert len(inner) == 87 and {x["path"] for x in inner} == set(raw) - {"evidence-manifest.json"}
    for row in inner:
        assert len(raw[row["path"]]) == row["bytes"] and sha(raw[row["path"]]) == row["sha256"]
        assert oct(archive.getmember(row["path"]).mode) == "0o644" and row["mode"] == "100644"
    for row in manifest["members"]:
        name = row["path"].removeprefix(PROOF)
        if name in raw:
            assert raw[name] == blob(CANDIDATE, row["path"])
log = raw["make-pi-ci-01.log"]
assert len(log) == 616947 and sha(log) == "e3b31f6f629f45eefeb0e2374c98958a850425738b63347f7e1ec48c82cf8eac"
objects = []
for number, line in enumerate(log.decode().splitlines(), 1):
    if line.startswith("{"):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(item) is dict:
            objects.append((number, item))
def select(key):
    return [(n, obj[key]) for n, obj in objects if key in obj]

commands = select("qh01_composition_command") + select("qh01_lifecycle_command")
cases = select("qh01_composition_case") + select("qh01_lifecycle_case")
results = select("qh01_lifecycle_result")
assert len(commands) == len(cases) == 4 and len(results) == 3
assert [x["id"] for _, x in cases] == ["bridge_rgb_kind1_basic", *IDS]
assert not any(key.endswith("_failure") for _, obj in objects for key in obj if key.startswith("qh01_"))
expected_keys = ["qh01_composition_command", "qh01_composition_case"]
for _ in IDS:
    expected_keys.extend(["qh01_lifecycle_command", "qh01_lifecycle_result", "qh01_lifecycle_case"])
assert [key for _, obj in objects for key in obj if key.startswith("qh01_")] == expected_keys
assert len({c["output"] for _, c in commands}) == 4
worker = [(n, x) for n, x in objects if x.get("role", "").startswith("public RGB worker build,")]
native = [(n, x) for n, x in objects if x.get("role") == "public fixture build, not hardware qualification"]
assert len(worker) == len(native) == 1 and native[0][0] < worker[0][0] < commands[0][0]
w = worker[0][1]
assert w["CARGO_TARGET_DIR"] is None and w["sha256"] == "95f541ec0f05bf4849b71bd0507ca47eaa4a5f649696492ad48edcbc375c0df5"
for path, digest in w["source"].items():
    assert sha(blob(CANDIDATE, path)) == digest
build = select("bridge_service_build")
assert len(build) == 1 and build[0][0] < native[0][0]
assert build[0][1] == parsed(CANDIDATE, PROOF + "actual-build-record.json")
assert len(build[0][1]["source_before"]) == 5 and len(build[0][1]["outputs"]) == 10
observations = []
for index, ((command_line, command), (case_line, case)) in enumerate(zip(commands, cases, strict=True)):
    cancelled = index == 3
    assert command_line < case_line and (index == 3 or case_line < commands[index + 1][0])
    assert command["argv"] == case["argv"] and case["worker_initialization"] == {"path": w["worker"], "sha256": w["sha256"]}
    assert case["source_before"] == case["source_after"] and len(case["source_before"]) == 60
    assert case["generated_before"] == case["generated_after"] == cases[0][1]["generated_before"] and len(case["generated_before"]) == 62
    for path, digest in case["source_before"].items():
        assert sha(blob(CANDIDATE, path)) == sha(blob(EXECUTED, path)) == digest
    name = ("qh01_composition_case-" if index == 0 else "qh01_lifecycle_case-") + case["id"] + ".json"
    assert case == parsed(CANDIDATE, PROOF + name) == json.loads(raw[name])
    rows, collected = case["node_records"], case["collection"]
    assert rows[0]["event"] == "present" and rows[-1]["event"] == "result"
    assert base64.b64decode(case["native_response_base64"]) == base64.b64decode(rows[-1]["native_response_base64"])
    wire = base64.b64decode(case["native_response_base64"], validate=True)
    assert len(wire) >= 4 and int.from_bytes(wire[:4], "little") == len(wire) - 4
    assert json.loads(wire[4:]) == case["service_response"]
    assert case["frames"]["presented"] == {"bytes": 259, "sha256": "88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7"}
    assert sha(rows[0]["frame"].encode("ascii")) == case["frames"]["presented"]["sha256"]
    assert collected["node_wait_raw"] == 0 and collected["node_EOF"] == ["stderr", "stdout"]
    assert collected["parent_fd_before"] == collected["parent_fd_after"] and collected["runtime_strong_reference"] is True
    b3 = collected["B3"]
    assert b3["closed"] is True and b3["parent_owned_fds"] == [] and b3["EOF"] == [1, 2, 4, 5]
    assert b3["terminal"]["ownership"] == "settled" and all(v is True for v in b3["terminal"]["worker_io"].values())
    assert b3["terminal"]["worker_wait"]["collector_pid"] == b3["owner_pid"]
    assert rows[-1]["timer_args"] == [100] and rows[-1]["clear_calls"] == 1
    assert rows[-1]["deadline_fires"] == (1 if index == 2 else 0)
    if index:
        assert command["id"] == case["id"] == case["actual"]["case"] == rows[-1]["lifecycle"]["case"]
        assert command["argv"][-2:] == ["--case", case["id"]]
        assert results[index - 1][1] == case["actual"] and command_line < results[index - 1][0] < case_line
        assert case["frames"]["scanned"] is None
        assert case["cancel_refusals"] == ({"take_result_refused": True, "reservation_before_close_refused": True, "caller_released_bytes": 0} if cancelled else None)
        assert case["service_response"]["error"]["code"] == ("signer_transport_timeout" if index == 2 else "signer_transport_failed")
    if cancelled:
        assert case["frames"]["decoded"] is None and case["decoded_request"] is None
        assert b3["commands"] == ["P", "X"] and b3["owner_wait_raw"] == 512
        assert b3["terminal"]["worker_wait"]["raw_status"] == 9
        assert b3["terminal"]["G_bytes"] == b3["terminal"]["image_bytes_sent"] == b3["terminal"]["result_bytes"] == 0
        assert case["actual"]["caller_released_bytes"] == 0
    else:
        assert case["frames"]["decoded"] == case["frames"]["presented"]
        assert b3["owner_wait_raw"] == b3["terminal"]["worker_wait"]["raw_status"] == 0
    if index == 2:
        lifecycle = rows[-1]["lifecycle"]
        assert case["frames"]["late_scan"] == {"bytes": lifecycle["late_scan_bytes"], "sha256": lifecycle["late_scan_sha256"]}
        assert case["frames"]["late_scan"] == {"bytes": 611, "sha256": "f27dbe54785a9510e43f05d27dbb67c488c77def150e0110d51264762cdeec1b"}
        timeout = next(row for row in rows if row["event"] == "timeout")
        assert timeout["closes"] == 0 and timeout["underlying_settled"] is False and timeout["abort_observed"] is True
        assert lifecycle["closes"] == 1 and lifecycle["underlying_settled"] is True
    observations.append({"id": case["id"], "command_line": command_line, "case_line": case_line, "frames": case["frames"], "parent_pid": case["actual"]["parent_pid"], "node_pid": collected["node_pid"], "owner_pid": b3["owner_pid"], "worker_pid": b3["terminal"]["worker_pid"]})
assert len(select("python_owner_case")) == len([p for p in raw if p.startswith("owner-cases/")]) == 70
legacy = [obj for _, obj in objects if "case" in obj]
assert len(legacy) == 62 and sum(obj.get("pass") is True for obj in legacy) == 39
command = parsed(CANDIDATE, PROOF + "make-pi-ci-01-command.json")
assert command["source_commit"] == EXECUTED and command["source_before"] == command["source_after"] == ""
assert command["exit_code"] == command["wait_raw"] == 0 and command["outer_timeout"] is None
report = {"role": "INDEPENDENT_STATIC_GIT_AND_ORIGINAL_ARCHIVE_CHECKS_NO_PRODUCT_EXECUTION", "candidate": CANDIDATE,
          "tree": "e22d520ff560615db8e0593afc470a270b4d1397", "base": BASE, "executed_author_source": EXECUTED,
          "changed_paths": changed, "source_sha256": freeze["sources"], "unchanged_bindings": correspondence["unchanged_sha256"],
          "manifest_members": 12, "archive_raw_members": 87, "archive_members_including_manifest": 88,
          "archive_sha256": sha(blob(CANDIDATE, PROOF + "evidence.tar.gz")), "log_bytes": len(log), "log_sha256": sha(log),
          "same_run": {"cases": observations, "dynamic_sources_each": 60, "generated_outputs_each": 62, "compiler_sources": 5, "compiler_outputs": 10,
                       "worker_producer_count": 1, "native_producer_count": 1, "owner_rows": 70, "legacy_top_level_cases": 62, "legacy_final_cases": 39,
                       "suite_lines": [line for line in log.decode().splitlines() if line.startswith("Ran ")]},
          "author_command": command, "reviewer_runtime_runs": 0,
          "read_invocation_observation": "An exploratory git diff omitted cwd and failed outside the repository; a subsequent independent schema reader made that compound shell exit0. No diff conclusion came from that failed command. The complete diff was subsequently read in this exact worktree; no source or runtime change.",
          "verdict": "PASS_STATIC_AND_ARCHIVE_BINDINGS"}
(HERE / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"verdict": report["verdict"], "source_files": 3, "cases": 4, "raw_members": 87, "product_runs": 0}))
