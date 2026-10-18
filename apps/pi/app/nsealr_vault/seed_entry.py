from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import secrets
from typing import Callable, Protocol

from mnemonic import Mnemonic

from .crypto import xonly_pubkey_from_secret
from .nip06 import derive_nip06_secret


VALID_MNEMONIC_WORD_COUNTS = (12, 15, 18, 21, 24)
_ENGLISH_MNEMONIC = Mnemonic("english")
_ENGLISH_WORDLIST = frozenset(_ENGLISH_MNEMONIC.wordlist)
_ENGLISH_WORDS = tuple(_ENGLISH_MNEMONIC.wordlist)
SEEDQR_WORD_COUNTS = (12, 24)
COMPACT_SEEDQR_BYTE_LENGTHS = {
    16: 12,
    32: 24,
}
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CHARSET_REV = {char: index for index, char in enumerate(BECH32_CHARSET)}
HEX32_RE = re.compile(r"^[0-9a-f]{64}$")
SECP256K1_ORDER = int("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141", 16)
BIP39_GENERATION_ENTROPY_BYTES = {
    12: 16,
    24: 32,
}


class MnemonicWordInput(Protocol):
    def read_mnemonic_word(self, word_index: int, word_count: int) -> str:
        """Return one user-entered BIP-39 word for a RAM-only signing session."""


def normalize_mnemonic_words(words: list[str] | tuple[str, ...]) -> str:
    normalized = [word.strip().lower() for word in words]
    if any(not word for word in normalized):
        raise ValueError("mnemonic words must not be empty")
    if len(normalized) not in VALID_MNEMONIC_WORD_COUNTS:
        counts = ", ".join(str(count) for count in VALID_MNEMONIC_WORD_COUNTS)
        raise ValueError(f"mnemonic word count must be one of {counts}")

    unknown = [word for word in normalized if word not in _ENGLISH_WORDLIST]
    if unknown:
        raise ValueError(f"mnemonic word is not in the BIP-39 English wordlist: {unknown[0]}")

    mnemonic = " ".join(normalized)
    if not _ENGLISH_MNEMONIC.check(mnemonic):
        raise ValueError("mnemonic failed BIP-39 checksum validation")
    return mnemonic


def bip39_word_indexes_from_mnemonic(mnemonic: str) -> tuple[int, ...]:
    normalized = normalize_mnemonic_words(mnemonic.split())
    return tuple(_ENGLISH_WORDS.index(word) for word in normalized.split())


def mnemonic_from_bip39_word_indexes(word_indexes: list[int] | tuple[int, ...]) -> str:
    indexes = tuple(word_indexes)
    count = len(indexes)
    if count not in VALID_MNEMONIC_WORD_COUNTS:
        counts = ", ".join(str(value) for value in VALID_MNEMONIC_WORD_COUNTS)
        raise ValueError(f"BIP-39 word index count must be one of {counts}")
    if any(index < 0 or index >= len(_ENGLISH_WORDS) for index in indexes):
        raise ValueError("BIP-39 word index is outside the English wordlist")
    return normalize_mnemonic_words([_ENGLISH_WORDS[index] for index in indexes])


def mnemonic_from_standard_seedqr(value: str) -> str:
    seedqr = "".join(value.split())
    if not seedqr:
        raise ValueError("SeedQR digit stream must not be empty")
    if not seedqr.isdigit():
        raise ValueError("SeedQR digit stream must contain only digits")
    if len(seedqr) % 4 != 0:
        raise ValueError("SeedQR digit stream length must be divisible by four")
    word_count = len(seedqr) // 4
    if word_count not in SEEDQR_WORD_COUNTS:
        counts = ", ".join(str(count) for count in SEEDQR_WORD_COUNTS)
        raise ValueError(f"SeedQR word count must be one of {counts}")

    words: list[str] = []
    for offset in range(0, len(seedqr), 4):
        index = int(seedqr[offset:offset + 4])
        if index >= len(_ENGLISH_WORDS):
            raise ValueError("SeedQR word index is outside the BIP-39 English wordlist")
        words.append(_ENGLISH_WORDS[index])
    return normalize_mnemonic_words(words)


def mnemonic_from_compact_seedqr(value: bytes) -> str:
    if len(value) not in COMPACT_SEEDQR_BYTE_LENGTHS:
        allowed = ", ".join(str(length) for length in sorted(COMPACT_SEEDQR_BYTE_LENGTHS))
        raise ValueError(f"CompactSeedQR byte length must be one of {allowed}")
    return normalize_mnemonic_words(_ENGLISH_MNEMONIC.to_mnemonic(value).split())


