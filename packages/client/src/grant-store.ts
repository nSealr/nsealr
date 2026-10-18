import { compactJsonUtf8ByteLength } from "@nsealr/protocol";
import {
  LOCAL_CLIENT_SURFACES,
  parseLocalClientIdentity,
  type LocalClientSurface
} from "./client-identity.js";
import {
  LOCAL_PAIRING_APPROVAL_FORMAT,
  LOCAL_SERVICE_OPERATIONS,
  type LocalClientGrant,
  type LocalPairingApproval,
  type PairableLocalServiceOperation
} from "./service.js";

export const LOCAL_GRANT_STORE_FORMAT = "nsealr-local-grant-store-v0";
export const MAX_LOCAL_GRANT_STORE_JSON_BYTES = 64 * 1024;
export const MAX_LOCAL_GRANT_STORE_GRANTS = 512;

export type LocalGrantStore = {
  format: typeof LOCAL_GRANT_STORE_FORMAT;
  updated_at: number;
  grants: LocalClientGrant[];
  contains_secret_material: false;
};

export type LocalGrantStoreOptions = {
  updatedAt: number;
};

export type LocalGrantRevocationOptions = {
  revokedAt: number;
};

export type LocalGrantSelector = {
  clientId: string;
  origin: string;
  surface: LocalClientSurface;
};

export type LocalGrantStoreRevocationOptions = LocalGrantRevocationOptions & {
  updatedAt?: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireNonNegativeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer`);
  }
  return value;
}

function requireHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 64 lowercase hex characters`);
  }
  return value;
}

function requireSurface(value: unknown): LocalClientSurface {
  if (typeof value !== "string" || !LOCAL_CLIENT_SURFACES.includes(value as LocalClientSurface)) {
    throw new Error("grant surface is unsupported");
  }
  return value as LocalClientSurface;
}

function requireOriginForSurface(value: unknown, surface: LocalClientSurface): string {
  try {
    return parseLocalClientIdentity({ surface, origin: value }).origin;
  } catch (error) {
    if (error instanceof Error && error.message.includes("origin scheme")) {
      throw new Error("grant origin scheme is unsupported");
    }
    throw new Error("grant origin is invalid");
  }
}

function requireAllowedOperations(value: unknown): PairableLocalServiceOperation[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("grant allowed_operations must be a non-empty array");
  }
  const operations: PairableLocalServiceOperation[] = [];
  for (const operation of value) {
    if (
      typeof operation !== "string" ||
      !LOCAL_SERVICE_OPERATIONS.includes(operation as (typeof LOCAL_SERVICE_OPERATIONS)[number])
    ) {
      throw new Error("grant allowed operation is unsupported");
    }
    if (operation === "service_status" || operation === "request_pairing") {
      throw new Error("grant allowed operation does not require pairing");
    }
    if (operations.includes(operation as PairableLocalServiceOperation)) {
      throw new Error("grant allowed operation is duplicated");
    }
    operations.push(operation as PairableLocalServiceOperation);
  }
  return operations;
}

function parseLocalGrantSelector(selector: LocalGrantSelector): LocalGrantSelector {
  if (!isRecord(selector)) throw new Error("local grant selector must be an object");
  const surface = requireSurface(selector.surface);
  return {
    clientId: requireHex64(selector.clientId, "local grant selector client_id"),
    origin: requireOriginForSurface(selector.origin, surface),
    surface
  };
}

export function parseLocalGrant(value: unknown): LocalClientGrant {
  if (!isRecord(value)) throw new Error("grant must be an object");
  if (!hasOnlyKeys(value, [
    "client_id",
    "origin",
    "surface",
    "allowed_operations",
    "pairing_digest",
    "approved_at",
    "revoked",
    "expires_at"
  ])) {
    throw new Error("grant has unsupported fields");
  }
  const approvedAt = requireNonNegativeInteger(value.approved_at, "grant approved_at");
  const expiresAt = "expires_at" in value
    ? requireNonNegativeInteger(value.expires_at, "grant expires_at")
    : undefined;
  if (expiresAt !== undefined && expiresAt <= approvedAt) {
    throw new Error("grant expires_at must be greater than approved_at");
  }
  if ("revoked" in value && typeof value.revoked !== "boolean") {
    throw new Error("grant revoked flag is invalid");
  }
  const pairingDigest = "pairing_digest" in value
    ? requireHex64(value.pairing_digest, "grant pairing_digest")
    : undefined;
  const surface = requireSurface(value.surface);
  return {
    client_id: requireHex64(value.client_id, "grant client_id"),
    origin: requireOriginForSurface(value.origin, surface),
    surface,
    allowed_operations: requireAllowedOperations(value.allowed_operations),
    approved_at: approvedAt,
    ...(pairingDigest !== undefined ? { pairing_digest: pairingDigest } : {}),
    ...(value.revoked === true ? { revoked: true } : {}),
    ...(expiresAt !== undefined ? { expires_at: expiresAt } : {})
  };
}

