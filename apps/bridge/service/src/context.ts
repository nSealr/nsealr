import { readFileSync } from "node:fs";
import {
  parseLocalGrantStore,
  parseLocalStorageApproval,
  requireLocalStorageApprovalEntry,
  type LocalGrantStore,
  type LocalServiceContext
} from "@nsealr/client";
import { parseAccountDescriptor, type AccountDescriptor } from "@nsealr/policy";
import { type SerialLinePortOpener } from "@nsealr/transport";
import {
  createServiceRouteDispatcher,
  parseServiceRouteDriverStore,
  type ServiceRouteDriverStore
} from "./drivers.js";

export const SERVICE_ACCOUNT_STORE_FORMAT = "nsealr-service-account-store-v0";
export const MAX_SERVICE_ACCOUNT_STORE_JSON_BYTES = 64 * 1024;
export const MAX_SERVICE_ACCOUNT_STORE_ACCOUNTS = 256;

export type ServiceAccountStore = {
  format: typeof SERVICE_ACCOUNT_STORE_FORMAT;
  updated_at: number;
  accounts: AccountDescriptor[];
  contains_secret_material: false;
};

export type ServiceContextFileOptions = {
  grantStorePath?: string;
  accountStorePath?: string;
  routeDriverStorePath?: string;
  storageApprovalPath?: string;
  openSerialLinePort?: SerialLinePortOpener;
  now?: number;
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

function compactJsonUtf8ByteLength(value: unknown): number {
  return Buffer.byteLength(JSON.stringify(value), "utf8");
}

function readJsonFile(path: string, label: string): unknown {
  const contents = readFileSync(path, "utf8");
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`${label} JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function hasContextFilePath(options: ServiceContextFileOptions): boolean {
  return (
    options.grantStorePath !== undefined ||
    options.accountStorePath !== undefined ||
    options.routeDriverStorePath !== undefined
  );
}

function requireContextStorageApproval(options: ServiceContextFileOptions): void {
  if (!hasContextFilePath(options)) return;
  if (options.storageApprovalPath === undefined) {
    throw new Error("service context files require --storage-approval");
  }
  const approval = parseLocalStorageApproval(readJsonFile(options.storageApprovalPath, "local storage approval"));
  if (options.grantStorePath !== undefined) {
    requireLocalStorageApprovalEntry(approval, {
      purpose: "grant_store",
      path: options.grantStorePath,
      access: "read_only"
    });
  }
  if (options.accountStorePath !== undefined) {
    requireLocalStorageApprovalEntry(approval, {
      purpose: "account_store",
      path: options.accountStorePath,
      access: "read_only"
    });
  }
  if (options.routeDriverStorePath !== undefined) {
    requireLocalStorageApprovalEntry(approval, {
      purpose: "route_driver_store",
      path: options.routeDriverStorePath,
      access: "read_only"
    });
  }
}

function takeOptionValue(args: string[], index: number, option: string): string {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

export function parseServiceAccountStore(value: unknown): ServiceAccountStore {
  if (!isRecord(value)) throw new Error("service account store must be an object");
  if (compactJsonUtf8ByteLength(value) > MAX_SERVICE_ACCOUNT_STORE_JSON_BYTES) {
    throw new Error("service account store JSON exceeds max bytes");
  }
  if (!hasOnlyKeys(value, ["format", "updated_at", "accounts", "contains_secret_material"])) {
    throw new Error("service account store has unsupported fields");
  }
  if (value.format !== SERVICE_ACCOUNT_STORE_FORMAT) {
    throw new Error("service account store format is unsupported");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("service account store must not contain secret material");
  }
  const updatedAt = requireNonNegativeInteger(value.updated_at, "service account store updated_at");
  if (!Array.isArray(value.accounts)) {
    throw new Error("service account store accounts must be an array");
  }
  if (value.accounts.length > MAX_SERVICE_ACCOUNT_STORE_ACCOUNTS) {
    throw new Error("service account store has too many accounts");
  }
  const accounts = value.accounts.map(parseAccountDescriptor);
  const accountIds = new Set<string>();
  for (const account of accounts) {
    if (accountIds.has(account.account_id)) {
      throw new Error("service account store account_id is duplicated");
    }
    accountIds.add(account.account_id);
  }
  return {
    format: SERVICE_ACCOUNT_STORE_FORMAT,
    updated_at: updatedAt,
    accounts,
    contains_secret_material: false
  };
}

function validateRouteDriverTargets(
  routeDriverStore: ServiceRouteDriverStore | undefined,
  accountStore: ServiceAccountStore | undefined
): void {
  if (routeDriverStore === undefined) return;
  if (accountStore === undefined) {
    throw new Error("service route driver store requires --account-store");
  }
  const accountsById = new Map(accountStore.accounts.map((account) => [account.account_id, account]));
  for (const route of routeDriverStore.routes) {
    const account = accountsById.get(route.account_id);
    if (account === undefined) {
      throw new Error(`service route driver account target is missing: ${route.account_id}`);
    }
    if (account.signer_route.type !== route.route_type) {
      throw new Error(`service route driver route_type does not match account: ${route.account_id}`);
    }
    if (account.signer_route.transport !== route.transport) {
      throw new Error(`service route driver transport does not match account: ${route.account_id}`);
    }
  }
}

export function loadServiceContextFromFiles(options: ServiceContextFileOptions): LocalServiceContext {
  requireContextStorageApproval(options);
  const grantStore: LocalGrantStore | undefined = options.grantStorePath === undefined
    ? undefined
    : parseLocalGrantStore(readJsonFile(options.grantStorePath, "local grant store"));
  const accountStore: ServiceAccountStore | undefined = options.accountStorePath === undefined
    ? undefined
    : parseServiceAccountStore(readJsonFile(options.accountStorePath, "service account store"));
  const routeDriverStore = options.routeDriverStorePath === undefined
    ? undefined
    : parseServiceRouteDriverStore(readJsonFile(options.routeDriverStorePath, "service route driver store"));
  validateRouteDriverTargets(routeDriverStore, accountStore);
  if (routeDriverStore !== undefined && options.openSerialLinePort === undefined) {
    throw new Error("service route driver store requires an explicit serial-line opener");
  }
  return {
    ...(accountStore !== undefined ? { accounts: accountStore.accounts } : {}),
    ...(grantStore !== undefined ? { grants: grantStore.grants } : {}),
    ...(routeDriverStore !== undefined && options.openSerialLinePort !== undefined
      ? {
          signerDispatcher: createServiceRouteDispatcher(routeDriverStore, {
            openSerialLinePort: options.openSerialLinePort
          })
        }
      : {}),
    ...(options.now !== undefined ? { now: options.now } : {})
  };
}

export function contextArgsFromCliArgs(args: string[]): ServiceContextFileOptions {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const options: ServiceContextFileOptions = {};

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--grant-store") {
      if (options.grantStorePath !== undefined) throw new Error("--grant-store is duplicated");
      options.grantStorePath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--account-store") {
      if (options.accountStorePath !== undefined) throw new Error("--account-store is duplicated");
      options.accountStorePath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--route-driver-store") {
      if (options.routeDriverStorePath !== undefined) throw new Error("--route-driver-store is duplicated");
      options.routeDriverStorePath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--storage-approval") {
      if (options.storageApprovalPath !== undefined) throw new Error("--storage-approval is duplicated");
      options.storageApprovalPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--now") {
      if (options.now !== undefined) throw new Error("--now is duplicated");
      const value = Number(takeOptionValue(normalizedArgs, index, arg));
      options.now = requireNonNegativeInteger(value, "--now");
      index += 1;
    } else {
      throw new Error(`unsupported service option: ${arg}`);
    }
  }

  return options;
}