def _bech32_polymod(values: list[int]) -> int:
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _bech32_decode(value: str) -> tuple[str, list[int]]:
    candidate = value.strip()
    if candidate != candidate.lower():
        raise ValueError("nsec must be lowercase bech32")
    separator = candidate.rfind("1")
    if separator <= 0 or separator + 7 > len(candidate):
        raise ValueError("nsec bech32 payload is malformed")
    hrp = candidate[:separator]
    payload = candidate[separator + 1:]
    if any(char not in BECH32_CHARSET_REV for char in payload):
        raise ValueError("nsec bech32 payload contains unsupported characters")
    data = [BECH32_CHARSET_REV[char] for char in payload]
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != 1:
        raise ValueError("nsec bech32 checksum is invalid")
    return hrp, data[:-6]


def _convert_5bit_words_to_bytes(words: list[int]) -> bytes:
    accumulator = 0
    bit_count = 0
    out = bytearray()
    for word in words:
        if word < 0 or word > 31:
            raise ValueError("nsec bech32 word is out of range")
        accumulator = (accumulator << 5) | word
        bit_count += 5
        while bit_count >= 8:
            bit_count -= 8
            out.append((accumulator >> bit_count) & 0xFF)
    if bit_count >= 5 or ((accumulator << (8 - bit_count)) & 0xFF) != 0:
        raise ValueError("nsec bech32 payload has invalid padding")
    return bytes(out)


def _convert_bytes_to_5bit_words(data: bytes) -> list[int]:
    accumulator = 0
    bit_count = 0
    out: list[int] = []
    for byte in data:
        accumulator = (accumulator << 8) | byte
        bit_count += 8
        while bit_count >= 5:
            bit_count -= 5
            out.append((accumulator >> bit_count) & 31)
    if bit_count:
        out.append((accumulator << (5 - bit_count)) & 31)
    return out


def _bech32_checksum(hrp: str, data: list[int]) -> list[int]:
    polymod = _bech32_polymod(_bech32_hrp_expand(hrp) + data + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> (5 * (5 - index))) & 31 for index in range(6)]


def _validate_secret_key_hex(secret_key: str) -> None:
    if not HEX32_RE.fullmatch(secret_key):
        raise ValueError("secret key must be 32-byte lowercase hex")
    secret_int = int(secret_key, 16)
    if secret_int <= 0 or secret_int >= SECP256K1_ORDER:
        raise ValueError("secret key must be a valid secp256k1 scalar")


def secret_key_from_nsec(value: str) -> str:
    hrp, words = _bech32_decode(value)
    if hrp != "nsec":
        raise ValueError("nsec bech32 prefix must be nsec")
    secret = _convert_5bit_words_to_bytes(words)
    if len(secret) != 32:
        raise ValueError("nsec payload must decode to a 32-byte secret key")
    secret_key = secret.hex()
    _validate_secret_key_hex(secret_key)
    return secret_key


def nsec_from_secret_key(secret_key: str) -> str:
    _validate_secret_key_hex(secret_key)
    data = _convert_bytes_to_5bit_words(bytes.fromhex(secret_key))
    checksum = _bech32_checksum("nsec", data)
    return "nsec1" + "".join(BECH32_CHARSET[word] for word in data + checksum)


@dataclass(frozen=True)
class SessionImportSource:
    source_type: str
    label: str
    bip39_word_indexes: tuple[int, ...] = ()
    nsec_secret_key: str = ""

    @classmethod
    def bip39_seed(cls, label: str, word_indexes: list[int] | tuple[int, ...]) -> "SessionImportSource":
        return cls(source_type="bip39_seed", label=label, bip39_word_indexes=tuple(word_indexes))

    @classmethod
    def nsec(cls, label: str, secret_key: str) -> "SessionImportSource":
        _validate_secret_key_hex(secret_key)
        return cls(source_type="nsec", label=label, nsec_secret_key=secret_key)


def generate_bip39_session_source(
    label: str,
    *,
    word_count: int = 12,
    entropy: bytes | None = None,
    random_bytes: Callable[[int], bytes] = secrets.token_bytes,
) -> SessionImportSource:
    byte_count = BIP39_GENERATION_ENTROPY_BYTES.get(word_count)
    if byte_count is None:
        counts = ", ".join(str(count) for count in sorted(BIP39_GENERATION_ENTROPY_BYTES))
        raise ValueError(f"generated mnemonic word count must be one of {counts}")
    material = entropy if entropy is not None else random_bytes(byte_count)
    if not isinstance(material, bytes) or len(material) != byte_count:
        raise ValueError(f"generated mnemonic entropy must be {byte_count} bytes")
    mnemonic = _ENGLISH_MNEMONIC.to_mnemonic(material)
    return SessionImportSource.bip39_seed(label, bip39_word_indexes_from_mnemonic(mnemonic))


