import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { basename, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { sha256Utf8Hex } from "@nsealr/core";
import { NATIVE_HOST_NAME } from "@nsealr/client";
import { build as esbuild, type Plugin } from "esbuild";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";
import {
  assertBrowserExtensionPackagePlan,
  browserExtensionPackagePlanDigest,
  buildBrowserExtensionPackagePlan,
  parseBrowserExtensionPackagePlanReview,
  type BrowserExtensionPackagePlan,
  type BrowserExtensionPackagePlanReview
} from "./package-plan.js";
import {
  BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
  browserExtensionRouteConfigDigest,
  parseBrowserExtensionRouteConfigApproval,
  parseBrowserExtensionRouteConfig,
  type BrowserExtensionDispatchableRouteType
} from "./route-config.js";
import {
  type BrowserExtensionManifestOptions,
  type BrowserExtensionManifestPermission
} from "./manifest.js";
import {
  isBrowserExtensionOriginMethodAllowed,
  parseBrowserExtensionOriginPermissionStore,
  type BrowserExtensionOriginPermissionStore
} from "./origin-permission-store.js";
import { browserExtensionPopupHtml } from "./popup-html.js";

export const BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT = "nsealr-browser-extension-package-build-v0";
export type BrowserExtensionPackageOriginPermissionMode = "embedded" | "extension_storage";

export type BrowserExtensionPackageBuildOptions = BrowserExtensionManifestOptions & {
  outDir: string;
  packagePlanReview: unknown;
  routeConfig: unknown;
  routeConfigApproval: unknown;
  extensionId?: string;
  originPermissionMode?: BrowserExtensionPackageOriginPermissionMode;
  originPermissionStore?: unknown;
  localPairingDigest?: string;
};

export type BrowserExtensionPackageBuildFile = {
  path:
    "manifest.json" |
    typeof BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE |
    typeof BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE |
    typeof BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE |
    typeof BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE |
    typeof BROWSER_EXTENSION_POPUP_HTML_FILE;
  bytes: number;
  sha256: string;
};

export type BrowserExtensionPackageBuildResult = {
  format: typeof BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT;
  target: BrowserExtensionManifestOptions["target"];
  out_dir: string;
  package_plan_digest: string;
  route_config_digest: string;
  route_account_id: string;
  route_type: BrowserExtensionDispatchableRouteType;
  native_host_name: typeof NATIVE_HOST_NAME;
  popup_mode: BrowserExtensionPackagePlan["popup_mode"];
  manifest_permissions: readonly BrowserExtensionManifestPermission[];
  origin_permission_mode: "none" | BrowserExtensionPackageOriginPermissionMode;
  extension_id?: string;
  local_pairing_digest?: string;
  content_script_origins: readonly string[];
  package_digest: string;
  files: readonly BrowserExtensionPackageBuildFile[];
  installs_native_host_manifest: false;
  writes_extension_storage: false;
  stores_production_secrets: false;
  dispatches_signers: false;
  uses_active_tab_permission: boolean;
  embeds_origin_permission_store: boolean;
  uses_extension_origin_permission_storage: boolean;
};

export type BrowserExtensionPackageVerifyOptions = {
  packagePlanReview: unknown;
};

const PACKAGE_OUTPUT_DIR = "browser-extension-package";
const COMPANION_ROOT = fileURLToPath(new URL("../../..", import.meta.url));
const REVIEWED_REPO_OUTPUT_ROOT = resolve(COMPANION_ROOT, "release-artifacts/browser-extension");
const PACKAGE_DIGEST_INPUT_FORMAT = "nsealr-browser-extension-package-digest-v0";
const nodeBufferReference = /(?:\bBuffer\s*(?:\.|\[)|new\s+Buffer\b|typeof\s+Buffer|globalThis\.Buffer)/u;
const nodeProcessReference = /(?:\bprocess\s*(?:\.|\[)|typeof\s+process|globalThis\.process)/u;
const textEncoder = new TextEncoder();
const PACKAGE_BUILD_FILE_PATHS = Object.freeze([
  "manifest.json",
  BROWSER_EXTENSION_POPUP_HTML_FILE,
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE
] as const);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: readonly string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function isPathInside(root: string, candidate: string): boolean {
  const relativePath = relative(root, candidate);
  return relativePath === "" || (!relativePath.startsWith("..") && !isAbsolute(relativePath));
}

function isReviewedRepoOutputPath(outDir: string): boolean {
  const relativePath = relative(REVIEWED_REPO_OUTPUT_ROOT, outDir);
  return relativePath !== "" && !relativePath.startsWith("..") && !isAbsolute(relativePath);
}

async function pathExists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

function requireSafePackageOutputPath(outDir: string): string {
  if (outDir === "/" || outDir === process.cwd()) {
    throw new Error("browser extension package out-dir is unsafe");
  }
  if (isPathInside(COMPANION_ROOT, outDir) && !isReviewedRepoOutputPath(outDir)) {
    throw new Error(
      "browser extension package out-dir must be outside the companion source tree or a child of release-artifacts/browser-extension/"
    );
  }
  return outDir;
}

function requireOutDir(value: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error("browser extension package out-dir is required");
  }
  const outDir = resolve(value);
  return requireSafePackageOutputPath(outDir);
}

function requireLowerHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function requirePositiveSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || !Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${label} must be a positive safe integer`);
  }
  return value;
}

function requireAbsoluteResultPath(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0 || !isAbsolute(value) || /[\0\r\n]/u.test(value)) {
    throw new Error(`${label} must be an absolute path`);
  }
  return value;
}

function requireTarget(value: unknown): BrowserExtensionManifestOptions["target"] {
  if (value !== "chromium" && value !== "firefox") {
    throw new Error("browser extension package build target is unsupported");
  }
  return value;
}

function requirePopupMode(value: unknown): BrowserExtensionPackagePlan["popup_mode"] {
  if (value !== "pending_requests" && value !== "origin_permission_approval") {
    throw new Error("browser extension package build popup mode is unsupported");
  }
  return value;
}

function requirePackageBuildOriginPermissionMode(value: unknown): BrowserExtensionPackageBuildResult["origin_permission_mode"] {
  if (value !== "none" && value !== "embedded" && value !== "extension_storage") {
    throw new Error("browser extension package build origin permission mode is unsupported");
  }
  return value;
}

function requireNativeHostName(value: unknown): typeof NATIVE_HOST_NAME {
  if (value !== NATIVE_HOST_NAME) {
    throw new Error("browser extension package build native host name drifted");
  }
  return NATIVE_HOST_NAME;
}

function requireFalse(value: unknown, label: string): false {
  if (value !== false) {
    throw new Error(`${label} must be false`);
  }
  return false;
}

function requireBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(`${label} must be boolean`);
  }
  return value;
}

function requireContentScriptOrigins(value: unknown): string[] {
  if (!Array.isArray(value)) {
    throw new Error("browser extension package build content_script_origins must be an array");
  }
  const origins = value.map((origin) => {
    if (typeof origin !== "string") {
      throw new Error("browser extension package build content script origin is invalid");
    }
    try {
      const url = new URL(origin);
      if (url.origin !== origin || url.origin === "null") {
        throw new Error("invalid origin");
      }
      return origin;
    } catch {
      throw new Error("browser extension package build content script origin is invalid");
    }
  });
  if (new Set(origins).size !== origins.length || [...origins].sort().join("\n") !== origins.join("\n")) {
    throw new Error("browser extension package build content_script_origins must be sorted and unique");
  }
  return origins;
}

function requireManifestPermissions(value: unknown): BrowserExtensionManifestPermission[] {
  if (!Array.isArray(value)) {
    throw new Error("browser extension package build manifest_permissions must be an array");
  }
  const allowed = new Set(["nativeMessaging", "activeTab", "storage"]);
  const permissions = value.map((permission) => {
    if (typeof permission !== "string" || !allowed.has(permission)) {
      throw new Error("browser extension package build manifest permission is unsupported");
    }
    return permission as BrowserExtensionManifestPermission;
  });
  if (new Set(permissions).size !== permissions.length) {
    throw new Error("browser extension package build manifest_permissions must be unique");
  }
  return permissions;
}

function requirePackageFile(value: unknown, expectedPath: BrowserExtensionPackageBuildFile["path"]): BrowserExtensionPackageBuildFile {
  if (!isRecord(value)) {
    throw new Error("browser extension package build file entry must be an object");
  }
  if (!hasOnlyKeys(value, ["path", "bytes", "sha256"])) {
    throw new Error("browser extension package build file entry has unsupported fields");
  }
  if (value.path !== expectedPath) {
    throw new Error(`browser extension package build file entry must be ${expectedPath}`);
  }
  return Object.freeze({
    path: expectedPath,
    bytes: requirePositiveSafeInteger(value.bytes, `browser extension package build ${expectedPath} bytes`),
    sha256: requireLowerHex64(value.sha256, `browser extension package build ${expectedPath} sha256`)
  });
}

function requirePackageFiles(value: unknown): BrowserExtensionPackageBuildResult["files"] {
  if (!Array.isArray(value) || value.length !== PACKAGE_BUILD_FILE_PATHS.length) {
    throw new Error("browser extension package build files list is invalid");
  }
  return Object.freeze(PACKAGE_BUILD_FILE_PATHS.map((path, index) => requirePackageFile(value[index], path)));
}

function requireExtensionId(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._@+-]{1,128}$/u.test(value)) {
    throw new Error(`${label} is invalid`);
  }
  return value;
}

function requireChromiumExtensionId(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[a-p]{32}$/u.test(value)) {
    throw new Error(`${label} must be a Chromium extension id`);
  }
  return value;
}

function normalizedRouteConfig(value: unknown): {
  format: typeof BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT;
  account_id: string;
  route_type: BrowserExtensionDispatchableRouteType;
} {
  const parsed = parseBrowserExtensionRouteConfig(value);
  return {
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    account_id: parsed.route_request.account_id,
    route_type: parsed.route_request.route_type
  };
}

function contentScriptMatchOrigin(match: string): string {
  const wildcardSuffix = "/*";
  if (!match.endsWith(wildcardSuffix)) {
    throw new Error("browser extension package content-script match is unsupported");
  }
  const origin = match.slice(0, -wildcardSuffix.length);
  try {
    const url = new URL(origin);
    if (url.origin !== origin || url.origin === "null") {
      throw new Error("invalid origin");
    }
    return origin;
  } catch {
    throw new Error("browser extension package content-script match origin is invalid");
  }
}

function packagedContentScriptOrigins(plan: BrowserExtensionPackagePlan): string[] {
  return [...new Set((plan.manifest.content_scripts ?? []).flatMap((script) => (
    script.matches.map(contentScriptMatchOrigin)
  )))].sort();
}

function packageExtensionId(options: BrowserExtensionPackageBuildOptions): string | undefined {
  if (options.extensionId !== undefined) {
    const extensionId = options.target === "chromium"
      ? requireChromiumExtensionId(options.extensionId, "browser extension package extensionId")
      : requireExtensionId(options.extensionId, "browser extension package extensionId");
    if (
      options.target === "firefox" &&
      options.firefoxExtensionId !== undefined &&
      options.firefoxExtensionId !== extensionId
    ) {
      throw new Error("browser extension package extensionId must match firefoxExtensionId");
    }
    return extensionId;
  }
  if (options.target === "firefox" && options.firefoxExtensionId !== undefined) {
    return requireExtensionId(options.firefoxExtensionId, "browser extension package firefoxExtensionId");
  }
  return undefined;
}

type BrowserExtensionPackageOriginPermissions = {
  mode: "embedded";
  store: BrowserExtensionOriginPermissionStore;
  localPairingDigest: string;
  extensionId: string;
} | {
  mode: "extension_storage";
  localPairingDigest: string;
  extensionId?: string;
};

function requireOriginPermissionMode(
  value: BrowserExtensionPackageOriginPermissionMode | undefined
): BrowserExtensionPackageOriginPermissionMode {
  const mode = value ?? "embedded";
  if (mode !== "embedded" && mode !== "extension_storage") {
    throw new Error("browser extension package origin permission mode is unsupported");
  }
  return mode;
}

function requirePackageManifestProfile(
  options: BrowserExtensionPackageBuildOptions,
  originPermissionMode: BrowserExtensionPackageOriginPermissionMode
): void {
  if (originPermissionMode === "extension_storage") {
    if (options.popupMode !== undefined && options.popupMode !== "origin_permission_approval") {
      throw new Error("browser extension package extension-storage origin permissions require origin approval popup");
    }
    if (options.originPermissionStorageMode !== undefined && options.originPermissionStorageMode !== "extension") {
      throw new Error("browser extension package extension-storage origin permissions require extension storage mode");
    }
    return;
  }
  if (options.popupMode === "origin_permission_approval" || options.originPermissionStorageMode === "extension") {
    throw new Error("browser extension package origin approval popup requires extension-storage origin permission mode");
  }
}

function originPermissionsForPackage(
  options: BrowserExtensionPackageBuildOptions,
  plan: BrowserExtensionPackagePlan
): BrowserExtensionPackageOriginPermissions | undefined {
  const origins = packagedContentScriptOrigins(plan);
  const originPermissionMode = requireOriginPermissionMode(options.originPermissionMode);
  const hasOriginPermissionInput =
    options.originPermissionStore !== undefined ||
    options.localPairingDigest !== undefined ||
    options.originPermissionMode !== undefined;
  if (origins.length === 0) {
    if (hasOriginPermissionInput) {
      throw new Error("browser extension package origin permissions require content-script matches");
    }
    return undefined;
  }
  if (options.originPermissionStore === undefined || options.localPairingDigest === undefined) {
    if (originPermissionMode === "embedded") {
      throw new Error("browser extension package origin permission store is required for content-script builds");
    }
    if (options.localPairingDigest === undefined) {
      throw new Error("browser extension package localPairingDigest is required for extension-storage origin permissions");
    }
  }
  const localPairingDigest = requireLowerHex64(
    options.localPairingDigest,
    "browser extension package localPairingDigest"
  );
  if (originPermissionMode === "extension_storage") {
    if (plan.popup_mode !== "origin_permission_approval" || !plan.uses_extension_storage) {
      throw new Error("browser extension package extension-storage origin permissions require popup approval storage");
    }
    if (options.originPermissionStore !== undefined) {
      throw new Error("browser extension package extension-storage origin permissions must start from browser storage");
    }
    const extensionId = packageExtensionId(options);
    return {
      mode: "extension_storage",
      localPairingDigest,
      ...(extensionId !== undefined ? { extensionId } : {})
    };
  }
  const extensionId = packageExtensionId(options);
  if (extensionId === undefined) {
    throw new Error("browser extension package extensionId is required for embedded origin-permission builds");
  }
  const store = parseBrowserExtensionOriginPermissionStore(options.originPermissionStore);
  for (const origin of origins) {
    for (const method of ["get_public_key", "sign_event"] as const) {
      if (!isBrowserExtensionOriginMethodAllowed(store, {
        origin,
        extensionId,
        localPairingDigest,
        method
      })) {
        throw new Error(`browser extension package origin permission is missing ${method} for ${origin}`);
      }
    }
  }
  return { mode: "embedded", store, localPairingDigest, extensionId };
}

function requireApprovedRouteConfig(routeConfig: unknown, approval: unknown): void {
  const routeConfigDigest = browserExtensionRouteConfigDigest(routeConfig);
  const parsedApproval = parseBrowserExtensionRouteConfigApproval(approval);
  if (parsedApproval.route_config_digest !== routeConfigDigest) {
    throw new Error("browser extension package route config approval digest mismatch");
  }
  if (parsedApproval.review.route_config_digest !== routeConfigDigest) {
    throw new Error("browser extension package route config review digest mismatch");
  }
}

function virtualEntrypointPlugin(
  routeConfig: unknown,
  originPermissions: BrowserExtensionPackageOriginPermissions | undefined
): Plugin {
  const usesExtensionOriginPermissionStorage = originPermissions?.mode === "extension_storage";
  const backgroundOptionsJson = JSON.stringify({
    routeConfig,
    ...(originPermissions?.mode === "embedded" ? {
      extensionId: originPermissions.extensionId,
      originPermissions: {
        store: originPermissions.store,
        localPairingDigest: originPermissions.localPairingDigest
      }
    } : {})
  });
  return {
    name: "nsealr-browser-extension-package-entrypoints",
    setup(build): void {
      build.onResolve({ filter: /^nsealr:browser-extension\/(background|content-script|page-script|popup)$/ }, (args) => ({
        path: args.path,
        namespace: "nsealr-browser-extension"
      }));
      build.onLoad({ filter: /background$/, namespace: "nsealr-browser-extension" }, () => ({
        loader: "ts",
        resolveDir: COMPANION_ROOT,
        contents: usesExtensionOriginPermissionStorage
          ? `
            import { installNsealrBackgroundEntrypoint } from "./apps/browser-extension/src/nsealr-background-entrypoint.ts";
            import { requireBrowserExtensionOriginPermissionStorageGlobal } from "./apps/browser-extension/src/browser-globals.ts";
            import { readBrowserExtensionOriginPermissionStoreFromStorage } from "./apps/browser-extension/src/origin-permission-storage.ts";
            const originPermissionStorage = requireBrowserExtensionOriginPermissionStorageGlobal(globalThis);
            installNsealrBackgroundEntrypoint({
              globalScope: globalThis,
              ...${backgroundOptionsJson},
              originPermissions: {
                loadStore: () => readBrowserExtensionOriginPermissionStoreFromStorage(originPermissionStorage),
                localPairingDigest: ${JSON.stringify(originPermissions?.localPairingDigest)}
              },
              originPermissionStorage
            });
          `
          : `
            import { installNsealrBackgroundEntrypoint } from "./apps/browser-extension/src/nsealr-background-entrypoint.ts";
            installNsealrBackgroundEntrypoint({
              globalScope: globalThis,
              ...${backgroundOptionsJson}
            });
          `
      }));
      build.onLoad({ filter: /content-script$/, namespace: "nsealr-browser-extension" }, () => ({
        loader: "ts",
        resolveDir: COMPANION_ROOT,
        contents: `
          import { installNsealrContentScriptEntrypoint } from "./apps/browser-extension/src/nsealr-content-script-entrypoint.ts";
          installNsealrContentScriptEntrypoint({
            globalScope: globalThis
          });
        `
      }));
      build.onLoad({ filter: /page-script$/, namespace: "nsealr-browser-extension" }, () => ({
        loader: "ts",
        resolveDir: COMPANION_ROOT,
        contents: `
          import { installNsealrPageScriptEntrypoint } from "./apps/browser-extension/src/nsealr-page-script-entrypoint.ts";
          installNsealrPageScriptEntrypoint({
            globalScope: globalThis
          });
        `
      }));
      build.onLoad({ filter: /popup$/, namespace: "nsealr-browser-extension" }, () => ({
        loader: "ts",
        resolveDir: COMPANION_ROOT,
        contents: usesExtensionOriginPermissionStorage
          ? `
            import { installNsealrPopupOriginPermissionEntrypoint } from "./apps/browser-extension/src/nsealr-popup-entrypoint.ts";
            installNsealrPopupOriginPermissionEntrypoint({
              globalScope: globalThis
            });
          `
          : `
            import { installNsealrPopupEntrypoint } from "./apps/browser-extension/src/nsealr-popup-entrypoint.ts";
            installNsealrPopupEntrypoint({
              globalScope: globalThis
            });
          `
      }));
    }
  };
}

function bundleOutputByFile(outputs: readonly { path: string; contents: Uint8Array }[]): Map<string, Uint8Array> {
  const bundles = new Map<string, Uint8Array>();
  for (const output of outputs) {
    bundles.set(basename(output.path), output.contents);
  }
  return bundles;
}

function assertBundleOutputs(bundles: Map<string, Uint8Array>, plan: BrowserExtensionPackagePlan): void {
  const decoder = new TextDecoder("utf-8", { fatal: true });
  for (const entrypoint of plan.entrypoints) {
    const bundle = bundles.get(entrypoint.output);
    if (bundle === undefined) {
      throw new Error(`browser extension package build missing ${entrypoint.output}`);
    }
    const source = decoder.decode(bundle);
    if (nodeBufferReference.test(source) || nodeProcessReference.test(source) || /node:/u.test(source)) {
      throw new Error(`browser extension package build ${entrypoint.output} contains Node runtime references`);
    }
  }
}

function packageFile(path: BrowserExtensionPackageBuildFile["path"], source: string): BrowserExtensionPackageBuildFile {
  return Object.freeze({
    path,
    bytes: textEncoder.encode(source).byteLength,
    sha256: sha256Utf8Hex(source)
  });
}

function buildPackageFileManifest(
  manifestJson: string,
  popupHtml: string,
  bundles: Map<string, Uint8Array>
): BrowserExtensionPackageBuildResult["files"] {
  const decoder = new TextDecoder("utf-8", { fatal: true });
  function bundleFile(path: BrowserExtensionPackageBuildFile["path"]): BrowserExtensionPackageBuildFile {
    const contents = bundles.get(path);
    if (contents === undefined) {
      throw new Error(`browser extension package build missing ${path}`);
    }
    return packageFile(path, decoder.decode(contents));
  }
  return Object.freeze([
    packageFile("manifest.json", manifestJson),
    packageFile(BROWSER_EXTENSION_POPUP_HTML_FILE, popupHtml),
    bundleFile(BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE),
    bundleFile(BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE),
    bundleFile(BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE),
    bundleFile(BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE)
  ]);
}

function packageDigest(target: BrowserExtensionManifestOptions["target"], files: BrowserExtensionPackageBuildResult["files"]): string {
  return sha256Utf8Hex(JSON.stringify({
    format: PACKAGE_DIGEST_INPUT_FORMAT,
    target,
    files
  }));
}

function assertPackageBuildModeConsistency(result: BrowserExtensionPackageBuildResult): void {
  const expectedPermissions = result.origin_permission_mode === "extension_storage"
    ? ["nativeMessaging", "activeTab", "storage"]
    : ["nativeMessaging"];
  if (JSON.stringify(result.manifest_permissions) !== JSON.stringify(expectedPermissions)) {
    throw new Error("browser extension package build manifest permission metadata is inconsistent");
  }
  if (result.uses_active_tab_permission !== result.manifest_permissions.includes("activeTab")) {
    throw new Error("browser extension package build activeTab metadata is inconsistent");
  }
  if (result.origin_permission_mode === "none") {
    if (
      result.content_script_origins.length !== 0 ||
      "extension_id" in result ||
      "local_pairing_digest" in result ||
      result.embeds_origin_permission_store !== false ||
      result.uses_extension_origin_permission_storage !== false
    ) {
      throw new Error("browser extension package build ungated origin metadata is inconsistent");
    }
    return;
  }
  if (result.content_script_origins.length === 0 || result.local_pairing_digest === undefined) {
    throw new Error("browser extension package build gated origin metadata is incomplete");
  }
  if (result.origin_permission_mode === "embedded") {
    if (
      result.extension_id === undefined ||
      result.embeds_origin_permission_store !== true ||
      result.uses_extension_origin_permission_storage !== false
    ) {
      throw new Error("browser extension package build embedded origin metadata is inconsistent");
    }
    return;
  }
  if (
    result.embeds_origin_permission_store !== false ||
    result.uses_extension_origin_permission_storage !== true
  ) {
    throw new Error("browser extension package build extension-storage metadata is inconsistent");
  }
}

export function parseBrowserExtensionPackageBuildResult(value: unknown): BrowserExtensionPackageBuildResult {
  if (!isRecord(value)) {
    throw new Error("browser extension package build result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "target",
    "out_dir",
    "package_plan_digest",
    "route_config_digest",
    "route_account_id",
    "route_type",
    "native_host_name",
    "popup_mode",
    "manifest_permissions",
    "origin_permission_mode",
    "extension_id",
    "local_pairing_digest",
    "content_script_origins",
    "package_digest",
    "files",
    "installs_native_host_manifest",
    "writes_extension_storage",
    "stores_production_secrets",
    "dispatches_signers",
    "uses_active_tab_permission",
    "embeds_origin_permission_store",
    "uses_extension_origin_permission_storage"
  ])) {
    throw new Error("browser extension package build result has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT) {
    throw new Error("browser extension package build result format is unsupported");
  }
  const target = requireTarget(value.target);
  const routeConfig = normalizedRouteConfig({
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    account_id: value.route_account_id,
    route_type: value.route_type
  });
  const files = requirePackageFiles(value.files);
  const result: BrowserExtensionPackageBuildResult = Object.freeze({
    format: BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT,
    target,
    out_dir: requireSafePackageOutputPath(
      requireAbsoluteResultPath(value.out_dir, "browser extension package build out_dir")
    ),
    package_plan_digest: requireLowerHex64(value.package_plan_digest, "browser extension package build package_plan_digest"),
    route_config_digest: requireLowerHex64(value.route_config_digest, "browser extension package build route_config_digest"),
    route_account_id: routeConfig.account_id,
    route_type: routeConfig.route_type,
    native_host_name: requireNativeHostName(value.native_host_name),
    popup_mode: requirePopupMode(value.popup_mode),
    manifest_permissions: Object.freeze(requireManifestPermissions(value.manifest_permissions)),
    origin_permission_mode: requirePackageBuildOriginPermissionMode(value.origin_permission_mode),
    ...(value.extension_id !== undefined ? {
      extension_id: target === "chromium"
        ? requireChromiumExtensionId(value.extension_id, "browser extension package build extension_id")
        : requireExtensionId(value.extension_id, "browser extension package build extension_id")
    } : {}),
    ...(value.local_pairing_digest !== undefined ? {
      local_pairing_digest: requireLowerHex64(
        value.local_pairing_digest,
        "browser extension package build local_pairing_digest"
      )
    } : {}),
    content_script_origins: Object.freeze(requireContentScriptOrigins(value.content_script_origins)),
    package_digest: requireLowerHex64(value.package_digest, "browser extension package build package_digest"),
    files,
    installs_native_host_manifest: requireFalse(
      value.installs_native_host_manifest,
      "browser extension package build installs_native_host_manifest"
    ),
    writes_extension_storage: requireFalse(
      value.writes_extension_storage,
      "browser extension package build writes_extension_storage"
    ),
    stores_production_secrets: requireFalse(
      value.stores_production_secrets,
      "browser extension package build stores_production_secrets"
    ),
    dispatches_signers: requireFalse(
      value.dispatches_signers,
      "browser extension package build dispatches_signers"
    ),
    uses_active_tab_permission: requireBoolean(
      value.uses_active_tab_permission,
      "browser extension package build uses_active_tab_permission"
    ),
    embeds_origin_permission_store: requireBoolean(
      value.embeds_origin_permission_store,
      "browser extension package build embeds_origin_permission_store"
    ),
    uses_extension_origin_permission_storage: requireBoolean(
      value.uses_extension_origin_permission_storage,
      "browser extension package build uses_extension_origin_permission_storage"
    )
  });
  if (result.package_digest !== packageDigest(result.target, result.files)) {
    throw new Error("browser extension package build package digest mismatch");
  }
  assertPackageBuildModeConsistency(result);
  return result;
}

function assertManifestMatchesPackageBuild(
  result: BrowserExtensionPackageBuildResult,
  manifestJson: string
): BrowserExtensionPackagePlan {
  let manifest: unknown;
  try {
    manifest = JSON.parse(manifestJson);
  } catch (error) {
    throw new Error(`browser extension package manifest JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (!isRecord(manifest)) {
    throw new Error("browser extension package manifest must be an object");
  }
  const expectedPackagePlan = expectedPackagePlanForBuildResult(result, manifest);
  if (browserExtensionPackagePlanDigest(expectedPackagePlan) !== result.package_plan_digest) {
    throw new Error("browser extension package plan digest mismatch");
  }
  if (JSON.stringify(manifest) !== JSON.stringify(expectedPackagePlan.manifest)) {
    throw new Error("browser extension package manifest drifted");
  }
  if (JSON.stringify(manifest.permissions) !== JSON.stringify(result.manifest_permissions)) {
    throw new Error("browser extension package manifest permissions drifted");
  }
  if ("host_permissions" in manifest || "optional_host_permissions" in manifest) {
    throw new Error("browser extension package manifest must not include host permissions");
  }
  if (!isRecord(manifest.background) || manifest.background.service_worker !== BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE) {
    throw new Error("browser extension package manifest background entrypoint drifted");
  }
  if (!isRecord(manifest.action) || manifest.action.default_popup !== BROWSER_EXTENSION_POPUP_HTML_FILE) {
    throw new Error("browser extension package manifest popup drifted");
  }
  if (result.target === "chromium" && "browser_specific_settings" in manifest) {
    throw new Error("browser extension package Chromium manifest must not include Firefox settings");
  }
  if (result.target === "firefox") {
    if (
      !isRecord(manifest.browser_specific_settings) ||
      !isRecord(manifest.browser_specific_settings.gecko) ||
      typeof manifest.browser_specific_settings.gecko.id !== "string"
    ) {
      throw new Error("browser extension package Firefox settings drifted");
    }
    requireExtensionId(
      manifest.browser_specific_settings.gecko.id,
      "browser extension package Firefox extension id"
    );
    if (result.extension_id !== undefined && manifest.browser_specific_settings.gecko.id !== result.extension_id) {
      throw new Error("browser extension package Firefox extension id metadata drifted");
    }
  }

  if (result.content_script_origins.length === 0) {
    if ("content_scripts" in manifest || "web_accessible_resources" in manifest) {
      throw new Error("browser extension package ungated manifest must not include content-script resources");
    }
    return expectedPackagePlan;
  }

  const matches = result.content_script_origins.map((origin) => `${origin}/*`);
  const expectedContentScript = [{
    matches,
    js: [BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE],
    run_at: "document_start",
    all_frames: false,
    match_about_blank: false
  }];
  if (JSON.stringify(manifest.content_scripts) !== JSON.stringify(expectedContentScript)) {
    throw new Error("browser extension package manifest content-script drifted");
  }
  const expectedResources = [{
    resources: [BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE],
    matches
  }];
  if (JSON.stringify(manifest.web_accessible_resources) !== JSON.stringify(expectedResources)) {
    throw new Error("browser extension package manifest page-script resource drifted");
  }
  return expectedPackagePlan;
}

function assertPackagePlanReviewMatchesPackageBuild(
  result: BrowserExtensionPackageBuildResult,
  expectedPackagePlan: BrowserExtensionPackagePlan,
  packagePlanReview: unknown
): BrowserExtensionPackagePlanReview | undefined {
  const parsedReview = parseBrowserExtensionPackagePlanReview(packagePlanReview);
  if (parsedReview.package_plan_digest !== result.package_plan_digest) {
    throw new Error("browser extension package-plan review digest mismatch");
  }
  if (JSON.stringify(parsedReview.package_plan) !== JSON.stringify(expectedPackagePlan)) {
    throw new Error("browser extension package-plan review does not match package build");
  }
  return parsedReview;
}

function assertPackagePlanReviewMatchesPackagePlan(
  packagePlanReview: unknown,
  expectedPackagePlan: BrowserExtensionPackagePlan,
  expectedPackagePlanDigest: string
): BrowserExtensionPackagePlanReview {
  const parsedReview = parseBrowserExtensionPackagePlanReview(packagePlanReview);
  if (parsedReview.package_plan_digest !== expectedPackagePlanDigest) {
    throw new Error("browser extension package-plan review digest mismatch");
  }
  if (JSON.stringify(parsedReview.package_plan) !== JSON.stringify(expectedPackagePlan)) {
    throw new Error("browser extension package-plan review does not match package build");
  }
  return parsedReview;
}

function requirePackagePlanReviewOption(options: BrowserExtensionPackageVerifyOptions | undefined): unknown {
  if (options === undefined || options.packagePlanReview === undefined) {
    throw new Error("browser extension package-plan review is required for package verification");
  }
  return options.packagePlanReview;
}

function expectedPackagePlanForBuildResult(
  result: BrowserExtensionPackageBuildResult,
  manifest: Record<string, unknown>
): BrowserExtensionPackagePlan {
  const contentScriptMatches = result.content_script_origins.map((origin) => `${origin}/*`);
  return assertBrowserExtensionPackagePlan(buildBrowserExtensionPackagePlan({
    target: result.target,
    ...(contentScriptMatches.length > 0 ? { contentScriptMatches } : {}),
    ...(result.popup_mode !== "pending_requests" ? { popupMode: result.popup_mode } : {}),
    ...(result.origin_permission_mode === "extension_storage" ? { originPermissionStorageMode: "extension" } : {}),
    ...(result.target === "firefox" ? { firefoxExtensionId: firefoxExtensionIdFromManifest(manifest) } : {})
  }));
}

function firefoxExtensionIdFromManifest(manifest: Record<string, unknown>): string {
  if (
    !isRecord(manifest.browser_specific_settings) ||
    !isRecord(manifest.browser_specific_settings.gecko) ||
    typeof manifest.browser_specific_settings.gecko.id !== "string"
  ) {
    throw new Error("browser extension package Firefox settings drifted");
  }
  return requireExtensionId(
    manifest.browser_specific_settings.gecko.id,
    "browser extension package Firefox extension id"
  );
}

function assertBackgroundMatchesPackageBuild(
  result: BrowserExtensionPackageBuildResult,
  backgroundSource: string | undefined
): void {
  if (backgroundSource === undefined || !backgroundSource.includes(result.native_host_name)) {
    throw new Error("browser extension package background native-host binding drifted");
  }
  if (!backgroundSource.includes(result.route_account_id) || !backgroundSource.includes(result.route_type)) {
    throw new Error("browser extension package background route metadata drifted");
  }
  if (result.origin_permission_mode === "embedded") {
    if (
      result.extension_id === undefined ||
      result.local_pairing_digest === undefined ||
      !backgroundSource.includes(result.extension_id) ||
      !backgroundSource.includes(result.local_pairing_digest)
    ) {
      throw new Error("browser extension package background embedded origin metadata drifted");
    }
  }
  if (result.origin_permission_mode === "extension_storage") {
    if (
      result.local_pairing_digest === undefined ||
      !backgroundSource.includes(result.local_pairing_digest) ||
      !backgroundSource.includes("originPermissionStorage")
    ) {
      throw new Error("browser extension package background extension-storage origin metadata drifted");
    }
  }
}

function assertPopupMatchesPackageBuild(
  result: BrowserExtensionPackageBuildResult,
  popupSource: string | undefined
): void {
  if (popupSource === undefined) {
    throw new Error("browser extension package popup entrypoint is missing");
  }
  if (result.popup_mode === "pending_requests") {
    if (
      !popupSource.includes("list_pending_requests") ||
      !popupSource.includes("cancel_pending_request") ||
      !popupSource.includes("data-nsealr-popup")
    ) {
      throw new Error("browser extension package popup mode drifted");
    }
    return;
  }
  if (
    !popupSource.includes("request_origin_permission_review") ||
    !popupSource.includes("approve_origin_permission") ||
    !popupSource.includes("active_tab") ||
    !popupSource.includes("data-nsealr-popup-origin-permission")
  ) {
    throw new Error("browser extension package popup mode drifted");
  }
}

function assertContentScriptMatchesPackageBuild(contentScriptSource: string | undefined): void {
  if (
    contentScriptSource === undefined ||
    !contentScriptSource.includes("installNsealrContentScriptEntrypoint") ||
    !contentScriptSource.includes("nsealr-page-script") ||
    !contentScriptSource.includes("nsealr-page-bridge-v0") ||
    !contentScriptSource.includes("runtime.sendMessage") ||
    !contentScriptSource.includes("postMessage")
  ) {
    throw new Error("browser extension package content-script binding drifted");
  }
}

function assertPageScriptMatchesPackageBuild(pageScriptSource: string | undefined): void {
  if (
    pageScriptSource === undefined ||
    !pageScriptSource.includes("installNsealrPageScriptEntrypoint") ||
    !pageScriptSource.includes("nsealr-page-bridge-v0") ||
    !pageScriptSource.includes("getPublicKey") ||
    !pageScriptSource.includes("signEvent") ||
    !pageScriptSource.includes("postMessage")
  ) {
    throw new Error("browser extension package page-script binding drifted");
  }
}

async function assertPackageDirectoryContainsOnlyExpectedFiles(result: BrowserExtensionPackageBuildResult): Promise<void> {
  const expectedFiles = new Set<string>(result.files.map((file) => file.path));
  const actualFiles = new Set<string>();
  for (const entry of await readdir(result.out_dir, { withFileTypes: true })) {
    if (!entry.isFile()) {
      throw new Error(`browser extension package unexpected output entry: ${entry.name}`);
    }
    if (!expectedFiles.has(entry.name)) {
      throw new Error(`browser extension package unexpected output file: ${entry.name}`);
    }
    actualFiles.add(entry.name);
  }
  for (const expectedFile of expectedFiles) {
    if (!actualFiles.has(expectedFile)) {
      throw new Error(`browser extension package missing output file: ${expectedFile}`);
    }
  }
}

export async function verifyBrowserExtensionPackageBuildDirectory(
  value: unknown,
  options?: BrowserExtensionPackageVerifyOptions
): Promise<BrowserExtensionPackageBuildResult> {
  const result = parseBrowserExtensionPackageBuildResult(value);
  const packagePlanReview = requirePackagePlanReviewOption(options);
  const fileContents = new Map<string, string>();
  await assertPackageDirectoryContainsOnlyExpectedFiles(result);

  for (const file of result.files) {
    const source = await readFile(join(result.out_dir, file.path), "utf8");
    if (textEncoder.encode(source).byteLength !== file.bytes) {
      throw new Error(`browser extension package ${file.path} byte count mismatch`);
    }
    if (sha256Utf8Hex(source) !== file.sha256) {
      throw new Error(`browser extension package ${file.path} sha256 mismatch`);
    }
    if (file.path.endsWith(".js") && (
      nodeBufferReference.test(source) ||
      nodeProcessReference.test(source) ||
      /node:/u.test(source)
    )) {
      throw new Error(`browser extension package ${file.path} contains Node runtime references`);
    }
    fileContents.set(file.path, source);
  }

  const manifestJson = fileContents.get("manifest.json");
  if (manifestJson === undefined) {
    throw new Error("browser extension package manifest is missing");
  }
  const expectedPackagePlan = assertManifestMatchesPackageBuild(result, manifestJson);
  assertPackagePlanReviewMatchesPackageBuild(result, expectedPackagePlan, packagePlanReview);

  const popupHtml = fileContents.get(BROWSER_EXTENSION_POPUP_HTML_FILE);
  if (popupHtml === undefined || popupHtml !== browserExtensionPopupHtml()) {
    throw new Error("browser extension package popup HTML drifted");
  }
  assertPopupMatchesPackageBuild(result, fileContents.get(BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE));

  assertBackgroundMatchesPackageBuild(result, fileContents.get(BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE));
  assertContentScriptMatchesPackageBuild(fileContents.get(BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE));
  assertPageScriptMatchesPackageBuild(fileContents.get(BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE));

  return result;
}

export async function buildBrowserExtensionPackage(
  options: BrowserExtensionPackageBuildOptions
): Promise<BrowserExtensionPackageBuildResult> {
  const outDir = requireOutDir(options.outDir);
  if (await pathExists(outDir)) {
    throw new Error("browser extension package out-dir already exists");
  }
  const routeConfig = normalizedRouteConfig(options.routeConfig);
  requireApprovedRouteConfig(routeConfig, options.routeConfigApproval);
  const originPermissionMode = requireOriginPermissionMode(options.originPermissionMode);
  requirePackageManifestProfile(options, originPermissionMode);
  const plan = assertBrowserExtensionPackagePlan(buildBrowserExtensionPackagePlan({
    ...options,
    ...(originPermissionMode === "extension_storage"
      ? {
          popupMode: "origin_permission_approval",
          originPermissionStorageMode: "extension"
        }
      : {})
  }));
  const packagePlanDigest = browserExtensionPackagePlanDigest(plan);
  assertPackagePlanReviewMatchesPackagePlan(options.packagePlanReview, plan, packagePlanDigest);
  const originPermissions = originPermissionsForPackage(options, plan);
  const contentScriptOrigins = packagedContentScriptOrigins(plan);
  const buildResult = await esbuild({
    absWorkingDir: COMPANION_ROOT,
    bundle: true,
    entryNames: "[name]",
    entryPoints: [
      { in: "nsealr:browser-extension/background", out: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE.replace(/\.js$/u, "") },
      { in: "nsealr:browser-extension/content-script", out: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE.replace(/\.js$/u, "") },
      { in: "nsealr:browser-extension/page-script", out: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE.replace(/\.js$/u, "") },
      { in: "nsealr:browser-extension/popup", out: BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE.replace(/\.js$/u, "") }
    ],
    format: "iife",
    legalComments: "none",
    logLevel: "silent",
    outdir: PACKAGE_OUTPUT_DIR,
    platform: "browser",
    plugins: [virtualEntrypointPlugin(routeConfig, originPermissions)],
    sourcemap: false,
    target: "es2022",
    treeShaking: true,
    write: false
  });
  const bundles = bundleOutputByFile(buildResult.outputFiles ?? []);
  assertBundleOutputs(bundles, plan);

  const manifestJson = `${JSON.stringify(plan.manifest, null, 2)}\n`;
  const popupHtml = browserExtensionPopupHtml();
  const files = buildPackageFileManifest(manifestJson, popupHtml, bundles);
  await mkdir(outDir, { recursive: true });
  await writeFile(join(outDir, "manifest.json"), manifestJson);
  await writeFile(join(outDir, BROWSER_EXTENSION_POPUP_HTML_FILE), popupHtml);
  for (const entrypoint of plan.entrypoints) {
    const contents = bundles.get(entrypoint.output);
    if (contents === undefined) {
      throw new Error(`browser extension package build missing ${entrypoint.output}`);
    }
    await writeFile(join(outDir, entrypoint.output), contents);
  }

  const totalBytes = files.reduce((sum, file) => sum + file.bytes, 0);
  if (totalBytes <= 0) {
    throw new Error("browser extension package build produced empty output");
  }

  return Object.freeze({
    format: BROWSER_EXTENSION_PACKAGE_BUILD_FORMAT,
    target: plan.target,
    out_dir: outDir,
    package_plan_digest: packagePlanDigest,
    route_config_digest: browserExtensionRouteConfigDigest(routeConfig),
    route_account_id: routeConfig.account_id,
    route_type: routeConfig.route_type,
    native_host_name: plan.native_host_name,
    popup_mode: plan.popup_mode,
    manifest_permissions: Object.freeze([...plan.manifest.permissions]),
    origin_permission_mode: originPermissions?.mode ?? "none",
    ...(originPermissions?.extensionId !== undefined ? { extension_id: originPermissions.extensionId } : {}),
    ...(originPermissions?.localPairingDigest !== undefined
      ? { local_pairing_digest: originPermissions.localPairingDigest }
      : {}),
    content_script_origins: Object.freeze(contentScriptOrigins),
    package_digest: packageDigest(plan.target, files),
    files,
    installs_native_host_manifest: false,
    writes_extension_storage: false,
    stores_production_secrets: false,
    dispatches_signers: false,
    uses_active_tab_permission: plan.uses_active_tab_permission,
    embeds_origin_permission_store: originPermissions?.mode === "embedded",
    uses_extension_origin_permission_storage: originPermissions?.mode === "extension_storage"
  });
}
