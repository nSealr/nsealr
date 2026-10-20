#!/usr/bin/env python3
"""Copy only the admitted public S03 inputs, with exact Git/hash bindings."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
REVIEW = "826fc0d71d5dad07fa735efafe27ac33863f49bb"
ADMISSION = Path("/home/tux/nsealr/.restart-tools/goal/s03-preparation-checks-2026-10-20/implementation-admission.json")

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, data, mode):
    if path.exists():
        assert path.read_bytes() == data, path
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    path.chmod(0o755 if mode == "100755" else 0o644)

def copy(row, destination):
    data = git("show", row["commit"] + ":" + row["path"])
    entry = git("ls-tree", row["commit"], "--", row["path"]).decode().strip().split()
    assert entry[:3] == [row["mode"], "blob", row["blob"]], row
    assert len(data) == row["bytes"] and sha(data) == row["sha256"], row
    save(ROOT / destination, data, row["mode"])
    return dict(row, destination=destination,
                source_url="https://github.com/nSealr/nsealr/blob/" + row["commit"] + "/" + row["path"])

def main():
    historical = json.loads((SPEC / "source-pin-addendum.json").read_bytes())["historical_public_copy_manifest"]["files"]
    assert len(historical) == 80
    rows = [dict(copy(row, row["path"]), group="original_historical_public_copy") for row in historical]
    prefix = "docs/restart/implementation/reviews/S03-integration-spec-final/"
    review_rows = []
    for line in git("ls-tree", "-r", REVIEW, "--", prefix).decode().splitlines():
        meta, path = line.split("\t")
        mode, kind, blob = meta.split()
        assert kind == "blob" and mode in ("100644", "100755")
        data = git("show", REVIEW + ":" + path)
        row = dict(commit=REVIEW, path=path, mode=mode, blob=blob, bytes=len(data), sha256=sha(data))
        destination = str(HERE.relative_to(ROOT) / "spec-review" / path.removeprefix(prefix))
        review_rows.append(copy(row, destination))
    assert len(review_rows) == 6
    rows += [dict(row, group="distinct_preimplementation_review") for row in review_rows]
    admission = ADMISSION.read_bytes()
    assert sha(admission) == "c4549b268e1d1fea32ab49c9cc4ca5f9e1429e7c542004d33642259436b1f1e6"
    destination = HERE / "implementation-admission.json"
    save(destination, admission, "100644")
    rows.append(dict(group="root_implementation_admission", source_path=str(ADMISSION),
                     destination=str(destination.relative_to(ROOT)), mode="100644",
                     bytes=len(admission), sha256=sha(admission)))
    result = dict(schema_version=1, task="S03", specification="e95eaaf8e3fd76ede797f128f0cc7de43ab2bb03",
                  product_input="b1c90139a651895284b2624da7d12903cf16bc9d", files=rows,
                  privacy=dict(selection="Exact80 public historical Git blobs, full6-file public specification review and one public-safe root admission; no private history, runtime, manual or cache copied.",
                               historical_paths_preserved=True, original_source_reviews_not_rebound=True))
    (HERE / "input-copy-inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(copies=len(rows), historical=80, spec_review=6, admission=1,
                          inventory_sha256=sha((HERE / "input-copy-inventory.json").read_bytes()))))

if __name__ == "__main__":
    main()
