import {
  parseRouteSelectionRequest,
  type RouteSelectionRequest
} from "@nsealr/policy";
import { sha256Utf8Hex } from "@nsealr/core";

export const BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT = "nsealr-browser-extension-route-config-v0";
export const BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT = "nsealr-browser-extension-route-config-review-v0";
export const BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT = "nsealr-browser-extension-route-config-approval-v0";
export const BROWSER_EXTENSION_ROUTE_CONFIG_METHOD = "sign_event";
export type BrowserExtensionDispatchableRouteType =
  | "esp32_usb_nip46"
  | "custom_hardware_wallet"
  | "external_nip46";
const BROWSER_EXTENSION_ROUTE_CONFIG_ROUTE_TYPES = new Set([
  "esp32_usb_nip46",
  "custom_hardware_wallet",
  "external_nip46"
]);
export type BrowserExtensionRouteRequest = RouteSelectionRequest & {
  route_type: BrowserExtensionDispatchableRouteType;
};

export type BrowserExtensionRouteConfig = {
  format: typeof BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT;
  account_id: string;
  route_type: BrowserExtensionDispatchableRouteType;
};

export type BrowserExtensionParsedRouteConfig = {
  format: typeof BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT;
  route_config: BrowserExtensionRouteConfig;
  route_request: BrowserExtensionRouteRequest;
  stores_production_secrets: false;
};

export type BrowserExtensionRouteConfigReview = {
  format: typeof BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT;
  route_config_digest: string;
  route_config: BrowserExtensionRouteConfig;
  route_request: BrowserExtensionRouteRequest;
  requires_user_approval: true;
  writes_extension_storage: false;
  creates_grants: false;
  dispatches_signers: false;
  stores_production_secrets: false;
};

export type BrowserExtensionRouteConfigApproval = {
  format: typeof BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT;
  route_config_digest: string;
  approved_at: number;
  review: BrowserExtensionRouteConfigReview;
  requires_user_approval: true;
  writes_extension_storage: false;
  creates_grants: false;
  dispatches_signers: false;
  stores_production_secrets: false;
};

