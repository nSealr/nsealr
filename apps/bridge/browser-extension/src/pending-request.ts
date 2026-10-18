import {
  isBrowserExtensionRequestId,
  type BrowserExtensionMethod,
  type BrowserExtensionRequest
} from "./messages.js";
import {
  parseRouteSelectionRequest,
  type RouteSelectionRequest
} from "@nsealr/policy";
import {
  requireBrowserExtensionDispatchableRouteType,
  type BrowserExtensionDispatchableRouteType
} from "./route-config.js";
import { requireBrowserExtensionPageOrigin } from "./page-origin.js";
import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionSenderInput
} from "./sender.js";

export const BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT =
  "nsealr-browser-extension-pending-request-state-v0";
export const BROWSER_EXTENSION_MAX_ACTIVE_PENDING_REQUESTS = 16;

export type BrowserExtensionPendingRequestStatus = "pending" | "resolved" | "rejected" | "cancelled";
export type BrowserExtensionPendingRequestSettledStatus = "resolved" | "rejected";

export type BrowserExtensionPendingRequestState = {
  format: typeof BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT;
  request_id: string;
  method: BrowserExtensionRequest["method"];
  extension_id: string;
  page_origin: string;
  app_name?: string;
  route_account_id?: string;
  route_type?: BrowserExtensionDispatchableRouteType;
  status: BrowserExtensionPendingRequestStatus;
  started_at: number;
  updated_at: number;
  stores_production_secrets: false;
  includes_event_template: false;
};

export type BrowserExtensionPendingRequestLifecycle = {
  start(request: BrowserExtensionRequest, sender: BrowserExtensionSenderInput): BrowserExtensionPendingRequestState;
  settle(
    state: BrowserExtensionPendingRequestState,
    status: BrowserExtensionPendingRequestSettledStatus
  ): BrowserExtensionPendingRequestState;
  cancel(requestId: string): BrowserExtensionPendingRequestState | undefined;
  abortSignal(state: BrowserExtensionPendingRequestState): AbortSignal | undefined;
  active(): readonly BrowserExtensionPendingRequestState[];
};

