import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, utf8ToBytes } from "@noble/hashes/utils.js";
import { computeEventId, verifySchnorrSignature } from "@nsealr/core";
import { compactJsonUtf8ByteLength, NSEALR_V0_LIMITS, parseStrictJson, validateRequest, validateResponse } from "@nsealr/protocol";

export type Nip46RequestMessage = {
  id: string;
  method: string;
  params: string[];
};

export type Nip46ResponseMessage = {
  id: string;
  result?: string;
  error?: string;
};

export type Nip46Permission = {
  method: string;
  parameter?: string;
  event_kind?: number;
};

export type Nip46PermissionRequirement = Nip46Permission;

export type Nip46ConnectIntent = {
  id: string;
  remote_signer_pubkey: string;
  secret?: string;
  requested_permissions: Nip46Permission[];
};

export type Nip46ConnectionUriDescriptor = {
  format: "nsealr-nip46-connection-uri-v0";
  kind: "bunker" | "nostrconnect";
  remote_signer_pubkey?: string;
  client_pubkey?: string;
  relays: string[];
  secret_present: boolean;
  requested_permissions: Nip46Permission[];
  client_metadata?: {
    name?: string;
    url?: string;
    image?: string;
  };
  starts_relay_session: false;
  creates_grants: false;
  stores_production_secrets: false;
  exposes_secret: false;
};

export type Nip46ConnectionTokenResponse = {
  format: "nsealr-nip46-connection-token-response-v0";
  kind: "nostrconnect";
  client_pubkey: string;
  remote_signer_pubkey: string;
  relays: string[];
  requested_permissions: Nip46Permission[];
  client_metadata?: {
    name?: string;
    url?: string;
    image?: string;
  };
  response_message_id: string;
  client_pubkey_bound_to_recipient: true;
  secret_matched: true;
  starts_relay_session: false;
  derives_nip44_key: false;
  acknowledges_connect: false;
  opens_relay: false;
  creates_grants: false;
  dispatches_signer: false;
  stores_production_secrets: false;
  persists_session_state: false;
  exposes_secret: false;
  contains_secret_material: false;
};

export type Nip46RelayEventDirection = "client_to_remote_signer" | "remote_signer_to_client";

export type Nip46RelayEventEnvelope = {
  format: "nsealr-nip46-relay-event-envelope-v0";
  direction: Nip46RelayEventDirection;
  sender_pubkey: string;
  recipient_pubkey: string;
  encrypted_content: string;
  has_signed_event_fields: boolean;
  event_id_verified: boolean;
  event_signature_verified: boolean;
  decrypts_content: false;
  opens_relay: false;
  creates_grants: false;
  stores_production_secrets: false;
};

export type Nip46RelayRequestStep = {
  format: "nsealr-nip46-relay-request-step-v0";
  envelope: Nip46RelayEventEnvelope;
  message_id: string;
  bridge_decision: Nip46BridgeDecision;
  decrypts_content: false;
  opens_relay: false;
  creates_grants: false;
  acknowledges_connect: false;
  dispatches_signer: false;
  stores_production_secrets: false;
  persists_session_state: false;
};

export type Nip46RelayResponseResultType =
  | "signed_event_result"
  | "public_key_result"
  | "connect_ack_result"
  | "relay_list_result"
  | "relay_no_change_result"
  | "pong_result"
  | "auth_challenge"
  | "error";

export type Nip46RelayResponseStep = {
  format: "nsealr-nip46-relay-response-step-v1";
  envelope: Nip46RelayEventEnvelope;
  message_id: string;
  response_message: Nip46ResponseMessage;
  result_type: Nip46RelayResponseResultType;
  auth_url?: string;
  relay_urls?: string[] | null;
  signed_event_shape_checked: boolean;
  signed_event_id_verified: boolean;
  signed_event_signature_verified: boolean;
  result_pubkey?: string;
  result_pubkey_bound_to_expected_user: boolean;
  decrypts_content: false;
  opens_relay: false;
  creates_grants: false;
  acknowledges_connect: false;
  dispatches_signer: false;
  relay_event_signature_verified: boolean;
  stores_production_secrets: false;
  persists_session_state: false;
};

export type Nip46ConnectReview = {
  format: "nsealr-nip46-connect-review-v0";
  id: string;
  remote_signer_pubkey: string;
  secret_present: boolean;
  requested_permissions: Nip46Permission[];
  pages: Array<{
    title: string;
    page_indicator: string;
    body_lines: string[];
  }>;
  connect_digest: string;
};

export type Nip46ConnectApproval = {
  format: "nsealr-nip46-connect-approval-v0";
  id: string;
  connect_digest: string;
  approved_at: number;
  acknowledges_connect: false;
  creates_grants: false;
  opens_relay: false;
  persists_session_state: false;
  stores_production_secrets: false;
  exposes_secret: false;
};

export type Nip46AuthChallengeReview = {
  format: "nsealr-nip46-auth-challenge-review-v0";
  id: string;
  remote_signer_pubkey: string;
  client_pubkey: string;
  auth_url: string;
  pages: Array<{
    title: string;
    page_indicator: string;
    body_lines: string[];
  }>;
  opens_url: false;
  opens_relay: false;
  acknowledges_connect: false;
  creates_grants: false;
  dispatches_signer: false;
  persists_session_state: false;
  stores_production_secrets: false;
  exposes_secret: false;
  contains_secret_material: false;
  auth_challenge_digest: string;
};

export type Nip46AuthChallengeApproval = {
  format: "nsealr-nip46-auth-challenge-approval-v0";
  id: string;
  auth_challenge_digest: string;
  approved_at: number;
  opens_url: false;
  opens_relay: false;
  acknowledges_connect: false;
  creates_grants: false;
  dispatches_signer: false;
  persists_session_state: false;
  stores_production_secrets: false;
  exposes_secret: false;
  contains_secret_material: false;
};

export type Nip46SessionLifecycle = {
  name: string;
  format: "nsealr-nip46-session-lifecycle-v0";
  phase: "approved_pending_ack";
  client_pubkey: string;
  remote_signer_pubkey: string;
  relays: string[];
  connect_digest: string;
  approved_at: number;
  expires_at: number;
  requested_permissions: Nip46Permission[];
  approved_permissions: Nip46Permission[];
  secret_present: boolean;
  secret_value_stored: false;
  contains_secret_material: false;
  derives_nip44_key: false;
  acknowledges_connect: false;
  opens_relay: false;
  creates_grants: false;
  dispatches_signer: false;
  stores_production_secrets: false;
  persists_session_state: false;
  scope: string;
};

export type Nip46SessionRequestGate = {
  format: "nsealr-nip46-session-request-gate-v0";
  session_name: string;
  session_phase: "approved_pending_ack";
  evaluated_at: number;
  envelope: Nip46RelayEventEnvelope;
  message_id: string;
  permission_requirement: Nip46PermissionRequirement;
  blocked_reason: "connect_ack_pending";
  response_message: Nip46ResponseMessage;
  client_pubkey_bound_to_sender: true;
  remote_signer_pubkey_bound_to_recipient: true;
  session_not_expired: true;
  uses_session_permissions: false;
  decrypts_content: false;
  opens_relay: false;
  creates_grants: false;
  acknowledges_connect: false;
  dispatches_signer: false;
  stores_production_secrets: false;
  persists_session_state: false;
};

export type Nip46ConnectApprovalOptions = {
  reviewedConnectDigest: string;
  approvedAt: number;
};

export type Nip46AuthChallengeApprovalOptions = {
  reviewedAuthChallengeDigest: string;
  approvedAt: number;
};

export type Nip46SessionLifecycleCheckpointOptions = {
  name: string;
  clientPubkey: string;
  relays: string[];
  approvedPermissions: unknown[];
  expiresAt: number;
};

export type Nip46BridgeDecision =
  | {
      type: "connect_review";
      connect_intent: Nip46ConnectIntent;
    }
  | {
      type: "local_response";
      permission_requirement: Nip46PermissionRequirement;
      response_message: Nip46ResponseMessage;
    }
  | {
      type: "signer_request";
      permission_requirement: Nip46PermissionRequirement;
      nsealr_request: NSealrBridgeRequest;
    }
  | {
      type: "permission_denied";
      permission_requirement: Nip46PermissionRequirement;
      response_message: Nip46ResponseMessage;
    };

const NIP46_PERMISSION_METHODS = new Set([
  "sign_event",
  "nip04_encrypt",
  "nip04_decrypt",
  "nip44_encrypt",
  "nip44_decrypt",
  "get_public_key",
  "ping",
  "switch_relays"
]);

