#!/usr/bin/env python3
"""Two already-public messages only; no fixture/contract/provider amendment."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
ORACLE = ROOT / "docs/restart/implementation/S03/oracle-source/bip340_reference.py"
ORACLE_SHA = "f69bd3446fd4dce92106d29a0dfb13bf9fbdf447cbfdcae1b2dcf9e6c0f1cda5"


def main():
    assert hashlib.sha256(ORACLE.read_bytes()).hexdigest() == ORACLE_SHA
    spec = importlib.util.spec_from_file_location("pinned_s03_bip340", ORACLE)
    bip = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bip)
    sys.path.insert(0, str(ROOT / "apps/pi/app"))
    from nsealr_vault.engine_adapter import EngineAdapter
    adapter = EngineAdapter(os.environ["NSEALR_QP01_LIBRARY"], os.environ["NSEALR_QP01_LIBRARY_SHA256"])
    key_path = ROOT / "protocols/contracts/v1/vectors/keys/test-key-1.json"
    # This exact scalar is public in the original contract. Never a key API.
    scalar = bytes.fromhex("11" * 32)
    pubkey = bip.pubkey_gen(scalar)
    rows = []
    for filename in ["kind-1-basic.json", "kind-1-tags.json"]:
        path = ROOT / "protocols/contracts/v1/vectors/events" / filename
        data = json.loads(path.read_text())
        request = json.dumps(data["request"], separators=(",", ":")).encode()
        original_frame = b"nsealr1:" + base64.urlsafe_b64encode(request).rstrip(b"=")
        calls, pages = [], []

        def auxiliary():
            value = bytes(32)
            calls.append({"call": len(calls) + 1, "reported_bytes": len(value), "bytes_hex": value.hex()})
            return value

        def present(page):
            pages.append({"kind": page.kind, "index": page.index, "total": page.total,
                          "label_hex": page.label.hex(), "body_hex": page.body.hex(),
                          "position_hex": page.position.hex()})
            return 1 if page.kind else 0

        response_frame = adapter.run_request_frame(original_frame, present, lambda: 0, auxiliary, lambda: False)
        payload = response_frame[8:]
        response = json.loads(base64.urlsafe_b64decode(payload + b"=" * (-len(payload) % 4)))
        actual = response["result"]["event"]
        template = data["event_template"]
        canonical = json.dumps([0, pubkey.hex(), template["created_at"], template["kind"],
                                template["tags"], template["content"]], ensure_ascii=False,
                               separators=(",", ":")).encode()
        message = hashlib.sha256(canonical).digest()
        zero_aux = bip.schnorr_sign(message, scalar, bytes(32))
        legacy = bytes.fromhex(data["signature"])
        actual_signature = bytes.fromhex(actual["sig"])
        row = {"fixture": str(path.relative_to(ROOT)), "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "request_id": data["request"]["request_id"], "canonical_hex": canonical.hex(), "event_id": message.hex(),
               "pubkey": pubkey.hex(), "legacy_signature": legacy.hex(), "oracle_zero_aux_signature": zero_aux.hex(),
               "actual_signature": actual_signature.hex(), "auxiliary_callbacks": calls, "presentations": pages,
               "actual_response": response, "input_frame_bytes": len(original_frame),
               "input_frame_sha256": hashlib.sha256(original_frame).hexdigest(),
               "output_frame_bytes": len(response_frame), "output_frame_sha256": hashlib.sha256(response_frame).hexdigest(),
               "oracle_verifies_legacy": bip.schnorr_verify(message, pubkey, legacy),
               "oracle_verifies_zero_aux": bip.schnorr_verify(message, pubkey, zero_aux),
               "oracle_verifies_actual": bip.schnorr_verify(message, pubkey, actual_signature),
               "actual_equals_zero_aux": actual_signature == zero_aux, "legacy_equals_zero_aux": legacy == zero_aux}
        assert actual["id"] == message.hex() == data["event_id"]
        assert actual["pubkey"] == pubkey.hex() == data["signed_event"]["pubkey"]
        assert {k: actual[k] for k in template} == template
        assert response["request_id"] == data["request"]["request_id"]
        assert calls == [{"call": 1, "reported_bytes": 32, "bytes_hex": "00" * 32}]
        assert row["oracle_verifies_legacy"] and row["oracle_verifies_zero_aux"] and row["oracle_verifies_actual"]
        assert row["actual_equals_zero_aux"] and not row["legacy_equals_zero_aux"]
        rows.append(row)
    print(json.dumps({"scope": "bounded diagnosis only; original expectations remain unchanged",
                      "oracle": str(ORACLE.relative_to(ROOT)), "oracle_sha256": ORACLE_SHA,
                      "key_source_sha256": hashlib.sha256(key_path.read_bytes()).hexdigest(),
                      "library": str(adapter.library_path), "library_sha256": adapter.library_sha256,
                      "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
