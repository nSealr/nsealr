"""One frozen, targeted reviewer replay; no build or whole-component gate."""
import ast
from datetime import datetime, timezone
import gzip
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
CANDIDATE = "28a84f37190a4d36637acbe7614940f4218621dc"
MICRO = "3c9afc1c08c078704026694e2ff463eabb3ab8ac"
BUILD = "0b197dc19affabe00039ef358dd6cb8602bb7705"
QUALIFIED = "dc0b7c81a12bf83d70b6ce9ecd65b49ce55fc082"
NEGATIVE = ROOT / "docs/restart/implementation/QP01/python-owner-adapter/negative"
OLD_ROOT = ROOT.parent / "qp01-python-owner-adapter-micro-review"
MICRO_PREFIX = "docs/restart/implementation/reviews/QP01-python-owner-adapter-micro"
R00 = ROOT.parent / "r00/tools/baseline/.work/final"
OUT = HERE / ".runtime/targeted-01"


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def blob(commit, path):
    return git("show", f"{commit}:{path}")


def verify_archive(path, expected):
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        assert len(members) == expected + 1
        assert all(row.isfile() for row in members)
        names = [row.name for row in members]
        assert len(set(names)) == len(names)
        manifest = json.loads(archive.extractfile("manifest.json").read())
        assert len(manifest["members"]) == expected
        assert set(names) == {"manifest.json", *(row["path"] for row in manifest["members"])}
        for row in manifest["members"]:
            data = archive.extractfile(row["path"]).read()
            assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
    return {"path": str(path.relative_to(ROOT)), "members": expected,
            "sha256": sha(path.read_bytes()), "all_member_bytes_verified": True}


def methods(source):
    return {f"{cls.name}.{method.name}": ast.dump(method, include_attributes=False)
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef)}


assert not OUT.exists(), "One run only: never overwrite or automatically retry"
OUT.mkdir(parents=True)
source = git("rev-parse", "HEAD").decode().strip()
assert git("status", "--porcelain").decode() == ""
assert git("status", "--porcelain", cwd=OLD_ROOT).decode() == ""
correspondence = read(NEGATIVE / "final-source-correspondence.json")
assert correspondence["qualified_complete_gate_source"] == QUALIFIED
bindings = correspondence["source_bindings"]
assert len(bindings) == 33
for row in bindings:
    data = (ROOT / row["path"]).read_bytes()
    assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
    assert data == blob(CANDIDATE, row["path"]) == blob(QUALIFIED, row["path"])
manifest = read(NEGATIVE / "artifact-manifest.json")
assert len(manifest["members"]) == 21
for row in manifest["members"]:
    data = blob(CANDIDATE, row["path"])
    assert data == (ROOT / row["path"]).read_bytes()
    assert (len(data), sha(data)) == (row["bytes"], row["sha256"])
    assert git("ls-tree", CANDIDATE, "--", row["path"]).decode().split()[0] == row["mode"]
archives = [verify_archive(NEGATIVE / "focused-evidence.tar.gz", 97),
            verify_archive(NEGATIVE / "full-validation/stable/python-owner-cases.tar.gz", 70)]
for role in ("original-setup-red", "stable"):
    directory = NEGATIVE / "full-validation" / role
    raw = read(directory / "raw-log.json")
    compressed = (directory / "make-ci.log.gz").read_bytes()
    data = gzip.decompress(compressed)
    assert (len(data), sha(data), sha(compressed)) == (raw["bytes"], raw["sha256"], raw["gzip_sha256"])
micro = json.loads(blob(MICRO, f"{MICRO_PREFIX}/verification.json"))
micro_preflight = json.loads(blob(MICRO, f"{MICRO_PREFIX}/replay/preflight.json"))
worker = micro["worker_elf"]
worker_path = Path(worker["worker"])
worker_bytes = worker_path.read_bytes()
assert worker_bytes[:4] == b"\x7fELF" and os.access(worker_path, os.X_OK)
assert (len(worker_bytes), sha(worker_bytes)) == (worker["bytes"], worker["sha256"])
for path, expected in worker["source_binding"].items():
    data = blob(BUILD, path)
    assert sha(data) == expected and data == blob(CANDIDATE, path)
    assert data == (OLD_ROOT / path).read_bytes() == (ROOT / path).read_bytes()