const NIP46_CONNECTION_URI_PARAMS = new Set(["relay", "secret", "perms", "name", "url", "image"]);
const NIP46_RELAY_DIRECTIONS = new Set(["client_to_remote_signer", "remote_signer_to_client"]);
const NIP46_SESSION_PHASES = new Set(["approved_pending_ack"]);
const NIP46_SESSION_FALSE_FIELDS = [
  "secret_value_stored",
  "contains_secret_material",
  "derives_nip44_key",
  "acknowledges_connect",
  "opens_relay",
  "creates_grants",
  "dispatches_signer",
  "stores_production_secrets",
  "persists_session_state"
] as const;
export const NIP46_SESSION_SECRET_FIELDS = new Set([
  "secret",
  "shared_secret",
  "session_secret",
  "nip44_key",
  "secret_key",
  "private_key",
  "nsec",
  "mnemonic",
  "seed",
  "passphrase"
]);
const NIP46_SESSION_ACTIVE_PHASES = new Set(["connect_ack", "session_active", "session_closed"]);
const NIP46_SESSION_ACTIVE_ALWAYS_FALSE = [
  "secret_value_stored",
  "contains_secret_material",
  "stores_production_secrets"
] as const;
// Exact expected lifecycle-flag values per active-session phase (machine-checkable).
export const NIP46_SESSION_ACTIVE_PHASE_FLAGS = {
  connect_ack: { acknowledges_connect: true, derives_nip44_key: true, opens_relay: true, dispatches_signer: false },
  session_active: { acknowledges_connect: true, derives_nip44_key: true, opens_relay: true, dispatches_signer: true },
  session_closed: { acknowledges_connect: true, derives_nip44_key: false, opens_relay: false, dispatches_signer: false }
} as const;
const X_ONLY_PUBKEY = /^[0-9a-f]{64}$/u;
const HEX_64_BYTE = /^[0-9a-f]{128}$/u;
const CONNECT_REVIEW_DIGEST_FORMAT = "nsealr-nip46-connect-digest-v0";
const AUTH_CHALLENGE_REVIEW_DIGEST_FORMAT = "nsealr-nip46-auth-challenge-digest-v0";
const NIP46_AUTH_CHALLENGE_FALSE_FIELDS = [
  "opens_url",
  "opens_relay",
  "acknowledges_connect",
  "creates_grants",
  "dispatches_signer",
  "persists_session_state",
  "stores_production_secrets",
  "exposes_secret",
  "contains_secret_material"
] as const;

type NSealrBridgeRequest =
  | {
      version: 1;
      request_id: string;
      method: "get_public_key";
    }
  | {
      version: 1;
      request_id: string;
      method: "sign_event";
      params: {
        event_template: unknown;
      };
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertOnlyKeys(value: Record<string, unknown>, allowedKeys: readonly string[], context: string): void {
  const allowed = new Set(allowedKeys);
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0) throw new Error(`${context} contains unknown fields: ${unknown.sort().join(", ")}`);
}

function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    const encoded = JSON.stringify(value);
    if (encoded === undefined) throw new Error("unsupported value in NIP-46 digest");
    return encoded;
  }
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }
  throw new Error("unsupported value in NIP-46 digest");
}

function sha256Utf8Hex(value: string): string {
  return bytesToHex(sha256(utf8ToBytes(value)));
}

function requireNip46Id(value: unknown): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(value)) {
    throw new Error("NIP-46 request id is invalid");
  }
  return value;
}

function requireLowerHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !X_ONLY_PUBKEY.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireXOnlyPubkey(value: unknown, label: string): string {
  return requireLowerHex64(value, `NIP-46 ${label}`);
}

function requireNip46RelayDirection(value: unknown): Nip46RelayEventDirection {
  if (typeof value !== "string" || !NIP46_RELAY_DIRECTIONS.has(value)) {
    throw new Error("NIP-46 relay event direction is invalid");
  }
  return value as Nip46RelayEventDirection;
}

function requireSignedEventFields(value: Record<string, unknown>): boolean {
  const signedFieldNames = ["id", "created_at", "sig"] as const;
  const presentFields = signedFieldNames.filter((field) => field in value);
  if (presentFields.length === 0) return false;
  if (presentFields.length !== signedFieldNames.length) {
    throw new Error("NIP-46 relay event signed fields must be complete when present");
  }
  if (typeof value.id !== "string" || !X_ONLY_PUBKEY.test(value.id)) {
    throw new Error("NIP-46 relay event id must be 32-byte lowercase hex");
  }
  if (
    typeof value.created_at !== "number" ||
    !Number.isSafeInteger(value.created_at) ||
    value.created_at < 0
  ) {
    throw new Error("NIP-46 relay event created_at must be a safe non-negative integer");
  }
  if (typeof value.sig !== "string" || !HEX_64_BYTE.test(value.sig)) {
    throw new Error("NIP-46 relay event sig must be 64-byte lowercase hex");
  }
  return true;
}

function verifySignedRelayEvent(value: Record<string, unknown>, senderPubkey: string, tags: string[][]): boolean {
  if (!requireSignedEventFields(value)) return false;
  const computedId = computeEventId({
    pubkey: senderPubkey,
    created_at: value.created_at as number,
    kind: 24133,
    tags,
    content: value.content as string
  });
  if (value.id !== computedId) {
    throw new Error("NIP-46 relay event id does not match NIP-01 canonical serialization");
  }
  if (!verifySchnorrSignature(senderPubkey, computedId, value.sig as string)) {
    throw new Error("NIP-46 relay event signature is invalid");
  }
  return true;
}

function requireSingleQueryParam(params: URLSearchParams, name: string): string | undefined {
  const values = params.getAll(name);
  if (values.length > 1) throw new Error(`NIP-46 connection URI ${name} must appear at most once`);
  return values[0];
}

function requireRelayUrl(value: string, context = "NIP-46 connection URI relay"): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch (error) {
    throw new Error(`${context} must be a valid URL`);
  }
  if (parsed.protocol !== "wss:" || parsed.username !== "" || parsed.password !== "" || parsed.hash !== "") {
    throw new Error(`${context} must be a wss URL without credentials or fragment`);
  }
  if (parsed.hostname === "") throw new Error(`${context} host is required`);
  return parsed.toString();
}

function requireOptionalHttpUrl(value: string, name: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch (error) {
    throw new Error(`NIP-46 connection URI ${name} must be a valid URL`);
  }
  if (
    (parsed.protocol !== "https:" && parsed.protocol !== "http:") ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    parsed.hash !== ""
  ) {
    throw new Error(`NIP-46 connection URI ${name} must be an http(s) URL without credentials or fragment`);
  }
  return parsed.toString();
}

function requireNip46AuthUrl(value: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch (error) {
    throw new Error("NIP-46 auth challenge URL must be a valid URL");
  }
  if (
    (parsed.protocol !== "https:" && parsed.protocol !== "http:") ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    parsed.hash !== ""
  ) {
    throw new Error("NIP-46 auth challenge URL must be an http(s) URL without credentials or fragment");
  }
  if (parsed.hostname === "") throw new Error("NIP-46 auth challenge URL host is required");
  return parsed.toString();
}

function requireMessage(value: unknown): Nip46RequestMessage {
  if (!isRecord(value)) throw new Error("NIP-46 message must be an object");
  if (compactJsonUtf8ByteLength(value) > NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes) {
    throw new Error("NIP-46 decrypted message JSON exceeds max_nip46_decrypted_message_json_bytes");
  }
  const id = requireNip46Id(value.id);
  if (typeof value.method !== "string" || value.method.length === 0) {
    throw new Error("NIP-46 method is required");
  }
  if (!Array.isArray(value.params) || !value.params.every((param) => typeof param === "string")) {
    throw new Error("NIP-46 params must be an array of strings");
  }
  return {
    id,
    method: value.method,
    params: value.params
  };
}

export function requireResponseMessage(value: unknown): Nip46ResponseMessage {
  if (!isRecord(value)) throw new Error("NIP-46 response message must be an object");
  if (compactJsonUtf8ByteLength(value) > NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes) {
    throw new Error("NIP-46 decrypted response JSON exceeds max_nip46_decrypted_message_json_bytes");
  }
  assertOnlyKeys(value, ["id", "result", "error"], "NIP-46 response message");
  const id = requireNip46Id(value.id);
  const hasResult = "result" in value;
  const hasError = "error" in value;
  if (hasResult && hasError) {
    if (value.result === "auth_url" && typeof value.error === "string") {
      return { id, result: "auth_url", error: requireNip46AuthUrl(value.error) };
    }
    throw new Error("NIP-46 response message result and error together are only allowed for auth_url");
  }
  if (!hasResult && !hasError) {
    throw new Error("NIP-46 response message must contain result or error");
  }
  if (hasResult) {
    if (typeof value.result !== "string") throw new Error("NIP-46 response message result must be a string");
    return { id, result: value.result };
  }
  if (typeof value.error !== "string") throw new Error("NIP-46 response message error must be a string");
  return { id, error: value.error };
}

function parseJsonParam(param: string, label: string): unknown {
  try {
    return parseStrictJson(param, NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes);
  } catch (error) {
    throw new Error(`NIP-46 ${label} param must be valid JSON`);
  }
}

function assertValidNSealrRequest(request: NSealrBridgeRequest): void {
  const result = validateRequest(request);
  if (!result.ok) throw new Error(result.error ?? "invalid nSealr request");
}

function parseSignEventPermissionKind(parameter: string): number {
  if (!/^[0-9]+$/u.test(parameter)) throw new Error("NIP-46 sign_event permission kind must be numeric");
  const eventKind = Number(parameter);
  if (
    !Number.isSafeInteger(eventKind) ||
    eventKind < 0 ||
    eventKind > NSEALR_V0_LIMITS.max_safe_integer
  ) {
    throw new Error("NIP-46 sign_event permission kind must be a safe non-negative integer");
  }
  return eventKind;
}

export function parseNip46Permissions(value: string): Nip46Permission[] {
  if (value.trim() === "") return [];
  return value.split(",").map((item) => {
    const permission = item.trim();
    if (permission.length === 0) throw new Error("NIP-46 permission entries must be non-empty");
    const [method, parameter, extra] = permission.split(":");
    if (!method || extra !== undefined) throw new Error("NIP-46 permission format is invalid");
    if (method === "connect") throw new Error("NIP-46 permissions must not request connect");
    if (!NIP46_PERMISSION_METHODS.has(method)) throw new Error(`unsupported permission method: ${method}`);
    if (method === "sign_event" && parameter !== undefined) {
      const event_kind = parseSignEventPermissionKind(parameter);
      return {
        method,
        parameter,
        event_kind
      };
    }
    if (parameter !== undefined) {
      throw new Error(`NIP-46 permission method does not accept a parameter: ${method}`);
    }
    return { method };
  });
}

