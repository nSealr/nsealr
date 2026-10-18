#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";
import {
  BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT,
  buildBrowserExtensionPackage,
  type BrowserExtensionPackageOriginPermissionMode
} from "./package-build.js";
import {
  BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT
} from "./route-config.js";
import {
  type BrowserExtensionManifestOptions,
  type BrowserExtensionTarget
} from "./manifest.js";

type PackageBuildCliOptions = {
  target?: BrowserExtensionTarget;
  outDir?: string;
  packagePlanReviewPath?: string;
  firefoxExtensionId?: string;
  contentScriptMatches: string[];
  routeAccountId?: string;
  routeType?: string;
  routeConfigApprovalPath?: string;
  extensionId?: string;
  originPermissionMode?: BrowserExtensionPackageOriginPermissionMode;
  originPermissionStorePath?: string;
  localPairingDigest?: string;
};

function takeOptionValue(args: string[], index: number, option: string): string {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

function parsePackageBuildArgs(args: string[]): PackageBuildCliOptions {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const options: PackageBuildCliOptions = {
    contentScriptMatches: []
  };

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--target") {
      if (options.target !== undefined) throw new Error("--target must be specified only once");
      const target = takeOptionValue(normalizedArgs, index, arg);
      if (target !== "chromium" && target !== "firefox") throw new Error("--target must be chromium or firefox");
      options.target = target;
      index += 1;
    } else if (arg === "--out-dir") {
      if (options.outDir !== undefined) throw new Error("--out-dir must be specified only once");
      options.outDir = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--package-plan-review") {
      if (options.packagePlanReviewPath !== undefined) {
        throw new Error("--package-plan-review must be specified only once");
      }
      options.packagePlanReviewPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--package-plan-digest") {
      throw new Error("--package-plan-review is required; --package-plan-digest is unsupported");
    } else if (arg === "--firefox-extension-id") {
      if (options.firefoxExtensionId !== undefined) throw new Error("--firefox-extension-id must be specified only once");
      options.firefoxExtensionId = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--content-script-match") {
      options.contentScriptMatches.push(takeOptionValue(normalizedArgs, index, arg));
      index += 1;
    } else if (arg === "--route-account-id") {
      if (options.routeAccountId !== undefined) throw new Error("--route-account-id must be specified only once");
      options.routeAccountId = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--route-type") {
      if (options.routeType !== undefined) throw new Error("--route-type must be specified only once");
      options.routeType = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--route-config-approval") {
      if (options.routeConfigApprovalPath !== undefined) {
        throw new Error("--route-config-approval must be specified only once");
      }
      options.routeConfigApprovalPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--extension-id") {
      if (options.extensionId !== undefined) throw new Error("--extension-id must be specified only once");
      options.extensionId = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--origin-permission-mode") {
      if (options.originPermissionMode !== undefined) {
        throw new Error("--origin-permission-mode must be specified only once");
      }
      const mode = takeOptionValue(normalizedArgs, index, arg);
      if (mode !== "embedded" && mode !== "extension-storage") {
        throw new Error("--origin-permission-mode must be embedded or extension-storage");
      }
      options.originPermissionMode = mode === "extension-storage" ? "extension_storage" : "embedded";
      index += 1;
    } else if (arg === "--origin-permission-store") {
      if (options.originPermissionStorePath !== undefined) {
        throw new Error("--origin-permission-store must be specified only once");
      }
      options.originPermissionStorePath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--local-pairing-digest") {
      if (options.localPairingDigest !== undefined) {
        throw new Error("--local-pairing-digest must be specified only once");
      }
      options.localPairingDigest = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else {
      throw new Error(`unsupported browser-extension package-build option: ${arg}`);
    }
  }

  return options;
}

function manifestOptionsFromCli(options: PackageBuildCliOptions): BrowserExtensionManifestOptions {
  if (options.target === undefined) throw new Error("--target is required");
  if (options.target === "chromium" && options.firefoxExtensionId !== undefined) {
    throw new Error("--firefox-extension-id is only valid for Firefox package builds");
  }
  return {
    target: options.target,
    ...(options.firefoxExtensionId !== undefined ? { firefoxExtensionId: options.firefoxExtensionId } : {}),
    ...(options.contentScriptMatches.length > 0 ? { contentScriptMatches: options.contentScriptMatches } : {})
  };
}

function routeConfigFromCli(options: PackageBuildCliOptions): unknown {
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

export async function browserExtensionPackageBuildJsonFromArgs(args: string[]): Promise<string> {
  const options = parsePackageBuildArgs(args);
  if (options.outDir === undefined) throw new Error("--out-dir is required");
  if (options.routeConfigApprovalPath === undefined) throw new Error("--route-config-approval is required");
  if (options.packagePlanReviewPath === undefined) throw new Error("--package-plan-review is required");
  const result = await buildBrowserExtensionPackage({
    ...manifestOptionsFromCli(options),
    outDir: options.outDir,
    packagePlanReview: readJsonFile(options.packagePlanReviewPath, "browser extension package-plan review"),
    routeConfig: routeConfigFromCli(options),
    routeConfigApproval: readJsonFile(options.routeConfigApprovalPath, "browser extension route config approval"),
    ...(options.extensionId !== undefined ? { extensionId: options.extensionId } : {}),
    ...(options.originPermissionMode !== undefined ? { originPermissionMode: options.originPermissionMode } : {}),
    ...(options.originPermissionStorePath !== undefined
      ? {
          originPermissionStore: readJsonFile(
            options.originPermissionStorePath,
            "browser extension origin permission store"
          )
        }
      : {}),
    ...(options.localPairingDigest !== undefined ? { localPairingDigest: options.localPairingDigest } : {})
  });
  return `${JSON.stringify(result, null, 2)}\n`;
}

export async function runBrowserExtensionPackageBuildCli(args: string[]): Promise<void> {
  try {
    const resultJson = await browserExtensionPackageBuildJsonFromArgs(args);
    const result = JSON.parse(resultJson) as { format?: string };
    if (result.format !== BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT) {
      throw new Error("browser extension package build returned unsupported output");
    }
    writeSync(1, resultJson);
  } catch (error) {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await runBrowserExtensionPackageBuildCli(process.argv.slice(2));
}
