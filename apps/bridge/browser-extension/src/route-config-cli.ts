#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";
import {
  BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
  approveBrowserExtensionRouteConfigReview,
  createBrowserExtensionRouteConfigReview,
  parseBrowserExtensionRouteConfigReview
} from "./route-config.js";

type RouteConfigCliOptions = {
  routeAccountId?: string;
  routeType?: string;
  reviewPath?: string;
  reviewedRouteConfigDigest?: string;
  approvedAt?: number;
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

function parseRouteConfigCliArgs(args: string[]): RouteConfigCliOptions {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const options: RouteConfigCliOptions = {};
  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--route-account-id") {
      if (options.routeAccountId !== undefined) throw new Error("--route-account-id must be specified only once");
      options.routeAccountId = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--route-type") {
      if (options.routeType !== undefined) throw new Error("--route-type must be specified only once");
      options.routeType = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--review") {
      if (options.reviewPath !== undefined) throw new Error("--review must be specified only once");
      options.reviewPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--reviewed-route-config-digest") {
      if (options.reviewedRouteConfigDigest !== undefined) {
        throw new Error("--reviewed-route-config-digest must be specified only once");
      }
      options.reviewedRouteConfigDigest = requireLowerHex64(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--approved-at") {
      if (options.approvedAt !== undefined) throw new Error("--approved-at must be specified only once");
      options.approvedAt = requireNonNegativeSafeInteger(takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else {
      throw new Error(`unsupported browser-extension route-config option: ${arg}`);
    }
  }
  return options;
}

function routeConfigFromCli(options: RouteConfigCliOptions): unknown {
  if (options.routeAccountId === undefined) throw new Error("--route-account-id is required");
  if (options.routeType === undefined) throw new Error("--route-type is required");
  return {
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    account_id: options.routeAccountId,
    route_type: options.routeType
  };
}

function readJsonFile(path: string, label: string): unknown {
  const contents = readFileSync(path, "utf8");
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`${label} JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export function browserExtensionRouteConfigReviewJsonFromArgs(args: string[]): string {
  const options = parseRouteConfigCliArgs(args);
  if (options.reviewPath !== undefined) throw new Error("--review is only supported by route-config approve");
  if (options.reviewedRouteConfigDigest !== undefined) {
    throw new Error("--reviewed-route-config-digest is only supported by route-config approve");
  }
  if (options.approvedAt !== undefined) throw new Error("--approved-at is only supported by route-config approve");
  return `${JSON.stringify(createBrowserExtensionRouteConfigReview(routeConfigFromCli(options)), null, 2)}\n`;
}

export function browserExtensionRouteConfigApprovalJsonFromArgs(args: string[]): string {
  const options = parseRouteConfigCliArgs(args);
  if (options.routeAccountId !== undefined) throw new Error("--route-account-id is only supported by route-config review");
  if (options.routeType !== undefined) throw new Error("--route-type is only supported by route-config review");
  if (options.reviewPath === undefined) throw new Error("--review is required");
  if (options.reviewedRouteConfigDigest === undefined) throw new Error("--reviewed-route-config-digest is required");
  if (options.approvedAt === undefined) throw new Error("--approved-at is required");
  return `${JSON.stringify(approveBrowserExtensionRouteConfigReview(
    parseBrowserExtensionRouteConfigReview(readJsonFile(options.reviewPath, "browser extension route config review")),
    {
      reviewedRouteConfigDigest: options.reviewedRouteConfigDigest,
      approvedAt: options.approvedAt
    }
  ), null, 2)}\n`;
}

export async function runBrowserExtensionRouteConfigCli(command: string | undefined, args: string[]): Promise<void> {
  try {
    if (command === "review") {
      writeSync(1, browserExtensionRouteConfigReviewJsonFromArgs(args));
      return;
    }
    if (command === "approve") {
      writeSync(1, browserExtensionRouteConfigApprovalJsonFromArgs(args));
      return;
    }
    throw new Error("browser-extension route-config command must be review or approve");
  } catch (error) {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await runBrowserExtensionRouteConfigCli(process.argv[2], process.argv.slice(3));
}