export function parseNip46ApprovedPermissions(value: string): Nip46Permission[] {
  const permissions = parseNip46Permissions(value);
  for (const permission of permissions) {
    if (permission.method === "sign_event" && permission.parameter === undefined) {
      throw new Error("approved sign_event permission must include parameter and event_kind");
    }
  }
  return permissions;
}

function parseNip46PermissionObject(permission: unknown, context: string, approvedOnly: boolean): Nip46Permission {
  if (!isRecord(permission) || typeof permission.method !== "string") {
    throw new Error(`${context}: permission entries must include method`);
  }
  if (!NIP46_PERMISSION_METHODS.has(permission.method)) {
    throw new Error(`${context}: permission method is invalid`);
  }
  if (permission.method === "sign_event") {
    if (permission.parameter === undefined) {
      if (!approvedOnly) {
        assertOnlyKeys(permission, ["method"], context);
        return { method: "sign_event" };
      }
      throw new Error(`${context}: approved sign_event permission must include parameter and event_kind`);
    }
    const parameter = permission.parameter;
    const eventKind = permission.event_kind;
    const parsedParameterKind = typeof parameter === "string" ? Number(parameter) : Number.NaN;
    if (
      typeof parameter !== "string" ||
      !/^[0-9]+$/u.test(parameter) ||
      typeof eventKind !== "number" ||
      !Number.isSafeInteger(eventKind) ||
      eventKind < 0 ||
      eventKind > NSEALR_V0_LIMITS.max_safe_integer ||
      eventKind !== parsedParameterKind ||
      !Number.isSafeInteger(parsedParameterKind)
    ) {
      throw new Error(`${context}: sign_event permission parameter must match event_kind and be safe`);
    }
    if (Object.keys(permission).some((key) => !["method", "parameter", "event_kind"].includes(key))) {
      throw new Error(`${context}: sign_event permission contains unknown fields`);
    }
    return {
      method: "sign_event",
      parameter,
      event_kind: eventKind
    };
  }
  if ("parameter" in permission || "event_kind" in permission || Object.keys(permission).length !== 1) {
    throw new Error(`${context}: non-sign_event permission must only include method`);
  }
  return { method: permission.method };
}

function parseNip46RequestedPermission(permission: unknown, context: string): Nip46Permission {
  return parseNip46PermissionObject(permission, context, false);
}

function parseNip46PolicyPermission(permission: unknown, context: string): Nip46Permission {
  return parseNip46PermissionObject(permission, context, true);
}

export function parseNip46PolicyFile(policy: unknown, context = "NIP-46 policy file"): Nip46Permission[] {
  if (!isRecord(policy) || policy.format !== "nsealr-nip46-policy-v0") {
    throw new Error(`${context}: must use format nsealr-nip46-policy-v0`);
  }
  if (!Array.isArray(policy.approved_permissions)) {
    throw new Error(`${context}: approved_permissions must be a list`);
  }
  return policy.approved_permissions.map((permission) => parseNip46PolicyPermission(permission, context));
}

