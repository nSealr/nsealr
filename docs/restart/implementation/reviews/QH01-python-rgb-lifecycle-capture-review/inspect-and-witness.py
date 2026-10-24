"""Frozen Git/archive inspection and three bounded data-only checker witnesses.

No product modules, processes, sockets, files or signals are exercised. The
original log is read only. Expected before execution: all three corruptions are
incorrectly accepted by candidate9703's new lifecycle function.
"""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
CANDIDATE = "9703d03d0cf2e57bbf4de523b70aa0a2c7110768"
BASE = "bd523ad3488305cd691916605ac77c27131c8e9a"
HEAD = "f7f300960e693fa6f47001cdb6f069372b82b67d"
CHECKER = "docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py"
PACKET = "docs/restart/implementation/reviews/QH01-python-rgb-lifecycle-capture/"
ADAPTER = "apps/pi/app/nsealr_vault/qr_owner_adapter.py"
WORKER = "apps/pi/qr-worker/src/main.rs"
LOG = Path("/home/tux/nsealr/.restart-tools/goal/qh01-python-rgb-lifecycle-ci-runtime-2026-10-24/make-pi-ci-01.log")

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def blob(ref, path):
    return git("show", ref + ":" + path)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

assert git("rev-parse", CANDIDATE + "^{tree}").decode().strip() == "9a11a5c1ac6699af616332c5b80dc5d4d11afc86"
source = blob(CANDIDATE, CHECKER)
assert source == (ROOT / CHECKER).read_bytes()
assert sha(source) == "20f7e533837c659936e4e9b8b59d0b4879055dcafe4957122bc279a2b907d247"
old, changed = ast.parse(blob(BASE, CHECKER)), ast.parse(source)
added = [n for n in changed.body if isinstance(n, ast.FunctionDef) and n.name == "verify_qh01_lifecycle"]
assert len(added) == 1
changed.body.remove(added[0])
product = next(n for n in changed.body if isinstance(n, ast.FunctionDef) and n.name == "verify_product")
call = ast.parse("out.update(verify_qh01_lifecycle(objects))").body[0]
added_calls = [n for n in product.body if ast.dump(n) == ast.dump(call)]
assert len(added_calls) == 1
product.body.remove(added_calls[0])
assert ast.dump(changed) == ast.dump(old)
manifest = json.loads(blob(CANDIDATE, PACKET + "artifact-manifest.json"))
assert manifest["members_count"] == len(manifest["members"]) == 19
paths = git("ls-tree", "-r", "--full-tree", "--name-only", CANDIDATE, PACKET).decode().splitlines()
assert set(paths) == {r["path"] for r in manifest["members"]} | {PACKET + "artifact-manifest.json"}
for row in manifest["members"]:
    raw = blob(CANDIDATE, row["path"])
    assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
for path in (ADAPTER, WORKER):
    assert blob(CANDIDATE, path) == blob(HEAD, path)
log = LOG.read_bytes()
assert len(log) == 616947 and sha(log) == "e3b31f6f629f45eefeb0e2374c98958a850425738b63347f7e1ec48c82cf8eac"
objects = []
for line in log.decode().splitlines():
    if line.startswith("{"):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(value) is dict:
            objects.append(value)
spec = importlib.util.spec_from_file_location("frozen_lifecycle_checker", ROOT / CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
baseline = checker.verify_qh01_lifecycle(objects)
witnesses = []

def selected(rows, index):
    return [o["qh01_lifecycle_case"] for o in rows if "qh01_lifecycle_case" in o][index]["collection"]["B3"]

def wire(o):
    return b"".join((json.dumps(row, separators=(",", ":")) + "\n").encode("ascii") for row in (o["phase"], o["terminal"]))

for name, index in [("noncanonical_status_over4096", 0), ("canonical_phase_nonpipe_FD", 0), ("preG_unexpected_stderr", 2)]:
    rows = copy.deepcopy(objects)
    o = selected(rows, index)
    original = base64.b64decode(o["status_wire_base64"], validate=True)
    if name == "noncanonical_status_over4096":
        mutated = b" " * 4096 + original
        assert len(mutated) > 4096
        violation = "Only wire changes: prepend4096 ASCII spaces; parsed phase/terminal unchanged, status cap exceeded and canonical serialization violated."
    elif name == "canonical_phase_nonpipe_FD":
        o["phase"]["fds"][0]["target"] = "/definitely-not-a-pipe"
        mutated = wire(o)
        assert len(mutated) < 4096
        violation = "FD0 target no longer equals pipe:[ino]; keep numbers/identity and canonical phase/terminal wire cross-binding."
    else:
        t = o["terminal"]
        assert t["G_bytes"] == t["image_bytes_sent"] == t["stderr_observed"] == t["stderr_retained"] == 0
        assert t["worker_wait"]["exit_code"] == -9
        t["stderr_observed"] = t["stderr_retained"] = 1
        t["worker_stderr_base64"] = base64.b64encode(b"x").decode("ascii")
        mutated = wire(o)
        violation = "Actual preG SIGKILL trace changed to one stderr byte with exact counts/canonical base64 and status-wire cross-binding; source emits none before G on this admitted path."
    o["status_wire_base64"] = base64.b64encode(mutated).decode("ascii")
    result = checker.verify_qh01_lifecycle(rows)
    assert result == baseline, "The anticipated missing check no longer reproduces; retain this failure."
    witnesses.append({"name": name, "case_index": index, "mutation": violation,
                      "original_status_bytes": len(original), "mutated_status_bytes": len(mutated),
                      "original_status_sha256": sha(original), "mutated_status_sha256": sha(mutated),
                      "checker_returned_success": True, "same_return_as_original": True,
                      "classification": "INVALID_EVIDENCE_ACCEPTED_NOT_A_PRODUCT_RUN_OR_LEAK"})
out = {"candidate": CANDIDATE, "tree": "9a11a5c1ac6699af616332c5b80dc5d4d11afc86",
       "checker_sha256": sha(source), "script_sha256": sha(Path(__file__).read_bytes()),
       "runtime_source": HEAD, "log_path": str(LOG), "log_bytes": len(log), "log_sha256": sha(log),
       "source_checks": {"old_AST_exact_after_only_new_function_and_call_removed": True,
                         "author_manifest_members": 19, "author_manifest_plus_self": 20,
                         "B3_sha256": sha(blob(CANDIDATE, ADAPTER)), "worker_sha256": sha(blob(CANDIDATE, WORKER))},
       "original_lifecycle_return": baseline, "witnesses": witnesses,
       "verdict": "CHANGES_REQUESTED", "new_product_processes": 0}
(OUT / "witness-result.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"verdict": "CHANGES_REQUESTED", "invalid_witnesses_accepted": len(witnesses), "product_processes": 0}))
