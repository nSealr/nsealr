import { parseLocalClientIdentity } from "@nsealr/client/browser";
import {
  parseBrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionMethod
} from "./pairing.js";
import { BROWSER_EXTENSION_NAME } from "./manifest.js";

export const BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT =
  "nsealr-browser-origin-permission-store-v0";

export type BrowserExtensionOriginPermissionStore = {
  format: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT;
  updated_at: number;
  approvals: readonly BrowserExtensionOriginPermissionApproval[];
  requires_user_approval: true;
  writes_extension_storage: false;
  creates_grants: false;
  dispatches_signers: false;
  stores_production_secrets: false;
  contains_secret_material: false;
};

export type BrowserExtensionOriginPermissionStoreOptions = {
  updatedAt: number;
};

export type BrowserExtensionOriginPermissionStoreMutationOptions = {
  updatedAt: number;
};

export type BrowserExtensionOriginPermissionApprovalKey = {
  origin: string;
  extensionId: string;
  localPairingDigest: string;
};

export type BrowserExtensionOriginPermissionLookup = {
  origin: string;
  extensionId: string;
  localPairingDigest: string;
  method: BrowserExtensionOriginPermissionMethod["method"];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireNonNegativeSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function requireHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireOriginPermissionMethod(value: unknown): BrowserExtensionOriginPermissionMethod["method"] {
  if (value !== "get_public_key" && value !== "sign_event") {
    throw new Error("browser extension origin permission lookup method is unsupported");
  }
  return value;
}

function requireLookupIdentity(lookup: {
  origin: string;
  extensionId: string;
}): { origin: string; extensionId: string } {
  const identity = parseLocalClientIdentity({
    surface: "browser_extension",
    origin: lookup.origin,
    app_name: `${BROWSER_EXTENSION_NAME} Browser Extension`,
    instance_id: lookup.extensionId
  });
  if (identity.instance_id === undefined) {
    throw new Error("browser extension origin permission lookup extensionId is invalid");
  }
  return {
    origin: identity.origin,
    extensionId: identity.instance_id
  };
}

function approvalKey(approval: BrowserExtensionOriginPermissionApproval): string {
  return `${approval.origin}\u0000${approval.extension_id}\u0000${approval.local_pairing_digest}`;
}

function normalizeApprovalKey(
  key: BrowserExtensionOriginPermissionApprovalKey
): BrowserExtensionOriginPermissionApprovalKey {
  const identity = requireLookupIdentity(key);
  return {
    origin: identity.origin,
    extensionId: identity.extensionId,
    localPairingDigest: requireHex64(
      key.localPairingDigest,
      "browser extension origin permission key localPairingDigest"
    )
  };
}

function approvalMatchesKey(
  approval: BrowserExtensionOriginPermissionApproval,
  key: BrowserExtensionOriginPermissionApprovalKey
): boolean {
  return approval.origin === key.origin
    && approval.extension_id === key.extensionId
    && approval.local_pairing_digest === key.localPairingDigest;
}

function compareApprovals(
  left: BrowserExtensionOriginPermissionApproval,
  right: BrowserExtensionOriginPermissionApproval
): number {
  return left.origin.localeCompare(right.origin)
    || left.extension_id.localeCompare(right.extension_id)
    || left.local_pairing_digest.localeCompare(right.local_pairing_digest)
    || left.approved_at - right.approved_at
    || left.app_name.localeCompare(right.app_name);
}

function parseApprovals(value: unknown): BrowserExtensionOriginPermissionApproval[] {
  if (!Array.isArray(value)) {
    throw new Error("browser extension origin permission store approvals must be an array");
  }
  const approvals = value.map(parseBrowserExtensionOriginPermissionApproval);
  const seen = new Set<string>();
  for (const approval of approvals) {
    const key = approvalKey(approval);
    if (seen.has(key)) {
      throw new Error("browser extension origin permission store approval is duplicated");
    }
    seen.add(key);
  }
  return approvals
    .sort(compareApprovals)
    .map((approval) => Object.freeze(approval));
}

function buildOriginPermissionStore(
  approvals: BrowserExtensionOriginPermissionApproval[],
  updatedAt: number
): BrowserExtensionOriginPermissionStore {
  return Object.freeze({
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
    updated_at: updatedAt,
    approvals: Object.freeze(approvals),
    requires_user_approval: true,
    writes_extension_storage: false,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export function createBrowserExtensionOriginPermissionStore(
  approvals: readonly unknown[],
  options: BrowserExtensionOriginPermissionStoreOptions
): BrowserExtensionOriginPermissionStore {
  return buildOriginPermissionStore(
    parseApprovals([...approvals]),
    requireNonNegativeSafeInteger(options.updatedAt, "browser extension origin permission store updatedAt")
  );
}

export function parseBrowserExtensionOriginPermissionStore(
  value: unknown
): BrowserExtensionOriginPermissionStore {
  if (!isRecord(value)) {
    throw new Error("browser extension origin permission store must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "updated_at",
    "approvals",
    "requires_user_approval",
    "writes_extension_storage",
    "creates_grants",
    "dispatches_signers",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension origin permission store has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT) {
    throw new Error("browser extension origin permission store format is unsupported");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension origin permission store must require user approval");
  }
  if (value.writes_extension_storage !== false) {
    throw new Error("browser extension origin permission store must not write extension storage");
  }
  if (value.creates_grants !== false) {
    throw new Error("browser extension origin permission store must not create grants");
  }
  if (value.dispatches_signers !== false) {
    throw new Error("browser extension origin permission store must not dispatch signers");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("browser extension origin permission store must not store production secrets");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("browser extension origin permission store must not contain secret material");
  }
  return buildOriginPermissionStore(
    parseApprovals(value.approvals),
    requireNonNegativeSafeInteger(
      value.updated_at,
      "browser extension origin permission store updated_at"
    )
  );
}

function mutationUpdatedAt(
  store: BrowserExtensionOriginPermissionStore,
  options: BrowserExtensionOriginPermissionStoreMutationOptions
): number {
  const updatedAt = requireNonNegativeSafeInteger(
    options.updatedAt,
    "browser extension origin permission store mutation updatedAt"
  );
  if (updatedAt < store.updated_at) {
    throw new Error("browser extension origin permission store mutation updatedAt must not move backward");
  }
  return updatedAt;
}

export function upsertBrowserExtensionOriginPermissionApproval(
  store: unknown,
  approval: unknown,
  options: BrowserExtensionOriginPermissionStoreMutationOptions
): BrowserExtensionOriginPermissionStore {
  const parsedStore = parseBrowserExtensionOriginPermissionStore(store);
  const parsedApproval = parseBrowserExtensionOriginPermissionApproval(approval);
  const updatedAt = mutationUpdatedAt(parsedStore, options);
  return buildOriginPermissionStore(parseApprovals([
    ...parsedStore.approvals.filter((existing) => approvalKey(existing) !== approvalKey(parsedApproval)),
    parsedApproval
  ]), updatedAt);
}

export function revokeBrowserExtensionOriginPermissionApproval(
  store: unknown,
  key: BrowserExtensionOriginPermissionApprovalKey,
  options: BrowserExtensionOriginPermissionStoreMutationOptions
): BrowserExtensionOriginPermissionStore {
  const parsedStore = parseBrowserExtensionOriginPermissionStore(store);
  const normalizedKey = normalizeApprovalKey(key);
  const updatedAt = mutationUpdatedAt(parsedStore, options);
  return buildOriginPermissionStore(
    parsedStore.approvals.filter((approval) => !approvalMatchesKey(approval, normalizedKey)),
    updatedAt
  );
}

export function findBrowserExtensionOriginPermissionApproval(
  store: unknown,
  lookup: BrowserExtensionOriginPermissionLookup
): BrowserExtensionOriginPermissionApproval | undefined {
  const parsedStore = parseBrowserExtensionOriginPermissionStore(store);
  const identity = requireLookupIdentity(lookup);
  const localPairingDigest = requireHex64(
    lookup.localPairingDigest,
    "browser extension origin permission lookup localPairingDigest"
  );
  const method = requireOriginPermissionMethod(lookup.method);
  return parsedStore.approvals.find((approval) => (
    approval.origin === identity.origin
    && approval.extension_id === identity.extensionId
    && approval.local_pairing_digest === localPairingDigest
    && approval.approved_methods.includes(method)
  ));
}

export function isBrowserExtensionOriginMethodAllowed(
  store: unknown,
  lookup: BrowserExtensionOriginPermissionLookup
): boolean {
  return findBrowserExtensionOriginPermissionApproval(store, lookup) !== undefined;
}
