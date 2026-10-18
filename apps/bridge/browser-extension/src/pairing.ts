import {
  createBrowserNativeMessagingLocalServiceClient,
  type BrowserNativeMessageSender
} from "@nsealr/browser-provider";
import {
  reviewPairingIntent,
  type LocalPairingReview,
  type LocalServiceResponse,
  type PairableLocalServiceOperation
} from "@nsealr/client/browser";
import { parseLocalClientIdentity } from "@nsealr/client/browser";
import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionClientContext
} from "./sender.js";
import { BROWSER_EXTENSION_NAME } from "./manifest.js";

export const BROWSER_EXTENSION_DEFAULT_PAIRING_OPERATIONS = [
  "select_account_route",
  "dispatch_signer_request"
] as const satisfies readonly PairableLocalServiceOperation[];
export const BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT = "nsealr-browser-origin-permission-review-v0";
export const BROWSER_EXTENSION_ORIGIN_PERMISSION_APPROVAL_FORMAT = "nsealr-browser-origin-permission-approval-v0";

export type BrowserExtensionNativeMessagingPairingOptions = {
  sendNativeMessage: BrowserNativeMessageSender;
  hostName?: string;
  nextServiceRequestId?: () => string;
  requestedOperations?: readonly PairableLocalServiceOperation[];
  nativeMessageTimeoutMs?: number;
  nativeMessageAbortSignal?: AbortSignal;
};

export type BrowserExtensionPairingIntentResult = {
  context: BrowserExtensionClientContext;
  response: LocalServiceResponse;
};

export type BrowserExtensionPairingReviewResult = BrowserExtensionPairingIntentResult & {
  review: LocalPairingReview;
};

export type BrowserExtensionOriginPermissionMethod = {
  method: "get_public_key" | "sign_event";
  label: string;
  effect: string;
};

export type BrowserExtensionOriginPermissionReview = {
  format: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT;
  origin: string;
  app_name: string;
  extension_id: string;
  requested_methods: BrowserExtensionOriginPermissionMethod[];
  local_pairing_digest: string;
  requires_user_approval: true;
  stores_production_secrets: false;
  creates_grants: false;
  injects_provider: false;
};

export type BrowserExtensionOriginPermissionReviewResult = BrowserExtensionPairingReviewResult & {
  originReview: BrowserExtensionOriginPermissionReview;
};

export type BrowserExtensionOriginPermissionApproval = {
  format: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_APPROVAL_FORMAT;
  origin: string;
  app_name: string;
  extension_id: string;
  approved_methods: BrowserExtensionOriginPermissionMethod["method"][];
  local_pairing_digest: string;
  approved_at: number;
  requires_user_approval: true;
  authorizes_provider_injection: true;
  creates_grants: false;
  stores_production_secrets: false;
  contains_secret_material: false;
};

export type BrowserExtensionOriginPermissionApprovalOptions = {
  reviewedLocalPairingDigest: string;
  approvedAt: number;
};

const BROWSER_EXTENSION_METHOD_REVIEWS: Record<
  BrowserExtensionOriginPermissionMethod["method"],
  Omit<BrowserExtensionOriginPermissionMethod, "method">
