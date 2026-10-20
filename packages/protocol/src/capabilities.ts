/** Bounded public compatibility data. These values never approve device actions. */
export type ProfileId = "esp32_no_se" | "pi_qr" | "p4_qr" | "custom_board";
export type Support = "supported" | "unavailable" | "unknown";
export type Configuration = "configured" | "unconfigured" | "unavailable" | "unknown";
export type Availability = "available" | "unavailable" | "unknown";
export type AvailabilityReason = "locked" | "provider_missing" | "busy" | "not_implemented" | "unknown";
export type CapabilityMethodId = "get_capabilities" | "get_public_key" | "sign_event" | "nip44_encrypt" | "nip44_decrypt";
export type AlgorithmId = "bip340.secp256k1.v1" | "nip44.v2";
export type TransportId = "usb" | "qr";
export type CustodyMode = "volatile_session" | "mcu_wrapped_persistent" | "custom_se_assisted_persistent";
export type CompatibilityReason = "invalid_capabilities" | "unsupported_contract" | "unknown_manifest" | "profile_mismatch" | "custody_mismatch" | "required_component_unavailable" | "unsupported_method" | "unsupported_algorithm" | "transport_mismatch" | "limits_unknown" | "limit_exceeded" | "runtime_unavailable" | "workflow_not_admitted";

export class CapabilityError extends Error {
  constructor(public readonly reason: CompatibilityReason, message: string) {
    super(message);
    this.name = "CapabilityError";
  }
}

export const CAPABILITY_BOUNDS = Object.freeze({ json_bytes: 8192, methods: 16, transports: 4, entries: 32, identifier_bytes: 128, depth: 8 });
export const SIGNING_CONTRACT = "nsealr.signing.v2" as const;
export const SIGNING_VERSION = 2 as const;

export type ReportedFeature = {
  support: Support;
  configuration: Configuration;
  availability: Availability;
  reason: AvailabilityReason | null;
};
export type ReportedMethod = ReportedFeature & {
  id: CapabilityMethodId;
  revision: 1;
  operation_id: string;
  algorithm_ids: AlgorithmId[];
  execution_location: "mcu" | "se" | "host_os" | "unknown";
  limits_id: string;
};
export type ReportedTransport = ReportedFeature & {
  id: TransportId;
  codec_id: "nsealr.serial-frame.v0" | "nsealr.qr-envelope.v0";
  limits_id: string;
};
export type MessageFeature = ReportedFeature & { workflow_id: string | null };
export type MessageFeatures = {
  nip44_v2_primitive: MessageFeature;
  verified_message_context_v1: MessageFeature;
  nip17_59_one_to_one_text_v1: MessageFeature;
};
export type FullCapabilities = {
  format: "nsealr.capabilities.v1";
  form: "full";
  profile: ProfileId;
  requirements_id: string;
  implementation_id: string;
  limits_id: string;
  device: { name: string; firmware: string; hardware: string };
  custody: { mode: CustodyMode; configuration_id: string };
  secure_element: { state: "absent" | "unknown" } | { state: "required"; configuration_id: string };
  consent: "manual_local";
  methods: ReportedMethod[];
  transports: ReportedTransport[];
  messages: MessageFeatures;
};
export type RuntimeMethodDelta = Pick<ReportedMethod, "configuration" | "availability" | "reason"> & { method_id: CapabilityMethodId };
export type ReferenceCapabilities = {
  format: "nsealr.capabilities.v1";
  form: "reference";
  profile: ProfileId;
  implementation_id: string;
  runtime: RuntimeMethodDelta[];
};
export type ReportedCapabilities = FullCapabilities | ReferenceCapabilities;
export type ImplementationProfile = Omit<FullCapabilities, "format" | "form"> & {
  format: "nsealr.implementation-profile.v1";
  conformance_only: boolean;
};

