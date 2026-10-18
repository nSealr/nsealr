from __future__ import annotations

from .seed_entry import (
    SessionImportSource,
    bip39_word_indexes_from_mnemonic,
    mnemonic_from_compact_seedqr,
    mnemonic_from_standard_seedqr,
    secret_key_from_nsec,
)


class SessionSourceQrError(RuntimeError):
    pass


def _trim_ascii_whitespace(value: str) -> str:
    start = 0
    while start < len(value) and value[start] in " \n\r\t":
        start += 1
    end = len(value)
    while end > start and value[end - 1] in " \n\r\t":
        end -= 1
    return value[start:end]


def _is_standard_seedqr_digit_stream(value: str) -> bool:
    saw_digit = False
    for char in value:
        if char in " \n\r\t":
            continue
        if char < "0" or char > "9":
            return False
        saw_digit = True
    return saw_digit


def parse_session_source_qr_text(label: str, decoded_text: str) -> SessionImportSource:
    text = _trim_ascii_whitespace(decoded_text)
    if not text:
        raise SessionSourceQrError("decoded session QR text must not be empty")

    try:
        if text.startswith("nsec1"):
            return SessionImportSource.nsec(label, secret_key_from_nsec(text))
        if _is_standard_seedqr_digit_stream(text):
            mnemonic = mnemonic_from_standard_seedqr(text)
            return SessionImportSource.bip39_seed(label, bip39_word_indexes_from_mnemonic(mnemonic))
        return SessionImportSource.bip39_seed(label, bip39_word_indexes_from_mnemonic(text))
    except ValueError as exc:
        raise SessionSourceQrError(str(exc)) from exc


def parse_compact_seedqr_session_source(label: str, entropy: bytes) -> SessionImportSource:
    try:
        mnemonic = mnemonic_from_compact_seedqr(entropy)
        return SessionImportSource.bip39_seed(label, bip39_word_indexes_from_mnemonic(mnemonic))
    except ValueError as exc:
        raise SessionSourceQrError(str(exc)) from exc
