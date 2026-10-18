import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  isBrowserExtensionRequestId,
  parseBrowserExtensionRequest,
  type BrowserExtensionRequest
} from "./messages.js";
import { type BrowserExtensionResponse } from "./handler.js";
import {
  type BrowserExtensionBackgroundRequester,
  type BrowserExtensionPageRequestOptions
} from "./page-provider.js";

export const BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL = "nsealr-page-bridge-v0";

export type BrowserExtensionPageBridgeRequest = {
  protocol: typeof BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL;
  version: 1;
  direction: "page_to_extension";
  request_id: string;
  request: BrowserExtensionRequest;
};

export type BrowserExtensionPageBridgeResponse = {
  protocol: typeof BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL;
  version: 1;
  direction: "extension_to_page";
  request_id: string;
  response: BrowserExtensionResponse;
};

export type BrowserExtensionPageBridgeOptions = {
  requestBackground: (
    request: BrowserExtensionRequest,
    options: BrowserExtensionPageRequestOptions
  ) => Promise<unknown> | unknown;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionPageBridgeMessageExchange = (
  request: BrowserExtensionPageBridgeRequest,
  options: BrowserExtensionPageRequestOptions
) => Promise<unknown> | unknown;

export type BrowserExtensionPageBridgeRequesterOptions = {
  exchangeBridgeMessage: BrowserExtensionPageBridgeMessageExchange;
  abortSignal?: AbortSignal;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function assertNotCancelled(abortSignal: AbortSignal | undefined): void {
  if (abortSignal?.aborted === true) {
    throw new Error("browser page bridge request was cancelled");
  }
}

async function runWithAbortSignal<T>(
  abortSignal: AbortSignal | undefined,
  operation: (abortSignal: AbortSignal | undefined) => Promise<T> | T
): Promise<T> {
  assertNotCancelled(abortSignal);
  const operationPromise = Promise.resolve(operation(abortSignal));
  if (abortSignal === undefined) return operationPromise;

  let abortListener: (() => void) | undefined;
  const abortPromise = new Promise<T>((_resolve, reject) => {
    abortListener = () => reject(new Error("browser page bridge request was cancelled"));
    if (abortSignal.aborted) {
      abortListener();
      return;
    }
    abortSignal.addEventListener("abort", abortListener, { once: true });
  });
  try {
    return await Promise.race([operationPromise, abortPromise]);
  } finally {
    if (abortListener !== undefined) {
      abortSignal.removeEventListener("abort", abortListener);
    }
  }
}

async function withPageBridgeAbortSignal<T>(
  first: AbortSignal | undefined,
  second: AbortSignal | undefined,
  operation: (abortSignal: AbortSignal | undefined) => Promise<T> | T
): Promise<T> {
  assertNotCancelled(first);
  assertNotCancelled(second);
  if (first === undefined || first === second) return runWithAbortSignal(second ?? first, operation);
  if (second === undefined) return runWithAbortSignal(first, operation);

  const abortController = new AbortController();
  const abort = () => abortController.abort();
  first.addEventListener("abort", abort, { once: true });
  second.addEventListener("abort", abort, { once: true });
  try {
    return await runWithAbortSignal(abortController.signal, operation);
  } finally {
    first.removeEventListener("abort", abort);
    second.removeEventListener("abort", abort);
  }
}

export function parseBrowserExtensionPageBridgeRequest(value: unknown): BrowserExtensionPageBridgeRequest {
  if (!isRecord(value)) throw new Error("browser page bridge request must be an object");
  if (!hasOnlyKeys(value, ["protocol", "version", "direction", "request_id", "request"])) {
    throw new Error("browser page bridge request has unsupported fields");
  }
  if (value.protocol !== BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL) {
    throw new Error("browser page bridge request protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser page bridge request version is unsupported");
  }
  if (value.direction !== "page_to_extension") {
    throw new Error("browser page bridge request direction is unsupported");
  }
  if (!isBrowserExtensionRequestId(value.request_id)) {
    throw new Error("browser page bridge request_id is invalid");
  }
  const request = parseBrowserExtensionRequest(value.request);
  if (request.request_id !== value.request_id) {
    throw new Error("browser page bridge request_id does not match inner request");
  }
  return {
    protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
    version: 1,
    direction: "page_to_extension",
    request_id: value.request_id,
    request
  };
}

function requireBackgroundResponse(value: unknown, requestId: string): BrowserExtensionResponse {
  if (!isRecord(value)) throw new Error("browser page bridge response must be an object");
  if (value.protocol !== BROWSER_EXTENSION_MESSAGE_PROTOCOL) {
    throw new Error("browser page bridge response protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser page bridge response version is unsupported");
  }
  if (!isBrowserExtensionRequestId(value.request_id) || value.request_id !== requestId) {
    throw new Error("browser page bridge response request_id does not match request");
  }
  if (value.ok !== true && value.ok !== false) {
    throw new Error("browser page bridge response ok flag is invalid");
  }
  if (value.ok) {
    if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "ok", "result"])) {
      throw new Error("browser page bridge response has unsupported fields");
    }
    if (!isRecord(value.result)) {
      throw new Error("browser page bridge response result is invalid");
    }
  } else {
    if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "ok", "error"])) {
      throw new Error("browser page bridge response has unsupported fields");
    }
    if (!isRecord(value.error)) {
      throw new Error("browser page bridge response error is invalid");
    }
    if (!hasOnlyKeys(value.error, ["code", "message", "retryable"])) {
      throw new Error("browser page bridge response error has unsupported fields");
    }
    if (typeof value.error.code !== "string" || !/^[a-z0-9_:-]{1,64}$/u.test(value.error.code)) {
      throw new Error("browser page bridge response error code is invalid");
    }
    if (typeof value.error.message !== "string" || value.error.message.length === 0 || value.error.message.length > 512) {
      throw new Error("browser page bridge response error message is invalid");
    }
    if (value.error.retryable !== false) {
      throw new Error("browser page bridge response error retryable flag is invalid");
    }
  }
  return value as BrowserExtensionResponse;
}

