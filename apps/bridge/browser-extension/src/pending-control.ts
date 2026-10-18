import {
  isBrowserExtensionRequestId
} from "./messages.js";
import {
  BROWSER_EXTENSION_MAX_ACTIVE_PENDING_REQUESTS,
  type BrowserExtensionPendingRequestLifecycle,
  type BrowserExtensionPendingRequestState,
  parseBrowserExtensionPendingRequestState
} from "./pending-request.js";
import {
  parseBrowserExtensionOriginPermissionApproval,
  parseBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  parseBrowserExtensionOriginPermissionStorageWriteResult,
  type BrowserExtensionOriginPermissionStorageWriteResult
} from "./origin-permission-storage.js";
import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionSenderInput
} from "./sender.js";

export const BROWSER_EXTENSION_CONTROL_PROTOCOL = "nsealr-browser-extension-control-v0";

export type BrowserExtensionCancelPendingRequest = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  method: "cancel_pending_request";
  params: {
    pending_request_id: string;
  };
};

export type BrowserExtensionListPendingRequests = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  method: "list_pending_requests";
};

export type BrowserExtensionRequestOriginPermissionReview = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  method: "request_origin_permission_review";
  params: {
    sender: BrowserExtensionSenderInput;
  };
};

export type BrowserExtensionApproveOriginPermission = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  method: "approve_origin_permission";
  params: {
    origin_review: BrowserExtensionOriginPermissionReview;
    reviewed_local_pairing_digest: string;
  };
};

export type BrowserExtensionControlRequest =
  | BrowserExtensionCancelPendingRequest
  | BrowserExtensionListPendingRequests
  | BrowserExtensionRequestOriginPermissionReview
  | BrowserExtensionApproveOriginPermission;

export type BrowserExtensionCancelPendingResponse = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  ok: true;
  result: {
    pending_request_id: string;
    cancelled: boolean;
    stores_production_secrets: false;
    contains_secret_material: false;
  };
};

export type BrowserExtensionListPendingResponse = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  ok: true;
  result: {
    pending_requests: readonly BrowserExtensionPendingRequestState[];
    stores_production_secrets: false;
    contains_secret_material: false;
  };
};

export type BrowserExtensionOriginPermissionReviewResponse = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  ok: true;
  result: {
    origin_review: BrowserExtensionOriginPermissionReview;
    stores_production_secrets: false;
    contains_secret_material: false;
    creates_grants: false;
    injects_provider: false;
  };
};

export type BrowserExtensionOriginPermissionApprovalResponse = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  ok: true;
  result: {
    approval: BrowserExtensionOriginPermissionApproval;
    storage_write: BrowserExtensionOriginPermissionStorageWriteResult;
    requires_user_approval: true;
    writes_extension_storage: true;
    creates_grants: false;
    dispatches_signers: false;
    stores_production_secrets: false;
    contains_secret_material: false;
  };
};

export type BrowserExtensionControlErrorResponse = {
  protocol: typeof BROWSER_EXTENSION_CONTROL_PROTOCOL;
  version: 1;
  request_id: string;
  ok: false;
  error: {
    code: string;
    message: string;
    retryable: false;
  };
};

export type BrowserExtensionControlResponse =
  | BrowserExtensionCancelPendingResponse
  | BrowserExtensionListPendingResponse
  | BrowserExtensionOriginPermissionReviewResponse
  | BrowserExtensionOriginPermissionApprovalResponse
  | BrowserExtensionControlErrorResponse;

export type BrowserExtensionControlSenderOptions = {
  extensionId?: string;
};

export type BrowserExtensionOriginPermissionController = {
  requestOriginPermissionReview(
    sender: BrowserExtensionSenderInput
  ): { originReview: BrowserExtensionOriginPermissionReview } | Promise<{ originReview: BrowserExtensionOriginPermissionReview }>;
  approveOriginPermission?(
    originReview: BrowserExtensionOriginPermissionReview,
    reviewedLocalPairingDigest: string
  ): {
    approval: BrowserExtensionOriginPermissionApproval;
    storageWrite: BrowserExtensionOriginPermissionStorageWriteResult;
  } | Promise<{
    approval: BrowserExtensionOriginPermissionApproval;
    storageWrite: BrowserExtensionOriginPermissionStorageWriteResult;
  }>;
};

export type BrowserExtensionControlHandlerOptions = BrowserExtensionControlSenderOptions & {
  controller?: BrowserExtensionOriginPermissionController;
  pendingRequests?: BrowserExtensionPendingRequestLifecycle;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireRequestId(value: unknown, label: string): string {
  if (!isBrowserExtensionRequestId(value)) {
    throw new Error(`browser extension control ${label} is invalid`);
  }
  return value;
}

function requireErrorCode(value: string): string {
  if (!/^[a-z0-9_:-]{1,64}$/u.test(value)) {
    throw new Error("browser extension control error code is invalid");
  }
  return value;
}

function requireErrorMessage(value: string): string {
  if (value.length === 0 || value.length > 512) {
    throw new Error("browser extension control error message is invalid");
  }
  return value;
}

function requireHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`browser extension control ${label} is invalid`);
  }
  return value;
}

