from __future__ import annotations

import json
from typing import Any


# Wire revision is independent of the retained codec/implementation-limit v0 IDs.
SIGNING_VERSION = 2

# The independent Python harness is a synthetic conformance implementation, not
# an identified Pi release or shared-engine/device qualification. Only discovery
# is advertised available; the selected manifest retains unavailable provider
# defaults for public-key/signing operations. Its local verification is separate.
PI_REFERENCE_CAPABILITIES: dict[str, Any] = {
    "format": "nsealr.capabilities.v1",
    "form": "reference",
    "profile": "pi_qr",
    "implementation_id": "nsealr.conformance.pi_qr.v1",
    "runtime": [
        {
            "method_id": "get_capabilities",
            "configuration": "configured",
            "availability": "available",
            "reason": None,
        }
    ],
}


NSEALR_V0_LIMITS: dict[str, int] = {
    "max_request_id_length": 128,
    "max_decoded_request_json_bytes": 704,
    "max_static_qr_decoded_json_bytes": 704,
    "max_animated_qr_decoded_json_bytes": 4096,
    "max_animated_qr_frame_payload_chars": 256,
    "max_animated_qr_frame_count": 64,
    "max_serial_frame_bytes": 1024,
    "max_nip46_decrypted_message_json_bytes": 1024,
    "max_content_utf8_bytes": 512,
    "max_tag_count": 16,
    "max_tag_fields_per_tag": 8,
    "max_tag_field_utf8_bytes": 64,
    "max_total_tag_utf8_bytes": 4096,
    "max_safe_integer": 9007199254740991,
}


def utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


def compact_json_utf8_size(value: Any) -> int:
    return utf8_size(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