export type MethodLimits = {
  method_id: CapabilityMethodId;
  scope: "sign_event" | "discovery" | "message";
  request_json_bytes: number;
  response_json_bytes: number;
  parse_work: number;
  retained_bytes: number;
  pending_requests: number;
  deadline_ms: number;
  queued_operations: number;
  cached_responses: number;
  content_utf8_bytes?: number;
  tag_count?: number;
  tag_fields?: number;
  tag_field_utf8_bytes?: number;
  aggregate_tag_utf8_bytes?: number;
  canonical_bytes?: number;
  review_pages?: number;
  plaintext_bytes?: number;
  padded_bytes?: number;
  ciphertext_bytes?: number;
  base64_bytes?: number;
  context_bytes?: number;
  pending_contexts?: number;
};
export type TransportLimits = {
  transport_id: TransportId;
  scope: "transport";
  frame_bytes: number;
  frame_count: number;
  reassembly_bytes: number;
  parse_work: number;
  retained_bytes: number;
  pending_requests: number;
  deadline_ms: number;
  queued_frames: number;
  static_decoded_json_bytes?: number;
  chunk_payload_chars?: number;
};
export type LimitsManifest = {
  format: "nsealr.limits.v1";
  limits_id: string;
  methods: MethodLimits[];
  transports: TransportLimits[];
};

const profiles = ["esp32_no_se", "pi_qr", "p4_qr", "custom_board"] as const;
const methodIds = ["get_capabilities", "get_public_key", "sign_event", "nip44_encrypt", "nip44_decrypt"] as const;
const messageIds = ["nip44_v2_primitive", "verified_message_context_v1", "nip17_59_one_to_one_text_v1"] as const;
const featureKeys = ["support", "configuration", "availability", "reason"] as const;
const methodKeys = ["id", "revision", "operation_id", "algorithm_ids", "execution_location", "limits_id", ...featureKeys] as const;
const fullKeys = ["format", "form", "profile", "requirements_id", "implementation_id", "limits_id", "device", "custody", "secure_element", "consent", "methods", "transports", "messages"] as const;
const encoder = new TextEncoder();

function fail(message: string, reason: CompatibilityReason = "invalid_capabilities"): never {
  throw new CapabilityError(reason, message);
}
function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) fail(`${label} must be an object`);
  return value as Record<string, unknown>;
}
function keys(value: Record<string, unknown>, allowed: readonly string[], label: string): void {
  if (Object.keys(value).some((key) => !allowed.includes(key)) || allowed.some((key) => !Object.hasOwn(value, key))) fail(`${label} has missing or unknown fields`);
}
function choice<T extends string>(value: unknown, allowed: readonly T[], label: string): T {
  if (typeof value !== "string" || !allowed.includes(value as T)) fail(`${label} is unsupported`);
  return value as T;
}
function unicode(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const unit = value.charCodeAt(i);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) return false;
  }
  return true;
}
function identifier(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(value)) fail(`${label} is not a bounded identifier`);
  return value;
}
function label(value: unknown, name: string): string {
  if (typeof value !== "string" || value.length === 0 || !unicode(value) || encoder.encode(value).byteLength > 128) fail(`${name} exceeds the UTF8 label bound`);
  return value;
}
function integer(value: unknown, name: string, allowZero = false): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < (allowZero ? 0 : 1)) fail(`${name} must be a finite ${allowZero ? "nonnegative" : "positive"} safe integer`, "limits_unknown");
  return value;
}
function array(value: unknown, max: number, name: string, min = 0): unknown[] {
  if (!Array.isArray(value) || value.length < min || value.length > max) fail(`${name} exceeds its entry bound`);
  return value;
}
function uniqueIds(values: readonly string[], name: string): void {
  if (new Set(values).size !== values.length) fail(`${name} contains duplicate IDs`);
}

/** Package-private raw lexical guard. It does not build another object parser:
 * JSON.parse still parses values, after duplicate/Unicode/depth/work checks.
 * Callers must use original bytes; validating a previously parsed object alone
 * cannot recover duplicate-key evidence. */
