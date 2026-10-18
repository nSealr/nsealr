from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .controls import ButtonAction, LogicalReviewControlSession, ReviewControlSession
from .crypto import xonly_pubkey_from_secret
from .display import (
    DisplayFrameLimits,
    ReviewDetailPageLimits,
    render_display_frame,
    render_review_detail_frame,
    render_review_detail_pages,
    screen_review_for_request,
)
from .qr import (
    ANIMATED_QR_ENVELOPE_PREFIX,
    QR_ENVELOPE_PREFIX,
    decode_animated_qr_envelope_frames,
    decode_qr_envelope,
    encode_qr_envelope,
)
from .review import review_event_template
from .signer import sign_request


class QrVaultIO(Protocol):
    def scan_request_qr(self) -> str:
        """Return one scanned nSealr QR envelope."""

    def show_review(self, screen_review: dict[str, Any]) -> bool:
        """Display trusted review pages and return the physical approval result."""

    def emit_response_qr(self, response_qr: str) -> None:
        """Publish one QR envelope response for the host to scan."""


class ButtonQrVaultIO(Protocol):
    def scan_request_qr(self) -> str:
        """Return one scanned nSealr QR envelope."""

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        """Render one bounded trusted review frame before reading the next physical button."""

    def read_review_button(self) -> ButtonAction:
        """Return the next physical button action."""

    def emit_response_qr(self, response_qr: str) -> None:
        """Publish one QR envelope response for the host to scan."""


@dataclass(frozen=True)
class QrVaultFlowResult:
    request_id: str
    approved: bool
    approval_digest: str
    response: dict[str, Any]
    review_transcript: list[dict[str, Any]] | None = None


def run_qr_vault_flow(
    io: QrVaultIO,
    secret_key_hex: str,
    response_encoder: Callable[[dict[str, Any]], str] = encode_qr_envelope,
) -> QrVaultFlowResult:
    request = _decode_scanned_request_qr(io.scan_request_qr())
    if not isinstance(request, dict):
        raise ValueError("QR vault flow requires a JSON object request")

    author_pubkey = xonly_pubkey_from_secret(secret_key_hex)
    screen_review = screen_review_for_request(request, author_pubkey=author_pubkey)
    approval_digest = str(screen_review["approval_digest"])
    approved = io.show_review(screen_review)
    response = sign_request(
        request,
        secret_key_hex,
        approved=approved,
        approval_digest=approval_digest,
    )
    io.emit_response_qr(response_encoder(response))
    return QrVaultFlowResult(
        request_id=str(request["request_id"]),
        approved=approved,
        approval_digest=approval_digest,
        response=response,
    )


def run_button_qr_vault_flow(
    io: ButtonQrVaultIO,
    secret_key_hex: str,
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
    max_button_steps: int = 32,
    response_encoder: Callable[[dict[str, Any]], str] = encode_qr_envelope,
) -> QrVaultFlowResult:
    return run_button_qr_vault_flow_with_secret_provider(
        io,
        lambda: secret_key_hex,
        display_limits=display_limits,
        max_button_steps=max_button_steps,
        response_encoder=response_encoder,
    )


def run_button_qr_vault_flow_with_secret_provider(
    io: ButtonQrVaultIO,
    secret_key_provider: Callable[[], str],
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
    max_button_steps: int = 32,
    response_encoder: Callable[[dict[str, Any]], str] = encode_qr_envelope,
) -> QrVaultFlowResult:
    if max_button_steps <= 0:
        raise ValueError("button review flow max steps must be positive")

    request = _decode_scanned_request_qr(io.scan_request_qr())
    if not isinstance(request, dict):
        raise ValueError("QR vault flow requires a JSON object request")

    secret_key_hex = secret_key_provider()
    author_pubkey = xonly_pubkey_from_secret(secret_key_hex)
    screen_review = screen_review_for_request(request, author_pubkey=author_pubkey)
    approval_digest = str(screen_review["approval_digest"])
    session = ReviewControlSession(screen_review)
    approved: bool | None = None
    review_transcript: list[dict[str, Any]] = []

    for _ in range(max_button_steps):
        frame = render_display_frame(screen_review, session.page_index, display_limits)
        io.display_review_frame(screen_review, session.page_index, frame)
        button = io.read_review_button()
        approved = session.handle_button(button)
        review_transcript.append(
            {
                "frame": frame,
                "button": button,
                "decision": approved,
                "approved_for_signing": session.approved,
            }
        )
        if approved is not None:
            break

    if approved is None:
        raise RuntimeError("button review flow did not reach approval or rejection")

    response = sign_request(
        request,
        secret_key_hex,
        approved=approved,
        approval_digest=approval_digest,
    )
    io.emit_response_qr(response_encoder(response))
    return QrVaultFlowResult(
        request_id=str(request["request_id"]),
        approved=approved,
        approval_digest=approval_digest,
        response=response,
        review_transcript=review_transcript,
    )


