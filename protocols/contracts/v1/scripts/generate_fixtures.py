#!/usr/bin/env python3
"""Generate deterministic M1 nSealr protocol fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import secp256k1


ROOT = Path(__file__).resolve().parents[1]
SECRET_KEY_HEX = "1111111111111111111111111111111111111111111111111111111111111111"


def canonical_event_serialization(event: dict) -> str:
    payload = [
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def event_id(event: dict) -> str:
    serialized = canonical_event_serialization(event)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def xonly_pubkey(private_key: secp256k1.PrivateKey) -> str:
    out = secp256k1.ffi.new("unsigned char [32]")
    ok = secp256k1.lib.secp256k1_xonly_pubkey_serialize(
        secp256k1.secp256k1_ctx,
        out,
        private_key.pubkey.xonly_pubkey,
    )
    if ok != 1:
        raise RuntimeError("failed to serialize x-only public key")
    return bytes(secp256k1.ffi.buffer(out, 32)).hex()


def sign_event(private_key: secp256k1.PrivateKey, template: dict) -> dict:
    pubkey = xonly_pubkey(private_key)
    event = {
        "pubkey": pubkey,
        "created_at": template["created_at"],
        "kind": template["kind"],
        "tags": template["tags"],
        "content": template["content"],
    }
    event["id"] = event_id(event)
    signature = private_key.schnorr_sign(bytes.fromhex(event["id"]), "", raw=True)
    event["sig"] = signature.hex()
    return {
        "id": event["id"],
        "pubkey": event["pubkey"],
        "created_at": event["created_at"],
        "kind": event["kind"],
        "tags": event["tags"],
        "content": event["content"],
        "sig": event["sig"],
    }


def write_json(rel: str, value: dict) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sign_fixture(private_key: secp256k1.PrivateKey, name: str, request_id: str, template: dict) -> None:
    event = sign_event(private_key, template)
    request = {
        "version": 1,
        "request_id": request_id,
        "method": "sign_event",
        "params": {"event_template": template},
    }
    response = {
        "version": 1,
        "request_id": request_id,
        "ok": True,
        "result": {"event": event},
    }
    vector = {
        "name": name,
        "request": request,
        "response": response,
        "event_template": template,
        "signed_event": event,
        "canonical_serialization": canonical_event_serialization(event),
        "event_id": event["id"],
        "signature": event["sig"],
    }
    write_json(f"vectors/events/{name}.json", vector)
    write_json(f"examples/request-{name}.json", request)
    write_json(f"examples/response-{name}.json", response)


def main() -> int:
    private_key = secp256k1.PrivateKey(bytes.fromhex(SECRET_KEY_HEX), raw=True)
    public_key = xonly_pubkey(private_key)

    write_json(
        "vectors/keys/test-key-1.json",
        {
            "name": "test-key-1",
            "warning": "Deterministic public fixture key for tests only. Never use in production.",
            "secret_key": SECRET_KEY_HEX,
            "public_key": public_key,
        },
    )

    write_json(
        "examples/request-get-public-key.json",
        {
            "version": 1,
            "request_id": "req-pubkey-1",
            "method": "get_public_key",
        },
    )
    write_json(
        "examples/response-get-public-key.json",
        {
            "version": 1,
            "request_id": "req-pubkey-1",
            "ok": True,
            "result": {"public_key": public_key},
        },
    )
    write_json(
        "examples/response-error-rejected.json",
        {
            "version": 1,
            "request_id": "req-kind-1-basic",
            "ok": False,
            "error": {
                "code": "user_rejected",
                "message": "User rejected the signing request.",
                "retryable": True,
            },
        },
    )

    sign_fixture(
        private_key,
        "kind-1-basic",
        "req-kind-1-basic",
        {
            "created_at": 1710000000,
            "kind": 1,
            "tags": [],
            "content": "nSealr fixture: basic kind 1 event.",
        },
    )
    sign_fixture(
        private_key,
        "kind-1-tags",
        "req-kind-1-tags",
        {
            "created_at": 1710000060,
            "kind": 1,
            "tags": [
                ["p", public_key, "", "mention"],
                ["t", "nsealr"],
            ],
            "content": "nSealr fixture: tagged kind 1 event.",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

