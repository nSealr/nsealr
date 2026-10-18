from __future__ import annotations

from typing import Any


SEEDSIGNER_ST7789_WIDTH = 240
SEEDSIGNER_ST7789_HEIGHT = 240
BODY_AREA_BOTTOM = 208

_MARGIN = 8
_TITLE_Y = 8
_PAGE_Y = 10
_BODY_Y = 44
_FOOTER_Y = 216
_GLYPH_WIDTH = 6
_GLYPH_HEIGHT = 7
_BODY_LINE_HEIGHT_NORMAL = 20
_BODY_LINE_HEIGHT_COMPACT = 12

_BODY_STYLE_COLORS = {
    "meta": "green",
    "value": "yellow",
    "normal": "white",
}


def layout_seed_signer_st7789_review_frame(
    frame: dict[str, Any],
    *,
    width: int = SEEDSIGNER_ST7789_WIDTH,
    height: int = SEEDSIGNER_ST7789_HEIGHT,
) -> list[dict[str, object]]:
    """Build bounded draw commands for a SeedSigner-compatible 240x240 ST7789."""

    if width <= 0 or height <= 0:
        raise ValueError("display dimensions must be positive")

    title = str(frame.get("title", ""))
    page_indicator = str(frame.get("page_indicator", ""))
    action_hint = str(frame.get("action_hint", ""))
    body_lines = frame.get("body_lines", [])
    if not isinstance(body_lines, list):
        raise ValueError("review frame body_lines must be a list")
    body_styles = frame.get("body_line_styles", [])
    if body_styles is None:
        body_styles = []
    if not isinstance(body_styles, list):
        raise ValueError("review frame body_line_styles must be a list")

    commands: list[dict[str, object]] = [
        _rect("background", 0, 0, width, height, "black"),
        _text("title", title, _MARGIN, _TITLE_Y, 2, "white", max_width=150),
        _text(
            "page_indicator",
            page_indicator,
            max(_MARGIN, width - _MARGIN - _text_width(page_indicator, 1)),
            _PAGE_Y,
            1,
            "green",
        ),
    ]

    y = _BODY_Y
    for index, line in enumerate(body_lines):
        style = str(body_styles[index]) if index < len(body_styles) else "normal"
        if style not in _BODY_STYLE_COLORS:
            style = "normal"
        scale = 2 if style == "normal" else 1
        line_height = _BODY_LINE_HEIGHT_NORMAL if style == "normal" else _BODY_LINE_HEIGHT_COMPACT
        command = _text(
            "body_line",
            str(line),
            _MARGIN,
            y,
            scale,
            _BODY_STYLE_COLORS[style],
            style=style,
            max_width=width - (_MARGIN * 2),
        )
        if command["y"] + command["height"] >= BODY_AREA_BOTTOM:
            raise ValueError("body lines exceed display body area")
        commands.append(command)
        y += line_height

    commands.append(_text("action_hint", action_hint, _MARGIN, _FOOTER_Y, 2, "green", max_width=width - (_MARGIN * 2)))
    _validate_bounds(commands, width, height)
    return commands


def _rect(role: str, x: int, y: int, width: int, height: int, color: str) -> dict[str, object]:
    return {
        "type": "rect",
        "role": role,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "color": color,
    }


def _text(
    role: str,
    text: str,
    x: int,
    y: int,
    scale: int,
    color: str,
    *,
    style: str | None = None,
    max_width: int | None = None,
) -> dict[str, object]:
    width = _text_width(text, scale)
    if max_width is not None:
        width = min(width, max_width)
    command: dict[str, object] = {
        "type": "text",
        "role": role,
        "text": text,
        "x": x,
        "y": y,
        "width": width,
        "height": _GLYPH_HEIGHT * scale,
        "scale": scale,
        "color": color,
    }
    if style is not None:
        command["style"] = style
    return command


def _text_width(text: str, scale: int) -> int:
    if not text:
        return 0
    return len(text) * _GLYPH_WIDTH * scale


def _validate_bounds(commands: list[dict[str, object]], width: int, height: int) -> None:
    for command in commands:
        x = int(command["x"])
        y = int(command["y"])
        command_width = int(command["width"])
        command_height = int(command["height"])
        if x < 0 or y < 0 or x + command_width > width or y + command_height > height:
            raise ValueError(f"{command['role']} draw command is outside display bounds")
