import { sha256Utf8Hex, verifySignedEventResponse } from "@nsealr/core";
import {
  parseRouteSelectionRequest,
  selectAccountRoute,
  type AccountDescriptor,
  type RouteSelection,
  type RouteSelectionRequest
} from "@nsealr/policy";
import {
  CapabilityError, checkedProduct, compactJsonUtf8ByteLength, intersectMethodLimits,
  NSEALR_V0_LIMITS, parseImplementationProfile, parseLimitsManifest,
  resolveReportedCapabilities, validateRequest, validateResponse,
  type ImplementationProfile, type LimitsManifest, type MethodLimits,
  type ReportedCapabilities, type TransportLimits
} from "@nsealr/protocol";
import {
  parseLocalClientIdentity,
  type LocalClientIdentity,
  type LocalClientSurface
} from "./client-identity.js";

export {
  LOCAL_CLIENT_SURFACES,
  parseLocalClientIdentity,
  type LocalClientIdentity,
  type LocalClientSurface
} from "./client-identity.js";

export const LOCAL_SERVICE_PROTOCOL = "nsealr-local-service-v0";
export const LOCAL_SERVICE_NAME = "nsealr-companion-service";
export const NATIVE_HOST_NAME = "dev.nsealr.companion";
export const LOCAL_PAIRING_INTENT_FORMAT = "nsealr-local-pairing-intent-v0";
export const LOCAL_PAIRING_APPROVAL_FORMAT = "nsealr-local-pairing-approval-v0";
export const EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT = "nsealr-external-review-acknowledgement-v0";
export const MAX_SERVICE_JSON_BYTES = 16 * 1024;

export const LOCAL_SERVICE_OPERATIONS = [
  "service_status",
  "request_pairing",
  "select_account_route",
  "validate_signer_request",
  "dispatch_signer_request",
  "verify_signer_response"
] as const;

export type LocalServiceOperation = (typeof LOCAL_SERVICE_OPERATIONS)[number];
export type PairableLocalServiceOperation = Exclude<LocalServiceOperation, "service_status" | "request_pairing">;

export type LocalClientGrant = {
  client_id: string;
  origin: string;
  surface: LocalClientSurface;
  allowed_operations: PairableLocalServiceOperation[];
  pairing_digest?: string;
  approved_at?: number;
  revoked?: boolean;
  expires_at?: number;
};

export type SignerDispatchRequest = {
  client: LocalClientIdentity;
  route_selection: RouteSelection;
  request: unknown;
  external_review_acknowledgement?: ExternalReviewAcknowledgement;
  /** Local revalidation immediately before the actual operation write. */
  before_write?: () => void;
  /** Diagnostic local intersection, never physical approval or device authority. */
  effective_limits?: EffectiveSignerLimits;
  /** Local cancellation/deadline signal; never serialized into device JSON. */
  abort_signal?: AbortSignal;
};

/** Explicit current adapter observations, supplied locally, never from a wire
 * descriptor or an evidence URL. These do not qualify an attached device. */
export type SignerCompatibilitySnapshot = {
  implementation: ImplementationProfile;
  adapter: ImplementationProfile;
  reported: ReportedCapabilities;
  limits: LimitsManifest;
  adapter_limits: LimitsManifest;
  connection_id: string;
  generation: number;
  /** Locally observed complete review plan for this exact request/implementation,
   * connection generation and relevant review context/geometry. Never wire data,
   * a four-section preview count, consent, attestation or a physical-fit claim. */
  review_plan?: {
    request_sha256: string;
    implementation_id: string;
    connection_id: string;
    generation: number;
    context_id: string;
    geometry_id: string;
    pages: number;
  };
};
export type EffectiveSignerLimits = { method: MethodLimits; transport: TransportLimits };

function compatibilityError(reason: ConstructorParameters<typeof CapabilityError>[0], message: string): never {
  throw new CapabilityError(reason, message);
}

function encodedBytes(decoded: number): number {
  const groups = Math.floor(decoded / 3), tail = decoded % 3;
  const size = checkedProduct(groups, 4) + (tail ? tail + 1 : 0);
  if (!Number.isSafeInteger(size)) compatibilityError("limit_exceeded", "encoded size overflow");
  return size;
}

/** Intersect the exact selected semantics before any operation write. No
 * reported support/availability is converted into trusted consent or evidence. */