export function readBoundedJson(input: string | Uint8Array, maxBytes = 8192, maxDepth = 8): unknown {
  let source: string;
  if (typeof input === "string") {
    if (!unicode(input) || encoder.encode(input).byteLength > maxBytes) fail("JSON exceeds its byte/Unicode bound");
    source = input;
  } else {
    if (input.byteLength > maxBytes) fail("JSON exceeds its byte bound");
    try { source = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(input); }
    catch { fail("JSON is not valid UTF8"); }
  }
  if (source.startsWith("\ufeff")) fail("JSON BOM is not accepted");
  let at = 0;
  const ws = () => { while (/[\x20\x09\x0a\x0d]/u.test(source[at] ?? "!") && at < source.length) at++; };
  const string = (): string => {
    const begin = at++;
    while (at < source.length) {
      const char = source[at++];
      if (char === "\\") { at++; continue; }
      if (char === '"') {
        let decoded: unknown;
        try { decoded = JSON.parse(source.slice(begin, at)); } catch { fail("Malformed JSON string"); }
        if (typeof decoded !== "string" || !unicode(decoded)) fail("JSON contains an invalid Unicode scalar");
        return decoded;
      }
    }
    return fail("Unterminated JSON string");
  };
  const value = (depth: number): void => {
    ws();
    const char = source[at];
    if (char === "{" || char === "[") {
      if (depth >= maxDepth) fail("JSON nesting exceeds its bound");
      at++; ws();
      const object = char === "{";
      const end = object ? "}" : "]";
      const seen = new Set<string>();
      if (source[at] === end) { at++; return; }
      while (at < source.length) {
        if (object) {
          if (source[at] !== '"') fail("JSON object key is missing");
          const key = string();
          if (encoder.encode(key).byteLength > 128 || seen.size >= 32 || seen.has(key)) fail("Duplicate or oversized JSON object key");
          seen.add(key); ws();
          if (source[at++] !== ":") fail("JSON key separator is missing");
        }
        value(depth + 1); ws();
        if (source[at] === end) { at++; return; }
        if (source[at++] !== ",") fail("JSON value separator is missing");
        ws();
      }
      fail("Unterminated JSON container");
    }
    if (char === '"') { string(); return; }
    for (const literal of ["true", "false", "null"]) {
      if (source.startsWith(literal, at)) { at += literal.length; return; }
    }
    const number = /^(?:0|[1-9][0-9]*)/u.exec(source.slice(at));
    if (!number) fail("JSON requires an unsigned integer or value");
    if (!Number.isSafeInteger(Number(number[0]))) fail("JSON integer is unsafe");
    at += number[0].length;
  };
  value(0); ws();
  if (at !== source.length) fail("JSON has trailing or invalid token data");
  try { return JSON.parse(source); } catch { return fail("Malformed JSON"); }
}

