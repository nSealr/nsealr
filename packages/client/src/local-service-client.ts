import { validateResponse } from "@nsealr/protocol";
import { parseRouteSelection } from "@nsealr/policy";
import {
  decodeNativeMessage,
  encodeNativeMessage,
  type NativeMessageFrameExchange
} from "./native-messaging.js";
import {
  LOCAL_SERVICE_NAME,
  LOCAL_SERVICE_OPERATIONS,
  LOCAL_SERVICE_PROTOCOL,
  parsePairingIntent,
  type LocalServiceOperation,
  type LocalServiceRequest,
  type LocalServiceResponse,
  type PairableLocalServiceOperation
} from "./service.js";
import {
  parseLocalClientIdentity,
  type LocalClientIdentity
} from "./client-identity.js";

export type LocalServiceExchangeOptions = {
  abortSignal?: AbortSignal;
};

export type LocalServiceExchange = (
  request: LocalServiceRequest,
  options?: LocalServiceExchangeOptions
) => Promise<unknown> | unknown;

export type LocalServiceClientOptions = {
  exchange: LocalServiceExchange;
  nextRequestId?: () => string;
  timeoutMs?: number;
  abortSignal?: AbortSignal;
};

export type NativeMessagingLocalServiceClientOptions = {
  exchange: NativeMessageFrameExchange;
  nextRequestId?: () => string;
  timeoutMs?: number;
  abortSignal?: AbortSignal;
};

export type LocalServiceDispatchSignerRequestOptions = {
  requestId?: string;
  externalReviewAcknowledgement?: Extract<
    LocalServiceRequest,
    { operation: "dispatch_signer_request" }
  >["params"]["external_review_acknowledgement"];
};

type RequestParams = Extract<LocalServiceRequest, { params: unknown }>["params"];
type LocalServiceResultKey = "service" | "pairing_intent" | "route_selection" | "validation" | "signer_response";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function isHex64(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/u.test(value);
}

function isLocalServiceOperation(value: unknown): value is LocalServiceOperation {
  return typeof value === "string" && LOCAL_SERVICE_OPERATIONS.includes(value as LocalServiceOperation);
}

function isPairableOperation(value: unknown): value is PairableLocalServiceOperation {
  return isLocalServiceOperation(value) && value !== "service_status" && value !== "request_pairing";
}

function isLocalClientIdentity(value: unknown): value is LocalClientIdentity {
  try {
    parseLocalClientIdentity(value);
    return true;
  } catch {
    return false;
  }
}

function defaultRequestIdFactory(): () => string {
  let sequence = 0;
  return () => {
    sequence += 1;
    return `local-client-${sequence}`;
  };
}

function assertTimeoutMs(value: number): void {
  if (!Number.isInteger(value) || value <= 0 || value > 300_000) {
    throw new Error("local service timeout must be a positive integer not greater than 300000");
  }
}

type LocalServiceBounds = {
  timeoutMs?: number;
  abortSignal?: AbortSignal;
};

async function withLocalServiceBounds<T>(operation: Promise<T>, bounds: LocalServiceBounds): Promise<T> {
  const timeoutMs = bounds.timeoutMs;
  const abortSignal = bounds.abortSignal;
  if (timeoutMs === undefined && abortSignal === undefined) return operation;
  if (timeoutMs !== undefined) assertTimeoutMs(timeoutMs);
  if (abortSignal?.aborted === true) {
    throw new Error("local service request was cancelled");
  }

  let timeout: ReturnType<typeof setTimeout> | undefined;
  let abortListener: (() => void) | undefined;
  const racers: Promise<T>[] = [operation];
  if (timeoutMs !== undefined) {
    racers.push(new Promise<T>((_resolve, reject) => {
      timeout = setTimeout(() => {
        reject(new Error("local service response timed out"));
      }, timeoutMs);
    }));
  }
  if (abortSignal !== undefined) {
    racers.push(new Promise<T>((_resolve, reject) => {
      abortListener = () => reject(new Error("local service request was cancelled"));
      abortSignal.addEventListener("abort", abortListener, { once: true });
    }));
  }
  try {
    return await Promise.race(racers);
  } finally {
    if (timeout !== undefined) clearTimeout(timeout);
    if (abortListener !== undefined) {
      abortSignal?.removeEventListener("abort", abortListener);
    }
  }
}

function validateRequestId(value: unknown, expectedRequestId: string): string | undefined {
  if (typeof value !== "string") return "local service response request_id is invalid";
  if (value !== expectedRequestId) return "local service response request_id does not match request";
  return undefined;
}

function validateServiceError(value: unknown): string | undefined {
  if (!isRecord(value)) return "local service error must be an object";
  if (!hasOnlyKeys(value, ["code", "message", "retryable"])) return "local service error has unsupported fields";
  if (typeof value.code !== "string" || value.code.length === 0) return "local service error code is invalid";
  if (typeof value.message !== "string" || value.message.length === 0) return "local service error message is invalid";
  if (value.retryable !== false) return "local service error retryable must be false";
  return undefined;
}

