from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from .st7789_layout import layout_seed_signer_st7789_review_frame


class QrScanner(Protocol):
    def scan_request_qr(self) -> str:
        """Return one scanned nSealr request QR envelope."""


class ReviewDisplay(Protocol):
    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        """Render one bounded trusted review frame."""


class ReviewButtonInput(Protocol):
    def read_review_button(self) -> str:
        """Return one physical review button action."""


class ResponseQrDisplay(Protocol):
    def emit_response_qr(self, response_qr: str) -> None:
        """Display or export one nSealr response QR envelope."""


class ComposedButtonQrVaultIO:
    def __init__(
        self,
        *,
        scanner: QrScanner,
        review_display: ReviewDisplay,
        button_input: ReviewButtonInput,
        response_display: ResponseQrDisplay,
    ) -> None:
        self.scanner = scanner
        self.review_display = review_display
        self.button_input = button_input
        self.response_display = response_display

    def scan_request_qr(self) -> str:
        return self.scanner.scan_request_qr()

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        self.review_display.display_review_frame(screen_review, page_index, frame)

    def read_review_button(self) -> str:
        return self.button_input.read_review_button()

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_display.emit_response_qr(response_qr)


class FileQrVaultIO:
    def __init__(self, request: Path, review: Path, response: Path, approved: bool) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.approved = approved

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def show_review(self, screen_review: dict[str, Any]) -> bool:
        self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.approved

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")


class FileButtonQrVaultIO:
    def __init__(
        self,
        request: Path,
        review: Path,
        response: Path,
        buttons: list[str],
        display_frame_log: Path | None = None,
        st7789_layout_log: Path | None = None,
    ) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.buttons = list(buttons)
        self.display_frame_log = display_frame_log
        self.st7789_layout_log = st7789_layout_log
        self.display_frames: list[dict[str, Any]] = []
        self.st7789_layouts: list[list[dict[str, object]]] = []
        self._wrote_review = False

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        if not self._wrote_review:
            self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self._wrote_review = True
        if self.display_frame_log is not None:
            self.display_frames.append(frame)
            self.display_frame_log.write_text(
                json.dumps(self.display_frames, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if self.st7789_layout_log is not None:
            self.st7789_layouts.append(layout_seed_signer_st7789_review_frame(frame))
            self.st7789_layout_log.write_text(
                json.dumps(self.st7789_layouts, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("button sequence ended before approval or rejection")
        return self.buttons.pop(0)

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")
