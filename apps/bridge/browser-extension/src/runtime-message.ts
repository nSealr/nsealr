import {
  type BrowserExtensionBackgroundController,
  type BrowserExtensionBackgroundRequestOptions
} from "./background.js";
import { type BrowserExtensionResponse } from "./handler.js";
import {
  browserExtensionErrorResponse,
  isBrowserExtensionRequestId,
  parseBrowserExtensionRequest
} from "./messages.js";
import {
  type BrowserExtensionPendingRequestLifecycle,
  type BrowserExtensionPendingRequestState
} from "./pending-request.js";
import {
  BROWSER_EXTENSION_CONTROL_PROTOCOL,
  handleBrowserExtensionControlMessage,
  isBrowserExtensionControlEnvelope,
  type BrowserExtensionControlResponse
} from "./pending-control.js";
import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionSenderInput
} from "./sender.js";

export type BrowserExtensionRuntimeSender = {
  id?: unknown;
  origin?: unknown;
  url?: unknown;
};

export type BrowserExtensionRuntimeSenderOptions = {
  extensionId?: string;
  appName?: string;
};

export type BrowserExtensionRuntimeMessageOptions = BrowserExtensionRuntimeSenderOptions & {
  controller: Pick<
    BrowserExtensionBackgroundController,
    "handleRequest" | "requestOriginPermissionReview" | "approveOriginPermission"
  >;
  nativeMessageAbortSignal?: AbortSignal;
  pendingRequests?: BrowserExtensionPendingRequestLifecycle;
  onPendingRequestError?: (error: unknown) => void;
};

export type BrowserExtensionRuntimeMessageResponse = BrowserExtensionResponse | BrowserExtensionControlResponse;

export type BrowserExtensionRuntimeMessageResponder = (response: BrowserExtensionRuntimeMessageResponse) => void;

export type BrowserExtensionRuntimeMessageListener = (
  value: unknown,
  runtimeSender: unknown,
  sendResponse: BrowserExtensionRuntimeMessageResponder
) => true;

export type BrowserExtensionRuntimeMessageEventTarget = {
  addListener(listener: BrowserExtensionRuntimeMessageListener): void;
  removeListener(listener: BrowserExtensionRuntimeMessageListener): void;
};

export type BrowserExtensionRuntimeMessageListenerOptions = BrowserExtensionRuntimeMessageOptions & {
  runtimeOnMessage: BrowserExtensionRuntimeMessageEventTarget;
  onError?: (error: unknown) => void;
};

export type BrowserExtensionRuntimeMessageListenerHandle = {
  dispose(): void;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fallbackRequestId(value: unknown): string {
  if (isRecord(value) && isBrowserExtensionRequestId(value.request_id)) {
    return value.request_id;
  }
  return "invalid-browser-extension-request";
}

function fallbackControlRequestId(value: unknown): string {
  if (isRecord(value) && isBrowserExtensionRequestId(value.request_id)) {
    return value.request_id;
  }
  return "invalid-browser-extension-control-request";
}

function requireRuntimeString(value: unknown, label: string): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`browser runtime sender ${label} is invalid`);
  }
  return value;
}

function runtimeExtensionId(
  runtimeSender: BrowserExtensionRuntimeSender,
  options: BrowserExtensionRuntimeSenderOptions
): string {
  const senderId = requireRuntimeString(runtimeSender.id, "id");
  if (options.extensionId !== undefined && senderId !== undefined && options.extensionId !== senderId) {
    throw new Error("browser runtime sender id does not match expected extension id");
  }
  const extensionId = options.extensionId ?? senderId;
  if (extensionId === undefined) {
    throw new Error("browser runtime sender id is required");
  }
  return extensionId;
}

export function browserExtensionSenderFromRuntimeSender(
  value: unknown,
  options: BrowserExtensionRuntimeSenderOptions = {}
): BrowserExtensionSenderInput {
  if (!isRecord(value)) throw new Error("browser runtime sender must be an object");
  const runtimeSender: BrowserExtensionRuntimeSender = value;
  const pageOrigin = requireRuntimeString(runtimeSender.origin, "origin");
  const pageUrl = requireRuntimeString(runtimeSender.url, "url");
  if (pageOrigin === undefined && pageUrl === undefined) {
    throw new Error("browser runtime sender page origin or url is required");
  }
  const sender: BrowserExtensionSenderInput = {
    extension_id: runtimeExtensionId(runtimeSender, options),
    ...(pageOrigin !== undefined ? { page_origin: pageOrigin } : {}),
    ...(pageUrl !== undefined ? { page_url: pageUrl } : {}),
    ...(options.appName !== undefined ? { app_name: options.appName } : {})
  };
  browserExtensionClientContextFromSender(sender);
  return sender;
}