function parseNip46ConnectionUriWithSecret(value: string): {
  descriptor: Nip46ConnectionUriDescriptor;
  secret?: string;
} {
  if (typeof value !== "string" || value.trim() !== value || value.length === 0) {
    throw new Error("NIP-46 connection URI must be a non-empty trimmed string");
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch (error) {
    throw new Error("NIP-46 connection URI is invalid");
  }

  const kind = url.protocol === "bunker:" ? "bunker" : url.protocol === "nostrconnect:" ? "nostrconnect" : undefined;
  if (kind === undefined) throw new Error("NIP-46 connection URI scheme must be bunker or nostrconnect");
  if (url.username !== "" || url.password !== "" || url.pathname !== "" || url.hash !== "") {
    throw new Error("NIP-46 connection URI must not include credentials, path, or fragment");
  }

  for (const key of url.searchParams.keys()) {
    if (!NIP46_CONNECTION_URI_PARAMS.has(key)) {
      throw new Error(`NIP-46 connection URI unsupported query parameter: ${key}`);
    }
  }

  const relays = url.searchParams.getAll("relay").map((relay) => requireRelayUrl(relay));
  if (relays.length === 0) throw new Error("NIP-46 connection URI requires at least one relay");
  if (new Set(relays).size !== relays.length) throw new Error("NIP-46 connection URI relays must be unique");

  const secret = requireSingleQueryParam(url.searchParams, "secret");
  const perms = requireSingleQueryParam(url.searchParams, "perms");
  const name = requireSingleQueryParam(url.searchParams, "name");
  const clientUrl = requireSingleQueryParam(url.searchParams, "url");
  const image = requireSingleQueryParam(url.searchParams, "image");
  if (secret === "") throw new Error("NIP-46 connection URI secret must be non-empty when present");

  if (kind === "bunker") {
    if (perms !== undefined || name !== undefined || clientUrl !== undefined || image !== undefined) {
      throw new Error("NIP-46 bunker URI must not include client metadata or requested permissions");
    }
    return {
      descriptor: {
        format: "nsealr-nip46-connection-uri-v0",
        kind,
        remote_signer_pubkey: requireXOnlyPubkey(url.hostname, "bunker remote-signer pubkey"),
        relays,
        secret_present: secret !== undefined && secret !== "",
        requested_permissions: [],
        starts_relay_session: false,
        creates_grants: false,
        stores_production_secrets: false,
        exposes_secret: false
      },
      ...(secret !== undefined && { secret })
    };
  }

  if (secret === undefined || secret === "") {
    throw new Error("NIP-46 nostrconnect URI requires a secret");
  }

  return {
    descriptor: {
      format: "nsealr-nip46-connection-uri-v0",
      kind,
      client_pubkey: requireXOnlyPubkey(url.hostname, "nostrconnect client pubkey"),
      relays,
      secret_present: true,
      requested_permissions: perms !== undefined ? parseNip46Permissions(perms) : [],
      ...((name !== undefined || clientUrl !== undefined || image !== undefined) && {
        client_metadata: {
          ...(name !== undefined && { name }),
          ...(clientUrl !== undefined && { url: requireOptionalHttpUrl(clientUrl, "url") }),
          ...(image !== undefined && { image: requireOptionalHttpUrl(image, "image") })
        }
      }),
      starts_relay_session: false,
      creates_grants: false,
      stores_production_secrets: false,
      exposes_secret: false
    },
    secret
  };
}

export function parseNip46ConnectionUri(value: string): Nip46ConnectionUriDescriptor {
  return parseNip46ConnectionUriWithSecret(value).descriptor;
}

export function parseNip46RelayEventEnvelope(
  value: unknown,
  direction: Nip46RelayEventDirection
): Nip46RelayEventEnvelope {
  const checkedDirection = requireNip46RelayDirection(direction);
  if (!isRecord(value)) throw new Error("NIP-46 relay event must be an object");
  if (value.kind !== 24133) throw new Error("NIP-46 relay event kind must be 24133");
  const senderPubkey = requireXOnlyPubkey(value.pubkey, "relay event pubkey");
  if (typeof value.content !== "string" || value.content.length === 0) {
    throw new Error("NIP-46 relay event content must be a non-empty encrypted string");
  }
  if (!Array.isArray(value.tags)) throw new Error("NIP-46 relay event tags must be an array");
  for (const tag of value.tags) {
    if (!Array.isArray(tag)) throw new Error("NIP-46 relay event tag must be an array");
    if (!tag.every((field) => typeof field === "string")) {
      throw new Error("NIP-46 relay event tag fields must be strings");
    }
  }
  const tags = value.tags as string[][];
  const pTags = tags.filter((tag) => tag[0] === "p");
  if (pTags.length !== 1) throw new Error("NIP-46 relay event must include exactly one p tag");
  const pTag = pTags[0];
  if (pTag.length !== 2) throw new Error("NIP-46 relay event p tag must contain only marker and pubkey");
  const recipientPubkey = requireXOnlyPubkey(pTag[1], "relay event p tag pubkey");
  const hasSignedEventFields = verifySignedRelayEvent(value, senderPubkey, tags);
  return {
    format: "nsealr-nip46-relay-event-envelope-v0",
    direction: checkedDirection,
    sender_pubkey: senderPubkey,
    recipient_pubkey: recipientPubkey,
    encrypted_content: value.content,
    has_signed_event_fields: hasSignedEventFields,
    event_id_verified: hasSignedEventFields,
    event_signature_verified: hasSignedEventFields,
    decrypts_content: false,
    opens_relay: false,
    creates_grants: false,
    stores_production_secrets: false
  };
}

export function evaluateNip46RelayRequestStep(value: unknown): Nip46RelayRequestStep {
  if (!isRecord(value)) throw new Error("NIP-46 relay request step must be an object");
  const direction = requireNip46RelayDirection(value.direction);
  if (direction !== "client_to_remote_signer") {
    throw new Error("NIP-46 relay request step direction must be client_to_remote_signer");
  }
  const envelope = parseNip46RelayEventEnvelope(value.event, direction);
  const message = requireMessage(value.decrypted_message);
  if (!Array.isArray(value.granted_permissions)) {
    throw new Error("NIP-46 relay request step granted_permissions must be a list");
  }
  const grantedPermissions = value.granted_permissions.map((permission) =>
    parseNip46PolicyPermission(permission, "NIP-46 relay request step granted_permissions")
  );
  return {
    format: "nsealr-nip46-relay-request-step-v0",
    envelope,
    message_id: message.id,
    bridge_decision: decideNip46BridgeAction(message, grantedPermissions),
    decrypts_content: false,
    opens_relay: false,
    creates_grants: false,
    acknowledges_connect: false,
    dispatches_signer: false,
    stores_production_secrets: false,
    persists_session_state: false
  };
}

function parseNip46RelayResponseStepParts(value: unknown): {
  envelope: Nip46RelayEventEnvelope;
  responseMessage: Nip46ResponseMessage;
} {
  if (!isRecord(value)) throw new Error("NIP-46 relay response step must be an object");
  const direction = requireNip46RelayDirection(value.direction);
  if (direction !== "remote_signer_to_client") {
    throw new Error("NIP-46 relay response step direction must be remote_signer_to_client");
  }
  return {
    envelope: parseNip46RelayEventEnvelope(value.event, direction),
    responseMessage: requireResponseMessage(value.decrypted_message)
  };
}

function relayResponseResultType(message: Nip46ResponseMessage): {
  resultType: Nip46RelayResponseResultType;
  signedEventShapeChecked: boolean;
  signedEventIdVerified?: boolean;
  signedEventSignatureVerified?: boolean;
  resultPubkey?: string;
  authUrl?: string;
  relayUrls?: string[] | null;
} {
  if (message.result === "auth_url" && message.error !== undefined) {
    return { resultType: "auth_challenge", signedEventShapeChecked: false, authUrl: message.error };
  }
  if (message.error !== undefined) {
    return { resultType: "error", signedEventShapeChecked: false };
  }
  const result = message.result;
  if (result === undefined) throw new Error("NIP-46 response message result is missing");
  if (X_ONLY_PUBKEY.test(result)) {
    return { resultType: "public_key_result", signedEventShapeChecked: false, resultPubkey: result };
  }
  if (result === "ack") {
    return { resultType: "connect_ack_result", signedEventShapeChecked: false };
  }
  if (result === "pong") {
    return { resultType: "pong_result", signedEventShapeChecked: false };
  }
  let event: unknown;
  try {
    event = parseStrictJson(result, NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes);
  } catch (error) {
    throw new Error("NIP-46 response message result is not a supported response shape");
  }
  if (event === null) {
    return { resultType: "relay_no_change_result", signedEventShapeChecked: false, relayUrls: null };
  }
  if (Array.isArray(event)) {
    if (event.length === 0) throw new Error("NIP-46 switch_relays response relays must be a non-empty list or null");
    const relayUrls = event.map((relay) => {
      if (typeof relay !== "string") throw new Error("NIP-46 switch_relays response relays must be strings");
      return requireRelayUrl(relay, "NIP-46 switch_relays response relay");
    });
    if (new Set(relayUrls).size !== relayUrls.length) {
      throw new Error("NIP-46 switch_relays response relays must be unique");
    }
    return { resultType: "relay_list_result", signedEventShapeChecked: false, relayUrls };
  }
  const shape = validateResponse({
    version: 1,
    request_id: message.id,
    ok: true,
    result: { event }
  });
  if (!shape.ok) {
    throw new Error(shape.error ?? "NIP-46 signed-event response shape is invalid");
  }
  if (!isRecord(event) || typeof event.pubkey !== "string" || !X_ONLY_PUBKEY.test(event.pubkey)) {
    throw new Error("NIP-46 signed-event response pubkey is invalid");
  }
  const computedId = computeEventId({
    pubkey: event.pubkey,
    created_at: event.created_at as number,
    kind: event.kind as number,
    tags: event.tags as string[][],
    content: event.content as string
  });
  if (event.id !== computedId) {
    throw new Error("NIP-46 signed-event response id does not match NIP-01 canonical serialization");
  }
  if (!verifySchnorrSignature(event.pubkey, computedId, event.sig as string)) {
    throw new Error("NIP-46 signed-event response signature is invalid");
  }
  return {
    resultType: "signed_event_result",
    signedEventShapeChecked: true,
    signedEventIdVerified: true,
    signedEventSignatureVerified: true,
    resultPubkey: event.pubkey
  };
}

export function evaluateNip46RelayResponseStep(value: unknown): Nip46RelayResponseStep {
  const { envelope, responseMessage } = parseNip46RelayResponseStepParts(value);
  const {
    resultType,
    signedEventShapeChecked,
    signedEventIdVerified = false,
    signedEventSignatureVerified = false,
    resultPubkey,
    authUrl,
    relayUrls
  } = relayResponseResultType(responseMessage);
  const expectedUser = isRecord(value) && value.expected_user_pubkey !== undefined
    ? requireXOnlyPubkey(value.expected_user_pubkey, "expected user pubkey") : undefined;
  const resultPubkeyBoundToExpectedUser = resultPubkey !== undefined && expectedUser !== undefined && resultPubkey === expectedUser;
  if (resultPubkey !== undefined && expectedUser !== undefined && !resultPubkeyBoundToExpectedUser) {
    throw new Error("NIP-46 result pubkey does not match expected user pubkey");
  }
  return {
    format: "nsealr-nip46-relay-response-step-v1",
    envelope,
    message_id: responseMessage.id,
    response_message: responseMessage,
    result_type: resultType,
    ...(authUrl !== undefined && { auth_url: authUrl }),
    ...(relayUrls !== undefined && { relay_urls: relayUrls }),
    signed_event_shape_checked: signedEventShapeChecked,
    signed_event_id_verified: signedEventIdVerified,
    signed_event_signature_verified: signedEventSignatureVerified,
    ...(resultPubkey !== undefined && { result_pubkey: resultPubkey }),
    result_pubkey_bound_to_expected_user: resultPubkeyBoundToExpectedUser,
    decrypts_content: false,
    opens_relay: false,
    creates_grants: false,
    acknowledges_connect: false,
    dispatches_signer: false,
    relay_event_signature_verified: envelope.event_signature_verified,
    stores_production_secrets: false,
    persists_session_state: false
  };
}

export function verifyNip46ConnectionTokenResponse(value: unknown): Nip46ConnectionTokenResponse {
  if (!isRecord(value)) throw new Error("NIP-46 connection token response input must be an object");
  if (typeof value.connectionUri !== "string") {
    throw new Error("NIP-46 connection token response connectionUri must be a string");
  }
  const { descriptor, secret } = parseNip46ConnectionUriWithSecret(value.connectionUri);
  if (descriptor.kind !== "nostrconnect" || descriptor.client_pubkey === undefined || secret === undefined || secret === "") {
    throw new Error("NIP-46 connection token response requires a nostrconnect URI with secret");
  }
  const { envelope, responseMessage } = parseNip46RelayResponseStepParts(value.responseStep);
  if (envelope.recipient_pubkey !== descriptor.client_pubkey) {
    throw new Error("NIP-46 connection token response recipient does not match client pubkey");
  }
  if (responseMessage.error !== undefined) {
    throw new Error("NIP-46 connection token response must not contain an error");
  }
  if (responseMessage.result !== secret) {
    throw new Error("NIP-46 connection token response secret mismatch");
  }
  return {
    format: "nsealr-nip46-connection-token-response-v0",
    kind: "nostrconnect",
    client_pubkey: descriptor.client_pubkey,
    remote_signer_pubkey: envelope.sender_pubkey,
    relays: descriptor.relays,
    requested_permissions: descriptor.requested_permissions,
    ...(descriptor.client_metadata !== undefined && { client_metadata: descriptor.client_metadata }),
    response_message_id: responseMessage.id,
    client_pubkey_bound_to_recipient: true,
    secret_matched: true,
    starts_relay_session: false,
    derives_nip44_key: false,
    acknowledges_connect: false,
    opens_relay: false,
    creates_grants: false,
    dispatches_signer: false,
    stores_production_secrets: false,
    persists_session_state: false,
    exposes_secret: false,
    contains_secret_material: false
  };
}

export function parseNip46ConnectIntent(value: unknown): Nip46ConnectIntent {
  const message = requireMessage(value);
  if (message.method !== "connect") throw new Error("NIP-46 connect intent requires connect method");
  if (message.params.length < 1 || message.params.length > 3) {
    throw new Error("NIP-46 connect requires remote-signer pubkey plus optional secret and permissions");
  }
  return {
    id: message.id,
    remote_signer_pubkey: requireXOnlyPubkey(message.params[0], "connect remote-signer pubkey"),
    ...(message.params[1] !== undefined && message.params[1] !== "" ? { secret: message.params[1] } : {}),
    requested_permissions: message.params[2] !== undefined ? parseNip46Permissions(message.params[2]) : []
  };
}

export function nip46PermissionLabel(permission: Nip46PermissionRequirement): string {
  if (permission.method === "sign_event" && permission.parameter !== undefined) {
    return `sign_event:${permission.parameter}`;
  }
  return permission.method;
}

type Nip46ConnectReviewWithoutDigest = Omit<Nip46ConnectReview, "connect_digest">;

function connectDigestForReview(review: Nip46ConnectReviewWithoutDigest): string {
  return sha256Utf8Hex(canonicalJson({
    format: CONNECT_REVIEW_DIGEST_FORMAT,
    review
  }));
}

function parseNip46ReviewPage(value: unknown, context: string): Nip46ConnectReview["pages"][number] {
  if (!isRecord(value)) throw new Error(`${context} must be an object`);
  assertOnlyKeys(value, ["title", "page_indicator", "body_lines"], context);
  if (typeof value.title !== "string" || value.title.length === 0) throw new Error(`${context} title is invalid`);
  if (typeof value.page_indicator !== "string" || value.page_indicator.length === 0) {
    throw new Error(`${context} page_indicator is invalid`);
  }
  if (!Array.isArray(value.body_lines) || !value.body_lines.every((line) => typeof line === "string")) {
    throw new Error(`${context} body_lines must be strings`);
  }
  return {
    title: value.title,
    page_indicator: value.page_indicator,
    body_lines: value.body_lines
  };
}

function requireSafeNonNegativeInteger(value: unknown, label: string): number {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < 0
  ) {
    throw new Error(`${label} must be a safe non-negative integer`);
  }
  return value;
}

