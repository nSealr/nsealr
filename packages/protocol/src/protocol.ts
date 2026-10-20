import { readBoundedJson, validateReportedCapabilities } from "./capabilities.js";
import {
  compactJsonUtf8ByteLength,
  NSEALR_V0_LIMITS,
  utf8ByteLength
} from "./limits.js";

export type ValidationResult = {
  ok: boolean;
  error?: string;
};

const PARAMETERLESS_METHODS = ["get_capabilities", "get_public_key"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isRequestId(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9._:-]+$/u.test(value) && value.length <= NSEALR_V0_LIMITS.max_request_id_length;
}

function isLowerHex(value: unknown, length: number): value is string {
  return typeof value === "string" && new RegExp(`^[0-9a-f]{${length}}$`, "u").test(value);
}

function unknownFields(value: Record<string, unknown>, allowed: readonly string[]): string[] {
  const allowedSet = new Set(allowed);
  return Object.keys(value).filter((key) => !allowedSet.has(key));
}

function validateSafeIntegerField(field: "created_at" | "kind", value: unknown): ValidationResult {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    return { ok: false, error: `event_template ${field} must be a non-negative safe integer` };
  }
  if (!Number.isSafeInteger(value) || value > NSEALR_V0_LIMITS.max_safe_integer) {
    return { ok: false, error: `event_template ${field} exceeds max_safe_integer` };
  }
  return { ok: true };
}

function validateSignedEventIntegerField(field: "created_at" | "kind", value: unknown): ValidationResult {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    return { ok: false, error: `signed event ${field} must be a non-negative safe integer` };
  }
  if (!Number.isSafeInteger(value) || value > NSEALR_V0_LIMITS.max_safe_integer) {
    return { ok: false, error: `signed event ${field} exceeds max_safe_integer` };
  }
  return { ok: true };
}

function validateTags(value: unknown, label: "event_template" | "signed event"): ValidationResult {
  if (!Array.isArray(value)) {
    return { ok: false, error: `${label} tags must be an array` };
  }
  if (value.length > NSEALR_V0_LIMITS.max_tag_count) {
    return { ok: false, error: `${label} tags exceeds max_tag_count` };
  }
  let totalTagBytes = 0;
  for (const [tagIndex, tag] of value.entries()) {
    if (!Array.isArray(tag)) return { ok: false, error: `${label} tags[${tagIndex}] must be an array` };
    if (tag.length > NSEALR_V0_LIMITS.max_tag_fields_per_tag) {
      return { ok: false, error: `${label} tags[${tagIndex}] exceeds max_tag_fields_per_tag` };
    }
    for (const [fieldIndex, item] of tag.entries()) {
      if (typeof item !== "string") {
        return { ok: false, error: `${label} tags[${tagIndex}][${fieldIndex}] must be a string` };
      }
      const itemBytes = utf8ByteLength(item);
      totalTagBytes += itemBytes;
      if (itemBytes > NSEALR_V0_LIMITS.max_tag_field_utf8_bytes) {
        return { ok: false, error: `${label} tag field exceeds max_tag_field_utf8_bytes` };
      }
    }
  }
  if (totalTagBytes > NSEALR_V0_LIMITS.max_total_tag_utf8_bytes) {
    return { ok: false, error: `${label} tags exceed max_total_tag_utf8_bytes` };
  }
  return { ok: true };
}

function validateEventTemplate(value: unknown): ValidationResult {
  if (!isRecord(value)) return { ok: false, error: "event_template must be an object" };
  const forbidden = ["id", "pubkey", "sig"].filter((field) => field in value);
  if (forbidden.length > 0) {
    return { ok: false, error: `event_template contains forbidden fields: ${forbidden.join(", ")}` };
  }
  const extra = unknownFields(value, ["created_at", "kind", "tags", "content", "id", "pubkey", "sig"]);
  if (extra.length > 0) return { ok: false, error: `event_template contains unknown fields: ${extra.join(", ")}` };

  const createdAt = validateSafeIntegerField("created_at", value.created_at);
  if (!createdAt.ok) return createdAt;
  const kind = validateSafeIntegerField("kind", value.kind);
  if (!kind.ok) return kind;

  const tags = validateTags(value.tags, "event_template");
  if (!tags.ok) return tags;
  if (typeof value.content !== "string") return { ok: false, error: "content must be a string" };
  if (utf8ByteLength(value.content) > NSEALR_V0_LIMITS.max_content_utf8_bytes) {
    return { ok: false, error: "event_template content exceeds max_content_utf8_bytes" };
  }
  return { ok: true };
}

export function validateRequest(value: unknown): ValidationResult {
  if (!isRecord(value)) return { ok: false, error: "request must be an object" };
  try { readBoundedJson(JSON.stringify(value), NSEALR_V0_LIMITS.max_decoded_request_json_bytes); }
  catch (error) { return { ok: false, error: error instanceof Error ? error.message : "invalid request JSON" }; }
  if (compactJsonUtf8ByteLength(value) > NSEALR_V0_LIMITS.max_decoded_request_json_bytes) {
    return { ok: false, error: "decoded request JSON exceeds max_decoded_request_json_bytes" };
  }
  if (value.version !== 2) return { ok: false, error: "version must be 2" };
  if (!isRequestId(value.request_id)) return { ok: false, error: "request_id is invalid" };
  if (typeof value.method === "string" && (PARAMETERLESS_METHODS as readonly string[]).includes(value.method)) {
    if ("params" in value) return { ok: false, error: `${value.method} must not include params` };
    const extra = unknownFields(value, ["version", "request_id", "method"]);
    if (extra.length > 0) return { ok: false, error: `unknown top-level fields: ${extra.join(", ")}` };
    return { ok: true };
  }
  if (value.method === "sign_event") {
    const extra = unknownFields(value, ["version", "request_id", "method", "params"]);
    if (extra.length > 0) return { ok: false, error: `unknown top-level fields: ${extra.join(", ")}` };
    if (!isRecord(value.params)) return { ok: false, error: "sign_event requires params" };
    const paramExtra = unknownFields(value.params, ["event_template"]);
    if (paramExtra.length > 0) return { ok: false, error: `sign_event params contain unknown fields: ${paramExtra.join(", ")}` };
    const result = validateEventTemplate(value.params.event_template);
    if (!result.ok) return result;
    return { ok: true };
  }
  return { ok: false, error: "unsupported method" };
}