function validateRouteSelection(value: unknown): string | undefined {
  try {
    parseRouteSelection(value);
    return undefined;
  } catch (error) {
    return error instanceof Error
      ? `local service route selection is invalid: ${error.message}`
      : "local service route selection is invalid";
  }
}

function validateSignerResponseResult(value: unknown): string | undefined {
  const validation = validateResponse(value);
  return validation.ok ? undefined : `local service signer response is invalid: ${validation.error}`;
}

function validateServiceResult(value: unknown): string | undefined {
  if (!isRecord(value)) return "local service result must be an object";
  const resultTypes = ["service", "pairing_intent", "route_selection", "validation", "signer_response"].filter((key) => key in value);
  if (resultTypes.length !== 1 || !hasOnlyKeys(value, resultTypes)) {
    return "local service result type is unsupported";
  }
  if ("service" in value) {
    if (!isRecord(value.service)) return "local service status result is invalid";
    if (!hasOnlyKeys(value.service, ["protocol", "name", "operations", "requires_pairing", "stores_production_secrets"])) {
      return "local service status result has unsupported fields";
    }
    if (value.service.protocol !== LOCAL_SERVICE_PROTOCOL) return "local service protocol is invalid";
    if (value.service.name !== LOCAL_SERVICE_NAME) return "local service name is invalid";
    if (
      !Array.isArray(value.service.operations) ||
      value.service.operations.length !== LOCAL_SERVICE_OPERATIONS.length ||
      !value.service.operations.every((operation, index) => operation === LOCAL_SERVICE_OPERATIONS[index])
    ) {
      return "local service operations are invalid";
    }
    if (value.service.requires_pairing !== true) return "local service pairing requirement is invalid";
    if (value.service.stores_production_secrets !== false) return "local service secret-storage flag is invalid";
    return undefined;
  }
  if ("pairing_intent" in value) {
    if (!isRecord(value.pairing_intent)) return "local service pairing result is invalid";
    if (
      !hasOnlyKeys(value.pairing_intent, [
        "format",
        "client_id",
        "client",
        "requested_operations",
        "pairing_digest",
        "requires_user_approval",
        "stores_production_secrets"
      ])
    ) {
      return "local service pairing result has unsupported fields";
    }
    if (value.pairing_intent.format !== "nsealr-local-pairing-intent-v0") return "local service pairing format is invalid";
    if (!isHex64(value.pairing_intent.client_id)) return "local service pairing client_id is invalid";
    if (!isLocalClientIdentity(value.pairing_intent.client)) return "local service pairing client is invalid";
    if (
      !Array.isArray(value.pairing_intent.requested_operations) ||
      value.pairing_intent.requested_operations.length === 0 ||
      !value.pairing_intent.requested_operations.every(isPairableOperation) ||
      new Set(value.pairing_intent.requested_operations).size !== value.pairing_intent.requested_operations.length
    ) {
      return "local service pairing operations are invalid";
    }
    if (!isHex64(value.pairing_intent.pairing_digest)) return "local service pairing digest is invalid";
    if (value.pairing_intent.requires_user_approval !== true) return "local service pairing approval flag is invalid";
    if (value.pairing_intent.stores_production_secrets !== false) return "local service pairing secret-storage flag is invalid";
    try {
      parsePairingIntent(value.pairing_intent);
    } catch (error) {
      return error instanceof Error ? `local service pairing intent is invalid: ${error.message}` : "local service pairing intent is invalid";
    }
    return undefined;
  }
  if ("route_selection" in value) {
    return validateRouteSelection(value.route_selection);
  }
  if ("validation" in value) {
    if (!isRecord(value.validation)) return "local service validation result is invalid";
    if (!hasOnlyKeys(value.validation, ["valid", "error"])) return "local service validation result has unsupported fields";
    if (typeof value.validation.valid !== "boolean") return "local service validation flag is invalid";
    if ("error" in value.validation && typeof value.validation.error !== "string") {
      return "local service validation error is invalid";
    }
    return undefined;
  }
  if ("signer_response" in value) {
    return validateSignerResponseResult(value.signer_response);
  }
  return "local service result type is unsupported";
}

export function validateLocalServiceResponse(value: unknown, expectedRequestId: string): LocalServiceResponse {
  if (!isRecord(value)) throw new Error("local service response must be an object");
  if (value.version !== 1) throw new Error("local service response version must be 1");
  const requestIdError = validateRequestId(value.request_id, expectedRequestId);
  if (requestIdError !== undefined) throw new Error(requestIdError);
  if (value.ok === false) {
    if (!hasOnlyKeys(value, ["version", "request_id", "ok", "error"])) {
      throw new Error("local service error response has unsupported fields");
    }
    const error = validateServiceError(value.error);
    if (error !== undefined) throw new Error(error);
    return value as LocalServiceResponse;
  }
  if (value.ok === true) {
    if (!hasOnlyKeys(value, ["version", "request_id", "ok", "result"])) {
      throw new Error("local service success response has unsupported fields");
    }
    const error = validateServiceResult(value.result);
    if (error !== undefined) throw new Error(error);
    return value as LocalServiceResponse;
  }
  throw new Error("local service response ok flag is invalid");
}

