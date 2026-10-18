from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import secp256k1

HEX32_RE = re.compile(r"^[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{128}$")


def canonical_event_serialization(event: dict[str, Any]) -> str:
    payload = [
        0,
        event["pubkey"],
        event["created_at"],
        event["kind"],
        event["tags"],
        event["content"],
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def event_id(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_event_serialization(event).encode("utf-8")).hexdigest()


def _private_key(secret_key_hex: str) -> secp256k1.PrivateKey:
    if not HEX32_RE.fullmatch(secret_key_hex):
        raise ValueError("secret key must be 32-byte lowercase hex")
    secret = bytes.fromhex(secret_key_hex)
    return secp256k1.PrivateKey(secret, raw=True)


def xonly_pubkey_from_secret(secret_key_hex: str) -> str:
    private_key = _private_key(secret_key_hex)
    out = secp256k1.ffi.new("unsigned char [32]")
    ok = secp256k1.lib.secp256k1_xonly_pubkey_serialize(
        secp256k1.secp256k1_ctx,
        out,
        private_key.pubkey.xonly_pubkey,
    )
    if ok != 1:
        raise RuntimeError("failed to serialize x-only public key")
    return bytes(secp256k1.ffi.buffer(out, 32)).hex()


def sign_event(template: dict[str, Any], secret_key_hex: str) -> dict[str, Any]:
    for forbidden in ("id", "pubkey", "sig"):
        if forbidden in template:
            raise ValueError(f"event_template must not contain {forbidden}")

    private_key = _private_key(secret_key_hex)
    event = {
        "pubkey": xonly_pubkey_from_secret(secret_key_hex),
        "created_at": template["created_at"],
        "kind": template["kind"],
        "tags": template["tags"],
        "content": template["content"],
    }
    event["id"] = event_id(event)
    event["sig"] = private_key.schnorr_sign(bytes.fromhex(event["id"]), "", raw=True).hex()
    return {
        "id": event["id"],
        "pubkey": event["pubkey"],
        "created_at": event["created_at"],
        "kind": event["kind"],
        "tags": event["tags"],
        "content": event["content"],
        "sig": event["sig"],
    }


def verify_schnorr_signature(pubkey_hex: str, msg_hex: str, sig_hex: str) -> bool:
    if not HEX32_RE.fullmatch(pubkey_hex) or not HEX32_RE.fullmatch(msg_hex) or not HEX64_RE.fullmatch(sig_hex):
        return False
    xonly_pubkey = secp256k1.ffi.new("secp256k1_xonly_pubkey *")
    parsed = secp256k1.lib.secp256k1_xonly_pubkey_parse(
        secp256k1.secp256k1_ctx,
        xonly_pubkey,
        bytes.fromhex(pubkey_hex),
    )
    if parsed != 1:
        return False
    verified = secp256k1.lib.secp256k1_schnorrsig_verify(
        secp256k1.secp256k1_ctx,
        bytes.fromhex(sig_hex),
        bytes.fromhex(msg_hex),
        32,
        xonly_pubkey,
    )
    return bool(verified)
