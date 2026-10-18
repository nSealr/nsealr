from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .controls import ButtonAction, ReviewControlSession
from .display import DisplayFrameLimits, render_display_frame
from .seed_entry import SessionImportSource, session_source_backup_payload, session_source_backup_review


class SessionSourceBackupFlowError(RuntimeError):
    pass


class SessionSourceBackupIO(Protocol):
    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        """Render one bounded backup review frame before reading a button."""

    def read_review_button(self) -> ButtonAction:
        """Return one local physical review action."""

    def emit_backup_payload(self, backup_payload: dict[str, str]) -> None:
        """Reveal the recovery payload only after local final-page approval."""


class _ButtonSequenceExhausted(RuntimeError):
    pass


@dataclass(frozen=True)
class SessionSourceBackupTranscriptStep:
    page_index: int
    button: ButtonAction
    decision: bool | None
    revealed: bool


@dataclass(frozen=True)
class SessionSourceBackupFlowResult:
    review: dict[str, Any]
    approved: bool
    revealed: bool
    backup_payload: dict[str, str] | None
    transcript: list[SessionSourceBackupTranscriptStep]


def run_session_source_backup_flow(
    source: SessionImportSource,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionSourceBackupFlowResult:
    button_iter = iter(buttons)

    def read_button() -> ButtonAction:
        try:
            return next(button_iter)
        except StopIteration as exc:
            raise _ButtonSequenceExhausted from exc

    return _run_session_source_backup_control_loop(
        source,
        read_button=read_button,
        max_button_steps=max_button_steps,
    )


def run_session_source_backup_io_flow(
    source: SessionImportSource,
    io: SessionSourceBackupIO,
    *,
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
    max_button_steps: int = 32,
) -> SessionSourceBackupFlowResult:
    return _run_session_source_backup_control_loop(
        source,
        read_button=io.read_review_button,
        display_frame=lambda review, page_index: io.display_review_frame(
            review,
            page_index,
            render_display_frame(review, page_index, display_limits),
        ),
        emit_backup_payload=io.emit_backup_payload,
        max_button_steps=max_button_steps,
    )


def _run_session_source_backup_control_loop(
    source: SessionImportSource,
    *,
    read_button: Callable[[], ButtonAction],
    display_frame: Callable[[dict[str, Any], int], None] | None = None,
    emit_backup_payload: Callable[[dict[str, str]], None] | None = None,
    max_button_steps: int = 32,
) -> SessionSourceBackupFlowResult:
    if max_button_steps <= 0:
        raise SessionSourceBackupFlowError("session source backup flow max button steps must be positive")

    review = session_source_backup_review(source)
    controls = ReviewControlSession({"pages": review["pages"]})
    transcript: list[SessionSourceBackupTranscriptStep] = []

    for _step_count in range(1, max_button_steps + 1):
        page_index = controls.page_index
        if display_frame is not None:
            display_frame(review, page_index)
        try:
            button = read_button()
        except _ButtonSequenceExhausted as exc:
            raise SessionSourceBackupFlowError("session source backup review did not reach approval or rejection") from exc
        decision = controls.handle_button(button)
        revealed = decision is True
        transcript.append(SessionSourceBackupTranscriptStep(page_index, button, decision, revealed))
        if decision is not None:
            backup_payload = session_source_backup_payload(source) if revealed else None
            if backup_payload is not None and emit_backup_payload is not None:
                emit_backup_payload(backup_payload)
            return SessionSourceBackupFlowResult(
                review,
                approved=decision,
                revealed=revealed,
                backup_payload=backup_payload,
                transcript=transcript,
            )

    raise SessionSourceBackupFlowError("session source backup review exceeded max button steps")