export function assessSignerCompatibility(route: RouteSelection, request: unknown, snapshot: SignerCompatibilitySnapshot): EffectiveSignerLimits {
  if (route.contract !== "nsealr.signing.v2" || route.profile === null) compatibilityError("unsupported_contract", "nSealr compatibility requires an explicit local profile");
  if (typeof snapshot.connection_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(snapshot.connection_id) || !Number.isSafeInteger(snapshot.generation) || snapshot.generation < 0) compatibilityError("runtime_unavailable", "current connection observation is unavailable");
  const local = parseImplementationProfile(snapshot.implementation);
  const adapter = parseImplementationProfile(snapshot.adapter);
  const reported = resolveReportedCapabilities(snapshot.reported, local);
  for (const [role, source] of [local, adapter, reported].entries()) {
    if (source.profile !== route.profile) compatibilityError("profile_mismatch", "selected profile differs from implementation/adapter/report");
    if (source.implementation_id !== route.implementation_id) compatibilityError("unknown_manifest", "selected implementation differs");
    if (source.custody.mode !== route.custody) compatibilityError("custody_mismatch", "selected custody differs; fallback is forbidden");
    if (source.profile === "custom_board" && (source.secure_element.state !== "required" || local.secure_element.state !== "required" || source.secure_element.configuration_id !== local.secure_element.configuration_id)) compatibilityError("required_component_unavailable", "required SE configuration is not identified");
    const method = source.methods.find((entry) => entry.id === route.method);
    if (!method || method.support !== "supported" || method.revision !== route.method_revision || method.operation_id !== route.operation_id) compatibilityError("unsupported_method", "exact method/catalog revision is not implemented");
    if (route.algorithm_id !== null && !method.algorithm_ids.includes(route.algorithm_id)) compatibilityError("unsupported_algorithm", "exact algorithm is not implemented");
    if (method.limits_id !== route.limits_id || source.limits_id !== route.limits_id) compatibilityError("limits_unknown", "exact method limits are unknown");
    // Local implementation defaults describe support. Current report and
    // adapter state independently determine availability at this instant.
    if (role !== 0 && (method.configuration !== "configured" || method.availability !== "available")) compatibilityError("runtime_unavailable", "method is currently unavailable");
    const transport = source.transports.find((entry) => entry.id === route.transport);
    if (!transport || transport.codec_id !== route.codec_id || transport.limits_id !== route.limits_id) compatibilityError("transport_mismatch", "exact transport/codec is not implemented");
    if (transport.support !== "supported" || transport.configuration !== "configured" || transport.availability !== "available") compatibilityError("runtime_unavailable", "transport is currently unavailable");
  }
  const peer = parseLimitsManifest(snapshot.limits), own = parseLimitsManifest(snapshot.adapter_limits);
  if (peer.limits_id !== route.limits_id || own.limits_id !== route.limits_id) compatibilityError("limits_unknown", "selected limits manifest differs");
  const peerMethod = peer.methods.find((entry) => entry.method_id === route.method);
  const localMethod = own.methods.find((entry) => entry.method_id === route.method);
  const peerTransport = peer.transports.find((entry) => entry.transport_id === route.transport);
  const localTransport = own.transports.find((entry) => entry.transport_id === route.transport);
  if (!peerMethod || !localMethod || !peerTransport || !localTransport) compatibilityError("limits_unknown", "applicable limit dimensions are missing");
  const method = intersectMethodLimits(localMethod, peerMethod);
  // The existing transport's local 30s default remains an independent ceiling.
  // A peer/local metadata record cannot overflow or extend the actual timer.
  method.deadline_ms = Math.min(method.deadline_ms, 30_000);
  method.request_json_bytes = Math.min(method.request_json_bytes, NSEALR_V0_LIMITS.max_decoded_request_json_bytes);
  if (method.scope === "sign_event") {
    method.content_utf8_bytes = Math.min(method.content_utf8_bytes!, NSEALR_V0_LIMITS.max_content_utf8_bytes);
    method.tag_count = Math.min(method.tag_count!, NSEALR_V0_LIMITS.max_tag_count);
    method.tag_fields = Math.min(method.tag_fields!, NSEALR_V0_LIMITS.max_tag_fields_per_tag);
    method.tag_field_utf8_bytes = Math.min(method.tag_field_utf8_bytes!, NSEALR_V0_LIMITS.max_tag_field_utf8_bytes);
    method.aggregate_tag_utf8_bytes = Math.min(method.aggregate_tag_utf8_bytes!, NSEALR_V0_LIMITS.max_total_tag_utf8_bytes);
  }
  const transport = { ...localTransport } as unknown as Record<string, unknown>;
  if (Object.keys(localTransport).sort().join() !== Object.keys(peerTransport).sort().join()) compatibilityError("limits_unknown", "transport dimensions/units differ");
  for (const key of Object.keys(localTransport)) if (typeof transport[key] === "number") transport[key] = Math.min(Number(transport[key]), Number((peerTransport as unknown as Record<string, unknown>)[key]));
  const boundTransport = transport as unknown as TransportLimits;
  boundTransport.deadline_ms = Math.min(boundTransport.deadline_ms, 30_000);
  if (route.transport === "usb") boundTransport.frame_bytes = Math.min(boundTransport.frame_bytes, NSEALR_V0_LIMITS.max_serial_frame_bytes);
  else {
    boundTransport.reassembly_bytes = Math.min(boundTransport.reassembly_bytes, NSEALR_V0_LIMITS.max_animated_qr_decoded_json_bytes);
    boundTransport.static_decoded_json_bytes = Math.min(boundTransport.static_decoded_json_bytes!, NSEALR_V0_LIMITS.max_static_qr_decoded_json_bytes);
    boundTransport.chunk_payload_chars = Math.min(boundTransport.chunk_payload_chars!, NSEALR_V0_LIMITS.max_animated_qr_frame_payload_chars);
    boundTransport.frame_count = Math.min(boundTransport.frame_count, NSEALR_V0_LIMITS.max_animated_qr_frame_count);
  }
  parseLimitsManifest({ format: "nsealr.limits.v1", limits_id: route.limits_id, methods: [method], transports: [boundTransport] });
  const validation = validateRequest(request);
  if (!validation.ok || !isRecord(request) || request.method !== route.method) compatibilityError("unsupported_method", validation.error ?? "request method differs from selected route");
  const bytes = compactJsonUtf8ByteLength(request);
  if (bytes > method.request_json_bytes || bytes > boundTransport.reassembly_bytes || bytes > method.parse_work || bytes > boundTransport.parse_work) compatibilityError("limit_exceeded", "request exceeds effective byte/work capacity");
  const frameBytes = route.transport === "usb" ? "nsealr1f:request::0000000000000000\n".length + encodedBytes(bytes) : "nsealr1:".length + encodedBytes(bytes);
  if (frameBytes > boundTransport.frame_bytes) compatibilityError("limit_exceeded", "complete encoded request exceeds frame capacity");
  if (route.transport === "qr" && bytes > boundTransport.static_decoded_json_bytes!) compatibilityError("limit_exceeded", "static QR request exceeds actual decoded capacity");
  if (method.scope === "sign_event") {
    const event = (request.params as {event_template: {created_at: number; kind: number; content: string; tags: string[][]}}).event_template;
    if ([4, 13, 14, 1059, 10050, 22242].includes(event.kind)) compatibilityError("workflow_not_admitted", "user-message/setup/AUTH events require their separately admitted context/workflow; generic signing is not a blind-sign route");
    const encoder = new TextEncoder(); let tags = 0;
    if (encoder.encode(event.content).length > method.content_utf8_bytes! || event.tags.length > method.tag_count!) compatibilityError("limit_exceeded", "event exceeds effective content/tag capacity");
    for (const tag of event.tags) {
      if (tag.length > method.tag_fields!) compatibilityError("limit_exceeded", "tag exceeds effective field count");
      for (const field of tag) { const size = encoder.encode(field).length; tags += size; if (size > method.tag_field_utf8_bytes!) compatibilityError("limit_exceeded", "tag field exceeds effective UTF8 capacity"); }
    }
    if (tags > method.aggregate_tag_utf8_bytes!) compatibilityError("limit_exceeded", "tags exceed aggregate capacity");
    // Output sizes use the fixed wire shape and fixed-width public fields;
    // this is capacity planning, never a computed crypto expected answer.
    const response = { version: 2, request_id: request.request_id, ok: true, result: { event: { id: "0".repeat(64), pubkey: route.public_key, ...event, sig: "0".repeat(128) } } };
    const output = compactJsonUtf8ByteLength(response);
    const encodedOutput = route.transport === "usb" ? "nsealr1f:response::0000000000000000\n".length + encodedBytes(output) : "nsealr1:".length + encodedBytes(output);
    if (output > method.response_json_bytes || output > boundTransport.reassembly_bytes || encodedOutput > boundTransport.frame_bytes) compatibilityError("limit_exceeded", "complete response cannot fit effective capacity");
    const canonicalBytes = compactJsonUtf8ByteLength([0, route.public_key, event.created_at, event.kind, event.tags, event.content]);
    const plan = snapshot.review_plan;
    if (!plan || !Number.isSafeInteger(plan.pages) || plan.pages < 1 ||
      plan.request_sha256 !== sha256Utf8Hex(JSON.stringify(request)) ||
      plan.implementation_id !== route.implementation_id || plan.connection_id !== snapshot.connection_id || plan.generation !== snapshot.generation ||
      typeof plan.context_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(plan.context_id) ||
      typeof plan.geometry_id !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(plan.geometry_id)) compatibilityError("runtime_unavailable", "current complete local review plan is missing or stale");
    if (canonicalBytes > method.canonical_bytes! || plan.pages > method.review_pages!) compatibilityError("limit_exceeded", "canonical/complete-review capacity is insufficient");
  }
  return { method, transport: boundTransport };
}

