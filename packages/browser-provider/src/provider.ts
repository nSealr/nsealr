import {
  type EventTemplate,
  type SignEventRequest,
  type SignEventResponse,
  type SignedEvent,
  verifySignedEventResponse
} from "@nsealr/core";
import {
  LocalServiceClient,
  NATIVE_HOST_NAME,
  type LocalClientIdentity,
  type LocalServiceRequest,
  type LocalServiceResponse,
  type LocalServiceExchange
} from "@nsealr/client/browser";
import { validateRequest, validateResponse } from "@nsealr/protocol";

export { NATIVE_HOST_NAME } from "@nsealr/client/browser";

export type Nip07Provider = {
  getPublicKey(): Promise<string>;
  signEvent(eventTemplate: EventTemplate): Promise<SignedEvent>;
};

export type BrowserProviderBackend = {
  getPublicKey(client: LocalClientIdentity): Promise<unknown>;
  signEventRequest(request: SignEventRequest, client: LocalClientIdentity): Promise<unknown>;
};

export type BrowserProviderOptions = {
  backend: BrowserProviderBackend;
  client: LocalClientIdentity;
  nextRequestId?: () => string;
};

export type LocalServiceBrowserProviderBackendOptions = {
  service: Pick<LocalServiceClient, "selectAccountRoute" | "dispatchSignerRequest">;
  routeRequest: Extract<LocalServiceRequest, { operation: "select_account_route" }>["params"]["route_request"];
  signingUnavailableMessage?: string;
};

export type BrowserNativeMessageOptions = {
  abortSignal?: AbortSignal;
};

export type BrowserNativeMessageSender = (
  hostName: string,
  message: LocalServiceRequest,
  options: BrowserNativeMessageOptions
) => Promise<unknown> | unknown;

export type BrowserNativeMessagingLocalServiceClientOptions = {
  sendNativeMessage: BrowserNativeMessageSender;
  hostName?: string;
  nextRequestId?: () => string;
  timeoutMs?: number;
  abortSignal?: AbortSignal;
};

function defaultRequestIdFactory(): () => string {
  let sequence = 0;
  return () => {
    sequence += 1;
    return `nip07-sign-event-${sequence}`;
  };
}

function assertLowerHex(value: unknown, length: number, label: string): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(`${label} is invalid`);
  }
  if (!new RegExp(`^[0-9a-f]{${length}}$`, "u").test(value)) {
    throw new Error(`${label} is invalid`);
  }
}

function assertNativeHostName(value: string): void {
  if (!/^[a-z0-9_]+(?:\.[a-z0-9_]+)*$/u.test(value) || value.length > 128) {
    throw new Error("native host name is invalid");
  }
}

function signerRequestForTemplate(requestId: string, eventTemplate: EventTemplate): SignEventRequest {
  const request: SignEventRequest = {
    version: 1,
    request_id: requestId,
    method: "sign_event",
    params: {
      event_template: eventTemplate
    }
  };
  const validation = validateRequest(request);
  if (!validation.ok) {
    throw new Error(`NIP-07 signEvent input invalid: ${validation.error}`);
  }
  return request;
}

function signedEventFromResponse(request: SignEventRequest, response: unknown): SignedEvent {
  const validation = validateResponse(response);
  if (!validation.ok) {
    throw new Error(`NIP-07 signEvent response invalid: ${validation.error}`);
  }
  const typedResponse = response as SignEventResponse | {
    version: 1;
    request_id: string;
    ok: false;
    error: {
      code: string;
      message: string;
      retryable: boolean;
    };
  };
  if (typedResponse.request_id !== request.request_id) {
    throw new Error("NIP-07 signEvent response request_id does not match request");
  }
  if (typedResponse.ok === false) {
    throw new Error(`NIP-07 signEvent rejected: ${typedResponse.error.message}`);
  }
  const verification = verifySignedEventResponse(request, typedResponse);
  if (!verification.ok) {
    throw new Error(`NIP-07 signEvent response invalid: ${verification.error}`);
  }
  return typedResponse.result.event;
}

function localServiceErrorMessage(response: LocalServiceResponse, label: string): string {
  if (response.ok === false) {
    return `${label}: ${response.error.message}`;
  }
  return `${label}: unexpected local service result`;
}

function localServiceProtocolError(request: SignEventRequest, code: string, message: string): {
  version: 1;
  request_id: string;
  ok: false;
  error: {
    code: string;
    message: string;
    retryable: false;
  };
} {
  return {
    version: 1,
    request_id: request.request_id,
    ok: false,
    error: {
      code,
      message,
      retryable: false
    }
  };
}

export function createBrowserNativeMessagingLocalServiceClient(
  options: BrowserNativeMessagingLocalServiceClientOptions
): LocalServiceClient {
  const hostName = options.hostName ?? NATIVE_HOST_NAME;
  assertNativeHostName(hostName);
  const exchange: LocalServiceExchange = (request, exchangeOptions) => {
    return options.sendNativeMessage(hostName, request, {
      ...(exchangeOptions?.abortSignal !== undefined ? { abortSignal: exchangeOptions.abortSignal } : {})
    });
  };
  return new LocalServiceClient({
    exchange,
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.timeoutMs !== undefined ? { timeoutMs: options.timeoutMs } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
}

export function createLocalServiceBrowserProviderBackend(
  options: LocalServiceBrowserProviderBackendOptions
): BrowserProviderBackend {
  const unavailableMessage = options.signingUnavailableMessage ?? "Signer dispatch is not configured";
  return {
    async getPublicKey(client: LocalClientIdentity): Promise<string> {
      const response = await options.service.selectAccountRoute(client, options.routeRequest);
      if (response.ok !== true || !("route_selection" in response.result)) {
        throw new Error(localServiceErrorMessage(response, "NIP-07 route selection failed"));
      }
      return response.result.route_selection.public_key;
    },

    async signEventRequest(request: SignEventRequest, client: LocalClientIdentity): Promise<unknown> {
      const dispatchResponse = await options.service.dispatchSignerRequest(client, options.routeRequest, request);
      if (dispatchResponse.ok === true && "signer_response" in dispatchResponse.result) {
        return dispatchResponse.result.signer_response;
      }
      if (dispatchResponse.ok === false) {
        const code = dispatchResponse.error.code === "signer_route_unavailable"
          ? dispatchResponse.error.code
          : "local_service_dispatch_failed";
        return localServiceProtocolError(
          request,
          code,
          dispatchResponse.error.code === "signer_route_unavailable"
            ? unavailableMessage
            : dispatchResponse.error.message
        );
      }
      return localServiceProtocolError(request, "local_service_dispatch_failed", "local service dispatch returned an unexpected result");
    }
  };
}

export function createNip07Provider(options: BrowserProviderOptions): Nip07Provider {
  const nextRequestId = options.nextRequestId ?? defaultRequestIdFactory();
  return {
    async getPublicKey(): Promise<string> {
      const publicKey = await options.backend.getPublicKey(options.client);
      assertLowerHex(publicKey, 64, "NIP-07 public key");
      return publicKey;
    },

    async signEvent(eventTemplate: EventTemplate): Promise<SignedEvent> {
      const request = signerRequestForTemplate(nextRequestId(), eventTemplate);
      const response = await options.backend.signEventRequest(request, options.client);
      return signedEventFromResponse(request, response);
    }
  };
}