export type BrowserExtensionPendingRequestLifecycleOptions = {
  now?: () => number;
  onState?: (state: BrowserExtensionPendingRequestState) => void;
  maxActiveRequests?: number;
  routeRequest?: Pick<RouteSelectionRequest, "account_id" | "route_type">;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireNonNegativeSafeInteger(value: number, label: string): number {
  if (!Number.isInteger(value) || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function requirePositiveSafeInteger(value: number, label: string): number {
  if (!Number.isInteger(value) || !Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${label} must be a positive safe integer`);
  }
  return value;
}

function requirePendingExtensionId(value: unknown): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._@+-]{1,128}$/u.test(value)) {
    throw new Error("browser extension pending request extension_id is invalid");
  }
  return value;
}

function requirePendingAppName(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 80) {
    throw new Error("browser extension pending request app_name is invalid");
  }
  return value;
}

function requirePendingRequestMethod(value: unknown): BrowserExtensionMethod {
  if (value !== "get_public_key" && value !== "sign_event") {
    throw new Error("browser extension pending request method is invalid");
  }
  return value;
}

function requirePendingRequestStatus(value: unknown): BrowserExtensionPendingRequestStatus {
  if (
    value !== "pending" &&
    value !== "resolved" &&
    value !== "rejected" &&
    value !== "cancelled"
  ) {
    throw new Error("browser extension pending request status is invalid");
  }
  return value;
}

function pendingRouteSummary(
  routeRequest: BrowserExtensionPendingRequestLifecycleOptions["routeRequest"] | undefined
): Pick<BrowserExtensionPendingRequestState, "route_account_id" | "route_type"> {
  if (routeRequest === undefined) return {};
  const routeType = requireBrowserExtensionDispatchableRouteType(routeRequest.route_type);
  const parsed = parseRouteSelectionRequest({
    account_id: routeRequest.account_id,
    method: "sign_event",
    route_type: routeType
  });
  return {
    route_account_id: parsed.account_id,
    route_type: routeType
  };
}

function pendingRouteSummaryFromState(
  value: Record<string, unknown>
): Pick<BrowserExtensionPendingRequestState, "route_account_id" | "route_type"> {
  if (value.route_account_id === undefined) {
    if (value.route_type !== undefined) {
      throw new Error("browser extension pending request route_account_id is required");
    }
    return {};
  }
  if (value.route_type === undefined) {
    throw new Error("browser extension pending request route_type is required");
  }
  return pendingRouteSummary({
    account_id: value.route_account_id as string,
    route_type: value.route_type as RouteSelectionRequest["route_type"]
  });
}

function emitState(
  onState: ((state: BrowserExtensionPendingRequestState) => void) | undefined,
  state: BrowserExtensionPendingRequestState
): BrowserExtensionPendingRequestState {
  onState?.(state);
  return state;
}

export function parseBrowserExtensionPendingRequestState(
  value: unknown
): BrowserExtensionPendingRequestState {
  if (!isRecord(value)) {
    throw new Error("browser extension pending request state must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "request_id",
    "method",
    "extension_id",
    "page_origin",
    "app_name",
    "route_account_id",
    "route_type",
    "status",
    "started_at",
    "updated_at",
    "stores_production_secrets",
    "includes_event_template"
  ])) {
    throw new Error("browser extension pending request state has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT) {
    throw new Error("browser extension pending request state format is unsupported");
  }
  if (!isBrowserExtensionRequestId(value.request_id)) {
    throw new Error("browser extension pending request state request_id is invalid");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension pending request state must not store production secrets");
  }
  if (value.includes_event_template !== false) {
    throw new Error("browser extension pending request state must not include event templates");
  }
  return Object.freeze({
    format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
    request_id: value.request_id,
    method: requirePendingRequestMethod(value.method),
    extension_id: requirePendingExtensionId(value.extension_id),
    page_origin: requireBrowserExtensionPageOrigin(
      value.page_origin,
      "browser extension pending request page_origin is invalid"
    ),
    ...(value.app_name !== undefined
      ? { app_name: requirePendingAppName(value.app_name) }
      : {}),
    ...pendingRouteSummaryFromState(value),
    status: requirePendingRequestStatus(value.status),
    started_at: requireNonNegativeSafeInteger(
      value.started_at as number,
      "browser extension pending request started_at"
    ),
    updated_at: requireNonNegativeSafeInteger(
      value.updated_at as number,
      "browser extension pending request updated_at"
    ),
    stores_production_secrets: false,
    includes_event_template: false
  });
}

export function createBrowserExtensionPendingRequestLifecycle(
  options: BrowserExtensionPendingRequestLifecycleOptions = {}
): BrowserExtensionPendingRequestLifecycle {
  const active = new Map<string, BrowserExtensionPendingRequestState>();
  const abortControllers = new Map<string, AbortController>();
  const now = options.now ?? Date.now;
  const maxActiveRequests = requirePositiveSafeInteger(
    options.maxActiveRequests ?? BROWSER_EXTENSION_MAX_ACTIVE_PENDING_REQUESTS,
    "browser extension pending request maxActiveRequests"
  );
  const routeSummary = pendingRouteSummary(options.routeRequest);

  function stateWithStatus(
    state: BrowserExtensionPendingRequestState,
    status: Exclude<BrowserExtensionPendingRequestStatus, "pending">
  ): BrowserExtensionPendingRequestState {
    const timestamp = requireNonNegativeSafeInteger(now(), "browser extension pending request timestamp");
    return Object.freeze({
      ...state,
      status,
      updated_at: timestamp
    });
  }

  return Object.freeze({
    start(request: BrowserExtensionRequest, sender: BrowserExtensionSenderInput): BrowserExtensionPendingRequestState {
      if (active.has(request.request_id)) {
        throw new Error("browser extension pending request id is already active");
      }
      if (active.size >= maxActiveRequests) {
        throw new Error("browser extension pending request active limit reached");
      }
      const context = browserExtensionClientContextFromSender(sender);
      const timestamp = requireNonNegativeSafeInteger(now(), "browser extension pending request timestamp");
      const state = Object.freeze({
        format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
        request_id: request.request_id,
        method: request.method,
        extension_id: context.extension_id,
        page_origin: context.page_origin,
        ...(context.client.app_name !== undefined ? { app_name: context.client.app_name } : {}),
        ...routeSummary,
        status: "pending" as const,
        started_at: timestamp,
        updated_at: timestamp,
        stores_production_secrets: false as const,
        includes_event_template: false as const
      });
      const abortController = new AbortController();
      active.set(state.request_id, state);
      abortControllers.set(state.request_id, abortController);
      try {
        return emitState(options.onState, state);
      } catch (error) {
        active.delete(state.request_id);
        abortControllers.delete(state.request_id);
        throw error;
      }
    },

    settle(
      state: BrowserExtensionPendingRequestState,
      status: BrowserExtensionPendingRequestSettledStatus
    ): BrowserExtensionPendingRequestState {
      if (active.get(state.request_id) !== state) {
        return state;
      }
      const settled = stateWithStatus(state, status);
      active.delete(state.request_id);
      abortControllers.delete(state.request_id);
      return emitState(options.onState, settled);
    },

    cancel(requestId: string): BrowserExtensionPendingRequestState | undefined {
      const state = active.get(requestId);
      if (state === undefined) return undefined;
      const controller = abortControllers.get(requestId);
      controller?.abort();
      const cancelled = stateWithStatus(state, "cancelled");
      active.delete(requestId);
      abortControllers.delete(requestId);
      return emitState(options.onState, cancelled);
    },

    abortSignal(state: BrowserExtensionPendingRequestState): AbortSignal | undefined {
      return abortControllers.get(state.request_id)?.signal;
    },

    active(): readonly BrowserExtensionPendingRequestState[] {
      return Object.freeze(Array.from(active.values()));
    }
  });
}
