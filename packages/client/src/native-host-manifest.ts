import { dirname, isAbsolute } from "node:path";
import { sha256Utf8Hex } from "@nsealr/core";
import { NATIVE_HOST_NAME } from "./service.js";

export const NATIVE_HOST_DESCRIPTION = "nSealr companion native messaging host";
export const NATIVE_HOST_INSTALL_PLAN_FORMAT = "nsealr-native-host-install-plan-v0";
export const NATIVE_HOST_INSTALL_APPROVAL_FORMAT = "nsealr-native-host-install-approval-v0";
export const NATIVE_HOST_INSTALL_EXECUTION_FORMAT = "nsealr-native-host-install-execution-v0";

export type NativeHostBrowser = "chromium" | "firefox";

export type ChromiumNativeHostManifest = {
  name: string;
  description: string;
  path: string;
  type: "stdio";
  allowed_origins: string[];
};

export type FirefoxNativeHostManifest = {
  name: string;
  description: string;
  path: string;
  type: "stdio";
  allowed_extensions: string[];
};

export type NativeHostManifest = ChromiumNativeHostManifest | FirefoxNativeHostManifest;

export type NativeHostManifestOptions = {
  browser: NativeHostBrowser;
  hostPath: string;
  extensionIds: string[];
  name?: string;
  description?: string;
};

export type NativeHostInstallPlanOptions = NativeHostManifestOptions & {
  manifestPath: string;
};

export type NativeHostInstallPlan = {
  format: typeof NATIVE_HOST_INSTALL_PLAN_FORMAT;
  install_digest: string;
  browser: NativeHostBrowser;
  manifest_path: string;
  manifest: NativeHostManifest;
  would_create_directories: [{
    purpose: "native_host_manifest_parent";
    path: string;
    access: "ensure_directory";
    contains_secret_material: false;
  }];
  would_write_files: [{
    purpose: "native_host_manifest";
    path: string;
    access: "write_new";
    contains_secret_material: false;
  }];
  requires_user_approval: true;
  writes_files: false;
  stores_production_secrets: false;
};

export type NativeHostInstallApproval = {
  format: typeof NATIVE_HOST_INSTALL_APPROVAL_FORMAT;
  install_digest: string;
  approved_at: number;
  plan: NativeHostInstallPlan;
  requires_user_approval: true;
  writes_files: false;
  stores_production_secrets: false;
};

export type NativeHostInstallExecution = {
  format: typeof NATIVE_HOST_INSTALL_EXECUTION_FORMAT;
  install_digest: string;
  approved_at: number;
  browser: NativeHostBrowser;
  manifest_path: string;
  directories_ensured: [{
    purpose: "native_host_manifest_parent";
    path: string;
    access: "ensure_directory";
    contains_secret_material: false;
  }];
  files_written: [{
    purpose: "native_host_manifest";
    path: string;
    access: "write_new";
    bytes: number;
    sha256: string;
    contains_secret_material: false;
  }];
  requires_user_approval: true;
  writes_files: true;
  stores_production_secrets: false;
};

export type NativeHostInstallApprovalOptions = {
  reviewedInstallDigest: string;
  approvedAt: number;
};

export type NativeHostInstallExecutionOptions = {
  reviewedInstallDigest: string;
  writer: {
    ensureDirectory(path: string): Promise<void> | void;
    writeFileNew(path: string, contents: string): Promise<void> | void;
  };
};

type NativeHostInstallPlanWithoutDigest = Omit<NativeHostInstallPlan, "install_digest">;

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

function requirePositiveSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || !Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${label} must be a positive safe integer`);
  }
  return value;
}

function requireHostName(value: string | undefined): string {
  const name = value ?? NATIVE_HOST_NAME;
  if (!/^[a-z0-9_]+(?:\.[a-z0-9_]+)*$/u.test(name) || name.length > 128) {
    throw new Error("native host name is invalid");
  }
  return name;
}

function requireDescription(value: string | undefined): string {
  const description = value ?? NATIVE_HOST_DESCRIPTION;
  if (description.length === 0 || description.length > 160) {
    throw new Error("native host description is invalid");
  }
  return description;
}

function requireHostPath(value: string): string {
  if (value.length === 0 || !isAbsolute(value)) {
    throw new Error("native host path must be absolute");
  }
  return value;
}

function requireManifestPath(value: string): string {
  if (value.length === 0) {
    throw new Error("native host manifest path must not be empty");
  }
  if (value.length > 4096) {
    throw new Error("native host manifest path exceeds max length");
  }
  if (value.startsWith("~")) {
    throw new Error("native host manifest path must be expanded before planning");
  }
  if (!isAbsolute(value)) {
    throw new Error("native host manifest path must be absolute");
  }
  if (/[\0\r\n]/u.test(value)) {
    throw new Error("native host manifest path contains unsupported control characters");
  }
  const segments = value.split(/[\\/]+/u).filter((segment) => segment.length > 0);
  if (segments.some((segment) => segment === "." || segment === "..")) {
    throw new Error("native host manifest path must not contain relative segments");
  }
  if (!value.endsWith(".json")) {
    throw new Error("native host manifest path must end with .json");
  }
  return value;
}

function deduplicateNonEmptyStrings(values: string[], errorMessage: string): string[] {
  if (values.length === 0) {
    throw new Error(errorMessage);
  }
  return [...new Set(values)];
}

function chromiumOrigin(extensionId: string): string {
  if (!/^[a-p]{32}$/u.test(extensionId)) {
    throw new Error("chromium extension id is invalid");
  }
  return `chrome-extension://${extensionId}/`;
}

function firefoxExtensionId(extensionId: string): string {
  if (!/^[A-Za-z0-9._@+-]{1,128}$/u.test(extensionId)) {
    throw new Error("firefox extension id is invalid");
  }
  return extensionId;
}

export function buildNativeHostManifest(options: NativeHostManifestOptions): NativeHostManifest {
  const base = {
    name: requireHostName(options.name),
    description: requireDescription(options.description),
    path: requireHostPath(options.hostPath),
    type: "stdio" as const
  };
  const extensionIds = deduplicateNonEmptyStrings(options.extensionIds, "at least one extension id is required");

  if (options.browser === "chromium") {
    return {
      ...base,
      allowed_origins: extensionIds.map(chromiumOrigin)
    };
  }
  if (options.browser === "firefox") {
    return {
      ...base,
      allowed_extensions: extensionIds.map(firefoxExtensionId)
    };
  }
  throw new Error("native host browser is unsupported");
}

function parseNativeHostBrowser(value: unknown): NativeHostBrowser {
  if (value !== "chromium" && value !== "firefox") {
    throw new Error("native host browser is unsupported");
  }
  return value;
}

function parseNativeHostManifest(value: unknown, browser: NativeHostBrowser): NativeHostManifest {
  if (!isRecord(value)) throw new Error("native host manifest must be an object");
  const baseKeys = ["name", "description", "path", "type"];
  const browserKeys = browser === "chromium" ? ["allowed_origins"] : ["allowed_extensions"];
  if (!hasOnlyKeys(value, [...baseKeys, ...browserKeys])) {
    throw new Error("native host manifest has unsupported fields");
  }
  if (typeof value.name !== "string") throw new Error("native host name is invalid");
  const name = requireHostName(value.name);
  if (typeof value.description !== "string") throw new Error("native host description is invalid");
  const description = requireDescription(value.description);
  if (typeof value.path !== "string") throw new Error("native host path must be absolute");
  const path = requireHostPath(value.path);
  if (value.type !== "stdio") throw new Error("native host type is unsupported");
  if (browser === "chromium") {
    if (!Array.isArray(value.allowed_origins) || value.allowed_origins.length === 0) {
      throw new Error("chromium native host allowed origins are invalid");
    }
    const allowedOrigins = value.allowed_origins.map((origin) => {
      if (typeof origin !== "string" || !origin.startsWith("chrome-extension://") || !origin.endsWith("/")) {
        throw new Error("chromium native host allowed origin is invalid");
      }
      const extensionId = origin.slice("chrome-extension://".length, -1);
      return chromiumOrigin(extensionId);
    });
    return {
      name,
      description,
      path,
      type: "stdio",
      allowed_origins: deduplicateNonEmptyStrings(
        allowedOrigins,
        "chromium native host allowed origins are invalid"
      )
    };
  }
  if (!Array.isArray(value.allowed_extensions) || value.allowed_extensions.length === 0) {
    throw new Error("firefox native host allowed extensions are invalid");
  }
  const allowedExtensions = value.allowed_extensions.map((extensionId) => {
    if (typeof extensionId !== "string") throw new Error("firefox extension id is invalid");
    return firefoxExtensionId(extensionId);
  });
  return {
    name,
    description,
    path,
    type: "stdio",
    allowed_extensions: deduplicateNonEmptyStrings(
      allowedExtensions,
      "firefox native host allowed extensions are invalid"
    )
  };
}