export type SignerRequestDispatcher = (request: SignerDispatchRequest) => unknown | Promise<unknown>;

export class SignerRouteUnavailableError extends Error {
  constructor(message = "signer route is not configured") {
    super(message);
    this.name = "SignerRouteUnavailableError";
  }
}

export const SIGNER_TRANSPORT_ERROR_CODES = [
  "signer_transport_open_failed",
  "signer_transport_timeout",
  "signer_transport_protocol_error",
  "signer_transport_io_failed",
  "signer_transport_close_failed",
  "signer_transport_failed"
] as const;

export type SignerTransportErrorCode = (typeof SIGNER_TRANSPORT_ERROR_CODES)[number];

export class SignerTransportError extends Error {
  readonly code: SignerTransportErrorCode;

  constructor(code: SignerTransportErrorCode, message: string) {
    super(message);
    this.name = "SignerTransportError";
    this.code = code;
  }
}

export type RouteDispatchEntry = {
  account_id?: RouteSelection["account_id"];
  route_type?: RouteSelection["route_type"];
  transport?: RouteSelection["transport"];
  dispatch: SignerRequestDispatcher;
};

export type LocalServiceContext = {
  accounts?: AccountDescriptor[];
  grants?: LocalClientGrant[];
  now?: number;
  signerDispatcher?: SignerRequestDispatcher;
  /** Current locally selected adapter state. Absence blocks local dispatch. */
  signerCompatibility?: (route: RouteSelection, request: unknown) => SignerCompatibilitySnapshot;
  /** Local monotonic milliseconds; peer clocks cannot extend the deadline. */
  monotonicNow?: () => number | undefined;
};

export type PairingIntent = {
  format: typeof LOCAL_PAIRING_INTENT_FORMAT;
  client_id: string;
  client: LocalClientIdentity;
  requested_operations: PairableLocalServiceOperation[];
  pairing_digest: string;
  requires_user_approval: true;
  stores_production_secrets: false;
};

export type LocalPairingApproval = {
  format: typeof LOCAL_PAIRING_APPROVAL_FORMAT;
  pairing_digest: string;
  approved_at: number;
  grant: LocalClientGrant;
  stores_production_secrets: false;
};

export type ExternalReviewAcknowledgement = {
  format: typeof EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT;
  acknowledged: true;
  source: "external-review";
  approval_digest: string;
  stores_production_secrets: false;
  contains_secret_material: false;
};

export type LocalServiceRequest =
  | {
      version: 1;
      request_id: string;
      operation: "service_status";
    }
  | {
      version: 1;
      request_id: string;
      operation: "request_pairing";
      params: {
        client: LocalClientIdentity;
        requested_operations: PairableLocalServiceOperation[];
      };
    }
  | {
      version: 1;
      request_id: string;
      operation: "validate_signer_request";
      params: {
        client: LocalClientIdentity;
        request: unknown;
      };
    }
  | {
      version: 1;
      request_id: string;
      operation: "select_account_route";
      params: {
        client: LocalClientIdentity;
        route_request: RouteSelectionRequest;
      };
    }
  | {
      version: 1;
      request_id: string;
      operation: "dispatch_signer_request";
      params: {
        client: LocalClientIdentity;
        route_request: RouteSelectionRequest;
        request: unknown;
        external_review_acknowledgement?: ExternalReviewAcknowledgement;
      };
    }
  | {
      version: 1;
      request_id: string;
      operation: "verify_signer_response";
      params: {
        client: LocalClientIdentity;
        request: unknown;
        response: unknown;
      };
    };

