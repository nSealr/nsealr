from __future__ import annotations

from typing import Any

from .limits import NSEALR_V0_LIMITS, utf8_size


DEVELOPMENT_REVIEW_AUTHOR_PUBKEY = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"


def _require_template(template: dict[str, Any]) -> None:
    forbidden = sorted({"id", "pubkey", "sig"} & set(template))
    if forbidden:
        raise ValueError(f"event_template contains forbidden fields: {', '.join(forbidden)}")
    allowed = {"created_at", "kind", "tags", "content"}
    unknown = sorted(set(template) - allowed)
    if unknown:
        raise ValueError(f"event_template contains unknown fields: {', '.join(unknown)}")
    for field in ("created_at", "kind", "tags", "content"):
        if field not in template:
            raise ValueError(f"event_template missing {field}")
    if type(template["created_at"]) is not int or template["created_at"] < 0:
        raise ValueError("event_template created_at must be a non-negative safe integer")
    if template["created_at"] > NSEALR_V0_LIMITS["max_safe_integer"]:
        raise ValueError("event_template created_at exceeds max_safe_integer")
    if type(template["kind"]) is not int or template["kind"] < 0:
        raise ValueError("event_template kind must be a non-negative safe integer")
    if template["kind"] > NSEALR_V0_LIMITS["max_safe_integer"]:
        raise ValueError("event_template kind exceeds max_safe_integer")
    if not isinstance(template["content"], str):
        raise ValueError("content must be a string")
    if utf8_size(template["content"]) > NSEALR_V0_LIMITS["max_content_utf8_bytes"]:
        raise ValueError("event_template content exceeds max_content_utf8_bytes")
    if not isinstance(template["tags"], list):
        raise ValueError("event_template tags must be an array")
    if len(template["tags"]) > NSEALR_V0_LIMITS["max_tag_count"]:
        raise ValueError("event_template tags exceeds max_tag_count")
    total_tag_bytes = 0
    for tag_index, tag in enumerate(template["tags"]):
        if not isinstance(tag, list):
            raise ValueError(f"event_template tags[{tag_index}] must be an array")
        if len(tag) > NSEALR_V0_LIMITS["max_tag_fields_per_tag"]:
            raise ValueError(f"event_template tags[{tag_index}] exceeds max_tag_fields_per_tag")
        for field_index, item in enumerate(tag):
            if not isinstance(item, str):
                raise ValueError(f"event_template tags[{tag_index}][{field_index}] must be a string")
            item_bytes = utf8_size(item)
            total_tag_bytes += item_bytes
            if item_bytes > NSEALR_V0_LIMITS["max_tag_field_utf8_bytes"]:
                raise ValueError("event_template tag field exceeds max_tag_field_utf8_bytes")
    if total_tag_bytes > NSEALR_V0_LIMITS["max_total_tag_utf8_bytes"]:
        raise ValueError("event_template tags exceed max_total_tag_utf8_bytes")


def review_event_template(
    template: dict[str, Any],
    author_pubkey: str | None = DEVELOPMENT_REVIEW_AUTHOR_PUBKEY,
) -> dict[str, Any]:
    _require_template(template)

    kind = template["kind"]
    content = template["content"]
    tags = template["tags"]
    selected_author_pubkey = DEVELOPMENT_REVIEW_AUTHOR_PUBKEY if author_pubkey is None else author_pubkey

    return {
        "kind": kind,
        "created_at": template["created_at"],
        "author_pubkey": selected_author_pubkey,
        "content": content,
        "content_utf8_bytes": utf8_size(content),
        "tag_count": len(tags),
        "tags": tags,
    }