export function parseBrowserExtensionPageBridgeResponse(
  value: unknown,
  requestId: string
): BrowserExtensionPageBridgeResponse {
  if (!isRecord(value)) throw new Error("browser page bridge response envelope must be an object");
  if (!hasOnlyKeys(value, ["protocol", "version", "direction", "request_id", "response"])) {
    throw new Error("browser page bridge response envelope has unsupported fields");
  }
  if (value.protocol !== BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL) {
    throw new Error("browser page bridge response envelope protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser page bridge response envelope version is unsupported");
  }
  if (value.direction !== "extension_to_page") {
    throw new Error("browser page bridge response envelope direction is unsupported");
  }
  if (!isBrowserExtensionRequestId(value.request_id) || value.request_id !== requestId) {
    throw new Error("browser page bridge response envelope request_id does not match request");
  }
  const response = requireBackgroundResponse(value.response, requestId);
  return {
    protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
    version: 1,
    direction: "extension_to_page",
    request_id: requestId,
    response
  };
}

export async function handleBrowserExtensionPageBridgeRequest(
  value: unknown,
  options: BrowserExtensionPageBridgeOptions
): Promise<BrowserExtensionPageBridgeResponse> {
  assertNotCancelled(options.abortSignal);
  const request = parseBrowserExtensionPageBridgeRequest(value);
  const response = requireBackgroundResponse(await options.requestBackground(request.request, {
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  }), request.request_id);
  return {
    protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
    version: 1,
    direction: "extension_to_page",
    request_id: request.request_id,
    response
  };
}

export function createBrowserExtensionPageBridgeBackgroundRequester(
  options: BrowserExtensionPageBridgeRequesterOptions
): BrowserExtensionBackgroundRequester {
  return async (
    request: BrowserExtensionRequest,
    requestOptions: BrowserExtensionPageRequestOptions = {}
  ): Promise<BrowserExtensionResponse> => withPageBridgeAbortSignal(
    options.abortSignal,
    requestOptions.abortSignal,
    async (abortSignal) => {
      const parsedRequest = parseBrowserExtensionRequest(request);
      const bridgeRequest: BrowserExtensionPageBridgeRequest = {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "page_to_extension",
        request_id: parsedRequest.request_id,
        request: parsedRequest
      };
      const bridgeResponse = parseBrowserExtensionPageBridgeResponse(
        await options.exchangeBridgeMessage(bridgeRequest, {
          ...(abortSignal !== undefined ? { abortSignal } : {})
        }),
        parsedRequest.request_id
      );
      return bridgeResponse.response;
    }
  );
}