function parseErrorCode(value: unknown): string {
  if (typeof value !== "string") {
    throw new Error("browser extension control error code is invalid");
  }
  return requireErrorCode(value);
}

function parseErrorMessage(value: unknown): string {
  if (typeof value !== "string") {
    throw new Error("browser extension control error message is invalid");
  }
  return requireErrorMessage(value);
}

function fallbackControlRequestId(value: unknown): string {
  if (isRecord(value) && isBrowserExtensionRequestId(value.request_id)) {
    return value.request_id;
  }
  return "invalid-browser-extension-control-request";
}

function controlErrorResponse(
  requestId: string,
  code: string,
  message: string
): BrowserExtensionControlResponse {
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requireRequestId(requestId, "request_id"),
    ok: false,
    error: {
      code: requireErrorCode(code),
      message: requireErrorMessage(message),
      retryable: false
    }
  };
}

function internalSenderUrl(value: unknown, label: string): URL | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`browser extension control sender ${label} is invalid`);
  }
  try {
    return new URL(value);
  } catch {
    throw new Error(`browser extension control sender ${label} is invalid`);
  }
}

function requireInternalSender(value: unknown, options: BrowserExtensionControlSenderOptions): void {
  if (!isRecord(value)) {
    throw new Error("browser extension control sender must be an object");
  }
  const senderId = value.id;
  if (typeof senderId !== "string" || senderId.length === 0) {
    throw new Error("browser extension control sender id is required");
  }
  if (options.extensionId !== undefined && senderId !== options.extensionId) {
    throw new Error("browser extension control sender id does not match expected extension id");
  }
  const originUrl = internalSenderUrl(value.origin, "origin");
  const pageUrl = internalSenderUrl(value.url, "url");
  if (originUrl === undefined && pageUrl === undefined) {
    throw new Error("browser extension control sender internal origin or url is required");
  }
  for (const url of [originUrl, pageUrl]) {
    if (url === undefined) continue;
    if (url.protocol === "http:" || url.protocol === "https:") {
      throw new Error("browser extension control sender must be extension-internal");
    }
    if (url.protocol !== "chrome-extension:" && url.protocol !== "moz-extension:") {
      throw new Error("browser extension control sender URL scheme is unsupported");
    }
  }
}

function parseCancelParams(value: unknown): BrowserExtensionCancelPendingRequest["params"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control params must be an object");
  }
  if (!hasOnlyKeys(value, ["pending_request_id"])) {
    throw new Error("browser extension control params have unsupported fields");
  }
  return {
    pending_request_id: requireRequestId(value.pending_request_id, "pending_request_id")
  };
}

function parseSenderParams(value: unknown): BrowserExtensionRequestOriginPermissionReview["params"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control params must be an object");
  }
  if (!hasOnlyKeys(value, ["sender"])) {
    throw new Error("browser extension control params have unsupported fields");
  }
  const context = browserExtensionClientContextFromSender(value.sender);
  return {
    sender: {
      extension_id: context.extension_id,
      page_origin: context.page_origin,
      ...(context.client.app_name !== undefined ? { app_name: context.client.app_name } : {})
    }
  };
}

function parseApproveOriginPermissionParams(
  value: unknown
): BrowserExtensionApproveOriginPermission["params"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control params must be an object");
  }
  if (!hasOnlyKeys(value, ["origin_review", "reviewed_local_pairing_digest"])) {
    throw new Error("browser extension control params have unsupported fields");
  }
  return {
    origin_review: parseBrowserExtensionOriginPermissionReview(value.origin_review),
    reviewed_local_pairing_digest: requireHex64(
      value.reviewed_local_pairing_digest,
      "reviewed_local_pairing_digest"
    )
  };
}