function nativeHostInstallPlanDigest(plan: NativeHostInstallPlanWithoutDigest): string {
  return sha256Utf8Hex(JSON.stringify(plan));
}

export function buildNativeHostInstallPlan(options: NativeHostInstallPlanOptions): NativeHostInstallPlan {
  const manifest = buildNativeHostManifest(options);
  const manifestPath = requireManifestPath(options.manifestPath);
  const manifestParent = dirname(manifestPath);
  const withoutDigest: NativeHostInstallPlanWithoutDigest = {
    format: NATIVE_HOST_INSTALL_PLAN_FORMAT,
    browser: options.browser,
    manifest_path: manifestPath,
    manifest,
    would_create_directories: [{
      purpose: "native_host_manifest_parent",
      path: manifestParent,
      access: "ensure_directory",
      contains_secret_material: false
    }],
    would_write_files: [{
      purpose: "native_host_manifest",
      path: manifestPath,
      access: "write_new",
      contains_secret_material: false
    }],
    requires_user_approval: true,
    writes_files: false,
    stores_production_secrets: false
  };
  return {
    ...withoutDigest,
    install_digest: nativeHostInstallPlanDigest(withoutDigest)
  };
}

export function parseNativeHostInstallPlan(value: unknown): NativeHostInstallPlan {
  if (!isRecord(value)) throw new Error("native host install plan must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "install_digest",
    "browser",
    "manifest_path",
    "manifest",
    "would_create_directories",
    "would_write_files",
    "requires_user_approval",
    "writes_files",
    "stores_production_secrets"
  ])) {
    throw new Error("native host install plan has unsupported fields");
  }
  if (value.format !== NATIVE_HOST_INSTALL_PLAN_FORMAT) {
    throw new Error("native host install plan format is unsupported");
  }
  const browser = parseNativeHostBrowser(value.browser);
  if (typeof value.manifest_path !== "string") throw new Error("native host manifest path must be absolute");
  const manifestPath = requireManifestPath(value.manifest_path);
  const manifestParent = dirname(manifestPath);
  const manifest = parseNativeHostManifest(value.manifest, browser);
  if (!Array.isArray(value.would_create_directories) || value.would_create_directories.length !== 1) {
    throw new Error("native host install plan directory intent is invalid");
  }
  const [directoryIntent] = value.would_create_directories;
  if (!isRecord(directoryIntent) || !hasOnlyKeys(directoryIntent, [
    "purpose",
    "path",
    "access",
    "contains_secret_material"
  ])) {
    throw new Error("native host install plan directory intent is invalid");
  }
  if (
    directoryIntent.purpose !== "native_host_manifest_parent" ||
    directoryIntent.path !== manifestParent ||
    directoryIntent.access !== "ensure_directory" ||
    directoryIntent.contains_secret_material !== false
  ) {
    throw new Error("native host install plan directory intent is invalid");
  }
  if (!Array.isArray(value.would_write_files) || value.would_write_files.length !== 1) {
    throw new Error("native host install plan write intent is invalid");
  }
  const [writeIntent] = value.would_write_files;
  if (!isRecord(writeIntent) || !hasOnlyKeys(writeIntent, [
    "purpose",
    "path",
    "access",
    "contains_secret_material"
  ])) {
    throw new Error("native host install plan write intent is invalid");
  }
  if (
    writeIntent.purpose !== "native_host_manifest" ||
    writeIntent.path !== manifestPath ||
    writeIntent.access !== "write_new" ||
    writeIntent.contains_secret_material !== false
  ) {
    throw new Error("native host install plan write intent is invalid");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("native host install plan must require user approval");
  }
  if (value.writes_files !== false) {
    throw new Error("native host install plan must not write files");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("native host install plan must not store production secrets");
  }
  const withoutDigest: NativeHostInstallPlanWithoutDigest = {
    format: NATIVE_HOST_INSTALL_PLAN_FORMAT,
    browser,
    manifest_path: manifestPath,
    manifest,
    would_create_directories: [{
      purpose: "native_host_manifest_parent",
      path: manifestParent,
      access: "ensure_directory",
      contains_secret_material: false
    }],
    would_write_files: [{
      purpose: "native_host_manifest",
      path: manifestPath,
      access: "write_new",
      contains_secret_material: false
    }],
    requires_user_approval: true,
    writes_files: false,
    stores_production_secrets: false
  };
  const installDigest = requireHex64(value.install_digest, "native host install plan digest");
  if (installDigest !== nativeHostInstallPlanDigest(withoutDigest)) {
    throw new Error("native host install plan digest mismatch");
  }
  return {
    ...withoutDigest,
    install_digest: installDigest
  };
}