export async function handleBrowserExtensionRuntimeMessage(
  value: unknown,
  runtimeSender: unknown,
  options: BrowserExtensionRuntimeMessageOptions
): Promise<BrowserExtensionRuntimeMessageResponse> {
  if (isBrowserExtensionControlEnvelope(value)) {
    return handleBrowserExtensionControlMessage(value, runtimeSender, {
      ...(options.extensionId !== undefined ? { extensionId: options.extensionId } : {}),
      controller: options.controller,
      ...(options.pendingRequests !== undefined ? { pendingRequests: options.pendingRequests } : {})
    });
  }
  let sender: BrowserExtensionSenderInput;
  try {
    sender = browserExtensionSenderFromRuntimeSender(runtimeSender, options);
  } catch {
    return browserExtensionErrorResponse(
      fallbackRequestId(value),
      "invalid_sender",
      "browser runtime sender is invalid"
    );
  }
  const pending = startPendingRequest(value, sender, options);
  const pendingAbortSignal = pending === undefined ? undefined : options.pendingRequests?.abortSignal(pending);
  try {
    const response = await withMergedAbortSignal(
      options.nativeMessageAbortSignal,
      pendingAbortSignal,
      (nativeMessageAbortSignal) => options.controller.handleRequest(value, sender, {
        ...(nativeMessageAbortSignal !== undefined ? { nativeMessageAbortSignal } : {})
      })
    );
    settlePendingRequest(pending, response, options);
    return response;
  } catch (error) {
    if (pending !== undefined && options.pendingRequests !== undefined) {
      try {
        options.pendingRequests.settle(pending, "rejected");
      } catch (pendingError) {
        reportRuntimeListenerError(pendingError, options.onPendingRequestError);
      }
    }
    throw error;
  }
}

async function withMergedAbortSignal<T>(
  first: AbortSignal | undefined,
  second: AbortSignal | undefined,
  operation: (abortSignal: AbortSignal | undefined) => Promise<T> | T
): Promise<T> {
  if (first === undefined || first === second) return operation(second ?? first);
  if (second === undefined) return operation(first);

  const abortController = new AbortController();
  const abort = () => abortController.abort();
  first.addEventListener("abort", abort, { once: true });
  second.addEventListener("abort", abort, { once: true });
  if (first.aborted || second.aborted) abort();
  try {
    return await operation(abortController.signal);
  } finally {
    first.removeEventListener("abort", abort);
    second.removeEventListener("abort", abort);
  }
}

function runtimeMessageHandlerOptions(
  options: BrowserExtensionRuntimeMessageListenerOptions
): BrowserExtensionRuntimeMessageOptions {
  return {
    controller: options.controller,
    ...(options.extensionId !== undefined ? { extensionId: options.extensionId } : {}),
    ...(options.appName !== undefined ? { appName: options.appName } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {}),
    ...(options.pendingRequests !== undefined ? { pendingRequests: options.pendingRequests } : {}),
    ...(options.onError !== undefined ? { onPendingRequestError: options.onError } : {})
  };
}

function reportRuntimeListenerError(error: unknown, onError: ((error: unknown) => void) | undefined): void {
  if (onError === undefined) return;
  try {
    onError(error);
  } catch {
    // Listener diagnostics must not create unhandled browser promise failures.
  }
}

function runtimeHandlerFailureResponse(value: unknown): BrowserExtensionRuntimeMessageResponse {
  if (isBrowserExtensionControlEnvelope(value)) {
    return {
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: fallbackControlRequestId(value),
      ok: false,
      error: {
        code: "runtime_handler_failed",
        message: "browser extension runtime control request failed",
        retryable: false
      }
    };
  }
  return browserExtensionErrorResponse(
    fallbackRequestId(value),
    "runtime_handler_failed",
    "browser extension runtime request failed"
  );
}

function sendRuntimeResponse(
  sendResponse: BrowserExtensionRuntimeMessageResponder,
  response: BrowserExtensionRuntimeMessageResponse,
  onError: ((error: unknown) => void) | undefined
): void {
  try {
    sendResponse(response);
  } catch (error) {
    reportRuntimeListenerError(error, onError);
  }
}

function startPendingRequest(
  value: unknown,
  sender: BrowserExtensionSenderInput,
  options: BrowserExtensionRuntimeMessageOptions
): BrowserExtensionPendingRequestState | undefined {
  if (options.pendingRequests === undefined) return undefined;
  try {
    return options.pendingRequests.start(parseBrowserExtensionRequest(value), sender);
  } catch (error) {
    reportRuntimeListenerError(error, options.onPendingRequestError);
    return undefined;
  }
}

function settlePendingRequest(
  pending: BrowserExtensionPendingRequestState | undefined,
  response: BrowserExtensionResponse,
  options: BrowserExtensionRuntimeMessageOptions
): void {
  if (pending === undefined || options.pendingRequests === undefined) return;
  try {
    options.pendingRequests.settle(pending, response.ok ? "resolved" : "rejected");
  } catch (error) {
    reportRuntimeListenerError(error, options.onPendingRequestError);
  }
}

export function installBrowserExtensionRuntimeMessageListener(
  options: BrowserExtensionRuntimeMessageListenerOptions
): BrowserExtensionRuntimeMessageListenerHandle {
  let disposed = false;
  const handlerOptions = runtimeMessageHandlerOptions(options);
  const listener: BrowserExtensionRuntimeMessageListener = (value, runtimeSender, sendResponse) => {
    void (async () => {
      try {
        const response = await handleBrowserExtensionRuntimeMessage(value, runtimeSender, handlerOptions);
        if (!disposed) sendRuntimeResponse(sendResponse, response, options.onError);
      } catch (error) {
        reportRuntimeListenerError(error, options.onError);
        if (!disposed) {
          sendRuntimeResponse(sendResponse, runtimeHandlerFailureResponse(value), options.onError);
        }
      }
    })();
    return true;
  };
  options.runtimeOnMessage.addListener(listener);
  return Object.freeze({
    dispose(): void {
      if (disposed) return;
      disposed = true;
      options.runtimeOnMessage.removeListener(listener);
    }
  });
}