function parseCancelResult(value: unknown): BrowserExtensionCancelPendingResponse["result"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control cancel result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "pending_request_id",
    "cancelled",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension control cancel result has unsupported fields");
  }
  if (value.cancelled !== true && value.cancelled !== false) {
    throw new Error("browser extension control cancel result cancelled flag is invalid");
  }
  if (value.stores_production_secrets !== false || value.contains_secret_material !== false) {
    throw new Error("browser extension control cancel result must be secretless");
  }
  return {
    pending_request_id: requireRequestId(value.pending_request_id, "pending_request_id"),
    cancelled: value.cancelled,
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

function parseOriginPermissionReviewResult(
  value: unknown
): BrowserExtensionOriginPermissionReviewResponse["result"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control origin permission result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "origin_review",
    "stores_production_secrets",
    "contains_secret_material",
    "creates_grants",
    "injects_provider"
  ])) {
    throw new Error("browser extension control origin permission result has unsupported fields");
  }
  if (
    value.stores_production_secrets !== false ||
    value.contains_secret_material !== false ||
    value.creates_grants !== false ||
    value.injects_provider !== false
  ) {
    throw new Error("browser extension control origin permission result must be secretless and non-authorizing");
  }
  return {
    origin_review: parseBrowserExtensionOriginPermissionReview(value.origin_review),
    stores_production_secrets: false,
    contains_secret_material: false,
    creates_grants: false,
    injects_provider: false
  };
}

function parseOriginPermissionApprovalResult(
  value: unknown
): BrowserExtensionOriginPermissionApprovalResponse["result"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control origin permission approval result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "approval",
    "storage_write",
    "requires_user_approval",
    "writes_extension_storage",
    "creates_grants",
    "dispatches_signers",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension control origin permission approval result has unsupported fields");
  }
  if (
    value.requires_user_approval !== true ||
    value.writes_extension_storage !== true ||
    value.creates_grants !== false ||
    value.dispatches_signers !== false ||
    value.stores_production_secrets !== false ||
    value.contains_secret_material !== false
  ) {
    throw new Error("browser extension control origin permission approval result has unsafe effects");
  }
  return {
    approval: parseBrowserExtensionOriginPermissionApproval(value.approval),
    storage_write: parseBrowserExtensionOriginPermissionStorageWriteResult(value.storage_write),
    requires_user_approval: true,
    writes_extension_storage: true,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

function parseListResult(value: unknown): BrowserExtensionListPendingResponse["result"] {
  if (!isRecord(value)) {
    throw new Error("browser extension control list result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "pending_requests",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension control list result has unsupported fields");
  }
  if (!Array.isArray(value.pending_requests)) {
    throw new Error("browser extension control list result pending_requests must be an array");
  }
  if (value.pending_requests.length > BROWSER_EXTENSION_MAX_ACTIVE_PENDING_REQUESTS) {
    throw new Error("browser extension control list result has too many pending_requests");
  }
  if (value.stores_production_secrets !== false || value.contains_secret_material !== false) {
    throw new Error("browser extension control list result must be secretless");
  }
  const pendingRequests = value.pending_requests.map(parseBrowserExtensionPendingRequestState);
  if (pendingRequests.some((state) => state.status !== "pending")) {
    throw new Error("browser extension control list result pending_requests must be active");
  }
  return {
    pending_requests: Object.freeze(pendingRequests),
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

function parseErrorResponse(value: Record<string, unknown>): BrowserExtensionControlErrorResponse {
  if (!isRecord(value.error)) {
    throw new Error("browser extension control error response error must be an object");
  }
  if (!hasOnlyKeys(value.error, ["code", "message", "retryable"])) {
    throw new Error("browser extension control error response has unsupported error fields");
  }
  if (value.error.retryable !== false) {
    throw new Error("browser extension control error response retryable flag is invalid");
  }
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requireRequestId(value.request_id, "request_id"),
    ok: false,
    error: {
      code: parseErrorCode(value.error.code),
      message: parseErrorMessage(value.error.message),
      retryable: false
    }
  };
}

export function isBrowserExtensionControlEnvelope(value: unknown): boolean {
  return isRecord(value) && value.protocol === BROWSER_EXTENSION_CONTROL_PROTOCOL;
}

export function parseBrowserExtensionControlRequest(value: unknown): BrowserExtensionControlRequest {
  if (!isRecord(value)) {
    throw new Error("browser extension control request must be an object");
  }
  if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "method", "params"])) {
    throw new Error("browser extension control request has unsupported fields");
  }
  if (value.protocol !== BROWSER_EXTENSION_CONTROL_PROTOCOL) {
    throw new Error("browser extension control protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser extension control version is unsupported");
  }
  if (value.method === "list_pending_requests") {
    if ("params" in value) {
      throw new Error("browser extension control list_pending_requests must not include params");
    }
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      method: "list_pending_requests"
    };
  }
  if (value.method === "request_origin_permission_review") {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      method: "request_origin_permission_review",
      params: parseSenderParams(value.params)
    };
  }
  if (value.method === "approve_origin_permission") {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      method: "approve_origin_permission",
      params: parseApproveOriginPermissionParams(value.params)
    };
  }
  if (value.method !== "cancel_pending_request") {
    throw new Error("browser extension control method is unsupported");
  }
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requireRequestId(value.request_id, "request_id"),
    method: "cancel_pending_request",
    params: parseCancelParams(value.params)
  };
}

