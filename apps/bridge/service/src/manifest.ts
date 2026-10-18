import { readFileSync } from "node:fs";
import {
  approveNativeHostInstallPlan,
  buildNativeHostInstallPlan,
  buildNativeHostManifest,
  executeNativeHostInstallApproval,
  parseNativeHostInstallPlan,
  type NativeHostInstallPlan,
  type NativeHostInstallApproval,
  type NativeHostInstallExecution,
  type NativeHostInstallExecutionOptions,
  type NativeHostBrowser,
  type NativeHostManifest
} from "@nsealr/client";

export {
  NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
  NATIVE_HOST_INSTALL_EXECUTION_FORMAT,
  NATIVE_HOST_DESCRIPTION,
  NATIVE_HOST_NAME,
  NATIVE_HOST_INSTALL_PLAN_FORMAT,
  approveNativeHostInstallPlan,
  buildNativeHostInstallPlan,
  buildNativeHostManifest,
  executeNativeHostInstallApproval,
  parseNativeHostInstallExecution,
  parseNativeHostInstallApproval,
  parseNativeHostInstallPlan,
  type ChromiumNativeHostManifest,
  type FirefoxNativeHostManifest,
  type NativeHostInstallApproval,
  type NativeHostInstallApprovalOptions,
  type NativeHostInstallExecution,
  type NativeHostInstallExecutionOptions,
  type NativeHostInstallPlan,
  type NativeHostInstallPlanOptions,
  type NativeHostBrowser,
  type NativeHostManifest,
  type NativeHostManifestOptions
} from "@nsealr/client";

