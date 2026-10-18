import { sha256Utf8Hex, verifySignedEventResponse } from "@nsealr/core";
import {
  parseRouteSelectionRequest,
  selectAccountRoute,
  type AccountDescriptor,
  type RouteSelection,
  type RouteSelectionRequest
} from "@nsealr/policy";
import { compactJsonUtf8ByteLength, NSEALR_V0_LIMITS, validateRequest, validateResponse } from "@nsealr/protocol";
import { approvalDigestForRequest } from "@nsealr/review";
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
};

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
    }
  | {
      ok: false;
      response: LocalServiceResponse;
    };

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
  const displayLessSignEvent = routeSelection.trusted_review === "display_less" && routeRequest.method === "sign_event";
  if (displayLessSignEvent) {
    if (acknowledgement === undefined) {
      return {
        ok: false,
        response: errorResponse(
          request,
          "external_review_acknowledgement_required",
          "display-less signer dispatch requires external review acknowledgement"
        )
      };
    }
    if (acknowledgement.approval_digest !== approvalDigestForRequest(request.params.request)) {
      return {
        ok: false,
        response: errorResponse(
          request,
          "external_review_acknowledgement_mismatch",
          "external review approval_digest does not match signer request"
        )
      };
    }
  } else if (acknowledgement !== undefined) {
    return {
      ok: false,
      response: errorResponse(
        request,
        "external_review_acknowledgement_unsupported",
        "external review acknowledgement is only supported for display-less sign_event dispatch"
      )
    };
  }

  if (context.signerDispatcher === undefined) {
    return {
      ok: false,
      response: errorResponse(request, "signer_route_unavailable", "signer dispatch is not configured")
    };
  }

  return {
    ok: true,
    dispatcher: context.signerDispatcher,
    dispatchRequest: {
      client: request.params.client,
      route_selection: routeSelection,
      request: request.params.request,
      ...(acknowledgement !== undefined ? { external_review_acknowledgement: acknowledgement } : {})
    }
  };
}

function dispatchFailureResponse(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  error: unknown
): LocalServiceResponse {
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

function dispatchSignerRequest(
  request: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>,
  context: LocalServiceContext
): LocalServiceResponse {
  const prepared = prepareSignerDispatch(request, context);
  if (!prepared.ok) return prepared.response;

  let signerResponse: unknown;
  try {
    signerResponse = prepared.dispatcher(prepared.dispatchRequest);
  } catch (error) {
    return dispatchFailureResponse(request, error);
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
  try {
    signerResponse = await prepared.dispatcher(prepared.dispatchRequest);
  } catch (error) {
    return dispatchFailureResponse(request, error);
  }
  return dispatchSuccessResponse(request, prepared.dispatchRequest.route_selection, signerResponse);
}
