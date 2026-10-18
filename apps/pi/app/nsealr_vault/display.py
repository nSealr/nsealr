from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import textwrap
from typing import Any

from .review import review_event_template


@dataclass(frozen=True)
class DisplayFrameLimits:
    max_title_chars: int = 24
    max_body_lines: int = 6
    max_line_chars: int = 32


@dataclass(frozen=True)
class ReviewDetailPageLimits:
    max_title_chars: int = 18
    max_body_lines: int = 5
    max_line_chars: int = 26
    max_compact_body_lines: int = 9
    max_compact_line_chars: int = 48


def render_display_frame(
    screen_review: dict[str, Any],
    page_index: int,
    limits: DisplayFrameLimits = DisplayFrameLimits(),
) -> dict[str, Any]:
    _validate_display_limits(limits)
    pages = screen_review.get("pages")
    if not isinstance(pages, list) or not all(isinstance(page, dict) for page in pages):
        raise ValueError("screen review pages must be a list of objects")
    if page_index < 0 or page_index >= len(pages):
        raise ValueError("screen review page index out of range")

    page = pages[page_index]
    return {
        "title": _truncate_for_display(str(page["title"]), limits.max_title_chars),
        "page_indicator": f"Page {page_index + 1}/{len(pages)}",
        "body_lines": _wrap_body_lines(page.get("lines"), limits),
        "action_hint": _action_hint(str(page.get("action"))),
    }


def render_review_detail_frame(
    detail_review: dict[str, Any],
    page_index: int,
    limits: ReviewDetailPageLimits = ReviewDetailPageLimits(),
) -> dict[str, Any]:
    _validate_detail_page_limits(limits)
    pages = detail_review.get("pages")
    if not isinstance(pages, list) or not all(isinstance(page, dict) for page in pages):
        raise ValueError("review detail pages must be a list of objects")
    if page_index < 0 or page_index >= len(pages):
        raise ValueError("review detail page index out of range")

    page = pages[page_index]
    lines = page.get("lines")
    if not isinstance(lines, list):
        raise ValueError("review detail page lines must be a list")
    styles = page.get("body_line_styles", [])
    if not isinstance(styles, list):
        raise ValueError("review detail page body_line_styles must be a list")
    body_lines, body_styles = _bounded_detail_frame_body_lines(lines, styles, limits)
    return {
        "title": str(page["title"]),
        "page_indicator": str(page.get("page_indicator") or f"Page {page_index + 1}/{len(pages)}"),
        "body_lines": body_lines,
        "action_hint": _action_hint(str(page.get("action"))),
        "body_line_styles": body_styles,
    }


def render_review_pages(review: dict[str, Any]) -> list[dict[str, object]]:
    return [
        {
            "title": "Event",
            "lines": [
                f"Kind {review['kind']}",
                f"Created {review['created_at']}",
                "Author",
                str(review["author_pubkey"]),
            ],
            "action": "next",
        },
        {
            "title": "Content",
            "lines": [str(review["content"])],
            "action": "next",
        },
        {
            "title": "Tags",
            "lines": _tag_lines(review),
            "action": "next",
        },
        {
            "title": "Decision",
            "lines": ["Approve signing only if all pages match."],
            "action": "approve_or_reject",
        },
    ]


def render_review_detail_pages(
    review: dict[str, Any],
    limits: ReviewDetailPageLimits = ReviewDetailPageLimits(),
) -> list[dict[str, object]]:
    _validate_detail_page_limits(limits)
    pages: list[dict[str, object]] = []
    _append_detail_pages(pages, "Event", *_detail_event_lines(review, limits), limits, 1, 4)
    _append_detail_pages(pages, "Content", *_detail_content_lines(review, limits), limits, 2, 4)
    _append_detail_pages(pages, "Tags", *_detail_tag_lines(review, limits), limits, 3, 4)
    pages.append(
        {
            "title": "Decision",
            "lines": ["Approve signing only if all pages match."],
            "action": "approve_or_reject",
            "page_indicator": "Page 4/4",
            "body_line_styles": [],
            "logical_page_id": "Decision",
        }
    )
    return pages


def _tag_lines(review: dict[str, Any]) -> list[str]:
    tag_count = int(review["tag_count"])
    if tag_count == 0:
        return ["No tags"]
    lines: list[str] = []
    for index, tag in enumerate(review["tags"], start=1):
        lines.append(f"Tag {index}/{tag_count}")
        if tag:
            lines.extend(str(item) for item in tag)
        else:
            lines.append("empty tag")
    return lines


