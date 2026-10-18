import {
  parseBrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionApproval
} from "./pairing.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
  createBrowserExtensionOriginPermissionStore,
  parseBrowserExtensionOriginPermissionStore,
  revokeBrowserExtensionOriginPermissionApproval,
  upsertBrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionApprovalKey,
  type BrowserExtensionOriginPermissionStore
} from "./origin-permission-store.js";

export const BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY =
  "nsealr.browser.origin_permissions.v0";
export const BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT =
  "nsealr-browser-origin-permission-storage-write-v0";

export type BrowserExtensionOriginPermissionStorageArea = {
  get(key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY): Promise<unknown> | unknown;
  set(items: {
    [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: BrowserExtensionOriginPermissionStore;
  }): Promise<void> | void;
  remove?(key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY): Promise<void> | void;
};

export type BrowserExtensionOriginPermissionStorageReadOptions = {
  emptyUpdatedAt?: number;
};

export type BrowserExtensionOriginPermissionStorageMutationOptions =
  BrowserExtensionOriginPermissionStorageReadOptions & {
    updatedAt: number;
  };

export type BrowserExtensionOriginPermissionStorageRemoveOptions = {
  removedAt: number;
};

export type BrowserExtensionOriginPermissionStorageWriteResult = {
  format: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT;
  storage_key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY;
  store_format: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT;
  updated_at: number;
  approval_count: number;
  requires_user_approval: true;
  reads_extension_storage: boolean;
  writes_extension_storage: true;
  creates_grants: false;
  dispatches_signers: false;
  stores_production_secrets: false;
  contains_secret_material: false;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireStorageArea(
  value: BrowserExtensionOriginPermissionStorageArea
): BrowserExtensionOriginPermissionStorageArea {
  if (!isRecord(value) || typeof value.get !== "function" || typeof value.set !== "function") {
    throw new Error("browser extension origin permission storage area is invalid");
  }
  if (value.remove !== undefined && typeof value.remove !== "function") {
    throw new Error("browser extension origin permission storage remove dependency is invalid");
  }
  return value;
}

function requireNonNegativeSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function emptyStore(options: BrowserExtensionOriginPermissionStorageReadOptions): BrowserExtensionOriginPermissionStore {
  return createBrowserExtensionOriginPermissionStore([], {
    updatedAt: requireNonNegativeSafeInteger(
      options.emptyUpdatedAt ?? 0,
      "browser extension origin permission empty storage updatedAt"
    )
  });
}

function parseStorageReadResult(
  value: unknown,
  options: BrowserExtensionOriginPermissionStorageReadOptions
): BrowserExtensionOriginPermissionStore {
  if (!isRecord(value)) {
    throw new Error("browser extension origin permission storage read result must be an object");
  }
  if (!hasOnlyKeys(value, [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY])) {
    throw new Error("browser extension origin permission storage read result has unsupported fields");
  }
  if (!(BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY in value)) {
    return emptyStore(options);
  }
  return parseBrowserExtensionOriginPermissionStore(
    value[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]
  );
}

function storageWriteResult(
  store: BrowserExtensionOriginPermissionStore,
  readsExtensionStorage: boolean
): BrowserExtensionOriginPermissionStorageWriteResult {
  return Object.freeze({
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
    storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
    store_format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
    updated_at: store.updated_at,
    approval_count: store.approvals.length,
    requires_user_approval: true,
    reads_extension_storage: readsExtensionStorage,
    writes_extension_storage: true,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export function parseBrowserExtensionOriginPermissionStorageWriteResult(
  value: unknown
): BrowserExtensionOriginPermissionStorageWriteResult {
  if (!isRecord(value)) {
    throw new Error("browser extension origin permission storage write result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "storage_key",
    "store_format",
    "updated_at",
    "approval_count",
    "requires_user_approval",
    "reads_extension_storage",
    "writes_extension_storage",
    "creates_grants",
    "dispatches_signers",
    "stores_production_secrets",
    "contains_secret_material"
  ])) {
    throw new Error("browser extension origin permission storage write result has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT) {
    throw new Error("browser extension origin permission storage write result format is unsupported");
  }
  if (value.storage_key !== BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY) {
    throw new Error("browser extension origin permission storage write result key is unsupported");
  }
  if (value.store_format !== BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT) {
    throw new Error("browser extension origin permission storage write result store format is unsupported");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("browser extension origin permission storage write result must require user approval");
  }
  if (value.reads_extension_storage !== true && value.reads_extension_storage !== false) {
    throw new Error("browser extension origin permission storage write result read flag is invalid");
  }
  if (
    value.writes_extension_storage !== true ||
    value.creates_grants !== false ||
    value.dispatches_signers !== false ||
    value.stores_production_secrets !== false ||
    value.contains_secret_material !== false
  ) {
    throw new Error("browser extension origin permission storage write result has unsafe effects");
  }
  return Object.freeze({
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
    storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
    store_format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
    updated_at: requireNonNegativeSafeInteger(
      value.updated_at,
      "browser extension origin permission storage write result updated_at"
    ),
    approval_count: requireNonNegativeSafeInteger(
      value.approval_count,
      "browser extension origin permission storage write result approval_count"
    ),
    requires_user_approval: true,
    reads_extension_storage: value.reads_extension_storage,
    writes_extension_storage: true,
    creates_grants: false,
    dispatches_signers: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export async function readBrowserExtensionOriginPermissionStoreFromStorage(
  area: BrowserExtensionOriginPermissionStorageArea,
  options: BrowserExtensionOriginPermissionStorageReadOptions = {}
): Promise<BrowserExtensionOriginPermissionStore> {
  const storage = requireStorageArea(area);
  return parseStorageReadResult(
    await storage.get(BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY),
    options
  );
}

export async function writeBrowserExtensionOriginPermissionStoreToStorage(
  area: BrowserExtensionOriginPermissionStorageArea,
  store: unknown,
  options: { readsExtensionStorage?: boolean } = {}
): Promise<BrowserExtensionOriginPermissionStorageWriteResult> {
  const storage = requireStorageArea(area);
  const parsedStore = parseBrowserExtensionOriginPermissionStore(store);
  await storage.set({
    [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: parsedStore
  });
  return storageWriteResult(parsedStore, options.readsExtensionStorage === true);
}

export async function upsertBrowserExtensionOriginPermissionApprovalInStorage(
  area: BrowserExtensionOriginPermissionStorageArea,
  approval: unknown,
  options: BrowserExtensionOriginPermissionStorageMutationOptions
): Promise<BrowserExtensionOriginPermissionStorageWriteResult> {
  const parsedApproval: BrowserExtensionOriginPermissionApproval =
    parseBrowserExtensionOriginPermissionApproval(approval);
  const current = await readBrowserExtensionOriginPermissionStoreFromStorage(area, options);
  return writeBrowserExtensionOriginPermissionStoreToStorage(
    area,
    upsertBrowserExtensionOriginPermissionApproval(current, parsedApproval, {
      updatedAt: options.updatedAt
    }),
    { readsExtensionStorage: true }
  );
}

export async function revokeBrowserExtensionOriginPermissionApprovalInStorage(
  area: BrowserExtensionOriginPermissionStorageArea,
  key: BrowserExtensionOriginPermissionApprovalKey,
  options: BrowserExtensionOriginPermissionStorageMutationOptions
): Promise<BrowserExtensionOriginPermissionStorageWriteResult> {
  const current = await readBrowserExtensionOriginPermissionStoreFromStorage(area, options);
  return writeBrowserExtensionOriginPermissionStoreToStorage(
    area,
    revokeBrowserExtensionOriginPermissionApproval(current, key, {
      updatedAt: options.updatedAt
    }),
    { readsExtensionStorage: true }
  );
}

export async function removeBrowserExtensionOriginPermissionStoreFromStorage(
  area: BrowserExtensionOriginPermissionStorageArea,
  options: BrowserExtensionOriginPermissionStorageRemoveOptions
): Promise<BrowserExtensionOriginPermissionStorageWriteResult> {
  const storage = requireStorageArea(area);
  if (storage.remove === undefined) {
    throw new Error("browser extension origin permission storage remove dependency is unavailable");
  }
  await storage.remove(BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY);
  return storageWriteResult(
    emptyStore({
      emptyUpdatedAt: requireNonNegativeSafeInteger(
        options.removedAt,
        "browser extension origin permission storage removedAt"
      )
    }),
    false
  );
}