type Nip46AuthChallengeReviewWithoutDigest = Omit<Nip46AuthChallengeReview, "auth_challenge_digest">;

function authChallengeDigestForReview(review: Nip46AuthChallengeReviewWithoutDigest): string {
  return sha256Utf8Hex(canonicalJson({
    format: AUTH_CHALLENGE_REVIEW_DIGEST_FORMAT,
    review
  }));
}

function authChallengeReviewForParts(input: {
  id: string;
  remoteSignerPubkey: string;
  clientPubkey: string;
  authUrl: string;
}): Nip46AuthChallengeReview {
  const reviewWithoutDigest: Nip46AuthChallengeReviewWithoutDigest = {
    format: "nsealr-nip46-auth-challenge-review-v0",
    id: input.id,
    remote_signer_pubkey: input.remoteSignerPubkey,
    client_pubkey: input.clientPubkey,
    auth_url: input.authUrl,
    pages: [
      {
        title: "Auth Challenge",
        page_indicator: "Page 1/2",
        body_lines: ["Remote signer", input.remoteSignerPubkey, "Client", input.clientPubkey]
      },
      {
        title: "Auth URL",
        page_indicator: "Page 2/2",
        body_lines: [input.authUrl, "No automatic opening"]
      }
    ],
    opens_url: false,
    opens_relay: false,
    acknowledges_connect: false,
    creates_grants: false,
    dispatches_signer: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false,
    contains_secret_material: false
  };
  return {
    ...reviewWithoutDigest,
    auth_challenge_digest: authChallengeDigestForReview(reviewWithoutDigest)
  };
}

export function reviewNip46AuthChallengeStep(value: unknown): Nip46AuthChallengeReview {
  const step = evaluateNip46RelayResponseStep(value);
  if (step.result_type !== "auth_challenge" || step.auth_url === undefined) {
    throw new Error("NIP-46 auth challenge review requires an auth_challenge response step");
  }
  return authChallengeReviewForParts({
    id: step.message_id,
    remoteSignerPubkey: step.envelope.sender_pubkey,
    clientPubkey: step.envelope.recipient_pubkey,
    authUrl: step.auth_url
  });
}

function requireFalseAuthChallengeFlag(
  value: Record<string, unknown>,
  field: typeof NIP46_AUTH_CHALLENGE_FALSE_FIELDS[number],
  context: "review" | "approval"
): void {
  if (value[field] !== false) throw new Error(`NIP-46 auth challenge ${context} ${field} must be false`);
}

export function parseNip46AuthChallengeReview(value: unknown): Nip46AuthChallengeReview {
  if (!isRecord(value)) throw new Error("NIP-46 auth challenge review must be an object");
  assertOnlyKeys(
    value,
    [
      "format",
      "id",
      "remote_signer_pubkey",
      "client_pubkey",
      "auth_url",
      "pages",
      "opens_url",
      "opens_relay",
      "acknowledges_connect",
      "creates_grants",
      "dispatches_signer",
      "persists_session_state",
      "stores_production_secrets",
      "exposes_secret",
      "contains_secret_material",
      "auth_challenge_digest"
    ],
    "NIP-46 auth challenge review"
  );
  if (value.format !== "nsealr-nip46-auth-challenge-review-v0") {
    throw new Error("NIP-46 auth challenge review format is invalid");
  }
  const id = requireNip46Id(value.id);
  const remoteSignerPubkey = requireXOnlyPubkey(value.remote_signer_pubkey, "auth challenge remote-signer pubkey");
  const clientPubkey = requireXOnlyPubkey(value.client_pubkey, "auth challenge client pubkey");
  if (typeof value.auth_url !== "string") throw new Error("NIP-46 auth challenge review auth_url must be a string");
  const authUrl = requireNip46AuthUrl(value.auth_url);
  if (!Array.isArray(value.pages) || value.pages.length === 0) {
    throw new Error("NIP-46 auth challenge review pages must be a non-empty list");
  }
  const pages = value.pages.map((page, index) =>
    parseNip46ReviewPage(page, `NIP-46 auth challenge review pages[${index}]`)
  );
  for (const field of NIP46_AUTH_CHALLENGE_FALSE_FIELDS) {
    requireFalseAuthChallengeFlag(value, field, "review");
  }
  const authChallengeDigest = requireLowerHex64(
    value.auth_challenge_digest,
    "NIP-46 auth challenge review auth_challenge_digest"
  );
  const reviewWithoutDigest: Nip46AuthChallengeReviewWithoutDigest = {
    format: "nsealr-nip46-auth-challenge-review-v0",
    id,
    remote_signer_pubkey: remoteSignerPubkey,
    client_pubkey: clientPubkey,
    auth_url: authUrl,
    pages,
    opens_url: false,
    opens_relay: false,
    acknowledges_connect: false,
    creates_grants: false,
    dispatches_signer: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false,
    contains_secret_material: false
  };
  if (authChallengeDigest !== authChallengeDigestForReview(reviewWithoutDigest)) {
    throw new Error("NIP-46 auth challenge review digest mismatch");
  }
  const canonicalReview = authChallengeReviewForParts({
    id,
    remoteSignerPubkey,
    clientPubkey,
    authUrl
  });
  if (canonicalJson(canonicalReview) !== canonicalJson({ ...reviewWithoutDigest, auth_challenge_digest: authChallengeDigest })) {
    throw new Error("NIP-46 auth challenge review is not canonical");
  }
  return {
    ...reviewWithoutDigest,
    auth_challenge_digest: authChallengeDigest
  };
}

export function approveNip46AuthChallengeReview(
  value: unknown,
  options: Nip46AuthChallengeApprovalOptions
): Nip46AuthChallengeApproval {
  const review = parseNip46AuthChallengeReview(value);
  const reviewedAuthChallengeDigest = requireLowerHex64(
    options.reviewedAuthChallengeDigest,
    "reviewed NIP-46 auth challenge digest"
  );
  if (reviewedAuthChallengeDigest !== review.auth_challenge_digest) {
    throw new Error("reviewed auth challenge digest does not match NIP-46 auth challenge review");
  }
  return {
    format: "nsealr-nip46-auth-challenge-approval-v0",
    id: review.id,
    auth_challenge_digest: review.auth_challenge_digest,
    approved_at: requireSafeNonNegativeInteger(options.approvedAt, "NIP-46 auth challenge approval approved_at"),
    opens_url: false,
    opens_relay: false,
    acknowledges_connect: false,
    creates_grants: false,
    dispatches_signer: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false,
    contains_secret_material: false
  };
}

export function parseNip46AuthChallengeApproval(value: unknown): Nip46AuthChallengeApproval {
  if (!isRecord(value)) throw new Error("NIP-46 auth challenge approval must be an object");
  assertOnlyKeys(
    value,
    [
      "format",
      "id",
      "auth_challenge_digest",
      "approved_at",
      "opens_url",
      "opens_relay",
      "acknowledges_connect",
      "creates_grants",
      "dispatches_signer",
      "persists_session_state",
      "stores_production_secrets",
      "exposes_secret",
      "contains_secret_material"
    ],
    "NIP-46 auth challenge approval"
  );
  if (value.format !== "nsealr-nip46-auth-challenge-approval-v0") {
    throw new Error("NIP-46 auth challenge approval format is invalid");
  }
  const id = requireNip46Id(value.id);
  const authChallengeDigest = requireLowerHex64(
    value.auth_challenge_digest,
    "NIP-46 auth challenge approval auth_challenge_digest"
  );
  const approvedAt = requireSafeNonNegativeInteger(value.approved_at, "NIP-46 auth challenge approval approved_at");
  for (const field of NIP46_AUTH_CHALLENGE_FALSE_FIELDS) {
    requireFalseAuthChallengeFlag(value, field, "approval");
  }
  return {
    format: "nsealr-nip46-auth-challenge-approval-v0",
    id,
    auth_challenge_digest: authChallengeDigest,
    approved_at: approvedAt,
    opens_url: false,
    opens_relay: false,
    acknowledges_connect: false,
    creates_grants: false,
    dispatches_signer: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false,
    contains_secret_material: false
  };
}