export type LocalServiceResponse =
  | {
      version: 1;
      request_id: string;
      ok: true;
      result:
        | {
            service: {
              protocol: typeof LOCAL_SERVICE_PROTOCOL;
              name: typeof LOCAL_SERVICE_NAME;
              operations: LocalServiceOperation[];
              requires_pairing: true;
              stores_production_secrets: false;
            };
          }
        | {
            pairing_intent: PairingIntent;
          }
        | {
            route_selection: RouteSelection;
          }
        | {
            validation: {
              valid: boolean;
              error?: string;
            };
          }
        | {
            signer_response: unknown;
          };
    }
  | {
      version: 1;
      request_id: string;
      ok: false;
      error: {
        code: string;
        message: string;
        retryable: false;
      };
    };

type PreparedSignerDispatch =
  | {
      ok: true;
      dispatcher: SignerRequestDispatcher;
      dispatchRequest: SignerDispatchRequest;
      release: () => void;
      checkCurrent: () => void;
      timeout_ms?: number;
    }
  | {
      ok: false;
      response: LocalServiceResponse;
    };

const pendingDispatches = new WeakMap<LocalServiceContext, number>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function isRequestId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[A-Za-z0-9._:-]+$/u.test(value) &&
    value.length <= NSEALR_V0_LIMITS.max_request_id_length
  );
}

function isAllowedOperation(value: unknown): value is LocalServiceOperation {
  return typeof value === "string" && LOCAL_SERVICE_OPERATIONS.includes(value as LocalServiceOperation);
}

function safeRequestId(value: unknown): string {
  return isRecord(value) && isRequestId(value.request_id) ? value.request_id : "invalid-service-request";
}

function errorResponse(request: unknown, code: string, message: string): LocalServiceResponse {
  return {
    version: 1,
    request_id: safeRequestId(request),
    ok: false,
    error: {
      code,
      message,
      retryable: false
    }
  };
}

function validationResult(valid: boolean, error?: string): { validation: { valid: boolean; error?: string } } {
  return error === undefined ? { validation: { valid } } : { validation: { valid, error } };
}

function isPromiseLike(value: unknown): value is PromiseLike<unknown> {
  return isRecord(value) && typeof value.then === "function";
}

function routeDispatchSpecificity(entry: RouteDispatchEntry): number {
  return Number(entry.account_id !== undefined) + Number(entry.route_type !== undefined) + Number(entry.transport !== undefined);
}

function routeDispatchEntryMatches(entry: RouteDispatchEntry, request: SignerDispatchRequest): boolean {
  const route = request.route_selection;
  return (
    (entry.account_id === undefined || entry.account_id === route.account_id) &&
    (entry.route_type === undefined || entry.route_type === route.route_type) &&
    (entry.transport === undefined || entry.transport === route.transport)
  );
}

export function createRouteDispatcher(entries: RouteDispatchEntry[]): SignerRequestDispatcher {
  if (entries.length === 0) throw new Error("route dispatcher requires at least one entry");
  const registry = [...entries];
  return (request) => {
    const matches = registry.filter((entry) => routeDispatchEntryMatches(entry, request));
    if (matches.length === 0) {
      throw new SignerRouteUnavailableError(`no signer dispatcher for route ${request.route_selection.route_type}`);
    }
    const bestSpecificity = Math.max(...matches.map(routeDispatchSpecificity));
    const bestMatches = matches.filter((entry) => routeDispatchSpecificity(entry) === bestSpecificity);
    if (bestMatches.length !== 1) {
      throw new Error(`ambiguous signer dispatcher for route ${request.route_selection.route_type}`);
    }
    return bestMatches[0].dispatch(request);
  };
}

function validateClientIdentity(value: unknown): { ok: true; client: LocalClientIdentity } | { ok: false; error: string } {
  try {
    return { ok: true, client: parseLocalClientIdentity(value) };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "client identity is invalid"
    };
  }
}

function validateRequestedOperations(value: unknown): { ok: true; operations: PairableLocalServiceOperation[] } | { ok: false; error: string } {
  if (!Array.isArray(value) || value.length === 0) return { ok: false, error: "requested_operations must be a non-empty array" };
  const operations: PairableLocalServiceOperation[] = [];
  for (const operation of value) {
    if (!isAllowedOperation(operation)) return { ok: false, error: "requested operation is unsupported" };
    if (operation === "service_status" || operation === "request_pairing") {
      return { ok: false, error: "requested operation does not require pairing" };
    }
    if (operations.includes(operation)) return { ok: false, error: "requested operation is duplicated" };
    operations.push(operation);
  }
  return { ok: true, operations };
}

function requireLowerHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function parseExternalReviewAcknowledgement(value: unknown): ExternalReviewAcknowledgement {
  if (!isRecord(value)) {
    throw new Error("external review acknowledgement must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "acknowledged",
    "source",
    "approval_digest",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("external review acknowledgement has unsupported fields");
  }
  if (value.format !== EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT) {
    throw new Error("external review acknowledgement format is unsupported");
  }
  if (value.acknowledged !== true) {
    throw new Error("external review acknowledgement must be explicitly acknowledged");
  }
  if (value.source !== "external-review") {
    throw new Error("external review acknowledgement source is unsupported");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("external review acknowledgement must not store production secrets");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("external review acknowledgement must not contain secret material");
  }
  return {
    format: EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT,
    acknowledged: true,
    source: "external-review",
    approval_digest: requireLowerHex64(value.approval_digest, "external review acknowledgement approval_digest"),
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

function parseOptionalExternalReviewAcknowledgement(
  value: unknown
): { ok: true; acknowledgement?: ExternalReviewAcknowledgement } | { ok: false; error: string } {
  if (value === undefined) return { ok: true };
  try {
    return { ok: true, acknowledgement: parseExternalReviewAcknowledgement(value) };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "external review acknowledgement is invalid"
    };
  }
}

function validateServiceRequest(value: unknown): { ok: true; request: LocalServiceRequest } | { ok: false; error: string } {
  if (!isRecord(value)) return { ok: false, error: "service request must be an object" };
  if (compactJsonUtf8ByteLength(value) > MAX_SERVICE_JSON_BYTES) {
    return { ok: false, error: "service request JSON exceeds max bytes" };
  }
  if (value.version !== 1) return { ok: false, error: "service request version must be 1" };
  if (!isRequestId(value.request_id)) return { ok: false, error: "service request_id is invalid" };
  if (!isAllowedOperation(value.operation)) return { ok: false, error: "service operation is unsupported" };
  if (!hasOnlyKeys(value, ["version", "request_id", "operation", "params"])) {
    return { ok: false, error: "service request has unsupported fields" };
  }
  if (value.operation === "service_status") {
    if ("params" in value) return { ok: false, error: "service_status must not include params" };
    return { ok: true, request: value as LocalServiceRequest };
  }
  if (!isRecord(value.params)) return { ok: false, error: `${value.operation} requires params` };
  const client = validateClientIdentity(value.params.client);
  if (!client.ok) return client;
  if (value.operation === "request_pairing") {
    if (!hasOnlyKeys(value.params, ["client", "requested_operations"])) {
      return { ok: false, error: "request_pairing params have unsupported fields" };
    }
    const requestedOperations = validateRequestedOperations(value.params.requested_operations);
    if (!requestedOperations.ok) return requestedOperations;
    return {
      ok: true,
      request: {
        version: 1,
        request_id: value.request_id,
        operation: "request_pairing",
        params: {
          client: client.client,
          requested_operations: requestedOperations.operations
        }
      }
    };
  }
  if (value.operation === "validate_signer_request" && "request" in value.params) {
    if (!hasOnlyKeys(value.params, ["client", "request"])) {
      return { ok: false, error: "validate_signer_request params have unsupported fields" };
    }
    return {
      ok: true,
      request: {
        version: 1,
        request_id: value.request_id,
        operation: "validate_signer_request",
        params: {
          client: client.client,
          request: value.params.request
        }
      }
    };
  }
  if (value.operation === "select_account_route" && "route_request" in value.params) {
    if (!hasOnlyKeys(value.params, ["client", "route_request"])) {
      return { ok: false, error: "select_account_route params have unsupported fields" };
    }
    return {
      ok: true,
      request: {
        version: 1,
        request_id: value.request_id,
        operation: "select_account_route",
        params: {
          client: client.client,
          route_request: value.params.route_request as RouteSelectionRequest
        }
      }
    };
  }
  if (value.operation === "dispatch_signer_request" && "route_request" in value.params && "request" in value.params) {
    if (!hasOnlyKeys(value.params, [
      "client",
      "route_request",
      "request",
      "external_review_acknowledgement"
    ])) {
      return { ok: false, error: "dispatch_signer_request params have unsupported fields" };
    }
    const acknowledgement = parseOptionalExternalReviewAcknowledgement(value.params.external_review_acknowledgement);
    if (!acknowledgement.ok) return acknowledgement;
    return {
      ok: true,
      request: {
        version: 1,
        request_id: value.request_id,
        operation: "dispatch_signer_request",
        params: {
          client: client.client,
          route_request: value.params.route_request as RouteSelectionRequest,
          request: value.params.request,
          ...(acknowledgement.acknowledgement !== undefined
            ? { external_review_acknowledgement: acknowledgement.acknowledgement }
            : {})
        }
      }
    };
  }
  if (value.operation === "verify_signer_response" && "request" in value.params && "response" in value.params) {
    if (!hasOnlyKeys(value.params, ["client", "request", "response"])) {
      return { ok: false, error: "verify_signer_response params have unsupported fields" };
    }
    return {
      ok: true,
      request: {
        version: 1,
        request_id: value.request_id,
        operation: "verify_signer_response",
        params: {
          client: client.client,
          request: value.params.request,
          response: value.params.response
        }
      }
    };
  }
  return { ok: false, error: `${value.operation} params are invalid` };
}

export function clientIdForIdentity(client: LocalClientIdentity): string {
  return sha256Utf8Hex(JSON.stringify({
    surface: client.surface,
    origin: client.origin,
    app_name: client.app_name ?? "",
    instance_id: client.instance_id ?? ""
  }));
}

function pairingDigest(intent: Omit<PairingIntent, "pairing_digest">): string {
  return sha256Utf8Hex(JSON.stringify(intent));
}

function pairingIntentDigest(intent: PairingIntent): string {
  return pairingDigest({
    format: intent.format,
    client_id: intent.client_id,
    client: intent.client,
    requested_operations: intent.requested_operations,
    requires_user_approval: intent.requires_user_approval,
    stores_production_secrets: intent.stores_production_secrets
  });
}

function pairingIntent(client: LocalClientIdentity, requestedOperations: PairableLocalServiceOperation[]): PairingIntent {
  const intentWithoutDigest: Omit<PairingIntent, "pairing_digest"> = {
    format: LOCAL_PAIRING_INTENT_FORMAT,
    client_id: clientIdForIdentity(client),
    client,
    requested_operations: requestedOperations,
    requires_user_approval: true as const,
    stores_production_secrets: false as const
  };
  return {
    ...intentWithoutDigest,
    pairing_digest: pairingDigest(intentWithoutDigest)
  };
}

export function parsePairingIntent(value: unknown): PairingIntent {
  if (!isRecord(value)) throw new Error("pairing intent must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "client_id",
    "client",
    "requested_operations",
    "pairing_digest",
    "requires_user_approval",
    "stores_production_secrets"
  ])) {
    throw new Error("pairing intent has unsupported fields");
  }
  if (value.format !== LOCAL_PAIRING_INTENT_FORMAT) {
    throw new Error("pairing intent format is unsupported");
  }
  const client = validateClientIdentity(value.client);
  if (!client.ok) throw new Error(client.error);
  const requestedOperations = validateRequestedOperations(value.requested_operations);
  if (!requestedOperations.ok) throw new Error(requestedOperations.error);
  if (typeof value.client_id !== "string" || value.client_id !== clientIdForIdentity(client.client)) {
    throw new Error("pairing intent client_id mismatch");
  }
  if (typeof value.pairing_digest !== "string" || !/^[0-9a-f]{64}$/u.test(value.pairing_digest)) {
    throw new Error("pairing intent digest is invalid");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("pairing intent must require user approval");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("pairing intent must not store production secrets");
  }
  const pairing: PairingIntent = {
    format: LOCAL_PAIRING_INTENT_FORMAT,
    client_id: value.client_id,
    client: client.client,
    requested_operations: requestedOperations.operations,
    pairing_digest: value.pairing_digest,
    requires_user_approval: true,
    stores_production_secrets: false
  };
  if (pairing.pairing_digest !== pairingIntentDigest(pairing)) {
    throw new Error("pairing intent digest mismatch");
  }
  return pairing;
}

