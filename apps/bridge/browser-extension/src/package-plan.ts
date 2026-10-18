import { sha256Utf8Hex } from "@nsealr/core";
import { NATIVE_HOST_NAME } from "@nsealr/client";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";
import {
  buildBrowserExtensionManifest,
  type BrowserExtensionPopupMode,
  type BrowserExtensionManifest,
  type BrowserExtensionManifestOptions
} from "./manifest.js";

export const BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT = "nsealr-browser-extension-package-plan-v0";
export const BROWSER_EXTENSION_PACKAGE_PLAN_DIGEST_INPUT_FORMAT =
  "nsealr-browser-extension-package-plan-digest-v0";
export const BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT =
  "nsealr-browser-extension-package-plan-review-v0";
export const BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_SOURCE =
  "apps/browser-extension/src/nsealr-background-entrypoint.ts";
export const BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_SOURCE =
  "apps/browser-extension/src/nsealr-content-script-entrypoint.ts";
export const BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_SOURCE =
  "apps/browser-extension/src/nsealr-page-script-entrypoint.ts";
export const BROWSER_EXTENSION_POPUP_ENTRYPOINT_SOURCE =
  "apps/browser-extension/src/nsealr-popup-entrypoint.ts";

export type BrowserExtensionPackageEntrypointRole =
  "background_service_worker" |
  "content_script" |
  "page_script" |
  "action_popup";

export type BrowserExtensionPackageEntrypoint = {
  role: BrowserExtensionPackageEntrypointRole;
  source: string;
  output: string;
};

export type BrowserExtensionPackagePlan = {
  format: typeof BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT;
  target: BrowserExtensionManifestOptions["target"];
  popup_mode: BrowserExtensionPopupMode;
  native_host_name: typeof NATIVE_HOST_NAME;
  manifest: BrowserExtensionManifest;
  entrypoints: readonly [
    BrowserExtensionPackageEntrypoint,
    BrowserExtensionPackageEntrypoint,
    BrowserExtensionPackageEntrypoint,
    BrowserExtensionPackageEntrypoint
  ];
  installs_native_host_manifest: false;
  writes_extension_storage: false;
  uses_extension_storage: boolean;
  uses_active_tab_permission: boolean;
  stores_production_secrets: false;
  dispatches_signers: false;
};