vendor = git("ls-tree", "-r", "--full-tree", CANDIDATE, "--", "vendor")
assert vendor and vendor == git("ls-tree", "-r", "--full-tree", BUILD, "--", "vendor")
assert len(vendor.splitlines()) == micro_preflight["vendor_entries"] == 2125
for path in ("apps/pi/app/nsealr_vault/qr_owner_adapter.py", "apps/pi/app/nsealr_vault/qr_worker.py",
             "apps/pi/tests/test_qr_owner_adapter.py", "apps/pi/app/nsealr_vault/qr.py"):
    assert blob(BUILD, path) == blob(CANDIDATE, path)
test_path = "apps/pi/tests/test_qr_owner_adapter_lifecycle.py"
earlier = methods(blob("76a550d5e1b82027c94505be69ab868ed8a1368a", test_path))
current = methods(blob(CANDIDATE, test_path))
assert len(earlier) == 20 and all(current[key] == value for key, value in earlier.items())
assert set(current) - set(earlier) == {"OwnerAdapterLifecycleTests.test_10_normal259_release_once"}
assert methods(blob("975c05a6d7dc1d96e5f5044f640719cb20a7bd87", test_path)) == current
test_files = sorted((ROOT / "apps/pi/tests").glob("test_qr_owner_adapter*.py"))
assert [p.name for p in test_files] == ["test_qr_owner_adapter.py", "test_qr_owner_adapter_lifecycle.py"]
counts = {p.name: sum(name.split(".")[-1].startswith("test_") for name in methods(p.read_bytes())) for p in test_files}
assert sorted(counts.values()) == [3, 14]
expectations = read(NEGATIVE / "expectations.json")
python = Path(expectations["baseline_python"]["path"])
assert sha(python.read_bytes()) == expectations["baseline_python"]["sha256"] == micro["python"]["sha256"]
assert sys.version_info[:3] == (3, 12, 15) and Path(sys.executable).resolve() == python.resolve()
environment = read(R00 / "environment.json")
for key, directory in (("TMPDIR", "tmp"), ("XDG_CACHE_HOME", "cache"),
                       ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data")):
    (OUT / directory).mkdir()
    environment[key] = str(OUT / directory)
environment.update(PYTHONPATH=str(ROOT / "apps/pi/app"),
                   NSEALR_QP01_QR_WORKER=str(worker_path),
                   NSEALR_QP01_QR_WORKER_SHA256=worker["sha256"],
                   NSEALR_QP01_OWNER_EVIDENCE=str(OUT / "cases"))
argv = [str(python), "-B", "-m", "unittest", "discover", "-s", "apps/pi/tests",
        "-p", "test_qr_owner_adapter*.py", "-v", "-f"]
write(OUT / "preflight.json", {
    "candidate": CANDIDATE, "candidate_tree": git("rev-parse", f"{CANDIDATE}^{{tree}}").decode().strip(),
    "review_execution_source": source, "source_bindings": bindings, "author_manifest_members_verified": 21,
    "archives": archives, "author_raw_gzip_hashes_verified": ["original-setup-red", "stable"],
    "micro_review_reused": MICRO, "original_actual_build_source": BUILD,
    "worker_rechecked_before_any_frame": worker, "worker_build_source_inputs_exact": True,
    "vendor_entries": 2125, "vendor_tree": git("rev-parse", f"{CANDIDATE}:vendor").decode().strip(),
    "vendor_listing_sha256": sha(vendor), "unchanged_existing_method_ASTs": 20,
    "test_counts": counts, "python_version": sys.version, "python_sha256": sha(python.read_bytes()),
    "host": platform.uname()._asdict(), "new_builds": 0, "native_C": 0, "Node": 0})
command = {"argv": argv, "cwd": str(ROOT), "source": source,
           "tree": git("rev-parse", "HEAD^{tree}").decode().strip(), "source_status_before": "",
           "environment": environment, "started_utc": datetime.now(timezone.utc).isoformat(),
           "outer_watchdog": None, "no_signal_or_forced_cleanup_by_wrapper": True,
           "role": "ONE independent targeted17-method replay; unchanged source, retained verified ELF; no full gate"}
write(OUT / "command.json", command)
start = time.monotonic()
with (OUT / "stdout.log").open("wb") as stdout, (OUT / "stderr.log").open("wb") as stderr:
    completed = subprocess.run(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, check=False)
command.update(exit_code=completed.returncode, elapsed_seconds=time.monotonic() - start,
               completed_utc=datetime.now(timezone.utc).isoformat(),
               source_status_after=git("status", "--porcelain").decode(),
               worker_sha256_after=sha(worker_path.read_bytes()))
write(OUT / "command.json", command)
print(json.dumps({"exit_code": completed.returncode, "elapsed_seconds": command["elapsed_seconds"],
                  "source": source, "output": str(OUT)}))
sys.exit(completed.returncode)
