"""Frozen Git/manifest inspection only; no candidate import or product execution."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
FINAL = "00d72b477ef43269f65b2dfe8ff828270f8d1a7d"
BASE = "bd523ad3488305cd691916605ac77c27131c8e9a"
CHECKER = "docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py"
REVIEWS = "docs/restart/implementation/reviews/"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def data(ref, path):
    return git("show", ref + ":" + path)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

assert git("rev-parse", FINAL + "^{tree}").decode().strip() == "22b62fd5348de444b2d880778629249095e098e7"
source = data(FINAL, CHECKER)
assert source == (ROOT / CHECKER).read_bytes()
assert sha(source) == "4b66f6242f2fed02eb2da923396d2ecf9b4f697c55edd6068a920003e4eef36f"
old, tree = ast.parse(data(BASE, CHECKER)), ast.parse(source)
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verify_qh01_lifecycle"]
assert len(functions) == 1
tree.body.remove(functions[0])
product = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verify_product")
expected = ast.parse("out.update(verify_qh01_lifecycle(objects))").body[0]
calls = [n for n in product.body if ast.dump(n) == ast.dump(expected)]
assert len(calls) == 1
product.body.remove(calls[0])
assert ast.dump(tree) == ast.dump(old)
before = data("522356e199cb214ee39d540a36dc66940c18746f", CHECKER)
addition = b"        assert list(p['limits']) == ['AS', 'CPU', 'CORE']\n"
assert source.count(addition) == 1 and source.replace(addition, b"") == before
packets = []
for prefix, original, expected_count in [
    ("QH01-python-rgb-lifecycle-capture", "9703d03d0cf2e57bbf4de523b70aa0a2c7110768", 19),
    ("QH01-python-rgb-lifecycle-capture-correction", "522356e199cb214ee39d540a36dc66940c18746f", 9),
    ("QH01-python-rgb-lifecycle-capture-order", FINAL, 8),
    ("QH01-python-rgb-lifecycle-capture-review", "b284ca9b0e4a94f657615ee3ac0bfe8d26b34cb2", 11),
]:
    path = REVIEWS + prefix + "/"
    listing = git("ls-tree", "-r", "--full-tree", "--name-only", FINAL, path).decode().splitlines()
    manifest = json.loads(data(FINAL, path + "artifact-manifest.json"))
    assert manifest["members_count"] == len(manifest["members"]) == expected_count
    assert set(listing) == {x["path"] for x in manifest["members"]} | {path + "artifact-manifest.json"}
    for member in manifest["members"]:
        raw = data(FINAL, member["path"])
        assert len(raw) == member["bytes"] and sha(raw) == member["sha256"]
    for name in listing:
        assert git("ls-tree", FINAL, name) == git("ls-tree", original, name)
    packets.append({"prefix": path, "original": original, "members": expected_count,
                    "total": len(listing), "manifest_sha256": sha(data(FINAL, path + "artifact-manifest.json")),
                    "exact_modes_blobs_preserved": True})
bindings = {}
for path in ["apps/pi/app/nsealr_vault/qr_owner_adapter.py", "apps/pi/qr-worker/src/main.rs"]:
    assert data(FINAL, path) == data(BASE, path)
    bindings[path] = sha(data(FINAL, path))
for suffix, digest in [
    ("QH01-python-rgb-lifecycle-capture-correction/test_capture_extension.py", "faeab9165364e562a12115712139b71b96d98b86a4bbc19d498464fff1ff9bef"),
    ("QH01-python-rgb-lifecycle-capture-order/test_limits_order.py", "2eaabca1fafc085823f5bd7822ef5d0febd91e4e96575c2ff7389be7400191ac"),
]:
    path = REVIEWS + suffix
    assert sha(data(FINAL, path)) == digest
    bindings[path] = digest
result = {"role": "metadata-only frozen source and historical packet correspondence",
          "candidate": FINAL, "tree": "22b62fd5348de444b2d880778629249095e098e7",
          "checker_sha256": sha(source), "old_BD_AST_preserved": True,
          "only_checker_change_from_522": "one ordered limits-key assertion", "packets": packets,
          "source_bindings": bindings, "new_product_processes": 0,
          "read_lookup_observation": "An initial read used nonexistent control.py/report.json names and returned exit1. The actual inventory named test_limits_order.py/control.json; these exact files were then read. No verifier/test/runtime result was inferred from the failed lookup."}
(OUT / "source-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"source_and_packet_checks": "PASS", "packets": len(packets), "files": sum(x["total"] for x in packets), "product_processes": 0}))
