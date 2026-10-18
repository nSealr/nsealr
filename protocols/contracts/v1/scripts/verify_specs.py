#!/usr/bin/env python3
"""Verify nSealr M1 specs, examples, and cryptographic fixtures."""

from __future__ import annotations

import hashlib
import json
import re
import base64
import binascii
from pathlib import Path
from urllib.parse import parse_qsl, urlparse, urlunparse

import secp256k1


ROOT = Path(__file__).resolve().parents[1]
HEX32_RE = re.compile(r"^[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{128}$")
HEX8_RE = re.compile(r"^[0-9a-f]{16}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
POLICY_ID_RE = re.compile(r"^policy-[A-Za-z0-9._:-]{1,121}$")
GRANT_ID_RE = re.compile(r"^grant-[A-Za-z0-9._:-]{1,122}$")
PROPOSAL_ID_RE = re.compile(r"^proposal-[A-Za-z0-9._:-]{1,119}$")
B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
QR_PREFIX = "nsealr1:"
ANIMATED_QR_PREFIX = "nsealr1a:"
SERIAL_PREFIX = "nsealr1f:"
APDU_HEX_RE = re.compile(r"^[0-9a-f]+$")
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CHARSET_REV = {char: index for index, char in enumerate(BECH32_CHARSET)}
LIMIT_PROFILE = "vectors/limits/nsealr-v0.json"
MAX_SAFE_INTEGER = 9007199254740991
DEVICE_METHODS = {"get_capabilities", "get_signing_status", "get_public_key", "sign_event"}
ROUTE_TYPES = {
    "raspberry_qr_vault",
    "esp32_qr_vault",
    "esp32_usb_nip46",
    "smartcard",
    "custom_hardware_wallet",
    "external_nip46",
}
QR_ROUTE_TYPES = {"raspberry_qr_vault", "esp32_qr_vault"}
ROUTE_REPOSITORIES = {
    "raspberry_qr_vault": "raspberry",
    "esp32_qr_vault": "firmware",
    "esp32_usb_nip46": "firmware",
    "smartcard": "smartcard",
    "custom_hardware_wallet": "hardware",
}
ROUTE_TRANSPORTS = {"qr", "usb", "smartcard", "nfc", "nip46_relay", "embedded"}
ROUTE_CUSTODY_MODES = {
    "stateless_session",
    "device_persistent",
    "card_persistent",
    "custom_hardware_persistent",
    "external_signer",
}
ACCESS_SURFACES = {"browser_provider_nip07"}
ACCESS_SURFACE_TRANSPORTS = {"local_service"}
LOCAL_CLIENT_SURFACES = {"browser_extension", "desktop_app", "cli", "sdk", "native_host_test"}
LOCAL_SERVICE_PAIRABLE_OPERATIONS = {
    "select_account_route",
    "validate_signer_request",
    "dispatch_signer_request",
    "verify_signer_response",
}
ROUTE_REVIEW_MODES = {"device_display", "external_review", "external_policy", "display_less"}
POLICY_SUPPORT_MODES = {"manual_only", "scoped_automation", "external"}
POLICY_MODES = {"manual_only", "scoped_automation"}
POLICY_REVIEW_REQUIREMENTS = {
    "connect",
    "delete_event",
    "nip04_decrypt",
    "nip44_decrypt",
    "policy_change",
    "sign_event",
    "switch_relays",
    "unknown_method",
}
POLICY_FORBIDDEN_PERMISSIONS = {
    "companion_authoritative_policy_change",
    "decrypt_without_review",
    "export_secret",
    "local_private_key_storage",
    "trusted_review_claim",
    "wildcard",
}
POLICY_RISK_NAMES = {"decrypt", "delete", "kind:1", "policy_change", "profile", "sign_event", "unknown"}
POLICY_RISK_TIERS = {"device_review", "external_policy", "external_review", "low_scoped", "manual"}
POLICY_CHANGE_ROUTE_TYPES = {"esp32_usb_nip46", "custom_hardware_wallet"}
GRANT_ROUTE_TYPES = {"esp32_usb_nip46", "custom_hardware_wallet"}
GRANT_AUTOMATION_EVENT_KINDS = {1}
POLICY_DECISIONS = {"allow", "deny", "manual_review"}
POLICY_DECISION_REASONS = {
    "decrypt_requires_manual_review",
    "forbidden_permission",
    "grant_expired",
    "grant_rate_limited",
    "grant_revoked",
    "grant_valid",
    "no_matching_grant",
    "policy_manual_only",
    "policy_route_mismatch",
    "unknown_method_requires_manual_review",
}
DECRYPT_METHODS = {"nip04_decrypt", "nip44_decrypt"}
SECRET_FIELD_NAMES = {
    "secret_key",
    "private_key",
    "nsec",
    "mnemonic",
    "seed",
    "passphrase",
    "nip49_ciphertext",
}
SIGNING_STATUS_GATES = [
    "runtime_signing_feature",
    "parser_limits",
    "trusted_review_display",
    "physical_approval_controls",
    "approval_digest_binding",
    "unicode_review_rendering",
    "key_provisioning",
    "source_public_key_proof",
    "secure_boot",
    "flash_encryption",
    "debug_lock",
    "companion_signed_output_verification",
]
ESP32_S3_SCAFFOLD_MISSING_SIGNING_GATES = [
    "runtime_signing_feature",
    "trusted_review_display",
    "physical_approval_controls",
    "unicode_review_rendering",
    "key_provisioning",
    "source_public_key_proof",
    "secure_boot",
    "flash_encryption",
    "debug_lock",
    "companion_signed_output_verification",
]
ESP32_S3_SCAFFOLD_DEVELOPMENT_ACCEPTED_SIGNING_GATES = [
    "parser_limits",
    "trusted_review_display",
    "physical_approval_controls",
    "approval_digest_binding",
]
REVIEW_DETAIL_BODY_LINE_STYLES = {"meta", "normal", "value"}
FEATURE_TARGETS = {"required", "optional", "not_applicable", "forbidden", "research"}
FEATURE_CURRENT_STATUSES = {
    "implemented",
    "partial",
    "planned",
    "hardware_blocked",
    "research",
    "not_applicable",
    "forbidden",
    "disabled_until_gates_pass",
}
FEATURE_SOLUTION_IDS = {
    "raspberry_qr_vault",
    "esp32_qr_vault",
    "esp32_usb_nip46",
    "smartcard",
    "custom_hardware_wallet",
}
FEATURE_IDS = {
    "request_validation_v0",
    "nostr_event_review_universal",
    "review_detail_pages",
    "approval_digest_binding",
    "physical_approval",
    "sign_event_bip340",
    "qr_static_request",
    "qr_animated_request",
    "qr_response",
    "stateless_session_custody",
    "seedqr_session_import",
    "nip19_nsec_session_import",
    "session_source_generation",
    "manual_only_policy",
    "device_display_review",
    "serial_usb_transport",
    "nip46_decrypted_bridge",
    "scoped_policy_automation",
    "persistent_secret_custody",
    "smartcard_apdu",
    "external_review_acknowledgement",
    "secure_boot_hardening",
    "response_verification",
}
CUSTODY_ALLOWED_STORAGE = {
    "tropic01_wrapped_secret_blob",
    "esp32_flash_encrypted_blob",
}
CUSTODY_FORBIDDEN_OUTPUTS = {
    "flash",
    "logs",
    "crash_dumps",
    "usb_reports",
    "companion_descriptors",
    "debug_output",
}
CUSTODY_WIPE_EVENTS = {
    "manual_lock",
    "power_loss",
    "pin_attempt_exhausted",
    "session_timeout",
    "firmware_error",
    "debug_policy_violation",
}
STATELESS_QR_PARITY_FEATURES = {
    "request_validation_v0",
    "nostr_event_review_universal",
    "review_detail_pages",
    "approval_digest_binding",
    "physical_approval",
    "sign_event_bip340",
    "qr_static_request",
    "qr_animated_request",
    "qr_response",
    "stateless_session_custody",
    "seedqr_session_import",
    "nip19_nsec_session_import",
    "session_source_generation",
    "manual_only_policy",
    "device_display_review",
    "response_verification",
}
ROUTE_REFUSAL_SAFETY = {
    "stores_production_secrets": False,
    "contains_secret_material": False,
    "creates_grants": False,
    "dispatches_without_signer": False,
    "requires_shared_request_validation": True,
    "requires_signed_response_verification": True,
}


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def load_required_json(rel: str, errors: list[str]) -> dict | None:
    path = ROOT / rel
    if not path.exists():
        errors.append(f"{rel}: missing required file")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def implementation_limits() -> dict:
    return load_json(LIMIT_PROFILE)


def implementation_limit_values() -> dict:
    return implementation_limits()["limits"]


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
    return hashlib.sha256(canonical_event_serialization(event).encode("utf-8")).hexdigest()


def base64url_json(value: dict) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def animated_qr_checksum(digest: str, index: int, total: int, chunk: str) -> str:
    frame_without_checksum = f"{ANIMATED_QR_PREFIX}{digest}:{index}/{total}:{chunk}"
    return sha256_hex(frame_without_checksum.encode("utf-8"))[:16]


def animated_qr_frames(value: dict, chunk_size: int) -> list[str]:
    decoded = compact_json(value).encode("utf-8")
    digest = sha256_hex(decoded)
    payload = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    chunks = [payload[index : index + chunk_size] for index in range(0, len(payload), chunk_size)]
    frames = []
    for index, chunk in enumerate(chunks, start=1):
        checksum = animated_qr_checksum(digest, index, len(chunks), chunk)
        frames.append(f"{ANIMATED_QR_PREFIX}{digest}:{index}/{len(chunks)}:{chunk}:{checksum}")
    return frames


def json_utf8_size(value: object) -> int:
    return len(compact_json(value).encode("utf-8"))


def utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


def serial_checksum(frame_type: str, payload: str) -> str:
    return hashlib.sha256(f"{frame_type}:{payload}".encode("utf-8")).hexdigest()[:16]


def bech32_polymod(values: list[int]) -> int:
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def decode_lower_bech32(path: str, value: object, errors: list[str]) -> tuple[str, list[int]] | None:
    if not isinstance(value, str):
        errors.append(f"{path}: nsec must be a string")
        return None
    if value != value.lower():
        errors.append(f"{path}: nsec must be canonical lowercase bech32")
        return None
    separator = value.rfind("1")
    if separator <= 0 or separator + 7 > len(value):
        errors.append(f"{path}: nsec bech32 payload is malformed")
        return None
    hrp = value[:separator]
    payload = value[separator + 1:]
    if any(char not in BECH32_CHARSET_REV for char in payload):
        errors.append(f"{path}: nsec bech32 payload contains unsupported characters")
        return None
    data = [BECH32_CHARSET_REV[char] for char in payload]
    if bech32_polymod(bech32_hrp_expand(hrp) + data) != 1:
        errors.append(f"{path}: nsec bech32 checksum is invalid")
        return None
    return hrp, data[:-6]


def convert_5bit_words_to_bytes(path: str, words: list[int], errors: list[str]) -> bytes | None:
    accumulator = 0
    bit_count = 0
    out = bytearray()
    for word in words:
        if word < 0 or word > 31:
            errors.append(f"{path}: nsec bech32 word is out of range")
            return None
        accumulator = (accumulator << 5) | word
        bit_count += 5
        while bit_count >= 8:
            bit_count -= 8
            out.append((accumulator >> bit_count) & 0xFF)
    if bit_count >= 5 or ((accumulator << (8 - bit_count)) & 0xFF) != 0:
        errors.append(f"{path}: nsec bech32 payload has invalid padding")
        return None
    return bytes(out)


def secret_key_from_nsec(path: str, value: object, errors: list[str]) -> str | None:
    decoded = decode_lower_bech32(path, value, errors)
    if decoded is None:
        return None
    hrp, words = decoded
    if hrp != "nsec":
        errors.append(f"{path}: nsec bech32 prefix must be nsec")
        return None
    secret = convert_5bit_words_to_bytes(path, words, errors)
    if secret is None:
        return None
    if len(secret) != 32:
        errors.append(f"{path}: nsec payload must decode to a 32-byte secret key")
        return None
    return secret.hex()


def verify_schnorr(pubkey_hex: str, msg_hex: str, sig_hex: str) -> bool:
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


def xonly_pubkey_from_secret(secret_key_hex: str) -> str | None:
    if not HEX32_RE.fullmatch(secret_key_hex):
        return None
    private_key = secp256k1.PrivateKey(bytes.fromhex(secret_key_hex), raw=True)
    out = secp256k1.ffi.new("unsigned char [32]")
    ok = secp256k1.lib.secp256k1_xonly_pubkey_serialize(
        secp256k1.secp256k1_ctx,
        out,
        private_key.pubkey.xonly_pubkey,
    )
    if ok != 1:
        return None
    return bytes(secp256k1.ffi.buffer(out, 32)).hex()


def check_implementation_limits(errors: list[str]) -> None:
    profile = load_required_json(LIMIT_PROFILE, errors)
    if profile is None:
        return
    if profile.get("format") != "nsealr-implementation-limits-v0":
        errors.append(f"{LIMIT_PROFILE}: format mismatch")
    if profile.get("name") != "nsealr-v0":
        errors.append(f"{LIMIT_PROFILE}: name mismatch")
    limits = profile.get("limits")
    if not isinstance(limits, dict):
        errors.append(f"{LIMIT_PROFILE}: limits must be an object")
        return
    required = {
        "max_request_id_length",
        "max_decoded_request_json_bytes",
        "max_static_qr_decoded_json_bytes",
        "max_animated_qr_decoded_json_bytes",
        "max_animated_qr_frame_payload_chars",
        "max_animated_qr_frame_count",
        "max_serial_frame_bytes",
        "max_nip46_decrypted_message_json_bytes",
        "max_content_utf8_bytes",
        "max_tag_count",
        "max_tag_fields_per_tag",
        "max_tag_field_utf8_bytes",
        "max_total_tag_utf8_bytes",
        "max_safe_integer",
    }
    missing = sorted(required - set(limits))
    if missing:
        errors.append(f"{LIMIT_PROFILE}: missing limits {missing}")
    for field in required & set(limits):
        if not isinstance(limits[field], int) or limits[field] <= 0:
            errors.append(f"{LIMIT_PROFILE}: {field} must be a positive integer")
    if limits.get("max_request_id_length") != 128:
        errors.append(f"{LIMIT_PROFILE}: max_request_id_length must remain 128")
    integer_policy = profile.get("integer_policy")
    if not isinstance(integer_policy, dict):
        errors.append(f"{LIMIT_PROFILE}: integer_policy must be an object")
        return
    for field in ("created_at", "kind"):
        policy = integer_policy.get(field)
        if not isinstance(policy, dict):
            errors.append(f"{LIMIT_PROFILE}: integer_policy.{field} must be an object")
            continue
        expected = {
            "type": "integer",
            "minimum": 0,
            "maximum": limits.get("max_safe_integer"),
        }
        if policy != expected:
            errors.append(f"{LIMIT_PROFILE}: integer_policy.{field} mismatch")


def check_safe_integer(path: Path, field: str, value: object, errors: list[str], limits: dict) -> None:
    if type(value) is not int:
        errors.append(f"{path}: event_template {field} must be a non-negative safe integer")
        return
    if value < 0:
        errors.append(f"{path}: event_template {field} must be a non-negative safe integer")
    if value > limits["max_safe_integer"]:
        errors.append(f"{path}: event_template {field} exceeds max_safe_integer")


def check_signed_event_safe_integer(path: Path, field: str, value: object, errors: list[str], limits: dict) -> None:
    if type(value) is not int:
        errors.append(f"{path}: signed event {field} must be a non-negative safe integer")
        return
    if value < 0:
        errors.append(f"{path}: signed event {field} must be a non-negative safe integer")
    if value > limits["max_safe_integer"]:
        errors.append(f"{path}: signed event {field} exceeds max_safe_integer")


def check_request_shape(path: Path, value: object, errors: list[str]) -> None:
    limits = implementation_limit_values()
    if not isinstance(value, dict):
        errors.append(f"{path}: request must be an object")
        return
    if json_utf8_size(value) > limits["max_decoded_request_json_bytes"]:
        errors.append(f"{path}: decoded request JSON exceeds max_decoded_request_json_bytes")

    if value.get("version") != 1:
        errors.append(f"{path}: version must be 1")
    request_id = value.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        errors.append(f"{path}: request_id must match the v0 request id profile")
    elif len(request_id) > limits["max_request_id_length"]:
        errors.append(f"{path}: request_id exceeds max_request_id_length")
    method = value.get("method")
    if method not in DEVICE_METHODS:
        errors.append(f"{path}: unsupported method {method!r}")
        return
    allowed_top_level = {"version", "request_id", "method"}
    if method == "sign_event":
        allowed_top_level.add("params")
    unknown_top_level = sorted(set(value) - allowed_top_level)
    if unknown_top_level:
        errors.append(f"{path}: unknown top-level fields: {unknown_top_level}")
    if method == "get_capabilities" and "params" in value:
        errors.append(f"{path}: get_capabilities must not include params in v0")
    if method == "get_signing_status" and "params" in value:
        errors.append(f"{path}: get_signing_status must not include params in v0")
    if method == "get_public_key" and "params" in value:
        errors.append(f"{path}: get_public_key must not include params in v0")
    if method == "sign_event":
        params = value.get("params")
        if not isinstance(params, dict):
            errors.append(f"{path}: sign_event requires params")
            return
        unknown_params = sorted(set(params) - {"event_template"})
        if unknown_params:
            errors.append(f"{path}: sign_event params contain unknown fields: {unknown_params}")
        template = params.get("event_template")
        if not isinstance(template, dict):
            errors.append(f"{path}: event_template must be an object")
            return
        forbidden = {"id", "pubkey", "sig"} & set(template)
        if forbidden:
            errors.append(f"{path}: event_template contains forbidden fields: {sorted(forbidden)}")
        required_fields = {"created_at", "kind", "tags", "content"}
        unknown_template_fields = sorted(set(template) - required_fields - {"id", "pubkey", "sig"})
        if unknown_template_fields:
            errors.append(f"{path}: event_template contains unknown fields: {unknown_template_fields}")
        for field in sorted(required_fields):
            if field not in template:
                errors.append(f"{path}: event_template missing {field}")
        if "created_at" in template:
            check_safe_integer(path, "created_at", template["created_at"], errors, limits)
        if "kind" in template:
            check_safe_integer(path, "kind", template["kind"], errors, limits)
        if "tags" in template:
            tags = template["tags"]
            if not isinstance(tags, list):
                errors.append(f"{path}: event_template tags must be an array")
            else:
                if len(tags) > limits["max_tag_count"]:
                    errors.append(f"{path}: event_template tags exceeds max_tag_count")
                total_tag_bytes = 0
                for tag_index, tag in enumerate(tags):
                    if not isinstance(tag, list):
                        errors.append(f"{path}: event_template tags[{tag_index}] must be an array")
                        continue
                    if len(tag) > limits["max_tag_fields_per_tag"]:
                        errors.append(f"{path}: event_template tags[{tag_index}] exceeds max_tag_fields_per_tag")
                    for field_index, item in enumerate(tag):
                        if not isinstance(item, str):
                            errors.append(f"{path}: event_template tags[{tag_index}][{field_index}] must be a string")
                            continue
                        item_bytes = utf8_size(item)
                        total_tag_bytes += item_bytes
                        if item_bytes > limits["max_tag_field_utf8_bytes"]:
                            errors.append(f"{path}: event_template tag field exceeds max_tag_field_utf8_bytes")
                if total_tag_bytes > limits["max_total_tag_utf8_bytes"]:
                    errors.append(f"{path}: event_template tags exceed max_total_tag_utf8_bytes")
        if "content" in template:
            content = template["content"]
            if not isinstance(content, str):
                errors.append(f"{path}: event_template content must be a string")
            elif utf8_size(content) > limits["max_content_utf8_bytes"]:
                errors.append(f"{path}: event_template content exceeds max_content_utf8_bytes")


def request_shape_errors(path: Path, value: dict) -> list[str]:
    errors: list[str] = []
    check_request_shape(path, value, errors)
    return errors


def check_response_shape(path: Path, value: dict, errors: list[str]) -> None:
    limits = implementation_limit_values()
    if not isinstance(value, dict):
        errors.append(f"{path}: response must be an object")
        return
    allowed_top_level = {"version", "request_id", "ok"}
    if value.get("ok") is True:
        allowed_top_level.add("result")
    elif value.get("ok") is False:
        allowed_top_level.add("error")
    unknown_top_level = sorted(set(value) - allowed_top_level)
    if unknown_top_level:
        errors.append(f"{path}: unknown top-level response fields: {unknown_top_level}")
    if value.get("version") != 1:
        errors.append(f"{path}: version must be 1")
    request_id = value.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        errors.append(f"{path}: request_id is invalid")
    elif len(request_id) > limits["max_request_id_length"]:
        errors.append(f"{path}: request_id exceeds max_request_id_length")
    if value.get("ok") is True:
        if "error" in value:
            errors.append(f"{path}: successful response must not include error")
        result = value.get("result")
        if not isinstance(result, dict):
            errors.append(f"{path}: successful response requires result")
            return
        result_fields = {"public_key", "capabilities", "signing_status", "event"} & set(result)
        unknown_result_fields = sorted(set(result) - {"public_key", "capabilities", "signing_status", "event"})
        if unknown_result_fields:
            errors.append(f"{path}: successful response result has unknown fields: {unknown_result_fields}")
        if len(result_fields) != 1:
            errors.append(f"{path}: successful response result must contain exactly one result field")
            return
        if "public_key" in result and (not isinstance(result["public_key"], str) or not HEX32_RE.fullmatch(result["public_key"])):
            errors.append(f"{path}: public_key must be 32-byte lowercase hex")
        if "capabilities" in result:
            capabilities = result["capabilities"]
            if not isinstance(capabilities, dict):
                errors.append(f"{path}: capabilities must be an object")
                return
            for field in ("device", "protocols", "methods", "transports"):
                if field not in capabilities:
                    errors.append(f"{path}: capabilities missing {field}")
            if "signing_enabled" in capabilities and not isinstance(capabilities["signing_enabled"], bool):
                errors.append(f"{path}: signing_enabled must be boolean")
            if "requires_physical_approval" in capabilities and not isinstance(capabilities["requires_physical_approval"], bool):
                errors.append(f"{path}: requires_physical_approval must be boolean")
            methods = capabilities.get("methods")
            if isinstance(methods, list):
                unknown_methods = sorted(set(methods) - DEVICE_METHODS)
                if unknown_methods:
                    errors.append(f"{path}: capabilities declare unknown methods: {unknown_methods}")
        if "signing_status" in result:
            signing_status = result["signing_status"]
            if not isinstance(signing_status, dict):
                errors.append(f"{path}: signing_status must be an object")
                return
            unknown_status_fields = sorted(set(signing_status) - {"signing_enabled", "missing_gates", "development_accepted_gates"})
            if unknown_status_fields:
                errors.append(f"{path}: signing_status has unknown fields: {unknown_status_fields}")
            if not isinstance(signing_status.get("signing_enabled"), bool):
                errors.append(f"{path}: signing_status.signing_enabled must be boolean")
            missing_gates = signing_status.get("missing_gates")
            if not isinstance(missing_gates, list):
                errors.append(f"{path}: signing_status.missing_gates must be an array")
            else:
                seen_missing_gates: set[str] = set()
                for gate in missing_gates:
                    if gate not in SIGNING_STATUS_GATES:
                        errors.append(f"{path}: signing_status.missing_gates contains unknown gate {gate!r}")
                    elif gate in seen_missing_gates:
                        errors.append(f"{path}: duplicate signing_status missing gate: {gate}")
                    else:
                        seen_missing_gates.add(gate)
                if signing_status.get("signing_enabled") is True and missing_gates:
                    errors.append(f"{path}: signing_status signing_enabled true requires empty missing_gates")
                if signing_status.get("signing_enabled") is False and not missing_gates:
                    errors.append(f"{path}: signing_status signing_enabled false requires at least one missing gate")
            accepted_gates = signing_status.get("development_accepted_gates")
            if not isinstance(accepted_gates, list):
                errors.append(f"{path}: signing_status.development_accepted_gates must be an array")
            else:
                seen_accepted_gates: set[str] = set()
                for gate in accepted_gates:
                    if gate not in SIGNING_STATUS_GATES:
                        errors.append(f"{path}: signing_status.development_accepted_gates contains unknown gate {gate!r}")
                    elif gate in seen_accepted_gates:
                        errors.append(f"{path}: duplicate signing_status development_accepted gate: {gate}")
                    else:
                        seen_accepted_gates.add(gate)
        if "event" in result:
            event = result["event"]
            if not isinstance(event, dict):
                errors.append(f"{path}: signed event must be an object")
                return
            unknown_event_fields = sorted(set(event) - {"id", "pubkey", "created_at", "kind", "tags", "content", "sig"})
            if unknown_event_fields:
                errors.append(f"{path}: signed event has unknown fields: {unknown_event_fields}")
            for field in ("id", "pubkey", "created_at", "kind", "tags", "content", "sig"):
                if field not in event:
                    errors.append(f"{path}: signed event missing {field}")
            if "id" in event and (not isinstance(event["id"], str) or not HEX32_RE.fullmatch(event["id"])):
                errors.append(f"{path}: event id must be 32-byte lowercase hex")
            if "pubkey" in event and (not isinstance(event["pubkey"], str) or not HEX32_RE.fullmatch(event["pubkey"])):
                errors.append(f"{path}: pubkey must be 32-byte lowercase hex")
            if "created_at" in event:
                check_signed_event_safe_integer(path, "created_at", event["created_at"], errors, limits)
            if "kind" in event:
                check_signed_event_safe_integer(path, "kind", event["kind"], errors, limits)
            if "tags" in event:
                tags = event["tags"]
                if not isinstance(tags, list):
                    errors.append(f"{path}: signed event tags must be an array")
                else:
                    if len(tags) > limits["max_tag_count"]:
                        errors.append(f"{path}: signed event tags exceeds max_tag_count")
                    total_tag_bytes = 0
                    for tag_index, tag in enumerate(tags):
                        if not isinstance(tag, list):
                            errors.append(f"{path}: signed event tags[{tag_index}] must be an array")
                            continue
                        if len(tag) > limits["max_tag_fields_per_tag"]:
                            errors.append(f"{path}: signed event tags[{tag_index}] exceeds max_tag_fields_per_tag")
                        for field_index, item in enumerate(tag):
                            if not isinstance(item, str):
                                errors.append(f"{path}: signed event tags[{tag_index}][{field_index}] must be a string")
                                continue
                            item_bytes = utf8_size(item)
                            total_tag_bytes += item_bytes
                            if item_bytes > limits["max_tag_field_utf8_bytes"]:
                                errors.append(f"{path}: signed event tag field exceeds max_tag_field_utf8_bytes")
                    if total_tag_bytes > limits["max_total_tag_utf8_bytes"]:
                        errors.append(f"{path}: signed event tags exceed max_total_tag_utf8_bytes")
            if "content" in event:
                content = event["content"]
                if not isinstance(content, str):
                    errors.append(f"{path}: signed event content must be a string")
                elif utf8_size(content) > limits["max_content_utf8_bytes"]:
                    errors.append(f"{path}: signed event content exceeds max_content_utf8_bytes")
            if "sig" in event and (not isinstance(event["sig"], str) or not HEX64_RE.fullmatch(event["sig"])):
                errors.append(f"{path}: signature must be 64-byte lowercase hex")
    elif value.get("ok") is False:
        if "result" in value:
            errors.append(f"{path}: error response must not include result")
        error = value.get("error")
        if not isinstance(error, dict):
            errors.append(f"{path}: error response requires error object")
            return
        for field in ("code", "message", "retryable"):
            if field not in error:
                errors.append(f"{path}: error missing {field}")
        if "code" in error and not isinstance(error["code"], str):
            errors.append(f"{path}: error code must be a string")
        if "message" in error and not isinstance(error["message"], str):
            errors.append(f"{path}: error message must be a string")
        if "retryable" in error and not isinstance(error["retryable"], bool):
            errors.append(f"{path}: error retryable must be boolean")
    else:
        errors.append(f"{path}: ok must be true or false")


def expected_review(template: dict) -> dict:
    author_pubkey = load_required_json("vectors/keys/test-key-1.json", [])["public_key"]
    content = template["content"]
    tags = template["tags"]
    return {
        "kind": template["kind"],
        "created_at": template["created_at"],
        "author_pubkey": author_pubkey,
        "content": content,
        "content_utf8_bytes": len(content.encode("utf-8")),
        "tag_count": len(tags),
        "tags": tags,
    }


def review_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "review").glob("*.json"))


def check_review_vector(rel: str, errors: list[str]) -> None:
    vector = load_required_json(f"vectors/review/{rel}.json", errors)
    if vector is None:
        return
    request = vector.get("request")
    if not isinstance(request, dict):
        errors.append(f"vectors/review/{rel}.json: request must be an object")
        return
    check_request_shape(Path(f"vectors/review/{rel}.json"), request, errors)
    if request.get("method") != "sign_event":
        errors.append(f"vectors/review/{rel}.json: request method must be sign_event")
        return
    expected = expected_review(request["params"]["event_template"])
    if vector.get("name") != rel:
        errors.append(f"vectors/review/{rel}.json: name mismatch")
    if vector.get("request") != request:
        errors.append(f"vectors/review/{rel}.json: request mismatch")
    if vector.get("review") != expected:
        errors.append(f"vectors/review/{rel}.json: review mismatch")


def expected_review_pages(review: dict) -> list[dict]:
    return [
        {
            "title": "Event",
            "lines": [
                f"Kind {review['kind']}",
                f"Created {review['created_at']}",
                "Author",
                str(review["author_pubkey"]),
            ],
            "action": "next",
        },
        {
            "title": "Content",
            "lines": [str(review["content"])],
            "action": "next",
        },
        {
            "title": "Tags",
            "lines": expected_tag_page_lines(review),
            "action": "next",
        },
        {
            "title": "Decision",
            "lines": ["Approve signing only if all pages match."],
            "action": "approve_or_reject",
        },
    ]


def expected_tag_page_lines(review: dict) -> list[str]:
    tag_count = review["tag_count"]
    if tag_count == 0:
        return ["No tags"]
    lines = []
    for index, tag in enumerate(review["tags"], start=1):
        lines.append(f"Tag {index}/{tag_count}")
        if tag:
            lines.extend(str(item) for item in tag)
        else:
            lines.append("empty tag")
    return lines


def approval_digest_for_screen_review(request: dict, review: dict, pages: list[dict]) -> str:
    payload = {
        "version": request["version"],
        "method": request["method"],
        "request_id": request["request_id"],
        "event_template": request["params"]["event_template"],
        "review": review,
        "pages": pages,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def expected_screen_review(request: dict) -> dict:
    review = expected_review(request["params"]["event_template"])
    pages = expected_review_pages(review)
    return {
        "format": "screen-pages",
        "request_id": request["request_id"],
        "approval_digest": approval_digest_for_screen_review(request, review, pages),
        "pages": pages,
    }


def review_screen_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "review-screens").glob("*.json"))


def review_display_frame_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "review-display-frames").glob("*.json"))


def review_detail_page_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "review-detail-pages").glob("*.json"))


def review_transcript_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "review-transcripts").glob("*.json"))


def nip46_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46").glob("*.json"))


def nip46_policy_file_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-policy-files").glob("*.json"))


def nip46_connection_uri_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-connection-uris").glob("*.json"))


def nip46_connection_token_response_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-connection-token-responses").glob("*.json"))


def nip46_relay_event_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-relay-events").glob("*.json"))


def nip46_relay_step_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-relay-steps").glob("*.json"))


def nip46_auth_challenge_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-auth-challenges").glob("*.json"))


def nip46_session_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-sessions").glob("*.json"))


def nip46_session_gate_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-session-gates").glob("*.json"))


