import { type EventTemplate, type SignEventRequest } from "@nsealr/core";
import { NSEALR_V0_LIMITS, validateRequest } from "@nsealr/protocol";

export const BROWSER_EXTENSION_MESSAGE_PROTOCOL = "nsealr-browser-extension-v0";

export type BrowserExtensionMethod = "get_public_key" | "sign_event";

export type BrowserExtensionRequest =
  | {
      protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
      version: 1;
      request_id: string;
      method: "get_public_key";
    }
  | {
      protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
      version: 1;
      request_id: string;
      method: "sign_event";
      params: {
        event_template: EventTemplate;
      };
    };

export type BrowserExtensionErrorResponse = {
  protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
  version: 1;
  request_id: string;
  ok: false;
  error: {
    code: string;
    message: string;
    retryable: false;
  };
};

const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]+$/u;

export function isBrowserExtensionRequestId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    REQUEST_ID_PATTERN.test(value) &&
    value.length <= NSEALR_V0_LIMITS.max_request_id_length
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireRequestId(value: unknown): string {
  if (!isBrowserExtensionRequestId(value)) {
    throw new Error("browser extension request_id is invalid");
  }
  return value;
}

function requireErrorCode(value: unknown): string {
  if (typeof value !== "string" || !/^[a-z0-9_:-]{1,64}$/u.test(value)) {
    throw new Error("browser extension error code is invalid");
  }
  return value;
}

function requireErrorMessage(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 512) {
    throw new Error("browser extension error message is invalid");
  }
  return value;
}

function signEventTemplate(requestId: string, value: unknown): EventTemplate {
  if (!isRecord(value)) throw new Error("browser extension sign_event params must be an object");
  if (!hasOnlyKeys(value, ["event_template"])) {
    throw new Error("browser extension sign_event params have unsupported fields");
  }
  const request: SignEventRequest = {
    version: 1,
    request_id: requestId,
    method: "sign_event",
    params: {
      event_template: value.event_template as EventTemplate
    }
  };
  const validation = validateRequest(request);
  if (!validation.ok) {
    throw new Error(`browser extension sign_event request is invalid: ${validation.error}`);
  }
  return request.params.event_template;
}

export function parseBrowserExtensionRequest(value: unknown): BrowserExtensionRequest {
  if (!isRecord(value)) throw new Error("browser extension request must be an object");
  if (!hasOnlyKeys(value, ["protocol", "version", "request_id", "method", "params"])) {
    throw new Error("browser extension request has unsupported fields");
  }
  if (value.protocol !== BROWSER_EXTENSION_MESSAGE_PROTOCOL) {
    throw new Error("browser extension request protocol is unsupported");
  }
  if (value.version !== 1) {
    throw new Error("browser extension request version is unsupported");
  }
  const requestId = requireRequestId(value.request_id);
  if (value.method === "get_public_key") {
    if ("params" in value) {
      throw new Error("browser extension get_public_key must not include params");
    }
    return {
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: requestId,
      method: "get_public_key"
    };
  }
  if (value.method === "sign_event") {
    return {
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: requestId,
      method: "sign_event",
      params: {
        event_template: signEventTemplate(requestId, value.params)
      }
    };
  }
  throw new Error("browser extension request method is unsupported");
}

export function browserExtensionErrorResponse(
  requestId: string,
  code: string,
  message: string
): BrowserExtensionErrorResponse {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requireRequestId(requestId),
    ok: false,
    error: {
      code: requireErrorCode(code),
      message: requireErrorMessage(message),
      retryable: false
    }
  };
}
