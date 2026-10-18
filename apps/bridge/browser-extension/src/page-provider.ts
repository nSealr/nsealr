import {
  type EventTemplate,
  type SignEventRequest,
  type SignEventResponse,
  type SignedEvent,
  verifySignedEventResponse
} from "@nsealr/core";
import { type Nip07Provider } from "@nsealr/browser-provider";
import { validateResponse } from "@nsealr/protocol";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  isBrowserExtensionRequestId,
  parseBrowserExtensionRequest,
  type BrowserExtensionRequest
} from "./messages.js";

export type BrowserExtensionPageProvider = Nip07Provider;

export type BrowserExtensionPageRequestOptions = {
  abortSignal?: AbortSignal;
};

export type BrowserExtensionBackgroundRequester = (
  request: BrowserExtensionRequest,
  options: BrowserExtensionPageRequestOptions
) => Promise<unknown> | unknown;

export type BrowserExtensionPageProviderOptions = {
  requestBackground: BrowserExtensionBackgroundRequester;
  nextRequestId?: () => string;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionPageProviderTarget = {
  nostr?: unknown;
};

function defaultRequestIdFactory(): () => string {
  let sequence = 0;
  return () => {
    sequence += 1;
    return `browser-page-${sequence}`;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireResponseEnvelope(value: unknown, requestId: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error("browser extension response must be an object");
  if (value.protocol !== BROWSER_EXTENSION_MESSAGE_PROTOCOL) {
    throw new Error("browser extension response protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser extension response version is unsupported");
  }
  if (!isBrowserExtensionRequestId(value.request_id) || value.request_id !== requestId) {
    throw new Error("browser extension response request_id does not match request");
  }
  return value;
}

function rejectErrorResponse(value: Record<string, unknown>): void {
  if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "ok", "error"])) {
    throw new Error("browser extension error response has unsupported fields");
  }
  if (!isRecord(value.error)) throw new Error("browser extension error response is invalid");
  if (!hasOnlyKeys(value.error, ["code", "message", "retryable"])) {
    throw new Error("browser extension error response has unsupported error fields");
  }
  if (typeof value.error.code !== "string" || !/^[a-z0-9_:-]{1,64}$/u.test(value.error.code)) {
    throw new Error("browser extension error response code is invalid");
  }
  if (typeof value.error.message !== "string" || value.error.message.length === 0) {
    throw new Error("browser extension error response message is invalid");
  }
  if (value.error.retryable !== false) {
    throw new Error("browser extension error response retryable flag is invalid");
  }
  throw new Error(`browser extension request failed: ${value.error.message}`);
}

function requireSuccessResult(value: unknown, requestId: string): Record<string, unknown> {
  const envelope = requireResponseEnvelope(value, requestId);
  if (envelope.ok === false) {
    rejectErrorResponse(envelope);
  }
  if (envelope.ok !== true) throw new Error("browser extension response ok flag is invalid");
  if (!hasOnlyKeys(envelope, ["protocol", "version", "request_id", "ok", "result"])) {
    throw new Error("browser extension success response has unsupported fields");
  }
  if (!isRecord(envelope.result)) throw new Error("browser extension success result is invalid");
  return envelope.result;
}

function requirePublicKey(value: unknown, requestId: string): string {
  const result = requireSuccessResult(value, requestId);
  if (!hasOnlyKeys(result, ["pubkey"])) {
    throw new Error("browser extension public-key response has unsupported fields");
  }
  if (typeof result.pubkey !== "string" || !/^[0-9a-f]{64}$/u.test(result.pubkey)) {
    throw new Error("browser extension public-key response is invalid");
  }
  return result.pubkey;
}

function signerRequestFromTemplate(requestId: string, eventTemplate: EventTemplate): SignEventRequest {
  return {
    version: 1,
    request_id: requestId,
    method: "sign_event",
    params: {
      event_template: eventTemplate
    }
  };
}

function requireSignedEvent(value: unknown, request: SignEventRequest): SignedEvent {
  const result = requireSuccessResult(value, request.request_id);
  if (!hasOnlyKeys(result, ["event"])) {
    throw new Error("browser extension signed-event response has unsupported fields");
  }
  const response: SignEventResponse = {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      event: result.event as SignedEvent
    }
  };
  const validation = validateResponse(response);
  if (!validation.ok) {
    throw new Error(`browser extension signed-event response is invalid: ${validation.error}`);
  }
  const verification = verifySignedEventResponse(request, response);
  if (!verification.ok) {
    throw new Error(`browser extension signed-event response is invalid: ${verification.error}`);
  }
  return response.result.event;
}

function assertNotCancelled(abortSignal: AbortSignal | undefined): void {
  if (abortSignal?.aborted === true) {
    throw new Error("browser extension page request was cancelled");
  }
}

export function createBrowserExtensionPageProvider(
  options: BrowserExtensionPageProviderOptions
): BrowserExtensionPageProvider {
  const nextRequestId = options.nextRequestId ?? defaultRequestIdFactory();
  return Object.freeze({
    async getPublicKey(): Promise<string> {
      assertNotCancelled(options.abortSignal);
      const request = parseBrowserExtensionRequest({
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: nextRequestId(),
        method: "get_public_key"
      });
      const response = await options.requestBackground(request, {
        ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
      });
      return requirePublicKey(response, request.request_id);
    },

    async signEvent(eventTemplate: EventTemplate): Promise<SignedEvent> {
      assertNotCancelled(options.abortSignal);
      const requestId = nextRequestId();
      const signerRequest = signerRequestFromTemplate(requestId, eventTemplate);
      const request = parseBrowserExtensionRequest({
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: requestId,
        method: "sign_event",
        params: {
          event_template: signerRequest.params.event_template
        }
      });
      const response = await options.requestBackground(request, {
        ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
      });
      return requireSignedEvent(response, signerRequest);
    }
  });
}

export function installBrowserExtensionPageProvider(
  target: BrowserExtensionPageProviderTarget,
  provider: BrowserExtensionPageProvider
): BrowserExtensionPageProvider {
  if (target.nostr !== undefined) {
    throw new Error("browser page already has a nostr provider");
  }
  Object.defineProperty(target, "nostr", {
    value: provider,
    enumerable: true,
    configurable: false,
    writable: false
  });
  return provider;
}