function feature(value: Record<string, unknown>, name: string): void {
  const support = choice(value.support, ["supported", "unavailable", "unknown"], `${name}.support`);
  const configuration = choice(value.configuration, ["configured", "unconfigured", "unavailable", "unknown"], `${name}.configuration`);
  const availability = choice(value.availability, ["available", "unavailable", "unknown"], `${name}.availability`);
  if (configuration === "configured" && support !== "supported") fail(`${name} is configured but unsupported`);
  if (availability === "available") {
    if (support !== "supported" || configuration !== "configured" || value.reason !== null) fail(`${name} has contradictory available state`);
  } else choice(value.reason, ["locked", "provider_missing", "busy", "not_implemented", "unknown"], `${name}.reason`);
}
function validateFull(value: unknown): FullCapabilities {
  const full = record(value, "capabilities"); keys(full, fullKeys, "capabilities");
  if (full.format !== "nsealr.capabilities.v1" || full.form !== "full") fail("Unsupported capability format", "unsupported_contract");
  choice(full.profile, profiles, "profile");
  for (const key of ["requirements_id", "implementation_id", "limits_id"]) identifier(full[key], key);
  const device = record(full.device, "device"); keys(device, ["name", "firmware", "hardware"], "device");
  for (const key of ["name", "firmware", "hardware"]) label(device[key], `device.${key}`);
  const custody = record(full.custody, "custody"); keys(custody, ["mode", "configuration_id"], "custody");
  choice(custody.mode, ["volatile_session", "mcu_wrapped_persistent", "custom_se_assisted_persistent"], "custody.mode");
  identifier(custody.configuration_id, "custody.configuration_id");
  const se = record(full.secure_element, "secure_element");
  choice(se.state, ["absent", "unknown", "required"], "secure_element.state");
  keys(se, se.state === "required" ? ["state", "configuration_id"] : ["state"], "secure_element");
  if (se.state === "required") identifier(se.configuration_id, "secure_element.configuration_id");
  if (full.consent !== "manual_local") fail("Only initial manual local consent is supported");
  const methods = array(full.methods, 16, "methods", 1);
  const names: string[] = [];
  for (const entry of methods) {
    const method = record(entry, "method"); keys(method, methodKeys, "method");
    names.push(choice(method.id, methodIds, "method.id"));
    if (method.revision !== 1) fail("Unknown method revision", "unsupported_method");
    identifier(method.operation_id, "method.operation_id"); identifier(method.limits_id, "method.limits_id");
    const algorithms = array(method.algorithm_ids, 4, "algorithm_ids").map((id) => choice(id, ["bip340.secp256k1.v1", "nip44.v2"], "algorithm_id"));
    uniqueIds(algorithms, "algorithm_ids");
    choice(method.execution_location, ["mcu", "se", "host_os", "unknown"], "execution_location");
    feature(method, "method");
    if (method.availability === "available" && (method.execution_location === "unknown" || method.id !== "get_capabilities" && algorithms.length === 0)) fail("Available method lacks execution/algorithm semantics");
  }
  uniqueIds(names, "methods");
  const transports = array(full.transports, 4, "transports", 1);
  const transportIds: string[] = [];
  for (const entry of transports) {
    const transport = record(entry, "transport"); keys(transport, ["id", "codec_id", "limits_id", ...featureKeys], "transport");
    transportIds.push(choice(transport.id, ["usb", "qr"], "transport.id"));
    const codec = choice(transport.codec_id, ["nsealr.serial-frame.v0", "nsealr.qr-envelope.v0"], "codec_id");
    if (codec !== (transport.id === "usb" ? "nsealr.serial-frame.v0" : "nsealr.qr-envelope.v0")) fail("Codec does not match transport", "transport_mismatch");
    identifier(transport.limits_id, "transport.limits_id"); feature(transport, "transport");
  }
  uniqueIds(transportIds, "transports");
  const messages = record(full.messages, "messages"); keys(messages, messageIds, "messages");
  for (const id of messageIds) {
    const message = record(messages[id], id); keys(message, [...featureKeys, "workflow_id"], id); feature(message, id);
    if (id !== "nip17_59_one_to_one_text_v1" || message.support !== "supported") {
      if (message.workflow_id !== null) fail("Only admitted workflow metadata can name a workflow");
    } else identifier(message.workflow_id, "workflow_id");
  }
  const primitive = messages.nip44_v2_primitive as ReportedFeature;
  const context = messages.verified_message_context_v1 as ReportedFeature;
  const workflow = messages.nip17_59_one_to_one_text_v1 as ReportedFeature;
  if (context.support === "supported" && primitive.support !== "supported" || workflow.support === "supported" && (primitive.support !== "supported" || context.support !== "supported")) fail("Message capability dependencies contradict each other", "workflow_not_admitted");
  return full as FullCapabilities;
}

