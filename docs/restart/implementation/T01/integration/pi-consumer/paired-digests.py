"""Compare six observed diagnostics to already fixed independent expectations."""
import json
import runpy
import subprocess
from pathlib import Path

from nsealr_vault.display import approval_digest_for_request

ROOT = Path(__file__).resolve().parents[6]
EVIDENCE = ROOT / "docs/restart/implementation/T01/integration/evidence"
expected = json.loads((EVIDENCE / "independent-wire2-transform.json").read_bytes())["diagnostic_digest_map"]
# Reuse the fixed, product-free formula only to identify each OLD input's map
# entry. Expected new values remain the literal eab4c96f map fixed before edits.
independent = runpy.run_path(str(EVIDENCE / "independent-wire2-transform.py"))
rows = []
for path in sorted((ROOT / "protocols/contracts/v1/vectors/review").glob("*.json")):
    relative = path.relative_to(ROOT).as_posix()
    old = json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", "dbad656997ad8cf9024ca1489291f5f1d4d3094a:" + relative]))
    old_digest = independent["diagnostic"](old["request"], old["review"], independent["pages"](old["review"]))
    current = json.loads(path.read_bytes())
    observed = approval_digest_for_request(current["request"])
    assert observed == expected[old_digest], relative
    rows.append({"path": relative, "old_digest": old_digest, "expected_new_digest": expected[old_digest], "observed_new_digest": observed})
assert len(rows) == len(expected) == 6
assert {row["old_digest"] for row in rows} == set(expected)
result = {"status": "PASS_SIX_FIXED_DIAGNOSTIC_PAIRS", "expected_source": "eab4c96f06f770f0e5ad404c3c316c43340681e0", "expected_from_product_output": False, "rows": rows}
Path(__file__).with_name("paired-digests.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "count": len(rows)}))
