import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, utf8ToBytes } from "@noble/hashes/utils.js";

export type EventReview = {
  kind: number;
  created_at: number;
  author_pubkey: string;
  content: string;
  content_utf8_bytes: number;
  tag_count: number;
  tags: string[][];
};

export type ReviewPage = {
  title: string;
  lines: string[];
  action: "next" | "approve_or_reject";
};

export const REVIEW_DETAIL_BODY_LINE_STYLES = ["meta", "normal", "value"] as const;
export type ReviewBodyLineStyle = (typeof REVIEW_DETAIL_BODY_LINE_STYLES)[number];

export type ReviewDetailPageLimits = {
  max_title_chars: number;
  max_body_lines: number;
  max_line_chars: number;
  max_compact_body_lines: number;
  max_compact_line_chars: number;
};

export type ReviewDetailPage = ReviewPage & {
  page_indicator: string;
  body_line_styles: ReviewBodyLineStyle[];
  logical_page_id: string;
};

export type ScreenReview = {
  format: "screen-pages";
  request_id: string;
  approval_digest: string;
  pages: ReviewPage[];
};

export const DEVELOPMENT_REVIEW_AUTHOR_PUBKEY =
  "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

const DISPLAY_SAFE_ASCII = new Set(
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 !\"#$%&'()*+,-./:;<=>?@[\\]_{|}~".split("")
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function requireTemplate(value: unknown): {
  created_at: number;
  kind: number;
  tags: string[][];
  content: string;
} {
  if (!isRecord(value)) throw new Error("event_template must be an object");
  for (const field of ["created_at", "kind", "tags", "content"] as const) {
    if (!(field in value)) throw new Error(`event_template missing ${field}`);
  }
  if (!isNonNegativeInteger(value.created_at)) throw new Error("created_at must be a non-negative integer");
  if (!isNonNegativeInteger(value.kind)) throw new Error("kind must be a non-negative integer");
  if (typeof value.content !== "string") throw new Error("content must be a string");
  if (!Array.isArray(value.tags) || !value.tags.every((tag) => Array.isArray(tag) && tag.every((item) => typeof item === "string"))) {
    throw new Error("tags must be an array of string arrays");
  }
  return {
    created_at: value.created_at,
    kind: value.kind,
    tags: value.tags,
    content: value.content
  };
}

const UTF8_ENCODER = new TextEncoder();

function utf8ByteLength(value: string): number {
  return UTF8_ENCODER.encode(value).length;
}

function sha256Utf8Hex(value: string): string {
  return bytesToHex(sha256(utf8ToBytes(value)));
}

export function reviewEventTemplate(
  value: unknown,
  authorPubkey = DEVELOPMENT_REVIEW_AUTHOR_PUBKEY
): EventReview {
  const template = requireTemplate(value);

  return {
    kind: template.kind,
    created_at: template.created_at,
    author_pubkey: authorPubkey,
    content: template.content,
    content_utf8_bytes: utf8ByteLength(template.content),
    tag_count: template.tags.length,
    tags: template.tags
  };
}

function tagPageLines(review: EventReview): string[] {
  if (review.tag_count === 0) return ["No tags"];
  return review.tags.flatMap((tag, index) => {
    const lines = [`Tag ${index + 1}/${review.tag_count}`];
    if (tag.length === 0) return [...lines, "empty tag"];
    return [...lines, ...tag.map((item) => String(item))];
  });
}

function displaySafeText(text: string): string {
  const output: string[] = [];
  for (const char of text) {
    const codepoint = char.codePointAt(0);
    if (codepoint === undefined) throw new Error("invalid codepoint");
    if (char === "\n") {
      output.push("\\n");
    } else if (char === "\t") {
      output.push("\\t");
    } else if (char === "\r") {
      output.push("\\r");
    } else if (char === "\b") {
      output.push("\\b");
    } else if (char === "\f") {
      output.push("\\f");
    } else if (codepoint <= 0x7f && DISPLAY_SAFE_ASCII.has(char)) {
      output.push(char);
    } else {
      output.push(`U+${codepoint.toString(16).toUpperCase().padStart(4, "0")}`);
    }
  }
  return output.join("");
}

function splitExactDisplayLines(text: string, width: number): string[] {
  if (text === "") return [""];
  const lines: string[] = [];
  for (let index = 0; index < text.length; index += width) {
    lines.push(text.slice(index, index + width));
  }
  return lines;
}

function appendDetailValueLines(lines: string[], styles: ReviewBodyLineStyle[], value: string, width: number): void {
  for (const line of splitExactDisplayLines(value, width)) {
    lines.push(line);
    styles.push("value");
  }
}

function appendDetailTagItemLines(lines: string[], styles: ReviewBodyLineStyle[], value: string, width: number): void {
  if (value === "") return;
  const safeValue = displaySafeText(value);
  const continuationIndent = "  ";
  const continuationWidth = width > continuationIndent.length ? width - continuationIndent.length : width;
  let position = 0;
  let firstLine = true;
  while (position < safeValue.length) {
    const lineWidth = firstLine ? width : continuationWidth;
    let line = safeValue.slice(position, position + lineWidth);
    if (!firstLine && width > continuationIndent.length) line = continuationIndent + line;
    lines.push(line);
    styles.push("value");
    position += lineWidth;
    firstLine = false;
  }
}

function detailEventLines(review: EventReview, limits: ReviewDetailPageLimits): [string[], ReviewBodyLineStyle[]] {
  const lines = [`Kind ${review.kind}`, `Created ${review.created_at}`, "Author"];
  const styles: ReviewBodyLineStyle[] = ["meta", "meta", "meta"];
  appendDetailTagItemLines(lines, styles, String(review.author_pubkey), limits.max_compact_line_chars);
  return [lines, styles];
}

function detailContentLines(review: EventReview, limits: ReviewDetailPageLimits): [string[], ReviewBodyLineStyle[]] {
  if (review.content === "") return [["empty content"], ["meta"]];
  const safeContent = displaySafeText(review.content);
  if (safeContent.length <= limits.max_compact_line_chars) return [[safeContent], ["normal"]];
  const lines = [`bytes: ${utf8ByteLength(review.content)}`];
  const styles: ReviewBodyLineStyle[] = ["meta"];
  appendDetailValueLines(lines, styles, safeContent, limits.max_compact_line_chars);
  return [lines, styles];
}

function detailTagLines(review: EventReview, limits: ReviewDetailPageLimits): [string[], ReviewBodyLineStyle[]] {
  if (review.tags.length === 0) return [["No tags"], ["normal"]];
  const lines: string[] = [];
  const styles: ReviewBodyLineStyle[] = [];
  for (const [index, tag] of review.tags.entries()) {
    lines.push(`Tag ${index + 1}/${review.tags.length}`);
    styles.push("meta");
    if (tag.length === 0) {
      lines.push("empty tag");
      styles.push("value");
      continue;
    }
    for (const item of tag) appendDetailTagItemLines(lines, styles, String(item), limits.max_compact_line_chars);
  }
  return [lines, styles];
}

function detailPageIndicator(
  pageIndex: number,
  pageCount: number,
  firstLine: number,
  lastLine: number,
  lineCount: number
): string {
  const base = `Page ${pageIndex}/${pageCount}`;
  if (lineCount === 0 || (firstLine === 1 && lastLine >= lineCount)) return base;
  return `${base} Lines ${firstLine}-${lastLine}/${lineCount}`;
}

function appendDetailPages(
  pages: ReviewDetailPage[],
  title: string,
  lines: string[],
  styles: ReviewBodyLineStyle[],
  limits: ReviewDetailPageLimits,
  logicalPageIndex: number,
  logicalPageCount: number
): void {
  const linesPerScreen = styles.length > 0 ? limits.max_compact_body_lines : limits.max_body_lines;
  const total = lines.length > 0 ? lines.length : 1;
  let position = 0;
  while (position < total) {
    const firstPosition = position;
    const bodyLines: string[] = [];
    const bodyStyles: ReviewBodyLineStyle[] = [];
    for (let line = 0; line < linesPerScreen && position < lines.length; line += 1) {
      bodyLines.push(lines[position]);
      bodyStyles.push(styles[position] ?? "normal");
      position += 1;
    }
    if (bodyLines.length === 0) {
      bodyLines.push("");
      bodyStyles.push("normal");
      position = total;
    }
    pages.push({
      title,
      lines: bodyLines,
      action: "next",
      page_indicator: detailPageIndicator(logicalPageIndex, logicalPageCount, firstPosition + 1, position, total),
      body_line_styles: bodyStyles,
      logical_page_id: title
    });
    if (position >= total) break;
  }
}

function validateDetailLimits(limits: ReviewDetailPageLimits): void {
  for (const [key, value] of Object.entries(limits)) {
    if (!Number.isInteger(value) || value <= 0) {
      throw new Error(`review detail-page limit ${key} must be a positive integer`);
    }
  }
}

export function renderReviewPages(review: EventReview): ReviewPage[] {
  const pages: ReviewPage[] = [
    {
      title: "Event",
      lines: [`Kind ${review.kind}`, `Created ${review.created_at}`, "Author", String(review.author_pubkey)],
      action: "next"
    },
    {
      title: "Content",
      lines: [String(review.content)],
      action: "next"
    },
    {
      title: "Tags",
      lines: tagPageLines(review),
      action: "next"
    },
    {
      title: "Decision",
      lines: ["Approve signing only if all pages match."],
      action: "approve_or_reject"
    }
  ];
  return pages;
}

export function renderReviewDetailPages(review: EventReview, limits: ReviewDetailPageLimits): ReviewDetailPage[] {
  validateDetailLimits(limits);
  const pages: ReviewDetailPage[] = [];
  appendDetailPages(pages, "Event", ...detailEventLines(review, limits), limits, 1, 4);
  appendDetailPages(pages, "Content", ...detailContentLines(review, limits), limits, 2, 4);
  appendDetailPages(pages, "Tags", ...detailTagLines(review, limits), limits, 3, 4);
  pages.push({
    title: "Decision",
    lines: ["Approve signing only if all pages match."],
    action: "approve_or_reject",
    page_indicator: "Page 4/4",
    body_line_styles: [],
    logical_page_id: "Decision"
  });
  return pages;
}

function requireSignEventRequest(value: unknown): {
  version: 1;
  request_id: string;
  method: "sign_event";
  params: { event_template: unknown };
} {
  if (!isRecord(value)) throw new Error("screen review requires request object");
  if (value.version !== 1) throw new Error("screen review requires version 1");
  if (typeof value.request_id !== "string") throw new Error("screen review requires request_id");
  if (value.method !== "sign_event") throw new Error("screen review supports sign_event requests only");
  if (!isRecord(value.params) || !("event_template" in value.params)) {
    throw new Error("screen review requires params.event_template");
  }
  return {
    version: 1,
    request_id: value.request_id,
    method: "sign_event",
    params: { event_template: value.params.event_template }
  };
}

function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    const encoded = JSON.stringify(value);
    if (encoded === undefined) throw new Error("unsupported value in approval digest");
    return encoded;
  }
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  throw new Error("unsupported value in approval digest");
}

function approvalDigestForScreenReview(
  request: ReturnType<typeof requireSignEventRequest>,
  review: EventReview,
  pages: ReviewPage[]
): string {
  const payload = {
    version: request.version,
    method: request.method,
    request_id: request.request_id,
    event_template: request.params.event_template,
    review,
    pages
  };
  return sha256Utf8Hex(canonicalJson(payload));
}

export function screenReviewForRequest(
  value: unknown,
  authorPubkey = DEVELOPMENT_REVIEW_AUTHOR_PUBKEY
): ScreenReview {
  const request = requireSignEventRequest(value);
  const review = reviewEventTemplate(request.params.event_template, authorPubkey);
  const pages = renderReviewPages(review);
  return {
    format: "screen-pages",
    request_id: request.request_id,
    approval_digest: approvalDigestForScreenReview(request, review, pages),
    pages
  };
}

export function approvalDigestForRequest(value: unknown, authorPubkey = DEVELOPMENT_REVIEW_AUTHOR_PUBKEY): string {
  return screenReviewForRequest(value, authorPubkey).approval_digest;
}