function takeOptionValue(args: string[], index: number, option: string): string {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

function setSingletonOption<T>(current: T | undefined, value: T, option: string): T {
  if (current !== undefined) {
    throw new Error(`${option} is duplicated`);
  }
  return value;
}

export function nativeHostManifestFromArgs(args: string[]): NativeHostManifest {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  let browser: NativeHostBrowser | undefined;
  let hostPath: string | undefined;
  let manifestPath: string | undefined;
  let name: string | undefined;
  let description: string | undefined;
  const extensionIds: string[] = [];

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--native-host-manifest") {
      const value = takeOptionValue(normalizedArgs, index, arg);
      if (value !== "chromium" && value !== "firefox") {
        throw new Error("native host manifest browser must be chromium or firefox");
      }
      browser = setSingletonOption(browser, value, arg);
      index += 1;
    } else if (arg === "--host-path") {
      hostPath = setSingletonOption(hostPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--manifest-path") {
      manifestPath = setSingletonOption(manifestPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--extension-id") {
      extensionIds.push(takeOptionValue(normalizedArgs, index, arg));
      index += 1;
    } else if (arg === "--host-name") {
      name = setSingletonOption(name, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--description") {
      description = setSingletonOption(description, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else {
      throw new Error(`unsupported service option: ${arg}`);
    }
  }

  if (browser === undefined) throw new Error("--native-host-manifest is required");
  if (manifestPath !== undefined) throw new Error("--manifest-path is only supported with --native-host-install-plan");
  if (hostPath === undefined) throw new Error("--host-path is required");
  return buildNativeHostManifest({
    browser,
    hostPath,
    extensionIds,
    name,
    description
  });
}

export function nativeHostManifestJsonFromArgs(args: string[]): string {
  return `${JSON.stringify(nativeHostManifestFromArgs(args), null, 2)}\n`;
}

export function nativeHostInstallPlanFromArgs(args: string[]): NativeHostInstallPlan {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  let browser: NativeHostBrowser | undefined;
  let hostPath: string | undefined;
  let manifestPath: string | undefined;
  let name: string | undefined;
  let description: string | undefined;
  const extensionIds: string[] = [];

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--native-host-install-plan") {
      const value = takeOptionValue(normalizedArgs, index, arg);
      if (value !== "chromium" && value !== "firefox") {
        throw new Error("native host install-plan browser must be chromium or firefox");
      }
      browser = setSingletonOption(browser, value, arg);
      index += 1;
    } else if (arg === "--native-host-manifest") {
      throw new Error("--native-host-manifest is only supported without --native-host-install-plan");
    } else if (arg === "--host-path") {
      hostPath = setSingletonOption(hostPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--manifest-path") {
      manifestPath = setSingletonOption(manifestPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--extension-id") {
      extensionIds.push(takeOptionValue(normalizedArgs, index, arg));
      index += 1;
    } else if (arg === "--host-name") {
      name = setSingletonOption(name, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--description") {
      description = setSingletonOption(description, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else {
      throw new Error(`unsupported service option: ${arg}`);
    }
  }

  if (browser === undefined) throw new Error("--native-host-install-plan is required");
  if (hostPath === undefined) throw new Error("--host-path is required");
  if (manifestPath === undefined) throw new Error("--manifest-path is required");
  return buildNativeHostInstallPlan({
    browser,
    hostPath,
    manifestPath,
    extensionIds,
    name,
    description
  });
}

export function nativeHostInstallPlanJsonFromArgs(args: string[]): string {
  return `${JSON.stringify(nativeHostInstallPlanFromArgs(args), null, 2)}\n`;
}

function readJsonFile(path: string, label: string): unknown {
  const contents = readFileSync(path, "utf8");
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`${label} JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
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

function requireLowerHex64(value: string, option: string): string {
  if (!/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${option} must be 32-byte lowercase hex`);
  }
  return value;
}

export function nativeHostInstallApprovalFromArgs(args: string[]): NativeHostInstallApproval {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  let planPath: string | undefined;
  let reviewedInstallDigest: string | undefined;
  let approvedAt: number | undefined;

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--native-host-install-approval") {
      planPath = setSingletonOption(planPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--reviewed-install-digest") {
      reviewedInstallDigest = setSingletonOption(
        reviewedInstallDigest,
        requireLowerHex64(takeOptionValue(normalizedArgs, index, arg), arg),
        arg
      );
      index += 1;
    } else if (arg === "--approved-at") {
      approvedAt = setSingletonOption(
        approvedAt,
        requireNonNegativeSafeInteger(takeOptionValue(normalizedArgs, index, arg), arg),
        arg
      );
      index += 1;
    } else {
      throw new Error(`unsupported service option: ${arg}`);
    }
  }

  if (planPath === undefined) throw new Error("--native-host-install-approval is required");
  if (reviewedInstallDigest === undefined) throw new Error("--reviewed-install-digest is required");
  if (approvedAt === undefined) throw new Error("--approved-at is required");
  return approveNativeHostInstallPlan(parseNativeHostInstallPlan(
    readJsonFile(planPath, "native host install plan")
  ), {
    reviewedInstallDigest,
    approvedAt
  });
}

export function nativeHostInstallApprovalJsonFromArgs(args: string[]): string {
  return `${JSON.stringify(nativeHostInstallApprovalFromArgs(args), null, 2)}\n`;
}

export async function nativeHostInstallExecutionFromArgs(
  args: string[],
  writer: NativeHostInstallExecutionOptions["writer"]
): Promise<NativeHostInstallExecution> {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  let approvalPath: string | undefined;
  let reviewedInstallDigest: string | undefined;

  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--native-host-install-execute") {
      approvalPath = setSingletonOption(approvalPath, takeOptionValue(normalizedArgs, index, arg), arg);
      index += 1;
    } else if (arg === "--reviewed-install-digest") {
      reviewedInstallDigest = setSingletonOption(
        reviewedInstallDigest,
        requireLowerHex64(takeOptionValue(normalizedArgs, index, arg), arg),
        arg
      );
      index += 1;
    } else {
      throw new Error(`unsupported service option: ${arg}`);
    }
  }

  if (approvalPath === undefined) throw new Error("--native-host-install-execute is required");
  if (reviewedInstallDigest === undefined) throw new Error("--reviewed-install-digest is required");
  return executeNativeHostInstallApproval(readJsonFile(
    approvalPath,
    "native host install approval"
  ), {
    reviewedInstallDigest,
    writer
  });
}

export async function nativeHostInstallExecutionJsonFromArgs(
  args: string[],
  writer: NativeHostInstallExecutionOptions["writer"]
): Promise<string> {
  return `${JSON.stringify(await nativeHostInstallExecutionFromArgs(args, writer), null, 2)}\n`;
}