export type BrowserExtensionPackagePlanReview = {
  format: typeof BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT;
  package_plan_digest: string;
  package_plan: BrowserExtensionPackagePlan;
  requires_user_review: true;
  installs_native_host_manifest: false;
  writes_extension_storage: false;
  stores_production_secrets: false;
  dispatches_signers: false;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: readonly string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireLowerHex64(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${label} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireTrue(value: unknown, label: string): true {
  if (value !== true) {
    throw new Error(`${label} must be true`);
  }
  return true;
}

function requireFalse(value: unknown, label: string): false {
  if (value !== false) {
    throw new Error(`${label} must be false`);
  }
  return false;
}

function packageEntrypoints(): BrowserExtensionPackagePlan["entrypoints"] {
  return Object.freeze([
    Object.freeze({
      role: "background_service_worker" as const,
      source: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_SOURCE,
      output: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE
    }),
    Object.freeze({
      role: "content_script" as const,
      source: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_SOURCE,
      output: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE
    }),
    Object.freeze({
      role: "page_script" as const,
      source: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_SOURCE,
      output: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE
    }),
    Object.freeze({
      role: "action_popup" as const,
      source: BROWSER_EXTENSION_POPUP_ENTRYPOINT_SOURCE,
      output: BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE
    })
  ]);
}

function entrypointByRole(
  plan: BrowserExtensionPackagePlan,
  role: BrowserExtensionPackageEntrypointRole
): BrowserExtensionPackageEntrypoint {
  const entrypoint = plan.entrypoints.find((candidate) => candidate.role === role);
  if (entrypoint === undefined) {
    throw new Error(`browser extension package plan is missing ${role} entrypoint`);
  }
  return entrypoint;
}

function assertEntrypoint(
  entrypoint: BrowserExtensionPackageEntrypoint,
  role: BrowserExtensionPackageEntrypointRole,
  source: string,
  output: string
): void {
  if (entrypoint.role !== role || entrypoint.source !== source || entrypoint.output !== output) {
    throw new Error(`browser extension package plan ${role} entrypoint is invalid`);
  }
}

function assertPermissionProfile(plan: BrowserExtensionPackagePlan): void {
  const permissions = plan.manifest.permissions as readonly string[];
  if (plan.popup_mode !== "pending_requests" && plan.popup_mode !== "origin_permission_approval") {
    throw new Error("browser extension package plan popup mode is unsupported");
  }
  if (permissions.includes("storage") !== plan.uses_extension_storage) {
    throw new Error("browser extension package plan storage permission profile is invalid");
  }
  if (permissions.includes("activeTab") !== plan.uses_active_tab_permission) {
    throw new Error("browser extension package plan activeTab permission profile is invalid");
  }
  if (plan.popup_mode === "origin_permission_approval" && !plan.uses_active_tab_permission) {
    throw new Error("browser extension package plan origin approval popup must request activeTab");
  }
  if (plan.uses_extension_storage && !plan.uses_active_tab_permission) {
    throw new Error("browser extension package plan extension storage requires activeTab review");
  }
  if ("host_permissions" in plan.manifest || "optional_host_permissions" in plan.manifest) {
    throw new Error("browser extension package plan must not request host permissions");
  }
}

export function assertBrowserExtensionPackagePlan(
  plan: BrowserExtensionPackagePlan
): BrowserExtensionPackagePlan {
  if (plan.format !== BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT) {
    throw new Error("browser extension package plan format is unsupported");
  }
  if (plan.native_host_name !== NATIVE_HOST_NAME) {
    throw new Error("browser extension package plan native host name drifted");
  }
  if (plan.installs_native_host_manifest !== false) {
    throw new Error("browser extension package plan must not install native-host manifests");
  }
  if (plan.writes_extension_storage !== false) {
    throw new Error("browser extension package plan must not write extension storage");
  }
  if (typeof plan.uses_extension_storage !== "boolean") {
    throw new Error("browser extension package plan extension storage profile is invalid");
  }
  if (typeof plan.uses_active_tab_permission !== "boolean") {
    throw new Error("browser extension package plan activeTab profile is invalid");
  }
  if (plan.stores_production_secrets !== false) {
    throw new Error("browser extension package plan must not store production secrets");
  }
  if (plan.dispatches_signers !== false) {
    throw new Error("browser extension package plan must not dispatch signers");
  }
  assertPermissionProfile(plan);

  const background = entrypointByRole(plan, "background_service_worker");
  assertEntrypoint(
    background,
    "background_service_worker",
    BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_SOURCE,
    BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE
  );
  if (plan.manifest.background.service_worker !== background.output) {
    throw new Error("browser extension package plan background output does not match manifest");
  }
  const popup = entrypointByRole(plan, "action_popup");
  assertEntrypoint(
    popup,
    "action_popup",
    BROWSER_EXTENSION_POPUP_ENTRYPOINT_SOURCE,
    BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE
  );
  if (plan.manifest.action.default_popup !== BROWSER_EXTENSION_POPUP_HTML_FILE) {
    throw new Error("browser extension package plan popup html does not match manifest");
  }
  const contentScript = entrypointByRole(plan, "content_script");
  assertEntrypoint(
    contentScript,
    "content_script",
    BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_SOURCE,
    BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE
  );
  if (plan.manifest.content_scripts !== undefined) {
    for (const manifestContentScript of plan.manifest.content_scripts) {
      if (manifestContentScript.js[0] !== contentScript.output) {
        throw new Error("browser extension package plan content-script output does not match manifest");
      }
    }
  }
  const pageScript = entrypointByRole(plan, "page_script");
  assertEntrypoint(
    pageScript,
    "page_script",
    BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_SOURCE,
    BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE
  );
  if (plan.manifest.content_scripts !== undefined) {
    const webAccessibleResources = plan.manifest.web_accessible_resources;
    if (webAccessibleResources === undefined || webAccessibleResources.length !== 1) {
      throw new Error("browser extension package plan must expose packaged page script for content-script injection");
    }
    if (webAccessibleResources[0].resources[0] !== pageScript.output) {
      throw new Error("browser extension package plan page-script output does not match web-accessible resources");
    }
  }
  return plan;
}

export function buildBrowserExtensionPackagePlan(
  options: BrowserExtensionManifestOptions
): BrowserExtensionPackagePlan {
  const popupMode = options.popupMode ?? "pending_requests";
  const usesExtensionStorage = options.originPermissionStorageMode === "extension";
  return assertBrowserExtensionPackagePlan(Object.freeze({
    format: BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
    target: options.target,
    popup_mode: popupMode,
    native_host_name: NATIVE_HOST_NAME,
    manifest: buildBrowserExtensionManifest(options),
    entrypoints: packageEntrypoints(),
    installs_native_host_manifest: false,
    writes_extension_storage: false,
    uses_extension_storage: usesExtensionStorage,
    uses_active_tab_permission: popupMode === "origin_permission_approval",
    stores_production_secrets: false,
    dispatches_signers: false
  }));
}

export function browserExtensionPackagePlanDigest(plan: BrowserExtensionPackagePlan): string {
  const reviewedPlan = assertBrowserExtensionPackagePlan(plan);
  return sha256Utf8Hex(JSON.stringify({
    format: BROWSER_EXTENSION_PACKAGE_PLAN_DIGEST_INPUT_FORMAT,
    plan: reviewedPlan
  }));
}

export function createBrowserExtensionPackagePlanReview(
  options: BrowserExtensionManifestOptions
): BrowserExtensionPackagePlanReview {
  const packagePlan = buildBrowserExtensionPackagePlan(options);
  return Object.freeze({
    format: BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT,
    package_plan_digest: browserExtensionPackagePlanDigest(packagePlan),
    package_plan: packagePlan,
    requires_user_review: true,
    installs_native_host_manifest: false,
    writes_extension_storage: false,
    stores_production_secrets: false,
    dispatches_signers: false
  });
}

export function parseBrowserExtensionPackagePlanReview(value: unknown): BrowserExtensionPackagePlanReview {
  if (!isRecord(value)) {
    throw new Error("browser extension package-plan review must be an object");
  }
  if (!hasOnlyKeys(value, [
    "format",
    "package_plan_digest",
    "package_plan",
    "requires_user_review",
    "installs_native_host_manifest",
    "writes_extension_storage",
    "stores_production_secrets",
    "dispatches_signers"
  ])) {
    throw new Error("browser extension package-plan review has unsupported fields");
  }
  if (value.format !== BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT) {
    throw new Error("browser extension package-plan review format is unsupported");
  }
  if (!isRecord(value.package_plan)) {
    throw new Error("browser extension package-plan review package_plan must be an object");
  }
  const packagePlan = assertBrowserExtensionPackagePlan(value.package_plan as BrowserExtensionPackagePlan);
  const packagePlanDigest = requireLowerHex64(
    value.package_plan_digest,
    "browser extension package-plan review package_plan_digest"
  );
  if (packagePlanDigest !== browserExtensionPackagePlanDigest(packagePlan)) {
    throw new Error("browser extension package-plan review digest mismatch");
  }
  return Object.freeze({
    format: BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT,
    package_plan_digest: packagePlanDigest,
    package_plan: packagePlan,
    requires_user_review: requireTrue(
      value.requires_user_review,
      "browser extension package-plan review requires_user_review"
    ),
    installs_native_host_manifest: requireFalse(
      value.installs_native_host_manifest,
      "browser extension package-plan review installs_native_host_manifest"
    ),
    writes_extension_storage: requireFalse(
      value.writes_extension_storage,
      "browser extension package-plan review writes_extension_storage"
    ),
    stores_production_secrets: requireFalse(
      value.stores_production_secrets,
      "browser extension package-plan review stores_production_secrets"
    ),
    dispatches_signers: requireFalse(
      value.dispatches_signers,
      "browser extension package-plan review dispatches_signers"
    )
  });
}

export function browserExtensionPackagePlanJson(options: BrowserExtensionManifestOptions): string {
  return `${JSON.stringify(buildBrowserExtensionPackagePlan(options), null, 2)}\n`;
}

export function browserExtensionPackagePlanReviewJson(options: BrowserExtensionManifestOptions): string {
  return `${JSON.stringify(createBrowserExtensionPackagePlanReview(options), null, 2)}\n`;
}
