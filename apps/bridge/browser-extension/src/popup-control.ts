import { isBrowserExtensionRequestId } from "./messages.js";
import {
  BROWSER_EXTENSION_CONTROL_PROTOCOL,
  parseBrowserExtensionControlResponse,
  type BrowserExtensionControlResponse
} from "./pending-control.js";
import { type BrowserExtensionPendingRequestState } from "./pending-request.js";
import {
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import { type BrowserExtensionOriginPermissionStorageWriteResult } from "./origin-permission-storage.js";
import { type BrowserExtensionSenderInput } from "./sender.js";

export type BrowserExtensionPopupRuntimeApi = {
  sendMessage(message: unknown): Promise<unknown> | unknown;
};

export type BrowserExtensionPopupControlOptions = {
  runtime: BrowserExtensionPopupRuntimeApi;
  nextRequestId?: () => string;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionPopupCancelResult = {
  pending_request_id: string;
  cancelled: boolean;
  stores_production_secrets: false;
  contains_secret_material: false;
};

export type BrowserExtensionPopupOriginPermissionReviewResult = {
  origin_review: BrowserExtensionOriginPermissionReview;
  stores_production_secrets: false;
  contains_secret_material: false;
  creates_grants: false;
  injects_provider: false;
};

export type BrowserExtensionPopupOriginPermissionApprovalResult = {
  approval: BrowserExtensionOriginPermissionApproval;
  storage_write: BrowserExtensionOriginPermissionStorageWriteResult;
  requires_user_approval: true;
  writes_extension_storage: true;
  creates_grants: false;
  dispatches_signers: false;
  stores_production_secrets: false;
  contains_secret_material: false;
};

export type BrowserExtensionPopupPendingRequestControls = {
  listPendingRequests(): Promise<readonly BrowserExtensionPendingRequestState[]>;
  cancelPendingRequest(pendingRequestId: string): Promise<BrowserExtensionPopupCancelResult>;
};

export type BrowserExtensionPopupControls = BrowserExtensionPopupPendingRequestControls & {
  requestOriginPermissionReview(sender: BrowserExtensionSenderInput): Promise<BrowserExtensionPopupOriginPermissionReviewResult>;
  approveOriginPermission(
    originReview: BrowserExtensionOriginPermissionReview,
    reviewedLocalPairingDigest: string
  ): Promise<BrowserExtensionPopupOriginPermissionApprovalResult>;
};

type BrowserExtensionPopupControlSuccessResponse = Exclude<
  BrowserExtensionControlResponse,
  { ok: false }
>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requirePopupRuntime(value: BrowserExtensionPopupRuntimeApi): BrowserExtensionPopupRuntimeApi {
  if (!isRecord(value) || typeof value.sendMessage !== "function") {
    throw new Error("browser extension popup runtime is invalid");
  }
  return value;
}

function requireControlRequestId(value: string): string {
  if (!isBrowserExtensionRequestId(value)) {
    throw new Error("browser extension popup control request id is invalid");
  }
  return value;
}

function requirePendingRequestId(value: string): string {
  if (!isBrowserExtensionRequestId(value)) {
    throw new Error("browser extension popup pending request id is invalid");
  }
  return value;
}

function defaultRequestIdFactory(): () => string {
  let next = 0;
  return () => `popup-control-${++next}`;
}

function assertNotCancelled(abortSignal: AbortSignal | undefined): void {
  if (abortSignal?.aborted === true) {
    throw new Error("browser extension popup control request was cancelled");
  }
}

async function withAbortSignal<T>(
  abortSignal: AbortSignal | undefined,
  operation: () => Promise<T> | T
): Promise<T> {
  assertNotCancelled(abortSignal);
  if (abortSignal === undefined) {
    return operation();
  }
  let rejectAbort: ((error: Error) => void) | undefined;
  const abortPromise = new Promise<never>((_, reject) => {
    rejectAbort = reject;
  });
  const abort = () => rejectAbort?.(new Error("browser extension popup control request was cancelled"));
  abortSignal.addEventListener("abort", abort, { once: true });
  try {
    return await Promise.race([Promise.resolve(operation()), abortPromise]);
  } finally {
    abortSignal.removeEventListener("abort", abort);
  }
}

export function createBrowserExtensionPopupControls(
  options: BrowserExtensionPopupControlOptions
): BrowserExtensionPopupControls {
  const runtime = requirePopupRuntime(options.runtime);
  const nextRequestId = options.nextRequestId ?? defaultRequestIdFactory();

  async function sendControlRequest(
    request: unknown,
    requestId: string
  ): Promise<BrowserExtensionPopupControlSuccessResponse> {
    const response = await withAbortSignal(options.abortSignal, () => runtime.sendMessage(request));
    assertNotCancelled(options.abortSignal);
    const parsed = parseBrowserExtensionControlResponse(response);
    if (parsed.request_id !== requestId) {
      throw new Error("browser extension popup control response request id mismatch");
    }
    if (!parsed.ok) {
      throw new Error(`browser extension popup control request failed: ${parsed.error.code}`);
    }
    return parsed;
  }

  return Object.freeze({
    async listPendingRequests(): Promise<readonly BrowserExtensionPendingRequestState[]> {
      const requestId = requireControlRequestId(nextRequestId());
      const response = await sendControlRequest({
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: requestId,
        method: "list_pending_requests"
      }, requestId);
      if (!("pending_requests" in response.result)) {
        throw new Error("browser extension popup control list response is invalid");
      }
      return response.result.pending_requests;
    },

    async cancelPendingRequest(pendingRequestId: string): Promise<BrowserExtensionPopupCancelResult> {
      const requestId = requireControlRequestId(nextRequestId());
      const response = await sendControlRequest({
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: requestId,
        method: "cancel_pending_request",
        params: {
          pending_request_id: requirePendingRequestId(pendingRequestId)
        }
      }, requestId);
      if (!("pending_request_id" in response.result)) {
        throw new Error("browser extension popup control cancel response is invalid");
      }
      return response.result;
    },

    async requestOriginPermissionReview(
      sender: BrowserExtensionSenderInput
    ): Promise<BrowserExtensionPopupOriginPermissionReviewResult> {
      const requestId = requireControlRequestId(nextRequestId());
      const response = await sendControlRequest({
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: requestId,
        method: "request_origin_permission_review",
        params: {
          sender
        }
      }, requestId);
      if (!("origin_review" in response.result)) {
        throw new Error("browser extension popup control origin permission response is invalid");
      }
      return response.result;
    },

    async approveOriginPermission(
      originReview: BrowserExtensionOriginPermissionReview,
      reviewedLocalPairingDigest: string
    ): Promise<BrowserExtensionPopupOriginPermissionApprovalResult> {
      const requestId = requireControlRequestId(nextRequestId());
      const response = await sendControlRequest({
        protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
        version: 1,
        request_id: requestId,
        method: "approve_origin_permission",
        params: {
          origin_review: originReview,
          reviewed_local_pairing_digest: reviewedLocalPairingDigest
        }
      }, requestId);
      if (!("approval" in response.result)) {
        throw new Error("browser extension popup control origin permission approval response is invalid");
      }
      return response.result;
    }
  });
}