function requireResultType(
  response: LocalServiceResponse,
  resultType: LocalServiceResultKey,
  operation: LocalServiceOperation
): LocalServiceResponse {
  if (response.ok === true && !(resultType in response.result)) {
    throw new Error(`${operation} returned unexpected local service result`);
  }
  return response;
}

export class LocalServiceClient {
  private readonly exchange: LocalServiceExchange;
  private readonly nextRequestId: () => string;
  private readonly timeoutMs: number | undefined;
  private readonly abortSignal: AbortSignal | undefined;

  constructor(options: LocalServiceClientOptions) {
    if (options.timeoutMs !== undefined) assertTimeoutMs(options.timeoutMs);
    this.exchange = options.exchange;
    this.nextRequestId = options.nextRequestId ?? defaultRequestIdFactory();
    this.timeoutMs = options.timeoutMs;
    this.abortSignal = options.abortSignal;
  }

  serviceStatus(requestId = this.nextRequestId()): Promise<LocalServiceResponse> {
    return this.send({
      version: 1,
      request_id: requestId,
      operation: "service_status"
    }).then((response) => requireResultType(response, "service", "service_status"));
  }

  requestPairing(
    client: LocalClientIdentity,
    requestedOperations: PairableLocalServiceOperation[],
    requestId = this.nextRequestId()
  ): Promise<LocalServiceResponse> {
    return this.sendWithParams("request_pairing", {
      client,
      requested_operations: requestedOperations
    }, requestId).then((response) => requireResultType(response, "pairing_intent", "request_pairing"));
  }

  validateSignerRequest(
    client: LocalClientIdentity,
    request: unknown,
    requestId = this.nextRequestId()
  ): Promise<LocalServiceResponse> {
    return this.sendWithParams("validate_signer_request", {
      client,
      request
    }, requestId).then((response) => requireResultType(response, "validation", "validate_signer_request"));
  }

  verifySignerResponse(
    client: LocalClientIdentity,
    request: unknown,
    response: unknown,
    requestId = this.nextRequestId()
  ): Promise<LocalServiceResponse> {
    return this.sendWithParams("verify_signer_response", {
      client,
      request,
      response
    }, requestId).then((localResponse) => requireResultType(localResponse, "validation", "verify_signer_response"));
  }

  selectAccountRoute(
    client: LocalClientIdentity,
    routeRequest: Extract<LocalServiceRequest, { operation: "select_account_route" }>["params"]["route_request"],
    requestId = this.nextRequestId()
  ): Promise<LocalServiceResponse> {
    return this.sendWithParams("select_account_route", {
      client,
      route_request: routeRequest
    }, requestId).then((response) => requireResultType(response, "route_selection", "select_account_route"));
  }

  dispatchSignerRequest(
    client: LocalClientIdentity,
    routeRequest: Extract<LocalServiceRequest, { operation: "dispatch_signer_request" }>["params"]["route_request"],
    request: unknown,
    options: LocalServiceDispatchSignerRequestOptions = {}
  ): Promise<LocalServiceResponse> {
    const requestId = options.requestId ?? this.nextRequestId();
    return this.sendWithParams("dispatch_signer_request", {
      client,
      route_request: routeRequest,
      request,
      ...(options.externalReviewAcknowledgement !== undefined
        ? { external_review_acknowledgement: options.externalReviewAcknowledgement }
        : {})
    }, requestId).then((response) => requireResultType(response, "signer_response", "dispatch_signer_request"));
  }

  private async send(request: LocalServiceRequest): Promise<LocalServiceResponse> {
    const bounds = {
      ...(this.timeoutMs !== undefined ? { timeoutMs: this.timeoutMs } : {}),
      ...(this.abortSignal !== undefined ? { abortSignal: this.abortSignal } : {})
    };
    if (this.abortSignal?.aborted === true) {
      throw new Error("local service request was cancelled");
    }
    const response = await withLocalServiceBounds(
      Promise.resolve(this.exchange(request, {
        ...(this.abortSignal !== undefined ? { abortSignal: this.abortSignal } : {})
      })),
      bounds
    );
    return validateLocalServiceResponse(response, request.request_id);
  }

  private sendWithParams(
    operation: Exclude<LocalServiceOperation, "service_status">,
    params: RequestParams,
    requestId: string
  ): Promise<LocalServiceResponse> {
    return this.send({
      version: 1,
      request_id: requestId,
      operation,
      params
    } as LocalServiceRequest);
  }
}

export function createNativeMessagingLocalServiceClient(
  options: NativeMessagingLocalServiceClientOptions
): LocalServiceClient {
  return new LocalServiceClient({
    nextRequestId: options.nextRequestId,
    ...(options.timeoutMs !== undefined ? { timeoutMs: options.timeoutMs } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    exchange: async (request) => decodeNativeMessage(await options.exchange(encodeNativeMessage(request)))
  });
}