export function approveNativeHostInstallPlan(
  plan: unknown,
  options: NativeHostInstallApprovalOptions
): NativeHostInstallApproval {
  const parsedPlan = parseNativeHostInstallPlan(plan);
  const reviewedInstallDigest = requireHex64(options.reviewedInstallDigest, "reviewedInstallDigest");
  if (reviewedInstallDigest !== parsedPlan.install_digest) {
    throw new Error("reviewed install digest does not match native host install plan");
  }
  return parseNativeHostInstallApproval({
    format: NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
    install_digest: parsedPlan.install_digest,
    approved_at: requireNonNegativeSafeInteger(options.approvedAt, "approvedAt"),
    plan: parsedPlan,
    requires_user_approval: true,
    writes_files: false,
    stores_production_secrets: false
  });
}

export function parseNativeHostInstallApproval(value: unknown): NativeHostInstallApproval {
  if (!isRecord(value)) throw new Error("native host install approval must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "install_digest",
    "approved_at",
    "plan",
    "requires_user_approval",
    "writes_files",
    "stores_production_secrets"
  ])) {
    throw new Error("native host install approval has unsupported fields");
  }
  if (value.format !== NATIVE_HOST_INSTALL_APPROVAL_FORMAT) {
    throw new Error("native host install approval format is unsupported");
  }
  const installDigest = requireHex64(value.install_digest, "native host install approval digest");
  const plan = parseNativeHostInstallPlan(value.plan);
  if (plan.install_digest !== installDigest) {
    throw new Error("native host install approval digest mismatch");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("native host install approval must require user approval");
  }
  if (value.writes_files !== false) {
    throw new Error("native host install approval must not write files");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("native host install approval must not store production secrets");
  }
  return {
    format: NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
    install_digest: installDigest,
    approved_at: requireNonNegativeSafeInteger(value.approved_at, "native host install approval approved_at"),
    plan,
    requires_user_approval: true,
    writes_files: false,
    stores_production_secrets: false
  };
}

export async function executeNativeHostInstallApproval(
  approval: unknown,
  options: NativeHostInstallExecutionOptions
): Promise<NativeHostInstallExecution> {
  const parsedApproval = parseNativeHostInstallApproval(approval);
  const reviewedInstallDigest = requireHex64(options.reviewedInstallDigest, "reviewedInstallDigest");
  if (reviewedInstallDigest !== parsedApproval.install_digest) {
    throw new Error("reviewed install digest does not match native host install approval");
  }
  if (
    !isRecord(options.writer) ||
    typeof options.writer.ensureDirectory !== "function" ||
    typeof options.writer.writeFileNew !== "function"
  ) {
    throw new Error("native host install writer is invalid");
  }

  const [directoryIntent] = parsedApproval.plan.would_create_directories;
  const [writeIntent] = parsedApproval.plan.would_write_files;
  const manifestJson = `${JSON.stringify(parsedApproval.plan.manifest, null, 2)}\n`;
  await options.writer.ensureDirectory(directoryIntent.path);
  await options.writer.writeFileNew(writeIntent.path, manifestJson);

  return parseNativeHostInstallExecution({
    format: NATIVE_HOST_INSTALL_EXECUTION_FORMAT,
    install_digest: parsedApproval.install_digest,
    approved_at: parsedApproval.approved_at,
    browser: parsedApproval.plan.browser,
    manifest_path: parsedApproval.plan.manifest_path,
    directories_ensured: [{
      purpose: "native_host_manifest_parent",
      path: directoryIntent.path,
      access: "ensure_directory",
      contains_secret_material: false
    }],
    files_written: [{
      purpose: "native_host_manifest",
      path: writeIntent.path,
      access: "write_new",
      bytes: new TextEncoder().encode(manifestJson).byteLength,
      sha256: sha256Utf8Hex(manifestJson),
      contains_secret_material: false
    }],
    requires_user_approval: true,
    writes_files: true,
    stores_production_secrets: false
  });
}