function requireNonNegativeTimestamp(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer timestamp`);
  }
  return value;
}

export function approvePairingIntent(
  intent: unknown,
  options: { approvedAt: number; expiresAt?: number }
): LocalPairingApproval {
  const pairing = parsePairingIntent(intent);
  const approvedAt = requireNonNegativeTimestamp(options.approvedAt, "approvedAt");
  const expiresAt = options.expiresAt === undefined
    ? undefined
    : requireNonNegativeTimestamp(options.expiresAt, "expiresAt");
  if (expiresAt !== undefined && expiresAt <= approvedAt) {
    throw new Error("expiresAt must be greater than approvedAt");
  }
  const grant: LocalClientGrant = {
    client_id: pairing.client_id,
    origin: pairing.client.origin,
    surface: pairing.client.surface,
    allowed_operations: [...pairing.requested_operations],
    pairing_digest: pairing.pairing_digest,
    approved_at: approvedAt,
    ...(expiresAt !== undefined ? { expires_at: expiresAt } : {})
  };
  return {
    format: LOCAL_PAIRING_APPROVAL_FORMAT,
    pairing_digest: pairing.pairing_digest,
    approved_at: approvedAt,
    grant,
    stores_production_secrets: false
  };
}

function grantApprovedAt(grant: LocalClientGrant): number {
  return typeof grant.approved_at === "number" && Number.isInteger(grant.approved_at) && grant.approved_at >= 0
    ? grant.approved_at
    : 0;
}

function selectClientGrant(context: LocalServiceContext, client: LocalClientIdentity): LocalClientGrant | undefined {
  const clientId = clientIdForIdentity(client);
  let selected: LocalClientGrant | undefined;
  let selectedApprovedAt = -1;
  for (const candidate of context.grants ?? []) {
    if (
      candidate.client_id !== clientId ||
      candidate.origin !== client.origin ||
      candidate.surface !== client.surface
    ) {
      continue;
    }
    const approvedAt = grantApprovedAt(candidate);
    if (selected === undefined || approvedAt >= selectedApprovedAt) {
      selected = candidate;
      selectedApprovedAt = approvedAt;
    }
  }
  return selected;
}

function authorizeClient(
  context: LocalServiceContext,
  client: LocalClientIdentity,
  operation: PairableLocalServiceOperation
): { ok: true } | { ok: false; error: string } {
  const now = context.now ?? Math.floor(Date.now() / 1000);
  const grant = selectClientGrant(context, client);
  if (grant === undefined) return { ok: false, error: "client is not paired" };
  if (grant.revoked === true) return { ok: false, error: "client pairing is revoked" };
  if (grant.expires_at !== undefined && grant.expires_at <= now) {
    return { ok: false, error: "client pairing is expired" };
  }
  if (!grant.allowed_operations.includes(operation)) {
    return { ok: false, error: "client is not authorized for operation" };
  }
  return { ok: true };
}

function serviceStatus(requestId: string): LocalServiceResponse {
  return {
    version: 1,
    request_id: requestId,
    ok: true,
    result: {
      service: {
        protocol: LOCAL_SERVICE_PROTOCOL,
        name: LOCAL_SERVICE_NAME,
        operations: [...LOCAL_SERVICE_OPERATIONS],
        requires_pairing: true,
        stores_production_secrets: false
      }
    }
  };
}

export function handleLocalServiceRequest(value: unknown, context: LocalServiceContext = {}): LocalServiceResponse {
  const serviceRequest = validateServiceRequest(value);
  if (!serviceRequest.ok) {
    return errorResponse(value, "invalid_service_request", serviceRequest.error);
  }

  const request = serviceRequest.request;
  if (request.operation === "service_status") return serviceStatus(request.request_id);
  if (request.operation === "request_pairing") {
    return {
      version: 1,
      request_id: request.request_id,
      ok: true,
      result: {
        pairing_intent: pairingIntent(request.params.client, request.params.requested_operations)
      }
    };
  }

  const authorization = authorizeClient(context, request.params.client, request.operation);
  if (!authorization.ok) {
    return errorResponse(request, "unauthorized_client", authorization.error);
  }

  if (request.operation === "validate_signer_request") {
    const validation = validateRequest(request.params.request);
    return {
      version: 1,
      request_id: request.request_id,
      ok: true,
      result: validationResult(validation.ok, validation.error)
    };
  }
  if (request.operation === "select_account_route") {
    try {
      return {
        version: 1,
        request_id: request.request_id,
        ok: true,
        result: {
          route_selection: selectAccountRoute(context.accounts ?? [], request.params.route_request)
        }
      };
    } catch (error) {
      return errorResponse(
        request,
        "route_selection_failed",
        error instanceof Error ? error.message : "route selection failed"
      );
    }
  }
  if (request.operation === "dispatch_signer_request") {
    return dispatchSignerRequest(request, context);
  }

  return verifySignerResponse(request);
}

export async function handleLocalServiceRequestAsync(
  value: unknown,
  context: LocalServiceContext = {}
): Promise<LocalServiceResponse> {
  const serviceRequest = validateServiceRequest(value);
  if (!serviceRequest.ok) {
    return errorResponse(value, "invalid_service_request", serviceRequest.error);
  }
  if (serviceRequest.request.operation !== "dispatch_signer_request") {
    return handleLocalServiceRequest(value, context);
  }
  return dispatchSignerRequestAsync(serviceRequest.request, context);
}

function verifySignerResponsePayload(
  signerRequestPayload: unknown,
  signerResponsePayload: unknown,
  expectedPublicKey?: string
): { ok: true } | { ok: false; error: string } {
  const signerRequest = validateRequest(signerRequestPayload);
  if (!signerRequest.ok) {
    return { ok: false, error: signerRequest.error ?? "signer request is invalid" };
  }
  const signerResponse = validateResponse(signerResponsePayload);
  if (!signerResponse.ok) {
    return { ok: false, error: signerResponse.error ?? "signer response is invalid" };
  }
  if (
    isRecord(signerRequestPayload) &&
    isRecord(signerResponsePayload) &&
    signerRequestPayload.request_id !== signerResponsePayload.request_id
  ) {
    return { ok: false, error: "response request_id does not match request" };
  }
  if (
    isRecord(signerRequestPayload) &&
    signerRequestPayload.method === "sign_event" &&
    isRecord(signerResponsePayload) &&
    signerResponsePayload.ok === true
  ) {
    const verification = verifySignedEventResponse(signerRequestPayload, signerResponsePayload);
    if (!verification.ok) {
      return { ok: false, error: verification.error ?? "signer response verification failed" };
    }
  }
  if (expectedPublicKey !== undefined) {
    const responsePublicKey = responsePublicKeyForRequest(signerRequestPayload, signerResponsePayload);
    if (responsePublicKey !== undefined && responsePublicKey !== expectedPublicKey) {
      return { ok: false, error: "signer response public key does not match selected route" };
    }
  }
  return { ok: true };
}

function responsePublicKeyForRequest(signerRequestPayload: unknown, signerResponsePayload: unknown): string | undefined {
  if (!isRecord(signerRequestPayload) || !isRecord(signerResponsePayload) || signerResponsePayload.ok !== true) {
    return undefined;
  }
  if (signerRequestPayload.method === "get_public_key" && isRecord(signerResponsePayload.result)) {
    return typeof signerResponsePayload.result.public_key === "string"
      ? signerResponsePayload.result.public_key
      : undefined;
  }
  if (
    signerRequestPayload.method === "sign_event" &&
    isRecord(signerResponsePayload.result) &&
    isRecord(signerResponsePayload.result.event)
  ) {
    return typeof signerResponsePayload.result.event.pubkey === "string"
      ? signerResponsePayload.result.event.pubkey
      : undefined;
  }
  return undefined;
}

function verifySignerResponse(request: Extract<LocalServiceRequest, { operation: "verify_signer_response" }>): LocalServiceResponse {
  const verification = verifySignerResponsePayload(request.params.request, request.params.response);
  return {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: validationResult(verification.ok, verification.ok ? undefined : verification.error)
  };
}

function prepareSignerDispatch(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  context: LocalServiceContext
): PreparedSignerDispatch {
  const signerRequest = validateRequest(request.params.request);
  if (!signerRequest.ok) {
    return {
      ok: false,
      response: errorResponse(request, "invalid_signer_request", signerRequest.error ?? "signer request is invalid")
    };
  }

  let routeRequest: RouteSelectionRequest;
  try {
    routeRequest = parseRouteSelectionRequest(request.params.route_request);
  } catch (error) {
    return {
      ok: false,
      response: errorResponse(
        request,
        "route_selection_failed",
        error instanceof Error ? error.message : "route selection request is invalid"
      )
    };
  }
  if (isRecord(request.params.request) && routeRequest.method !== request.params.request.method) {
    return {
      ok: false,
      response: errorResponse(request, "route_selection_failed", "route selection method does not match signer request")
    };
  }

  let routeSelection: RouteSelection;
  try {
    routeSelection = selectAccountRoute(context.accounts ?? [], routeRequest);
  } catch (error) {
    return {
      ok: false,
      response: errorResponse(
        request,
        "route_selection_failed",
        error instanceof Error ? error.message : "route selection failed"
      )
    };
  }

  const acknowledgement = request.params.external_review_acknowledgement;
  if (acknowledgement !== undefined) {
    return {
      ok: false,
      response: errorResponse(
        request,
        "external_review_acknowledgement_unsupported",
        "host review acknowledgements are unsupported for signer dispatch"
      )
    };
  }

  if (context.signerDispatcher === undefined) {
    return {
      ok: false,
      response: errorResponse(request, "signer_route_unavailable", "signer dispatch is not configured")
    };
  }

  const dispatchRequest: SignerDispatchRequest = {
    client: structuredClone(request.params.client),
    route_selection: structuredClone(routeSelection),
    request: structuredClone(request.params.request)
  };
  let active = true;
  const cancellation = new AbortController();
  let timeoutMs: number | undefined;
  let current = (): void => { if (!active) compatibilityError("runtime_unavailable", "operation is no longer active"); };
  if (routeSelection.contract === "nsealr.signing.v2") {
    try {
      if (!context.signerCompatibility) compatibilityError("runtime_unavailable", "current local adapter observations are not configured");
      const provider = context.signerCompatibility;
      const snapshot = provider(routeSelection, dispatchRequest.request);
      const effective = assessSignerCompatibility(routeSelection, dispatchRequest.request, snapshot);
      const maximum = Math.min(effective.method.pending_requests, effective.transport.pending_requests);
      if ((pendingDispatches.get(context) ?? 0) >= maximum) compatibilityError("runtime_unavailable", "pending operation capacity is exhausted");
      const clock = context.monotonicNow ?? (() => performance.now());
      const start = clock();
      if (start === undefined || !Number.isFinite(start) || start < 0 || start > Number.MAX_SAFE_INTEGER) compatibilityError("runtime_unavailable", "local monotonic clock is unavailable");
      const duration = Math.min(effective.method.deadline_ms, effective.transport.deadline_ms);
      timeoutMs = duration;
      const deadline = start + duration;
      if (!Number.isFinite(deadline) || deadline > Number.MAX_SAFE_INTEGER) compatibilityError("runtime_unavailable", "local deadline overflow");
      const selectedAccount = () => (context.accounts ?? []).find((account) => account.account_id === routeSelection.account_id);
      const original = sha256Utf8Hex(JSON.stringify([snapshot, routeSelection, dispatchRequest.request, selectedAccount()]));
      let last = start;
      current = () => {
        if (!active) compatibilityError("runtime_unavailable", "operation is no longer active");
        const now = clock();
        if (now === undefined || !Number.isFinite(now) || now < last || now >= deadline) compatibilityError("runtime_unavailable", "local deadline expired or clock rolled back/unavailable");
        last = now;
        const accountRoute = selectAccountRoute(context.accounts ?? [], routeRequest);
        const live = provider(accountRoute, dispatchRequest.request);
        assessSignerCompatibility(accountRoute, dispatchRequest.request, live);
        if (sha256Utf8Hex(JSON.stringify([live, accountRoute, dispatchRequest.request, selectedAccount()])) !== original) compatibilityError("runtime_unavailable", "account, capabilities, connection or limits changed; select again");
      };
      dispatchRequest.before_write = current;
      dispatchRequest.effective_limits = effective;
      dispatchRequest.abort_signal = cancellation.signal;
      pendingDispatches.set(context, (pendingDispatches.get(context) ?? 0) + 1);
    } catch (error) {
      return { ok: false, response: dispatchFailureResponse(request, error) };
    }
  }

  return {
    ok: true,
    dispatcher: context.signerDispatcher,
    dispatchRequest,
    checkCurrent: current,
    timeout_ms: timeoutMs,
    release: () => {
      if (!active) return;
      active = false;
      cancellation.abort();
      if (dispatchRequest.effective_limits) pendingDispatches.set(context, Math.max(0, (pendingDispatches.get(context) ?? 1) - 1));
    }
  };
}

function dispatchFailureResponse(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  error: unknown
): LocalServiceResponse {
  if (error instanceof CapabilityError) return errorResponse(request, error.reason, error.message);
  if (error instanceof SignerRouteUnavailableError) {
    return errorResponse(request, "signer_route_unavailable", error.message);
  }
  if (error instanceof SignerTransportError) {
    return errorResponse(request, error.code, error.message);
  }
  return errorResponse(
    request,
    "signer_dispatch_failed",
    error instanceof Error ? error.message : "signer dispatch failed"
  );
}

function dispatchSuccessResponse(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  routeSelection: RouteSelection,
  signerResponse: unknown
): LocalServiceResponse {
  const verification = verifySignerResponsePayload(request.params.request, signerResponse, routeSelection.public_key);
  if (!verification.ok) {
    return errorResponse(request, "invalid_signer_response", verification.error);
  }
  return {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      signer_response: signerResponse
    }
  };
}

function checkDispatchResponseCapacity(dispatch: SignerDispatchRequest, response: unknown): void {
  const effective = dispatch.effective_limits;
  if (!effective) return;
  const bytes = compactJsonUtf8ByteLength(response);
  if (bytes > effective.method.response_json_bytes || bytes > effective.transport.reassembly_bytes) compatibilityError("limit_exceeded", "response exceeds effective capacity");
}

function dispatchSignerRequest(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  context: LocalServiceContext
): LocalServiceResponse {
  const prepared = prepareSignerDispatch(request, context);
  if (!prepared.ok) return prepared.response;

  let signerResponse: unknown;
  try {
    prepared.checkCurrent();
    signerResponse = prepared.dispatcher(prepared.dispatchRequest);
    prepared.checkCurrent();
    if (!isPromiseLike(signerResponse)) checkDispatchResponseCapacity(prepared.dispatchRequest, signerResponse);
  } catch (error) {
    return dispatchFailureResponse(request, error);
  } finally {
    prepared.release();
  }

  if (isPromiseLike(signerResponse)) {
    signerResponse.then(undefined, () => undefined);
    return errorResponse(
      request,
      "signer_dispatch_failed",
      "async signer dispatcher requires handleLocalServiceRequestAsync"
    );
  }
  return dispatchSuccessResponse(request, prepared.dispatchRequest.route_selection, signerResponse);
}

async function dispatchSignerRequestAsync(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  context: LocalServiceContext
): Promise<LocalServiceResponse> {
  const prepared = prepareSignerDispatch(request, context);
  if (!prepared.ok) return prepared.response;

  let signerResponse: unknown;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    prepared.checkCurrent();
    const operation = prepared.dispatcher(prepared.dispatchRequest);
    signerResponse = prepared.timeout_ms === undefined ? await operation : await Promise.race([
      operation,
      new Promise<never>((_resolve, reject) => {
        timer = setTimeout(() => reject(new SignerTransportError("signer_transport_timeout", "local operation deadline expired")), prepared.timeout_ms);
      })
    ]);
    prepared.checkCurrent();
    checkDispatchResponseCapacity(prepared.dispatchRequest, signerResponse);
  } catch (error) {
    return dispatchFailureResponse(request, error);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
    prepared.release();
  }
  return dispatchSuccessResponse(request, prepared.dispatchRequest.route_selection, signerResponse);
}
