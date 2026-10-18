import json
import hashlib
from typing import Optional

from .limits import NSEALR_V0_LIMITS


QR_ENVELOPE_PREFIX = "nsealr1:"
ANIMATED_QR_ENVELOPE_PREFIX = "nsealr1a:"


def _assert_base64url(value: str) -> None:
    if not value:
        raise ValueError("QR envelope payload must be unpadded base64url")
    if "=" in value:
        raise ValueError("QR envelope payload must be unpadded base64url")
    if any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
        raise ValueError("QR envelope payload must be base64url")


def encode_qr_envelope(value: object) -> str:
    import base64

    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > NSEALR_V0_LIMITS["max_static_qr_decoded_json_bytes"]:
        raise ValueError("QR decoded JSON exceeds max_static_qr_decoded_json_bytes")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{QR_ENVELOPE_PREFIX}{encoded}"


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _animated_frame_checksum(digest: str, index: int, total: int, chunk: str) -> str:
    return _sha256_hex(f"{ANIMATED_QR_ENVELOPE_PREFIX}{digest}:{index}/{total}:{chunk}".encode("utf-8"))[:16]


def encode_animated_qr_envelope_frames(value: object, *, chunk_size_chars: Optional[int] = None) -> list[str]:
    import base64

    chunk_size = chunk_size_chars or NSEALR_V0_LIMITS["max_animated_qr_frame_payload_chars"]
    if chunk_size <= 0:
        raise ValueError("animated QR chunk size must be a positive integer")
    if chunk_size > NSEALR_V0_LIMITS["max_animated_qr_frame_payload_chars"]:
        raise ValueError("animated QR chunk exceeds max_animated_qr_frame_payload_chars")
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > NSEALR_V0_LIMITS["max_animated_qr_decoded_json_bytes"]:
        raise ValueError("animated QR decoded JSON exceeds max_animated_qr_decoded_json_bytes")
    digest = _sha256_hex(payload)
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    chunks = [encoded[index : index + chunk_size] for index in range(0, len(encoded), chunk_size)]
    if not chunks:
        raise ValueError("animated QR payload is empty")
    if len(chunks) > NSEALR_V0_LIMITS["max_animated_qr_frame_count"]:
        raise ValueError("animated QR frame count exceeds max_animated_qr_frame_count")
    total = len(chunks)
    return [
        f"{ANIMATED_QR_ENVELOPE_PREFIX}{digest}:{index}/{total}:{chunk}:{_animated_frame_checksum(digest, index, total, chunk)}"
        for index, chunk in enumerate(chunks, start=1)
    ]


def decode_qr_envelope(envelope: str) -> object:
    import base64
    import binascii

    if not envelope.startswith(QR_ENVELOPE_PREFIX):
        raise ValueError("QR envelope requires nsealr1 prefix")
    payload = envelope[len(QR_ENVELOPE_PREFIX) :]
    _assert_base64url(payload)
    padding = "=" * (-len(payload) % 4)
    try:
        decoded_bytes = base64.b64decode(f"{payload}{padding}".encode("ascii"), altchars=b"-_", validate=True)
    except binascii.Error as exc:
        raise ValueError("QR envelope payload must decode as base64url") from exc
    if len(decoded_bytes) > NSEALR_V0_LIMITS["max_static_qr_decoded_json_bytes"]:
        raise ValueError("QR decoded JSON exceeds max_static_qr_decoded_json_bytes")
    try:
        decoded = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("QR envelope payload must be valid UTF-8") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("QR envelope payload is not valid JSON") from exc


def _parse_animated_frame(frame: str) -> tuple[str, int, int, str]:
    if not frame.startswith(ANIMATED_QR_ENVELOPE_PREFIX):
        raise ValueError("animated QR frame requires nsealr1a prefix")
    parts = frame.split(":")
    if len(parts) != 5 or parts[0] != "nsealr1a":
        raise ValueError("animated QR frame is malformed")
    digest, index_total, chunk, checksum = parts[1], parts[2], parts[3], parts[4]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("animated QR digest must be 32-byte lowercase hex")
    if len(checksum) != 16 or any(char not in "0123456789abcdef" for char in checksum):
        raise ValueError("animated QR checksum must be 8-byte lowercase hex")
    if "/" not in index_total:
        raise ValueError("animated QR index must use index/total")
    index_text, total_text = index_total.split("/", 1)
    if not index_text.isdecimal() or not total_text.isdecimal():
        raise ValueError("animated QR index and total must be decimal")
    index = int(index_text)
    total = int(total_text)
    if index < 1 or total < 1 or index > total:
        raise ValueError("animated QR frame index is out of range")
    if total > NSEALR_V0_LIMITS["max_animated_qr_frame_count"]:
        raise ValueError("animated QR frame count exceeds max_animated_qr_frame_count")
    _assert_base64url(chunk)
    if len(chunk) > NSEALR_V0_LIMITS["max_animated_qr_frame_payload_chars"]:
        raise ValueError("animated QR chunk exceeds max_animated_qr_frame_payload_chars")
    if checksum != _animated_frame_checksum(digest, index, total, chunk):
        raise ValueError("animated QR frame checksum mismatch")
    return digest, index, total, chunk


def decode_animated_qr_envelope_frames(frames: list[str]) -> object:
    import base64
    import binascii

    if not frames:
        raise ValueError("animated QR requires at least one frame")
    parsed = [_parse_animated_frame(frame) for frame in frames]
    digest = parsed[0][0]
    total = parsed[0][2]
    if any(item[0] != digest or item[2] != total for item in parsed):
        raise ValueError("animated QR frame set mismatch")
    if len(parsed) != total:
        raise ValueError("animated QR frames must be unique and contiguous")
    by_index: dict[int, str] = {}
    for _, index, _, chunk in parsed:
        if index in by_index:
            raise ValueError("animated QR frames must be unique and contiguous")
        by_index[index] = chunk
    try:
        encoded = "".join(by_index[index] for index in range(1, total + 1))
    except KeyError as exc:
        raise ValueError("animated QR frames must be unique and contiguous") from exc
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded_bytes = base64.b64decode(f"{encoded}{padding}".encode("ascii"), altchars=b"-_", validate=True)
    except binascii.Error as exc:
        raise ValueError("animated QR payload must decode as base64url") from exc
    if len(decoded_bytes) > NSEALR_V0_LIMITS["max_animated_qr_decoded_json_bytes"]:
        raise ValueError("animated QR decoded JSON exceeds max_animated_qr_decoded_json_bytes")
    if _sha256_hex(decoded_bytes) != digest:
        raise ValueError("animated QR decoded digest mismatch")
    try:
        decoded = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("animated QR payload must be valid UTF-8") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("animated QR payload is not valid JSON") from exc