export function parseNativeHostInstallExecution(value: unknown): NativeHostInstallExecution {
  if (!isRecord(value)) throw new Error("native host install execution must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "install_digest",
    "approved_at",
    "browser",
    "manifest_path",
    "directories_ensured",
    "files_written",
    "requires_user_approval",
    "writes_files",
    "stores_production_secrets"
  ])) {
    throw new Error("native host install execution has unsupported fields");
  }
  if (value.format !== NATIVE_HOST_INSTALL_EXECUTION_FORMAT) {
    throw new Error("native host install execution format is unsupported");
  }
  const installDigest = requireHex64(value.install_digest, "native host install execution digest");
  const browser = parseNativeHostBrowser(value.browser);
  if (typeof value.manifest_path !== "string") throw new Error("native host manifest path must be absolute");
  const manifestPath = requireManifestPath(value.manifest_path);
  const manifestParent = dirname(manifestPath);
  if (!Array.isArray(value.directories_ensured) || value.directories_ensured.length !== 1) {
    throw new Error("native host install execution directory report is invalid");
  }
  const [directoryReport] = value.directories_ensured;
  if (!isRecord(directoryReport) || !hasOnlyKeys(directoryReport, [
    "purpose",
    "path",
    "access",
    "contains_secret_material"
  ])) {
    throw new Error("native host install execution directory report is invalid");
  }
  if (
    directoryReport.purpose !== "native_host_manifest_parent" ||
    directoryReport.path !== manifestParent ||
    directoryReport.access !== "ensure_directory" ||
    directoryReport.contains_secret_material !== false
  ) {
    throw new Error("native host install execution directory report is invalid");
  }
  if (!Array.isArray(value.files_written) || value.files_written.length !== 1) {
    throw new Error("native host install execution file report is invalid");
  }
  const [fileReport] = value.files_written;
  if (!isRecord(fileReport) || !hasOnlyKeys(fileReport, [
    "purpose",
    "path",
    "access",
    "bytes",
    "sha256",
    "contains_secret_material"
  ])) {
    throw new Error("native host install execution file report is invalid");
  }
  if (
    fileReport.purpose !== "native_host_manifest" ||
    fileReport.path !== manifestPath ||
    fileReport.access !== "write_new" ||
    fileReport.contains_secret_material !== false
  ) {
    throw new Error("native host install execution file report is invalid");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("native host install execution must require user approval");
  }
  if (value.writes_files !== true) {
    throw new Error("native host install execution must report file writes");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("native host install execution must not store production secrets");
  }
  return {
    format: NATIVE_HOST_INSTALL_EXECUTION_FORMAT,
    install_digest: installDigest,
    approved_at: requireNonNegativeSafeInteger(value.approved_at, "native host install execution approved_at"),
    browser,
    manifest_path: manifestPath,
    directories_ensured: [{
      purpose: "native_host_manifest_parent",
      path: manifestParent,
      access: "ensure_directory",
      contains_secret_material: false
    }],
    files_written: [{
      purpose: "native_host_manifest",
      path: manifestPath,
      access: "write_new",
      bytes: requirePositiveSafeInteger(fileReport.bytes, "native host install execution bytes"),
      sha256: requireHex64(fileReport.sha256, "native host install execution sha256"),
      contains_secret_material: false
    }],
    requires_user_approval: true,
    writes_files: true,
    stores_production_secrets: false
  };
}