export function reviewNip46ConnectIntent(intent: Nip46ConnectIntent): Nip46ConnectReview {
  const permissionLines = intent.requested_permissions.map((permission) => nip46PermissionLabel(permission));
  const reviewWithoutDigest: Nip46ConnectReviewWithoutDigest = {
    format: "nsealr-nip46-connect-review-v0",
    id: intent.id,
    remote_signer_pubkey: intent.remote_signer_pubkey,
    secret_present: intent.secret !== undefined,
    requested_permissions: intent.requested_permissions,
    pages: [
      {
        title: "Connect",
        page_indicator: "Page 1/2",
        body_lines: [
          "Remote signer",
          intent.remote_signer_pubkey,
          `Secret: ${intent.secret !== undefined ? "provided" : "none"}`
        ]
      },
      {
        title: "Permissions",
        page_indicator: "Page 2/2",
        body_lines: permissionLines.length > 0 ? permissionLines : ["No permissions requested"]
      }
    ]
  };
  return {
    ...reviewWithoutDigest,
    connect_digest: connectDigestForReview(reviewWithoutDigest)
  };
}

export function reviewNip46ConnectMessage(value: unknown): Nip46ConnectReview {
  return reviewNip46ConnectIntent(parseNip46ConnectIntent(value));
}

export function parseNip46ConnectReview(value: unknown): Nip46ConnectReview {
  if (!isRecord(value)) throw new Error("NIP-46 connect review must be an object");
  assertOnlyKeys(
    value,
    [
      "format",
      "id",
      "remote_signer_pubkey",
      "secret_present",
      "requested_permissions",
      "pages",
      "connect_digest"
    ],
    "NIP-46 connect review"
  );
  if (value.format !== "nsealr-nip46-connect-review-v0") {
    throw new Error("NIP-46 connect review format is invalid");
  }
  const id = requireNip46Id(value.id);
  const remoteSignerPubkey = requireXOnlyPubkey(value.remote_signer_pubkey, "connect review remote-signer pubkey");
  if (typeof value.secret_present !== "boolean") throw new Error("NIP-46 connect review secret_present must be boolean");
  if (!Array.isArray(value.requested_permissions)) {
    throw new Error("NIP-46 connect review requested_permissions must be a list");
  }
  const requestedPermissions = value.requested_permissions.map((permission, index) =>
    parseNip46RequestedPermission(permission, `NIP-46 connect review requested_permissions[${index}]`)
  );
  if (!Array.isArray(value.pages) || value.pages.length === 0) {
    throw new Error("NIP-46 connect review pages must be a non-empty list");
  }
  const pages = value.pages.map((page, index) => parseNip46ReviewPage(page, `NIP-46 connect review pages[${index}]`));
  const connectDigest = requireLowerHex64(value.connect_digest, "NIP-46 connect review connect_digest");
  const reviewWithoutDigest: Nip46ConnectReviewWithoutDigest = {
    format: "nsealr-nip46-connect-review-v0",
    id,
    remote_signer_pubkey: remoteSignerPubkey,
    secret_present: value.secret_present,
    requested_permissions: requestedPermissions,
    pages
  };
  if (connectDigest !== connectDigestForReview(reviewWithoutDigest)) {
    throw new Error("NIP-46 connect review digest mismatch");
  }
  const canonicalReview = reviewNip46ConnectIntent({
    id,
    remote_signer_pubkey: remoteSignerPubkey,
    ...(value.secret_present ? { secret: "redacted" } : {}),
    requested_permissions: requestedPermissions
  });
  if (canonicalJson(canonicalReview) !== canonicalJson({ ...reviewWithoutDigest, connect_digest: connectDigest })) {
    throw new Error("NIP-46 connect review is not canonical");
  }
  return {
    ...reviewWithoutDigest,
    connect_digest: connectDigest
  };
}

export function approveNip46ConnectReview(
  value: unknown,
  options: Nip46ConnectApprovalOptions
): Nip46ConnectApproval {
  const review = parseNip46ConnectReview(value);
  const reviewedConnectDigest = requireLowerHex64(
    options.reviewedConnectDigest,
    "reviewed NIP-46 connect digest"
  );
  if (reviewedConnectDigest !== review.connect_digest) {
    throw new Error("reviewed connect digest does not match NIP-46 connect review");
  }
  return {
    format: "nsealr-nip46-connect-approval-v0",
    id: review.id,
    connect_digest: review.connect_digest,
    approved_at: requireSafeNonNegativeInteger(options.approvedAt, "NIP-46 connect approval approved_at"),
    acknowledges_connect: false,
    creates_grants: false,
    opens_relay: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false
  };
}

function requireFalseConnectApprovalFlag(value: Record<string, unknown>, field: keyof Pick<
  Nip46ConnectApproval,
  "acknowledges_connect" | "creates_grants" | "opens_relay" | "persists_session_state" | "stores_production_secrets" | "exposes_secret"
>): void {
  if (value[field] !== false) throw new Error(`NIP-46 connect approval ${field} must be false`);
}

export function parseNip46ConnectApproval(value: unknown): Nip46ConnectApproval {
  if (!isRecord(value)) throw new Error("NIP-46 connect approval must be an object");
  assertOnlyKeys(
    value,
    [
      "format",
      "id",
      "connect_digest",
      "approved_at",
      "acknowledges_connect",
      "creates_grants",
      "opens_relay",
      "persists_session_state",
      "stores_production_secrets",
      "exposes_secret"
    ],
    "NIP-46 connect approval"
  );
  if (value.format !== "nsealr-nip46-connect-approval-v0") {
    throw new Error("NIP-46 connect approval format is invalid");
  }
  const id = requireNip46Id(value.id);
  const connectDigest = requireLowerHex64(value.connect_digest, "NIP-46 connect approval connect_digest");
  const approvedAt = requireSafeNonNegativeInteger(value.approved_at, "NIP-46 connect approval approved_at");
  for (const field of [
    "acknowledges_connect",
    "creates_grants",
    "opens_relay",
    "persists_session_state",
    "stores_production_secrets",
    "exposes_secret"
  ] as const) {
    requireFalseConnectApprovalFlag(value, field);
  }
  return {
    format: "nsealr-nip46-connect-approval-v0",
    id,
    connect_digest: connectDigest,
    approved_at: approvedAt,
    acknowledges_connect: false,
    creates_grants: false,
    opens_relay: false,
    persists_session_state: false,
    stores_production_secrets: false,
    exposes_secret: false
  };
}

function sessionSecretPaths(value: unknown, prefix = ""): string[] {
  const paths: string[] = [];
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      paths.push(...sessionSecretPaths(item, prefix === "" ? `[${index}]` : `${prefix}[${index}]`));
    }
    return paths;
  }
  if (!isRecord(value)) return paths;
  for (const [key, item] of Object.entries(value)) {
    const path = prefix === "" ? key : `${prefix}.${key}`;
    if (NIP46_SESSION_SECRET_FIELDS.has(key.toLowerCase())) paths.push(path);
    paths.push(...sessionSecretPaths(item, path));
  }
  return paths;
}

function assertNoSessionSecretMaterial(value: unknown): void {
  const secretPaths = sessionSecretPaths(value);
  if (secretPaths.length > 0) {
    throw new Error(`NIP-46 session must not contain secret material at ${secretPaths[0]}`);
  }
}

function requireNip46SessionName(value: unknown): string {
  if (typeof value !== "string" || !/^[a-z0-9][a-z0-9._:-]{0,127}$/u.test(value)) {
    throw new Error("NIP-46 session name is invalid");
  }
  return value;
}

function requireNip46SessionPhase(value: unknown): "approved_pending_ack" {
  if (typeof value !== "string" || !NIP46_SESSION_PHASES.has(value)) {
    throw new Error("NIP-46 session phase must be approved_pending_ack");
  }
  return value as "approved_pending_ack";
}

function requireRelayList(value: unknown): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("NIP-46 session relays must be a non-empty list");
  }
  const relays = value.map((relay) => {
    if (typeof relay !== "string") throw new Error("NIP-46 session relays must be strings");
    return requireRelayUrl(relay);
  });
  if (new Set(relays).size !== relays.length) throw new Error("NIP-46 session relays must be unique");
  return relays;
}

function parseSessionPermissions(
  value: unknown,
  label: "requested_permissions" | "approved_permissions"
): Nip46Permission[] {
  if (!Array.isArray(value)) throw new Error(`NIP-46 session ${label} must be a list`);
  return value.map((permission, index) =>
    label === "approved_permissions"
      ? parseNip46PolicyPermission(permission, `NIP-46 session ${label}[${index}]`)
      : parseNip46RequestedPermission(permission, `NIP-46 session ${label}[${index}]`)
  );
}

function requireFalseSessionFlag(value: Record<string, unknown>, field: typeof NIP46_SESSION_FALSE_FIELDS[number]): void {
  if (value[field] !== false) throw new Error(`${field} must be false`);
}

function assertApprovedPermissionsSubset(
  approvedPermissions: readonly Nip46Permission[],
  requestedPermissions: readonly Nip46Permission[]
): void {
  for (const approvedPermission of approvedPermissions) {
    if (!requestedPermissions.some((requestedPermission) => permissionMatchesRequirement(requestedPermission, approvedPermission))) {
      throw new Error("approved_permissions must be a subset of requested_permissions");
    }
  }
}

function requireSessionScope(value: unknown): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error("NIP-46 session scope must be a non-empty string");
  }
  for (const required of ["NIP-44", "relay", "acknowledge", "grant", "signer", "persist", "secret material"]) {
    if (!value.includes(required)) throw new Error(`NIP-46 session scope must mention ${required}`);
  }
  return value;
}

const NIP46_SESSION_SCOPE =
  "NIP-46 session lifecycle checkpoint only. It records a reviewed connect digest and approved permission subset, but does not acknowledge connect, derive NIP-44 keys, open relays, create grants, dispatch a signer, store production secrets, persist session state, or include secret material.";