export type BrowserExtensionRouteConfigApprovalOptions = {
  reviewedRouteConfigDigest: string;
  approvedAt: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireNonNegativeSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function routeRequestsEqual(left: RouteSelectionRequest, right: RouteSelectionRequest): boolean {
  return left.account_id === right.account_id
    && left.method === right.method
    && left.route_type === right.route_type;
}

export function requireBrowserExtensionDispatchableRouteType(
  value: unknown
): BrowserExtensionDispatchableRouteType {
  if (typeof value !== "string") {
    throw new Error("browser extension route config route_type is required");
  }
  const routeType = parseRouteSelectionRequest({
    account_id: "browser-extension-route-config-validation",
    method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
    route_type: value
  }).route_type;
  if (routeType === undefined || !BROWSER_EXTENSION_ROUTE_CONFIG_ROUTE_TYPES.has(routeType)) {
    throw new Error("browser extension route config route_type is not browser-dispatchable");
  }
  return routeType as BrowserExtensionDispatchableRouteType;
}

export function normalizeBrowserExtensionRouteConfig(value: unknown): BrowserExtensionRouteConfig {
  if (!isRecord(value)) throw new Error("browser extension route config must be an object");
  if (!hasOnlyKeys(value, ["format", "account_id", "route_type"])) {
    throw new Error("browser extension route config has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT) {
    throw new Error("browser extension route config format is unsupported");
  }
  const routeType = requireBrowserExtensionDispatchableRouteType(value.route_type);
  const routeRequest = parseRouteSelectionRequest({
    account_id: value.account_id,
    method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
    route_type: routeType
  });
  return Object.freeze({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    account_id: routeRequest.account_id,
    route_type: routeType
  });
}

export function browserExtensionRouteConfigDigest(routeConfig: unknown): string {
  const normalized = normalizeBrowserExtensionRouteConfig(routeConfig);
  return sha256Utf8Hex(JSON.stringify(normalized));
}

export function parseBrowserExtensionRouteConfig(value: unknown): BrowserExtensionParsedRouteConfig {
  const routeConfig = normalizeBrowserExtensionRouteConfig(value);
  const routeRequest = parseRouteSelectionRequest({
    account_id: routeConfig.account_id,
    method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
    route_type: routeConfig.route_type
  });
  return Object.freeze({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    route_config: routeConfig,
    route_request: {
      ...routeRequest,
      route_type: routeConfig.route_type
    },
    stores_production_secrets: false
  });
}

export function createBrowserExtensionRouteConfigReview(routeConfig: unknown): BrowserExtensionRouteConfigReview {
  const parsed = parseBrowserExtensionRouteConfig(routeConfig);
  return Object.freeze({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT,
    route_config_digest: browserExtensionRouteConfigDigest(parsed.route_config),
    route_config: parsed.route_config,
    route_request: parsed.route_request,
    requires_user_approval: true,
    writes_extension_storage: false,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false
  });
}

export function parseBrowserExtensionRouteConfigReview(value: unknown): BrowserExtensionRouteConfigReview {
  if (!isRecord(value)) throw new Error("browser extension route config review must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "route_config_digest",
    "route_config",
    "route_request",
    "requires_user_approval",
    "writes_extension_storage",
    "creates_grants",
    "dispatches_signers",
    "stores_production_secrets"
  ])) {
    throw new Error("browser extension route config review has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT) {
    throw new Error("browser extension route config review format is unsupported");
  }
  const expected = createBrowserExtensionRouteConfigReview(value.route_config);
  const digest = requireHex64(value.route_config_digest, "browser extension route config review digest");
  if (digest !== expected.route_config_digest) {
    throw new Error("browser extension route config review digest mismatch");
  }
  if (!routeRequestsEqual(parseRouteSelectionRequest(value.route_request), expected.route_request)) {
    throw new Error("browser extension route config review route request mismatch");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension route config review must require user approval");
  }
  if (value.writes_extension_storage !== false) {
    throw new Error("browser extension route config review must not write extension storage");
  }
  if (value.creates_grants !== false) {
    throw new Error("browser extension route config review must not create grants");
  }
  if (value.dispatches_signers !== false) {
    throw new Error("browser extension route config review must not dispatch signers");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension route config review must not store production secrets");
  }
  return expected;
}

export function approveBrowserExtensionRouteConfigReview(
  review: unknown,
  options: BrowserExtensionRouteConfigApprovalOptions
): BrowserExtensionRouteConfigApproval {
  const parsedReview = parseBrowserExtensionRouteConfigReview(review);
  const reviewedRouteConfigDigest = requireHex64(options.reviewedRouteConfigDigest, "reviewedRouteConfigDigest");
  if (reviewedRouteConfigDigest !== parsedReview.route_config_digest) {
    throw new Error("reviewed route config digest does not match browser extension route config review");
  }
  return parseBrowserExtensionRouteConfigApproval({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT,
    route_config_digest: parsedReview.route_config_digest,
    approved_at: requireNonNegativeSafeInteger(options.approvedAt, "approvedAt"),
    review: parsedReview,
    requires_user_approval: true,
    writes_extension_storage: false,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false
  });
}

export function parseBrowserExtensionRouteConfigApproval(value: unknown): BrowserExtensionRouteConfigApproval {
  if (!isRecord(value)) throw new Error("browser extension route config approval must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "route_config_digest",
    "approved_at",
    "review",
    "requires_user_approval",
    "writes_extension_storage",
    "creates_grants",
    "dispatches_signers",
    "stores_production_secrets"
  ])) {
    throw new Error("browser extension route config approval has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT) {
    throw new Error("browser extension route config approval format is unsupported");
  }
  const digest = requireHex64(value.route_config_digest, "browser extension route config approval digest");
  const review = parseBrowserExtensionRouteConfigReview(value.review);
  if (digest !== review.route_config_digest) {
    throw new Error("browser extension route config approval digest mismatch");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension route config approval must require user approval");
  }
  if (value.writes_extension_storage !== false) {
    throw new Error("browser extension route config approval must not write extension storage");
  }
  if (value.creates_grants !== false) {
    throw new Error("browser extension route config approval must not create grants");
  }
  if (value.dispatches_signers !== false) {
    throw new Error("browser extension route config approval must not dispatch signers");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension route config approval must not store production secrets");
  }
  return Object.freeze({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT,
    route_config_digest: digest,
    approved_at: requireNonNegativeSafeInteger(value.approved_at, "browser extension route config approval approved_at"),
    review,
    requires_user_approval: true,
    writes_extension_storage: false,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false
  });
}