def nip46_session_active_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip46-sessions-active").glob("*.json"))


def seedqr_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "seedqr").glob("*.json"))


def nip19_nsec_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "nip19").glob("*.json"))


def session_import_review_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "session-import-reviews").glob("*.json"))


def source_public_key_proof_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "source-public-key-proofs").glob("*.json"))


def session_source_backup_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "session-source-backups").glob("*.json"))


def smartcard_apdu_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "smartcard").glob("*.json"))


def invalid_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "invalid").glob("*.json"))


def account_descriptor_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "accounts").glob("*.json"))


def policy_profile_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "policies").glob("*.json"))


def grant_descriptor_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "grants").glob("*.json"))


def policy_decision_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "policy-decisions").glob("*.json"))


def policy_change_review_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "policy-changes").glob("*.json"))


def route_selection_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "route-selections").glob("*.json"))


def route_refusal_contract_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "route-refusals").glob("*.json"))


def access_surface_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "access-surfaces").glob("*.json"))


def feature_matrix_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "features").glob("*.json"))


def custody_contract_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "custody").glob("*.json"))


def device_security_profile_vector_names() -> list[str]:
    return sorted(path.stem for path in (ROOT / "vectors" / "devices").glob("*security-profile-*.json"))


def secret_field_paths(value: object, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in SECRET_FIELD_NAMES:
                paths.append(path)
            paths.extend(secret_field_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(secret_field_paths(child, path))
    return paths


def check_no_secret_fields(path: str, value: object, errors: list[str]) -> None:
    for secret_path in secret_field_paths(value):
        errors.append(f"{path}: must not contain secret field {secret_path}")


def check_string_id(path: str, field: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
        errors.append(f"{path}: {field} must be a stable string id")


def check_policy_id(path: str, field: str, value: object, errors: list[str]) -> bool:
    if not isinstance(value, str) or not POLICY_ID_RE.fullmatch(value):
        errors.append(f"{path}: {field} must be a policy-* stable string id")
        return False
    return True


def check_grant_id(path: str, field: str, value: object, errors: list[str]) -> bool:
    if not isinstance(value, str) or not GRANT_ID_RE.fullmatch(value):
        errors.append(f"{path}: {field} must be a grant-* stable string id")
        return False
    return True


def check_proposal_id(path: str, field: str, value: object, errors: list[str]) -> bool:
    if not isinstance(value, str) or not PROPOSAL_ID_RE.fullmatch(value):
        errors.append(f"{path}: {field} must be a proposal-* stable string id")
        return False
    return True


def check_known_fields(path: str, label: str, value: dict, allowed: set[str], errors: list[str]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        errors.append(f"{path}: {label} has unknown fields {unknown}")


def client_id_for_identity(client: dict) -> str:
    payload = {
        "surface": client.get("surface"),
        "origin": client.get("origin"),
        "app_name": client.get("app_name", ""),
        "instance_id": client.get("instance_id", ""),
    }
    return sha256_hex(compact_json(payload).encode("utf-8"))


def is_supported_local_client_origin(origin: str) -> bool:
    if origin.startswith(("extension:", "app:", "cli:", "sdk:")):
        return True
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return False
    if parsed.scheme == "https":
        return True
    return parsed.hostname in {"localhost", "127.0.0.1"}


def check_local_client_identity(path: str, value: object, errors: list[str]) -> dict | None:
    if not isinstance(value, dict):
        errors.append(f"{path}: client must be an object")
        return None
    unknown = sorted(set(value) - {"surface", "origin", "app_name", "instance_id"})
    if unknown:
        errors.append(f"{path}: client contains unknown fields {unknown}")
    if value.get("surface") not in LOCAL_CLIENT_SURFACES:
        errors.append(f"{path}: client.surface is unsupported")
    origin = value.get("origin")
    if not isinstance(origin, str) or not origin or len(origin) > 256:
        errors.append(f"{path}: client.origin is invalid")
    elif not is_supported_local_client_origin(origin):
        errors.append(f"{path}: client.origin scheme is unsupported")
    if "app_name" in value and (not isinstance(value["app_name"], str) or len(value["app_name"]) > 80):
        errors.append(f"{path}: client.app_name is invalid")
    if "instance_id" in value and (
        not isinstance(value["instance_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9._:@+-]{1,128}", value["instance_id"])
    ):
        errors.append(f"{path}: client.instance_id is invalid")
    return value


def check_local_client_grant(path: str, grant: object, client: dict, errors: list[str]) -> None:
    if not isinstance(grant, dict):
        errors.append(f"{path}: client_grant must be an object")
        return
    unknown = sorted(set(grant) - {"client_id", "origin", "surface", "allowed_operations", "pairing_digest", "approved_at", "revoked", "expires_at"})
    if unknown:
        errors.append(f"{path}: client_grant contains unknown fields {unknown}")
    if grant.get("client_id") != client_id_for_identity(client):
        errors.append(f"{path}: client_grant client_id mismatch")
    if grant.get("origin") != client.get("origin"):
        errors.append(f"{path}: client_grant origin mismatch")
    if grant.get("surface") != client.get("surface"):
        errors.append(f"{path}: client_grant surface mismatch")
    operations = grant.get("allowed_operations")
    if not isinstance(operations, list) or not all(isinstance(operation, str) for operation in operations):
        errors.append(f"{path}: client_grant.allowed_operations must be a string list")
    else:
        unknown_operations = sorted(set(operations) - LOCAL_SERVICE_PAIRABLE_OPERATIONS)
        if unknown_operations:
            errors.append(f"{path}: client_grant has unsupported operations {unknown_operations}")
        if len(set(operations)) != len(operations):
            errors.append(f"{path}: client_grant allowed_operations contains duplicates")
    approved_at = grant.get("approved_at")
    expires_at = grant.get("expires_at")
    if type(approved_at) is not int or approved_at < 0:
        errors.append(f"{path}: client_grant.approved_at must be a non-negative integer")
    if expires_at is not None:
        if type(expires_at) is not int or expires_at <= 0:
            errors.append(f"{path}: client_grant.expires_at must be a positive integer")
        elif type(approved_at) is int and expires_at <= approved_at:
            errors.append(f"{path}: client_grant.expires_at must be greater than approved_at")


def check_permission_shape(path: str, permission: object, errors: list[str], *, grant_permission: bool = False) -> None:
    if not isinstance(permission, dict):
        errors.append(f"{path}: permission must be an object")
        return
    method = permission.get("method")
    if method == "*":
        errors.append(f"{path}: grant permission must not use wildcards")
    if not isinstance(method, str) or not method:
        errors.append(f"{path}: permission.method must be a non-empty string")
    if permission.get("parameter") == "*":
        errors.append(f"{path}: grant permission must not use wildcards")
    if grant_permission and method in DECRYPT_METHODS:
        errors.append(f"{path}: decrypt grant permissions require manual review")
    if grant_permission and method != "sign_event":
        errors.append(f"{path}: v0 grants support only sign_event kind 1 automation")
    if method == "sign_event":
        parameter = permission.get("parameter")
        event_kind = permission.get("event_kind")
        if not isinstance(parameter, str) or not parameter.isdigit():
            errors.append(f"{path}: sign_event permission.parameter must be a decimal event kind")
        elif int(parameter) > MAX_SAFE_INTEGER:
            errors.append(f"{path}: sign_event permission.parameter exceeds max_safe_integer")
        if type(event_kind) is not int or event_kind < 0 or event_kind > MAX_SAFE_INTEGER:
            errors.append(f"{path}: sign_event permission.event_kind must be a non-negative safe integer")
        elif isinstance(parameter, str) and parameter.isdigit() and int(parameter) <= MAX_SAFE_INTEGER and int(parameter) != event_kind:
            errors.append(f"{path}: sign_event permission parameter/event_kind mismatch")
        if grant_permission and (parameter != "1" or event_kind not in GRANT_AUTOMATION_EVENT_KINDS):
            errors.append(f"{path}: v0 grants support only sign_event kind 1 automation")
    unknown = sorted(set(permission) - {"method", "parameter", "event_kind"})
    if unknown:
        errors.append(f"{path}: permission has unknown fields {unknown}")


def check_account_descriptor_shape(path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: account descriptor must be an object")
        return
    check_no_secret_fields(path, value, errors)
    check_known_fields(
        path,
        "account descriptor",
        value,
        {"format", "account_id", "label", "public_key", "signer_route", "recovery", "capabilities", "policy_profile_id"},
        errors,
    )
    if value.get("format") != "nsealr-account-descriptor-v0":
        errors.append(f"{path}: format mismatch")
    check_string_id(path, "account_id", value.get("account_id"), errors)
    if not isinstance(value.get("label"), str) or not value["label"]:
        errors.append(f"{path}: label must be a non-empty string")
    if not isinstance(value.get("public_key"), str) or not HEX32_RE.fullmatch(value["public_key"]):
        errors.append(f"{path}: public_key must be 32-byte lowercase hex")

    route = value.get("signer_route")
    if not isinstance(route, dict):
        errors.append(f"{path}: signer_route must be an object")
        return
    check_known_fields(
        path,
        "signer_route",
        route,
        {"type", "repository", "transport", "custody", "trusted_review", "policy_support"},
        errors,
    )
    route_type = route.get("type")
    if route_type not in ROUTE_TYPES:
        errors.append(f"{path}: signer_route.type is unknown")
    expected_repository = ROUTE_REPOSITORIES.get(route_type)
    if expected_repository is not None and route.get("repository") != expected_repository:
        errors.append(f"{path}: signer_route.repository must be {expected_repository}")
    if expected_repository is None and "repository" in route:
        errors.append(f"{path}: external signer routes must not claim a nSealr repository")
    if route.get("transport") not in ROUTE_TRANSPORTS:
        errors.append(f"{path}: signer_route.transport is unknown")
    if route.get("custody") not in ROUTE_CUSTODY_MODES:
        errors.append(f"{path}: signer_route.custody is unknown")
    if route.get("trusted_review") not in ROUTE_REVIEW_MODES:
        errors.append(f"{path}: signer_route.trusted_review is unknown")
    if route.get("policy_support") not in POLICY_SUPPORT_MODES:
        errors.append(f"{path}: signer_route.policy_support is unknown")

    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append(f"{path}: capabilities must be an object")
        return
    check_known_fields(
        path,
        "capabilities",
        capabilities,
        {"methods", "physical_review", "physical_approval", "persistent_grants"},
        errors,
    )
    methods = capabilities.get("methods")
    if not isinstance(methods, list) or not all(isinstance(method, str) for method in methods):
        errors.append(f"{path}: capabilities.methods must be an array of strings")
    elif unknown_methods := sorted(set(methods) - DEVICE_METHODS):
        errors.append(f"{path}: capabilities.methods contain unknown methods {unknown_methods}")
    for field in ("physical_review", "physical_approval", "persistent_grants"):
        if not isinstance(capabilities.get(field), bool):
            errors.append(f"{path}: capabilities.{field} must be boolean")

    if route_type in QR_ROUTE_TYPES:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
        if "tropic01" in serialized:
            errors.append(f"{path}: stateless QR vault descriptors must not reference TROPIC01")
        if route.get("transport") != "qr":
            errors.append(f"{path}: stateless QR vault routes must use qr transport")
        if route.get("custody") != "stateless_session":
            errors.append(f"{path}: stateless QR vault routes must use stateless_session custody")
        if route.get("policy_support") != "manual_only":
            errors.append(f"{path}: stateless QR vault routes must use manual_only policy support")
        if capabilities.get("persistent_grants") is not False:
            errors.append(f"{path}: stateless QR vault routes must not support persistent grants")
    elif route_type == "esp32_usb_nip46":
        if route.get("transport") != "usb":
            errors.append(f"{path}: ESP32 USB/NIP-46 routes must use usb transport")
        if route.get("custody") != "device_persistent":
            errors.append(f"{path}: ESP32 USB/NIP-46 routes must use device_persistent custody")
        if route.get("trusted_review") != "device_display":
            errors.append(f"{path}: ESP32 USB/NIP-46 routes must use device_display review")
        if route.get("policy_support") != "scoped_automation":
            errors.append(f"{path}: ESP32 USB/NIP-46 routes must use scoped_automation policy support")
        if capabilities.get("physical_review") is not True or capabilities.get("physical_approval") is not True:
            errors.append(f"{path}: ESP32 USB/NIP-46 routes require physical review and approval")
        if capabilities.get("persistent_grants") is not True:
            errors.append(f"{path}: ESP32 USB/NIP-46 routes require persistent grant support")
    elif route_type == "smartcard":
        if route.get("transport") != "smartcard":
            errors.append(f"{path}: smartcard routes must use smartcard transport")
        if route.get("custody") != "card_persistent":
            errors.append(f"{path}: smartcard routes must use card_persistent custody")
        if route.get("trusted_review") != "display_less":
            errors.append(f"{path}: smartcard routes must remain display_less")
        if route.get("policy_support") != "manual_only":
            errors.append(f"{path}: display-less smartcard routes must use manual_only policy support")
        if capabilities.get("physical_review") is not False or capabilities.get("physical_approval") is not False:
            errors.append(f"{path}: display-less smartcard routes must not claim physical review or approval")
        if capabilities.get("persistent_grants") is not False:
            errors.append(f"{path}: display-less smartcard routes must not support persistent grants")
    elif route_type == "custom_hardware_wallet":
        if route.get("transport") != "usb":
            errors.append(f"{path}: custom hardware-wallet routes must use usb transport in v0")
        if route.get("custody") != "custom_hardware_persistent":
            errors.append(f"{path}: custom hardware-wallet routes must use custom_hardware_persistent custody")
        if route.get("trusted_review") != "device_display":
            errors.append(f"{path}: custom hardware-wallet routes must use device_display review")
        if route.get("policy_support") != "scoped_automation":
            errors.append(f"{path}: custom hardware-wallet routes must use scoped_automation policy support")
        if capabilities.get("physical_review") is not True or capabilities.get("physical_approval") is not True:
            errors.append(f"{path}: custom hardware-wallet routes require physical review and approval")
        if capabilities.get("persistent_grants") is not True:
            errors.append(f"{path}: custom hardware-wallet routes require persistent grant support")
    elif route_type == "external_nip46":
        if route.get("transport") != "nip46_relay":
            errors.append(f"{path}: external NIP-46 routes must use nip46_relay transport")
        if route.get("custody") != "external_signer":
            errors.append(f"{path}: external NIP-46 routes must use external_signer custody")
        if route.get("trusted_review") != "external_policy":
            errors.append(f"{path}: external NIP-46 routes must use external_policy review")
        if route.get("policy_support") != "external":
            errors.append(f"{path}: external NIP-46 routes must use external policy support")
        if capabilities.get("physical_review") is not False or capabilities.get("physical_approval") is not False:
            errors.append(f"{path}: external NIP-46 routes must not claim nSealr physical review or approval")
        if capabilities.get("persistent_grants") is not False:
            errors.append(f"{path}: external NIP-46 routes must not claim nSealr persistent grants")

    recovery = value.get("recovery")
    if not isinstance(recovery, dict):
        errors.append(f"{path}: recovery must be an object")
        return
    recovery_type = recovery.get("type")
    if recovery_type == "nip06":
        check_known_fields(
            path,
            "NIP-06 recovery",
            recovery,
            {"type", "path", "account", "source_vector", "source_fingerprint"},
            errors,
        )
        if not isinstance(recovery.get("path"), str) or not recovery["path"].startswith("m/44'/1237'/"):
            errors.append(f"{path}: NIP-06 recovery path must use the Nostr derivation prefix")
        if type(recovery.get("account")) is not int or recovery["account"] < 0:
            errors.append(f"{path}: NIP-06 recovery account must be a non-negative integer")
        source_vector = recovery.get("source_vector")
        if not isinstance(source_vector, str):
            errors.append(f"{path}: NIP-06 recovery source_vector must be a string")
        elif not (ROOT / source_vector).exists():
            errors.append(f"{path}: NIP-06 recovery source_vector is missing")
        else:
            source = load_json(source_vector)
            if source.get("public_key") != value.get("public_key"):
                errors.append(f"{path}: NIP-06 recovery source_vector public_key mismatch")
            expected_fingerprint = session_key_source_fingerprint_for_vector(path, "bip39_seed", source, errors)
            source_fingerprint = recovery.get("source_fingerprint")
            if not isinstance(source_fingerprint, str) or not HEX8_RE.fullmatch(source_fingerprint):
                errors.append(f"{path}: NIP-06 recovery source_fingerprint must be 8-byte lowercase hex")
            elif expected_fingerprint is not None and source_fingerprint != expected_fingerprint:
                errors.append(f"{path}: NIP-06 recovery source_fingerprint mismatch")
    elif recovery_type == "device_slot":
        check_known_fields(path, "device_slot recovery", recovery, {"type", "slot_id", "backup_required"}, errors)
        if not isinstance(recovery.get("slot_id"), str) or not recovery["slot_id"]:
            errors.append(f"{path}: device_slot recovery requires slot_id")
        if not isinstance(recovery.get("backup_required"), bool):
            errors.append(f"{path}: device_slot recovery requires backup_required boolean")
    elif recovery_type == "card_slot":
        check_known_fields(path, "card_slot recovery", recovery, {"type", "card_id", "slot_id", "backup_required"}, errors)
        if not isinstance(recovery.get("card_id"), str) or not recovery["card_id"]:
            errors.append(f"{path}: card_slot recovery requires card_id")
        if not isinstance(recovery.get("slot_id"), str) or not recovery["slot_id"]:
            errors.append(f"{path}: card_slot recovery requires slot_id")
        if not isinstance(recovery.get("backup_required"), bool):
            errors.append(f"{path}: card_slot recovery requires backup_required boolean")
    elif recovery_type == "hardware_wallet_slot":
        check_known_fields(
            path,
            "hardware_wallet_slot recovery",
            recovery,
            {"type", "device_id", "slot_id", "backup_required"},
            errors,
        )
        if not isinstance(recovery.get("device_id"), str) or not recovery["device_id"]:
            errors.append(f"{path}: hardware_wallet_slot recovery requires device_id")
        if not isinstance(recovery.get("slot_id"), str) or not recovery["slot_id"]:
            errors.append(f"{path}: hardware_wallet_slot recovery requires slot_id")
        if not isinstance(recovery.get("backup_required"), bool):
            errors.append(f"{path}: hardware_wallet_slot recovery requires backup_required boolean")
    elif recovery_type == "external_signer":
        check_known_fields(path, "external_signer recovery", recovery, {"type", "external_signer_id"}, errors)
        if not isinstance(recovery.get("external_signer_id"), str) or not recovery["external_signer_id"]:
            errors.append(f"{path}: external_signer recovery requires external_signer_id")
    else:
        errors.append(f"{path}: recovery.type is unknown")

    policy_profile_id = value.get("policy_profile_id")
    if not check_policy_id(path, "policy_profile_id", policy_profile_id, errors):
        return
    if not (ROOT / "vectors" / "policies" / f"{policy_profile_id.removeprefix('policy-')}.json").exists():
        errors.append(f"{path}: policy_profile_id target is missing")
    else:
        policy = load_json(f"vectors/policies/{policy_profile_id.removeprefix('policy-')}.json")
        if isinstance(route_type, str) and route_type not in policy.get("route_types", []):
            errors.append(f"{path}: policy_profile_id does not include signer route type {route_type}")


def check_policy_profile_shape(path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: policy profile must be an object")
        return
    check_no_secret_fields(path, value, errors)
    check_known_fields(
        path,
        "policy profile",
        value,
        {
            "format",
            "policy_id",
            "label",
            "route_types",
            "mode",
            "grants_allowed",
            "manual_review_required",
            "forbidden_permissions",
            "grant_constraints",
            "risk_tiers",
        },
        errors,
    )
    if value.get("format") != "nsealr-policy-profile-v0":
        errors.append(f"{path}: format mismatch")
    policy_id = value.get("policy_id")
    check_policy_id(path, "policy_id", policy_id, errors)
    if not isinstance(value.get("label"), str) or not value["label"]:
        errors.append(f"{path}: label must be a non-empty string")
    route_types = value.get("route_types")
    if not isinstance(route_types, list) or not route_types:
        errors.append(f"{path}: route_types must be a non-empty array")
        route_types = []
    elif unknown_routes := sorted(set(route_types) - ROUTE_TYPES):
        errors.append(f"{path}: route_types contain unknown routes {unknown_routes}")
    mode = value.get("mode")
    if mode not in POLICY_MODES:
        errors.append(f"{path}: mode is unknown")
    if not isinstance(value.get("grants_allowed"), bool):
        errors.append(f"{path}: grants_allowed must be boolean")
    manual_review_required = value.get("manual_review_required")
    if not isinstance(manual_review_required, list) or not all(isinstance(item, str) for item in manual_review_required):
        errors.append(f"{path}: manual_review_required must be an array of strings")
    elif unknown_review := sorted(set(manual_review_required) - POLICY_REVIEW_REQUIREMENTS):
        errors.append(f"{path}: manual_review_required contains unsupported values {unknown_review}")
    forbidden_permissions = value.get("forbidden_permissions")
    if not isinstance(forbidden_permissions, list) or not all(isinstance(item, str) for item in forbidden_permissions):
        errors.append(f"{path}: forbidden_permissions must be an array of strings")
    else:
        if unknown_forbidden := sorted(set(forbidden_permissions) - POLICY_FORBIDDEN_PERMISSIONS):
            errors.append(f"{path}: forbidden_permissions contains unsupported values {unknown_forbidden}")
        for required_forbidden in ("wildcard", "export_secret"):
            if required_forbidden not in forbidden_permissions:
                errors.append(f"{path}: forbidden_permissions must include {required_forbidden}")
    if value.get("risk_tiers") is not None and not isinstance(value["risk_tiers"], dict):
        errors.append(f"{path}: risk_tiers must be an object")
    elif isinstance(value.get("risk_tiers"), dict):
        if unknown_risk_names := sorted(set(value["risk_tiers"]) - POLICY_RISK_NAMES):
            errors.append(f"{path}: risk_tiers contains unsupported keys {unknown_risk_names}")
        for risk_name, risk_tier in value["risk_tiers"].items():
            if risk_tier not in POLICY_RISK_TIERS:
                errors.append(f"{path}: risk_tiers.{risk_name} uses unsupported tier {risk_tier!r}")
    if set(route_types) & QR_ROUTE_TYPES and (mode != "manual_only" or value.get("grants_allowed") is not False):
        errors.append(f"{path}: QR vault routes must remain manual_only with grants_allowed false")
    if "smartcard" in route_types and (mode != "manual_only" or value.get("grants_allowed") is not False):
        errors.append(f"{path}: display-less smartcard routes must remain manual_only with grants_allowed false")
    if "external_nip46" in route_types and (mode != "manual_only" or value.get("grants_allowed") is not False):
        errors.append(f"{path}: external NIP-46 routes must remain external-policy manual without nSealr grants")
    if mode == "manual_only" and value.get("grants_allowed") is True:
        errors.append(f"{path}: manual_only profiles must not allow grants")
    if value.get("grants_allowed") is True:
        constraints = value.get("grant_constraints")
        if not isinstance(constraints, dict):
            errors.append(f"{path}: grant_constraints are required when grants_allowed is true")
        else:
            check_known_fields(
                path,
                "grant_constraints",
                constraints,
                {
                    "expiry_required",
                    "rate_limit_required",
                    "revocation_required",
                    "audit_log_required",
                    "device_confirmation_required",
                },
                errors,
            )
            for field in (
                "expiry_required",
                "rate_limit_required",
                "revocation_required",
                "audit_log_required",
                "device_confirmation_required",
            ):
                if constraints.get(field) is not True:
                    errors.append(f"{path}: grant_constraints.{field} must be true")
    elif "grant_constraints" in value:
        errors.append(f"{path}: grant_constraints must be absent when grants are not allowed")


def check_grant_descriptor_shape(path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: grant descriptor must be an object")
        return
    check_no_secret_fields(path, value, errors)
    check_known_fields(
        path,
        "grant descriptor",
        value,
        {
            "format",
            "grant_id",
            "account_id",
            "route_type",
            "client",
            "permission",
            "expires_at",
            "rate_limit",
            "requires_device_policy_confirmation",
            "revocable",
            "audit_event_format",
        },
        errors,
    )
    if value.get("format") != "nsealr-grant-descriptor-v0":
        errors.append(f"{path}: format mismatch")
    check_grant_id(path, "grant_id", value.get("grant_id"), errors)
    check_string_id(path, "account_id", value.get("account_id"), errors)
    route_type = value.get("route_type")
    if route_type not in ROUTE_TYPES:
        errors.append(f"{path}: route_type is unknown")
    elif route_type not in GRANT_ROUTE_TYPES:
        errors.append(f"{path}: grant route_type must be a nSealr persistent policy route")
    client = value.get("client")
    if not isinstance(client, dict):
        errors.append(f"{path}: client must be an object")
    else:
        check_known_fields(path, "client", client, {"pubkey", "label"}, errors)
        if not isinstance(client.get("pubkey"), str) or not HEX32_RE.fullmatch(client["pubkey"]):
            errors.append(f"{path}: client.pubkey must be 32-byte lowercase hex")
        if "label" in client and not isinstance(client["label"], str):
            errors.append(f"{path}: client.label must be a string")
    check_permission_shape(path, value.get("permission"), errors, grant_permission=True)
    if type(value.get("expires_at")) is not int or value["expires_at"] <= 0:
        errors.append(f"{path}: expires_at must be a positive integer")
    rate_limit = value.get("rate_limit")
    if not isinstance(rate_limit, dict):
        errors.append(f"{path}: rate_limit must be an object")
    else:
        check_known_fields(path, "rate_limit", rate_limit, {"max_uses", "window_seconds"}, errors)
        for field in ("max_uses", "window_seconds"):
            if type(rate_limit.get(field)) is not int or rate_limit[field] <= 0:
                errors.append(f"{path}: rate_limit.{field} must be a positive integer")
    if value.get("requires_device_policy_confirmation") is not True:
        errors.append(f"{path}: requires_device_policy_confirmation must be true")
    if value.get("revocable") is not True:
        errors.append(f"{path}: revocable must be true")
    if value.get("audit_event_format") != "nsealr-grant-audit-event-v0":
        errors.append(f"{path}: audit_event_format mismatch")


def check_account_descriptor_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/accounts/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_account_descriptor_shape(vector_path, vector, errors)


def check_policy_profile_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/policies/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_policy_profile_shape(vector_path, vector, errors)
    policy_id = vector.get("policy_id")
    if isinstance(policy_id, str) and policy_id != f"policy-{rel}":
        errors.append(f"{vector_path}: policy_id/file name mismatch")


def check_grant_descriptor_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/grants/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_grant_descriptor_shape(vector_path, vector, errors)
    account_id = vector.get("account_id")
    route_type = vector.get("route_type")
    matching_accounts = []
    for name in account_descriptor_vector_names():
        account = load_json(f"vectors/accounts/{name}.json")
        if account.get("account_id") == account_id:
            matching_accounts.append(account)
    if not matching_accounts:
        errors.append(f"{vector_path}: account_id target is missing")
    elif matching_accounts[0].get("signer_route", {}).get("type") != route_type:
        errors.append(f"{vector_path}: account route_type mismatch")


def policy_permission_key(permission: dict) -> str:
    if permission.get("method") == "sign_event":
        return f"sign_event:{permission.get('event_kind')}"
    return str(permission.get("method"))


def permissions_match(grant_permission: dict, request_permission: dict) -> bool:
    if grant_permission.get("method") != request_permission.get("method"):
        return False
    if grant_permission.get("method") == "sign_event":
        return (
            grant_permission.get("parameter") == request_permission.get("parameter")
            and grant_permission.get("event_kind") == request_permission.get("event_kind")
        )
    return "parameter" not in grant_permission and "event_kind" not in grant_permission


def policy_audit_event(request: dict, decision: str, reason: str, grant_id: str | None = None) -> dict:
    event = {
        "format": "nsealr-grant-audit-event-v0",
        "occurred_at": request["now"],
        "account_id": request["account_id"],
        "route_type": request["route_type"],
        "client_pubkey": request["client_pubkey"],
        "permission": request["permission"],
        "decision": decision,
        "reason": reason,
    }
    if grant_id is not None:
        event["grant_id"] = grant_id
    return event


def policy_decision(decision: str, reason: str, request: dict, grant_id: str | None = None) -> dict:
    result = {
        "format": "nsealr-policy-decision-v0",
        "decision": decision,
        "reason": reason,
        "audit_event": policy_audit_event(request, decision, reason, grant_id),
    }
    if grant_id is not None:
        result["grant_id"] = grant_id
    return result


def grant_rate_limited(grant: dict, request: dict) -> bool:
    usage_by_grant = request.get("grant_usage")
    if not isinstance(usage_by_grant, dict):
        return False
    usage = usage_by_grant.get(grant.get("grant_id"))
    if not isinstance(usage, dict):
        return False
    rate_limit = grant.get("rate_limit")
    if not isinstance(rate_limit, dict):
        return False
    if type(request.get("now")) is not int:
        return False
    if type(usage.get("window_started_at")) is not int or type(usage.get("uses")) is not int:
        return False
    if type(rate_limit.get("window_seconds")) is not int or type(rate_limit.get("max_uses")) is not int:
        return False
    window_ends_at = usage["window_started_at"] + rate_limit["window_seconds"]
    return request["now"] < window_ends_at and usage["uses"] >= rate_limit["max_uses"]


def expected_policy_decision(vector_path: str, vector: dict, errors: list[str]) -> dict | None:
    request = vector.get("request")
    if not isinstance(request, dict):
        errors.append(f"{vector_path}: request must be an object")
        return None
    profile_id = vector.get("policy_profile_id")
    if not isinstance(profile_id, str) or not profile_id.startswith("policy-"):
        errors.append(f"{vector_path}: policy_profile_id must reference a policy-* profile")
        return None
    policy_path = f"vectors/policies/{profile_id.removeprefix('policy-')}.json"
    policy = load_required_json(policy_path, errors)
    if policy is None:
        return None
    route_types = policy.get("route_types")
    if isinstance(route_types, list) and request.get("route_type") not in route_types:
        return policy_decision("manual_review", "policy_route_mismatch", request)

    permission = request.get("permission")
    if not isinstance(permission, dict):
        errors.append(f"{vector_path}: request.permission must be an object")
        return None
    method = permission.get("method")
    forbidden_permissions = policy.get("forbidden_permissions", [])
    if method in forbidden_permissions or method == "export_secret":
        return policy_decision("deny", "forbidden_permission", request)
    if method in DECRYPT_METHODS:
        return policy_decision("manual_review", "decrypt_requires_manual_review", request)
    if method == "unknown_method":
        return policy_decision("manual_review", "unknown_method_requires_manual_review", request)
    if policy.get("grants_allowed") is not True:
        return policy_decision("manual_review", "policy_manual_only", request)

    revoked = set(request.get("revoked_grant_ids", []))
    for grant_id in request.get("grant_ids", []):
        if not check_grant_id(vector_path, "request.grant_ids item", grant_id, errors):
            continue
        grant = load_required_json(f"vectors/grants/{grant_id.removeprefix('grant-')}.json", errors)
        if grant is None:
            continue
        if grant.get("account_id") != request.get("account_id"):
            continue
        if grant.get("route_type") != request.get("route_type"):
            continue
        if grant.get("client", {}).get("pubkey") != request.get("client_pubkey"):
            continue
        grant_permission = grant.get("permission")
        if not isinstance(grant_permission, dict) or not permissions_match(grant_permission, permission):
            continue
        if grant_id in revoked:
            return policy_decision("deny", "grant_revoked", request, grant_id)
        if type(request.get("now")) is int and type(grant.get("expires_at")) is int and request["now"] >= grant["expires_at"]:
            return policy_decision("deny", "grant_expired", request, grant_id)
        if grant_rate_limited(grant, request):
            return policy_decision("deny", "grant_rate_limited", request, grant_id)
        return policy_decision("allow", "grant_valid", request, grant_id)
    return policy_decision("manual_review", "no_matching_grant", request)


def check_policy_decision_request_shape(path: str, request: object, errors: list[str]) -> None:
    if not isinstance(request, dict):
        errors.append(f"{path}: request must be an object")
        return
    check_known_fields(
        path,
        "request",
        request,
        {"account_id", "route_type", "client_pubkey", "permission", "now", "grant_ids", "grant_usage", "revoked_grant_ids"},
        errors,
    )
    check_string_id(path, "request.account_id", request.get("account_id"), errors)
    if request.get("route_type") not in ROUTE_TYPES:
        errors.append(f"{path}: request.route_type is unknown")
    elif request.get("route_type") not in {"esp32_usb_nip46", "smartcard", "custom_hardware_wallet", "external_nip46"}:
        errors.append(f"{path}: request.route_type must be a persistent or external route")
    if not isinstance(request.get("client_pubkey"), str) or not HEX32_RE.fullmatch(request["client_pubkey"]):
        errors.append(f"{path}: request.client_pubkey must be 32-byte lowercase hex")
    check_permission_shape(path, request.get("permission"), errors)
    if type(request.get("now")) is not int or request["now"] <= 0:
        errors.append(f"{path}: request.now must be a positive integer")
    grant_ids = request.get("grant_ids")
    if not isinstance(grant_ids, list):
        errors.append(f"{path}: request.grant_ids must be an array of strings")
    else:
        for grant_id in grant_ids:
            check_grant_id(path, "request.grant_ids item", grant_id, errors)
    grant_usage = request.get("grant_usage")
    if not isinstance(grant_usage, dict):
        errors.append(f"{path}: request.grant_usage must be an object")
    else:
        for grant_id, usage in grant_usage.items():
            if not check_grant_id(path, "request.grant_usage key", grant_id, errors):
                errors.append(f"{path}: request.grant_usage keys must be grant ids")
                continue
            if not isinstance(usage, dict):
                errors.append(f"{path}: request.grant_usage.{grant_id} must be an object")
                continue
            unknown = sorted(set(usage) - {"window_started_at", "uses"})
            if unknown:
                errors.append(f"{path}: request.grant_usage.{grant_id} has unknown fields {unknown}")
            if type(usage.get("window_started_at")) is not int or usage["window_started_at"] <= 0:
                errors.append(f"{path}: request.grant_usage.{grant_id}.window_started_at must be a positive integer")
            if type(usage.get("uses")) is not int or usage["uses"] < 0:
                errors.append(f"{path}: request.grant_usage.{grant_id}.uses must be a non-negative integer")
    revoked_grant_ids = request.get("revoked_grant_ids")
    if not isinstance(revoked_grant_ids, list):
        errors.append(f"{path}: request.revoked_grant_ids must be an array of strings")
    else:
        for grant_id in revoked_grant_ids:
            check_grant_id(path, "request.revoked_grant_ids item", grant_id, errors)


def check_policy_decision_shape(path: str, decision: object, errors: list[str]) -> None:
    if not isinstance(decision, dict):
        errors.append(f"{path}: decision must be an object")
        return
    check_known_fields(path, "decision", decision, {"format", "decision", "reason", "grant_id", "audit_event"}, errors)
    if decision.get("format") != "nsealr-policy-decision-v0":
        errors.append(f"{path}: decision format mismatch")
    if decision.get("decision") not in POLICY_DECISIONS:
        errors.append(f"{path}: decision is unknown")
    if decision.get("reason") not in POLICY_DECISION_REASONS:
        errors.append(f"{path}: reason is unknown")
    if "grant_id" in decision:
        check_grant_id(path, "decision.grant_id", decision.get("grant_id"), errors)
    audit = decision.get("audit_event")
    if not isinstance(audit, dict):
        errors.append(f"{path}: audit_event must be an object")
        return
    check_known_fields(
        path,
        "audit_event",
        audit,
        {"format", "occurred_at", "account_id", "route_type", "client_pubkey", "permission", "decision", "reason", "grant_id"},
        errors,
    )
    if audit.get("format") != "nsealr-grant-audit-event-v0":
        errors.append(f"{path}: audit_event format mismatch")
    if type(audit.get("occurred_at")) is not int or audit["occurred_at"] <= 0:
        errors.append(f"{path}: audit_event.occurred_at must be a positive integer")
    check_string_id(path, "audit_event.account_id", audit.get("account_id"), errors)
    if audit.get("route_type") not in {"esp32_usb_nip46", "smartcard", "custom_hardware_wallet", "external_nip46"}:
        errors.append(f"{path}: audit_event.route_type must be a persistent or external route")
    if not isinstance(audit.get("client_pubkey"), str) or not HEX32_RE.fullmatch(audit["client_pubkey"]):
        errors.append(f"{path}: audit_event.client_pubkey must be 32-byte lowercase hex")
    check_permission_shape(path, audit.get("permission"), errors)
    if audit.get("decision") != decision.get("decision") or audit.get("reason") != decision.get("reason"):
        errors.append(f"{path}: audit_event decision/reason mismatch")
    if "grant_id" in audit:
        check_grant_id(path, "audit_event.grant_id", audit.get("grant_id"), errors)
    if decision.get("grant_id") != audit.get("grant_id"):
        errors.append(f"{path}: decision/audit_event grant_id mismatch")


def check_policy_decision_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/policy-decisions/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: policy decision vector must be an object")
        return
    check_no_secret_fields(vector_path, vector, errors)
    check_known_fields(
        vector_path,
        "policy decision vector",
        vector,
        {"name", "format", "policy_profile_id", "request", "decision"},
        errors,
    )
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-policy-decision-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    check_policy_decision_request_shape(vector_path, vector.get("request"), errors)
    check_policy_decision_shape(vector_path, vector.get("decision"), errors)
    expected = expected_policy_decision(vector_path, vector, errors)
    if expected is not None and vector.get("decision") != expected:
        errors.append(f"{vector_path}: decision mismatch")


def expected_policy_change_review_pages(proposal: dict) -> list[dict]:
    grants = proposal["proposed_grant_ids"]
    requester = proposal["requested_by"]
    policy_lines = [
        f"From: {proposal['current_policy_id']}",
        f"To: {proposal['proposed_policy_id']}",
        f"Grants: {len(grants)}",
    ]
    policy_lines.extend(f"Grant: {grant_id}" for grant_id in grants)
    requester_lines = [
        f"Surface: {requester['surface']}",
        f"Client: {requester['client_pubkey']}",
    ]
    if requester.get("label"):
        requester_lines.append(f"Label: {requester['label']}")
    return [
        {
            "title": "Policy change",
            "lines": [
                f"Action: {proposal['action']}",
                f"Account: {proposal['account_id']}",
                f"Route: {proposal['route_type']}",
            ],
            "action": "next",
        },
        {
            "title": "Requester",
            "lines": requester_lines,
            "action": "next",
        },
        {
            "title": "Policy",
            "lines": policy_lines,
            "action": "next",
        },
        {
            "title": "Decision",
            "lines": [
                "Review on device",
                "Physical approval required",
                "Companion cannot approve alone",
            ],
            "action": "approve_or_reject",
        },
    ]


def policy_change_approval_digest(proposal: dict, pages: list[dict]) -> str:
    canonical = json.dumps(
        {"proposal": proposal, "pages": pages},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256_hex(canonical.encode("utf-8"))


def check_policy_change_proposal_shape(path: str, proposal: object, errors: list[str]) -> dict | None:
    if not isinstance(proposal, dict):
        errors.append(f"{path}: proposal must be an object")
        return None
    unknown = sorted(
        set(proposal)
        - {
            "format",
            "proposal_id",
            "account_id",
            "route_type",
            "action",
            "current_policy_id",
            "proposed_policy_id",
            "proposed_grant_ids",
            "requested_by",
            "created_at",
            "device_review_required",
            "physical_approval_required",
            "companion_authoritative",
            "contains_secret_material",
        }
    )
    if unknown:
        errors.append(f"{path}: proposal has unknown fields {unknown}")
    if proposal.get("format") != "nsealr-policy-change-proposal-v0":
        errors.append(f"{path}: proposal format mismatch")
    check_proposal_id(path, "proposal_id", proposal.get("proposal_id"), errors)
    check_string_id(path, "account_id", proposal.get("account_id"), errors)
    route_type = proposal.get("route_type")
    if route_type not in POLICY_CHANGE_ROUTE_TYPES:
        errors.append(f"{path}: route_type must be a device-display persistent policy route")
    if proposal.get("action") != "set_policy":
        errors.append(f"{path}: action must be set_policy")
    for field in ("current_policy_id", "proposed_policy_id"):
        policy_id = proposal.get(field)
        if not check_policy_id(path, field, policy_id, errors):
            continue
        policy = load_required_json(f"vectors/policies/{policy_id.removeprefix('policy-')}.json", errors)
        if isinstance(route_type, str) and isinstance(policy, dict) and route_type not in policy.get("route_types", []):
            errors.append(f"{path}: {field} does not include route type {route_type}")

    matching_accounts = []
    for name in account_descriptor_vector_names():
        account = load_json(f"vectors/accounts/{name}.json")
        if account.get("account_id") == proposal.get("account_id"):
            matching_accounts.append(account)
    if not matching_accounts:
        errors.append(f"{path}: account_id target is missing")
    elif matching_accounts[0].get("signer_route", {}).get("type") != route_type:
        errors.append(f"{path}: account route_type mismatch")
    elif matching_accounts[0].get("policy_profile_id") != proposal.get("current_policy_id"):
        errors.append(f"{path}: current_policy_id must match the account descriptor default policy")

    grants = proposal.get("proposed_grant_ids")
    if not isinstance(grants, list):
        errors.append(f"{path}: proposed_grant_ids must be an array of strings")
        grants = []
    elif len(grants) != len(set(grants)):
        errors.append(f"{path}: proposed_grant_ids must be unique")
    for grant_id in grants:
        if not check_grant_id(path, "proposed_grant_ids item", grant_id, errors):
            continue
        grant = load_required_json(f"vectors/grants/{grant_id.removeprefix('grant-')}.json", errors)
        if not isinstance(grant, dict):
            continue
        if grant.get("account_id") != proposal.get("account_id"):
            errors.append(f"{path}: proposed grant {grant_id} account mismatch")
        if grant.get("route_type") != route_type:
            errors.append(f"{path}: proposed grant {grant_id} route mismatch")

    requester = proposal.get("requested_by")
    if not isinstance(requester, dict):
        errors.append(f"{path}: requested_by must be an object")
    else:
        unknown_requester = sorted(set(requester) - {"surface", "client_pubkey", "label"})
        if unknown_requester:
            errors.append(f"{path}: requested_by has unknown fields {unknown_requester}")
        if requester.get("surface") not in LOCAL_CLIENT_SURFACES:
            errors.append(f"{path}: requested_by.surface is unsupported")
        if not isinstance(requester.get("client_pubkey"), str) or not HEX32_RE.fullmatch(requester["client_pubkey"]):
            errors.append(f"{path}: requested_by.client_pubkey must be 32-byte lowercase hex")
        if "label" in requester and (not isinstance(requester.get("label"), str) or not requester["label"]):
            errors.append(f"{path}: requested_by.label must be a non-empty string")

    if type(proposal.get("created_at")) is not int or proposal["created_at"] <= 0:
        errors.append(f"{path}: created_at must be a positive integer")
    if proposal.get("device_review_required") is not True:
        errors.append(f"{path}: device_review_required must be true")
    if proposal.get("physical_approval_required") is not True:
        errors.append(f"{path}: physical_approval_required must be true")
    if proposal.get("companion_authoritative") is not False:
        errors.append(f"{path}: companion_authoritative must be false")
    if proposal.get("contains_secret_material") is not False:
        errors.append(f"{path}: contains_secret_material must be false")
    return proposal


def check_policy_change_review_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/policy-changes/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: policy change review vector must be an object")
        return
    check_no_secret_fields(vector_path, vector, errors)
    unknown = sorted(set(vector) - {"name", "format", "proposal", "review"})
    if unknown:
        errors.append(f"{vector_path}: unknown fields {unknown}")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-policy-change-review-v0":
        errors.append(f"{vector_path}: format mismatch")

    proposal = check_policy_change_proposal_shape(vector_path, vector.get("proposal"), errors)
    review = vector.get("review")
    if not isinstance(review, dict):
        errors.append(f"{vector_path}: review must be an object")
        return
    unknown_review = sorted(set(review) - {"format", "proposal_id", "approval_digest", "pages"})
    if unknown_review:
        errors.append(f"{vector_path}: review has unknown fields {unknown_review}")
    if review.get("format") != "nsealr-policy-change-review-pages-v0":
        errors.append(f"{vector_path}: review format mismatch")
    if proposal is None:
        return
    check_proposal_id(vector_path, "review.proposal_id", review.get("proposal_id"), errors)
    if review.get("proposal_id") != proposal.get("proposal_id"):
        errors.append(f"{vector_path}: review proposal_id mismatch")
    pages = review.get("pages")
    if not isinstance(pages, list):
        errors.append(f"{vector_path}: review pages must be an array")
        return
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            errors.append(f"{vector_path}: review pages[{index}] must be an object")
            continue
        unknown_page = sorted(set(page) - {"title", "lines", "action"})
        if unknown_page:
            errors.append(f"{vector_path}: review pages[{index}] has unknown fields {unknown_page}")
        if not isinstance(page.get("title"), str) or not page["title"]:
            errors.append(f"{vector_path}: review pages[{index}].title must be a non-empty string")
        if not isinstance(page.get("lines"), list) or not all(isinstance(line, str) for line in page["lines"]):
            errors.append(f"{vector_path}: review pages[{index}].lines must be strings")
        if page.get("action") not in {"next", "approve_or_reject"}:
            errors.append(f"{vector_path}: review pages[{index}].action is invalid")
    expected_pages = expected_policy_change_review_pages(proposal)
    if pages != expected_pages:
        errors.append(f"{vector_path}: review pages mismatch")
    expected_digest = policy_change_approval_digest(proposal, expected_pages)
    if review.get("approval_digest") != expected_digest:
        errors.append(f"{vector_path}: approval_digest mismatch")


def route_selection_from_account(account: dict) -> dict:
    route = account["signer_route"]
    capabilities = account["capabilities"]
    selection = {
        "format": "nsealr-route-selection-v0",
        "account_id": account["account_id"],
        "public_key": account["public_key"],
        "route_type": route["type"],
        "transport": route["transport"],
        "custody": route["custody"],
        "trusted_review": route["trusted_review"],
        "policy_support": route["policy_support"],
        "policy_profile_id": account["policy_profile_id"],
        "physical_review": capabilities["physical_review"],
        "physical_approval": capabilities["physical_approval"],
        "persistent_grants": capabilities["persistent_grants"],
        "contains_secret_material": False,
    }
    if "repository" in route:
        selection["repository"] = route["repository"]
    return selection


def check_route_selection_request_shape(path: str, request: object, errors: list[str]) -> None:
    if not isinstance(request, dict):
        errors.append(f"{path}: request must be an object")
        return
    unknown = sorted(set(request) - {"account_id", "method", "route_type"})
    if unknown:
        errors.append(f"{path}: request has unknown fields {unknown}")
    check_string_id(path, "request.account_id", request.get("account_id"), errors)
    if not isinstance(request.get("method"), str) or not request["method"]:
        errors.append(f"{path}: request.method must be a non-empty string")
    if "route_type" in request and request.get("route_type") not in ROUTE_TYPES:
        errors.append(f"{path}: request.route_type is unknown")


def check_route_selection_shape(path: str, selection: object, errors: list[str]) -> None:
    if not isinstance(selection, dict):
        errors.append(f"{path}: selection must be an object")
        return
    expected_fields = {
        "format",
        "account_id",
        "public_key",
        "route_type",
        "repository",
        "transport",
        "custody",
        "trusted_review",
        "policy_support",
        "policy_profile_id",
        "physical_review",
        "physical_approval",
        "persistent_grants",
        "contains_secret_material",
    }
    unknown = sorted(set(selection) - expected_fields)
    if unknown:
        errors.append(f"{path}: selection has unknown fields {unknown}")
    if selection.get("format") != "nsealr-route-selection-v0":
        errors.append(f"{path}: selection format mismatch")
    check_string_id(path, "selection.account_id", selection.get("account_id"), errors)
    if not isinstance(selection.get("public_key"), str) or not HEX32_RE.fullmatch(selection["public_key"]):
        errors.append(f"{path}: selection.public_key must be 32-byte lowercase hex")
    if selection.get("route_type") not in ROUTE_TYPES:
        errors.append(f"{path}: selection.route_type is unknown")
    expected_repository = ROUTE_REPOSITORIES.get(selection.get("route_type"))
    if expected_repository is not None and selection.get("repository") != expected_repository:
        errors.append(f"{path}: selection.repository must be {expected_repository}")
    if expected_repository is None and "repository" in selection:
        errors.append(f"{path}: external signer selections must not claim a nSealr repository")
    if selection.get("transport") not in ROUTE_TRANSPORTS:
        errors.append(f"{path}: selection.transport is unknown")
    if selection.get("custody") not in ROUTE_CUSTODY_MODES:
        errors.append(f"{path}: selection.custody is unknown")
    if selection.get("trusted_review") not in ROUTE_REVIEW_MODES:
        errors.append(f"{path}: selection.trusted_review is unknown")
    if selection.get("policy_support") not in POLICY_SUPPORT_MODES:
        errors.append(f"{path}: selection.policy_support is unknown")
    for field in ("physical_review", "physical_approval", "persistent_grants"):
        if not isinstance(selection.get(field), bool):
            errors.append(f"{path}: selection.{field} must be boolean")
    if selection.get("contains_secret_material") is not False:
        errors.append(f"{path}: selection.contains_secret_material must be false")


def expected_route_selection(vector_path: str, vector: dict, errors: list[str]) -> dict | None:
    request = vector.get("request")
    if not isinstance(request, dict):
        return None
    account_id = request.get("account_id")
    matches = []
    for name in account_descriptor_vector_names():
        account = load_json(f"vectors/accounts/{name}.json")
        if account.get("account_id") == account_id:
            matches.append(account)
    if not matches:
        errors.append(f"{vector_path}: request.account_id target is missing")
        return None
    if len(matches) > 1:
        errors.append(f"{vector_path}: request.account_id is ambiguous")
        return None
    account = matches[0]
    route = account.get("signer_route", {})
    capabilities = account.get("capabilities", {})
    if request.get("route_type") is not None and request.get("route_type") != route.get("type"):
        errors.append(f"{vector_path}: request.route_type does not match account route")
        return None
    if request.get("method") not in capabilities.get("methods", []):
        errors.append(f"{vector_path}: request.method is not supported by account")
        return None
    return route_selection_from_account(account)


def check_route_selection_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/route-selections/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: route selection vector must be an object")
        return
    check_no_secret_fields(vector_path, vector, errors)
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-route-selection-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    check_route_selection_request_shape(vector_path, vector.get("request"), errors)
    check_route_selection_shape(vector_path, vector.get("selection"), errors)
    expected = expected_route_selection(vector_path, vector, errors)
    if expected is not None and vector.get("selection") != expected:
        errors.append(f"{vector_path}: selection mismatch")


def check_route_refusal_error(path: str, value: object, expected_code: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: error expectation must be an object")
        return
    if set(value.keys()) != {"error_code", "message", "retryable"}:
        errors.append(f"{path}: error expectation has unsupported fields")
    if value.get("error_code") != expected_code:
        errors.append(f"{path}: expected error_code {expected_code}")
    if not isinstance(value.get("message"), str) or len(value.get("message", "")) == 0:
        errors.append(f"{path}: message must be a non-empty string")
    if value.get("retryable") is not False:
        errors.append(f"{path}: retryable must be false")


def check_route_refusal_contract_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/route-refusals/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: route-refusal contract must be an object")
        return
    check_no_secret_fields(vector_path, vector, errors)
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-route-refusal-contract-v0":
        errors.append(f"{vector_path}: format mismatch")

    request_vector = vector.get("request_vector")
    if not isinstance(request_vector, str) or not request_vector.startswith("examples/"):
        errors.append(f"{vector_path}: request_vector must point under examples/")
    else:
        request = load_required_json(request_vector, errors)
        if request is not None:
            check_request_shape(Path(request_vector), request, errors)
            if request.get("method") != "sign_event":
                errors.append(f"{vector_path}: request_vector must reference sign_event")

    cases = vector.get("cases")
    if not isinstance(cases, list) or len(cases) == 0:
        errors.append(f"{vector_path}: cases must be a non-empty array")
        cases = []

    route_vectors = route_selection_vector_names()
    seen_route_vectors: set[str] = set()
    for index, case in enumerate(cases):
        case_path = f"{vector_path}: cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{case_path}: case must be an object")
            continue
        route_selection_vector = case.get("route_selection_vector")
        if not isinstance(route_selection_vector, str) or route_selection_vector not in route_vectors:
            errors.append(f"{case_path}: route_selection_vector is invalid")
            continue
        if route_selection_vector in seen_route_vectors:
            errors.append(f"{case_path}: duplicate route_selection_vector")
        seen_route_vectors.add(route_selection_vector)

        route_vector = load_required_json(f"vectors/route-selections/{route_selection_vector}.json", errors)
        selection = route_vector.get("selection") if isinstance(route_vector, dict) else {}
        if not isinstance(selection, dict):
            errors.append(f"{case_path}: route selection is invalid")
            continue
        if case.get("route_type") != selection.get("route_type"):
            errors.append(f"{case_path}: route_type mismatch")
        if case.get("trusted_review") != selection.get("trusted_review"):
            errors.append(f"{case_path}: trusted_review mismatch")

        acknowledgement = case.get("external_review_acknowledgement")
        if not isinstance(acknowledgement, dict):
            errors.append(f"{case_path}: external_review_acknowledgement must be an object")
            continue
        mode = acknowledgement.get("mode")
        if selection.get("trusted_review") == "display_less":
            if mode != "required":
                errors.append(f"{case_path}: display-less routes must require external review acknowledgement")
            if "without_dispatcher" in case:
                errors.append(f"{case_path}: display-less route must not bypass acknowledgement before dispatcher")
            check_route_refusal_error(
                f"{case_path}.without_dispatcher_after_ack",
                case.get("without_dispatcher_after_ack"),
                "signer_route_unavailable",
                errors,
            )
            check_route_refusal_error(
                f"{case_path}.external_review_acknowledgement.missing_error",
                acknowledgement.get("missing_error"),
                "external_review_acknowledgement_required",
                errors,
            )
            check_route_refusal_error(
                f"{case_path}.external_review_acknowledgement.mismatch_error",
                acknowledgement.get("mismatch_error"),
                "external_review_acknowledgement_mismatch",
                errors,
            )
        else:
            if mode != "unsupported":
                errors.append(f"{case_path}: trusted-review routes must reject external review acknowledgement")
            if "without_dispatcher_after_ack" in case:
                errors.append(f"{case_path}: trusted-review route must use without_dispatcher")
            check_route_refusal_error(
                f"{case_path}.without_dispatcher",
                case.get("without_dispatcher"),
                "signer_route_unavailable",
                errors,
            )
            check_route_refusal_error(
                f"{case_path}.external_review_acknowledgement.unsupported_error",
                acknowledgement.get("unsupported_error"),
                "external_review_acknowledgement_unsupported",
                errors,
            )

    if seen_route_vectors != set(route_vectors):
        errors.append(f"{vector_path}: cases must cover every route selection vector")
    if vector.get("safety") != ROUTE_REFUSAL_SAFETY:
        errors.append(f"{vector_path}: safety boundary mismatch")
    scope = vector.get("scope")
    if not isinstance(scope, str) or "Secretless route-refusal" not in scope or "not a signer family" not in scope:
        errors.append(f"{vector_path}: scope must preserve secretless route-refusal boundary")


def check_access_surface_safety(path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: safety must be an object")
        return
    expected = {
        "stores_production_secrets": False,
        "contains_secret_material": False,
        "creates_grants": False,
        "dispatches_without_signer": False,
        "requires_shared_request_validation": True,
        "requires_signed_response_verification": True,
    }
    if value != expected:
        errors.append(f"{path}: safety boundary mismatch")


def check_access_surface_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/access-surfaces/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: access-surface vector must be an object")
        return
    check_no_secret_fields(vector_path, vector, errors)
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-access-surface-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("surface") not in ACCESS_SURFACES:
        errors.append(f"{vector_path}: surface is unsupported")
    if vector.get("transport") not in ACCESS_SURFACE_TRANSPORTS:
        errors.append(f"{vector_path}: transport is unsupported")

    client = check_local_client_identity(vector_path, vector.get("client"), errors)
    if client is not None:
        check_local_client_grant(vector_path, vector.get("client_grant"), client, errors)

    route_name = vector.get("route_selection_vector")
    if not isinstance(route_name, str):
        errors.append(f"{vector_path}: route_selection_vector must be a string")
        route = None
    else:
        route = load_required_json(f"vectors/route-selections/{route_name}.json", errors)
        check_route_selection_vector(route_name, errors)

    request_rel = vector.get("sign_event_request_vector")
    if not isinstance(request_rel, str) or not request_rel.startswith("examples/"):
        errors.append(f"{vector_path}: sign_event_request_vector must point under examples/")
        request = None
    else:
        request = load_required_json(request_rel, errors)
        if request is not None:
            check_request_shape(Path(request_rel), request, errors)
            if request.get("method") != "sign_event":
                errors.append(f"{vector_path}: sign_event_request_vector must reference sign_event")

    expected = vector.get("expected")
    if not isinstance(expected, dict):
        errors.append(f"{vector_path}: expected must be an object")
        expected = {}

    get_public_key = expected.get("get_public_key")
    if not isinstance(get_public_key, dict):
        errors.append(f"{vector_path}: expected.get_public_key must be an object")
    elif route is not None and get_public_key.get("public_key") != route.get("selection", {}).get("public_key"):
        errors.append(f"{vector_path}: expected get_public_key public_key mismatch")

    unavailable = expected.get("sign_event_without_dispatcher")
    if not isinstance(unavailable, dict):
        errors.append(f"{vector_path}: expected.sign_event_without_dispatcher must be an object")
    else:
        response = unavailable.get("response")
        if isinstance(response, dict):
            check_response_shape(Path(vector_path), response, errors)
            if request is not None and response.get("request_id") != request.get("request_id"):
                errors.append(f"{vector_path}: unavailable response request_id mismatch")
            if response.get("ok") is not False:
                errors.append(f"{vector_path}: unavailable response must be an error response")
            error = response.get("error", {})
            if error.get("code") != "signer_route_unavailable":
                errors.append(f"{vector_path}: unavailable response error code mismatch")
            if error.get("retryable") is not False:
                errors.append(f"{vector_path}: unavailable response must be non-retryable")
        else:
            errors.append(f"{vector_path}: unavailable response must be an object")

    check_access_surface_safety(vector_path, vector.get("safety"), errors)
    scope = vector.get("scope")
    if not isinstance(scope, str) or "not a signer family" not in scope or "secretless" not in scope:
        errors.append(f"{vector_path}: scope must state secretless access-surface boundary")


def check_review_screen_vector(rel: str, errors: list[str]) -> None:
    vector = load_required_json(f"vectors/review-screens/{rel}.json", errors)
    if vector is None:
        return
    request = vector.get("request")
    if not isinstance(request, dict):
        errors.append(f"vectors/review-screens/{rel}.json: request must be an object")
        return
    check_request_shape(Path(f"vectors/review-screens/{rel}.json"), request, errors)
    if request.get("method") != "sign_event":
        errors.append(f"vectors/review-screens/{rel}.json: request method must be sign_event")
        return
    expected_review_value = expected_review(request["params"]["event_template"])
    expected_screen = expected_screen_review(request)
    if vector.get("name") != rel:
        errors.append(f"vectors/review-screens/{rel}.json: name mismatch")
    if vector.get("review") != expected_review_value:
        errors.append(f"vectors/review-screens/{rel}.json: review mismatch")
    if vector.get("screen_review") != expected_screen:
        errors.append(f"vectors/review-screens/{rel}.json: screen_review mismatch")


def frame_for_page(page: dict, page_index: int, total_pages: int) -> dict:
    action_hint = "Next" if page["action"] == "next" else "Approve / Reject"
    return {
        "title": page["title"],
        "page_indicator": f"Page {page_index + 1}/{total_pages}",
        "body_lines": page["lines"],
        "action_hint": action_hint,
    }


def truncate_for_display(text: str, max_chars: int, *, force_ellipsis: bool = False) -> str:
    if len(text) <= max_chars and not force_ellipsis:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return f"{text[: max_chars - 3]}..."


def wrap_display_line(text: str, max_line_chars: int) -> list[str]:
    if text == "":
        return [""]
    wrapped = []
    position = 0
    while position < len(text):
        remaining = len(text) - position
        if remaining <= max_line_chars:
            wrapped.append(text[position:])
            break
        cut = max_line_chars
        space = text.rfind(" ", position, position + max_line_chars)
        if space >= position:
            cut = space - position
            if cut == 0:
                cut = max_line_chars
        wrapped.append(text[position : position + cut])
        position += cut
        while position < len(text) and text[position] == " ":
            position += 1
    return wrapped


def bounded_display_body_lines(lines: list[str], limits: dict) -> list[str]:
    wrapped = []
    for line in lines:
        wrapped.extend(wrap_display_line(str(line), limits["max_line_chars"]))
    if len(wrapped) > limits["max_body_lines"]:
        wrapped = wrapped[: limits["max_body_lines"]]
        wrapped[-1] = truncate_for_display(
            wrapped[-1],
            limits["max_line_chars"],
            force_ellipsis=True,
        )
    return [truncate_for_display(line, limits["max_line_chars"]) for line in wrapped]


def display_frame_for_page(page: dict, page_index: int, total_pages: int, limits: dict) -> dict:
    action_hint = "Next" if page["action"] == "next" else "Approve / Reject"
    return {
        "title": truncate_for_display(str(page["title"]), limits["max_title_chars"]),
        "page_indicator": f"Page {page_index + 1}/{total_pages}",
        "body_lines": bounded_display_body_lines(page["lines"], limits),
        "action_hint": action_hint,
    }


def check_display_limits(path: str, limits: object, errors: list[str]) -> dict | None:
    if not isinstance(limits, dict):
        errors.append(f"{path}: limits must be an object")
        return None
    required = ("max_title_chars", "max_body_lines", "max_line_chars")
    if any(not isinstance(limits.get(field), int) or limits[field] <= 0 for field in required):
        errors.append(f"{path}: limits must contain positive integer display bounds")
        return None
    return {field: limits[field] for field in required}


def check_review_display_frame_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/review-display-frames/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "review-display-frame-v0":
        errors.append(f"{vector_path}: format mismatch")

    source_name = vector.get("source_review_vector")
    if not isinstance(source_name, str):
        errors.append(f"{vector_path}: source_review_vector must be a string")
        return
    source = load_required_json(f"vectors/review/{source_name}.json", errors)
    if source is None:
        return
    review = source.get("review")
    if not isinstance(review, dict):
        errors.append(f"{vector_path}: source review must be an object")
        return
    pages = expected_review_pages(review)

    page_index = vector.get("page_index")
    if not isinstance(page_index, int) or page_index < 0 or page_index >= len(pages):
        errors.append(f"{vector_path}: page_index out of range")
        return
    limits = check_display_limits(vector_path, vector.get("limits"), errors)
    if limits is None:
        return
    expected = display_frame_for_page(pages[page_index], page_index, len(pages), limits)
    if vector.get("frame") != expected:
        errors.append(f"{vector_path}: frame mismatch")


DISPLAY_SAFE_ASCII = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " !\"#$%&'()*+,-./:;<=>?@[\\]_{|}~"
)


def display_safe_text(text: str) -> str:
    out = []
    for char in text:
        codepoint = ord(char)
        if char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif char == "\r":
            out.append("\\r")
        elif char == "\b":
            out.append("\\b")
        elif char == "\f":
            out.append("\\f")
        elif codepoint <= 0x7f and char in DISPLAY_SAFE_ASCII:
            out.append(char)
        else:
            out.append(f"U+{codepoint:04X}")
    return "".join(out)


def split_exact_display_lines(text: str, width: int) -> list[str]:
    if text == "":
        return [""]
    return [text[index:index + width] for index in range(0, len(text), width)]


def append_detail_value_lines(lines: list[str], styles: list[str], value: str, width: int) -> None:
    for line in split_exact_display_lines(value, width):
        lines.append(line)
        styles.append("value")


def append_detail_tag_item_lines(lines: list[str], styles: list[str], value: str, width: int) -> None:
    if value == "":
        return
    safe_value = display_safe_text(value)
    continuation_indent = "  "
    continuation_width = width - len(continuation_indent) if width > len(continuation_indent) else width
    position = 0
    first_line = True
    while position < len(safe_value):
        line_width = width if first_line else continuation_width
        line = safe_value[position:position + line_width]
        if not first_line and width > len(continuation_indent):
            line = continuation_indent + line
        lines.append(line)
        styles.append("value")
        position += line_width
        first_line = False


def detail_event_lines(review: dict, limits: dict) -> tuple[list[str], list[str]]:
    lines = [
        f"Kind {review['kind']}",
        f"Created {review['created_at']}",
        "Author",
    ]
    styles = ["meta", "meta", "meta"]
    append_detail_tag_item_lines(lines, styles, str(review["author_pubkey"]), limits["max_compact_line_chars"])
    return lines, styles


def detail_content_lines(review: dict, limits: dict) -> tuple[list[str], list[str]]:
    content = str(review["content"])
    if content == "":
        return ["empty content"], ["meta"]
    safe_content = display_safe_text(content)
    if len(safe_content) <= limits["max_compact_line_chars"]:
        return [safe_content], ["normal"]
    lines = [f"bytes: {utf8_size(content)}"]
    styles = ["meta"]
    append_detail_value_lines(lines, styles, safe_content, limits["max_compact_line_chars"])
    return lines, styles


def detail_tag_lines(review: dict, limits: dict) -> tuple[list[str], list[str]]:
    tags = review["tags"]
    if not tags:
        return ["No tags"], ["normal"]
    lines: list[str] = []
    styles: list[str] = []
    for tag_index, tag in enumerate(tags, start=1):
        lines.append(f"Tag {tag_index}/{len(tags)}")
        styles.append("meta")
        if tag:
            for item in tag:
                append_detail_tag_item_lines(lines, styles, str(item), limits["max_compact_line_chars"])
        else:
            lines.append("empty tag")
            styles.append("value")
    return lines, styles


def detail_page_indicator(
    page_index: int,
    page_count: int,
    first_line: int,
    last_line: int,
    line_count: int,
) -> str:
    base = f"Page {page_index}/{page_count}"
    if line_count == 0 or (first_line == 1 and last_line >= line_count):
        return base
    return f"{base} Lines {first_line}-{last_line}/{line_count}"


def append_detail_pages(
    pages: list[dict],
    title: str,
    lines: list[str],
    styles: list[str],
    limits: dict,
    logical_page_index: int,
    logical_page_count: int,
) -> None:
    lines_per_screen = limits["max_compact_body_lines"] if styles else limits["max_body_lines"]
    total = len(lines) if lines else 1
    position = 0
    while position < total:
        first_position = position
        body_lines: list[str] = []
        body_styles: list[str] = []
        for _ in range(lines_per_screen):
            if position >= len(lines):
                break
            body_lines.append(lines[position])
            body_styles.append(styles[position] if position < len(styles) else "normal")
            position += 1
        if not body_lines:
            body_lines = [""]
            body_styles = ["normal"]
            position = total
        pages.append(
            {
                "title": title,
                "lines": body_lines,
                "action": "next",
                "page_indicator": detail_page_indicator(
                    logical_page_index,
                    logical_page_count,
                    first_position + 1,
                    position,
                    total,
                ),
                "body_line_styles": body_styles,
                "logical_page_id": title,
            }
        )
        if position >= total:
            break


def expected_review_detail_pages(review: dict, limits: dict) -> list[dict]:
    pages: list[dict] = []
    append_detail_pages(pages, "Event", *detail_event_lines(review, limits), limits, 1, 4)
    append_detail_pages(pages, "Content", *detail_content_lines(review, limits), limits, 2, 4)
    append_detail_pages(pages, "Tags", *detail_tag_lines(review, limits), limits, 3, 4)
    pages.append(
        {
            "title": "Decision",
            "lines": ["Approve signing only if all pages match."],
            "action": "approve_or_reject",
            "page_indicator": "Page 4/4",
            "body_line_styles": [],
            "logical_page_id": "Decision",
        }
    )
    return pages


def check_review_detail_page_contract(vector_path: str, pages: object, errors: list[str]) -> None:
    if not isinstance(pages, list):
        errors.append(f"{vector_path}: pages must be an array")
        return
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict):
            errors.append(f"{vector_path}: pages[{page_index}] must be an object")
            continue
        lines = page.get("lines")
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            errors.append(f"{vector_path}: pages[{page_index}].lines must be an array of strings")
            continue
        styles = page.get("body_line_styles")
        if styles is None:
            errors.append(f"{vector_path}: pages[{page_index}].body_line_styles is required")
            continue
        if not isinstance(styles, list) or not all(isinstance(style, str) for style in styles):
            errors.append(f"{vector_path}: pages[{page_index}].body_line_styles must be an array of strings")
            continue
        if styles and len(styles) != len(lines):
            errors.append(f"{vector_path}: pages[{page_index}].body_line_styles length must match lines")
        unknown_styles = sorted({style for style in styles if style not in REVIEW_DETAIL_BODY_LINE_STYLES})
        if unknown_styles:
            errors.append(f"{vector_path}: pages[{page_index}].body_line_styles contain unknown styles {unknown_styles}")
        for line_index, (line, style) in enumerate(zip(lines, styles)):
            if line.startswith("  ") and style != "value":
                errors.append(
                    f"{vector_path}: pages[{page_index}].lines[{line_index}] continuation lines must use value style"
                )


def check_review_detail_page_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/review-detail-pages/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "review-detail-pages-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("display_profile") != "ascii-safe-codepoint-fallback-v0":
        errors.append(f"{vector_path}: display_profile mismatch")

    source_name = vector.get("source_review_vector")
    if not isinstance(source_name, str):
        errors.append(f"{vector_path}: source_review_vector must be a string")
        return
    source = load_required_json(f"vectors/review/{source_name}.json", errors)
    if source is None:
        return
    review = source.get("review")
    if not isinstance(review, dict):
        errors.append(f"{vector_path}: source review must be an object")
        return

    expected_screen = expected_screen_review(source["request"])
    screen_name = vector.get("source_screen_review_vector")
    if screen_name is not None:
        if not isinstance(screen_name, str):
            errors.append(f"{vector_path}: source_screen_review_vector must be a string")
            return
        screen = load_required_json(f"vectors/review-screens/{screen_name}.json", errors)
        if screen is None:
            return
        if screen.get("screen_review") != expected_screen:
            errors.append(f"{vector_path}: source_screen_review_vector mismatch")
    if vector.get("approval_digest") != expected_screen.get("approval_digest"):
        errors.append(f"{vector_path}: approval_digest mismatch")

    limits = check_display_limits(vector_path, vector.get("limits"), errors)
    if limits is None:
        return
    for field in ("max_compact_body_lines", "max_compact_line_chars"):
        if not isinstance(vector["limits"].get(field), int) or vector["limits"][field] <= 0:
            errors.append(f"{vector_path}: limits must contain positive integer compact display bounds")
            return
        limits[field] = vector["limits"][field]

    expected = expected_review_detail_pages(review, limits)
    pages = vector.get("pages")
    check_review_detail_page_contract(vector_path, pages, errors)
    if pages != expected:
        errors.append(f"{vector_path}: pages mismatch")


def expected_review_transcript(screen_review: dict, buttons: list[str], errors: list[str], rel: str) -> list[dict]:
    pages = screen_review["pages"]
    page_index = 0
    terminal = False
    transcript = []
    for button in buttons:
        if terminal:
            errors.append(f"vectors/review-transcripts/{rel}.json: button after terminal decision")
            break
        if button not in {"next", "approve", "reject"}:
            errors.append(f"vectors/review-transcripts/{rel}.json: unsupported button {button!r}")
            break

        frame = frame_for_page(pages[page_index], page_index, len(pages))
        decision = None
        approved = False
        if button == "next":
            if page_index + 1 < len(pages):
                page_index += 1
        elif button == "reject":
            decision = False
            terminal = True
        else:
            if page_index != len(pages) - 1:
                errors.append(f"vectors/review-transcripts/{rel}.json: approval before final page")
                break
            decision = True
            approved = True
            terminal = True

        transcript.append(
            {
                "frame": frame,
                "button": button,
                "decision": decision,
                "approved_for_signing": approved,
            }
        )
    return transcript


def detail_frame_for_page(page: dict, logical_page_has_scroll: bool, limits: dict) -> dict:
    action_hint = "Next" if page["action"] == "next" else "Approve / Reject"
    if logical_page_has_scroll and action_hint == "Next":
        action_hint = "Next/Scroll"
    lines, styles = bounded_detail_frame_body_lines(page, limits)
    return {
        "title": page["title"],
        "page_indicator": page["page_indicator"],
        "body_lines": lines,
        "action_hint": action_hint,
        "body_line_styles": styles,
    }


def detail_frame_compact_style(style: str) -> bool:
    return style in {"meta", "value"}


def bounded_detail_frame_body_lines(page: dict, limits: dict) -> tuple[list[str], list[str]]:
    wrapped: list[str] = []
    styles: list[str] = []
    has_compact_style = False
    page_styles = page.get("body_line_styles", [])
    for index, line in enumerate(page.get("lines", [])):
        style = page_styles[index] if index < len(page_styles) else "normal"
        has_compact_style = has_compact_style or detail_frame_compact_style(style)
        width = limits["max_compact_line_chars"] if detail_frame_compact_style(style) else limits["max_line_chars"]
        parts = split_exact_display_lines(str(line), width)
        wrapped.extend(parts)
        styles.extend([style] * len(parts))
    max_lines = limits["max_compact_body_lines"] if has_compact_style else limits["max_body_lines"]
    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
        styles = styles[:max_lines]
        width = (
            limits["max_compact_line_chars"]
            if styles and detail_frame_compact_style(styles[-1])
            else limits["max_line_chars"]
        )
        wrapped[-1] = truncate_for_display(wrapped[-1], width, force_ellipsis=True)
    for index, line in enumerate(wrapped):
        width = (
            limits["max_compact_line_chars"]
            if index < len(styles) and detail_frame_compact_style(styles[index])
            else limits["max_line_chars"]
        )
        wrapped[index] = truncate_for_display(line, width)
    return wrapped, styles


def detail_logical_ranges(pages: list[dict]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    current_id: str | None = None
    for index, page in enumerate(pages):
        page_id = str(page.get("logical_page_id") or f"__page_{index}")
        if page_id != current_id:
            ranges.append((index, 1))
            current_id = page_id
        else:
            start, count = ranges[-1]
            ranges[-1] = (start, count + 1)
    return ranges


def expected_detail_review_transcript(
    detail_pages: list[dict],
    buttons: list[str],
    limits: dict,
    errors: list[str],
    rel: str,
) -> list[dict]:
    logical_ranges = detail_logical_ranges(detail_pages)
    logical_page_index = 0
    scroll_page_offset = 0
    seen_logical_pages = {0}
    terminal = False
    transcript = []
    for button in buttons:
        if terminal:
            errors.append(f"vectors/review-transcripts/{rel}.json: button after terminal decision")
            break
        if button not in {"next", "scroll", "approve", "reject"}:
            errors.append(f"vectors/review-transcripts/{rel}.json: unsupported button {button!r}")
            break

        start, count = logical_ranges[logical_page_index]
        page_index = start + scroll_page_offset
        page = detail_pages[page_index]
        frame = detail_frame_for_page(page, count > 1, limits)
        decision = None
        approved = False
        if button == "next":
            logical_page_index = (logical_page_index + 1) % len(logical_ranges)
            scroll_page_offset = 0
            seen_logical_pages.add(logical_page_index)
        elif button == "scroll":
            if count > 1:
                scroll_page_offset = (scroll_page_offset + 1) % count
        elif button == "reject":
            decision = False
            terminal = True
        else:
            if page.get("action") != "approve_or_reject" or len(seen_logical_pages) != len(logical_ranges):
                errors.append(f"vectors/review-transcripts/{rel}.json: approval before final page")
                break
            decision = True
            approved = True
            terminal = True

        transcript.append(
            {
                "frame": frame,
                "button": button,
                "decision": decision,
                "approved_for_signing": approved,
            }
        )
    return transcript


def check_review_transcript_vector(rel: str, errors: list[str]) -> None:
    vector = load_required_json(f"vectors/review-transcripts/{rel}.json", errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"vectors/review-transcripts/{rel}.json: name mismatch")
    if vector.get("format") != "qr-review-transcript-v0":
        errors.append(f"vectors/review-transcripts/{rel}.json: format mismatch")

    source_vector_name = vector.get("source_vector")
    if not isinstance(source_vector_name, str):
        errors.append(f"vectors/review-transcripts/{rel}.json: source_vector must be a string")
        return
    source_vector = load_required_json(f"vectors/transports/{source_vector_name}.json", errors)
    if source_vector is None:
        return

    review_mode = vector.get("review_mode", "screen")
    if review_mode not in {"screen", "detail"}:
        errors.append(f"vectors/review-transcripts/{rel}.json: review_mode must be screen or detail")
        return

    request = vector.get("request")
    if not isinstance(request, dict):
        errors.append(f"vectors/review-transcripts/{rel}.json: request must be an object")
        return
    check_request_shape(Path(f"vectors/review-transcripts/{rel}.json"), request, errors)
    if request != source_vector.get("decoded"):
        errors.append(f"vectors/review-transcripts/{rel}.json: request must match source QR vector")
    if vector.get("qr_envelope") != source_vector.get("envelope"):
        errors.append(f"vectors/review-transcripts/{rel}.json: qr_envelope mismatch")

    buttons = vector.get("buttons")
    if not isinstance(buttons, list) or not all(isinstance(button, str) for button in buttons):
        errors.append(f"vectors/review-transcripts/{rel}.json: buttons must be a string list")
        return
    if review_mode == "screen":
        screen_review_name = vector.get("screen_review_vector")
        if not isinstance(screen_review_name, str):
            errors.append(f"vectors/review-transcripts/{rel}.json: screen_review_vector must be a string")
            return
        screen_vector = load_required_json(f"vectors/review-screens/{screen_review_name}.json", errors)
        if screen_vector is None:
            return
        if request != screen_vector.get("request"):
            errors.append(f"vectors/review-transcripts/{rel}.json: request must match review-screen vector")
        if vector.get("approval_digest") != screen_vector.get("screen_review", {}).get("approval_digest"):
            errors.append(f"vectors/review-transcripts/{rel}.json: approval_digest mismatch")
        expected = expected_review_transcript(screen_vector["screen_review"], buttons, errors, rel)
    else:
        detail_review_name = vector.get("detail_review_vector")
        if not isinstance(detail_review_name, str):
            errors.append(f"vectors/review-transcripts/{rel}.json: detail_review_vector must be a string")
            return
        detail_vector = load_required_json(f"vectors/review-detail-pages/{detail_review_name}.json", errors)
        if detail_vector is None:
            return
        source_review_name = detail_vector.get("source_review_vector")
        source_review = load_required_json(f"vectors/review/{source_review_name}.json", errors)
        if source_review is None:
            return
        if request != source_review.get("request"):
            errors.append(f"vectors/review-transcripts/{rel}.json: request must match detail review source")
        if vector.get("approval_digest") != detail_vector.get("approval_digest"):
            errors.append(f"vectors/review-transcripts/{rel}.json: approval_digest mismatch")
        pages = detail_vector.get("pages")
        check_review_detail_page_contract(f"vectors/review-transcripts/{rel}.json", pages, errors)
        if not isinstance(pages, list):
            return
        limits = detail_vector.get("limits")
        if not isinstance(limits, dict):
            errors.append(f"vectors/review-transcripts/{rel}.json: detail vector limits must be an object")
            return
        expected = expected_detail_review_transcript(pages, buttons, limits, errors, rel)
    if vector.get("transcript") != expected:
        errors.append(f"vectors/review-transcripts/{rel}.json: transcript mismatch")


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


NIP46_PERMISSION_METHODS = {
    "sign_event",
    "nip04_encrypt",
    "nip04_decrypt",
    "nip44_encrypt",
    "nip44_decrypt",
    "get_public_key",
    "ping",
    "switch_relays",
}
NIP46_CONNECTION_URI_PARAMS = {"relay", "secret", "perms", "name", "url", "image"}
NIP46_RELAY_DIRECTIONS = {"client_to_remote_signer", "remote_signer_to_client"}
NIP46_SESSION_PHASES = {"approved_pending_ack"}
NIP46_SESSION_FALSE_FLAGS = {
    "secret_value_stored",
    "contains_secret_material",
    "derives_nip44_key",
    "acknowledges_connect",
    "opens_relay",
    "creates_grants",
    "dispatches_signer",
    "stores_production_secrets",
    "persists_session_state",
}
NIP46_SESSION_SECRET_FIELD_NAMES = {
    "secret",
    "shared_secret",
    "session_secret",
    "nip44_key",
    "secret_key",
    "private_key",
    "nsec",
    "mnemonic",
    "seed",
    "passphrase",
}
NIP46_SESSION_ACTIVE_PHASES = {"connect_ack", "session_active", "session_closed"}
NIP46_SESSION_ACTIVE_ALWAYS_FALSE = {
    "secret_value_stored",
    "contains_secret_material",
    "stores_production_secrets",
}
# Exact expected lifecycle-flag values per phase (machine-checkable).
NIP46_SESSION_ACTIVE_PHASE_FLAGS = {
    "connect_ack": {"acknowledges_connect": True, "derives_nip44_key": True, "opens_relay": True, "dispatches_signer": False},
    "session_active": {"acknowledges_connect": True, "derives_nip44_key": True, "opens_relay": True, "dispatches_signer": True},
    "session_closed": {"acknowledges_connect": True, "derives_nip44_key": False, "opens_relay": False, "dispatches_signer": False},
}


def parse_nip46_permissions(value: str, vector_path: str, errors: list[str]) -> list[dict]:
    if value.strip() == "":
        return []
    parsed = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            errors.append(f"{vector_path}: NIP-46 permission entries must be non-empty")
            continue
        parts = item.split(":")
        if len(parts) > 2 or not parts[0]:
            errors.append(f"{vector_path}: NIP-46 permission format is invalid")
            continue
        method = parts[0]
        parameter = parts[1] if len(parts) == 2 else None
        if method == "connect":
            errors.append(f"{vector_path}: NIP-46 permissions must not request connect")
            continue
        if method not in NIP46_PERMISSION_METHODS:
            errors.append(f"{vector_path}: unsupported permission method: {method}")
            continue
        if method == "sign_event" and parameter is not None:
            if not parameter.isdigit():
                errors.append(f"{vector_path}: sign_event permission kind must be numeric")
                continue
            event_kind = int(parameter)
            if event_kind > MAX_SAFE_INTEGER:
                errors.append(f"{vector_path}: sign_event permission kind must be a safe non-negative integer")
                continue
            parsed.append({"method": method, "parameter": parameter, "event_kind": event_kind})
            continue
        if parameter is not None:
            errors.append(f"{vector_path}: permission method does not accept a parameter: {method}")
            continue
        parsed.append({"method": method})
    return parsed


def single_query_param(query: dict[str, list[str]], name: str, vector_path: str, errors: list[str]) -> str | None:
    values = query.get(name, [])
    if len(values) > 1:
        errors.append(f"{vector_path}: NIP-46 connection URI {name} must appear at most once")
        return None
    return values[0] if values else None


def normalized_websocket_relay(
    value: str,
    vector_path: str,
    errors: list[str],
    context: str = "NIP-46 connection URI relay",
) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme != "wss" or parsed.username or parsed.password or parsed.fragment:
        errors.append(f"{vector_path}: {context} must be a wss URL without credentials or fragment")
        return None
    if not parsed.hostname:
        errors.append(f"{vector_path}: {context} host is required")
        return None
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def normalized_http_url(value: str, name: str, vector_path: str, errors: list[str]) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.fragment:
        errors.append(f"{vector_path}: NIP-46 connection URI {name} must be an http(s) URL without credentials or fragment")
        return None
    if not parsed.hostname:
        errors.append(f"{vector_path}: NIP-46 connection URI {name} host is required")
        return None
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def normalized_nip46_auth_url(value: str, vector_path: str, errors: list[str]) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.fragment:
        errors.append(f"{vector_path}: NIP-46 auth challenge URL must be an http(s) URL without credentials or fragment")
        return None
    if not parsed.hostname:
        errors.append(f"{vector_path}: NIP-46 auth challenge URL host is required")
        return None
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def expected_nip46_connection_uri_descriptor(vector_path: str, uri: object, errors: list[str]) -> dict | None:
    if not isinstance(uri, str) or not uri or uri.strip() != uri:
        errors.append(f"{vector_path}: NIP-46 connection URI must be a non-empty trimmed string")
        return None
    parsed = urlparse(uri)
    if parsed.scheme not in {"bunker", "nostrconnect"}:
        errors.append(f"{vector_path}: NIP-46 connection URI scheme must be bunker or nostrconnect")
        return None
    if parsed.username or parsed.password or parsed.path or parsed.fragment:
        errors.append(f"{vector_path}: NIP-46 connection URI must not include credentials, path, or fragment")
        return None
    if not parsed.hostname or not HEX32_RE.fullmatch(parsed.hostname):
        errors.append(f"{vector_path}: NIP-46 connection URI pubkey must be 32-byte lowercase hex")
        return None

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query: dict[str, list[str]] = {}
    for key, value in pairs:
        if key not in NIP46_CONNECTION_URI_PARAMS:
            errors.append(f"{vector_path}: NIP-46 connection URI unsupported query parameter: {key}")
            continue
        query.setdefault(key, []).append(value)

    relays = [normalized_websocket_relay(value, vector_path, errors) for value in query.get("relay", [])]
    if not relays:
        errors.append(f"{vector_path}: NIP-46 connection URI requires at least one relay")
    relay_values = [relay for relay in relays if relay is not None]
    if len(set(relay_values)) != len(relay_values):
        errors.append(f"{vector_path}: NIP-46 connection URI relays must be unique")

    secret = single_query_param(query, "secret", vector_path, errors)
    perms = single_query_param(query, "perms", vector_path, errors)
    name = single_query_param(query, "name", vector_path, errors)
    client_url = single_query_param(query, "url", vector_path, errors)
    image = single_query_param(query, "image", vector_path, errors)
    if secret == "":
        errors.append(f"{vector_path}: NIP-46 connection URI secret must be non-empty when present")
    if errors and any(error.startswith(f"{vector_path}: NIP-46 connection URI") for error in errors):
        return None

    descriptor = {
        "format": "nsealr-nip46-connection-uri-v0",
        "kind": parsed.scheme,
        "relays": relay_values,
        "secret_present": secret is not None and secret != "",
        "requested_permissions": [],
        "starts_relay_session": False,
        "creates_grants": False,
        "stores_production_secrets": False,
        "exposes_secret": False,
    }

    if parsed.scheme == "bunker":
        if perms is not None or name is not None or client_url is not None or image is not None:
            errors.append(f"{vector_path}: NIP-46 bunker URI must not include client metadata or requested permissions")
            return None
        descriptor["remote_signer_pubkey"] = parsed.hostname
        return descriptor

    if secret is None or secret == "":
        errors.append(f"{vector_path}: NIP-46 nostrconnect URI requires a secret")
        return None
    descriptor["client_pubkey"] = parsed.hostname
    descriptor["requested_permissions"] = parse_nip46_permissions(perms or "", vector_path, errors)
    metadata = {}
    if name is not None:
        metadata["name"] = name
    if client_url is not None:
        normalized_url = normalized_http_url(client_url, "url", vector_path, errors)
        if normalized_url is not None:
            metadata["url"] = normalized_url
    if image is not None:
        normalized_image = normalized_http_url(image, "image", vector_path, errors)
        if normalized_image is not None:
            metadata["image"] = normalized_image
    if metadata:
        descriptor["client_metadata"] = metadata
    return descriptor


def decode_unpadded_base64url(payload: object, vector_path: str, label: str, errors: list[str]) -> bytes | None:
    if not isinstance(payload, str) or not payload:
        errors.append(f"{vector_path}: {label} payload must be a non-empty string")
        return None
    if "=" in payload:
        errors.append(f"{vector_path}: {label} payload must be unpadded base64url")
        return None
    if not B64URL_RE.fullmatch(payload):
        errors.append(f"{vector_path}: {label} payload must be base64url")
        return None
    padding = "=" * ((4 - len(payload) % 4) % 4)
    try:
        return base64.b64decode(
            f"{payload}{padding}".encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except binascii.Error:
        errors.append(f"{vector_path}: {label} payload must decode as base64url")
        return None


def check_qr_envelope_payload(vector_path: str, envelope: object, errors: list[str]) -> None:
    limits = implementation_limit_values()
    if not isinstance(envelope, str):
        errors.append(f"{vector_path}: QR envelope must be a string")
        return
    if not envelope.startswith(QR_PREFIX):
        errors.append(f"{vector_path}: QR envelope requires nsealr1 prefix")
        return
    payload = envelope[len(QR_PREFIX) :]
    decoded = decode_unpadded_base64url(payload, vector_path, "QR envelope", errors)
    if decoded is None:
        return
    if len(decoded) > limits["max_static_qr_decoded_json_bytes"]:
        errors.append(f"{vector_path}: QR decoded JSON exceeds max_static_qr_decoded_json_bytes")
    try:
        decoded_text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{vector_path}: QR envelope payload must be valid UTF-8")
        return
    try:
        decoded_json = json.loads(decoded_text)
    except json.JSONDecodeError:
        errors.append(f"{vector_path}: QR envelope payload must be JSON")
        return
    check_request_shape(Path(vector_path), decoded_json, errors)


def parse_animated_qr_frame(vector_path: str, frame: object, errors: list[str]) -> tuple[str, int, int, str] | None:
    limits = implementation_limit_values()
    if not isinstance(frame, str):
        errors.append(f"{vector_path}: animated QR frame must be a string")
        return None
    if not frame.startswith(ANIMATED_QR_PREFIX):
        errors.append(f"{vector_path}: animated QR frame requires nsealr1a prefix")
        return None
    parts = frame.split(":")
    if len(parts) != 5 or parts[0] != "nsealr1a":
        errors.append(f"{vector_path}: animated QR frame is malformed")
        return None
    digest, index_total, chunk, checksum = parts[1], parts[2], parts[3], parts[4]
    if not HEX32_RE.fullmatch(digest):
        errors.append(f"{vector_path}: animated QR digest must be 32-byte lowercase hex")
        return None
    if not HEX8_RE.fullmatch(checksum):
        errors.append(f"{vector_path}: animated QR checksum must be 8-byte lowercase hex")
        return None
    if "/" not in index_total:
        errors.append(f"{vector_path}: animated QR index must use index/total")
        return None
    index_text, total_text = index_total.split("/", 1)
    if not index_text.isdecimal() or not total_text.isdecimal():
        errors.append(f"{vector_path}: animated QR index and total must be decimal")
        return None
    index = int(index_text)
    total = int(total_text)
    if index < 1 or total < 1 or index > total:
        errors.append(f"{vector_path}: animated QR frame index is out of range")
        return None
    if total > limits["max_animated_qr_frame_count"]:
        errors.append(f"{vector_path}: animated QR frame count exceeds max_animated_qr_frame_count")
    if not B64URL_RE.fullmatch(chunk):
        errors.append(f"{vector_path}: animated QR chunk must be unpadded base64url")
        return None
    if len(chunk) > limits["max_animated_qr_frame_payload_chars"]:
        errors.append(f"{vector_path}: animated QR chunk exceeds max_animated_qr_frame_payload_chars")
    expected_checksum = animated_qr_checksum(digest, index, total, chunk)
    if checksum != expected_checksum:
        errors.append(f"{vector_path}: animated QR frame checksum mismatch")
    return digest, index, total, chunk


def check_animated_qr_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/transports/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    limits = implementation_limit_values()
    if vector.get("format") != "qr-animated-envelope-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("prefix") != ANIMATED_QR_PREFIX:
        errors.append(f"{vector_path}: prefix mismatch")
    decoded = vector.get("decoded")
    if not isinstance(decoded, dict):
        errors.append(f"{vector_path}: decoded must be an object")
        return
    decoded_bytes = compact_json(decoded).encode("utf-8")
    if len(decoded_bytes) > limits["max_animated_qr_decoded_json_bytes"]:
        errors.append(f"{vector_path}: decoded JSON exceeds max_animated_qr_decoded_json_bytes")
    digest = sha256_hex(decoded_bytes)
    if vector.get("decoded_json_sha256") != digest:
        errors.append(f"{vector_path}: decoded_json_sha256 mismatch")
    payload = base64.urlsafe_b64encode(decoded_bytes).decode("ascii").rstrip("=")
    if vector.get("payload_base64url") != payload:
        errors.append(f"{vector_path}: payload_base64url mismatch")
    chunk_size = vector.get("chunk_size_chars")
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        errors.append(f"{vector_path}: chunk_size_chars must be a positive integer")
        return
    if chunk_size > limits["max_animated_qr_frame_payload_chars"]:
        errors.append(f"{vector_path}: chunk_size_chars exceeds max_animated_qr_frame_payload_chars")
    expected_frames = animated_qr_frames(decoded, chunk_size)
    if vector.get("frames") != expected_frames:
        errors.append(f"{vector_path}: frames mismatch")
    frames = vector.get("frames")
    if not isinstance(frames, list) or not frames:
        errors.append(f"{vector_path}: frames must be a non-empty list")
        return
    parsed = [parse_animated_qr_frame(vector_path, frame, errors) for frame in frames]
    if any(item is None for item in parsed):
        return
    parsed_frames = [item for item in parsed if item is not None]
    digests = {item[0] for item in parsed_frames}
    totals = {item[2] for item in parsed_frames}
    if digests != {digest}:
        errors.append(f"{vector_path}: frame digest set mismatch")
    if len(totals) != 1:
        errors.append(f"{vector_path}: frame total mismatch")
        return
    total = totals.pop()
    indices = sorted(item[1] for item in parsed_frames)
    if indices != list(range(1, total + 1)):
        errors.append(f"{vector_path}: frames must be unique and contiguous")
    reassembled_payload = "".join(chunk for _, _, _, chunk in sorted(parsed_frames, key=lambda item: item[1]))
    if reassembled_payload != payload:
        errors.append(f"{vector_path}: reassembled payload mismatch")
    reassembled = decode_unpadded_base64url(reassembled_payload, vector_path, "animated QR", errors)
    if reassembled is not None and sha256_hex(reassembled) != digest:
        errors.append(f"{vector_path}: reassembled decoded digest mismatch")
    check_response_shape(Path(vector_path), decoded, errors)


def check_static_qr_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/transports/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("format") != "qr-envelope-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("prefix") != QR_PREFIX:
        errors.append(f"{vector_path}: prefix mismatch")
    decoded = vector.get("decoded")
    if not isinstance(decoded, dict):
        errors.append(f"{vector_path}: decoded must be an object")
        return
    check_request_shape(Path(vector_path), decoded, errors)
    payload = base64url_json(decoded)
    if vector.get("payload_base64url") != payload:
        errors.append(f"{vector_path}: payload_base64url mismatch")
    if vector.get("envelope") != f"{QR_PREFIX}{payload}":
        errors.append(f"{vector_path}: envelope mismatch")


def check_serial_frame_payload(vector_path: str, frame: object, errors: list[str]) -> None:
    limits = implementation_limit_values()
    if not isinstance(frame, str):
        errors.append(f"{vector_path}: serial frame must be a string")
        return
    if utf8_size(frame) > limits["max_serial_frame_bytes"]:
        errors.append(f"{vector_path}: serial frame exceeds max_serial_frame_bytes")
    if not frame.startswith(SERIAL_PREFIX):
        errors.append(f"{vector_path}: serial frame requires nsealr1f prefix")
        return
    if not frame.endswith("\n"):
        errors.append(f"{vector_path}: serial frame must end with newline")
    body = frame[len(SERIAL_PREFIX) :].rstrip("\n")
    parts = body.split(":")
    if len(parts) != 3:
        errors.append(f"{vector_path}: serial frame must contain type, payload, and checksum")
        return
    frame_type, payload, checksum = parts
    if frame_type not in {"request", "response", "error"}:
        errors.append(f"{vector_path}: unsupported serial frame type")
    if not re.fullmatch(r"^[0-9a-f]{16}$", checksum):
        errors.append(f"{vector_path}: serial checksum must be 16 lowercase hex characters")
    expected_checksum = serial_checksum(frame_type, payload)
    if checksum != expected_checksum:
        errors.append(f"{vector_path}: serial checksum mismatch")
    decoded = decode_unpadded_base64url(payload, vector_path, "serial frame", errors)
    if decoded is None:
        return
    try:
        decoded_text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{vector_path}: serial frame payload must be valid UTF-8")
        return
    try:
        decoded_json = json.loads(decoded_text)
    except json.JSONDecodeError:
        errors.append(f"{vector_path}: serial frame payload must be JSON")
        return
    if frame_type == "request":
        check_request_shape(Path(vector_path), decoded_json, errors)
    elif frame_type == "response":
        check_response_shape(Path(vector_path), decoded_json, errors)


def check_invalid_nip46_payload(vector_path: str, vector: dict, errors: list[str]) -> None:
    message = check_nip46_request_message(vector_path, vector.get("request_message"), errors)
    if message is None:
        return
    method = message.get("method")
    if method == "connect":
        expected_nip46_connect_intent(vector_path, message, errors)
        return
    expected_nip46_permission_requirement(vector_path, message, errors)


def check_invalid_nip46_connection_uri(vector_path: str, vector: dict, errors: list[str]) -> None:
    expected_nip46_connection_uri_descriptor(vector_path, vector.get("uri"), errors)


def check_invalid_nip46_connection_token_response(vector_path: str, vector: dict, errors: list[str]) -> None:
    token_response = vector.get("connection_token_response")
    if not isinstance(token_response, dict):
        errors.append(f"{vector_path}: connection_token_response must be an object")
        return
    source_vector = {
        "uri": token_response.get("connection_uri"),
        "secret_probe": token_response.get("secret_probe"),
    }
    expected_nip46_connection_token_response(
        vector_path,
        source_vector,
        token_response.get("response_step"),
        errors,
    )


def expected_nip46_relay_event_envelope(
    vector_path: str,
    event: object,
    direction: object,
    errors: list[str],
) -> dict | None:
    if direction not in NIP46_RELAY_DIRECTIONS:
        errors.append(f"{vector_path}: NIP-46 relay event direction is invalid")
        return None
    if not isinstance(event, dict):
        errors.append(f"{vector_path}: NIP-46 relay event must be an object")
        return None
    if event.get("kind") != 24133:
        errors.append(f"{vector_path}: NIP-46 relay event kind must be 24133")
    sender = event.get("pubkey")
    if not isinstance(sender, str) or not HEX32_RE.fullmatch(sender):
        errors.append(f"{vector_path}: NIP-46 relay event pubkey must be 32-byte lowercase hex")
    content = event.get("content")
    if not isinstance(content, str) or content == "":
        errors.append(f"{vector_path}: NIP-46 relay event content must be a non-empty encrypted string")
    tags = event.get("tags")
    if not isinstance(tags, list):
        errors.append(f"{vector_path}: NIP-46 relay event tags must be an array")
        p_tags = []
    else:
        for tag in tags:
            if not isinstance(tag, list):
                errors.append(f"{vector_path}: NIP-46 relay event tag must be an array")
                continue
            if any(not isinstance(field, str) for field in tag):
                errors.append(f"{vector_path}: NIP-46 relay event tag fields must be strings")
        p_tags = [tag for tag in tags if isinstance(tag, list) and len(tag) >= 1 and tag[0] == "p"]
    if len(p_tags) != 1:
        errors.append(f"{vector_path}: NIP-46 relay event must include exactly one p tag")
        recipient = None
    else:
        p_tag = p_tags[0]
        recipient = p_tag[1] if len(p_tag) >= 2 else None
        if len(p_tag) != 2:
            errors.append(f"{vector_path}: NIP-46 relay event p tag must contain only marker and pubkey")
        if not isinstance(recipient, str) or not HEX32_RE.fullmatch(recipient):
            errors.append(f"{vector_path}: NIP-46 relay event p tag pubkey must be 32-byte lowercase hex")

    signed_field_names = ("id", "created_at", "sig")
    present_signed_fields = [name for name in signed_field_names if name in event]
    if present_signed_fields and len(present_signed_fields) != len(signed_field_names):
        errors.append(f"{vector_path}: NIP-46 relay event signed fields must be complete when present")
    if "id" in event and (not isinstance(event.get("id"), str) or not HEX32_RE.fullmatch(event.get("id", ""))):
        errors.append(f"{vector_path}: NIP-46 relay event id must be 32-byte lowercase hex")
    created_at = event.get("created_at")
    if "created_at" in event and (type(created_at) is not int or created_at < 0 or created_at > MAX_SAFE_INTEGER):
        errors.append(f"{vector_path}: NIP-46 relay event created_at must be a safe non-negative integer")
    if "sig" in event and (not isinstance(event.get("sig"), str) or not HEX64_RE.fullmatch(event.get("sig", ""))):
        errors.append(f"{vector_path}: NIP-46 relay event sig must be 64-byte lowercase hex")
    if len(present_signed_fields) == len(signed_field_names) and isinstance(sender, str) and HEX32_RE.fullmatch(sender):
        computed_id = event_id(event)
        if event.get("id") != computed_id:
            errors.append(f"{vector_path}: NIP-46 relay event id does not match NIP-01 canonical serialization")
        elif not verify_schnorr(sender, computed_id, event["sig"]):
            errors.append(f"{vector_path}: NIP-46 relay event signature is invalid")

    if errors and any(error.startswith(f"{vector_path}: NIP-46 relay event") for error in errors):
        return None
    signed_event_verified = bool(present_signed_fields)
    return {
        "format": "nsealr-nip46-relay-event-envelope-v0",
        "direction": direction,
        "sender_pubkey": sender,
        "recipient_pubkey": recipient,
        "encrypted_content": content,
        "has_signed_event_fields": bool(present_signed_fields),
        "event_id_verified": signed_event_verified,
        "event_signature_verified": signed_event_verified,
        "decrypts_content": False,
        "opens_relay": False,
        "creates_grants": False,
        "stores_production_secrets": False,
    }


def check_invalid_nip46_relay_event(vector_path: str, vector: dict, errors: list[str]) -> None:
    expected_nip46_relay_event_envelope(
        vector_path,
        vector.get("relay_event"),
        vector.get("direction", "client_to_remote_signer"),
        errors,
    )


def expected_nip46_relay_request_step(vector_path: str, vector: dict, errors: list[str]) -> dict | None:
    if vector.get("direction") != "client_to_remote_signer":
        errors.append(f"{vector_path}: NIP-46 relay request step direction must be client_to_remote_signer")
        return None
    envelope = expected_nip46_relay_event_envelope(
        vector_path,
        vector.get("event"),
        vector.get("direction"),
        errors,
    )
    message = check_nip46_request_message(vector_path, vector.get("decrypted_message"), errors)
    granted = vector.get("granted_permissions")
    if not isinstance(granted, list):
        errors.append(f"{vector_path}: relay request step granted_permissions must be a list")
        granted_permissions = []
    else:
        granted_permissions = [
            permission
            for permission in (
                normalized_nip46_approved_permission(vector_path, permission, errors) for permission in granted
            )
            if permission is not None
        ]
    if envelope is None or message is None:
        return None
    decision = expected_nip46_bridge_decision(vector_path, message, granted_permissions, errors)
    if decision is None:
        return None
    return {
        "format": "nsealr-nip46-relay-request-step-v0",
        "envelope": envelope,
        "message_id": message["id"],
        "bridge_decision": decision,
        "decrypts_content": False,
        "opens_relay": False,
        "creates_grants": False,
        "acknowledges_connect": False,
        "dispatches_signer": False,
        "stores_production_secrets": False,
        "persists_session_state": False,
    }


def check_nip46_relay_response_message(vector_path: str, message: object, errors: list[str]) -> dict | None:
    if not isinstance(message, dict):
        errors.append(f"{vector_path}: response_message must be an object")
        return None
    if json_utf8_size(message) > implementation_limit_values()["max_nip46_decrypted_message_json_bytes"]:
        errors.append(f"{vector_path}: NIP-46 decrypted response JSON exceeds max_nip46_decrypted_message_json_bytes")
    if not isinstance(message.get("id"), str) or not REQUEST_ID_RE.fullmatch(message["id"]):
        errors.append(f"{vector_path}: response_message id is invalid")
    unknown = sorted(set(message) - {"id", "result", "error"})
    if unknown:
        errors.append(f"{vector_path}: response_message contains unknown fields: {unknown}")
    has_result = "result" in message
    has_error = "error" in message
    if has_result == has_error:
        if has_result and message.get("result") == "auth_url" and isinstance(message.get("error"), str):
            normalized_auth_url = normalized_nip46_auth_url(message["error"], vector_path, errors)
            if normalized_auth_url is not None and normalized_auth_url != message["error"]:
                errors.append(f"{vector_path}: response_message auth_url must be normalized")
            return message
        errors.append(f"{vector_path}: response_message result and error together are only allowed for auth_url")
        return message
    if has_result and not isinstance(message.get("result"), str):
        errors.append(f"{vector_path}: response_message result must be a string")
    if has_error and not isinstance(message.get("error"), str):
        errors.append(f"{vector_path}: response_message error must be a string")
    return message


def exact_json_equal(left: object, right: object) -> bool:
    """JSON object order is irrelevant; array order and value types are exact."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact_json_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact_json_equal(x, y) for x, y in zip(left, right))
    return left == right


def strict_nip46_result_json(text: str) -> object:
    if len(text.encode("utf-8")) > implementation_limit_values()["max_nip46_decrypted_message_json_bytes"]:
        raise ValueError("NIP-46 result exceeds host UTF-8 byte limit")
    depth = 0
    quoted = False
    escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 32:
                raise ValueError("NIP-46 result exceeds host JSON depth limit")
        elif char in "]}":
            depth -= 1
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("NIP-46 result contains duplicate JSON members")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError("NIP-46 result has a nonfinite JSON constant")
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def expected_nip46_relay_response_result_type(
    vector_path: str,
    message: dict,
    errors: list[str],
) -> tuple[str, bool, str | None, object, bool, bool]:
    if message.get("result") == "auth_url" and "error" in message:
        return ("auth_challenge", False, None, ..., False, False)
    if "error" in message:
        return ("error", False, None, ..., False, False)
    result = message.get("result")
    if not isinstance(result, str):
        return ("unknown_result", False, None, ..., False, False)
    # Metadata recognizes the shape before JSON decoding (all-digit hex is valid
    # metadata). This is not curve/session authentication or key discovery.
    if HEX32_RE.fullmatch(result):
        return ("public_key_result", False, result, ..., False, False)
    if result == "ack":
        return ("connect_ack_result", False, None, ..., False, False)
    if result == "pong":
        return ("pong_result", False, None, ..., False, False)
    try:
        decoded = strict_nip46_result_json(result)
    except (ValueError, UnicodeError, RecursionError):
        errors.append(f"{vector_path}: response_message result is not a supported response shape")
        return ("unknown_result", False, None, ..., False, False)
    if decoded is None:
        return ("relay_no_change_result", False, None, None, False, False)
    if isinstance(decoded, list):
        if not decoded:
            errors.append(f"{vector_path}: NIP-46 switch_relays response relays must be a non-empty list or null")
            return ("unknown_result", False, None, ..., False, False)
        relays = []
        for index, relay in enumerate(decoded):
            if not isinstance(relay, str):
                errors.append(f"{vector_path}: NIP-46 switch_relays response relays must be strings")
                continue
            normalized = normalized_websocket_relay(relay, vector_path, errors, "NIP-46 switch_relays response relay")
            if normalized is not None:
                relays.append(normalized)
                if relay != normalized:
                    errors.append(f"{vector_path}: relay_urls[{index}] must be normalized")
        if len(set(relays)) != len(relays):
            errors.append(f"{vector_path}: NIP-46 switch_relays response relays must be unique")
        return ("relay_list_result", False, None, relays, False, False)
    response_errors: list[str] = []
    check_response_shape(
        Path(vector_path),
        {"version": 1, "request_id": message.get("id"), "ok": True, "result": {"event": decoded}},
        response_errors,
    )
    if response_errors:
        errors.extend(response_errors)
        return ("unknown_result", False, None, ..., False, False)
    author = decoded.get("pubkey")
    if not isinstance(author, str) or not HEX32_RE.fullmatch(author):
        errors.append(f"{vector_path}: NIP-46 signed-event response pubkey is invalid")
        return ("signed_event_result", True, None, ..., False, False)
    computed_id = event_id(decoded)
    if decoded.get("id") != computed_id:
        errors.append(f"{vector_path}: NIP-46 signed-event response id does not match NIP-01 canonical serialization")
        return ("signed_event_result", True, author, ..., False, False)
    if not verify_schnorr(author, computed_id, decoded.get("sig")):
        errors.append(f"{vector_path}: NIP-46 signed-event response signature is invalid")
        return ("signed_event_result", True, author, ..., True, False)
    return ("signed_event_result", True, author, ..., True, True)


def expected_nip46_relay_response_step(vector_path: str, vector: dict, errors: list[str]) -> dict | None:
    if vector.get("direction") != "remote_signer_to_client":
        errors.append(f"{vector_path}: NIP-46 relay response step direction must be remote_signer_to_client")
        return None
    envelope = expected_nip46_relay_event_envelope(vector_path, vector.get("event"), vector.get("direction"), errors)
    message = check_nip46_relay_response_message(vector_path, vector.get("decrypted_message"), errors)
    if envelope is None or message is None:
        return None
    expected_user = vector.get("expected_user_pubkey")
    if "expected_user_pubkey" in vector and (not isinstance(expected_user, str) or not HEX32_RE.fullmatch(expected_user)):
        errors.append(f"{vector_path}: expected user pubkey is invalid")
        return None
    (
        result_type,
        shape_checked,
        result_pubkey,
        relay_urls,
        id_verified,
        signature_verified,
    ) = expected_nip46_relay_response_result_type(vector_path, message, errors)
    bound = result_pubkey is not None and expected_user is not None and result_pubkey == expected_user
    if result_pubkey is not None and expected_user is not None and not bound:
        errors.append(f"{vector_path}: NIP-46 result pubkey does not match expected user pubkey")
    if errors and any(error.startswith(f"{vector_path}:") for error in errors):
        return None
    expected = {
        "format": "nsealr-nip46-relay-response-step-v1",
        "envelope": envelope,
        "message_id": message["id"],
        "response_message": message,
        "result_type": result_type,
        "signed_event_shape_checked": shape_checked,
        "signed_event_id_verified": id_verified,
        "signed_event_signature_verified": signature_verified,
        "result_pubkey_bound_to_expected_user": bound,
        "decrypts_content": False,
        "opens_relay": False,
        "creates_grants": False,
        "acknowledges_connect": False,
        "dispatches_signer": False,
        "relay_event_signature_verified": envelope["event_signature_verified"],
        "stores_production_secrets": False,
        "persists_session_state": False,
    }
    if result_pubkey is not None:
        expected["result_pubkey"] = result_pubkey
    if result_type == "auth_challenge":
        expected["auth_url"] = message["error"]
    if relay_urls is not ...:
        expected["relay_urls"] = relay_urls
    return expected


NIP46_AUTH_CHALLENGE_FALSE_FLAGS = {
    "opens_url",
    "opens_relay",
    "acknowledges_connect",
    "creates_grants",
    "dispatches_signer",
    "persists_session_state",
    "stores_production_secrets",
    "exposes_secret",
    "contains_secret_material",
}


NIP46_CONNECTION_TOKEN_RESPONSE_FALSE_FLAGS = {
    "starts_relay_session",
    "derives_nip44_key",
    "acknowledges_connect",
    "opens_relay",
    "creates_grants",
    "dispatches_signer",
    "stores_production_secrets",
    "persists_session_state",
    "exposes_secret",
    "contains_secret_material",
}


def expected_nip46_connection_token_response(
    vector_path: str,
    source_vector: dict,
    response_step: object,
    errors: list[str],
) -> dict | None:
    descriptor = expected_nip46_connection_uri_descriptor(vector_path, source_vector.get("uri"), errors)
    if descriptor is None:
        return None
    if descriptor.get("kind") != "nostrconnect":
        errors.append(f"{vector_path}: source connection URI must be nostrconnect")
        return None
    secret_probe = source_vector.get("secret_probe")
    if not isinstance(secret_probe, str) or not secret_probe:
        errors.append(f"{vector_path}: source connection URI secret_probe must be a non-empty string")
        return None
    if not isinstance(response_step, dict):
        errors.append(f"{vector_path}: response_step must be an object")
        return None
    if response_step.get("direction") != "remote_signer_to_client":
        errors.append(f"{vector_path}: NIP-46 token response step direction must be remote_signer_to_client")
        return None
    envelope = expected_nip46_relay_event_envelope(
        vector_path,
        response_step.get("event"),
        response_step.get("direction"),
        errors,
    )
    message = check_nip46_relay_response_message(vector_path, response_step.get("decrypted_message"), errors)
    if envelope is None or message is None:
        return None
    if envelope["recipient_pubkey"] != descriptor["client_pubkey"]:
        errors.append(f"{vector_path}: NIP-46 connection token response recipient does not match client pubkey")
    if "error" in message:
        errors.append(f"{vector_path}: token response must not contain an error")
    if message.get("result") != secret_probe:
        errors.append(f"{vector_path}: token response secret mismatch")
    if errors and any(error.startswith(f"{vector_path}:") for error in errors):
        return None
    return {
        "format": "nsealr-nip46-connection-token-response-v0",
        "kind": "nostrconnect",
        "client_pubkey": descriptor["client_pubkey"],
        "remote_signer_pubkey": envelope["sender_pubkey"],
        "relays": descriptor["relays"],
        "requested_permissions": descriptor["requested_permissions"],
        **({"client_metadata": descriptor["client_metadata"]} if "client_metadata" in descriptor else {}),
        "response_message_id": message["id"],
        "client_pubkey_bound_to_recipient": True,
        "secret_matched": True,
        "starts_relay_session": False,
        "derives_nip44_key": False,
        "acknowledges_connect": False,
        "opens_relay": False,
        "creates_grants": False,
        "dispatches_signer": False,
        "stores_production_secrets": False,
        "persists_session_state": False,
        "exposes_secret": False,
        "contains_secret_material": False,
    }


def expected_nip46_auth_challenge_review(step: dict) -> dict:
    review = {
        "format": "nsealr-nip46-auth-challenge-review-v0",
        "id": step["message_id"],
        "remote_signer_pubkey": step["envelope"]["sender_pubkey"],
        "client_pubkey": step["envelope"]["recipient_pubkey"],
        "auth_url": step["auth_url"],
        "pages": [
            {
                "title": "Auth Challenge",
                "page_indicator": "Page 1/2",
                "body_lines": [
                    "Remote signer",
                    step["envelope"]["sender_pubkey"],
                    "Client",
                    step["envelope"]["recipient_pubkey"],
                ],
            },
            {
                "title": "Auth URL",
                "page_indicator": "Page 2/2",
                "body_lines": [
                    step["auth_url"],
                    "No automatic opening",
                ],
            },
        ],
        "opens_url": False,
        "opens_relay": False,
        "acknowledges_connect": False,
        "creates_grants": False,
        "dispatches_signer": False,
        "persists_session_state": False,
        "stores_production_secrets": False,
        "exposes_secret": False,
        "contains_secret_material": False,
    }
    review["auth_challenge_digest"] = nip46_auth_challenge_digest(review)
    return review


def nip46_auth_challenge_digest(review: dict) -> str:
    review_without_digest = {
        "format": review.get("format"),
        "id": review.get("id"),
        "remote_signer_pubkey": review.get("remote_signer_pubkey"),
        "client_pubkey": review.get("client_pubkey"),
        "auth_url": review.get("auth_url"),
        "pages": review.get("pages"),
        "opens_url": review.get("opens_url"),
        "opens_relay": review.get("opens_relay"),
        "acknowledges_connect": review.get("acknowledges_connect"),
        "creates_grants": review.get("creates_grants"),
        "dispatches_signer": review.get("dispatches_signer"),
        "persists_session_state": review.get("persists_session_state"),
        "stores_production_secrets": review.get("stores_production_secrets"),
        "exposes_secret": review.get("exposes_secret"),
        "contains_secret_material": review.get("contains_secret_material"),
    }
    payload = {
        "format": "nsealr-nip46-auth-challenge-digest-v0",
        "review": review_without_digest,
    }
    return sha256_hex(canonical_json(payload).encode("utf-8"))


def expected_nip46_auth_challenge_approval(
    review: dict,
    approved_at: object,
    errors: list[str],
    vector_path: str,
) -> dict | None:
    if type(approved_at) is not int or approved_at < 0 or approved_at > MAX_SAFE_INTEGER:
        errors.append(f"{vector_path}: auth challenge approval approved_at must be a safe non-negative integer")
        return None
    return {
        "format": "nsealr-nip46-auth-challenge-approval-v0",
        "id": review["id"],
        "auth_challenge_digest": review["auth_challenge_digest"],
        "approved_at": approved_at,
        "opens_url": False,
        "opens_relay": False,
        "acknowledges_connect": False,
        "creates_grants": False,
        "dispatches_signer": False,
        "persists_session_state": False,
        "stores_production_secrets": False,
        "exposes_secret": False,
        "contains_secret_material": False,
    }


def check_invalid_nip46_relay_step(vector_path: str, vector: dict, errors: list[str]) -> None:
    relay_step = vector.get("relay_step")
    if not isinstance(relay_step, dict):
        errors.append(f"{vector_path}: relay_step must be an object")
        return
    if relay_step.get("format") == "nsealr-nip46-relay-response-step-v1":
        expected_nip46_relay_response_step(vector_path, relay_step, errors)
        return
    expected_nip46_relay_request_step(vector_path, relay_step, errors)


def check_invalid_nip46_session(vector_path: str, vector: dict, errors: list[str]) -> None:
    check_nip46_session_lifecycle_shape(vector_path, vector.get("session"), errors)


def expected_nip46_session_request_gate(
    vector_path: str,
    vector: dict,
    session: dict,
    errors: list[str],
) -> dict | None:
    if vector.get("format") != "nsealr-nip46-session-request-gate-v0":
        errors.append(f"{vector_path}: format mismatch")
        return None
    evaluated_at = vector.get("evaluated_at")
    if type(evaluated_at) is not int or evaluated_at < 0 or evaluated_at > MAX_SAFE_INTEGER:
        errors.append(f"{vector_path}: evaluated_at must be a safe non-negative integer")
    elif type(session.get("approved_at")) is int and evaluated_at < session["approved_at"]:
        errors.append(f"{vector_path}: evaluated_at must be greater than or equal to approved_at")
    elif type(session.get("expires_at")) is int and evaluated_at >= session["expires_at"]:
        errors.append(f"{vector_path}: evaluated_at must be less than expires_at")

    if vector.get("direction") != "client_to_remote_signer":
        errors.append(f"{vector_path}: NIP-46 session request gate direction must be client_to_remote_signer")
        return None
    envelope = expected_nip46_relay_event_envelope(
        vector_path,
        vector.get("event"),
        vector.get("direction"),
        errors,
    )
    message = check_nip46_request_message(vector_path, vector.get("decrypted_message"), errors)
    if envelope is None or message is None or type(evaluated_at) is not int:
        return None
    if envelope["sender_pubkey"] != session.get("client_pubkey"):
        errors.append(f"{vector_path}: NIP-46 session request sender does not match session client_pubkey")
    if envelope["recipient_pubkey"] != session.get("remote_signer_pubkey"):
        errors.append(f"{vector_path}: NIP-46 session request recipient does not match session remote_signer_pubkey")
    if message.get("method") == "connect":
        errors.append(f"{vector_path}: NIP-46 session request gate must not process connect")
        return None
    permission_requirement = expected_nip46_permission_requirement(vector_path, message, errors)
    if permission_requirement is None:
        return None
    if errors and any(error.startswith(f"{vector_path}:") for error in errors):
        return None
    return {
        "format": "nsealr-nip46-session-request-gate-v0",
        "session_name": session["name"],
        "session_phase": session["phase"],
        "evaluated_at": evaluated_at,
        "envelope": envelope,
        "message_id": message["id"],
        "permission_requirement": permission_requirement,
        "blocked_reason": "connect_ack_pending",
        "response_message": {
            "id": message["id"],
            "error": "connect_pending: NIP-46 session is approved but connect is not acknowledged",
        },
        "client_pubkey_bound_to_sender": True,
        "remote_signer_pubkey_bound_to_recipient": True,
        "session_not_expired": True,
        "uses_session_permissions": False,
        "decrypts_content": False,
        "opens_relay": False,
        "creates_grants": False,
        "acknowledges_connect": False,
        "dispatches_signer": False,
        "stores_production_secrets": False,
        "persists_session_state": False,
    }


def check_invalid_nip46_session_gate(vector_path: str, vector: dict, errors: list[str]) -> None:
    gate = vector.get("session_gate")
    if not isinstance(gate, dict):
        errors.append(f"{vector_path}: session_gate must be an object")
        return
    session = check_nip46_session_lifecycle_shape(vector_path, gate.get("session"), errors)
    if session is None:
        return
    expected_nip46_session_request_gate(vector_path, gate, session, errors)


def check_invalid_nip46_session_active(vector_path: str, vector: dict, errors: list[str]) -> None:
    check_nip46_session_active_shape(vector_path, vector.get("session"), errors)


def check_invalid_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/invalid/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "pre-signing-invalid-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    expected_error = vector.get("expected_error")
    if not isinstance(expected_error, str) or not expected_error:
        errors.append(f"{vector_path}: expected_error must be a non-empty string")
        return

    rejection_errors: list[str] = []
    category = vector.get("category")
    if category == "signing-request":
        check_request_shape(Path(vector_path), vector.get("request"), rejection_errors)
    elif category == "qr-envelope":
        check_qr_envelope_payload(vector_path, vector.get("envelope"), rejection_errors)
    elif category == "serial-frame":
        check_serial_frame_payload(vector_path, vector.get("frame"), rejection_errors)
    elif category == "response":
        check_response_shape(Path(vector_path), vector.get("response"), rejection_errors)
    elif category == "nip46":
        check_invalid_nip46_payload(vector_path, vector, rejection_errors)
    elif category == "nip46-connection-uri":
        check_invalid_nip46_connection_uri(vector_path, vector, rejection_errors)
    elif category == "nip46-connection-token-response":
        check_invalid_nip46_connection_token_response(vector_path, vector, rejection_errors)
    elif category == "nip46-relay-event":
        check_invalid_nip46_relay_event(vector_path, vector, rejection_errors)
    elif category == "nip46-relay-step":
        check_invalid_nip46_relay_step(vector_path, vector, rejection_errors)
    elif category == "nip46-session":
        check_invalid_nip46_session(vector_path, vector, rejection_errors)
    elif category == "nip46-session-gate":
        check_invalid_nip46_session_gate(vector_path, vector, rejection_errors)
    elif category == "nip46-session-active":
        check_invalid_nip46_session_active(vector_path, vector, rejection_errors)
    elif category == "nip46-policy-file":
        policy = vector.get("policy_file")
        if not isinstance(policy, dict):
            rejection_errors.append(f"{vector_path}: policy_file must be an object")
        else:
            if policy.get("format") != "nsealr-nip46-policy-v0":
                rejection_errors.append(f"{vector_path}: format mismatch")
            approved_permissions = policy.get("approved_permissions")
            if not isinstance(approved_permissions, list):
                rejection_errors.append(f"{vector_path}: approved_permissions must be a list")
            else:
                for permission in approved_permissions:
                    normalized_nip46_approved_permission(vector_path, permission, rejection_errors)
    else:
        errors.append(f"{vector_path}: unsupported invalid-vector category {category!r}")
        return

    if not rejection_errors:
        errors.append(f"{vector_path}: invalid vector unexpectedly passed")
        return
    observed = "\n".join(rejection_errors)
    if expected_error not in observed:
        errors.append(f"{vector_path}: expected error {expected_error!r} not observed in {observed!r}")


def check_nip46_connect_intent(vector_path: str, vector: dict, message: dict, errors: list[str]) -> None:
    expected = expected_nip46_connect_intent(vector_path, message, errors)
    if expected is None:
        return
    if vector.get("connect_intent") != expected:
        errors.append(f"{vector_path}: connect_intent mismatch")
    expected_review = expected_nip46_connect_review(expected)
    if vector.get("connect_review") != expected_review:
        errors.append(f"{vector_path}: connect_review mismatch")
    expected_approval = expected_nip46_connect_approval(
        expected_review,
        vector.get("connect_approval", {}).get("approved_at") if isinstance(vector.get("connect_approval"), dict) else None,
        errors,
        vector_path,
    )
    if expected_approval is None:
        return
    if vector.get("connect_approval") != expected_approval:
        errors.append(f"{vector_path}: connect_approval mismatch")
    for forbidden in ("nsealr_request", "nsealr_response", "response_message", "local_response_message"):
        if forbidden in vector:
            errors.append(f"{vector_path}: connect must not include {forbidden}")
    for forbidden in ("permission_requirement", "permission_checks"):
        if forbidden in vector:
            errors.append(f"{vector_path}: connect must not include {forbidden}")


def expected_nip46_connect_intent(vector_path: str, message: dict, errors: list[str]) -> dict | None:
    params = message.get("params", [])
    if len(params) < 1 or len(params) > 3:
        errors.append(f"{vector_path}: connect requires remote-signer pubkey plus optional secret and permissions")
        return None
    remote_pubkey = params[0]
    if not isinstance(remote_pubkey, str) or not HEX32_RE.fullmatch(remote_pubkey):
        errors.append(f"{vector_path}: connect remote-signer pubkey must be 32-byte lowercase hex")
        return None
    expected = {
        "id": message["id"],
        "remote_signer_pubkey": remote_pubkey,
        "requested_permissions": parse_nip46_permissions(params[2] if len(params) > 2 else "", vector_path, errors),
    }
    if len(params) > 1 and params[1] != "":
        expected["secret"] = params[1]
    return expected


def expected_nip46_connect_review(intent: dict) -> dict:
    permissions = intent.get("requested_permissions", [])
    permission_lines = [permission_label(permission) for permission in permissions]
    review = {
        "format": "nsealr-nip46-connect-review-v0",
        "id": intent["id"],
        "remote_signer_pubkey": intent["remote_signer_pubkey"],
        "secret_present": "secret" in intent,
        "requested_permissions": permissions,
        "pages": [
            {
                "title": "Connect",
                "page_indicator": "Page 1/2",
                "body_lines": [
                    "Remote signer",
                    intent["remote_signer_pubkey"],
                    f"Secret: {'provided' if 'secret' in intent else 'none'}",
                ],
            },
            {
                "title": "Permissions",
                "page_indicator": "Page 2/2",
                "body_lines": permission_lines if permission_lines else ["No permissions requested"],
            },
        ],
    }
    review["connect_digest"] = nip46_connect_digest(review)
    return review


def nip46_connect_digest(review: dict) -> str:
    review_without_digest = {
        "format": review.get("format"),
        "id": review.get("id"),
        "remote_signer_pubkey": review.get("remote_signer_pubkey"),
        "secret_present": review.get("secret_present"),
        "requested_permissions": review.get("requested_permissions"),
        "pages": review.get("pages"),
    }
    payload = {
        "format": "nsealr-nip46-connect-digest-v0",
        "review": review_without_digest,
    }
    return sha256_hex(canonical_json(payload).encode("utf-8"))


def expected_nip46_connect_approval(
    review: dict,
    approved_at: object,
    errors: list[str],
    vector_path: str,
) -> dict | None:
    if type(approved_at) is not int or approved_at < 0 or approved_at > MAX_SAFE_INTEGER:
        errors.append(f"{vector_path}: connect_approval approved_at must be a safe non-negative integer")
        return None
    return {
        "format": "nsealr-nip46-connect-approval-v0",
        "id": review["id"],
        "connect_digest": review["connect_digest"],
        "approved_at": approved_at,
        "acknowledges_connect": False,
        "creates_grants": False,
        "opens_relay": False,
        "persists_session_state": False,
        "stores_production_secrets": False,
        "exposes_secret": False,
    }


def normalized_nip46_permission(vector_path: str, value: object, errors: list[str]) -> dict | None:
    if not isinstance(value, dict):
        errors.append(f"{vector_path}: permission entries must be objects")
        return None
    method = value.get("method")
    if not isinstance(method, str) or method not in NIP46_PERMISSION_METHODS:
        errors.append(f"{vector_path}: permission method is invalid")
        return None
    if method == "sign_event":
        if "parameter" not in value:
            if set(value) != {"method"}:
                errors.append(f"{vector_path}: broad sign_event permission must only include method")
                return None
            return {"method": method}
        parameter = value.get("parameter")
        event_kind = value.get("event_kind")
        if (
            set(value) != {"method", "parameter", "event_kind"}
            or not isinstance(parameter, str)
            or not parameter.isdigit()
            or not isinstance(event_kind, int)
            or event_kind < 0
            or event_kind > MAX_SAFE_INTEGER
            or int(parameter) > MAX_SAFE_INTEGER
            or event_kind != int(parameter)
        ):
            errors.append(f"{vector_path}: sign_event permission parameter must match event_kind and be safe")
            return None
        return {"method": method, "parameter": parameter, "event_kind": event_kind}
    if set(value) != {"method"}:
        errors.append(f"{vector_path}: non-sign_event permission must only include method")
        return None
    return {"method": method}


def normalized_nip46_approved_permission(vector_path: str, value: object, errors: list[str]) -> dict | None:
    normalized = normalized_nip46_permission(vector_path, value, errors)
    if normalized is None:
        return None
    if normalized.get("method") == "sign_event" and "parameter" not in normalized:
        errors.append(f"{vector_path}: approved sign_event permission must include parameter and event_kind")
        return None
    return normalized


def nip46_permission_matches_requirement(permission: dict, requirement: dict) -> bool:
    if permission.get("method") != requirement.get("method"):
        return False
    if requirement.get("method") != "sign_event":
        return "parameter" not in permission
    if "parameter" not in permission:
        return True
    return permission.get("event_kind") == requirement.get("event_kind")


def nip46_session_secret_field_paths(value: object, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in NIP46_SESSION_SECRET_FIELD_NAMES:
                paths.append(path)
            paths.extend(nip46_session_secret_field_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(nip46_session_secret_field_paths(child, path))
    return paths


def check_nip46_session_no_secret_material(vector_path: str, value: object, errors: list[str]) -> None:
    for path in nip46_session_secret_field_paths(value):
        errors.append(f"{vector_path}: NIP-46 session must not contain secret material at {path}")


def check_nip46_session_permissions(
    vector_path: str,
    value: object,
    errors: list[str],
    *,
    approved: bool,
) -> list[dict]:
    label = "approved_permissions" if approved else "requested_permissions"
    if not isinstance(value, list):
        errors.append(f"{vector_path}: {label} must be a list")
        return []
    parsed = []
    for index, permission in enumerate(value):
        parser = normalized_nip46_approved_permission if approved else normalized_nip46_permission
        normalized = parser(f"{vector_path}: {label}[{index}]", permission, errors)
        if normalized is not None:
            parsed.append(normalized)
            if permission != normalized:
                errors.append(f"{vector_path}: {label}[{index}] must be normalized")
    return parsed


def check_nip46_session_relays(vector_path: str, value: object, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{vector_path}: relays must be a non-empty list")
        return []
    relays = []
    for index, relay in enumerate(value):
        if not isinstance(relay, str):
            errors.append(f"{vector_path}: relays[{index}] must be a string")
            continue
        normalized = normalized_websocket_relay(relay, vector_path, errors)
        if normalized is not None:
            relays.append(normalized)
            if relay != normalized:
                errors.append(f"{vector_path}: relays[{index}] must be normalized")
    if len(set(relays)) != len(relays):
        errors.append(f"{vector_path}: relays must be unique")
    return relays


def approved_permissions_subset_of_requested(approved: list[dict], requested: list[dict]) -> bool:
    for approved_permission in approved:
        if not any(nip46_permission_matches_requirement(requested_permission, approved_permission) for requested_permission in requested):
            return False
    return True


def check_nip46_session_lifecycle_shape(vector_path: str, value: object, errors: list[str]) -> dict | None:
    if not isinstance(value, dict):
        errors.append(f"{vector_path}: NIP-46 session must be an object")
        return None
    check_nip46_session_no_secret_material(vector_path, value, errors)
    check_known_fields(
        vector_path,
        "NIP-46 session",
        value,
        {
            "name",
            "format",
            "phase",
            "client_pubkey",
            "remote_signer_pubkey",
            "relays",
            "connect_digest",
            "approved_at",
            "expires_at",
            "requested_permissions",
            "approved_permissions",
            "secret_present",
            "secret_value_stored",
            "contains_secret_material",
            "derives_nip44_key",
            "acknowledges_connect",
            "opens_relay",
            "creates_grants",
            "dispatches_signer",
            "stores_production_secrets",
            "persists_session_state",
            "scope",
        },
        errors,
    )
    if value.get("format") != "nsealr-nip46-session-lifecycle-v0":
        errors.append(f"{vector_path}: format mismatch")
    if value.get("name") != Path(vector_path).stem:
        errors.append(f"{vector_path}: name mismatch")
    if value.get("phase") not in NIP46_SESSION_PHASES:
        errors.append(f"{vector_path}: phase must be approved_pending_ack")
    if not isinstance(value.get("client_pubkey"), str) or not HEX32_RE.fullmatch(value["client_pubkey"]):
        errors.append(f"{vector_path}: client_pubkey must be 32-byte lowercase hex")
    if not isinstance(value.get("remote_signer_pubkey"), str) or not HEX32_RE.fullmatch(value["remote_signer_pubkey"]):
        errors.append(f"{vector_path}: remote_signer_pubkey must be 32-byte lowercase hex")
    check_nip46_session_relays(vector_path, value.get("relays"), errors)

    connect_digest = value.get("connect_digest")
    if not isinstance(connect_digest, str) or not HEX32_RE.fullmatch(connect_digest):
        errors.append(f"{vector_path}: connect_digest must be 32-byte lowercase hex")

    approved_at = value.get("approved_at")
    expires_at = value.get("expires_at")
    if type(approved_at) is not int or approved_at < 0 or approved_at > MAX_SAFE_INTEGER:
        errors.append(f"{vector_path}: approved_at must be a safe non-negative integer")
    if type(expires_at) is not int or expires_at < 0 or expires_at > MAX_SAFE_INTEGER:
        errors.append(f"{vector_path}: expires_at must be a safe non-negative integer")
    elif type(approved_at) is int and expires_at <= approved_at:
        errors.append(f"{vector_path}: expires_at must be greater than approved_at")

    requested_permissions = check_nip46_session_permissions(
        vector_path,
        value.get("requested_permissions"),
        errors,
        approved=False,
    )
    approved_permissions = check_nip46_session_permissions(
        vector_path,
        value.get("approved_permissions"),
        errors,
        approved=True,
    )
    if not approved_permissions_subset_of_requested(approved_permissions, requested_permissions):
        errors.append(f"{vector_path}: approved_permissions must be a subset of requested_permissions")

    if not isinstance(value.get("secret_present"), bool):
        errors.append(f"{vector_path}: secret_present must be boolean")
    for flag in sorted(NIP46_SESSION_FALSE_FLAGS):
        if value.get(flag) is not False:
            errors.append(f"{vector_path}: {flag} must be false")

    scope = value.get("scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: scope must be a non-empty string")
    else:
        for required in ("NIP-44", "relay", "acknowledge", "grant", "signer", "persist", "secret material"):
            if required not in scope:
                errors.append(f"{vector_path}: scope must mention {required}")
    return value


def check_nip46_session_source_binding(
    vector_path: str,
    session: dict | None,
    source_connect_review_vector: object,
    errors: list[str],
) -> None:
    if session is None:
        return
    connect_source = None
    if not isinstance(source_connect_review_vector, str) or not source_connect_review_vector.startswith("vectors/nip46/"):
        errors.append(f"{vector_path}: source_connect_review_vector must point under vectors/nip46/")
    else:
        connect_source = load_required_json(source_connect_review_vector, errors)
    if not isinstance(connect_source, dict):
        return
    source_digest = connect_source.get("connect_review", {}).get("connect_digest")
    if session.get("connect_digest") != source_digest:
        errors.append(f"{vector_path}: session connect_digest must match source_connect_review_vector")
    source_intent = connect_source.get("connect_intent", {})
    if session.get("remote_signer_pubkey") != source_intent.get("remote_signer_pubkey"):
        errors.append(f"{vector_path}: session remote_signer_pubkey must match source_connect_review_vector")
    if session.get("requested_permissions") != source_intent.get("requested_permissions"):
        errors.append(f"{vector_path}: session requested_permissions must match source_connect_review_vector")
    source_review = connect_source.get("connect_review", {})
    if session.get("secret_present") != source_review.get("secret_present"):
        errors.append(f"{vector_path}: session secret_present must match source_connect_review_vector")


def check_nip46_permission_policy(vector_path: str, vector: dict, expected_requirement: dict, errors: list[str]) -> None:
    requirement = normalized_nip46_permission(vector_path, vector.get("permission_requirement"), errors)
    if requirement != expected_requirement:
        errors.append(f"{vector_path}: permission_requirement mismatch")

    checks = vector.get("permission_checks")
    if not isinstance(checks, list) or not checks:
        errors.append(f"{vector_path}: permission_checks must be a non-empty list")
        return
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"{vector_path}: permission_checks[{index}] must be an object")
            continue
        granted = check.get("granted_permissions")
        if not isinstance(granted, list):
            errors.append(f"{vector_path}: permission_checks[{index}].granted_permissions must be a list")
            continue
        granted_permissions = [
            permission
            for permission in (
                normalized_nip46_permission(vector_path, permission, errors) for permission in granted
            )
            if permission is not None
        ]
        expected_permitted = any(
            nip46_permission_matches_requirement(permission, expected_requirement) for permission in granted_permissions
        )
        if check.get("permitted") is not expected_permitted:
            errors.append(f"{vector_path}: permission_checks[{index}].permitted mismatch")


def check_nip46_request_message(vector_path: str, message: object, errors: list[str]) -> dict | None:
    if not isinstance(message, dict):
        errors.append(f"{vector_path}: request_message must be an object")
        return None
    if json_utf8_size(message) > implementation_limit_values()["max_nip46_decrypted_message_json_bytes"]:
        errors.append(f"{vector_path}: NIP-46 decrypted message JSON exceeds max_nip46_decrypted_message_json_bytes")
    if not isinstance(message.get("id"), str) or not REQUEST_ID_RE.fullmatch(message["id"]):
        errors.append(f"{vector_path}: request_message id is invalid")
    if message.get("method") not in {"connect", "get_public_key", "sign_event", "ping", "switch_relays"}:
        errors.append(f"{vector_path}: unsupported NIP-46 method")
    if not isinstance(message.get("params"), list) or not all(isinstance(item, str) for item in message["params"]):
        errors.append(f"{vector_path}: request_message params must be a string array")
    return message


def expected_nip46_permission_requirement(vector_path: str, message: dict, errors: list[str]) -> dict | None:
    method = message.get("method")
    params = message.get("params", [])
    if method == "ping":
        if params:
            errors.append(f"{vector_path}: ping params must be empty")
            return None
        return {"method": "ping"}
    if method == "switch_relays":
        if params:
            errors.append(f"{vector_path}: switch_relays params must be empty")
            return None
        return {"method": "switch_relays"}
    if method == "get_public_key":
        if params:
            errors.append(f"{vector_path}: get_public_key params must be empty")
            return None
        return {"method": "get_public_key"}
    if method == "sign_event":
        if len(params) != 1:
            errors.append(f"{vector_path}: sign_event must have one JSON string param")
            return None
        try:
            event_template = json.loads(params[0])
        except json.JSONDecodeError:
            errors.append(f"{vector_path}: sign_event param must be valid JSON")
            return None
        request_errors = request_shape_errors(
            Path(vector_path),
            {
                "version": 1,
                "request_id": message.get("id"),
                "method": "sign_event",
                "params": {
                    "event_template": event_template,
                },
            },
        )
        if request_errors:
            errors.extend(request_errors)
            return None
        if not isinstance(event_template, dict) or type(event_template.get("kind")) is not int:
            errors.append(f"{vector_path}: sign_event event kind is invalid")
            return None
        return {
            "method": "sign_event",
            "parameter": str(event_template["kind"]),
            "event_kind": event_template["kind"],
        }
    return None


def expected_nsealr_request_from_nip46_message(
    vector_path: str, message: dict, errors: list[str]
) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", [])
    if method == "get_public_key":
        return {
            "version": 1,
            "request_id": request_id,
            "method": "get_public_key",
        }
    if method == "sign_event":
        if len(params) != 1:
            return None
        try:
            event_template = json.loads(params[0])
        except json.JSONDecodeError:
            return None
        return {
            "version": 1,
            "request_id": request_id,
            "method": "sign_event",
            "params": {
                "event_template": event_template,
            },
        }
    errors.append(f"{vector_path}: cannot create nSealr request for NIP-46 method")
    return None


def permission_label(requirement: dict) -> str:
    if requirement.get("method") == "sign_event" and "parameter" in requirement:
        return f"sign_event:{requirement['parameter']}"
    return str(requirement.get("method"))


def expected_nip46_bridge_decision(
    vector_path: str,
    message: dict,
    granted_permissions: list[dict],
    errors: list[str],
) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "connect":
        connect_intent = expected_nip46_connect_intent(vector_path, message, errors)
        if connect_intent is None:
            return None
        return {
            "type": "connect_review",
            "connect_intent": connect_intent,
        }

    requirement = expected_nip46_permission_requirement(vector_path, message, errors)
    if requirement is None:
        return None
    permitted = any(
        nip46_permission_matches_requirement(permission, requirement) for permission in granted_permissions
    )
    if not permitted:
        return {
            "type": "permission_denied",
            "permission_requirement": requirement,
            "response_message": {
                "id": request_id,
                "error": f"permission_denied: request requires approved permission {permission_label(requirement)}",
            },
        }
    if method == "ping":
        return {
            "type": "local_response",
            "permission_requirement": requirement,
            "response_message": {
                "id": request_id,
                "result": "pong",
            },
        }
    if method == "switch_relays":
        return {
            "type": "local_response",
            "permission_requirement": requirement,
            "response_message": {
                "id": request_id,
                "result": "null",
            },
        }

    nsealr_request = expected_nsealr_request_from_nip46_message(vector_path, message, errors)
    if nsealr_request is None:
        return None
    return {
        "type": "signer_request",
        "permission_requirement": requirement,
        "nsealr_request": nsealr_request,
    }


def check_nip46_bridge_decisions(
    vector_path: str,
    vector: dict,
    message: dict,
    errors: list[str],
) -> None:
    bridge_decisions = vector.get("bridge_decisions")
    if not isinstance(bridge_decisions, list) or not bridge_decisions:
        errors.append(f"{vector_path}: bridge_decisions must be a non-empty list")
        return
    for index, check in enumerate(bridge_decisions):
        if not isinstance(check, dict):
            errors.append(f"{vector_path}: bridge_decisions[{index}] must be an object")
            continue
        granted = check.get("granted_permissions")
        if not isinstance(granted, list):
            errors.append(f"{vector_path}: bridge_decisions[{index}].granted_permissions must be a list")
            continue
        granted_permissions = [
            permission
            for permission in (
                normalized_nip46_permission(vector_path, permission, errors) for permission in granted
            )
            if permission is not None
        ]
        expected = expected_nip46_bridge_decision(vector_path, message, granted_permissions, errors)
        if expected is not None and check.get("decision") != expected:
            errors.append(f"{vector_path}: bridge_decisions[{index}].decision mismatch")


def check_nip46_policy_file_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-policy-files/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("format") != "nsealr-nip46-policy-v0":
        errors.append(f"{vector_path}: format mismatch")
    approved_permissions = vector.get("approved_permissions")
    if not isinstance(approved_permissions, list):
        errors.append(f"{vector_path}: approved_permissions must be a list")
        return
    for index, permission in enumerate(approved_permissions):
        normalized = normalized_nip46_approved_permission(vector_path, permission, errors)
        if normalized is not None and permission != normalized:
            errors.append(f"{vector_path}: approved_permissions[{index}] must be normalized")


def check_nip46_connection_uri_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-connection-uris/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-nip46-connection-uri-v0":
        errors.append(f"{vector_path}: format mismatch")
    expected = expected_nip46_connection_uri_descriptor(vector_path, vector.get("uri"), errors)
    if expected is None:
        return
    if vector.get("expected_descriptor") != expected:
        errors.append(f"{vector_path}: expected_descriptor mismatch")
    secret_probe = vector.get("secret_probe")
    if not isinstance(secret_probe, str) or not secret_probe:
        errors.append(f"{vector_path}: secret_probe must be a non-empty string")
    elif not isinstance(vector.get("uri"), str) or secret_probe not in [
        value for key, value in parse_qsl(urlparse(vector["uri"]).query, keep_blank_values=True) if key == "secret"
    ]:
        errors.append(f"{vector_path}: secret_probe must match the decoded uri secret parameter")
    elif secret_probe in json.dumps(vector.get("expected_descriptor"), separators=(",", ":")):
        errors.append(f"{vector_path}: expected_descriptor must not echo secret_probe")
    scope = vector.get("scope")
    if not isinstance(scope, str) or "Descriptor-only" not in scope or "must not" not in scope:
        errors.append(f"{vector_path}: scope must state descriptor-only safety boundary")


def compact_seedqr_hex_from_indexes(indexes: list[int], word_count: int) -> str:
    bit_stream = "".join(f"{index:011b}" for index in indexes)
    checksum_bits = 4 if word_count == 12 else 8
    entropy_bits = bit_stream[:-checksum_bits]
    return int(entropy_bits, 2).to_bytes(len(entropy_bits) // 8, "big").hex()


def check_seedqr_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/seedqr/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: SeedQR vector must be an object")
        return
    if vector.get("format") != "nsealr-seedqr-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if not isinstance(vector.get("source"), str) or not vector["source"]:
        errors.append(f"{vector_path}: source must be a non-empty string")
    word_count = vector.get("word_count")
    if word_count not in {12, 24}:
        errors.append(f"{vector_path}: word_count must be 12 or 24")
        return
    mnemonic = vector.get("mnemonic")
    if not isinstance(mnemonic, str) or len(mnemonic.split()) != word_count:
        errors.append(f"{vector_path}: mnemonic word count mismatch")
    digits = vector.get("standard_seedqr_digits")
    if not isinstance(digits, str) or not digits.isdigit() or len(digits) != word_count * 4:
        errors.append(f"{vector_path}: standard_seedqr_digits must contain four digits per word")
        return
    indexes = [int(digits[index : index + 4]) for index in range(0, len(digits), 4)]
    if any(index > 2047 for index in indexes):
        errors.append(f"{vector_path}: standard_seedqr_digits contains an out-of-range BIP-39 index")
    if vector.get("standard_word_indexes") != indexes:
        errors.append(f"{vector_path}: standard_word_indexes mismatch")
    compact = vector.get("compact_seedqr_hex")
    expected_hex_chars = 32 if word_count == 12 else 64
    if not isinstance(compact, str) or not re.fullmatch(r"[0-9a-f]+", compact) or len(compact) != expected_hex_chars:
        errors.append(f"{vector_path}: compact_seedqr_hex length or encoding mismatch")
    elif compact != compact_seedqr_hex_from_indexes(indexes, word_count):
        errors.append(f"{vector_path}: compact_seedqr_hex mismatch")
    scope = vector.get("compatibility_scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: compatibility_scope must be a non-empty string")
    else:
        scope_lower = scope.lower()
        for required in ("bip-39", "nip-06", "not bitcoin descriptors", "xpubs", "psbts", "wallet policy"):
            if required not in scope_lower:
                errors.append(f"{vector_path}: compatibility_scope must mention {required}")


def check_nip19_nsec_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip19/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: NIP-19 nsec vector must be an object")
        return
    if vector.get("format") != "nsealr-nip19-nsec-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if not isinstance(vector.get("source"), str) or not vector["source"]:
        errors.append(f"{vector_path}: source must be a non-empty string")
    warning = vector.get("warning")
    if not isinstance(warning, str) or "Never use in production" not in warning:
        errors.append(f"{vector_path}: warning must identify the fixture key as non-production")
    expected_secret = vector.get("secret_key")
    if not isinstance(expected_secret, str) or not HEX32_RE.fullmatch(expected_secret):
        errors.append(f"{vector_path}: secret_key must be 32-byte lowercase hex")
        expected_secret = None
    expected_public = vector.get("public_key")
    if not isinstance(expected_public, str) or not HEX32_RE.fullmatch(expected_public):
        errors.append(f"{vector_path}: public_key must be 32-byte lowercase hex")
        expected_public = None
    decoded_secret = secret_key_from_nsec(vector_path, vector.get("nsec"), errors)
    if expected_secret is not None and decoded_secret is not None and decoded_secret != expected_secret:
        errors.append(f"{vector_path}: nsec decoded secret_key mismatch")
    if expected_secret is not None and expected_public is not None:
        actual_public = xonly_pubkey_from_secret(expected_secret)
        if actual_public != expected_public:
            errors.append(f"{vector_path}: public_key mismatch")
    scope = vector.get("compatibility_scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: compatibility_scope must be a non-empty string")
    else:
        scope_lower = scope.lower()
        for required in ("nip-19", "nsec", "private-key", "ram-only", "not a persistent policy", "nip-49"):
            if required not in scope_lower:
                errors.append(f"{vector_path}: compatibility_scope must mention {required}")


def session_key_source_kind_label(source_type: str) -> str:
    if source_type == "bip39_seed":
        return "BIP-39 seed"
    if source_type == "nsec":
        return "NIP-19 nsec"
    return "Unknown"


def session_key_source_fingerprint_for_vector(vector_path: str, source_type: str, source: dict, errors: list[str]) -> str | None:
    kind_label = session_key_source_kind_label(source_type)
    material = bytearray(f"nsealr.session-key-source.v0\n{kind_label}\n".encode("utf-8"))
    if source_type == "bip39_seed":
        indexes = source.get("standard_word_indexes")
        if not isinstance(indexes, list) or not all(type(index) is int for index in indexes):
            errors.append(f"{vector_path}: source SeedQR standard_word_indexes must be integer array")
            return None
        material.extend(f"{len(indexes)}\n".encode("utf-8"))
        for index in indexes:
            if index < 0 or index > 2047:
                errors.append(f"{vector_path}: source SeedQR word index out of range")
                return None
            material.extend(index.to_bytes(2, "big"))
        return sha256_hex(bytes(material))[:16]
    if source_type == "nsec":
        secret_key = source.get("secret_key")
        if not isinstance(secret_key, str) or not HEX32_RE.fullmatch(secret_key):
            errors.append(f"{vector_path}: source nsec secret_key must be 32-byte lowercase hex")
            return None
        material.extend(bytes.fromhex(secret_key))
        return sha256_hex(bytes(material))[:16]
    errors.append(f"{vector_path}: source_type is unknown")
    return None


def session_import_approval_digest(source_type: str, label: str, fingerprint: str) -> str:
    kind_label = session_key_source_kind_label(source_type)
    material = f"nsealr.session-import-review.v0\n{kind_label}\n{label}\n{fingerprint}".encode("utf-8")
    return sha256_hex(material)


def session_source_backup_approval_digest(
    source_type: str,
    label: str,
    fingerprint: str,
    backup_format: str,
) -> str:
    kind_label = session_key_source_kind_label(source_type)
    material = (
        "nsealr.session-source-backup-review.v0\n"
        f"{kind_label}\n"
        f"{label}\n"
        f"{fingerprint}\n"
        f"{backup_format}"
    ).encode("utf-8")
    return sha256_hex(material)


def expected_session_import_review_pages(
    source_type: str,
    label: str,
    fingerprint: str,
    word_count: int | None,
) -> list[dict]:
    lines = [
        f"Type: {session_key_source_kind_label(source_type)}",
        f"Label: {label}",
        f"Fingerprint: {fingerprint}",
    ]
    if source_type == "bip39_seed":
        lines.append(f"Words: {word_count}")
    lines.append("Secret: hidden")
    return [
        {
            "title": "Import source",
            "lines": lines,
            "action": "next",
            "page_indicator": "Page 1/2",
            "logical_page_id": "session-import-summary",
        },
        {
            "title": "Import?",
            "lines": [
                "Session RAM only",
                "No signing enabled",
                "Approve to load",
            ],
            "action": "approve_or_reject",
            "page_indicator": "Page 2/2",
            "logical_page_id": "session-import-decision",
        },
    ]


def expected_session_source_backup_pages(
    source_type: str,
    label: str,
    fingerprint: str,
    backup_format: str,
) -> list[dict]:
    if source_type == "bip39_seed" and backup_format == "bip39_words_seedqr":
        output = "words/SeedQR"
    elif source_type == "nsec" and backup_format == "nip19_nsec":
        output = "nsec QR/text"
    else:
        output = "unsupported"
    return [
        {
            "title": "Backup source",
            "lines": [
                "Danger: secret export",
                f"Type: {session_key_source_kind_label(source_type)}",
                f"Label: {label}",
                f"Fingerprint: {fingerprint}",
                f"Output: {output}",
                "Session RAM only",
            ],
            "action": "next",
            "page_indicator": "Page 1/2",
            "logical_page_id": "session-backup-warning",
        },
        {
            "title": "Show secret?",
            "lines": [
                "Anyone can sign",
                "Verify offline copy",
                "Approve to reveal",
            ],
            "action": "approve_or_reject",
            "page_indicator": "Page 2/2",
            "logical_page_id": "session-backup-decision",
        },
    ]


def check_session_import_review_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/session-import-reviews/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: session import review vector must be an object")
        return
    unknown_fields = sorted(
        set(vector)
        - {
            "format",
            "name",
            "source_type",
            "source_vector",
            "label",
            "word_count",
            "fingerprint",
            "review_id",
            "approval_digest",
            "pages",
            "security_scope",
        }
    )
    if unknown_fields:
        errors.append(f"{vector_path}: unknown fields {unknown_fields}")
    if vector.get("format") != "nsealr-session-import-review-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    source_type = vector.get("source_type")
    if source_type not in {"bip39_seed", "nsec"}:
        errors.append(f"{vector_path}: source_type must be bip39_seed or nsec")
        return
    label = vector.get("label")
    if not isinstance(label, str) or not label:
        errors.append(f"{vector_path}: label must be a non-empty string")
        return
    source_vector = vector.get("source_vector")
    if not isinstance(source_vector, str):
        errors.append(f"{vector_path}: source_vector must be a string")
        return
    expected_prefixes = ("vectors/seedqr/", "vectors/keys/") if source_type == "bip39_seed" else ("vectors/nip19/",)
    if not source_vector.startswith(expected_prefixes):
        expected = " or ".join(expected_prefixes)
        errors.append(f"{vector_path}: source_vector must point under {expected}")
        return
    source = load_required_json(source_vector, errors)
    if source is None:
        return

    fingerprint = vector.get("fingerprint")
    if not isinstance(fingerprint, str) or not HEX8_RE.fullmatch(fingerprint):
        errors.append(f"{vector_path}: fingerprint must be 8-byte lowercase hex")
        fingerprint = None
    expected_fingerprint = session_key_source_fingerprint_for_vector(vector_path, source_type, source, errors)
    if fingerprint is not None and expected_fingerprint is not None and fingerprint != expected_fingerprint:
        errors.append(f"{vector_path}: fingerprint mismatch")

    if fingerprint is not None:
        if vector.get("review_id") != f"session-import-{fingerprint}":
            errors.append(f"{vector_path}: review_id mismatch")
        expected_digest = session_import_approval_digest(source_type, label, fingerprint)
        if vector.get("approval_digest") != expected_digest:
            errors.append(f"{vector_path}: approval_digest mismatch")
    if not isinstance(vector.get("approval_digest"), str) or not HEX32_RE.fullmatch(vector["approval_digest"]):
        errors.append(f"{vector_path}: approval_digest must be 32-byte lowercase hex")

    word_count = None
    if source_type == "bip39_seed":
        source_indexes = source.get("standard_word_indexes")
        expected_word_count = len(source_indexes) if isinstance(source_indexes, list) else None
        word_count = vector.get("word_count")
        if word_count != expected_word_count:
            errors.append(f"{vector_path}: word_count must match source standard_word_indexes length")
    elif "word_count" in vector:
        errors.append(f"{vector_path}: word_count is only valid for bip39_seed")

    pages = vector.get("pages")
    if not isinstance(pages, list) or len(pages) != 2:
        errors.append(f"{vector_path}: pages must contain exactly two pages")
    elif fingerprint is not None:
        expected_pages = expected_session_import_review_pages(source_type, label, fingerprint, word_count)
        if pages != expected_pages:
            errors.append(f"{vector_path}: pages mismatch")
    if isinstance(pages, list):
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                errors.append(f"{vector_path}: pages[{page_index}] must be an object")
                continue
            if not isinstance(page.get("lines"), list) or not all(isinstance(line, str) for line in page["lines"]):
                errors.append(f"{vector_path}: pages[{page_index}].lines must be an array of strings")
    serialized_pages = json.dumps(pages, ensure_ascii=False, separators=(",", ":"))
    if "Secret: hidden" not in serialized_pages:
        errors.append(f"{vector_path}: pages must explicitly state Secret: hidden")
    if source_type == "bip39_seed":
        mnemonic = source.get("mnemonic")
        if isinstance(mnemonic, str):
            for word in mnemonic.split():
                if word and word in serialized_pages:
                    errors.append(f"{vector_path}: pages must not expose mnemonic word {word!r}")
    if source_type == "nsec":
        for secret_field in ("nsec", "secret_key"):
            secret_value = source.get(secret_field)
            if isinstance(secret_value, str) and secret_value in serialized_pages:
                errors.append(f"{vector_path}: pages must not expose source {secret_field}")

    scope = vector.get("security_scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: security_scope must be a non-empty string")
    else:
        scope_lower = scope.lower()
        for required in ("secret-hidden", "ram-only", "does not persist", "does not approve signing"):
            if required not in scope_lower:
                errors.append(f"{vector_path}: security_scope must mention {required}")


def check_source_public_key_proof_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/source-public-key-proofs/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: source public-key proof vector must be an object")
        return
    unknown_fields = sorted(
        set(vector)
        - {
            "format",
            "name",
            "proof_type",
            "source_type",
            "source_vector",
            "source_fingerprint",
            "account",
            "path",
            "passphrase",
            "expected_public_key",
            "security_scope",
        }
    )
    if unknown_fields:
        errors.append(f"{vector_path}: unknown fields {unknown_fields}")
    if vector.get("format") != "nsealr-source-public-key-proof-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")

    proof_type = vector.get("proof_type")
    source_type = vector.get("source_type")
    if proof_type == "nip06":
        if source_type != "bip39_seed":
            errors.append(f"{vector_path}: NIP-06 proof requires bip39_seed source_type")
        expected_prefixes = ("vectors/keys/",)
    elif proof_type == "nip19_nsec":
        if source_type != "nsec":
            errors.append(f"{vector_path}: NIP-19 nsec proof requires nsec source_type")
        expected_prefixes = ("vectors/nip19/",)
    else:
        errors.append(f"{vector_path}: proof_type must be nip06 or nip19_nsec")
        expected_prefixes = ()

    source_vector = vector.get("source_vector")
    if not isinstance(source_vector, str) or (expected_prefixes and not source_vector.startswith(expected_prefixes)):
        expected = " or ".join(expected_prefixes) if expected_prefixes else "a supported source vector"
        errors.append(f"{vector_path}: source_vector must point under {expected}")
        return
    source = load_required_json(source_vector, errors)
    if source is None:
        return

    expected_public_key = vector.get("expected_public_key")
    if not isinstance(expected_public_key, str) or not HEX32_RE.fullmatch(expected_public_key):
        errors.append(f"{vector_path}: expected_public_key must be 32-byte lowercase hex")
        expected_public_key = None
    source_fingerprint = vector.get("source_fingerprint")
    if not isinstance(source_fingerprint, str) or not HEX8_RE.fullmatch(source_fingerprint):
        errors.append(f"{vector_path}: source_fingerprint must be 8-byte lowercase hex")
        source_fingerprint = None
    if source_type in {"bip39_seed", "nsec"}:
        expected_fingerprint = session_key_source_fingerprint_for_vector(vector_path, source_type, source, errors)
        if source_fingerprint is not None and expected_fingerprint is not None and source_fingerprint != expected_fingerprint:
            errors.append(f"{vector_path}: source_fingerprint mismatch")

    if proof_type == "nip06":
        if vector.get("account") != source.get("account"):
            errors.append(f"{vector_path}: account must match source account")
        if vector.get("path") != source.get("path"):
            errors.append(f"{vector_path}: path must match source path")
        if vector.get("passphrase") != source.get("passphrase"):
            errors.append(f"{vector_path}: passphrase must match source passphrase")
    elif any(field in vector for field in ("account", "path", "passphrase")):
        errors.append(f"{vector_path}: account/path/passphrase are only valid for NIP-06 proofs")

    if expected_public_key is not None and source.get("public_key") != expected_public_key:
        errors.append(f"{vector_path}: expected_public_key must match source public_key")
    secret_key = source.get("secret_key")
    if isinstance(secret_key, str) and HEX32_RE.fullmatch(secret_key) and expected_public_key is not None:
        if xonly_pubkey_from_secret(secret_key) != expected_public_key:
            errors.append(f"{vector_path}: expected_public_key does not match source secret key")
    else:
        errors.append(f"{vector_path}: source secret_key must be available for proof verification")

    scope = vector.get("security_scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: security_scope must be a non-empty string")
    else:
        scope_lower = scope.lower()
        for required in ("proof", "public key", "ram-only", "before signing", "does not persist", "approve signing", "descriptors/fingerprints"):
            if required not in scope_lower:
                errors.append(f"{vector_path}: security_scope must mention {required}")


def check_session_source_backup_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/session-source-backups/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if not isinstance(vector, dict):
        errors.append(f"{vector_path}: session source backup vector must be an object")
        return
    unknown_fields = sorted(
        set(vector)
        - {
            "format",
            "name",
            "source_type",
            "source_vector",
            "label",
            "word_count",
            "fingerprint",
            "backup_format",
            "backup_payload",
            "review_id",
            "approval_digest",
            "pages",
            "security_scope",
        }
    )
    if unknown_fields:
        errors.append(f"{vector_path}: unknown fields {unknown_fields}")
    if vector.get("format") != "nsealr-session-source-backup-review-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    source_type = vector.get("source_type")
    if source_type not in {"bip39_seed", "nsec"}:
        errors.append(f"{vector_path}: source_type must be bip39_seed or nsec")
        return
    label = vector.get("label")
    if not isinstance(label, str) or not label:
        errors.append(f"{vector_path}: label must be a non-empty string")
        return
    source_vector = vector.get("source_vector")
    if not isinstance(source_vector, str):
        errors.append(f"{vector_path}: source_vector must be a string")
        return
    expected_prefixes = ("vectors/seedqr/", "vectors/keys/") if source_type == "bip39_seed" else ("vectors/nip19/",)
    if not source_vector.startswith(expected_prefixes):
        expected = " or ".join(expected_prefixes)
        errors.append(f"{vector_path}: source_vector must point under {expected}")
        return
    source = load_required_json(source_vector, errors)
    if source is None:
        return

    backup_format = vector.get("backup_format")
    expected_backup_format = "bip39_words_seedqr" if source_type == "bip39_seed" else "nip19_nsec"
    if backup_format != expected_backup_format:
        errors.append(f"{vector_path}: backup_format must be {expected_backup_format}")
        return

    fingerprint = vector.get("fingerprint")
    if not isinstance(fingerprint, str) or not HEX8_RE.fullmatch(fingerprint):
        errors.append(f"{vector_path}: fingerprint must be 8-byte lowercase hex")
        fingerprint = None
    expected_fingerprint = session_key_source_fingerprint_for_vector(vector_path, source_type, source, errors)
    if fingerprint is not None and expected_fingerprint is not None and fingerprint != expected_fingerprint:
        errors.append(f"{vector_path}: fingerprint mismatch")

    if fingerprint is not None:
        if vector.get("review_id") != f"session-backup-{fingerprint}":
            errors.append(f"{vector_path}: review_id mismatch")
        expected_digest = session_source_backup_approval_digest(source_type, label, fingerprint, backup_format)
        if vector.get("approval_digest") != expected_digest:
            errors.append(f"{vector_path}: approval_digest mismatch")
    if not isinstance(vector.get("approval_digest"), str) or not HEX32_RE.fullmatch(vector["approval_digest"]):
        errors.append(f"{vector_path}: approval_digest must be 32-byte lowercase hex")

    word_count = vector.get("word_count")
    if source_type == "bip39_seed":
        source_indexes = source.get("standard_word_indexes")
        expected_word_count = len(source_indexes) if isinstance(source_indexes, list) else None
        if word_count != expected_word_count:
            errors.append(f"{vector_path}: word_count must match source standard_word_indexes length")
    elif "word_count" in vector:
        errors.append(f"{vector_path}: word_count is only valid for bip39_seed")

    backup_payload = vector.get("backup_payload")
    if not isinstance(backup_payload, dict):
        errors.append(f"{vector_path}: backup_payload must be an object")
    elif source_type == "bip39_seed":
        expected_payload = {
            "mnemonic": source.get("mnemonic"),
            "standard_seedqr_digits": source.get("standard_seedqr_digits"),
            "compact_seedqr_hex": source.get("compact_seedqr_hex"),
        }
        if backup_payload != expected_payload:
            errors.append(f"{vector_path}: backup_payload must match source mnemonic and SeedQR payloads")
    elif backup_payload != {"nsec": source.get("nsec")}:
        errors.append(f"{vector_path}: backup_payload must match source nsec")

    pages = vector.get("pages")
    if not isinstance(pages, list) or len(pages) != 2:
        errors.append(f"{vector_path}: pages must contain exactly two pages")
    elif fingerprint is not None:
        expected_pages = expected_session_source_backup_pages(source_type, label, fingerprint, backup_format)
        if pages != expected_pages:
            errors.append(f"{vector_path}: pages mismatch")
    if isinstance(pages, list):
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                errors.append(f"{vector_path}: pages[{page_index}] must be an object")
                continue
            if not isinstance(page.get("lines"), list) or not all(isinstance(line, str) for line in page["lines"]):
                errors.append(f"{vector_path}: pages[{page_index}].lines must be an array of strings")
    serialized_pages = json.dumps(pages, ensure_ascii=False, separators=(",", ":"))
    for required in ("Danger: secret export", "Approve to reveal"):
        if required not in serialized_pages:
            errors.append(f"{vector_path}: pages must include {required!r}")
    if source_type == "bip39_seed":
        mnemonic = source.get("mnemonic")
        if isinstance(mnemonic, str):
            for word in mnemonic.split():
                if word and word in serialized_pages:
                    errors.append(f"{vector_path}: review pages must not expose mnemonic word {word!r}")
        for secret_field in ("mnemonic", "standard_seedqr_digits", "compact_seedqr_hex"):
            secret_value = source.get(secret_field)
            if isinstance(secret_value, str) and secret_value in serialized_pages:
                errors.append(f"{vector_path}: review pages must not expose source {secret_field}")
    if source_type == "nsec":
        for secret_field in ("nsec", "secret_key"):
            secret_value = source.get(secret_field)
            if isinstance(secret_value, str) and secret_value in serialized_pages:
                errors.append(f"{vector_path}: review pages must not expose source {secret_field}")

    scope = vector.get("security_scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: security_scope must be a non-empty string")
    else:
        scope_lower = scope.lower()
        for required in ("danger-zone", "ram-only", "must not expose", "does not persist", "does not approve signing"):
            if required not in scope_lower:
                errors.append(f"{vector_path}: security_scope must mention {required}")


def check_feature_matrix_feature_shape(
    path: str,
    feature_id: str,
    feature: object,
    canonical_contracts: dict[str, str],
    errors: list[str],
) -> None:
    if feature_id not in FEATURE_IDS:
        errors.append(f"{path}: unknown feature {feature_id}")
    if not isinstance(feature, dict):
        errors.append(f"{path}: feature {feature_id} must be an object")
        return

    target = feature.get("target")
    current = feature.get("current")
    if target not in FEATURE_TARGETS:
        errors.append(f"{path}: feature {feature_id} target is unknown")
    if current not in FEATURE_CURRENT_STATUSES:
        errors.append(f"{path}: feature {feature_id} current status is unknown")

    contract_id = feature.get("contract_id")
    active_target = target in {"required", "optional", "research"}
    if active_target:
        if not isinstance(contract_id, str) or not contract_id:
            errors.append(f"{path}: feature {feature_id} active target requires contract_id")
        elif canonical_contracts.get(feature_id) != contract_id:
            errors.append(f"{path}: feature {feature_id} contract_id does not match canonical feature contract")
    elif "contract_id" in feature:
        errors.append(f"{path}: feature {feature_id} inactive target must not set contract_id")

    notes = feature.get("notes")
    if not isinstance(notes, str) or not notes:
        errors.append(f"{path}: feature {feature_id} notes must be a non-empty string")


def check_feature_matrix_shape(path: str, matrix: object, errors: list[str]) -> None:
    if not isinstance(matrix, dict):
        errors.append(f"{path}: feature matrix must be an object")
        return
    if matrix.get("format") != "nsealr-signer-feature-matrix-v0":
        errors.append(f"{path}: format mismatch")
    if matrix.get("name") != Path(path).stem:
        errors.append(f"{path}: name mismatch")

    features = matrix.get("features")
    if not isinstance(features, list):
        errors.append(f"{path}: features must be a list")
        return
    feature_ids: list[str] = []
    canonical_contracts: dict[str, str] = {}
    for index, feature in enumerate(features):
        feature_path = f"{path}: features[{index}]"
        if not isinstance(feature, dict):
            errors.append(f"{feature_path}: feature definition must be an object")
            continue
        feature_id = feature.get("id")
        if feature_id not in FEATURE_IDS:
            errors.append(f"{feature_path}: unknown feature id")
            continue
        feature_ids.append(feature_id)
        contract_id = feature.get("contract_id")
        if not isinstance(contract_id, str) or not contract_id:
            errors.append(f"{feature_path}: contract_id must be a non-empty string")
        else:
            canonical_contracts[feature_id] = contract_id
        behavior = feature.get("behavior")
        if not isinstance(behavior, str) or not behavior:
            errors.append(f"{feature_path}: behavior must be a non-empty string")
    if set(feature_ids) != FEATURE_IDS:
        errors.append(f"{path}: feature definitions must match the canonical feature id set")
    if len(feature_ids) != len(set(feature_ids)):
        errors.append(f"{path}: feature definitions contain duplicates")

    solutions = matrix.get("solutions")
    if not isinstance(solutions, dict):
        errors.append(f"{path}: solutions must be an object")
        return
    if set(solutions) != FEATURE_SOLUTION_IDS:
        errors.append(f"{path}: solutions must match the five first-class signer families")
        return

    active_contracts: dict[str, str] = {}
    for solution_id, solution in sorted(solutions.items()):
        solution_path = f"{path}: solutions.{solution_id}"
        if not isinstance(solution, dict):
            errors.append(f"{solution_path}: solution must be an object")
            continue
        if not isinstance(solution.get("label"), str) or not solution["label"]:
            errors.append(f"{solution_path}: label must be a non-empty string")
        if not isinstance(solution.get("repository"), str) or not solution["repository"]:
            errors.append(f"{solution_path}: repository must be a non-empty string")
        if not isinstance(solution.get("product_goal"), str) or not solution["product_goal"]:
            errors.append(f"{solution_path}: product_goal must be a non-empty string")
        solution_features = solution.get("features")
        if not isinstance(solution_features, dict):
            errors.append(f"{solution_path}: features must be an object")
            continue
        if set(solution_features) != FEATURE_IDS:
            errors.append(f"{solution_path}: features must match the canonical feature id set")
            continue
        for feature_id, feature in sorted(solution_features.items()):
            feature_path = f"{solution_path}.features.{feature_id}"
            check_feature_matrix_feature_shape(feature_path, feature_id, feature, canonical_contracts, errors)
            if not isinstance(feature, dict):
                continue
            target = feature.get("target")
            contract_id = feature.get("contract_id")
            if target in {"required", "optional", "research"} and isinstance(contract_id, str):
                previous = active_contracts.setdefault(feature_id, contract_id)
                if previous != contract_id:
                    errors.append(
                        f"{feature_path}: shared feature contract drift for {feature_id}"
                    )

    parity_targets: dict[str, object] | None = None
    for solution_id in ("raspberry_qr_vault", "esp32_qr_vault"):
        solution = solutions.get(solution_id)
        if not isinstance(solution, dict) or not isinstance(solution.get("features"), dict):
            continue
        current_targets = {
            feature_id: solution["features"].get(feature_id, {}).get("target")
            for feature_id in STATELESS_QR_PARITY_FEATURES
            if isinstance(solution["features"].get(feature_id), dict)
        }
        if parity_targets is None:
            parity_targets = current_targets
        elif current_targets != parity_targets:
            errors.append(f"{path}: stateless_qr_vault parity mismatch")


def check_feature_matrix_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/features/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_feature_matrix_shape(vector_path, vector, errors)


def check_persistent_secret_custody_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/custody/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("format") != "nsealr-persistent-secret-custody-contract-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("contract_id") != "persistent-secret-custody-v0":
        errors.append(f"{vector_path}: contract_id mismatch")
    if vector.get("solution") != "custom_hardware_wallet":
        errors.append(f"{vector_path}: solution must be custom_hardware_wallet")
    if vector.get("repository") != "hardware":
        errors.append(f"{vector_path}: repository must be hardware")
    if vector.get("current_status") != "research":
        errors.append(f"{vector_path}: current_status must be research")
    scope = vector.get("scope")
    if not isinstance(scope, str) or "production secret storage" not in scope:
        errors.append(f"{vector_path}: scope must describe production secret storage boundary")

    requirements = vector.get("requirements")
    if not isinstance(requirements, dict):
        errors.append(f"{vector_path}: requirements must be an object")
        requirements = {}

    secret_at_rest = requirements.get("secret_at_rest")
    if not isinstance(secret_at_rest, dict):
        errors.append(f"{vector_path}: requirements.secret_at_rest must be an object")
    else:
        if secret_at_rest.get("plaintext_allowed") is not False:
            errors.append(f"{vector_path}: plaintext_allowed must be false")
        if set(secret_at_rest.get("allowed_storage", [])) != CUSTODY_ALLOWED_STORAGE:
            errors.append(f"{vector_path}: allowed_storage mismatch")
        if secret_at_rest.get("production_storage_enabled") is not False:
            errors.append(f"{vector_path}: production_storage_enabled must be false")

    unlock = requirements.get("unlock")
    if not isinstance(unlock, dict):
        errors.append(f"{vector_path}: requirements.unlock must be an object")
    else:
        if set(unlock.get("plaintext_locations", [])) != {"esp32_s3_ram"}:
            errors.append(f"{vector_path}: unlock plaintext_locations mismatch")
        if set(unlock.get("required_unlock_assist", [])) != {"tropic01"}:
            errors.append(f"{vector_path}: unlock required_unlock_assist mismatch")
        if unlock.get("requires_local_unlock") is not True:
            errors.append(f"{vector_path}: unlock requires_local_unlock must be true")
        if unlock.get("requires_device_review_state") is not True:
            errors.append(f"{vector_path}: unlock requires_device_review_state must be true")

    persistence = requirements.get("plaintext_persistence")
    if not isinstance(persistence, dict):
        errors.append(f"{vector_path}: requirements.plaintext_persistence must be an object")
    else:
        if persistence.get("scope") != "unlocked_session_ram_only":
            errors.append(f"{vector_path}: plaintext_persistence scope mismatch")
        if set(persistence.get("forbidden_outputs", [])) != CUSTODY_FORBIDDEN_OUTPUTS:
            errors.append(f"{vector_path}: plaintext_persistence forbidden_outputs mismatch")

    if set(requirements.get("wipe_events", [])) != CUSTODY_WIPE_EVENTS:
        errors.append(f"{vector_path}: wipe_events mismatch")

    pin_policy = requirements.get("pin_attempt_policy")
    if not isinstance(pin_policy, dict):
        errors.append(f"{vector_path}: requirements.pin_attempt_policy must be an object")
    else:
        if pin_policy.get("requires_tropic01_mac_and_destroy_or_vendor_equivalent") is not True:
            errors.append(f"{vector_path}: pin_attempt_policy must require TROPIC01 MAC-and-Destroy")
        if pin_policy.get("production_required") is not True:
            errors.append(f"{vector_path}: pin_attempt_policy production_required must be true")

    export_policy = requirements.get("backup_export_policy")
    if not isinstance(export_policy, dict):
        errors.append(f"{vector_path}: requirements.backup_export_policy must be an object")
    else:
        expected_false = {"enabled_by_default"}
        expected_true = {
            "requires_local_device_review",
            "requires_physical_approval",
            "requires_danger_zone_copy",
        }
        for field in sorted(expected_false):
            if export_policy.get(field) is not False:
                errors.append(f"{vector_path}: backup_export_policy.{field} must be false")
        for field in sorted(expected_true):
            if export_policy.get(field) is not True:
                errors.append(f"{vector_path}: backup_export_policy.{field} must be true")

    non_claims = vector.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) and item for item in non_claims):
        errors.append(f"{vector_path}: non_claims must be a non-empty list of strings")
    else:
        joined = "\n".join(non_claims).lower()
        required_non_claims = (
            "direct tropic01",
            "production signing",
            "stateless qr vault",
        )
        for required in required_non_claims:
            if required not in joined:
                errors.append(f"{vector_path}: non_claims must mention {required}")


def check_device_security_profile_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/devices/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "firmware-boot-hardening-profile-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("contract_id") != "firmware-boot-hardening-v0":
        errors.append(f"{vector_path}: contract_id mismatch")
    if vector.get("solution") != "esp32_usb_nip46":
        errors.append(f"{vector_path}: solution must be esp32_usb_nip46")
    if vector.get("repository") != "firmware":
        errors.append(f"{vector_path}: repository must be firmware")
    if vector.get("target") != "esp32_s3_usb_signer":
        errors.append(f"{vector_path}: target must be esp32_s3_usb_signer")
    if vector.get("profile") != "development_scaffold":
        errors.append(f"{vector_path}: profile must be development_scaffold")
    if vector.get("current") != "partial":
        errors.append(f"{vector_path}: current must be partial")

    boundary = vector.get("current_boundary")
    if not isinstance(boundary, dict):
        errors.append(f"{vector_path}: current_boundary must be an object")
        boundary = {}
    expected_boundary = {
        "schema": "nsealr-esp32-security-profile-v0",
        "runtime_signing_feature_enabled": False,
        "production_signing_allowed": False,
        "secure_boot_enabled": False,
        "flash_encryption_enabled": False,
        "debug_access_locked": False,
        "persistent_secret_storage": "not_implemented",
    }
    for key, expected in expected_boundary.items():
        if boundary.get(key) != expected:
            errors.append(f"{vector_path}: current_boundary.{key} mismatch")

    required_sections = vector.get("required_profile_sections")
    expected_sections = {
        "secure_boot",
        "flash_encryption",
        "debug_access",
        "key_provisioning",
        "trusted_review_display",
        "display_review_protocol_evidence",
        "unicode_review_rendering",
        "companion_transport_evidence",
        "firmware_protocol_evidence",
        "security_fuse_audit_evidence",
        "physical_approval_controls",
        "companion_signed_output_verification",
        "production_blockers",
    }
    if not isinstance(required_sections, list) or set(required_sections) != expected_sections:
        errors.append(f"{vector_path}: required_profile_sections mismatch")
    elif len(required_sections) != len(set(required_sections)):
        errors.append(f"{vector_path}: required_profile_sections contains duplicates")

    blockers = vector.get("required_production_blockers")
    if not isinstance(blockers, list):
        errors.append(f"{vector_path}: required_production_blockers must be an array")
        blockers = []
    for blocker in blockers:
        if blocker not in SIGNING_STATUS_GATES:
            errors.append(f"{vector_path}: unknown production blocker {blocker!r}")
    if len(blockers) != len(set(blockers)):
        errors.append(f"{vector_path}: required_production_blockers contains duplicates")
    for blocker in ("secure_boot", "flash_encryption", "debug_lock", "key_provisioning", "source_public_key_proof"):
        if blocker not in blockers:
            errors.append(f"{vector_path}: missing required production blocker {blocker}")

    implemented_controls = vector.get("implemented_controls")
    expected_implemented = {
        "validated_development_security_profile",
        "read_only_efuse_audit_report",
        "signing_status_reports_hardening_blockers",
    }
    if not isinstance(implemented_controls, list) or set(implemented_controls) != expected_implemented:
        errors.append(f"{vector_path}: implemented_controls mismatch")

    not_implemented_controls = vector.get("not_implemented_controls")
    expected_not_implemented = {
        "production_signing",
        "production_key_provisioning",
        "source_public_key_proof",
        "secure_boot_enabled",
        "flash_encryption_enabled",
        "debug_access_locked",
    }
    if not isinstance(not_implemented_controls, list) or set(not_implemented_controls) != expected_not_implemented:
        errors.append(f"{vector_path}: not_implemented_controls mismatch")

    notes = vector.get("notes")
    if not isinstance(notes, str) or "does not enable" not in notes:
        errors.append(f"{vector_path}: notes must state the non-enabling boundary")


def check_nip46_response_message(vector_path: str, message: object, expected_id: str, errors: list[str]) -> dict | None:
    if not isinstance(message, dict):
        errors.append(f"{vector_path}: response_message must be an object")
        return None
    if message.get("id") != expected_id:
        errors.append(f"{vector_path}: response_message id mismatch")
    if "result" not in message and "error" not in message:
        errors.append(f"{vector_path}: response_message must include result or error")
    if "result" in message and "error" in message:
        errors.append(f"{vector_path}: response_message must not include both result and error")
    if "result" in message and not isinstance(message["result"], str):
        errors.append(f"{vector_path}: response_message result must be a string")
    if "error" in message and not isinstance(message["error"], str):
        errors.append(f"{vector_path}: response_message error must be a string")
    return message


def check_nip46_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nip46-decrypted-payload-v0":
        errors.append(f"{vector_path}: format mismatch")

    message = check_nip46_request_message(vector_path, vector.get("request_message"), errors)
    if message is None:
        return
    request_id = message.get("id")
    if not isinstance(request_id, str):
        return
    method = message.get("method")
    params = message.get("params", [])
    if not isinstance(params, list):
        return

    check_nip46_bridge_decisions(vector_path, vector, message, errors)

    if method == "ping":
        if params:
            errors.append(f"{vector_path}: ping params must be empty")
        if "nsealr_request" in vector or "nsealr_response" in vector:
            errors.append(f"{vector_path}: ping must not include nSealr request/response")
        if vector.get("local_response_message") != {"id": request_id, "result": "pong"}:
            errors.append(f"{vector_path}: local_response_message mismatch")
        check_nip46_permission_policy(vector_path, vector, {"method": "ping"}, errors)
        return

    if method == "switch_relays":
        if params:
            errors.append(f"{vector_path}: switch_relays params must be empty")
        if "nsealr_request" in vector or "nsealr_response" in vector:
            errors.append(f"{vector_path}: switch_relays must not include nSealr request/response")
        if vector.get("local_response_message") != {"id": request_id, "result": "null"}:
            errors.append(f"{vector_path}: local_response_message mismatch")
        check_nip46_permission_policy(vector_path, vector, {"method": "switch_relays"}, errors)
        return

    if method == "connect":
        check_nip46_connect_intent(vector_path, vector, message, errors)
        return

    nsealr_request = vector.get("nsealr_request")
    if not isinstance(nsealr_request, dict):
        errors.append(f"{vector_path}: nsealr_request must be an object")
        return
    check_request_shape(Path(vector_path), nsealr_request, errors)
    if nsealr_request.get("request_id") != request_id:
        errors.append(f"{vector_path}: nsealr_request request_id mismatch")
    if nsealr_request.get("method") != method:
        errors.append(f"{vector_path}: nsealr_request method mismatch")

    if method == "get_public_key" and params:
        errors.append(f"{vector_path}: get_public_key params must be empty")
    if method == "get_public_key":
        check_nip46_permission_policy(vector_path, vector, {"method": "get_public_key"}, errors)
    if method == "sign_event":
        if len(params) != 1:
            errors.append(f"{vector_path}: sign_event must have one JSON string param")
        else:
            try:
                event_template = json.loads(params[0])
            except json.JSONDecodeError:
                errors.append(f"{vector_path}: sign_event param must be valid JSON")
            else:
                if event_template != nsealr_request.get("params", {}).get("event_template"):
                    errors.append(f"{vector_path}: sign_event param must match nSealr event_template")
                if not isinstance(event_template, dict) or not isinstance(event_template.get("kind"), int):
                    errors.append(f"{vector_path}: sign_event event kind is invalid")
                else:
                    check_nip46_permission_policy(
                        vector_path,
                        vector,
                        {
                            "method": "sign_event",
                            "parameter": str(event_template["kind"]),
                            "event_kind": event_template["kind"],
                        },
                        errors,
                    )

    nsealr_response = vector.get("nsealr_response")
    if not isinstance(nsealr_response, dict):
        errors.append(f"{vector_path}: nsealr_response must be an object")
        return
    check_response_shape(Path(vector_path), nsealr_response, errors)
    if nsealr_response.get("request_id") != request_id:
        errors.append(f"{vector_path}: nsealr_response request_id mismatch")

    response_message = check_nip46_response_message(vector_path, vector.get("response_message"), request_id, errors)
    if response_message is None:
        return
    if nsealr_response.get("ok") is False:
        error = nsealr_response.get("error", {})
        if response_message.get("error") != f"{error.get('code')}: {error.get('message')}":
            errors.append(f"{vector_path}: response_message error mismatch")
        return

    result = nsealr_response.get("result", {})
    if method == "get_public_key":
        if response_message.get("result") != result.get("public_key"):
            errors.append(f"{vector_path}: public-key result mismatch")
    if method == "sign_event":
        if response_message.get("result") != compact_json(result.get("event")):
            errors.append(f"{vector_path}: signed-event result mismatch")


def check_nip46_relay_event_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-relay-events/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-nip46-relay-event-envelope-v0":
        errors.append(f"{vector_path}: format mismatch")
    expected = expected_nip46_relay_event_envelope(
        vector_path,
        vector.get("event"),
        vector.get("direction"),
        errors,
    )
    if expected is None:
        return
    if vector.get("expected_envelope") != expected:
        errors.append(f"{vector_path}: expected_envelope mismatch")
    scope = vector.get("scope")
    if not isinstance(scope, str) or "NIP-44" not in scope or "relay" not in scope:
        errors.append(f"{vector_path}: scope must state relay/NIP-44 non-enabling boundary")


def check_nip46_relay_step_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-relay-steps/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") == "nsealr-nip46-relay-request-step-v0":
        expected = expected_nip46_relay_request_step(vector_path, vector, errors)
    elif vector.get("format") == "nsealr-nip46-relay-response-step-v1":
        expected = expected_nip46_relay_response_step(vector_path, vector, errors)
    else:
        errors.append(f"{vector_path}: format mismatch")
        return
    if expected is None:
        return
    if not exact_json_equal(vector.get("expected_step"), expected):
        errors.append(f"{vector_path}: expected_step mismatch")
    scope = vector.get("scope")
    scope_requires_signature_boundary = vector.get("format") == "nsealr-nip46-relay-response-step-v1"
    if (
        not isinstance(scope, str)
        or "NIP-44" not in scope
        or "relay" not in scope
        or "persist" not in scope
        or (scope_requires_signature_boundary and "signature" not in scope)
    ):
        errors.append(f"{vector_path}: scope must state relay/NIP-44/persistence non-enabling boundary")


def check_nip46_connection_token_response_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-connection-token-responses/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_known_fields(
        vector_path,
        "NIP-46 connection token response vector",
        vector,
        {"name", "format", "source_connection_uri_vector", "response_step", "expected_response", "scope"},
        errors,
    )
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-nip46-connection-token-response-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    source = vector.get("source_connection_uri_vector")
    if not isinstance(source, str) or not source.startswith("vectors/nip46-connection-uris/"):
        errors.append(f"{vector_path}: source_connection_uri_vector must point under vectors/nip46-connection-uris/")
        return
    source_vector = load_required_json(source, errors)
    if source_vector is None:
        return
    expected = expected_nip46_connection_token_response(vector_path, source_vector, vector.get("response_step"), errors)
    actual = vector.get("expected_response")
    if expected is not None and actual != expected:
        errors.append(f"{vector_path}: expected_response mismatch")
    elif isinstance(actual, dict):
        for flag in NIP46_CONNECTION_TOKEN_RESPONSE_FALSE_FLAGS:
            if actual.get(flag) is not False:
                errors.append(f"{vector_path}: expected_response {flag} must be false")
        if actual.get("client_pubkey_bound_to_recipient") is not True:
            errors.append(f"{vector_path}: expected_response client_pubkey_bound_to_recipient must be true")
        if actual.get("secret_matched") is not True:
            errors.append(f"{vector_path}: expected_response secret_matched must be true")
    secret_probe = source_vector.get("secret_probe")
    if isinstance(secret_probe, str) and isinstance(actual, dict):
        if secret_probe in json.dumps(actual, separators=(",", ":")):
            errors.append(f"{vector_path}: expected_response must not echo secret_probe")
    scope = vector.get("scope")
    if (
        not isinstance(scope, str)
        or "without storing or exposing" not in scope
        or "does not open relays" not in scope
        or "acknowledge connect" not in scope
        or "dispatch signers" not in scope
        or "persist session state" not in scope
    ):
        errors.append(f"{vector_path}: scope must state secretless non-enabling response boundary")


def check_nip46_auth_challenge_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-auth-challenges/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_known_fields(
        vector_path,
        "NIP-46 auth challenge vector",
        vector,
        {"name", "format", "source_relay_step_vector", "review", "approval", "scope"},
        errors,
    )
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-nip46-auth-challenge-review-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    source = vector.get("source_relay_step_vector")
    if not isinstance(source, str) or not source.startswith("vectors/nip46-relay-steps/"):
        errors.append(f"{vector_path}: source_relay_step_vector must point under vectors/nip46-relay-steps/")
        return
    source_vector = load_required_json(source, errors)
    if source_vector is None:
        return
    source_step = expected_nip46_relay_response_step(source, source_vector, errors)
    if source_step is None:
        return
    if source_step.get("result_type") != "auth_challenge" or "auth_url" not in source_step:
        errors.append(f"{vector_path}: source relay step must be an auth_challenge response")
        return
    expected_review = expected_nip46_auth_challenge_review(source_step)
    review = vector.get("review")
    if review != expected_review:
        errors.append(f"{vector_path}: review mismatch")
    elif isinstance(review, dict):
        for flag in NIP46_AUTH_CHALLENGE_FALSE_FLAGS:
            if review.get(flag) is not False:
                errors.append(f"{vector_path}: review {flag} must be false")
    approval = vector.get("approval")
    approved_at = approval.get("approved_at") if isinstance(approval, dict) else None
    expected_approval = expected_nip46_auth_challenge_approval(expected_review, approved_at, errors, vector_path)
    if expected_approval is not None and approval != expected_approval:
        errors.append(f"{vector_path}: approval mismatch")
    elif isinstance(approval, dict):
        for flag in NIP46_AUTH_CHALLENGE_FALSE_FLAGS:
            if approval.get(flag) is not False:
                errors.append(f"{vector_path}: approval {flag} must be false")
    scope = vector.get("scope")
    if (
        not isinstance(scope, str)
        or "without opening the URL" not in scope
        or "acknowledging connect" not in scope
        or "dispatching a signer" not in scope
        or "persisting session state" not in scope
    ):
        errors.append(f"{vector_path}: scope must state URL/ack/signer/persistence non-enabling boundary")


def check_nip46_session_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-sessions/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_known_fields(
        vector_path,
        "NIP-46 session lifecycle vector",
        vector,
        {"name", "format", "source_connect_review_vector", "session"},
        errors,
    )
    if vector.get("format") != "nsealr-nip46-session-lifecycle-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    session = check_nip46_session_lifecycle_shape(vector_path, vector.get("session"), errors)
    check_nip46_session_source_binding(vector_path, session, vector.get("source_connect_review_vector"), errors)


def check_nip46_session_active_persisted_state(vector_path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{vector_path}: persisted_state must be an object")
        return
    check_known_fields(vector_path, "persisted_state", value, {"fields", "contains_secret_material"}, errors)
    fields = value.get("fields")
    if not isinstance(fields, list) or not fields or not all(isinstance(f, str) and f for f in fields):
        errors.append(f"{vector_path}: persisted_state.fields must be a non-empty string list")
    else:
        for field in fields:
            if field.lower() in NIP46_SESSION_SECRET_FIELD_NAMES:
                errors.append(f"{vector_path}: persisted_state.fields must not include secret field {field}")
    if value.get("contains_secret_material") is not False:
        errors.append(f"{vector_path}: persisted_state.contains_secret_material must be false")


def check_nip46_session_active_nip44(vector_path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{vector_path}: nip44 must be an object")
        return
    check_known_fields(vector_path, "nip44", value, {"event_kind", "payload_encrypted", "version"}, errors)
    if value.get("event_kind") != 24133:
        errors.append(f"{vector_path}: nip44.event_kind must be 24133")
    if value.get("payload_encrypted") is not True:
        errors.append(f"{vector_path}: nip44.payload_encrypted must be true")
    if value.get("version") != 2:
        errors.append(f"{vector_path}: nip44.version must be 2")


def check_nip46_session_active_shape(vector_path: str, value: object, errors: list[str]) -> dict | None:
    if not isinstance(value, dict):
        errors.append(f"{vector_path}: active session must be an object")
        return None
    check_nip46_session_no_secret_material(vector_path, value, errors)
    check_known_fields(
        vector_path,
        "active session",
        value,
        {
            "name", "format", "phase", "client_pubkey", "remote_signer_pubkey",
            "relays", "connect_digest", "approved_permissions", "nip44",
            "acknowledges_connect", "derives_nip44_key", "opens_relay",
            "dispatches_signer", "creates_grants", "persists_session_state",
            "persisted_state", "secret_present", "secret_value_stored",
            "contains_secret_material", "stores_production_secrets", "scope",
        },
        errors,
    )
    if value.get("format") != "nsealr-nip46-session-active-v0":
        errors.append(f"{vector_path}: format mismatch")
    if value.get("name") != Path(vector_path).stem:
        errors.append(f"{vector_path}: name mismatch")
    phase = value.get("phase")
    if phase not in NIP46_SESSION_ACTIVE_PHASES:
        errors.append(f"{vector_path}: phase must be one of {sorted(NIP46_SESSION_ACTIVE_PHASES)}")
    for label in ("client_pubkey", "remote_signer_pubkey", "connect_digest"):
        if not isinstance(value.get(label), str) or not HEX32_RE.fullmatch(value.get(label, "")):
            errors.append(f"{vector_path}: {label} must be 32-byte lowercase hex")
    check_nip46_session_relays(vector_path, value.get("relays"), errors)
    check_nip46_session_active_nip44(vector_path, value.get("nip44"), errors)
    approved = check_nip46_session_permissions(vector_path, value.get("approved_permissions"), errors, approved=True)
    if not approved:
        errors.append(f"{vector_path}: approved_permissions must be non-empty")
    if value.get("persists_session_state") is not True:
        errors.append(f"{vector_path}: persists_session_state must be true")
    check_nip46_session_active_persisted_state(vector_path, value.get("persisted_state"), errors)
    if not isinstance(value.get("secret_present"), bool):
        errors.append(f"{vector_path}: secret_present must be boolean")
    for flag in sorted(NIP46_SESSION_ACTIVE_ALWAYS_FALSE):
        if value.get(flag) is not False:
            errors.append(f"{vector_path}: {flag} must be false")
    if phase in NIP46_SESSION_ACTIVE_PHASE_FLAGS:
        for flag, expected in NIP46_SESSION_ACTIVE_PHASE_FLAGS[phase].items():
            if value.get(flag) is not expected:
                errors.append(f"{vector_path}: {flag} must be {str(expected).lower()} in phase {phase}")
    if not isinstance(value.get("creates_grants"), bool):
        errors.append(f"{vector_path}: creates_grants must be boolean")
    scope = value.get("scope")
    if not isinstance(scope, str) or not scope:
        errors.append(f"{vector_path}: scope must be a non-empty string")
    else:
        for required in ("NIP-44", "relay", "persist", "secret material"):
            if required not in scope:
                errors.append(f"{vector_path}: scope must mention {required}")
    return value


def check_nip46_session_active_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-sessions-active/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_known_fields(
        vector_path,
        "NIP-46 active session vector",
        vector,
        {"name", "format", "source_session_vector", "session"},
        errors,
    )
    if vector.get("format") != "nsealr-nip46-session-active-vector-v0":
        errors.append(f"{vector_path}: format mismatch")
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    session = check_nip46_session_active_shape(vector_path, vector.get("session"), errors)
    source_session_vector = vector.get("source_session_vector")
    if not isinstance(source_session_vector, str) or not source_session_vector.startswith("vectors/nip46-sessions/"):
        errors.append(f"{vector_path}: source_session_vector must point under vectors/nip46-sessions/")
        return
    source = load_required_json(source_session_vector, errors)
    if not isinstance(source, dict) or session is None:
        return
    source_session = source.get("session", {})
    for label in ("client_pubkey", "remote_signer_pubkey", "connect_digest", "relays", "secret_present"):
        if session.get(label) != source_session.get(label):
            errors.append(f"{vector_path}: session {label} must match source_session_vector checkpoint")


def check_nip46_session_gate_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/nip46-session-gates/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    check_known_fields(
        vector_path,
        "NIP-46 session request gate vector",
        vector,
        {
            "name",
            "format",
            "source_session_vector",
            "evaluated_at",
            "direction",
            "event",
            "decrypted_message",
            "expected_gate",
            "scope",
        },
        errors,
    )
    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "nsealr-nip46-session-request-gate-v0":
        errors.append(f"{vector_path}: format mismatch")
    source_session_vector = vector.get("source_session_vector")
    if not isinstance(source_session_vector, str) or not source_session_vector.startswith("vectors/nip46-sessions/"):
        errors.append(f"{vector_path}: source_session_vector must point under vectors/nip46-sessions/")
        return
    source = load_required_json(source_session_vector, errors)
    if not isinstance(source, dict):
        return
    session = check_nip46_session_lifecycle_shape(source_session_vector, source.get("session"), errors)
    if session is None:
        return
    expected = expected_nip46_session_request_gate(vector_path, vector, session, errors)
    if expected is None:
        return
    if vector.get("expected_gate") != expected:
        errors.append(f"{vector_path}: expected_gate mismatch")
    scope = vector.get("scope")
    if (
        not isinstance(scope, str)
        or "NIP-44" not in scope
        or "relay" not in scope
        or "acknowledg" not in scope
        or "dispatch" not in scope
        or "persist" not in scope
    ):
        errors.append(f"{vector_path}: scope must state relay/NIP-44/ack/dispatch/persistence non-enabling boundary")


SMARTCARD_APDU_EXPECTATIONS = {
    "get-public-key": {
        "cla": "80",
        "ins": "10",
        "command_hex": "80100000",
        "status_word": "9000",
        "response_data_hex": lambda: load_json("vectors/keys/test-key-1.json")["public_key"],
    },
    "sign-event-id-kind-1-basic": {
        "cla": "80",
        "ins": "20",
        "event_id": lambda: load_json("vectors/events/kind-1-basic.json")["event_id"],
        "command_hex": lambda: f"8020000020{load_json('vectors/events/kind-1-basic.json')['event_id']}",
        "status_word": "9000",
        "expected_data_length": 64,
    },
    "sign-event-id-wrong-length": {
        "cla": "80",
        "ins": "20",
        "command_hex": "8020000001ff",
        "status_word": "6700",
        "response_hex": "6700",
    },
    "get-public-key-nonzero-p1": {
        "cla": "80",
        "ins": "10",
        "command_hex": "80100100",
        "status_word": "6a86",
        "response_hex": "6a86",
    },
    "get-public-key-with-le": {
        "cla": "80",
        "ins": "10",
        "command_hex": "8010000000",
        "status_word": "6700",
        "response_hex": "6700",
    },
    "sign-event-id-nonzero-p2": {
        "cla": "80",
        "ins": "20",
        "event_id": lambda: load_json("vectors/events/kind-1-basic.json")["event_id"],
        "command_hex": lambda: f"8020000120{load_json('vectors/events/kind-1-basic.json')['event_id']}",
        "status_word": "6a86",
        "response_hex": "6a86",
    },
    "sign-event-id-with-le": {
        "cla": "80",
        "ins": "20",
        "event_id": lambda: load_json("vectors/events/kind-1-basic.json")["event_id"],
        "command_hex": lambda: f"8020000020{load_json('vectors/events/kind-1-basic.json')['event_id']}00",
        "status_word": "6700",
        "response_hex": "6700",
    },
    "unsupported-cla": {
        "cla": "00",
        "ins": "10",
        "command_hex": "00100000",
        "status_word": "6e00",
        "response_hex": "6e00",
    },
    "unsupported-ins": {
        "cla": "80",
        "ins": "ff",
        "command_hex": "80ff0000",
        "status_word": "6d00",
        "response_hex": "6d00",
    },
}


def expected_apdu_value(value: object) -> object:
    if callable(value):
        return value()
    return value


def apdu_vector_status_word(vector: dict) -> str | None:
    status = vector.get("expected_status_word", vector.get("status_word"))
    return status if isinstance(status, str) else None


def check_smartcard_apdu_vector(rel: str, errors: list[str]) -> None:
    vector_path = f"vectors/smartcard/{rel}.json"
    vector = load_required_json(vector_path, errors)
    if vector is None:
        return
    expectation = SMARTCARD_APDU_EXPECTATIONS.get(rel)
    if expectation is None:
        errors.append(f"{vector_path}: unexpected smartcard APDU vector")
        return

    if vector.get("name") != rel:
        errors.append(f"{vector_path}: name mismatch")
    if vector.get("format") != "smartcard-apdu-v0":
        errors.append(f"{vector_path}: format mismatch")
    for field in ("cla", "ins", "event_id", "command_hex"):
        if field not in expectation:
            continue
        expected = expected_apdu_value(expectation[field])
        if vector.get(field) != expected:
            errors.append(f"{vector_path}: {field} mismatch")

    command_hex = vector.get("command_hex", "")
    if not isinstance(command_hex, str) or len(command_hex) % 2 != 0 or not APDU_HEX_RE.fullmatch(command_hex):
        errors.append(f"{vector_path}: command_hex must be even-length lowercase hex")

    expected_status = expected_apdu_value(expectation["status_word"])
    if apdu_vector_status_word(vector) != expected_status:
        errors.append(f"{vector_path}: status word mismatch")

    if "response_data_hex" in expectation:
        expected_response_data = expected_apdu_value(expectation["response_data_hex"])
        if vector.get("response_data_hex") != expected_response_data:
            errors.append(f"{vector_path}: response_data_hex mismatch")
        expected_response_hex = f"{expected_response_data}{expected_status}"
        if vector.get("response_hex") != expected_response_hex:
            errors.append(f"{vector_path}: response_hex mismatch")
    elif "response_hex" in expectation and vector.get("response_hex") != expectation["response_hex"]:
        errors.append(f"{vector_path}: response_hex mismatch")

    if "expected_data_length" in expectation and vector.get("expected_data_length") != expectation["expected_data_length"]:
        errors.append(f"{vector_path}: expected_data_length mismatch")


def main() -> int:
    errors: list[str] = []

    for schema in (
        "signing-request-v0.schema.json",
        "signing-response-v0.schema.json",
        "error-v0.schema.json",
        "nip46-policy-file-v0.schema.json",
        "account-descriptor-v0.schema.json",
        "policy-profile-v0.schema.json",
        "grant-descriptor-v0.schema.json",
        "policy-decision-vector-v0.schema.json",
        "route-selection-vector-v0.schema.json",
        "nip46-session-active-v0.schema.json",
    ):
        load_json(f"schemas/{schema}")

    signing_response_schema = load_json("schemas/signing-response-v0.schema.json")
    signing_status_props = (
        signing_response_schema.get("$defs", {})
        .get("signing_status", {})
        .get("properties", {})
    )
    for gate_field in ("missing_gates", "development_accepted_gates"):
        schema_gate_enum = signing_status_props.get(gate_field, {}).get("items", {}).get("enum", [])
        if schema_gate_enum != SIGNING_STATUS_GATES:
            errors.append(
                "schemas/signing-response-v0.schema.json: "
                f"signing_status.{gate_field} enum must match SIGNING_STATUS_GATES"
            )

    check_implementation_limits(errors)

    for path in sorted((ROOT / "examples").glob("request-*.json")):
        check_request_shape(path.relative_to(ROOT), load_json(str(path.relative_to(ROOT))), errors)

    for path in sorted((ROOT / "examples" / "invalid").glob("request-*.json")):
        invalid_errors = request_shape_errors(path.relative_to(ROOT), load_json(str(path.relative_to(ROOT))))
        if not invalid_errors:
            errors.append(f"{path.relative_to(ROOT)}: invalid request unexpectedly passed")

    for path in sorted((ROOT / "examples").glob("response-*.json")):
        check_response_shape(path.relative_to(ROOT), load_json(str(path.relative_to(ROOT))), errors)

    capability_request = load_required_json("examples/request-get-capabilities.json", errors)
    capability_response = load_required_json("examples/response-get-capabilities-esp32-s3-scaffold.json", errors)
    capability_vector = load_required_json("vectors/devices/esp32-s3-capabilities-scaffold.json", errors)
    signing_status_request = load_required_json("examples/request-get-signing-status.json", errors)
    signing_status_response = load_required_json("examples/response-get-signing-status-esp32-s3-scaffold.json", errors)
    signing_status_vector = load_required_json("vectors/devices/esp32-s3-signing-status-disabled.json", errors)
    public_key_request = load_required_json("examples/request-get-public-key.json", errors)
    public_key_response = load_required_json("examples/response-get-public-key.json", errors)
    public_key_vector = load_required_json("vectors/devices/esp32-s3-get-public-key-dev.json", errors)
    signing_disabled_response = load_required_json("examples/response-sign-event-disabled-esp32-s3-scaffold.json", errors)
    signing_disabled_vector = load_required_json("vectors/devices/esp32-s3-sign-event-disabled.json", errors)
    if capability_request is not None:
        if capability_request.get("method") != "get_capabilities":
            errors.append("examples/request-get-capabilities.json: method must be get_capabilities")
    if capability_request is not None and capability_response is not None:
        if capability_response.get("request_id") != capability_request.get("request_id"):
            errors.append("examples/response-get-capabilities-esp32-s3-scaffold.json: request_id mismatch")
        capabilities = capability_response.get("result", {}).get("capabilities", {})
        if capabilities.get("signing_enabled") is not False:
            errors.append("examples/response-get-capabilities-esp32-s3-scaffold.json: scaffold signing must be disabled")
        if capabilities.get("requires_physical_approval") is not True:
            errors.append("examples/response-get-capabilities-esp32-s3-scaffold.json: physical approval must be required")
        if "sign_event" not in capabilities.get("methods", []):
            errors.append("examples/response-get-capabilities-esp32-s3-scaffold.json: sign_event capability must be declared")
        if "get_signing_status" not in capabilities.get("methods", []):
            errors.append("examples/response-get-capabilities-esp32-s3-scaffold.json: get_signing_status capability must be declared")
    if capability_vector is not None and capability_request is not None and capability_response is not None:
        if capability_vector.get("request") != capability_request:
            errors.append("vectors/devices/esp32-s3-capabilities-scaffold.json: request mismatch")
        if capability_vector.get("response") != capability_response:
            errors.append("vectors/devices/esp32-s3-capabilities-scaffold.json: response mismatch")
    if signing_status_request is not None:
        if signing_status_request.get("method") != "get_signing_status":
            errors.append("examples/request-get-signing-status.json: method must be get_signing_status")
    if signing_status_request is not None and signing_status_response is not None:
        if signing_status_response.get("request_id") != signing_status_request.get("request_id"):
            errors.append("examples/response-get-signing-status-esp32-s3-scaffold.json: request_id mismatch")
        signing_status = signing_status_response.get("result", {}).get("signing_status", {})
        if signing_status.get("signing_enabled") is not False:
            errors.append("examples/response-get-signing-status-esp32-s3-scaffold.json: scaffold signing must be disabled")
        if signing_status.get("missing_gates") != ESP32_S3_SCAFFOLD_MISSING_SIGNING_GATES:
            errors.append("examples/response-get-signing-status-esp32-s3-scaffold.json: missing gate list mismatch")
        if signing_status.get("development_accepted_gates") != ESP32_S3_SCAFFOLD_DEVELOPMENT_ACCEPTED_SIGNING_GATES:
            errors.append("examples/response-get-signing-status-esp32-s3-scaffold.json: development accepted gate list mismatch")
    if signing_status_vector is not None and signing_status_request is not None and signing_status_response is not None:
        if signing_status_vector.get("request") != signing_status_request:
            errors.append("vectors/devices/esp32-s3-signing-status-disabled.json: request mismatch")
        if signing_status_vector.get("response") != signing_status_response:
            errors.append("vectors/devices/esp32-s3-signing-status-disabled.json: response mismatch")
    if public_key_request is not None:
        if public_key_request.get("method") != "get_public_key":
            errors.append("examples/request-get-public-key.json: method must be get_public_key")
    if public_key_request is not None and public_key_response is not None:
        if public_key_response.get("request_id") != public_key_request.get("request_id"):
            errors.append("examples/response-get-public-key.json: request_id mismatch")
    if public_key_vector is not None and public_key_request is not None and public_key_response is not None:
        if public_key_vector.get("request") != public_key_request:
            errors.append("vectors/devices/esp32-s3-get-public-key-dev.json: request mismatch")
        if public_key_vector.get("response") != public_key_response:
            errors.append("vectors/devices/esp32-s3-get-public-key-dev.json: response mismatch")
    if signing_disabled_response is not None:
        if signing_disabled_response.get("ok") is not False:
            errors.append("examples/response-sign-event-disabled-esp32-s3-scaffold.json: ok must be false")
        error = signing_disabled_response.get("error", {})
        if error.get("code") != "signing_disabled":
            errors.append("examples/response-sign-event-disabled-esp32-s3-scaffold.json: code must be signing_disabled")
        if error.get("retryable") is not False:
            errors.append("examples/response-sign-event-disabled-esp32-s3-scaffold.json: retryable must be false")
    if signing_disabled_vector is not None and signing_disabled_response is not None:
        if signing_disabled_vector.get("request") != load_json("examples/request-kind-1-basic.json"):
            errors.append("vectors/devices/esp32-s3-sign-event-disabled.json: request mismatch")
        if signing_disabled_vector.get("response") != signing_disabled_response:
            errors.append("vectors/devices/esp32-s3-sign-event-disabled.json: response mismatch")

    capabilities_enabled = load_required_json(
        "examples/response-get-capabilities-esp32-s3-enabled.json", errors
    )
    if capabilities_enabled is not None:
        enabled_caps = capabilities_enabled.get("result", {}).get("capabilities", {})
        if enabled_caps.get("signing_enabled") is not True:
            errors.append("examples/response-get-capabilities-esp32-s3-enabled.json: signing must be enabled")
        if enabled_caps.get("requires_physical_approval") is not True:
            errors.append("examples/response-get-capabilities-esp32-s3-enabled.json: physical approval must remain required")
        if "sign_event" not in enabled_caps.get("methods", []):
            errors.append("examples/response-get-capabilities-esp32-s3-enabled.json: sign_event capability must be declared")

    signing_status_enabled = load_required_json(
        "examples/response-get-signing-status-esp32-s3-enabled.json", errors
    )
    if signing_status_enabled is not None:
        enabled_status = signing_status_enabled.get("result", {}).get("signing_status", {})
        if enabled_status.get("signing_enabled") is not True:
            errors.append("examples/response-get-signing-status-esp32-s3-enabled.json: signing must be enabled")
        if enabled_status.get("missing_gates") != []:
            errors.append("examples/response-get-signing-status-esp32-s3-enabled.json: enabled status requires empty missing_gates")

    capabilities_enabled_request = load_required_json(
        "examples/request-get-capabilities-enabled.json", errors
    )
    if capabilities_enabled_request is not None and capabilities_enabled_request.get("method") != "get_capabilities":
        errors.append("examples/request-get-capabilities-enabled.json: method must be get_capabilities")
    if capabilities_enabled is not None and capabilities_enabled_request is not None:
        if capabilities_enabled.get("request_id") != capabilities_enabled_request.get("request_id"):
            errors.append("examples/response-get-capabilities-esp32-s3-enabled.json: request_id mismatch")
    capabilities_enabled_vector = load_required_json(
        "vectors/devices/esp32-s3-capabilities-enabled.json", errors
    )
    if capabilities_enabled_vector is not None:
        if capabilities_enabled_vector.get("request") != capabilities_enabled_request:
            errors.append("vectors/devices/esp32-s3-capabilities-enabled.json: request mismatch")
        if capabilities_enabled_vector.get("response") != capabilities_enabled:
            errors.append("vectors/devices/esp32-s3-capabilities-enabled.json: response mismatch")

    signing_status_enabled_request = load_required_json(
        "examples/request-get-signing-status-enabled.json", errors
    )
    if signing_status_enabled_request is not None and signing_status_enabled_request.get("method") != "get_signing_status":
        errors.append("examples/request-get-signing-status-enabled.json: method must be get_signing_status")
    if signing_status_enabled is not None and signing_status_enabled_request is not None:
        if signing_status_enabled.get("request_id") != signing_status_enabled_request.get("request_id"):
            errors.append("examples/response-get-signing-status-esp32-s3-enabled.json: request_id mismatch")
    signing_status_enabled_vector = load_required_json(
        "vectors/devices/esp32-s3-signing-status-enabled.json", errors
    )
    if signing_status_enabled_vector is not None:
        if signing_status_enabled_vector.get("request") != signing_status_enabled_request:
            errors.append("vectors/devices/esp32-s3-signing-status-enabled.json: request mismatch")
        if signing_status_enabled_vector.get("response") != signing_status_enabled:
            errors.append("vectors/devices/esp32-s3-signing-status-enabled.json: response mismatch")

    key = load_json("vectors/keys/test-key-1.json")
    if not HEX32_RE.fullmatch(key.get("public_key", "")):
        errors.append("vectors/keys/test-key-1.json: invalid public_key")
    if xonly_pubkey_from_secret(key.get("secret_key", "")) != key.get("public_key"):
        errors.append("vectors/keys/test-key-1.json: public_key mismatch")
    nip06_key = load_required_json("vectors/keys/nip06-account-0-leader.json", errors)
    if nip06_key is not None:
        if nip06_key.get("source") != "nostr-protocol/nips 06.md test vector":
            errors.append("vectors/keys/nip06-account-0-leader.json: source mismatch")
        if nip06_key.get("path") != "m/44'/1237'/0'/0/0":
            errors.append("vectors/keys/nip06-account-0-leader.json: path mismatch")
        if nip06_key.get("account") != 0:
            errors.append("vectors/keys/nip06-account-0-leader.json: account mismatch")
        if xonly_pubkey_from_secret(nip06_key.get("secret_key", "")) != nip06_key.get("public_key"):
            errors.append("vectors/keys/nip06-account-0-leader.json: public_key mismatch")
    if public_key_response is not None:
        response_public_key = public_key_response.get("result", {}).get("public_key")
        if response_public_key != key.get("public_key"):
            errors.append("examples/response-get-public-key.json: public_key must match test-key-1")

    for rel in ("kind-1-basic", "kind-1-tags"):
        vector = load_json(f"vectors/events/{rel}.json")
        event = vector["signed_event"]
        computed_serialization = canonical_event_serialization(event)
        computed_id = event_id(event)
        if vector["canonical_serialization"] != computed_serialization:
            errors.append(f"vectors/events/{rel}.json: canonical serialization mismatch")
        if vector["event_id"] != computed_id:
            errors.append(f"vectors/events/{rel}.json: vector event_id mismatch")
        if event["id"] != computed_id:
            errors.append(f"vectors/events/{rel}.json: signed event id mismatch")
        if not verify_schnorr(event["pubkey"], event["id"], event["sig"]):
            errors.append(f"vectors/events/{rel}.json: Schnorr signature verification failed")
        request = load_json(f"examples/request-{rel}.json")
        response = load_json(f"examples/response-{rel}.json")
        if request != vector["request"]:
            errors.append(f"examples/request-{rel}.json: does not match vector request")
        if response != vector["response"]:
            errors.append(f"examples/response-{rel}.json: does not match vector response")

    for rel in review_vector_names():
        check_review_vector(rel, errors)

    for rel in review_screen_vector_names():
        check_review_screen_vector(rel, errors)

    for rel in review_display_frame_vector_names():
        check_review_display_frame_vector(rel, errors)

    for rel in review_detail_page_vector_names():
        check_review_detail_page_vector(rel, errors)

    for rel in review_transcript_vector_names():
        check_review_transcript_vector(rel, errors)

    for rel in nip46_vector_names():
        check_nip46_vector(rel, errors)

    for rel in nip46_policy_file_vector_names():
        check_nip46_policy_file_vector(rel, errors)

    for rel in nip46_connection_uri_vector_names():
        check_nip46_connection_uri_vector(rel, errors)

    for rel in nip46_connection_token_response_vector_names():
        check_nip46_connection_token_response_vector(rel, errors)

    for rel in nip46_relay_event_vector_names():
        check_nip46_relay_event_vector(rel, errors)

    for rel in nip46_relay_step_vector_names():
        check_nip46_relay_step_vector(rel, errors)

    for rel in nip46_auth_challenge_vector_names():
        check_nip46_auth_challenge_vector(rel, errors)

    for rel in nip46_session_vector_names():
        check_nip46_session_vector(rel, errors)

    for rel in nip46_session_gate_vector_names():
        check_nip46_session_gate_vector(rel, errors)

    for rel in nip46_session_active_vector_names():
        check_nip46_session_active_vector(rel, errors)

    for rel in seedqr_vector_names():
        check_seedqr_vector(rel, errors)

    for rel in nip19_nsec_vector_names():
        check_nip19_nsec_vector(rel, errors)

    for rel in session_import_review_vector_names():
        check_session_import_review_vector(rel, errors)

    for rel in source_public_key_proof_vector_names():
        check_source_public_key_proof_vector(rel, errors)

    for rel in session_source_backup_vector_names():
        check_session_source_backup_vector(rel, errors)

    for rel in account_descriptor_vector_names():
        check_account_descriptor_vector(rel, errors)

    for rel in policy_profile_vector_names():
        check_policy_profile_vector(rel, errors)

    for rel in grant_descriptor_vector_names():
        check_grant_descriptor_vector(rel, errors)

    for rel in policy_decision_vector_names():
        check_policy_decision_vector(rel, errors)

    for rel in policy_change_review_vector_names():
        check_policy_change_review_vector(rel, errors)

    for rel in route_selection_vector_names():
        check_route_selection_vector(rel, errors)

    for rel in route_refusal_contract_vector_names():
        check_route_refusal_contract_vector(rel, errors)

    for rel in access_surface_vector_names():
        check_access_surface_vector(rel, errors)

    for rel in feature_matrix_vector_names():
        check_feature_matrix_vector(rel, errors)

    for rel in custody_contract_vector_names():
        check_persistent_secret_custody_vector(rel, errors)

    for rel in device_security_profile_vector_names():
        check_device_security_profile_vector(rel, errors)

    for rel in smartcard_apdu_vector_names():
        check_smartcard_apdu_vector(rel, errors)

    for rel in invalid_vector_names():
        check_invalid_vector(rel, errors)

    qr_request = load_json("examples/request-kind-1-basic.json")
    qr_vector = load_required_json("vectors/transports/qr-envelope-kind-1-basic.json", errors)
    if qr_vector is not None:
        expected_qr = f"{QR_PREFIX}{base64url_json(qr_request)}"
        if qr_vector.get("envelope") != expected_qr:
            errors.append("vectors/transports/qr-envelope-kind-1-basic.json: envelope mismatch")
        if qr_vector.get("decoded") != qr_request:
            errors.append("vectors/transports/qr-envelope-kind-1-basic.json: decoded request mismatch")
    check_animated_qr_vector("qr-animated-response-kind-1-basic", errors)

    serial_vector = load_required_json("vectors/transports/serial-frame-request-kind-1-basic.json", errors)
    if serial_vector is not None:
        payload = serial_vector.get("payload_base64url", "")
        frame_type = serial_vector.get("type", "")
        expected_serial = (
            f"{SERIAL_PREFIX}{frame_type}:{payload}:{serial_checksum(frame_type, payload)}\n"
        )
        if frame_type not in {"request", "response", "error"}:
            errors.append("vectors/transports/serial-frame-request-kind-1-basic.json: unsupported frame type")
        if not isinstance(payload, str) or not B64URL_RE.fullmatch(payload):
            errors.append("vectors/transports/serial-frame-request-kind-1-basic.json: invalid base64url payload")
        if serial_vector.get("decoded") != qr_request:
            errors.append("vectors/transports/serial-frame-request-kind-1-basic.json: decoded request mismatch")
        if serial_vector.get("frame") != expected_serial:
            errors.append("vectors/transports/serial-frame-request-kind-1-basic.json: frame mismatch")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("nSealr specs v0 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
