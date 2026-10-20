"""Reobserve the exact three failed input bytes, on both corrected intakes."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import nsealr_vault.signer as reference
from nsealr_vault.qr import decode_qr_envelope, decode_animated_qr_envelope_frames
from test_vault_core import Wire2RawQrTests

OUT = Path(__file__).parent
original = json.loads((OUT.parent / "raw-ingress-gap/observation.json").read_bytes())
rows = []
for item in original["rows"]:
    raw = item["original_json"].encode("utf-8")
    static, animated = Wire2RawQrTests.original_byte_frames(raw)
    for transport, decode, payload in (
        ("static", decode_qr_envelope, static),
        ("animated", decode_animated_qr_envelope_frames, animated),
    ):
        with patch.object(reference, "sign_request") as signer:
            rejected = False
            try:
                request = decode(payload)
                reference.sign_request(request, "unused", approved=True)
            except ValueError as error:
                rejected = True
                reason = str(error)
            signer.assert_not_called()
            assert rejected, (item["case"], transport)
            rows.append({"case": item["case"], "transport": transport, "original_json_sha256": hashlib.sha256(raw).hexdigest(), "original_json": item["original_json"], "result": "REJECTED_BEFORE_SIGNER", "reason": reason, "signer_invocations": signer.call_count})
result = {"status": "PASS_CORRECTED_SIX_ORIGINAL_INPUT_OBSERVATIONS", "historical_capture_unchanged": "../raw-ingress-gap/observation.json", "count": len(rows), "rows": rows}
assert len(rows) == 6
(OUT / "restoration-observations.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "count": len(rows)}))