export function parseLocalPairingApproval(value: unknown): LocalPairingApproval {
  if (!isRecord(value)) throw new Error("local pairing approval must be an object");
  if (!hasOnlyKeys(value, ["format", "pairing_digest", "approved_at", "grant", "stores_production_secrets"])) {
    throw new Error("local pairing approval has unsupported fields");
  }
  if (value.format !== LOCAL_PAIRING_APPROVAL_FORMAT) {
    throw new Error("local pairing approval format is unsupported");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("local pairing approval must not store production secrets");
  }
  const pairingDigest = requireHex64(value.pairing_digest, "local pairing approval pairing_digest");
  const approvedAt = requireNonNegativeInteger(value.approved_at, "local pairing approval approved_at");
  const grant = parseLocalGrant(value.grant);
  if (grant.pairing_digest !== pairingDigest) {
    throw new Error("local pairing approval grant pairing_digest mismatch");
  }
  if (grant.approved_at !== approvedAt) {
    throw new Error("local pairing approval grant approved_at mismatch");
  }
  return {
    format: LOCAL_PAIRING_APPROVAL_FORMAT,
    pairing_digest: pairingDigest,
    approved_at: approvedAt,
    grant,
    stores_production_secrets: false
  };
}

export function createLocalGrantStore(
  grants: LocalClientGrant[],
  options: LocalGrantStoreOptions
): LocalGrantStore {
  const store = {
    format: LOCAL_GRANT_STORE_FORMAT,
    updated_at: options.updatedAt,
    grants,
    contains_secret_material: false
  };
  return parseLocalGrantStore(store);
}

export function parseLocalGrantStore(value: unknown): LocalGrantStore {
  if (!isRecord(value)) throw new Error("local grant store must be an object");
  if (compactJsonUtf8ByteLength(value) > MAX_LOCAL_GRANT_STORE_JSON_BYTES) {
    throw new Error("local grant store JSON exceeds max bytes");
  }
  if (!hasOnlyKeys(value, ["format", "updated_at", "grants", "contains_secret_material"])) {
    throw new Error("local grant store has unsupported fields");
  }
  if (value.format !== LOCAL_GRANT_STORE_FORMAT) {
    throw new Error("local grant store format is unsupported");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("local grant store must not contain secret material");
  }
  const updatedAt = requireNonNegativeInteger(value.updated_at, "local grant store updated_at");
  if (!Array.isArray(value.grants)) {
    throw new Error("local grant store grants must be an array");
  }
  if (value.grants.length > MAX_LOCAL_GRANT_STORE_GRANTS) {
    throw new Error("local grant store has too many grants");
  }
  return {
    format: LOCAL_GRANT_STORE_FORMAT,
    updated_at: updatedAt,
    grants: value.grants.map(parseLocalGrant),
    contains_secret_material: false
  };
}

export function serializeLocalGrantStore(store: LocalGrantStore): string {
  return `${JSON.stringify(parseLocalGrantStore(store), null, 2)}\n`;
}

export function appendLocalGrant(store: LocalGrantStore, grant: LocalClientGrant, options: LocalGrantStoreOptions): LocalGrantStore {
  return createLocalGrantStore([...parseLocalGrantStore(store).grants, parseLocalGrant(grant)], options);
}

export function appendLocalGrantRevocation(
  store: LocalGrantStore,
  selector: LocalGrantSelector,
  options: LocalGrantStoreRevocationOptions
): LocalGrantStore {
  const parsedStore = parseLocalGrantStore(store);
  const parsedSelector = parseLocalGrantSelector(selector);
  let selected: LocalClientGrant | undefined;
  let selectedApprovedAt = -1;
  for (const grant of parsedStore.grants) {
    if (
      grant.client_id !== parsedSelector.clientId ||
      grant.origin !== parsedSelector.origin ||
      grant.surface !== parsedSelector.surface
    ) {
      continue;
    }
    const approvedAt = grant.approved_at ?? 0;
    if (approvedAt >= selectedApprovedAt) {
      selected = grant;
      selectedApprovedAt = approvedAt;
    }
  }
  if (selected === undefined) {
    throw new Error("local grant store has no matching grant to revoke");
  }
  if (selected.revoked === true) {
    throw new Error("latest matching local grant is already revoked");
  }
  const revokedAt = requireNonNegativeInteger(options.revokedAt, "revokedAt");
  const updatedAt = options.updatedAt === undefined
    ? revokedAt
    : requireNonNegativeInteger(options.updatedAt, "updatedAt");
  if (updatedAt < revokedAt) {
    throw new Error("updatedAt must be greater than or equal to revokedAt");
  }
  return appendLocalGrant(parsedStore, revokeLocalGrant(selected, { revokedAt }), { updatedAt });
}

export function revokeLocalGrant(grant: LocalClientGrant, options: LocalGrantRevocationOptions): LocalClientGrant {
  const parsed = parseLocalGrant({
    ...grant,
    approved_at: grant.approved_at ?? options.revokedAt
  });
  const revokedAt = requireNonNegativeInteger(options.revokedAt, "revokedAt");
  if (revokedAt < (parsed.approved_at ?? 0)) {
    throw new Error("revokedAt must be greater than or equal to grant approved_at");
  }
  return {
    client_id: parsed.client_id,
    origin: parsed.origin,
    surface: parsed.surface,
    allowed_operations: [...parsed.allowed_operations],
    ...(parsed.pairing_digest !== undefined ? { pairing_digest: parsed.pairing_digest } : {}),
    approved_at: revokedAt,
    revoked: true
  };
}