def generate_nsec_session_source(
    label: str,
    *,
    entropy: bytes | None = None,
    random_bytes: Callable[[int], bytes] = secrets.token_bytes,
    max_attempts: int = 128,
) -> SessionImportSource:
    if max_attempts <= 0:
        raise ValueError("nsec generation max_attempts must be positive")
    if entropy is not None:
        if not isinstance(entropy, bytes) or len(entropy) != 32:
            raise ValueError("generated nsec entropy must be 32 bytes")
        return SessionImportSource.nsec(label, entropy.hex())
    for _attempt in range(max_attempts):
        candidate = random_bytes(32)
        if not isinstance(candidate, bytes) or len(candidate) != 32:
            raise ValueError("generated nsec entropy must be 32 bytes")
        try:
            return SessionImportSource.nsec(label, candidate.hex())
        except ValueError:
            continue
    raise RuntimeError("failed to generate a valid nsec session source")


def _session_source_kind_label(source_type: str) -> str:
    if source_type == "bip39_seed":
        return "BIP-39 seed"
    if source_type == "nsec":
        return "NIP-19 nsec"
    raise ValueError("session import source type must be bip39_seed or nsec")


def _validate_session_import_source(source: SessionImportSource) -> None:
    if not source.label:
        raise ValueError("session import label must not be empty")
    if source.source_type == "bip39_seed":
        count = len(source.bip39_word_indexes)
        if count not in VALID_MNEMONIC_WORD_COUNTS:
            counts = ", ".join(str(value) for value in VALID_MNEMONIC_WORD_COUNTS)
            raise ValueError(f"session import BIP-39 word count must be one of {counts}")
        for index in source.bip39_word_indexes:
            if index < 0 or index >= len(_ENGLISH_WORDS):
                raise ValueError("session import BIP-39 word index is outside the English wordlist")
        return
    if source.source_type == "nsec":
        if not HEX32_RE.fullmatch(source.nsec_secret_key):
            raise ValueError("session import nsec source requires a 32-byte lowercase hex secret key")
        return
    _session_source_kind_label(source.source_type)


def session_import_source_fingerprint(source: SessionImportSource) -> str:
    _validate_session_import_source(source)
    material = bytearray(f"nsealr.session-key-source.v0\n{_session_source_kind_label(source.source_type)}\n".encode())
    if source.source_type == "bip39_seed":
        material.extend(f"{len(source.bip39_word_indexes)}\n".encode())
        for index in source.bip39_word_indexes:
            material.extend(index.to_bytes(2, "big"))
    else:
        material.extend(bytes.fromhex(source.nsec_secret_key))
    return hashlib.sha256(bytes(material)).hexdigest()[:16]


def session_import_review(source: SessionImportSource) -> dict[str, object]:
    fingerprint = session_import_source_fingerprint(source)
    digest_material = (
        "nsealr.session-import-review.v0\n"
        f"{_session_source_kind_label(source.source_type)}\n"
        f"{source.label}\n"
        f"{fingerprint}"
    ).encode()
    lines = [
        f"Type: {_session_source_kind_label(source.source_type)}",
        f"Label: {source.label}",
        f"Fingerprint: {fingerprint}",
    ]
    if source.source_type == "bip39_seed":
        lines.append(f"Words: {len(source.bip39_word_indexes)}")
    lines.append("Secret: hidden")
    return {
        "review_id": f"session-import-{fingerprint}",
        "approval_digest": hashlib.sha256(digest_material).hexdigest(),
        "pages": [
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
        ],
    }


def _standard_seedqr_from_word_indexes(word_indexes: tuple[int, ...]) -> str:
    if len(word_indexes) not in SEEDQR_WORD_COUNTS:
        counts = ", ".join(str(count) for count in SEEDQR_WORD_COUNTS)
        raise ValueError(f"SeedQR backup word count must be one of {counts}")
    return "".join(f"{index:04d}" for index in word_indexes)


def _compact_seedqr_from_word_indexes(word_indexes: tuple[int, ...]) -> str:
    mnemonic = mnemonic_from_bip39_word_indexes(word_indexes)
    entropy = bytes(_ENGLISH_MNEMONIC.to_entropy(mnemonic.split()))
    if len(entropy) not in COMPACT_SEEDQR_BYTE_LENGTHS:
        allowed = ", ".join(str(length) for length in sorted(COMPACT_SEEDQR_BYTE_LENGTHS))
        raise ValueError(f"CompactSeedQR backup entropy length must be one of {allowed}")
    return entropy.hex()


