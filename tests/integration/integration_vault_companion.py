#!/usr/bin/env python3
"""Run the first integrated QR smoke test."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
RASPBERRY = ROOT / "apps/pi"
SPECS = ROOT / "protocols/contracts/v1"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]
    stdin_text: str | None = None


def run(command: list[str] | CommandPlan, cwd: Path | None = None) -> None:
    if isinstance(command, CommandPlan):
        run_command(command.argv, command.cwd, input=command.stdin_text)
        return
    if cwd is None:
        raise ValueError("cwd is required when running a raw command")
    run_command(command, cwd)


def build_review_commands(
    *,
    companion: Path,
    raspberry: Path,
    request_path: Path,
    author_pubkey: str,
    companion_review_path: Path,
    vault_review_path: Path,
) -> list[CommandPlan]:
    return [
        CommandPlan(
            cwd=companion,
            argv=[
                "pnpm",
                "nsealr",
                "review-request",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--author-pubkey",
                author_pubkey,
                "--out",
                str(companion_review_path),
            ],
        ),
        CommandPlan(
            cwd=raspberry,
            argv=[
                str(raspberry / ".venv/bin/python"),
                "-m",
                "nsealr_vault",
                "review",
                "--request",
                str(request_path),
                "--review",
                str(vault_review_path),
                "--input-format",
                "qr",
                "--author-pubkey",
                author_pubkey,
            ],
        ),
    ]


def build_screen_review_commands(
    *,
    companion: Path,
    raspberry: Path,
    request_path: Path,
    author_pubkey: str,
    companion_screen_review_path: Path,
    vault_screen_review_path: Path,
) -> list[CommandPlan]:
    return [
        CommandPlan(
            cwd=companion,
            argv=[
                "pnpm",
                "nsealr",
                "review-request",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--screen-review",
                "--author-pubkey",
                author_pubkey,
                "--out",
                str(companion_screen_review_path),
            ],
        ),
        CommandPlan(
            cwd=raspberry,
            argv=[
                str(raspberry / ".venv/bin/python"),
                "-m",
                "nsealr_vault",
                "review",
                "--request",
                str(request_path),
                "--review",
                str(vault_screen_review_path),
                "--input-format",
                "qr",
                "--output-format",
                "screen-json",
                "--author-pubkey",
                author_pubkey,
            ],
        ),
    ]


def build_review_detail_pages_command(
    *,
    raspberry: Path,
    request_path: Path,
    author_pubkey: str,
    detail_pages_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "review",
            "--request",
            str(request_path),
            "--review",
            str(detail_pages_path),
            "--input-format",
            "qr",
            "--author-pubkey",
            author_pubkey,
            "--output-format",
            "detail-pages-json",
            "--max-title-chars",
            "18",
            "--max-body-lines",
            "5",
            "--max-line-chars",
            "26",
            "--max-compact-body-lines",
            "9",
            "--max-compact-line-chars",
            "48",
        ],
    )


def build_companion_review_detail_pages_command(
    *,
    companion: Path,
    request_path: Path,
    author_pubkey: str,
    detail_pages_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "review-request",
            "--request",
            str(request_path),
            "--request-format",
            "qr",
            "--detail-pages",
            "--author-pubkey",
            author_pubkey,
            "--max-title-chars",
            "18",
            "--max-body-lines",
            "5",
            "--max-line-chars",
            "26",
            "--max-compact-body-lines",
            "9",
            "--max-compact-line-chars",
            "48",
            "--out",
            str(detail_pages_path),
        ],
    )


def assert_json_files_equal(left: Path, right: Path) -> None:
    left_json = json.loads(left.read_text(encoding="utf-8"))
    right_json = json.loads(right.read_text(encoding="utf-8"))
    if left_json != right_json:
        raise AssertionError(f"review JSON mismatch: {left} != {right}")


def assert_screen_review_files_equal(actual: Path, expected: Path) -> None:
    actual_json = json.loads(actual.read_text(encoding="utf-8"))
    expected_json = json.loads(expected.read_text(encoding="utf-8"))
    if actual_json != expected_json:
        raise AssertionError(f"screen-review JSON mismatch: {actual} != {expected}")


def assert_screen_review_shape(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "screen-pages":
        raise AssertionError(f"screen-review format mismatch: {path}")
    if not isinstance(payload.get("approval_digest"), str) or len(payload["approval_digest"]) != 64:
        raise AssertionError(f"screen-review approval digest mismatch: {path}")
    pages = payload.get("pages")
    if not isinstance(pages, list):
        raise AssertionError(f"screen-review pages must be a list: {path}")
    titles = [page.get("title") for page in pages if isinstance(page, dict)]
    if titles != ["Event", "Content", "Tags", "Decision"]:
        raise AssertionError(f"screen-review page titles mismatch: {path}")
    if pages[-1].get("action") != "approve_or_reject":
        raise AssertionError(f"screen-review must end with approval decision: {path}")


def assert_review_detail_pages(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages = payload.get("pages") if isinstance(payload, dict) else payload
    if not isinstance(pages, list):
        raise AssertionError(f"review detail pages must be a list: {path}")
    titles = [page.get("title") for page in pages if isinstance(page, dict)]
    if not titles or titles[0] != "Event" or "Content" not in titles or "Tags" not in titles or titles[-1] != "Decision":
        raise AssertionError(f"review detail page titles mismatch: {path}")
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            raise AssertionError(f"review detail page {index} must be an object: {path}")
        if not isinstance(page.get("page_indicator"), str) or not page["page_indicator"].startswith("Page "):
            raise AssertionError(f"review detail page indicator missing at page {index}: {path}")
        lines = page.get("lines")
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise AssertionError(f"review detail page lines must be strings at page {index}: {path}")
        styles = page.get("body_line_styles")
        if not isinstance(styles, list):
            raise AssertionError(f"review detail page body_line_styles must be a list at page {index}: {path}")
        if styles and len(styles) != len(lines):
            raise AssertionError(f"review detail page style count mismatch at page {index}: {path}")
    if pages[-1].get("action") != "approve_or_reject":
        raise AssertionError(f"review detail pages must end with approval decision: {path}")


def assert_display_frame_log(path: Path, *, max_line_chars: int = 64) -> None:
    frames = json.loads(path.read_text(encoding="utf-8"))
    expected_titles = ["Event", "Content", "Tags", "Decision"]
    if [frame.get("title") for frame in frames] != expected_titles:
        raise AssertionError(f"display-frame log titles mismatch: {path}")
    for index, frame in enumerate(frames, start=1):
        if frame.get("page_indicator") != f"Page {index}/{len(expected_titles)}":
            raise AssertionError(f"display-frame page indicator mismatch at frame {index}: {path}")
        lines = frame.get("body_lines")
        if not isinstance(lines, list):
            raise AssertionError(f"display-frame body_lines must be a list at frame {index}: {path}")
        if any(not isinstance(line, str) or len(line) > max_line_chars for line in lines):
            raise AssertionError(f"display-frame line width exceeded at frame {index}: {path}")
    if frames[-1].get("action_hint") != "Approve / Reject":
        raise AssertionError(f"display-frame log must end with approval hint: {path}")


def assert_review_transcript_log(path: Path, display_frame_log_path: Path, buttons: list[str]) -> None:
    transcript = json.loads(path.read_text(encoding="utf-8"))
    display_frames = json.loads(display_frame_log_path.read_text(encoding="utf-8"))
    if not isinstance(transcript, list):
        raise AssertionError(f"review-transcript log must be a list: {path}")
    if not isinstance(display_frames, list):
        raise AssertionError(f"display-frame log must be a list: {display_frame_log_path}")
    if len(transcript) != len(display_frames) or len(transcript) != len(buttons):
        raise AssertionError(f"review-transcript length mismatch: {path}")
    if transcript != [
        {
            "frame": frame,
            "button": button,
            "decision": None if index < len(buttons) - 1 else button == "approve",
            "approved_for_signing": index == len(buttons) - 1 and button == "approve",
        }
        for index, (frame, button) in enumerate(zip(display_frames, buttons))
    ]:
        raise AssertionError(f"review-transcript log mismatch: {path} != displayed frames/buttons")


def mnemonic_words_stdin(mnemonic: str) -> str:
    words = mnemonic.split()
    if not words:
        raise ValueError("mnemonic must contain at least one BIP-39 word")
    return "\n".join(words) + "\n"


def build_flow_command(
    *,
    raspberry: Path,
    mnemonic: str,
    account: int,
    request_path: Path,
    screen_review_path: Path,
    response_path: Path,
    display_frame_log_path: Path,
    review_transcript_log_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "flow",
            "--mnemonic-words-stdin",
            "--mnemonic-word-count",
            str(len(mnemonic.split())),
            "--account",
            str(account),
            "--request",
            str(request_path),
            "--review",
            str(screen_review_path),
            "--response",
            str(response_path),
            "--button-sequence",
            "next,next,next,approve",
            "--display-frame-log",
            str(display_frame_log_path),
            "--review-transcript-log",
            str(review_transcript_log_path),
            "--max-line-chars",
            "64",
        ],
        stdin_text=mnemonic_words_stdin(mnemonic),
    )


def build_detail_flow_command(
    *,
    raspberry: Path,
    mnemonic: str,
    account: int,
    request_path: Path,
    detail_review_path: Path,
    response_path: Path,
    output_format: str = "qr",
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "flow",
            "--mnemonic-words-stdin",
            "--mnemonic-word-count",
            str(len(mnemonic.split())),
            "--account",
            str(account),
            "--request",
            str(request_path),
            "--review",
            str(detail_review_path),
            "--response",
            str(response_path),
            "--output-format",
            output_format,
            "--button-sequence",
            "next,next,next,approve",
            "--review-mode",
            "detail",
        ],
        stdin_text=mnemonic_words_stdin(mnemonic),
    )


def build_standard_seedqr_flow_command(
    *,
    raspberry: Path,
    standard_seedqr_digits: str,
    request_path: Path,
    screen_review_path: Path,
    response_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "flow",
            "--seedqr-stdin",
            "--request",
            str(request_path),
            "--review",
            str(screen_review_path),
            "--response",
            str(response_path),
            "--button-sequence",
            "next,next,next,approve",
        ],
        stdin_text=standard_seedqr_digits + "\n",
    )


def build_nsec_flow_command(
    *,
    raspberry: Path,
    nsec: str,
    request_path: Path,
    screen_review_path: Path,
    response_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "flow",
            "--nsec-stdin",
            "--request",
            str(request_path),
            "--review",
            str(screen_review_path),
            "--response",
            str(response_path),
            "--button-sequence",
            "next,next,next,approve",
        ],
        stdin_text=nsec + "\n",
    )


def build_session_import_review_command(
    *,
    raspberry: Path,
    source_argument: str,
    label: str,
    source_text: str,
    review_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "review-import",
            source_argument,
            "--label",
            label,
            "--out",
            str(review_path),
        ],
        stdin_text=source_text + "\n",
    )


def build_session_backup_source_command(
    *,
    raspberry: Path,
    source_argument: str,
    label: str,
    source_text: str,
    result_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "backup-source",
            source_argument,
            "--label",
            label,
            "--button-sequence",
            "next,approve",
            "--out",
            str(result_path),
        ],
        stdin_text=source_text + "\n",
    )


def assert_session_import_review_file(path: Path, vector: dict[str, object], forbidden_values: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("review_id", "approval_digest", "pages"):
        if payload.get(key) != vector.get(key):
            raise AssertionError(f"session import review {key} mismatch: {path}")
    rendered = json.dumps(payload, ensure_ascii=False)
    for value in forbidden_values:
        if value and value in rendered:
            raise AssertionError(f"session import review leaks source material: {path}")


def assert_session_backup_result_file(path: Path, vector: dict[str, object], forbidden_values: list[str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "nsealr-session-source-backup-result-v0":
        raise AssertionError(f"session backup result format mismatch: {path}")
    if payload.get("approved") is not True or payload.get("revealed") is not True:
        raise AssertionError(f"session backup result must be approved and revealed: {path}")
    if payload.get("backup_payload") != vector.get("backup_payload"):
        raise AssertionError(f"session backup payload mismatch: {path}")
    review = payload.get("review")
    if not isinstance(review, dict):
        raise AssertionError(f"session backup review must be an object: {path}")
    for key in ("review_id", "approval_digest", "pages"):
        if review.get(key) != vector.get(key):
            raise AssertionError(f"session backup review {key} mismatch: {path}")
    rendered_review = json.dumps(review, ensure_ascii=False)
    for value in forbidden_values:
        if value and value in rendered_review:
            raise AssertionError(f"session backup review leaks source material: {path}")
    transcript = payload.get("transcript")
    if not isinstance(transcript, list) or not transcript or transcript[-1].get("revealed") is not True:
        raise AssertionError(f"session backup transcript must end with reveal: {path}")


def main() -> int:
    for repo in (COMPANION, RASPBERRY, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    run(["make", "setup"], RASPBERRY)

    request = json.loads((SPECS / "examples/request-kind-1-basic.json").read_text(encoding="utf-8"))
    nip06_key = json.loads((SPECS / "vectors/keys/nip06-account-0-leader.json").read_text(encoding="utf-8"))
    seedqr_vector = json.loads((SPECS / "vectors/seedqr/seedsigner-vector-1.json").read_text(encoding="utf-8"))
    nsec_vector = json.loads((SPECS / "vectors/nip19/nsec-test-key-1.json").read_text(encoding="utf-8"))
    seedqr_import_review_vector = json.loads(
        (SPECS / "vectors/session-import-reviews/seedqr-vector-1.json").read_text(encoding="utf-8")
    )
    nsec_import_review_vector = json.loads(
        (SPECS / "vectors/session-import-reviews/nsec-test-key-1.json").read_text(encoding="utf-8")
    )
    seedqr_backup_vector = json.loads(
        (SPECS / "vectors/session-source-backups/seedqr-vector-1-backup.json").read_text(encoding="utf-8")
    )
    nsec_backup_vector = json.loads(
        (SPECS / "vectors/session-source-backups/nsec-test-key-1-backup.json").read_text(encoding="utf-8")
    )

    with tempfile.TemporaryDirectory(prefix="nsealr-integrated-") as temp_dir:
        temp = Path(temp_dir)
        template_path = temp / "template.json"
        request_path = temp / "request.qr"
        companion_review_path = temp / "companion-review.json"
        vault_review_path = temp / "vault-review.json"
        companion_screen_review_path = temp / "companion-screen-review.json"
        vault_screen_review_path = temp / "vault-screen-review.json"
        companion_detail_pages_path = temp / "companion-detail-pages.json"
        vault_detail_pages_path = temp / "vault-detail-pages.json"
        screen_review_path = temp / "screen-review.json"
        display_frame_log_path = temp / "display-frames.json"
        review_transcript_log_path = temp / "review-transcript.json"
        response_path = temp / "response.qr"
        detail_flow_review_path = temp / "detail-flow-review.json"
        detail_flow_response_path = temp / "detail-flow-response.qr"
        detail_flow_animated_response_path = temp / "detail-flow-response.qra"
        seedqr_flow_review_path = temp / "seedqr-flow-review.json"
        seedqr_flow_response_path = temp / "seedqr-flow-response.qr"
        nsec_flow_review_path = temp / "nsec-flow-review.json"
        nsec_flow_response_path = temp / "nsec-flow-response.qr"
        seedqr_import_review_path = temp / "seedqr-import-review.json"
        nsec_import_review_path = temp / "nsec-import-review.json"
        seedqr_backup_result_path = temp / "seedqr-backup-result.json"
        nsec_backup_result_path = temp / "nsec-backup-result.json"

        template_path.write_text(
            json.dumps(request["params"]["event_template"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        run(
            [
                "pnpm",
                "nsealr",
                "request",
                "sign-event",
                "--event-template",
                str(template_path),
                "--out",
                str(request_path),
                "--output-format",
                "qr",
            ],
            COMPANION,
        )
        for command in build_review_commands(
            companion=COMPANION,
            raspberry=RASPBERRY,
            request_path=request_path,
            author_pubkey=nip06_key["public_key"],
            companion_review_path=companion_review_path,
            vault_review_path=vault_review_path,
        ):
            run(command.argv, command.cwd)
        assert_json_files_equal(companion_review_path, vault_review_path)
        for command in build_screen_review_commands(
            companion=COMPANION,
            raspberry=RASPBERRY,
            request_path=request_path,
            author_pubkey=nip06_key["public_key"],
            companion_screen_review_path=companion_screen_review_path,
            vault_screen_review_path=vault_screen_review_path,
        ):
            run(command.argv, command.cwd)
        assert_json_files_equal(companion_screen_review_path, vault_screen_review_path)
        seedqr_import_review_command = build_session_import_review_command(
            raspberry=RASPBERRY,
            source_argument="--seedqr-stdin",
            label=str(seedqr_import_review_vector["label"]),
            source_text=str(seedqr_vector["standard_seedqr_digits"]),
            review_path=seedqr_import_review_path,
        )
        run(seedqr_import_review_command)
        assert_session_import_review_file(
            seedqr_import_review_path,
            seedqr_import_review_vector,
            seedqr_vector["mnemonic"].split(),
        )
        nsec_import_review_command = build_session_import_review_command(
            raspberry=RASPBERRY,
            source_argument="--nsec-stdin",
            label=str(nsec_import_review_vector["label"]),
            source_text=str(nsec_vector["nsec"]),
            review_path=nsec_import_review_path,
        )
        run(nsec_import_review_command)
        assert_session_import_review_file(
            nsec_import_review_path,
            nsec_import_review_vector,
            [nsec_vector["nsec"], nsec_vector["secret_key"]],
        )
        seedqr_backup_command = build_session_backup_source_command(
            raspberry=RASPBERRY,
            source_argument="--seedqr-stdin",
            label=str(seedqr_backup_vector["label"]),
            source_text=str(seedqr_vector["standard_seedqr_digits"]),
            result_path=seedqr_backup_result_path,
        )
        run(seedqr_backup_command)
        assert_session_backup_result_file(
            seedqr_backup_result_path,
            seedqr_backup_vector,
            seedqr_vector["mnemonic"].split(),
        )
        nsec_backup_command = build_session_backup_source_command(
            raspberry=RASPBERRY,
            source_argument="--nsec-stdin",
            label=str(nsec_backup_vector["label"]),
            source_text=str(nsec_vector["nsec"]),
            result_path=nsec_backup_result_path,
        )
        run(nsec_backup_command)
        assert_session_backup_result_file(
            nsec_backup_result_path,
            nsec_backup_vector,
            [nsec_vector["nsec"], nsec_vector["secret_key"]],
        )
        companion_detail_pages_command = build_companion_review_detail_pages_command(
            companion=COMPANION,
            request_path=request_path,
            author_pubkey=nip06_key["public_key"],
            detail_pages_path=companion_detail_pages_path,
        )
        run(companion_detail_pages_command.argv, companion_detail_pages_command.cwd)
        detail_pages_command = build_review_detail_pages_command(
            raspberry=RASPBERRY,
            request_path=request_path,
            author_pubkey=nip06_key["public_key"],
            detail_pages_path=vault_detail_pages_path,
        )
        run(detail_pages_command.argv, detail_pages_command.cwd)
        assert_json_files_equal(companion_detail_pages_path, vault_detail_pages_path)
        assert_review_detail_pages(vault_detail_pages_path)
        flow_command = build_flow_command(
            raspberry=RASPBERRY,
            mnemonic=nip06_key["mnemonic"],
            account=nip06_key["account"],
            request_path=request_path,
            screen_review_path=screen_review_path,
            response_path=response_path,
            display_frame_log_path=display_frame_log_path,
            review_transcript_log_path=review_transcript_log_path,
        )
        run(flow_command)
        assert_screen_review_files_equal(screen_review_path, companion_screen_review_path)
        assert_display_frame_log(display_frame_log_path)
        assert_review_transcript_log(
            review_transcript_log_path,
            display_frame_log_path,
            ["next", "next", "next", "approve"],
        )
        run(
            [
                "pnpm",
                "nsealr",
                "verify-response",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--response",
                str(response_path),
                "--response-format",
                "qr",
            ],
            COMPANION,
        )
        detail_flow_command = build_detail_flow_command(
            raspberry=RASPBERRY,
            mnemonic=nip06_key["mnemonic"],
            account=nip06_key["account"],
            request_path=request_path,
            detail_review_path=detail_flow_review_path,
            response_path=detail_flow_response_path,
        )
        run(detail_flow_command)
        detail_review = json.loads(detail_flow_review_path.read_text(encoding="utf-8"))
        if detail_review.get("format") != "review-detail-pages-v0":
            raise AssertionError(f"detail flow review format mismatch: {detail_flow_review_path}")
        assert_review_detail_pages(detail_flow_review_path)
        run(
            [
                "pnpm",
                "nsealr",
                "verify-response",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--response",
                str(detail_flow_response_path),
                "--response-format",
                "qr",
            ],
            COMPANION,
        )
        detail_flow_animated_command = build_detail_flow_command(
            raspberry=RASPBERRY,
            mnemonic=nip06_key["mnemonic"],
            account=nip06_key["account"],
            request_path=request_path,
            detail_review_path=detail_flow_review_path,
            response_path=detail_flow_animated_response_path,
            output_format="qr-animated",
        )
        run(detail_flow_animated_command)
        run(
            [
                "pnpm",
                "nsealr",
                "verify-response",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--response",
                str(detail_flow_animated_response_path),
                "--response-format",
                "qr-animated",
            ],
            COMPANION,
        )
        seedqr_flow_command = build_standard_seedqr_flow_command(
            raspberry=RASPBERRY,
            standard_seedqr_digits=seedqr_vector["standard_seedqr_digits"],
            request_path=request_path,
            screen_review_path=seedqr_flow_review_path,
            response_path=seedqr_flow_response_path,
        )
        run(seedqr_flow_command)
        assert_screen_review_shape(seedqr_flow_review_path)
        run(
            [
                "pnpm",
                "nsealr",
                "verify-response",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--response",
                str(seedqr_flow_response_path),
                "--response-format",
                "qr",
            ],
            COMPANION,
        )
        nsec_flow_command = build_nsec_flow_command(
            raspberry=RASPBERRY,
            nsec=nsec_vector["nsec"],
            request_path=request_path,
            screen_review_path=nsec_flow_review_path,
            response_path=nsec_flow_response_path,
        )
        run(nsec_flow_command)
        assert_screen_review_shape(nsec_flow_review_path)
        run(
            [
                "pnpm",
                "nsealr",
                "verify-response",
                "--request",
                str(request_path),
                "--request-format",
                "qr",
                "--response",
                str(nsec_flow_response_path),
                "--response-format",
                "qr",
            ],
            COMPANION,
        )

    print("nSealr integrated Raspberry QR flow/companion smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
