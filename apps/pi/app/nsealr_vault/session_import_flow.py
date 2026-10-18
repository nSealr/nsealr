from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .controls import ButtonAction, ReviewControlSession
from .display import DisplayFrameLimits, render_display_frame
from .seed_entry import (
    SessionImportSource,
    public_key_from_session_import_source,
    secret_key_from_session_import_source,
    session_import_review,
)


MAX_STATELESS_SESSION_SOURCES = 8


class SessionImportFlowError(RuntimeError):
    pass


class SessionImportReviewIO(Protocol):
    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        """Render one bounded session-import review frame before reading a button."""

    def read_review_button(self) -> ButtonAction:
        """Return one local physical review action."""


class _ButtonSequenceExhausted(RuntimeError):
    pass


@dataclass
class _SessionKeyringEntry:
    source_type: str
    label: str
    bip39_word_indexes: list[int] = field(default_factory=list)
    nsec_secret_key: bytearray = field(default_factory=bytearray)

    @classmethod
    def from_source(cls, source: SessionImportSource) -> "_SessionKeyringEntry":
        session_import_review(source)
        return cls(
            source_type=source.source_type,
            label=source.label,
            bip39_word_indexes=list(source.bip39_word_indexes),
            nsec_secret_key=bytearray.fromhex(source.nsec_secret_key) if source.nsec_secret_key else bytearray(),
        )

    def to_source(self) -> SessionImportSource:
        if self.source_type == "bip39_seed":
            return SessionImportSource.bip39_seed(self.label, tuple(self.bip39_word_indexes))
        if self.source_type == "nsec":
            return SessionImportSource.nsec(self.label, self.nsec_secret_key.hex())
        raise SessionImportFlowError("session key source has been wiped")

    def wipe(self) -> None:
        for index in range(len(self.bip39_word_indexes)):
            self.bip39_word_indexes[index] = 0
        for index in range(len(self.nsec_secret_key)):
            self.nsec_secret_key[index] = 0
        self.label = ""
        self.source_type = "wiped"


@dataclass
class StatelessSessionKeyring:
    max_sources: int = MAX_STATELESS_SESSION_SOURCES
    _sources: list[_SessionKeyringEntry] = field(default_factory=list, init=False)

    def __del__(self) -> None:
        try:
            self.clear()
        except Exception:
            pass

    def add_source(self, source: SessionImportSource) -> None:
        if len(self._sources) >= self.max_sources:
            raise SessionImportFlowError("stateless session keyring is full")
        self._sources.append(_SessionKeyringEntry.from_source(source))

    def clear(self) -> None:
        for source in self._sources:
            source.wipe()
        self._sources.clear()

    @property
    def empty(self) -> bool:
        return not self._sources

    @property
    def size(self) -> int:
        return len(self._sources)

    def source_at(self, index: int) -> SessionImportSource:
        try:
            return self._sources[index].to_source()
        except IndexError as exc:
            raise SessionImportFlowError("session key source index is out of range") from exc

    def public_key_at(self, index: int, *, account: int = 0, passphrase: str = "") -> str:
        return public_key_from_session_import_source(
            self.source_at(index),
            account=account,
            passphrase=passphrase,
        )


@dataclass
class StatelessSessionSecretProvider:
    keyring: StatelessSessionKeyring
    source_index: int = 0
    account: int = 0
    passphrase: str = ""
    _consumed: bool = False

    def public_key(self) -> str:
        return self.keyring.public_key_at(
            self.source_index,
            account=self.account,
            passphrase=self.passphrase,
        )

    def __call__(self) -> str:
        if self._consumed:
            raise RuntimeError("stateless session source has already been consumed")
        self._consumed = True
        return secret_key_from_session_import_source(
            self.keyring.source_at(self.source_index),
            account=self.account,
            passphrase=self.passphrase,
        )


@dataclass(frozen=True)
class SessionImportTranscriptStep:
    page_index: int
    button: ButtonAction
    decision: bool | None
    loaded: bool


@dataclass(frozen=True)
class SessionImportFlowResult:
    review: dict[str, Any]
    approved: bool
    loaded: bool
    transcript: list[SessionImportTranscriptStep]


def run_session_import_flow(
    keyring: StatelessSessionKeyring,
    source: SessionImportSource,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    button_iter = iter(buttons)

    def read_button() -> ButtonAction:
        try:
            return next(button_iter)
        except StopIteration as exc:
            raise _ButtonSequenceExhausted from exc

    return _run_session_import_control_loop(
        keyring,
        source,
        read_button=read_button,
        max_button_steps=max_button_steps,
    )


def run_session_import_io_flow(
    keyring: StatelessSessionKeyring,
    source: SessionImportSource,
    io: SessionImportReviewIO,
    *,
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    return _run_session_import_control_loop(
        keyring,
        source,
        read_button=io.read_review_button,
        display_frame=lambda review, page_index: io.display_review_frame(
            review,
            page_index,
            render_display_frame(review, page_index, display_limits),
        ),
        max_button_steps=max_button_steps,
    )


def _run_session_import_control_loop(
    keyring: StatelessSessionKeyring,
    source: SessionImportSource,
    *,
    read_button: Callable[[], ButtonAction],
    display_frame: Callable[[dict[str, Any], int], None] | None = None,
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    if max_button_steps <= 0:
        raise SessionImportFlowError("session import flow max button steps must be positive")

    review = session_import_review(source)
    controls = ReviewControlSession({"pages": review["pages"]})
    transcript: list[SessionImportTranscriptStep] = []

    for _step_count in range(1, max_button_steps + 1):
        page_index = controls.page_index
        if display_frame is not None:
            display_frame(review, page_index)
        try:
            button = read_button()
        except _ButtonSequenceExhausted as exc:
            raise SessionImportFlowError("session import review did not reach approval or rejection") from exc
        decision = controls.handle_button(button)
        loaded = False
        if decision is True:
            keyring.add_source(source)
            loaded = True
        transcript.append(SessionImportTranscriptStep(page_index, button, decision, loaded))
        if decision is not None:
            return SessionImportFlowResult(review, approved=decision, loaded=loaded, transcript=transcript)

    raise SessionImportFlowError("session import review exceeded max button steps")