def _session_source_backup_format(source: SessionImportSource) -> str:
    _validate_session_import_source(source)
    if source.source_type == "bip39_seed":
        return "bip39_words_seedqr"
    if source.source_type == "nsec":
        return "nip19_nsec"
    raise ValueError("session backup source type must be bip39_seed or nsec")


def session_source_backup_payload(source: SessionImportSource) -> dict[str, str]:
    _validate_session_import_source(source)
    if source.source_type == "bip39_seed":
        return {
            "mnemonic": mnemonic_from_bip39_word_indexes(source.bip39_word_indexes),
            "standard_seedqr_digits": _standard_seedqr_from_word_indexes(source.bip39_word_indexes),
            "compact_seedqr_hex": _compact_seedqr_from_word_indexes(source.bip39_word_indexes),
        }
    if source.source_type == "nsec":
        return {"nsec": nsec_from_secret_key(source.nsec_secret_key)}
    raise ValueError("session backup source type must be bip39_seed or nsec")


def session_source_backup_review(source: SessionImportSource) -> dict[str, object]:
    fingerprint = session_import_source_fingerprint(source)
    backup_format = _session_source_backup_format(source)
    digest_material = (
        "nsealr.session-source-backup-review.v0\n"
        f"{_session_source_kind_label(source.source_type)}\n"
        f"{source.label}\n"
        f"{fingerprint}\n"
        f"{backup_format}"
    ).encode()
    if source.source_type == "bip39_seed":
        output = "words/SeedQR"
    else:
        output = "nsec QR/text"
    lines = [
        "Danger: secret export",
        f"Type: {_session_source_kind_label(source.source_type)}",
        f"Label: {source.label}",
        f"Fingerprint: {fingerprint}",
        f"Output: {output}",
        "Session RAM only",
    ]
    return {
        "review_id": f"session-backup-{fingerprint}",
        "approval_digest": hashlib.sha256(digest_material).hexdigest(),
        "pages": [
            {
                "title": "Backup source",
                "lines": lines,
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
        ],
    }


def secret_key_from_session_import_source(
    source: SessionImportSource,
    *,
    account: int = 0,
    passphrase: str = "",
) -> str:
    _validate_session_import_source(source)
    if source.source_type == "nsec":
        return source.nsec_secret_key
    mnemonic = mnemonic_from_bip39_word_indexes(source.bip39_word_indexes)
    return derive_nip06_secret(mnemonic, passphrase=passphrase, account=account)


def public_key_from_session_import_source(
    source: SessionImportSource,
    *,
    account: int = 0,
    passphrase: str = "",
) -> str:
    return xonly_pubkey_from_secret(
        secret_key_from_session_import_source(
            source,
            account=account,
            passphrase=passphrase,
        )
    )


def collect_mnemonic_words(word_input: MnemonicWordInput, word_count: int) -> str:
    if word_count not in VALID_MNEMONIC_WORD_COUNTS:
        counts = ", ".join(str(count) for count in VALID_MNEMONIC_WORD_COUNTS)
        raise ValueError(f"mnemonic word count must be one of {counts}")
    return normalize_mnemonic_words(
        [word_input.read_mnemonic_word(index, word_count) for index in range(1, word_count + 1)]
    )


@dataclass
class MnemonicSessionSecretProvider:
    word_input: MnemonicWordInput
    word_count: int = 12
    account: int = 0
    passphrase: str = ""
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session mnemonic has already been consumed")
        self._consumed = True
        mnemonic = collect_mnemonic_words(self.word_input, self.word_count)
        return derive_nip06_secret(mnemonic, passphrase=self.passphrase, account=self.account)


@dataclass
class SeedQrSessionSecretProvider:
    seedqr: str | bytes
    qr_format: str = "standard"
    account: int = 0
    passphrase: str = ""
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session SeedQR has already been consumed")
        self._consumed = True
        if self.qr_format == "standard":
            if not isinstance(self.seedqr, str):
                raise ValueError("standard SeedQR input must be text")
            mnemonic = mnemonic_from_standard_seedqr(self.seedqr)
        elif self.qr_format == "compact":
            if not isinstance(self.seedqr, bytes):
                raise ValueError("CompactSeedQR input must be bytes")
            mnemonic = mnemonic_from_compact_seedqr(self.seedqr)
        else:
            raise ValueError("SeedQR format must be standard or compact")
        return derive_nip06_secret(mnemonic, passphrase=self.passphrase, account=self.account)


@dataclass
class NsecSessionSecretProvider:
    nsec: str
    _consumed: bool = False

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("session nsec has already been consumed")
        self._consumed = True
        return secret_key_from_nsec(self.nsec)
