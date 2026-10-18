#!/usr/bin/env python3
"""Independently reconcile candidate source, evidence and package provenance."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve()
CANDIDATE = "61641047d13b5bb265246b181edc38f4dc2073e7"
BASE = "61b0c39131012c40ff76321bb3650def6e7a9d83"
EVIDENCE = ROOT / "docs/restart/implementation/S02/evidence"
report = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "candidate": CANDIDATE, "base": BASE, "checks": [], "limitations": []}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check(kind, path, expected, actual):
    report["checks"].append({"kind": kind, "path": str(path), "expected": expected, "actual": actual, "pass": actual == expected})

def blob(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)

check("head", "HEAD", CANDIDATE, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
check("dirty", "worktree", "", subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
index = json.loads((EVIDENCE / "artifact-index.json").read_text())
for row in index["artifacts"]:
    check("artifact-index", row["path"], row["sha256"], sha((ROOT / row["path"]).read_bytes()))
tested = json.loads((EVIDENCE / "tested-source-hashes.json").read_text())
for path, expected in tested["files"].items():
    check("tested-source-to-candidate", path, expected, sha(blob(CANDIDATE, path)))
    check("candidate-to-readonly-worktree", path, sha(blob(CANDIDATE, path)), sha((ROOT / path).read_bytes()))
changed = subprocess.check_output(["git", "diff", "--name-only", f"{BASE}..{CANDIDATE}"], cwd=ROOT, text=True).splitlines()
source_changes = [p for p in changed if not p.startswith("docs/")]
check("changed-source-completeness", "tested-source-hashes.json", sorted(source_changes), sorted(tested["files"]))
latest_tested = json.loads((EVIDENCE / "rebased-integration/commands.json").read_text())
report["rebased_evidence_candidate"] = latest_tested["candidate_commit"]
report["changes_since_rebased_tests"] = subprocess.check_output(["git", "diff", "--name-only", latest_tested["candidate_commit"], CANDIDATE], cwd=ROOT, text=True).splitlines()
check("no-product-change-after-tests", "rebased-evidence-to-final", [], [p for p in report["changes_since_rebased_tests"] if not p.startswith("docs/")])

def nested_logs(obj, directory):
    if isinstance(obj, dict):
        if "log" in obj and "sha256" in obj:
            path = ROOT / obj["log"] if obj["log"].startswith("docs/") else directory / obj["log"]
            check("command-log", path.relative_to(ROOT), obj["sha256"], sha(path.read_bytes()))
        for value in obj.values():
            nested_logs(value, directory)
    elif isinstance(obj, list):
        for value in obj:
            nested_logs(value, directory)

for path in [EVIDENCE / "integration/commands.json", EVIDENCE / "rebased-integration/commands.json", EVIDENCE / "crypto/runs.json", EVIDENCE / "crypto/link-runs.json"]:
    nested_logs(json.loads(path.read_text()), path.parent)

lock = tomllib.loads((ROOT / "Cargo.lock").read_text())
packages = {(p["name"], p["version"]): p for p in lock["package"]}
dependencies = json.loads((EVIDENCE / "dependencies.json").read_text())
cache = Path.home() / ".cargo/registry/cache"
for package in dependencies["added_registry_sources"]:
    name, version = package["name"], package["version"]
    vendor = ROOT / "vendor" / name
    checksum = json.loads((vendor / ".cargo-checksum.json").read_text())
    check("lock-package-checksum", name, package["registry_checksum"], packages[(name, version)]["checksum"])
    check("vendor-package-checksum", name, package["registry_checksum"], checksum["package"])
    check("manifest", name, package["manifest_sha256"], sha((vendor / "Cargo.toml").read_bytes()))
    check("license-declaration", name, package["license"], tomllib.loads((vendor / "Cargo.toml").read_text())["package"]["license"])
    for filename, expected in package["license_files"].items():
        check("license-file", f"{name}/{filename}", expected, sha((vendor / filename).read_bytes()))
    for filename, expected in checksum["files"].items():
        check("vendor-file", f"{name}/{filename}", expected, sha((vendor / filename).read_bytes()))
    archives = list(cache.glob(f"*/{name}-{version}.crate"))
    if not archives:
        report["limitations"].append(f"Missing cached registry archive for {name}-{version}")
        continue
    archive = archives[0]
    check("registry-archive", name, package["registry_checksum"], sha(archive.read_bytes()))
    with tarfile.open(archive) as tar:
        prefix = f"{name}-{version}/"
        for member in tar:
            if member.isfile():
                filename = member.name.removeprefix(prefix)
                if (vendor / filename).is_file():
                    check("archive-to-vendor", f"{name}/{filename}", sha(tar.extractfile(member).read()), sha((vendor / filename).read_bytes()))
                else:
                    # Cargo vendor omits VCS/dotfile metadata. Preserve each
                    # omission for review; checksummed and licensed files above
                    # must still exist and match.
                    report.setdefault("archive_entries_omitted_from_vendor", []).append(f"{name}/{filename}")

registry_src = Path.home() / ".cargo/registry/src"
for row in json.loads((EVIDENCE / "source-review.json").read_text())["files"]:
    source = next(registry_src.glob("*/" + row["registry_source"]))
    check("reviewed-registry-source", row["registry_source"], row["sha256"], sha(source.read_bytes()))

research = ROOT / "research/2026-10-13/crypto"
check("BIP340-oracle", "official CSV", "34c9d1d9c3a88d524bc80778540dc43f8306ec249a7485293063c376db851c2d", sha((research / "sources/bitcoin/bips/bip-0340/test-vectors.csv").read_bytes()))
path = research / "sources/paulmillr/nip44/nip44.vectors.json"
check("NIP44-oracle", "pinned unredistributed JSON", "269ed0f69e4c192512cc779e78c555090cebc7c785b609e338a62afc3ce25040", sha(path.read_bytes()))
data = json.loads(path.read_text())["v2"]
generated = '// Generated from hash-verified public test vectors; do not commit this generated file.\n'
generated += 'const NIP44_VALID: &[(&str,&str,&str)] = &[\n' + ''.join('(' + ','.join(json.dumps(v[k]) for k in ('sec1', 'pub2', 'conversation_key')) + '),\n' for v in data['valid']['get_conversation_key']) + '];\n'
generated += 'const NIP44_INVALID: &[(&str,&str)] = &[\n' + ''.join('(' + ','.join(json.dumps(v[k]) for k in ('sec1', 'pub2')) + '),\n' for v in data['invalid']['get_conversation_key']) + '];\n'
check("generated-fixture-to-pinned-oracle", "tests/nip44_data.rs", sha(generated.encode()), sha((research / "tests/nip44_data.rs").read_bytes()))
tracked = subprocess.check_output(["git", "ls-files", "research/2026-10-13/crypto/tests/nip44_data.rs", "research/2026-10-13/crypto/sources/paulmillr/nip44/nip44.vectors.json"], cwd=ROOT, text=True)
check("unlicensed-fixture-not-published", "git ls-files", "", tracked)

report["limitations"].append("Command logs prove recorded outcomes only; this verifies integrity and source binding, not that every recorded run was independently executed. Focused reviewer runs are preserved separately. Earlier crypto ELFs share overwritten output paths; old ELF bytes are not available for independently rehashing each historical hash.")
report["passed"] = all(c["pass"] for c in report["checks"])
report["check_count"] = len(report["checks"])
report["failed_checks"] = [c for c in report["checks"] if not c["pass"]]
report["check_counts_by_kind"] = {kind: sum(c["kind"] == kind for c in report["checks"]) for kind in sorted({c["kind"] for c in report["checks"]})}
report["complete_checkset_sha256"] = sha(json.dumps(report["checks"], sort_keys=True, separators=(",", ":")).encode())
report["input_manifests"] = [{"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes())} for p in [EVIDENCE / "artifact-index.json", EVIDENCE / "tested-source-hashes.json", EVIDENCE / "source-review.json", EVIDENCE / "dependencies.json", ROOT / "Cargo.lock"]]
report["record_format"] = "Successful checks are summarized by kind to avoid repeating the candidate's hash manifests; the reproducible script regenerates the complete check set bound by complete_checkset_sha256. All failures would be preserved individually."
del report["checks"]
(HERE / "evidence-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ["check_count", "passed", "failed_checks", "limitations"]}, indent=2))
raise SystemExit(0 if report["passed"] else 1)
