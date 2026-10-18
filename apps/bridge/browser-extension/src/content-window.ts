import {
  handleBrowserExtensionContentScriptBridgeMessage,
  type BrowserExtensionContentScriptBackgroundRequester
} from "./content-script.js";
import { browserExtensionErrorResponse } from "./messages.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  parseBrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import {
  normalizeBrowserExtensionPageOrigin,
  requireBrowserExtensionPageOrigin
} from "./page-origin.js";

export type BrowserExtensionContentWindowEvent = {
  data: unknown;
  origin: string;
  source: unknown;
};

export type BrowserExtensionContentWindowBridgeOptions = {
  expectedOrigin: string;
  expectedSource: unknown;
  sender: unknown;
  requestBackground: BrowserExtensionContentScriptBackgroundRequester;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionContentWindowMessageListener = (event: unknown) => void;

export type BrowserExtensionContentWindowEventTarget = {
  addEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
  removeEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
};

export type BrowserExtensionContentWindowResponseTarget = {
  source: unknown;
  origin: string;
};

export type BrowserExtensionContentWindowResponsePoster = (
  response: BrowserExtensionPageBridgeResponse,
  target: BrowserExtensionContentWindowResponseTarget
) => Promise<void> | void;

export type BrowserExtensionContentWindowListenerOptions = BrowserExtensionContentWindowBridgeOptions & {
  target: BrowserExtensionContentWindowEventTarget;
  postResponse: BrowserExtensionContentWindowResponsePoster;
  onError?: (error: unknown) => void;
};

export type BrowserExtensionContentWindowListenerHandle = {
  dispose(): void;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireExpectedPageOrigin(value: unknown): string {
  return requireBrowserExtensionPageOrigin(value, "browser content-window expected origin is invalid");
}

function requireResponseOrigin(value: unknown): string {
  return requireBrowserExtensionPageOrigin(value, "browser content-window response origin is invalid");
}

function requireResponsePostMessageTarget(value: unknown): {
  postMessage(message: BrowserExtensionPageBridgeResponse, targetOrigin: string): void;
} {
  if (!isRecord(value) || typeof value.postMessage !== "function") {
    throw new Error("browser content-window response target is invalid");
  }
  return value as {
    postMessage(message: BrowserExtensionPageBridgeResponse, targetOrigin: string): void;
  };
}

function isIncomingPageBridgeEnvelope(value: unknown): boolean {
  if (isRecord(value) && value.protocol === BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL) {
    return value.direction !== "extension_to_page";
  }
  return false;
}

export async function handleBrowserExtensionContentWindowBridgeEvent(
  event: unknown,
  options: BrowserExtensionContentWindowBridgeOptions
): Promise<BrowserExtensionPageBridgeResponse | undefined> {
  if (!isRecord(event)) throw new Error("browser content-window event must be an object");
  if (event.source !== options.expectedSource) return undefined;
  const expectedOrigin = requireExpectedPageOrigin(options.expectedOrigin);
  if (normalizeBrowserExtensionPageOrigin(event.origin) !== expectedOrigin) return undefined;
  if (!isIncomingPageBridgeEnvelope(event.data)) return undefined;
  return handleBrowserExtensionContentScriptBridgeMessage(event.data, {
    sender: options.sender,
    requestBackground: options.requestBackground,
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
}

function requireResponseTarget(event: unknown): BrowserExtensionContentWindowResponseTarget {
  if (!isRecord(event) || typeof event.origin !== "string") {
    throw new Error("browser content-window response target is invalid");
  }
  return {
    source: event.source,
    origin: event.origin
  };
}

export function createBrowserExtensionContentWindowResponsePoster(): BrowserExtensionContentWindowResponsePoster {
  return (response, target) => {
    requireResponsePostMessageTarget(target.source).postMessage(response, requireResponseOrigin(target.origin));
  };
}

function reportListenerError(error: unknown, onError: ((error: unknown) => void) | undefined): void {
  if (onError === undefined) return;
  try {
    onError(error);
  } catch {
    // Listener diagnostics must not create unhandled browser promise failures.
  }
}

function contentWindowBridgeFailureResponse(
  event: unknown,
  options: BrowserExtensionContentWindowBridgeOptions
): BrowserExtensionPageBridgeResponse | undefined {
  try {
    if (!isRecord(event)) return undefined;
    if (event.source !== options.expectedSource) return undefined;
    const expectedOrigin = requireExpectedPageOrigin(options.expectedOrigin);
    if (normalizeBrowserExtensionPageOrigin(event.origin) !== expectedOrigin) return undefined;
    if (!isIncomingPageBridgeEnvelope(event.data)) return undefined;
    const bridgeRequest = parseBrowserExtensionPageBridgeRequest(event.data);
    return {
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: bridgeRequest.request_id,
      response: browserExtensionErrorResponse(
        bridgeRequest.request_id,
        "content_window_bridge_failed",
        "browser content-window bridge request failed"
      )
    };
  } catch {
    return undefined;
  }
}

export function installBrowserExtensionContentWindowBridgeListener(
  options: BrowserExtensionContentWindowListenerOptions
): BrowserExtensionContentWindowListenerHandle {
  let disposed = false;
  const bridgeOptions: BrowserExtensionContentWindowBridgeOptions = {
    expectedOrigin: options.expectedOrigin,
    expectedSource: options.expectedSource,
    sender: options.sender,
    requestBackground: options.requestBackground,
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  };
  const listener: BrowserExtensionContentWindowMessageListener = (event) => {
    void (async () => {
      try {
        const response = await handleBrowserExtensionContentWindowBridgeEvent(event, bridgeOptions);
        if (response === undefined || disposed) return;
        await options.postResponse(response, requireResponseTarget(event));
      } catch (error) {
        reportListenerError(error, options.onError);
        if (disposed) return;
        const response = contentWindowBridgeFailureResponse(event, bridgeOptions);
        if (response === undefined) return;
        try {
          await options.postResponse(response, requireResponseTarget(event));
        } catch (responseError) {
          reportListenerError(responseError, options.onError);
        }
      }
    })();
  };
  options.target.addEventListener("message", listener);
  return Object.freeze({
    dispose(): void {
      if (disposed) return;
      disposed = true;
      options.target.removeEventListener("message", listener);
    }
  });
}
