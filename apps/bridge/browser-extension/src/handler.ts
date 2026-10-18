import { type Nip07Provider } from "@nsealr/browser-provider";
import { type SignEventRequest, type SignedEvent, verifySignedEventResponse } from "@nsealr/core";
import { validateResponse } from "@nsealr/protocol";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  type BrowserExtensionErrorResponse,
  type BrowserExtensionRequest,
  browserExtensionErrorResponse,
  isBrowserExtensionRequestId,
  parseBrowserExtensionRequest
} from "./messages.js";
import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionClientContext
} from "./sender.js";
import { isBrowserExtensionOriginMethodAllowed } from "./origin-permission-store.js";

export { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./messages.js";

export type BrowserExtensionSuccessResponse =
  | {
      protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
      version: 1;
      request_id: string;
      ok: true;
      result: {
        pubkey: string;
      };
    }
  | {
      protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
      version: 1;
      request_id: string;
      ok: true;
      result: {
        event: SignedEvent;
      };
    };

export type BrowserExtensionResponse = BrowserExtensionSuccessResponse | BrowserExtensionErrorResponse;

export type BrowserExtensionHandlerOptions = {
  provider: Pick<Nip07Provider, "getPublicKey" | "signEvent">;
};

export type BrowserExtensionSenderHandlerOptions = {
  providerForClient: (context: BrowserExtensionClientContext) => BrowserExtensionHandlerOptions["provider"];
  originPermissions?: BrowserExtensionOriginPermissionAuthorization;
};

export type BrowserExtensionOriginPermissionAuthorization = {
  store: unknown;
  localPairingDigest: string;
} | {
  loadStore(): Promise<unknown> | unknown;
  localPairingDigest: string;
};

type BrowserExtensionStaticOriginPermissionAuthorization = Extract<
  BrowserExtensionOriginPermissionAuthorization,
  { store: unknown }
>;

type BrowserExtensionLoadedOriginPermissionAuthorization = Extract<
  BrowserExtensionOriginPermissionAuthorization,
  { loadStore(): Promise<unknown> | unknown }
>;

const FALLBACK_REQUEST_ID = "invalid-browser-extension-request";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fallbackRequestId(value: unknown): string {
  if (isRecord(value) && isBrowserExtensionRequestId(value.request_id)) {
    return value.request_id;
  }
  return FALLBACK_REQUEST_ID;
}

function errorResponse(requestId: string, code: string, message: string): BrowserExtensionErrorResponse {
  return browserExtensionErrorResponse(requestId, code, message);
}

function assertPublicKey(value: unknown): asserts value is string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error("provider returned invalid public key");
  }
}

function signerRequestFromExtensionRequest(request: Extract<BrowserExtensionRequest, { method: "sign_event" }>): SignEventRequest {
  return {
    version: 1,
    request_id: request.request_id,
    method: "sign_event",
    params: {
      event_template: request.params.event_template
    }
  };
}

function assertSignedEventResponse(request: SignEventRequest, event: SignedEvent): void {
  const response = {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      event
    }
  };
  const validation = validateResponse(response);
  if (!validation.ok) {
    throw new Error(`provider returned invalid signed event: ${validation.error}`);
  }
  const verification = verifySignedEventResponse(request, response);
  if (!verification.ok) {
    throw new Error(`provider returned invalid signed event: ${verification.error}`);
  }
}

async function handleGetPublicKey(
  request: Extract<BrowserExtensionRequest, { method: "get_public_key" }>,
  provider: BrowserExtensionHandlerOptions["provider"]
): Promise<BrowserExtensionResponse> {
  try {
    const pubkey = await provider.getPublicKey();
    assertPublicKey(pubkey);
    return {
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: request.request_id,
      ok: true,
      result: {
        pubkey
      }
    };
  } catch {
    return errorResponse(request.request_id, "provider_request_failed", "browser provider get_public_key failed");
  }
}

