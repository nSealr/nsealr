"""Observe the excluded reference ingress gap; do not bless it as a contract test."""
import base64
import json
from pathlib import Path

from nsealr_vault.qr import decode_qr_envelope
from nsealr_vault.signer import sign_request

ROOT = Path(__file__).resolve().parents[6]
ARTIFACT = ROOT / "protocols/contracts/v1"
request = json.loads((ARTIFACT / "examples/request-kind-1-basic.json").read_bytes())
key = json.loads((ARTIFACT / "vectors/keys/test-key-1.json").read_bytes())
raw = json.dumps(request, ensure_ascii=False, separators=(",", ":"))
rows = []
for name, original in (
    ("duplicate-kind", raw.replace('"kind":1', '"kind":0,"kind":1')),
    ("escaped-key-alias", raw.replace('"kind":1', '"kind":0,"\\u006bind":1')),
    ("negative-zero-spelling", raw.replace('"created_at":1710000000', '"created_at":-0')),
):
    assert original != raw
    envelope = "nsealr1:" + base64.urlsafe_b64encode(original.encode()).decode().rstrip("=")
    decoded = decode_qr_envelope(envelope)
    response = sign_request(decoded, key["secret_key"], approved=True)
    rows.append({
        "case": name,
        "original_json": original,
        "expected_strict_ingress": "REJECT before operation",
        "actual_reference_response_ok": response["ok"],
        "actual_error_code": response.get("error", {}).get("code"),
        "disposition": "OPEN_RAW_REFERENCE_GAP" if response["ok"] else "REJECTED",
    })
output = {
    "scope": "Excluded independent Pi reference decoder; not the shared Rust engine or a qualified signer",
    "source_boundary": "apps/pi/app/nsealr_vault/qr.py:84 json.loads(decoded) loses duplicate aliases and numeric spelling; signer.py receives only a dict",
    "fixed_case_obligation": "T01 S-03 retains original-byte duplicate and unsigned integer grammar rejection; this reference path does not satisfy it",
    "rows": rows,
    "unresolved": any(row["actual_reference_response_ok"] for row in rows),
    "required_shared_engine_boundary": "Q02 must submit original bytes to the core without a permissive JSON roundtrip. No excluded file is edited or negative obligation waived here.",
}
Path(__file__).with_name("raw-boundary-observation.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output, indent=2))
raise SystemExit(1 if output["unresolved"] else 0)