/** Validate reported data structurally; raw ingress must use parseReportedCapabilities. */
export function validateReportedCapabilities(value: unknown): ReportedCapabilities {
  const report = record(value, "capabilities");
  if (report.format !== "nsealr.capabilities.v1") fail("Unsupported capability format", "unsupported_contract");
  if (report.form === "full") return validateFull(report);
  keys(report, ["format", "form", "profile", "implementation_id", "runtime"], "reference");
  if (report.form !== "reference") fail("Unknown capability form");
  choice(report.profile, profiles, "profile"); identifier(report.implementation_id, "implementation_id");
  const deltas = array(report.runtime, 16, "runtime"); const ids: string[] = [];
  for (const entry of deltas) {
    const delta = record(entry, "runtime delta"); keys(delta, ["method_id", "configuration", "availability", "reason"], "runtime delta");
    ids.push(choice(delta.method_id, methodIds, "method_id"));
    choice(delta.configuration, ["configured", "unconfigured", "unavailable", "unknown"], "configuration");
    const availability = choice(delta.availability, ["available", "unavailable", "unknown"], "availability");
    if (availability === "available") {
      if (delta.configuration !== "configured" || delta.reason !== null) fail("Contradictory available delta");
    } else choice(delta.reason, ["locked", "provider_missing", "busy", "not_implemented", "unknown"], "reason");
  }
  uniqueIds(ids, "runtime"); return report as ReferenceCapabilities;
}

/** Parse the original bounded UTF8 descriptor bytes, preserving duplicate evidence. */
export function parseReportedCapabilities(input: string | Uint8Array): ReportedCapabilities {
  return validateReportedCapabilities(readBoundedJson(input));
}

/** Validate a locally selected implementation record. This does not authenticate
 * attached firmware or turn conformance examples into production evidence. */