async function handleSignEvent(
  request: Extract<BrowserExtensionRequest, { method: "sign_event" }>,
  provider: BrowserExtensionHandlerOptions["provider"]
): Promise<BrowserExtensionResponse> {
  try {
    const event = await provider.signEvent(request.params.event_template);
    assertSignedEventResponse(signerRequestFromExtensionRequest(request), event);
    return {
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: request.request_id,
      ok: true,
      result: {
        event
      }
    };
  } catch {
    return errorResponse(request.request_id, "provider_request_failed", "browser provider sign_event failed");
  }
}

export async function handleBrowserExtensionRequest(
  value: unknown,
  options: BrowserExtensionHandlerOptions
): Promise<BrowserExtensionResponse> {
  const requestId = fallbackRequestId(value);
  let request: BrowserExtensionRequest;
  try {
    request = parseBrowserExtensionRequest(value);
  } catch {
    return errorResponse(requestId, "invalid_request", "browser extension request is invalid");
  }

  return handleParsedBrowserExtensionRequest(request, options.provider);
}

async function handleParsedBrowserExtensionRequest(
  request: BrowserExtensionRequest,
  provider: BrowserExtensionHandlerOptions["provider"]
): Promise<BrowserExtensionResponse> {
  if (request.method === "get_public_key") {
    return handleGetPublicKey(request, provider);
  }
  return handleSignEvent(request, provider);
}

function hasOwnKey(value: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function hasStaticOriginPermissionStore(
  authorization: BrowserExtensionOriginPermissionAuthorization
): authorization is BrowserExtensionStaticOriginPermissionAuthorization {
  return hasOwnKey(authorization, "store");
}

function hasLoadedOriginPermissionStore(
  authorization: BrowserExtensionOriginPermissionAuthorization
): authorization is BrowserExtensionLoadedOriginPermissionAuthorization {
  return hasOwnKey(authorization, "loadStore");
}

async function originPermissionStore(
  authorization: BrowserExtensionOriginPermissionAuthorization
): Promise<unknown> {
  const hasStaticStore = hasStaticOriginPermissionStore(authorization);
  const hasStoreLoader = hasLoadedOriginPermissionStore(authorization);
  if (hasStaticStore === hasStoreLoader) {
    throw new Error("browser extension origin permission authorization source is invalid");
  }
  if (hasStaticStore) return authorization.store;
  if (typeof authorization.loadStore !== "function") {
    throw new Error("browser extension origin permission store loader is invalid");
  }
  return authorization.loadStore();
}

async function assertOriginPermission(
  request: BrowserExtensionRequest,
  context: BrowserExtensionClientContext,
  authorization: BrowserExtensionOriginPermissionAuthorization | undefined
): Promise<boolean> {
  if (authorization === undefined) return true;
  return isBrowserExtensionOriginMethodAllowed(await originPermissionStore(authorization), {
    origin: context.client.origin,
    extensionId: context.extension_id,
    localPairingDigest: authorization.localPairingDigest,
    method: request.method
  });
}

export async function handleBrowserExtensionSenderRequest(
  value: unknown,
  sender: unknown,
  options: BrowserExtensionSenderHandlerOptions
): Promise<BrowserExtensionResponse> {
  const requestId = fallbackRequestId(value);
  let request: BrowserExtensionRequest;
  let context: BrowserExtensionClientContext;
  try {
    request = parseBrowserExtensionRequest(value);
  } catch {
    return errorResponse(requestId, "invalid_request", "browser extension request is invalid");
  }
  try {
    context = browserExtensionClientContextFromSender(sender);
  } catch {
    return errorResponse(requestId, "invalid_sender", "browser extension sender is invalid");
  }
  try {
    if (!await assertOriginPermission(request, context, options.originPermissions)) {
      return errorResponse(request.request_id, "origin_permission_denied", "browser extension origin permission denied");
    }
  } catch {
    return errorResponse(request.request_id, "origin_permission_denied", "browser extension origin permission denied");
  }
  try {
    return handleParsedBrowserExtensionRequest(request, options.providerForClient(context));
  } catch {
    return errorResponse(request.request_id, "provider_selection_failed", "browser extension provider selection failed");
  }
}
