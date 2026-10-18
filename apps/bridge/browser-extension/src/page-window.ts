import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  parseBrowserExtensionPageBridgeRequest,
  parseBrowserExtensionPageBridgeResponse,
  type BrowserExtensionPageBridgeMessageExchange,
  type BrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import {
  normalizeBrowserExtensionPageOrigin,
  requireBrowserExtensionPageOrigin
} from "./page-origin.js";
import { type BrowserExtensionPageRequestOptions } from "./page-provider.js";

export type BrowserExtensionPageWindowEvent = {
  data: unknown;
  origin: string;
  source: unknown;
};

export type BrowserExtensionPageWindowMessageListener = (event: unknown) => void;

export type BrowserExtensionPageWindowTarget = {
  addEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
  removeEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
  postMessage(message: BrowserExtensionPageBridgeRequest, targetOrigin: string): void;
};

export type BrowserExtensionPageWindowBridgeExchangeOptions = {
  target: BrowserExtensionPageWindowTarget;
  expectedSource: unknown;
  expectedOrigin: string;
  abortSignal?: AbortSignal;
  responseTimeoutMs?: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireExpectedPageOrigin(value: unknown): string {
  return requireBrowserExtensionPageOrigin(value, "browser page-window expected origin is invalid");
}

function requireResponseTimeoutMs(value: number | undefined): number | undefined {
  if (value === undefined) return undefined;
  if (!Number.isInteger(value) || value <= 0 || value > 60_000) {
    throw new Error("browser page-window response timeout is invalid");
  }
  return value;
}

function assertNotCancelled(abortSignal: AbortSignal | undefined): void {
  if (abortSignal?.aborted === true) {
    throw new Error("browser page-window bridge request was cancelled");
  }
}

function responseCandidateMatches(value: unknown, requestId: string): boolean {
  return isRecord(value) &&
    value.protocol === BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL &&
    value.direction === "extension_to_page" &&
    value.request_id === requestId;
}

function removeAbortListener(abortSignal: AbortSignal | undefined, listener: (() => void) | undefined): void {
  if (abortSignal !== undefined && listener !== undefined) {
    abortSignal.removeEventListener("abort", listener);
  }
}

export function createBrowserExtensionPageWindowBridgeExchange(
  options: BrowserExtensionPageWindowBridgeExchangeOptions
): BrowserExtensionPageBridgeMessageExchange {
  const expectedOrigin = requireExpectedPageOrigin(options.expectedOrigin);
  const responseTimeoutMs = requireResponseTimeoutMs(options.responseTimeoutMs);

  return async (
    request: BrowserExtensionPageBridgeRequest,
    requestOptions: BrowserExtensionPageRequestOptions = {}
  ): Promise<BrowserExtensionPageBridgeResponse> => {
    const bridgeRequest = parseBrowserExtensionPageBridgeRequest(request);
    assertNotCancelled(options.abortSignal);
    assertNotCancelled(requestOptions.abortSignal);

    return new Promise((resolve, reject) => {
      let settled = false;
      let timeout: ReturnType<typeof setTimeout> | undefined;
      let optionAbortListener: (() => void) | undefined;
      let requestAbortListener: (() => void) | undefined;

      const cleanup = (): void => {
        options.target.removeEventListener("message", listener);
        removeAbortListener(options.abortSignal, optionAbortListener);
        removeAbortListener(requestOptions.abortSignal, requestAbortListener);
        if (timeout !== undefined) clearTimeout(timeout);
      };

      const settleResolve = (response: BrowserExtensionPageBridgeResponse): void => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve(response);
      };

      const settleReject = (error: unknown): void => {
        if (settled) return;
        settled = true;
        cleanup();
        reject(error);
      };

      const abort = (): void => {
        settleReject(new Error("browser page-window bridge request was cancelled"));
      };

      const listener: BrowserExtensionPageWindowMessageListener = (event) => {
        try {
          if (!isRecord(event)) return;
          if (event.source !== options.expectedSource) return;
          if (normalizeBrowserExtensionPageOrigin(event.origin) !== expectedOrigin) return;
          if (!responseCandidateMatches(event.data, bridgeRequest.request_id)) return;
          settleResolve(parseBrowserExtensionPageBridgeResponse(event.data, bridgeRequest.request_id));
        } catch (error) {
          settleReject(error);
        }
      };

      options.target.addEventListener("message", listener);
      optionAbortListener = abort;
      requestAbortListener = abort;
      options.abortSignal?.addEventListener("abort", optionAbortListener, { once: true });
      requestOptions.abortSignal?.addEventListener("abort", requestAbortListener, { once: true });
      if (responseTimeoutMs !== undefined) {
        timeout = setTimeout(() => {
          settleReject(new Error("browser page-window bridge response timed out"));
        }, responseTimeoutMs);
      }

      try {
        options.target.postMessage(bridgeRequest, expectedOrigin);
      } catch (error) {
        settleReject(error);
      }
    });
  };
}