_DISPLAY_SAFE_ASCII = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " !\"#$%&'()*+,-./:;<=>?@[\\]_{|}~"
)


def _display_safe_text(text: str) -> str:
    out: list[str] = []
    for char in text:
        codepoint = ord(char)
        if char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif char == "\r":
            out.append("\\r")
        elif char == "\b":
            out.append("\\b")
        elif char == "\f":
            out.append("\\f")
        elif codepoint <= 0x7F and char in _DISPLAY_SAFE_ASCII:
            out.append(char)
        else:
            out.append(f"U+{codepoint:04X}")
    return "".join(out)


def _split_exact_display_lines(text: str, width: int) -> list[str]:
    if text == "":
        return [""]
    return [text[index:index + width] for index in range(0, len(text), width)]


def _append_detail_value_lines(lines: list[str], styles: list[str], value: str, width: int) -> None:
    for line in _split_exact_display_lines(value, width):
        lines.append(line)
        styles.append("value")


def _append_detail_tag_item_lines(lines: list[str], styles: list[str], value: str, width: int) -> None:
    if value == "":
        return
    safe_value = _display_safe_text(value)
    continuation_indent = "  "
    continuation_width = width - len(continuation_indent) if width > len(continuation_indent) else width
    position = 0
    first_line = True
    while position < len(safe_value):
        line_width = width if first_line else continuation_width
        line = safe_value[position:position + line_width]
        if not first_line and width > len(continuation_indent):
            line = continuation_indent + line
        lines.append(line)
        styles.append("value")
        position += line_width
        first_line = False


def _detail_event_lines(
    review: dict[str, Any],
    limits: ReviewDetailPageLimits,
) -> tuple[list[str], list[str]]:
    lines = [
        f"Kind {review['kind']}",
        f"Created {review['created_at']}",
        "Author",
    ]
    styles = ["meta", "meta", "meta"]
    _append_detail_tag_item_lines(lines, styles, str(review["author_pubkey"]), limits.max_compact_line_chars)
    return lines, styles


def _detail_content_lines(
    review: dict[str, Any],
    limits: ReviewDetailPageLimits,
) -> tuple[list[str], list[str]]:
    content = str(review["content"])
    if content == "":
        return ["empty content"], ["meta"]
    safe_content = _display_safe_text(content)
    if len(safe_content) <= limits.max_compact_line_chars:
        return [safe_content], ["normal"]
    lines = [f"bytes: {len(content.encode('utf-8'))}"]
    styles = ["meta"]
    _append_detail_value_lines(lines, styles, safe_content, limits.max_compact_line_chars)
    return lines, styles


def _detail_tag_lines(
    review: dict[str, Any],
    limits: ReviewDetailPageLimits,
) -> tuple[list[str], list[str]]:
    tags = review["tags"]
    if not tags:
        return ["No tags"], ["normal"]
    lines: list[str] = []
    styles: list[str] = []
    for index, tag in enumerate(tags, start=1):
        lines.append(f"Tag {index}/{len(tags)}")
        styles.append("meta")
        if tag:
            for item in tag:
                _append_detail_tag_item_lines(lines, styles, str(item), limits.max_compact_line_chars)
        else:
            lines.append("empty tag")
            styles.append("value")
    return lines, styles


def _detail_page_indicator(
    page_index: int,
    page_count: int,
    first_line: int,
    last_line: int,
    line_count: int,
) -> str:
    base = f"Page {page_index}/{page_count}"
    if line_count == 0 or (first_line == 1 and last_line >= line_count):
        return base
    return f"{base} Lines {first_line}-{last_line}/{line_count}"


def _append_detail_pages(
    pages: list[dict[str, object]],
    title: str,
    lines: list[str],
    styles: list[str],
    limits: ReviewDetailPageLimits,
    logical_page_index: int,
    logical_page_count: int,
) -> None:
    lines_per_screen = limits.max_compact_body_lines if styles else limits.max_body_lines
    total = len(lines) if lines else 1
    position = 0
    while position < total:
        first_position = position
        body_lines: list[str] = []
        body_styles: list[str] = []
        for _ in range(lines_per_screen):
            if position >= len(lines):
                break
            body_lines.append(lines[position])
            body_styles.append(styles[position] if position < len(styles) else "normal")
            position += 1
        if not body_lines:
            body_lines = [""]
            body_styles = ["normal"]
            position = total
        pages.append(
            {
                "title": title,
                "lines": body_lines,
                "action": "next",
                "page_indicator": _detail_page_indicator(
                    logical_page_index,
                    logical_page_count,
                    first_position + 1,
                    position,
                    total,
                ),
                "body_line_styles": body_styles,
                "logical_page_id": title,
            }
        )
        if position >= total:
            break