function validateSignedEvent(value: unknown): ValidationResult {
  if (!isRecord(value)) return { ok: false, error: "event must be an object" };
  const extra = unknownFields(value, ["id", "pubkey", "created_at", "kind", "tags", "content", "sig"]);
  if (extra.length > 0) return { ok: false, error: `event contains unknown fields: ${extra.join(", ")}` };
  if (!isLowerHex(value.id, 64)) return { ok: false, error: "event id must be 32-byte lowercase hex" };
  if (!isLowerHex(value.pubkey, 64)) return { ok: false, error: "event pubkey must be 32-byte lowercase hex" };
  const createdAt = validateSignedEventIntegerField("created_at", value.created_at);
  if (!createdAt.ok) return createdAt;
  const kind = validateSignedEventIntegerField("kind", value.kind);
  if (!kind.ok) return kind;
  const tags = validateTags(value.tags, "signed event");
  if (!tags.ok) return tags;
  if (typeof value.content !== "string") return { ok: false, error: "content must be a string" };
  if (utf8ByteLength(value.content) > NSEALR_V0_LIMITS.max_content_utf8_bytes) {
    return { ok: false, error: "signed event content exceeds max_content_utf8_bytes" };
  }
  if (!isLowerHex(value.sig, 128)) return { ok: false, error: "event sig must be 64-byte lowercase hex" };
  return { ok: true };
}

function validateCapabilities(value: unknown): ValidationResult {
  try { validateReportedCapabilities(value); return { ok: true }; }
  catch (error) { return { ok: false, error: error instanceof Error ? error.message : "invalid reported capabilities" }; }
}

export function validateResponse(value: unknown): ValidationResult {
  if (!isRecord(value)) return { ok: false, error: "response must be an object" };
  try { readBoundedJson(JSON.stringify(value), 8192); }
  catch (error) { return { ok: false, error: error instanceof Error ? error.message : "invalid response JSON" }; }
  const extra = unknownFields(value, ["version", "request_id", "ok", "result", "error"]);
  if (extra.length > 0) return { ok: false, error: `unknown top-level response fields: ${extra.join(", ")}` };
  if (value.version !== 2) return { ok: false, error: "version must be 2" };
  if (!isRequestId(value.request_id)) return { ok: false, error: "request_id is invalid" };
  if (value.ok === false) {
    if ("result" in value) return { ok: false, error: "error response must not include result" };
    if (!isRecord(value.error)) return { ok: false, error: "error response requires error object" };
    if (unknownFields(value.error, ["code", "message", "retryable"]).length) return { ok: false, error: "unknown error fields" };
    if (typeof value.error.code !== "string") return { ok: false, error: "error code is required" };
    if (typeof value.error.message !== "string" || value.error.message.length === 0) return { ok: false, error: "error message is required" };
    if (typeof value.error.retryable !== "boolean") return { ok: false, error: "error retryable flag is required" };
    return { ok: true };
  }
  if (value.ok === true) {
    if ("error" in value) return { ok: false, error: "successful response must not include error" };
    if (!isRecord(value.result)) return { ok: false, error: "successful response requires result" };
    const result = value.result;
    const resultExtra = unknownFields(result, ["capabilities", "public_key", "event"]);
    if (resultExtra.length > 0) return { ok: false, error: `successful response result contains unknown fields: ${resultExtra.join(", ")}` };
    const resultFields = ["capabilities", "public_key", "event"].filter((field) => field in result);
    if (resultFields.length !== 1) {
      return { ok: false, error: "successful response result must contain exactly one result field" };
    }
    if ("capabilities" in result) return validateCapabilities(result.capabilities);
    if ("public_key" in result) {
      return isLowerHex(result.public_key, 64) ? { ok: true } : { ok: false, error: "public_key is invalid" };
    }
    if ("event" in result) return validateSignedEvent(result.event);
    return { ok: false, error: "successful response result is empty" };
  }
  return { ok: false, error: "ok must be true or false" };
}

/** Parse original request bytes before object validation loses duplicate/token evidence. */
export function parseSigningRequest(input: string | Uint8Array): unknown {
  const value = readBoundedJson(input, NSEALR_V0_LIMITS.max_decoded_request_json_bytes);
  const result = validateRequest(value);
  if (!result.ok) throw new Error(result.error);
  return value;
}

/** Parse original response bytes under the applicable local byte ceiling. */
export function parseSigningResponse(input: string | Uint8Array, maxBytes = 8192): unknown {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > 8192) throw new Error("invalid response byte ceiling");
  const value = readBoundedJson(input, maxBytes);
  const result = validateResponse(value);
  if (!result.ok) throw new Error(result.error);
  return value;
}