export function createNip46SessionLifecycleCheckpoint(
  reviewValue: unknown,
  approvalValue: unknown,
  options: Nip46SessionLifecycleCheckpointOptions
): Nip46SessionLifecycle {
  const review = parseNip46ConnectReview(reviewValue);
  const approval = parseNip46ConnectApproval(approvalValue);
  if (approval.id !== review.id) throw new Error("NIP-46 session approval id must match connect review");
  if (approval.connect_digest !== review.connect_digest) {
    throw new Error("NIP-46 session approval digest must match connect review");
  }
  const name = requireNip46SessionName(options.name);
  const clientPubkey = requireXOnlyPubkey(options.clientPubkey, "session client pubkey");
  const relays = requireRelayList(options.relays);
  const expiresAt = requireSafeNonNegativeInteger(options.expiresAt, "NIP-46 session expires_at");
  if (expiresAt <= approval.approved_at) throw new Error("expires_at must be greater than approved_at");
  const approvedPermissions = parseSessionPermissions(options.approvedPermissions, "approved_permissions");
  assertApprovedPermissionsSubset(approvedPermissions, review.requested_permissions);
  return {
    name,
    format: "nsealr-nip46-session-lifecycle-v0",
    phase: "approved_pending_ack",
    client_pubkey: clientPubkey,
    remote_signer_pubkey: review.remote_signer_pubkey,
    relays,
    connect_digest: review.connect_digest,
    approved_at: approval.approved_at,
    expires_at: expiresAt,
    requested_permissions: review.requested_permissions,
    approved_permissions: approvedPermissions,
    secret_present: review.secret_present,
    secret_value_stored: false,
    contains_secret_material: false,
    derives_nip44_key: false,
    acknowledges_connect: false,
    opens_relay: false,
    creates_grants: false,
    dispatches_signer: false,
    stores_production_secrets: false,
    persists_session_state: false,
    scope: NIP46_SESSION_SCOPE
  };
}

export function parseNip46SessionLifecycle(value: unknown): Nip46SessionLifecycle {
  if (!isRecord(value)) throw new Error("NIP-46 session must be an object");
  assertNoSessionSecretMaterial(value);
  assertOnlyKeys(
    value,
    [
      "name",
      "format",
      "phase",
      "client_pubkey",
      "remote_signer_pubkey",
      "relays",
      "connect_digest",
      "approved_at",
      "expires_at",
      "requested_permissions",
      "approved_permissions",
      "secret_present",
      "secret_value_stored",
      "contains_secret_material",
      "derives_nip44_key",
      "acknowledges_connect",
      "opens_relay",
      "creates_grants",
      "dispatches_signer",
      "stores_production_secrets",
      "persists_session_state",
      "scope"
    ],
    "NIP-46 session"
  );
  if (value.format !== "nsealr-nip46-session-lifecycle-v0") {
    throw new Error("NIP-46 session format is invalid");
  }
  const name = requireNip46SessionName(value.name);
  const phase = requireNip46SessionPhase(value.phase);
  const clientPubkey = requireXOnlyPubkey(value.client_pubkey, "session client pubkey");
  const remoteSignerPubkey = requireXOnlyPubkey(value.remote_signer_pubkey, "session remote-signer pubkey");
  const relays = requireRelayList(value.relays);
  const connectDigest = requireLowerHex64(value.connect_digest, "NIP-46 session connect_digest");
  const approvedAt = requireSafeNonNegativeInteger(value.approved_at, "NIP-46 session approved_at");
  const expiresAt = requireSafeNonNegativeInteger(value.expires_at, "NIP-46 session expires_at");
  if (expiresAt <= approvedAt) throw new Error("expires_at must be greater than approved_at");
  const requestedPermissions = parseSessionPermissions(value.requested_permissions, "requested_permissions");
  const approvedPermissions = parseSessionPermissions(value.approved_permissions, "approved_permissions");
  assertApprovedPermissionsSubset(approvedPermissions, requestedPermissions);
  if (typeof value.secret_present !== "boolean") throw new Error("NIP-46 session secret_present must be boolean");
  for (const field of NIP46_SESSION_FALSE_FIELDS) requireFalseSessionFlag(value, field);
  const scope = requireSessionScope(value.scope);
  return {
    name,
    format: "nsealr-nip46-session-lifecycle-v0",
    phase,
    client_pubkey: clientPubkey,
    remote_signer_pubkey: remoteSignerPubkey,
    relays,
    connect_digest: connectDigest,
    approved_at: approvedAt,
    expires_at: expiresAt,
    requested_permissions: requestedPermissions,
    approved_permissions: approvedPermissions,
    secret_present: value.secret_present,
    secret_value_stored: false,
    contains_secret_material: false,
    derives_nip44_key: false,
    acknowledges_connect: false,
    opens_relay: false,
    creates_grants: false,
    dispatches_signer: false,
    stores_production_secrets: false,
    persists_session_state: false,
    scope
  };
}

export type Nip46SessionActivePhase = "connect_ack" | "session_active" | "session_closed";

export type Nip46SessionActive = {
  name: string;
  format: "nsealr-nip46-session-active-v0";
  phase: Nip46SessionActivePhase;
  client_pubkey: string;
  remote_signer_pubkey: string;
  relays: string[];
  connect_digest: string;
  approved_permissions: Nip46Permission[];
  nip44: { event_kind: 24133; payload_encrypted: true; version: 2 };
  acknowledges_connect: boolean;
  derives_nip44_key: boolean;
  opens_relay: boolean;
  dispatches_signer: boolean;
  creates_grants: boolean;
  persists_session_state: true;
  persisted_state: { fields: string[]; contains_secret_material: false };
  secret_present: boolean;
  secret_value_stored: false;
  contains_secret_material: false;
  stores_production_secrets: false;
  scope: string;
};

function requireNip46SessionActivePhase(value: unknown): Nip46SessionActivePhase {
  if (typeof value !== "string" || !NIP46_SESSION_ACTIVE_PHASES.has(value)) {
    throw new Error("phase must be one of connect_ack, session_active, session_closed");
  }
  return value as Nip46SessionActivePhase;
}

export function parseNip46SessionActive(value: unknown): Nip46SessionActive {
  if (!isRecord(value)) throw new Error("NIP-46 active session must be an object");
  assertNoSessionSecretMaterial(value);
  assertOnlyKeys(
    value,
    [
      "name",
      "format",
      "phase",
      "client_pubkey",
      "remote_signer_pubkey",
      "relays",
      "connect_digest",
      "approved_permissions",
      "nip44",
      "acknowledges_connect",
      "derives_nip44_key",
      "opens_relay",
      "dispatches_signer",
      "creates_grants",
      "persists_session_state",
      "persisted_state",
      "secret_present",
      "secret_value_stored",
      "contains_secret_material",
      "stores_production_secrets",
      "scope"
    ],
    "NIP-46 active session"
  );
  if (value.format !== "nsealr-nip46-session-active-v0") {
    throw new Error("NIP-46 active session format is invalid");
  }
  const name = requireNip46SessionName(value.name);
  const phase = requireNip46SessionActivePhase(value.phase);
  const clientPubkey = requireXOnlyPubkey(value.client_pubkey, "active session client pubkey");
  const remoteSignerPubkey = requireXOnlyPubkey(value.remote_signer_pubkey, "active session remote-signer pubkey");
  const relays = requireRelayList(value.relays);
  const connectDigest = requireLowerHex64(value.connect_digest, "NIP-46 active session connect_digest");
  const approvedPermissions = parseSessionPermissions(value.approved_permissions, "approved_permissions");
  if (approvedPermissions.length === 0) throw new Error("approved_permissions must be non-empty");

  const nip44 = value.nip44;
  if (!isRecord(nip44)) throw new Error("nip44 must be an object");
  assertOnlyKeys(nip44, ["event_kind", "payload_encrypted", "version"], "nip44");
  if (nip44.event_kind !== 24133) throw new Error("nip44.event_kind must be 24133");
  if (nip44.payload_encrypted !== true) throw new Error("nip44.payload_encrypted must be true");
  if (nip44.version !== 2) throw new Error("nip44.version must be 2");

  if (value.persists_session_state !== true) throw new Error("persists_session_state must be true");
  const persistedState = value.persisted_state;
  if (!isRecord(persistedState)) throw new Error("persisted_state must be an object");
  assertOnlyKeys(persistedState, ["fields", "contains_secret_material"], "persisted_state");
  const fields = persistedState.fields;
  if (!Array.isArray(fields) || fields.length === 0 || !fields.every((field) => typeof field === "string" && field.length > 0)) {
    throw new Error("persisted_state.fields must be a non-empty string list");
  }
  for (const field of fields) {
    if (NIP46_SESSION_SECRET_FIELDS.has(field.toLowerCase())) {
      throw new Error(`persisted_state.fields must not include secret field ${field}`);
    }
  }
  if (persistedState.contains_secret_material !== false) {
    throw new Error("persisted_state.contains_secret_material must be false");
  }

  if (typeof value.secret_present !== "boolean") throw new Error("secret_present must be boolean");
  for (const flag of NIP46_SESSION_ACTIVE_ALWAYS_FALSE) requireFalseSessionFlag(value, flag);
  const expectedFlags = NIP46_SESSION_ACTIVE_PHASE_FLAGS[phase];
  for (const [flag, expected] of Object.entries(expectedFlags)) {
    if (value[flag] !== expected) throw new Error(`${flag} must be ${expected} in phase ${phase}`);
  }
  if (typeof value.creates_grants !== "boolean") throw new Error("creates_grants must be boolean");
  if (typeof value.scope !== "string" || value.scope.length === 0) {
    throw new Error("active session scope must be a non-empty string");
  }
  const scope = value.scope;
  for (const required of ["NIP-44", "relay", "persist", "secret material"]) {
    if (!scope.includes(required)) throw new Error(`active session scope must mention ${required}`);
  }

  return {
    name,
    format: "nsealr-nip46-session-active-v0",
    phase,
    client_pubkey: clientPubkey,
    remote_signer_pubkey: remoteSignerPubkey,
    relays,
    connect_digest: connectDigest,
    approved_permissions: approvedPermissions,
    nip44: { event_kind: 24133, payload_encrypted: true, version: 2 },
    acknowledges_connect: expectedFlags.acknowledges_connect,
    derives_nip44_key: expectedFlags.derives_nip44_key,
    opens_relay: expectedFlags.opens_relay,
    dispatches_signer: expectedFlags.dispatches_signer,
    creates_grants: value.creates_grants,
    persists_session_state: true,
    persisted_state: { fields: fields as string[], contains_secret_material: false },
    secret_present: value.secret_present,
    secret_value_stored: false,
    contains_secret_material: false,
    stores_production_secrets: false,
    scope
  };
}

