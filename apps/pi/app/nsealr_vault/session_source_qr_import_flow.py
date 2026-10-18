from __future__ import annotations

from .controls import ButtonAction
from .session_import_flow import SessionImportFlowResult, StatelessSessionKeyring, run_session_import_flow
from .session_source_qr import parse_compact_seedqr_session_source, parse_session_source_qr_text


def run_session_source_qr_text_import_flow(
    keyring: StatelessSessionKeyring,
    label: str,
    decoded_text: str,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    source = parse_session_source_qr_text(label, decoded_text)
    return run_session_import_flow(keyring, source, buttons, max_button_steps=max_button_steps)


def run_compact_seedqr_session_import_flow(
    keyring: StatelessSessionKeyring,
    label: str,
    entropy: bytes,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    source = parse_compact_seedqr_session_source(label, entropy)
    return run_session_import_flow(keyring, source, buttons, max_button_steps=max_button_steps)