export function parseBrowserExtensionControlResponse(value: unknown): BrowserExtensionControlResponse {
  if (!isRecord(value)) {
    throw new Error("browser extension control response must be an object");
  }
  if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "ok", "result", "error"])) {
    throw new Error("browser extension control response has unsupported fields");
  }
  if (value.protocol !== BROWSER_EXTENSION_CONTROL_PROTOCOL) {
    throw new Error("browser extension control response protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser extension control response version is unsupported");
  }
  if (value.ok === false) {
    if ("result" in value) {
      throw new Error("browser extension control error response must not include result");
    }
    return parseErrorResponse(value);
  }
  if (value.ok !== true) {
    throw new Error("browser extension control response ok flag is invalid");
  }
  if ("error" in value) {
    throw new Error("browser extension control success response must not include error");
  }
  const result = value.result;
  if (!isRecord(result)) {
    throw new Error("browser extension control success response result must be an object");
  }
  if ("origin_review" in result) {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      ok: true,
      result: parseOriginPermissionReviewResult(result)
    };
  }
  if ("approval" in result) {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      ok: true,
      result: parseOriginPermissionApprovalResult(result)
    };
  }
  if ("pending_requests" in result) {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: requireRequestId(value.request_id, "request_id"),
      ok: true,
      result: parseListResult(result)
    };
  }
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requireRequestId(value.request_id, "request_id"),
    ok: true,
    result: parseCancelResult(result)
  };
}

export async function handleBrowserExtensionControlMessage(
  value: unknown,
  runtimeSender: unknown,
  options: BrowserExtensionControlHandlerOptions
): Promise<BrowserExtensionControlResponse> {
  const requestId = fallbackControlRequestId(value);
  let request: BrowserExtensionControlRequest;
  try {
    request = parseBrowserExtensionControlRequest(value);
  } catch {
    return controlErrorResponse(requestId, "invalid_request", "browser extension control request is invalid");
  }
  try {
    requireInternalSender(runtimeSender, options);
  } catch {
    return controlErrorResponse(request.request_id, "invalid_sender", "browser extension control sender is invalid");
  }
  if (request.method === "request_origin_permission_review") {
    if (options.controller === undefined) {
      return controlErrorResponse(
        request.request_id,
        "origin_permission_review_unavailable",
        "browser extension origin permission review is unavailable"
      );
    }
    try {
      const result = await options.controller.requestOriginPermissionReview(request.params.sender);
      return {
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: request.request_id,
        ok: true,
        result: parseOriginPermissionReviewResult({
          origin_review: result.originReview,
          stores_production_secrets: false,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false
        })
      };
    } catch {
      return controlErrorResponse(
        request.request_id,
        "origin_permission_review_failed",
        "browser extension origin permission review failed"
      );
    }
  }
  if (request.method === "approve_origin_permission") {
    if (options.controller?.approveOriginPermission === undefined) {
      return controlErrorResponse(
        request.request_id,
        "origin_permission_approval_unavailable",
        "browser extension origin permission approval is unavailable"
      );
    }
    try {
      const result = await options.controller.approveOriginPermission(
        request.params.origin_review,
        request.params.reviewed_local_pairing_digest
      );
      return {
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: request.request_id,
        ok: true,
        result: parseOriginPermissionApprovalResult({
          approval: result.approval,
          storage_write: result.storageWrite,
          requires_user_approval: true,
          writes_extension_storage: true,
          creates_grants: false,
          dispatches_signers: false,
          stores_production_secrets: false,
          contains_secret_material: false
        })
      };
    } catch {
      return controlErrorResponse(
        request.request_id,
        "origin_permission_approval_failed",
        "browser extension origin permission approval failed"
      );
    }
  }
  if (options.pendingRequests === undefined) {
    return controlErrorResponse(request.request_id, "pending_requests_unavailable", "pending request control is unavailable");
  }
  if (request.method === "list_pending_requests") {
    let pendingRequests: readonly BrowserExtensionPendingRequestState[];
    try {
      pendingRequests = options.pendingRequests.active();
    } catch {
      return controlErrorResponse(request.request_id, "list_failed", "pending request listing failed");
    }
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: request.request_id,
      ok: true,
      result: {
        pending_requests: pendingRequests,
        stores_production_secrets: false,
        contains_secret_material: false
      }
    };
  }

  let cancelled: BrowserExtensionPendingRequestState | undefined;
  try {
    cancelled = options.pendingRequests.cancel(request.params.pending_request_id);
  } catch {
    return controlErrorResponse(request.request_id, "cancel_failed", "pending request cancellation failed");
  }
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      pending_request_id: request.params.pending_request_id,
      cancelled: cancelled !== undefined,
      stores_production_secrets: false,
      contains_secret_material: false
    }
  };
}