def run_detail_button_qr_vault_flow(
    io: ButtonQrVaultIO,
    secret_key_hex: str,
    detail_limits: ReviewDetailPageLimits = ReviewDetailPageLimits(),
    max_button_steps: int = 32,
    response_encoder: Callable[[dict[str, Any]], str] = encode_qr_envelope,
) -> QrVaultFlowResult:
    return run_detail_button_qr_vault_flow_with_secret_provider(
        io,
        lambda: secret_key_hex,
        detail_limits=detail_limits,
        max_button_steps=max_button_steps,
        response_encoder=response_encoder,
    )


def run_detail_button_qr_vault_flow_with_secret_provider(
    io: ButtonQrVaultIO,
    secret_key_provider: Callable[[], str],
    detail_limits: ReviewDetailPageLimits = ReviewDetailPageLimits(),
    max_button_steps: int = 32,
    response_encoder: Callable[[dict[str, Any]], str] = encode_qr_envelope,
) -> QrVaultFlowResult:
    if max_button_steps <= 0:
        raise ValueError("button review flow max steps must be positive")

    request = _decode_scanned_request_qr(io.scan_request_qr())
    if not isinstance(request, dict):
        raise ValueError("QR vault flow requires a JSON object request")

    secret_key_hex = secret_key_provider()
    author_pubkey = xonly_pubkey_from_secret(secret_key_hex)
    screen_review = screen_review_for_request(request, author_pubkey=author_pubkey)
    approval_digest = str(screen_review["approval_digest"])
    params = request.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
        raise ValueError("detail QR vault flow requires params.event_template")
    detail_review = {
        "format": "review-detail-pages-v0",
        "request_id": request["request_id"],
        "approval_digest": approval_digest,
        "display_profile": "ascii-safe-codepoint-fallback-v0",
        "pages": render_review_detail_pages(
            review_event_template(params["event_template"], author_pubkey=author_pubkey),
            limits=detail_limits,
        ),
    }
    session = LogicalReviewControlSession(detail_review)
    approved: bool | None = None
    review_transcript: list[dict[str, Any]] = []

    for _ in range(max_button_steps):
        frame = render_review_detail_frame(detail_review, session.page_index, limits=detail_limits)
        if session.can_scroll and frame["action_hint"] == "Next":
            frame["action_hint"] = "Next/Scroll"
        io.display_review_frame(detail_review, session.page_index, frame)
        button = io.read_review_button()
        approved = session.handle_button(button)
        review_transcript.append(
            {
                "frame": frame,
                "button": button,
                "decision": approved,
                "approved_for_signing": session.approved,
            }
        )
        if approved is not None:
            break

    if approved is None:
        raise RuntimeError("button review flow did not reach approval or rejection")

    response = sign_request(
        request,
        secret_key_hex,
        approved=approved,
        approval_digest=approval_digest,
    )
    io.emit_response_qr(response_encoder(response))
    return QrVaultFlowResult(
        request_id=str(request["request_id"]),
        approved=approved,
        approval_digest=approval_digest,
        response=response,
        review_transcript=review_transcript,
    )


def _decode_scanned_request_qr(scanned_qr: str) -> object:
    frames = [line.strip() for line in scanned_qr.splitlines() if line.strip()]
    if not frames:
        raise ValueError("QR vault flow requires a scanned request QR")
    if len(frames) == 1 and frames[0].startswith(QR_ENVELOPE_PREFIX):
        return decode_qr_envelope(frames[0])
    if all(frame.startswith(ANIMATED_QR_ENVELOPE_PREFIX) for frame in frames):
        return decode_animated_qr_envelope_frames(frames)
    if len(frames) == 1:
        return decode_qr_envelope(frames[0])
    raise ValueError("QR vault flow requires static nsealr1 or animated nsealr1a request QR")
