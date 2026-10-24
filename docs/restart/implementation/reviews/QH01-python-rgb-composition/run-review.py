"""One independent corrected composition; immutable inputs, no build or timeout kill."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CANDIDATE = "b6d07a4aff913249a06bf1e7ea31cb6265ea0cc0"
ORIGINAL = "f6d850316ab96a47203ddf925a972bb44c013ae6"
STATIC = "7b01abfefcde9177f9c3157fcd1d0a6f5ff3d3c6"
PREFIX = "docs/restart/implementation/QH01/manual-port/python-rgb-composition"
SOURCE = ROOT / PREFIX
FIX = SOURCE / "proof/attention-reporting-fix"
OUT = HERE / ".runtime/positive-01"
R00 = ROOT.parent / "r00/tools/baseline/.work/final"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(commit, path):
    return git("show", f"{commit}:{path}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def dump(node):
    return ast.dump(node, include_attributes=False)


def verify_manifest(path, commit):
    manifest = read(path)
    for row in manifest["members"]:
        data = blob(commit, row["path"])
        mode, _, oid = git("ls-tree", commit, "--", row["path"]).decode().split("\t")[0].split()
        assert (mode, oid, len(data), sha(data)) == (row["mode"], row["git_blob"], row["bytes"], row["sha256"])
    return len(manifest["members"])


assert not OUT.exists(), "No overwrite/retry of the single admitted positive"
OUT.mkdir(parents=True)
assert git("status", "--porcelain").decode() == ""
for name in ("static-review.json", "static-checks.json"):
    path = (HERE / name).relative_to(ROOT).as_posix()
    assert (ROOT / path).read_bytes() == blob(STATIC, path)
assert verify_manifest(FIX / "artifact-manifest.json", CANDIDATE) == 7
assert verify_manifest(SOURCE / "artifact-manifest.json", ORIGINAL) == 10
old = ast.parse(blob(ORIGINAL, PREFIX + "/run-composition.py"))
new = ast.parse((SOURCE / "run-composition.py").read_bytes())
old_class = next(n for n in old.body if isinstance(n, ast.ClassDef) and n.name == "Composition")
new_class = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == "Composition")
old_attention = next(n for n in old_class.body if isinstance(n, ast.FunctionDef) and n.name == "attention")
new_attention = next(n for n in new_class.body if isinstance(n, ast.FunctionDef) and n.name == "attention")
assert len(old_attention.body) == len(new_attention.body) == 3
assert dump(old_attention.body[2]) == dump(new_attention.body[2])
for original_statement, guarded in zip(old_attention.body[:2], new_attention.body[:2]):
    assert isinstance(guarded, ast.Try) and len(guarded.body) == 1
    assert dump(guarded.body[0]) == dump(original_statement)
    assert guarded.orelse == guarded.finalbody == [] and len(guarded.handlers) == 1
    handler = guarded.handlers[0]
    assert isinstance(handler.type, ast.Name) and handler.type.id == "BaseException"
    assert len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)
restored = copy.deepcopy(new)
restored_class = next(n for n in restored.body if isinstance(n, ast.ClassDef) and n.name == "Composition")
restored_class.body = [old_attention if isinstance(n, ast.FunctionDef) and n.name == "attention" else n for n in restored_class.body]
assert dump(restored) == dump(old)
assert blob(CANDIDATE, PREFIX + "/run-composition.py") == (SOURCE / "run-composition.py").read_bytes()
test = (SOURCE / "test_attention_reporting.py").read_bytes()
assert test == blob("2c4c9d397eda8316efcf6f43429dfee99f4d5463", PREFIX + "/test_attention_reporting.py")
with tarfile.open(FIX / "controls.tar.gz") as archive:
    members = archive.getmembers()
    assert len(members) == 14 and all(row.isfile() for row in members)
    raw = {row.name: archive.extractfile(row).read() for row in members}
    assert len(raw) == 14
    manifest = json.loads(raw["artifact-manifest.json"])
    assert len(manifest["members"]) == 13
    for row in manifest["members"]:
        assert (len(raw[row["path"]]), sha(raw[row["path"]])) == (row["bytes"], row["sha256"])
    for role, expected_exit in (("red-01", 1), ("green-01", 0)):
        command = json.loads(raw[f"{role}/command.json"])
        assert command["exit_code"] == expected_exit and command["source_before"] == command["source_after"] == ""
        assert sha(blob(command["source_commit"], PREFIX + "/run-composition.py")) == command["invoker_sha256"]
        assert command["test_sha256"] == sha(test)
    red = json.loads(raw["red-01/cases/write.json"])
    assert red["escaped_type"] == "OSError" and red["hold_iterations"] == red["child_creation_API_calls"] == 0
    green = [json.loads(data) for name, data in raw.items() if name.startswith("green-01/cases/")]
    assert {row["case"] for row in green} == {"write", "print", "both", "observation", "serialization", "report_base_exception"}
    for row in green:
        assert row["escaped_type"] == "HoldSentinel" and row["hold_iterations"] == row["poll_calls"] == row["sleep_calls"] == 2
        assert row["pump_calls"] == 1 and row["child_creation_API_calls"] == 0
        assert all(all(snapshot.values()) for snapshot in row["retained_identity_snapshots"])
inputs = read(SOURCE / "inputs.json")
assert len(inputs["tracked_files"]) == 29
overlay = []
for row in inputs["tracked_files"]:
    historic = blob(ORIGINAL, row["path"])
    assert (len(historic), sha(historic)) == (row["bytes"], row["sha256"])
    data = (ROOT / row["path"]).read_bytes()
    assert data == blob(CANDIDATE, row["path"])
    if data != historic:
        assert row["path"] == PREFIX + "/run-composition.py"
        assert sha(data) == "afe76bc482c4227986efbfbf260611f23c0ba38c2655fea95cb99dbc743d0662"
        overlay.append({"path": row["path"], "historical_sha256": row["sha256"], "current_sha256": sha(data)})
assert len(overlay) == 1
assert (SOURCE / "inputs.json").read_bytes() == blob(ORIGINAL, PREFIX + "/inputs.json")
for row in inputs["prepared_outputs"]:
    data = Path(row["absolute_path"]).read_bytes()
    assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
with tarfile.open(SOURCE / "proof/preparation.tar.gz") as archive:
    preparation = json.loads(archive.extractfile("preparation/result.json").read())
    for row in inputs["prepared_outputs"]:
        assert Path(row["absolute_path"]).read_bytes() == archive.extractfile(row["path"]).read()
    for row in preparation["input"]:
        data = (ROOT / row["path"]).read_bytes()
        assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
assert preparation["wait_raw"] == preparation["exit_code"] == 0 and preparation["compiler_collected_before_runtime"]
bridge = Path(inputs["prepared_outputs"][0]["absolute_path"]).parent
reuse = Path(preparation["cwd"])
link = preparation["module_resolution_symlink"]
assert (bridge / "node_modules").is_symlink() and str((bridge / "node_modules").readlink()) == link["target"]
dist_count = 0
for package in inputs["reused_libraries"]:
    assert git("rev-parse", CANDIDATE + ":packages/" + package["package"]).decode().strip() == package["source_tree"]
    lookup = reuse / "packages/client/node_modules" if package["package"] == "core" else bridge / "node_modules"
    assert (lookup / "@nsealr" / package["package"]).resolve() == (reuse / "packages" / package["package"]).resolve()
    assert (reuse / "packages" / package["package"] / "package.json").read_bytes() == blob(CANDIDATE, "packages/" + package["package"] + "/package.json")
    for row in package["dist"]:
        data = Path(row["path"]).read_bytes()
        assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
        dist_count += 1
assert dist_count == 52
for role in ("worker", "python", "node"):
    row = inputs[role]
    data = Path(row["path"]).read_bytes()
    assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
    assert data[:6] == b"\x7fELF\x02\x01" and int.from_bytes(data[18:20], "little") == 62
    assert os.access(row["path"], os.X_OK)
for path, expected in inputs["reused_W_source_binding"].items():
    data = blob(CANDIDATE, path)
    assert sha(data) == expected and data == blob(inputs["reused_W_original_actual_build_source"], path)
assert sys.version_info[:3] == (3, 12, 15) and Path(sys.executable).resolve() == Path(inputs["python"]["path"]).resolve()
environment = read(R00 / "environment.json")
for key, name in (("TMPDIR", "tmp"), ("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data")):
    (OUT / name).mkdir()
    environment[key] = str(OUT / name)
argv = [inputs["python"]["path"], str(SOURCE / "run-composition.py"), "--output", str(OUT / "composition"),
        "--worker", inputs["worker"]["path"], "--sha256", inputs["worker"]["sha256"],
        "--node", inputs["node"]["path"], "--bridge", str(bridge), "--reuse", str(reuse)]
source = git("rev-parse", "HEAD").decode().strip()
write(OUT / "preflight.json", {"candidate": CANDIDATE, "historical_static_review": STATIC,
      "historical_input_overlay": overlay, "historical_inputs_file_unchanged": True,
      "current_fix_manifest_members": 7, "historical_manifest_members": 10,
      "original_module_AST_restored_exact": True, "hold_AST_identical": True,
      "pure_RED_exit": 1, "pure_GREEN_cases": 6, "pure_archive_members": 13,
      "pure_controls_not_reexecuted": True, "prepared_outputs_rechecked": 11,
      "reused_dist_rechecked": 52, "source_to_prepared_JS_original_compiler_binding": preparation,
      "new_compilers": 0, "new_W_C_builds": 0,
      "tools": {role: inputs[role] for role in ("python", "node", "worker")},
      "ELF_ABI": "All three are executable ELF64 little-endian EM_X86_64; exact prior hashes",
      "python_version": sys.version, "Node_version_by_exact_binary_and_prior_preflight": "24.22.0",
      "host": platform.uname()._asdict(), "input_bindings": inputs["tracked_files"],
      "argv": argv, "source": source})
command = {"candidate": CANDIDATE, "source": source,
           "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
           "argv": argv, "cwd": str(ROOT), "environment": environment,
           "source_before": "", "started_utc": datetime.now(timezone.utc).isoformat(),
           "outer_watchdog": None, "role": "ONE independent actual corrected positive; no preparation/build/signing/old matrix"}
write(OUT / "command.json", command)
start = time.monotonic()
with (OUT / "stdout.log").open("wb") as stdout, (OUT / "stderr.log").open("wb") as stderr:
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, close_fds=True)
    command["invoker_pid"] = process.pid
    try:
        write(OUT / "command.json", command)
    except BaseException:
        pass  # Once spawned, failed bookkeeping must not bypass actual wait.
    while True:
        try:
            pid, raw_wait, usage = os.wait4(process.pid, 0)
            break
        except InterruptedError:
            continue
        except BaseException:
            try:
                write(OUT / "attention.json", {"reason": "invoker status unavailable; exact handle retained", "pid": process.pid})
            except BaseException:
                pass
            while True:
                time.sleep(1)
    assert pid == process.pid and (os.WIFEXITED(raw_wait) or os.WIFSIGNALED(raw_wait))
    process.returncode = os.waitstatus_to_exitcode(raw_wait)
command.update(invoker_wait_raw=raw_wait, exit_code=process.returncode,
               elapsed_seconds=time.monotonic() - start, completed_utc=datetime.now(timezone.utc).isoformat(),
               source_after=git("status", "--porcelain").decode())
try:
    os.wait4(process.pid, os.WNOHANG)
except ChildProcessError:
    command["after_actual_collection_ECHILD"] = True
else:
    raise RuntimeError("collected invoker remained waitable")
write(OUT / "command.json", command)
print(json.dumps({"exit_code": process.returncode, "actual_raw_wait": raw_wait,
                  "invoker_pid": process.pid, "elapsed_seconds": command["elapsed_seconds"], "output": str(OUT)}))
sys.exit(process.returncode)