def _validate_display_limits(limits: DisplayFrameLimits) -> None:
    if limits.max_title_chars <= 0 or limits.max_body_lines <= 0 or limits.max_line_chars <= 0:
        raise ValueError("display limits must be positive")


def _validate_detail_page_limits(limits: ReviewDetailPageLimits) -> None:
    if (
        limits.max_title_chars <= 0
        or limits.max_body_lines <= 0
        or limits.max_line_chars <= 0
        or limits.max_compact_body_lines <= 0
        or limits.max_compact_line_chars <= 0
    ):
        raise ValueError("review detail-page limits must be positive")


def _wrap_body_lines(value: object, limits: DisplayFrameLimits) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("screen review page lines must be a list")

    wrapped: list[str] = []
    for line in value:
        text = str(line)
        if text == "":
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                text,
                width=limits.max_line_chars,
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )

    if len(wrapped) > limits.max_body_lines:
        wrapped = wrapped[: limits.max_body_lines]
        wrapped[-1] = _truncate_for_display(wrapped[-1], limits.max_line_chars, force_ellipsis=True)
    return [_truncate_for_display(line, limits.max_line_chars) for line in wrapped]


def _detail_frame_compact_style(style: str) -> bool:
    return style in {"meta", "value"}


def _bounded_detail_frame_body_lines(
    lines: list[Any],
    styles: list[Any],
    limits: ReviewDetailPageLimits,
) -> tuple[list[str], list[str]]:
    wrapped: list[str] = []
    wrapped_styles: list[str] = []
    has_compact_style = False
    for index, line in enumerate(lines):
        style = str(styles[index]) if index < len(styles) else "normal"
        has_compact_style = has_compact_style or _detail_frame_compact_style(style)
        width = limits.max_compact_line_chars if _detail_frame_compact_style(style) else limits.max_line_chars
        parts = _split_exact_display_lines(str(line), width)
        wrapped.extend(parts)
        wrapped_styles.extend([style] * len(parts))

    max_lines = limits.max_compact_body_lines if has_compact_style else limits.max_body_lines
    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
        wrapped_styles = wrapped_styles[:max_lines]
        style = wrapped_styles[-1] if wrapped_styles else "normal"
        width = limits.max_compact_line_chars if _detail_frame_compact_style(style) else limits.max_line_chars
        wrapped[-1] = _truncate_for_display(wrapped[-1], width, force_ellipsis=True)
    for index, line in enumerate(wrapped):
        style = wrapped_styles[index] if index < len(wrapped_styles) else "normal"
        width = limits.max_compact_line_chars if _detail_frame_compact_style(style) else limits.max_line_chars
        wrapped[index] = _truncate_for_display(line, width)
    return wrapped, wrapped_styles


def _truncate_for_display(text: str, max_chars: int, *, force_ellipsis: bool = False) -> str:
    if len(text) <= max_chars and not force_ellipsis:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return text[: max_chars - 3] + "..."


def _action_hint(action: str) -> str:
    if action == "next":
        return "Next"
    if action == "approve_or_reject":
        return "Approve / Reject"
    raise ValueError("unsupported review page action")


def screen_review_for_request(request: dict[str, Any], author_pubkey: str | None = None) -> dict[str, Any]:
    review = _review_for_request(request, author_pubkey=author_pubkey)
    pages = render_review_pages(review)
    return {
        "format": "screen-pages",
        "request_id": request["request_id"],
        "approval_digest": _approval_digest(request, review, pages),
        "pages": pages,
    }


def approval_digest_for_request(request: dict[str, Any], author_pubkey: str | None = None) -> str:
    review = _review_for_request(request, author_pubkey=author_pubkey)
    return _approval_digest(request, review, render_review_pages(review))


def _review_for_request(request: dict[str, Any], author_pubkey: str | None = None) -> dict[str, Any]:
    params = request.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
        raise ValueError("screen review requires params.event_template")
    if author_pubkey is None:
        return review_event_template(params["event_template"])
    return review_event_template(params["event_template"], author_pubkey=author_pubkey)


def _approval_digest(
    request: dict[str, Any],
    review: dict[str, Any],
    pages: list[dict[str, object]],
) -> str:
    payload = {
        "version": request["version"],
        "method": request["method"],
        "request_id": request["request_id"],
        "event_template": request["params"]["event_template"],
        "review": review,
        "pages": pages,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
