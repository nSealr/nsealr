#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";
import {
  approveBrowserExtensionOriginPermissionReview,
  parseBrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  createBrowserExtensionOriginPermissionStore,
  revokeBrowserExtensionOriginPermissionApproval,
  upsertBrowserExtensionOriginPermissionApproval
} from "./origin-permission-store.js";

type OriginPermissionCliOptions = {
  reviewPath?: string;
  storePath?: string;
  approvalPath?: string;
  reviewedLocalPairingDigest?: string;
  approvedAt?: number;
  updatedAt?: number;
  origin?: string;
  extensionId?: string;
  localPairingDigest?: string;
};

const OPTION_LABELS: Record<keyof OriginPermissionCliOptions, string> = {
  reviewPath: "--review",
  storePath: "--store",
  approvalPath: "--approval",
  reviewedLocalPairingDigest: "--reviewed-local-pairing-digest",
  approvedAt: "--approved-at",
  updatedAt: "--updated-at",
  origin: "--origin",
  extensionId: "--extension-id",
  localPairingDigest: "--local-pairing-digest"
};

function takeOptionValue(args: string[], index: number, option: string): string {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

function requireLowerHex64(value: string, option: string): string {
  if (!/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${option} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireNonNegativeSafeInteger(value: string, option: string): number {
  if (!/^(0|[1-9]\d*)$/u.test(value)) {
    throw new Error(`${option} must be a non-negative safe integer`);
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`${option} must be a non-negative safe integer`);
  }
  return parsed;
}

function parseOriginPermissionCliArgs(args: string[]): OriginPermissionCliOptions {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const options: OriginPermissionCliOptions = {};
  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--review") {
      if (options.reviewPath !== undefined) throw new Error("--review must be specified only once");
      options.reviewPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--store") {
      if (options.storePath !== undefined) throw new Error("--store must be specified only once");
      options.storePath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--approval") {
      if (options.approvalPath !== undefined) throw new Error("--approval must be specified only once");
      options.approvalPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--reviewed-local-pairing-digest") {
      if (options.reviewedLocalPairingDigest !== undefined) {
        throw new Error("--reviewed-local-pairing-digest must be specified only once");
      }
      options.reviewedLocalPairingDigest = requireLowerHex64(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--local-pairing-digest") {
      if (options.localPairingDigest !== undefined) {
        throw new Error("--local-pairing-digest must be specified only once");
      }
      options.localPairingDigest = requireLowerHex64(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--approved-at") {
      if (options.approvedAt !== undefined) throw new Error("--approved-at must be specified only once");
      options.approvedAt = requireNonNegativeSafeInteger(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--updated-at") {
      if (options.updatedAt !== undefined) throw new Error("--updated-at must be specified only once");
      options.updatedAt = requireNonNegativeSafeInteger(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--origin") {
      if (options.origin !== undefined) throw new Error("--origin must be specified only once");
      options.origin = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--extension-id") {
      if (options.extensionId !== undefined) throw new Error("--extension-id must be specified only once");
      options.extensionId = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else {
      throw new Error(`unsupported browser-extension origin-permission option: ${arg}`);
    }
  }
  return options;
}

function readJsonFile(path: string, label: string): unknown {
  const contents = readFileSync(path, "utf8");
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`${label} JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function requireOption<T>(value: T | undefined, option: string): T {
  if (value === undefined) throw new Error(`${option} is required`);
  return value;
}

function ensureOnlyAllowed(options: OriginPermissionCliOptions, allowed: readonly (keyof OriginPermissionCliOptions)[]): void {
  const allowedSet = new Set<keyof OriginPermissionCliOptions>(allowed);
  const keys = Object.keys(options) as (keyof OriginPermissionCliOptions)[];
  for (const key of keys) {
    if (!allowedSet.has(key)) {
      throw new Error(`${OPTION_LABELS[key]} is not supported by this command`);
    }
  }
}

export function browserExtensionOriginPermissionApprovalJsonFromArgs(args: string[]): string {
  const options = parseOriginPermissionCliArgs(args);
  ensureOnlyAllowed(options, ["reviewPath", "reviewedLocalPairingDigest", "approvedAt"]);
  return `${JSON.stringify(approveBrowserExtensionOriginPermissionReview(
    parseBrowserExtensionOriginPermissionReview(readJsonFile(
      requireOption(options.reviewPath, "--review"),
      "browser extension origin permission review"
    )),
    {
      reviewedLocalPairingDigest: requireOption(
        options.reviewedLocalPairingDigest,
        "--reviewed-local-pairing-digest"
      ),
      approvedAt: requireOption(options.approvedAt, "--approved-at")
    }
  ), null, 2)}\n`;
}

export function browserExtensionOriginPermissionStoreCreateJsonFromArgs(args: string[]): string {
  const options = parseOriginPermissionCliArgs(args);
  ensureOnlyAllowed(options, ["updatedAt"]);
  return `${JSON.stringify(createBrowserExtensionOriginPermissionStore([], {
    updatedAt: requireOption(options.updatedAt, "--updated-at")
  }), null, 2)}\n`;
}

export function browserExtensionOriginPermissionStoreUpsertJsonFromArgs(args: string[]): string {
  const options = parseOriginPermissionCliArgs(args);
  ensureOnlyAllowed(options, ["storePath", "approvalPath", "updatedAt"]);
  return `${JSON.stringify(upsertBrowserExtensionOriginPermissionApproval(
    readJsonFile(requireOption(options.storePath, "--store"), "browser extension origin permission store"),
    readJsonFile(requireOption(options.approvalPath, "--approval"), "browser extension origin permission approval"),
    {
      updatedAt: requireOption(options.updatedAt, "--updated-at")
    }
  ), null, 2)}\n`;
}

export function browserExtensionOriginPermissionStoreRevokeJsonFromArgs(args: string[]): string {
  const options = parseOriginPermissionCliArgs(args);
  ensureOnlyAllowed(options, ["storePath", "origin", "extensionId", "localPairingDigest", "updatedAt"]);
  return `${JSON.stringify(revokeBrowserExtensionOriginPermissionApproval(
    readJsonFile(requireOption(options.storePath, "--store"), "browser extension origin permission store"),
    {
      origin: requireOption(options.origin, "--origin"),
      extensionId: requireOption(options.extensionId, "--extension-id"),
      localPairingDigest: requireOption(options.localPairingDigest, "--local-pairing-digest")
    },
    {
      updatedAt: requireOption(options.updatedAt, "--updated-at")
    }
  ), null, 2)}\n`;
}

export async function runBrowserExtensionOriginPermissionCli(
  command: string | undefined,
  args: string[]
): Promise<void> {
  try {
    if (command === "approve") {
      writeSync(1, browserExtensionOriginPermissionApprovalJsonFromArgs(args));
      return;
    }
    if (command === "store-create") {
      writeSync(1, browserExtensionOriginPermissionStoreCreateJsonFromArgs(args));
      return;
    }
    if (command === "store-upsert") {
      writeSync(1, browserExtensionOriginPermissionStoreUpsertJsonFromArgs(args));
      return;
    }
    if (command === "store-revoke") {
      writeSync(1, browserExtensionOriginPermissionStoreRevokeJsonFromArgs(args));
      return;
    }
    throw new Error("browser-extension origin-permission command must be approve, store-create, store-upsert, or store-revoke");
  } catch (error) {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await runBrowserExtensionOriginPermissionCli(process.argv[2], process.argv.slice(3));
}