> = {
  get_public_key: {
    label: "Read public key",
    effect: "The page can read the selected account public key through the browser provider."
  },
  sign_event: {
    label: "Request event signatures",
    effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
  }
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

function requireNonNegativeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer`);
  }
  return value;
}

function requireBrowserExtensionIdentity(
  origin: unknown,
  appName: unknown,
  extensionId: unknown
): { origin: string; app_name: string; extension_id: string } {
  if (typeof appName !== "string") {
    throw new Error("browser extension origin permission app_name is invalid");
  }
  if (appName.length === 0) {
    throw new Error("browser extension origin permission app_name is invalid");
  }
  if (typeof extensionId !== "string") {
    throw new Error("browser extension origin permission extension_id is invalid");
  }
  const client = parseLocalClientIdentity({
    surface: "browser_extension",
    origin,
    app_name: appName,
    instance_id: extensionId
  });
  return {
    origin: client.origin,
    app_name: client.app_name ?? `${BROWSER_EXTENSION_NAME} Browser Extension`,
    extension_id: client.instance_id ?? extensionId
  };
}

function parseOriginPermissionMethod(value: unknown): BrowserExtensionOriginPermissionMethod {
  if (!isRecord(value)) throw new Error("browser extension origin permission method must be an object");
  if (!hasOnlyKeys(value, ["method", "label", "effect"])) {
    throw new Error("browser extension origin permission method has unsupported fields");
  }
  if (value.method !== "get_public_key" && value.method !== "sign_event") {
    throw new Error("browser extension origin permission method is unsupported");
  }
  const expected = BROWSER_EXTENSION_METHOD_REVIEWS[value.method];
  if (value.label !== expected.label || value.effect !== expected.effect) {
    throw new Error("browser extension origin permission method text is invalid");
  }
  return {
    method: value.method,
    label: expected.label,
    effect: expected.effect
  };
}

function parseOriginPermissionMethods(value: unknown): BrowserExtensionOriginPermissionMethod[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("browser extension origin permission methods must be a non-empty array");
  }
  const methods = value.map(parseOriginPermissionMethod);
  const seen = new Set<BrowserExtensionOriginPermissionMethod["method"]>();
  for (const method of methods) {
    if (seen.has(method.method)) {
      throw new Error("browser extension origin permission method is duplicated");
    }
    seen.add(method.method);
  }
  return methods;
}

function parseApprovedMethods(value: unknown): BrowserExtensionOriginPermissionMethod["method"][] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("browser extension origin permission approved_methods must be a non-empty array");
  }
  const methods: BrowserExtensionOriginPermissionMethod["method"][] = [];
  for (const method of value) {
    if (method !== "get_public_key" && method !== "sign_event") {
      throw new Error("browser extension origin permission approved method is unsupported");
    }
    if (methods.includes(method)) {
      throw new Error("browser extension origin permission approved method is duplicated");
    }
    methods.push(method);
  }
  return methods;
}

function originPermissionMethods(review: LocalPairingReview): BrowserExtensionOriginPermissionMethod[] {
  const operations = new Set(review.requested_operations.map((operation) => operation.operation));
  const methods: BrowserExtensionOriginPermissionMethod[] = [];
  if (operations.has("select_account_route")) {
    methods.push({
      method: "get_public_key",
      ...BROWSER_EXTENSION_METHOD_REVIEWS.get_public_key
    });
  }
  if (operations.has("dispatch_signer_request")) {
    methods.push({
      method: "sign_event",
      ...BROWSER_EXTENSION_METHOD_REVIEWS.sign_event
    });
  }
  if (methods.length === 0) {
    throw new Error("browser extension origin permission review has no page-visible methods");
  }
  return methods;
}

export function projectBrowserExtensionOriginPermissionReview(
  result: BrowserExtensionPairingReviewResult
): BrowserExtensionOriginPermissionReview {
  return parseBrowserExtensionOriginPermissionReview({
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT,
    origin: result.context.client.origin,
    app_name: result.context.client.app_name ?? `${BROWSER_EXTENSION_NAME} Browser Extension`,
    extension_id: result.context.extension_id,
    requested_methods: originPermissionMethods(result.review),
    local_pairing_digest: result.review.pairing_digest,
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  });
}

export function parseBrowserExtensionOriginPermissionReview(
  value: unknown
): BrowserExtensionOriginPermissionReview {
  if (!isRecord(value)) throw new Error("browser extension origin permission review must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "origin",
    "app_name",
    "extension_id",
    "requested_methods",
    "local_pairing_digest",
    "requires_user_approval",
    "stores_production_secrets",
    "creates_grants",
    "injects_provider"
  ])) {
    throw new Error("browser extension origin permission review has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT) {
    throw new Error("browser extension origin permission review format is unsupported");
  }
  const identity = requireBrowserExtensionIdentity(value.origin, value.app_name, value.extension_id);
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension origin permission review must require user approval");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension origin permission review must not store production secrets");
  }
  if (value.creates_grants !== false) {
    throw new Error("browser extension origin permission review must not create grants");
  }
  if (value.injects_provider !== false) {
    throw new Error("browser extension origin permission review must not inject providers");
  }
  return {
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT,
    origin: identity.origin,
    app_name: identity.app_name,
    extension_id: identity.extension_id,
    requested_methods: parseOriginPermissionMethods(value.requested_methods),
    local_pairing_digest: requireHex64(value.local_pairing_digest, "browser extension origin permission local_pairing_digest"),
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  };
}

export function parseBrowserExtensionOriginPermissionApproval(
  value: unknown
): BrowserExtensionOriginPermissionApproval {
  if (!isRecord(value)) throw new Error("browser extension origin permission approval must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "origin",
    "app_name",
    "extension_id",
    "approved_methods",
    "local_pairing_digest",
    "approved_at",
    "requires_user_approval",
    "authorizes_provider_injection",
    "creates_grants",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension origin permission approval has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ORIGIN_PERMISSION_APPROVAL_FORMAT) {
    throw new Error("browser extension origin permission approval format is unsupported");
  }
  const identity = requireBrowserExtensionIdentity(value.origin, value.app_name, value.extension_id);
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension origin permission approval must require user approval");
  }
  if (value.authorizes_provider_injection !== true) {
    throw new Error("browser extension origin permission approval must authorize provider injection");
  }
  if (value.creates_grants !== false) {
    throw new Error("browser extension origin permission approval must not create grants");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension origin permission approval must not store production secrets");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("browser extension origin permission approval must not contain secret material");
  }
  return {
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_APPROVAL_FORMAT,
    origin: identity.origin,
    app_name: identity.app_name,
    extension_id: identity.extension_id,
    approved_methods: parseApprovedMethods(value.approved_methods),
    local_pairing_digest: requireHex64(value.local_pairing_digest, "browser extension origin permission local_pairing_digest"),
    approved_at: requireNonNegativeInteger(value.approved_at, "browser extension origin permission approved_at"),
    requires_user_approval: true,
    authorizes_provider_injection: true,
    creates_grants: false,
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

export function approveBrowserExtensionOriginPermissionReview(
  review: unknown,
  options: BrowserExtensionOriginPermissionApprovalOptions
): BrowserExtensionOriginPermissionApproval {
  const parsedReview = parseBrowserExtensionOriginPermissionReview(review);
  const reviewedDigest = requireHex64(
    options.reviewedLocalPairingDigest,
    "browser extension origin permission reviewedLocalPairingDigest"
  );
  if (reviewedDigest !== parsedReview.local_pairing_digest) {
    throw new Error("reviewed local pairing digest does not match origin permission review");
  }
  return parseBrowserExtensionOriginPermissionApproval({
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_APPROVAL_FORMAT,
    origin: parsedReview.origin,
    app_name: parsedReview.app_name,
    extension_id: parsedReview.extension_id,
    approved_methods: parsedReview.requested_methods.map((method) => method.method),
    local_pairing_digest: parsedReview.local_pairing_digest,
    approved_at: requireNonNegativeInteger(options.approvedAt, "approvedAt"),
    requires_user_approval: true,
    authorizes_provider_injection: true,
    creates_grants: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export async function requestBrowserExtensionNativeMessagingPairingIntent(
  sender: unknown,
  options: BrowserExtensionNativeMessagingPairingOptions
): Promise<BrowserExtensionPairingIntentResult> {
  const context = browserExtensionClientContextFromSender(sender);
  const service = createBrowserNativeMessagingLocalServiceClient({
    sendNativeMessage: options.sendNativeMessage,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextRequestId: options.nextServiceRequestId } : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { timeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined ? { abortSignal: options.nativeMessageAbortSignal } : {})
  });
  const response = await service.requestPairing(
    context.client,
    [...(options.requestedOperations ?? BROWSER_EXTENSION_DEFAULT_PAIRING_OPERATIONS)]
  );

  return {
    context,
    response
  };
}

export async function requestBrowserExtensionNativeMessagingPairingReview(
  sender: unknown,
  options: BrowserExtensionNativeMessagingPairingOptions
): Promise<BrowserExtensionPairingReviewResult> {
  const result = await requestBrowserExtensionNativeMessagingPairingIntent(sender, options);
  if (result.response.ok !== true || !("pairing_intent" in result.response.result)) {
    throw new Error("browser extension pairing response did not include a pairing intent");
  }
  return {
    ...result,
    review: reviewPairingIntent(result.response.result.pairing_intent)
  };
}

export async function requestBrowserExtensionNativeMessagingOriginPermissionReview(
  sender: unknown,
  options: BrowserExtensionNativeMessagingPairingOptions
): Promise<BrowserExtensionOriginPermissionReviewResult> {
  const result = await requestBrowserExtensionNativeMessagingPairingReview(sender, options);
  return {
    ...result,
    originReview: projectBrowserExtensionOriginPermissionReview(result)
  };
}