export function evaluateNip46SessionRequestGate(value: unknown): Nip46SessionRequestGate {
  if (!isRecord(value)) throw new Error("NIP-46 session request gate must be an object");
  assertOnlyKeys(
    value,
    ["format", "session", "evaluated_at", "direction", "event", "decrypted_message"],
    "NIP-46 session request gate"
  );
  if (value.format !== "nsealr-nip46-session-request-gate-v0") {
    throw new Error("NIP-46 session request gate format is invalid");
  }
  const session = parseNip46SessionLifecycle(value.session);
  const evaluatedAt = requireSafeNonNegativeInteger(value.evaluated_at, "NIP-46 session request gate evaluated_at");
  if (evaluatedAt < session.approved_at) {
    throw new Error("NIP-46 session request gate evaluated_at must be greater than or equal to approved_at");
  }
  if (evaluatedAt >= session.expires_at) {
    throw new Error("NIP-46 session request gate evaluated_at must be less than expires_at");
  }
  const direction = requireNip46RelayDirection(value.direction);
  if (direction !== "client_to_remote_signer") {
    throw new Error("NIP-46 session request gate direction must be client_to_remote_signer");
  }
  const envelope = parseNip46RelayEventEnvelope(value.event, direction);
  if (envelope.sender_pubkey !== session.client_pubkey) {
    throw new Error("NIP-46 session request sender does not match session client_pubkey");
  }
  if (envelope.recipient_pubkey !== session.remote_signer_pubkey) {
    throw new Error("NIP-46 session request recipient does not match session remote_signer_pubkey");
  }
  const message = requireMessage(value.decrypted_message);
  if (message.method === "connect") {
    throw new Error("NIP-46 session request gate must not process connect");
  }
  return {
    format: "nsealr-nip46-session-request-gate-v0",
    session_name: session.name,
    session_phase: session.phase,
    evaluated_at: evaluatedAt,
    envelope,
    message_id: message.id,
    permission_requirement: nip46PermissionRequirementFromRequest(message),
    blocked_reason: "connect_ack_pending",
    response_message: {
      id: message.id,
      error: "connect_pending: NIP-46 session is approved but connect is not acknowledged"
    },
    client_pubkey_bound_to_sender: true,
    remote_signer_pubkey_bound_to_recipient: true,
    session_not_expired: true,
    uses_session_permissions: false,
    decrypts_content: false,
    opens_relay: false,
    creates_grants: false,
    acknowledges_connect: false,
    dispatches_signer: false,
    stores_production_secrets: false,
    persists_session_state: false
  };
}

export function nip46PermissionRequirementFromRequest(value: unknown): Nip46PermissionRequirement {
  const message = requireMessage(value);
  if (message.method === "connect") throw new Error("NIP-46 connect requires policy review");
  if (message.method === "ping") {
    if (message.params.length !== 0) throw new Error("NIP-46 ping params must be empty");
    return { method: "ping" };
  }
  if (message.method === "switch_relays") {
    if (message.params.length !== 0) throw new Error("NIP-46 switch_relays params must be empty");
    return { method: "switch_relays" };
  }
  if (message.method === "get_public_key") {
    if (message.params.length !== 0) throw new Error("NIP-46 get_public_key params must be empty");
    return { method: "get_public_key" };
  }
  if (message.method === "sign_event") {
    const request = nsealrRequestFromNip46(message);
    if (request.method !== "sign_event") throw new Error("NIP-46 sign_event permission request mismatch");
    const eventTemplate = request.params.event_template;
    if (!isRecord(eventTemplate) || typeof eventTemplate.kind !== "number") {
      throw new Error("NIP-46 sign_event event kind is invalid");
    }
    return {
      method: "sign_event",
      parameter: String(eventTemplate.kind),
      event_kind: eventTemplate.kind
    };
  }
  throw new Error(`unsupported NIP-46 method: ${message.method}`);
}

function permissionMatchesRequirement(
  grantedPermission: Nip46Permission,
  requirement: Nip46PermissionRequirement
): boolean {
  if (grantedPermission.method !== requirement.method) return false;
  if (requirement.method !== "sign_event") return grantedPermission.parameter === undefined;
  if (grantedPermission.parameter === undefined) return true;
  return grantedPermission.event_kind === requirement.event_kind;
}

export function isNip46RequestPermitted(value: unknown, grantedPermissions: readonly Nip46Permission[]): boolean {
  const requirement = nip46PermissionRequirementFromRequest(value);
  return grantedPermissions.some((permission) => permissionMatchesRequirement(permission, requirement));
}

function permissionDeniedResponse(id: string, requirement: Nip46PermissionRequirement): Nip46ResponseMessage {
  return {
    id,
    error: `permission_denied: request requires approved permission ${nip46PermissionLabel(requirement)}`
  };
}

export function decideNip46BridgeAction(
  value: unknown,
  grantedPermissions: readonly Nip46Permission[]
): Nip46BridgeDecision {
  const message = requireMessage(value);
  if (message.method === "connect") {
    return {
      type: "connect_review",
      connect_intent: parseNip46ConnectIntent(message)
    };
  }

  const requirement = nip46PermissionRequirementFromRequest(message);
  if (!grantedPermissions.some((permission) => permissionMatchesRequirement(permission, requirement))) {
    return {
      type: "permission_denied",
      permission_requirement: requirement,
      response_message: permissionDeniedResponse(message.id, requirement)
    };
  }

  if (message.method === "ping" || message.method === "switch_relays") {
    const response = respondToLocalNip46Request(message);
    if (response === undefined) throw new Error(`NIP-46 ${message.method} response was not generated`);
    return {
      type: "local_response",
      permission_requirement: requirement,
      response_message: response
    };
  }

  return {
    type: "signer_request",
    permission_requirement: requirement,
    nsealr_request: nsealrRequestFromNip46(message)
  };
}

export function respondToLocalNip46Request(value: unknown): Nip46ResponseMessage | undefined {
  const message = requireMessage(value);
  if (message.method === "ping") {
    if (message.params.length !== 0) throw new Error("NIP-46 ping params must be empty");
    return {
      id: message.id,
      result: "pong"
    };
  }
  if (message.method === "switch_relays") {
    if (message.params.length !== 0) throw new Error("NIP-46 switch_relays params must be empty");
    return {
      id: message.id,
      result: "null"
    };
  }
  return undefined;
}

export function nsealrRequestFromNip46(value: unknown): NSealrBridgeRequest {
  const message = requireMessage(value);
  if (message.method === "ping") {
    throw new Error("NIP-46 ping is handled locally");
  }
  if (message.method === "connect") {
    throw new Error("NIP-46 connect requires policy review");
  }
  if (message.method === "get_public_key") {
    if (message.params.length !== 0) throw new Error("NIP-46 get_public_key params must be empty");
    const request: NSealrBridgeRequest = {
      version: 1,
      request_id: message.id,
      method: "get_public_key"
    };
    assertValidNSealrRequest(request);
    return request;
  }
  if (message.method === "sign_event") {
    if (message.params.length !== 1) throw new Error("NIP-46 sign_event requires one JSON event-template param");
    const request: NSealrBridgeRequest = {
      version: 1,
      request_id: message.id,
      method: "sign_event",
      params: {
        event_template: parseJsonParam(message.params[0], "sign_event")
      }
    };
    assertValidNSealrRequest(request);
    return request;
  }
  throw new Error(`unsupported NIP-46 method: ${message.method}`);
}

export function nip46ResponseFromNSealr(nip46RequestId: string, response: unknown): Nip46ResponseMessage {
  const id = requireNip46Id(nip46RequestId);
  const shape = validateResponse(response);
  if (!shape.ok) throw new Error(shape.error ?? "invalid nSealr response");
  if (!isRecord(response)) throw new Error("nSealr response must be an object");

  if (response.ok === false) {
    if (!isRecord(response.error)) throw new Error("nSealr error response must include error");
    return {
      id,
      error: `${response.error.code}: ${response.error.message}`
    };
  }

  if (!isRecord(response.result)) throw new Error("nSealr success response must include result");
  if ("event" in response.result) {
    return {
      id,
      result: JSON.stringify(response.result.event)
    };
  }
  if (typeof response.result.public_key === "string") {
    return {
      id,
      result: response.result.public_key
    };
  }
  throw new Error("unsupported nSealr response result for NIP-46");
}