export function parseImplementationProfile(value: unknown): ImplementationProfile {
  const manifest = record(value, "implementation");
  const expected = [...fullKeys.filter((key) => key !== "form"), "conformance_only"];
  keys(manifest, expected, "implementation");
  if (manifest.format !== "nsealr.implementation-profile.v1" || typeof manifest.conformance_only !== "boolean") fail("Unknown implementation manifest", "unknown_manifest");
  const { conformance_only, ...fields } = manifest;
  validateFull({ ...fields, format: "nsealr.capabilities.v1", form: "full" });
  return manifest as ImplementationProfile;
}

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (typeof value === "object" && value !== null) return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable((value as Record<string, unknown>)[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function immutable(full: FullCapabilities): unknown {
  const strip = ({ configuration: _configuration, availability: _availability, reason: _reason, ...data }: ReportedFeature & Record<string, unknown>) => data;
  return {
    ...full,
    methods: full.methods.map((method) => strip(method)).sort((a, b) => String(a.id).localeCompare(String(b.id))),
    transports: full.transports.map((transport) => strip(transport)).sort((a, b) => String(a.id).localeCompare(String(b.id))),
    messages: Object.fromEntries(messageIds.map((id) => [id, strip(full.messages[id])]))
  };
}
function fullFromManifest(manifest: ImplementationProfile): FullCapabilities {
  const { conformance_only: _conformance, ...data } = structuredClone(manifest);
  return { ...data, format: "nsealr.capabilities.v1", form: "full" };
}

/** Resolve only against the exact caller-selected local manifest. No URLs,
 * downloads, arbitrary IDs or descriptor claims supply trusted manifests. */
export function resolveReportedCapabilities(value: unknown, localValue: ImplementationProfile): FullCapabilities {
  const report = validateReportedCapabilities(value);
  const local = parseImplementationProfile(localValue);
  if (report.implementation_id !== local.implementation_id) fail("Unknown implementation manifest", "unknown_manifest");
  if (report.profile !== local.profile) fail("Reported profile differs from selected manifest", "profile_mismatch");
  const base = fullFromManifest(local);
  if (report.form === "full") {
    if (stable(immutable(report)) !== stable(immutable(base))) fail("Immutable descriptor differs from selected manifest", "unknown_manifest");
    return structuredClone(report);
  }
  for (const delta of report.runtime) {
    const method = base.methods.find((entry) => entry.id === delta.method_id);
    if (!method || method.support !== "supported") fail("Delta cannot create an implemented method", "unsupported_method");
    Object.assign(method, { configuration: delta.configuration, availability: delta.availability, reason: delta.reason });
  }
  // Omitted entries retain the local manifest's explicit unavailable/unknown
  // defaults. An available default is unsafe for compact resolution.
  for (const method of base.methods) {
    if (!report.runtime.some((entry) => entry.method_id === method.id) && method.availability === "available") fail("Compact form omitted necessary runtime state", "runtime_unavailable");
  }
  return validateFull(base);
}

/** Produce a reference only when it completely represents the full current
 * state. A transport/runtime change outside method deltas cannot be omitted. */
export function compactReportedCapabilities(fullValue: FullCapabilities, localValue: ImplementationProfile, encodedBudget: number): ReferenceCapabilities {
  const full = resolveReportedCapabilities(fullValue, localValue); const local = fullFromManifest(localValue);
  if (stable(full.transports) !== stable(local.transports) || stable(full.messages) !== stable(local.messages)) fail("Runtime change is not representable by method deltas", "runtime_unavailable");
  const runtime = full.methods.filter((method) => {
    const original = local.methods.find((entry) => entry.id === method.id)!;
    return method.availability === "available" || stable([method.configuration, method.availability, method.reason]) !== stable([original.configuration, original.availability, original.reason]);
  }).map(({ id, configuration, availability, reason }) => ({ method_id: id, configuration, availability, reason }));
  const result: ReferenceCapabilities = { format: "nsealr.capabilities.v1", form: "reference", profile: full.profile, implementation_id: full.implementation_id, runtime };
  if (encoder.encode(JSON.stringify(result)).byteLength > encodedBudget) fail("Complete compact descriptor exceeds transport budget", "runtime_unavailable");
  resolveReportedCapabilities(result, localValue);
  return result;
}

const methodBase = ["method_id", "scope", "request_json_bytes", "response_json_bytes", "parse_work", "retained_bytes", "pending_requests", "deadline_ms", "queued_operations", "cached_responses"];
const eventDimensions = ["content_utf8_bytes", "tag_count", "tag_fields", "tag_field_utf8_bytes", "aggregate_tag_utf8_bytes", "canonical_bytes", "review_pages"];
const messageDimensions = ["plaintext_bytes", "padded_bytes", "ciphertext_bytes", "base64_bytes", "context_bytes", "pending_contexts"];

/** Validate discriminated method/transport dimensions; no missing dimension is
 * interpreted as unlimited, and no unsupported dimension is silently added. */
export function parseLimitsManifest(value: unknown): LimitsManifest {
  const limits = record(value, "limits"); keys(limits, ["format", "limits_id", "methods", "transports"], "limits");
  if (limits.format !== "nsealr.limits.v1") fail("Unknown limits format", "unsupported_contract");
  identifier(limits.limits_id, "limits_id");
  const methods = array(limits.methods, 16, "method limits", 1); const methodNames: string[] = [];
  for (const entry of methods) {
    const method = record(entry, "method limits"); methodNames.push(choice(method.method_id, methodIds, "method_id"));
    const scope = choice(method.scope, ["sign_event", "discovery", "message"], "limits.scope");
    const dimensions = scope === "sign_event" ? eventDimensions : scope === "message" ? messageDimensions : [];
    keys(method, [...methodBase, ...dimensions], "method limits");
    if (scope === "sign_event" && method.method_id !== "sign_event" || scope === "discovery" && !["get_capabilities", "get_public_key"].includes(String(method.method_id)) || scope === "message" && !["nip44_encrypt", "nip44_decrypt"].includes(String(method.method_id))) fail("Limit dimensions do not apply to method", "limits_unknown");
    for (const key of [...methodBase.slice(2), ...dimensions]) integer(method[key], key, ["queued_operations", "cached_responses"].includes(key));
    const pending = checkedProduct(Number(method.request_json_bytes), Number(method.pending_requests));
    const queue = checkedProduct(Number(method.request_json_bytes), Number(method.queued_operations));
    const cache = checkedProduct(Number(method.response_json_bytes), Number(method.cached_responses));
    if (checkedSum(pending, queue, cache) > Number(method.retained_bytes) || Number(method.response_json_bytes) > Number(method.retained_bytes)) fail("Method retention is inconsistent", "limits_unknown");
  }
  uniqueIds(methodNames, "method limits");
  const transports = array(limits.transports, 4, "transport limits", 1); const transportNames: string[] = [];
  for (const entry of transports) {
    const transport = record(entry, "transport limits"); const id = choice(transport.transport_id, ["usb", "qr"], "transport_id"); transportNames.push(id);
    if (transport.scope !== "transport") fail("Unknown transport limits scope", "limits_unknown");
    const dimensions = ["frame_bytes", "frame_count", "reassembly_bytes", "parse_work", "retained_bytes", "pending_requests", "deadline_ms", "queued_frames", ...(id === "qr" ? ["static_decoded_json_bytes", "chunk_payload_chars"] : [])];
    keys(transport, ["transport_id", "scope", ...dimensions], "transport limits");
    for (const key of dimensions) integer(transport[key], key, key === "queued_frames");
    const frames = checkedProduct(Number(transport.frame_bytes), Number(transport.queued_frames));
    const pending = checkedProduct(Number(transport.reassembly_bytes), Number(transport.pending_requests));
    if (checkedSum(frames, pending) > Number(transport.retained_bytes)) fail("Transport retention is inconsistent", "limits_unknown");
  }
  uniqueIds(transportNames, "transport limits"); return limits as LimitsManifest;
}

/** Checked multiplication is performed before allocation or transport writes. */
export function checkedProduct(left: number, right: number): number {
  integer(left, "left", true); integer(right, "right", true);
  const product = left * right;
  if (!Number.isSafeInteger(product)) fail("Size multiplication overflow", "limit_exceeded");
  return product;
}
function checkedSum(...values: number[]): number {
  let result = 0;
  for (const value of values) { integer(value, "size", true); result += value; if (!Number.isSafeInteger(result)) fail("Size addition overflow", "limit_exceeded"); }
  return result;
}

/** Intersect exact applicable dimensions without increasing either local cap. */
export function intersectMethodLimits(local: MethodLimits, peer: MethodLimits): MethodLimits {
  if (local.method_id !== peer.method_id || local.scope !== peer.scope || stable(Object.keys(local).sort()) !== stable(Object.keys(peer).sort())) fail("Mismatched limit units/dimensions", "limits_unknown");
  const output = { ...local } as unknown as Record<string, unknown>;
  for (const key of Object.keys(local)) {
    if (["method_id", "scope"].includes(key)) continue;
    const allowZero = ["queued_operations", "cached_responses"].includes(key);
    output[key] = Math.min(integer((local as unknown as Record<string, unknown>)[key], key, allowZero), integer((peer as unknown as Record<string, unknown>)[key], key, allowZero));
  }
  return output as unknown as MethodLimits;
}

/** Separate primitive/context/workflow eligibility; no compound API is added. */
export function requireMessageFeature(messages: MessageFeatures, kind: keyof MessageFeatures, admittedWorkflow?: string): void {
  const feature = messages[kind];
  if (feature.support !== "supported" || feature.configuration !== "configured" || feature.availability !== "available") fail("Requested message feature is unavailable", "workflow_not_admitted");
  if (kind !== "nip44_v2_primitive" && messages.nip44_v2_primitive.availability !== "available") fail("Primitive cannot establish context/workflow", "workflow_not_admitted");
  if (kind === "nip17_59_one_to_one_text_v1" && (messages.verified_message_context_v1.availability !== "available" || !admittedWorkflow || feature.workflow_id !== admittedWorkflow)) fail("Named message workflow is not admitted", "workflow_not_admitted");
}
