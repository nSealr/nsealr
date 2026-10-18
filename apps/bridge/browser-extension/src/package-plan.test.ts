import { describe, expect, it } from "vitest";
import { NATIVE_HOST_NAME } from "@nsealr/client";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_SOURCE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_SOURCE,
  BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
  BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_SOURCE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_SOURCE,
  assertBrowserExtensionPackagePlan,
  browserExtensionPackagePlanDigest,
  browserExtensionPackagePlanJson,
  createBrowserExtensionPackagePlanReview,
  buildBrowserExtensionPackagePlan,
  type BrowserExtensionPackagePlan
} from "./package-plan.js";

function tamperedPlan(value: unknown): BrowserExtensionPackagePlan {
  return value as BrowserExtensionPackagePlan;
}

describe("browser extension package plan", () => {
  it("builds a secretless Chromium package plan without installing anything", () => {
    const plan = buildBrowserExtensionPackagePlan({ target: "chromium" });

    expect(plan).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
      target: "chromium",
      popup_mode: "pending_requests",
      native_host_name: NATIVE_HOST_NAME,
      installs_native_host_manifest: false,
      writes_extension_storage: false,
      uses_extension_storage: false,
      uses_active_tab_permission: false,
      stores_production_secrets: false,
      dispatches_signers: false
    });
    expect(plan.manifest.background.service_worker).toBe(BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE);
    expect(plan.manifest.action.default_popup).toBe(BROWSER_EXTENSION_POPUP_HTML_FILE);
    expect(plan.manifest.permissions).toEqual(["nativeMessaging"]);
    expect("content_scripts" in plan.manifest).toBe(false);
    expect("host_permissions" in plan.manifest).toBe(false);
    expect(plan.entrypoints).toEqual([
      {
        role: "background_service_worker",
        source: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_SOURCE,
        output: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE
      },
      {
        role: "content_script",
        source: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_SOURCE,
        output: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE
      },
      {
        role: "page_script",
        source: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_SOURCE,
        output: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE
      },
      {
        role: "action_popup",
        source: BROWSER_EXTENSION_POPUP_ENTRYPOINT_SOURCE,
        output: BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE
      }
    ]);
  });

  it("builds an explicit storage-backed origin approval popup package plan", () => {
    const plan = buildBrowserExtensionPackagePlan({
      target: "chromium",
      popupMode: "origin_permission_approval",
      originPermissionStorageMode: "extension",
      contentScriptMatches: ["https://example.com/*"]
    });

    expect(plan.popup_mode).toBe("origin_permission_approval");
    expect(plan.uses_extension_storage).toBe(true);
    expect(plan.uses_active_tab_permission).toBe(true);
    expect(plan.manifest.permissions).toEqual(["nativeMessaging", "activeTab", "storage"]);
    expect("host_permissions" in plan.manifest).toBe(false);
    expect(assertBrowserExtensionPackagePlan(plan)).toBe(plan);
  });

  it("keeps explicit content-script manifests aligned with the packaged output", () => {
    const plan = buildBrowserExtensionPackagePlan({
      target: "chromium",
      contentScriptMatches: ["https://example.com/*"]
    });

    expect(plan.manifest.content_scripts).toEqual([{
      matches: ["https://example.com/*"],
      js: [BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE],
      run_at: "document_start",
      all_frames: false,
      match_about_blank: false
    }]);
    expect(plan.manifest.web_accessible_resources).toEqual([{
      resources: [BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE],
      matches: ["https://example.com/*"]
    }]);
    expect(assertBrowserExtensionPackagePlan(plan)).toBe(plan);
  });

  it("renders deterministic package-plan JSON", () => {
    expect(JSON.parse(browserExtensionPackagePlanJson({ target: "chromium" }))).toEqual(
      buildBrowserExtensionPackagePlan({ target: "chromium" })
    );
  });

  it("binds reviewed package plans to a deterministic digest", () => {
    const plan = buildBrowserExtensionPackagePlan({
      target: "chromium",
      contentScriptMatches: ["https://example.com/*"]
    });

    expect(browserExtensionPackagePlanDigest(plan)).toMatch(/^[0-9a-f]{64}$/u);
    expect(browserExtensionPackagePlanDigest(plan)).toBe(browserExtensionPackagePlanDigest(
      JSON.parse(browserExtensionPackagePlanJson({
        target: "chromium",
        contentScriptMatches: ["https://example.com/*"]
      })) as BrowserExtensionPackagePlan
    ));
    expect(browserExtensionPackagePlanDigest(plan)).not.toBe(browserExtensionPackagePlanDigest(
      buildBrowserExtensionPackagePlan({
        target: "chromium",
        popupMode: "origin_permission_approval",
        originPermissionStorageMode: "extension",
        contentScriptMatches: ["https://example.com/*"]
      })
    ));
  });

  it("renders a review envelope for package-build gating", () => {
    const review = createBrowserExtensionPackagePlanReview({
      target: "chromium",
      contentScriptMatches: ["https://example.com/*"]
    });

    expect(review).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT,
      package_plan_digest: browserExtensionPackagePlanDigest(review.package_plan),
      requires_user_review: true,
      installs_native_host_manifest: false,
      writes_extension_storage: false,
      stores_production_secrets: false,
      dispatches_signers: false
    });
  });

  it("rejects package-plan drift before a bundle can be treated as reviewed", () => {
    const plan = buildBrowserExtensionPackagePlan({
      target: "chromium",
      contentScriptMatches: ["https://example.com/*"]
    });

    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      native_host_name: "dev.nsealr.tampered"
    }))).toThrow(/native host/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      writes_extension_storage: true
    }))).toThrow(/extension storage/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        background: {
          service_worker: "background.js",
          type: "module"
        }
      }
    }))).toThrow(/background output/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        permissions: ["nativeMessaging", "storage"]
      }
    }))).toThrow(/storage permission profile/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      popup_mode: "origin_permission_approval",
      uses_active_tab_permission: false
    }))).toThrow(/activeTab/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        content_scripts: [{
          ...plan.manifest.content_scripts![0],
          js: ["content-script.js"]
        }]
      }
    }))).toThrow(/content-script output/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      entrypoints: [
        plan.entrypoints[0],
        plan.entrypoints[1],
        {
          ...plan.entrypoints[2],
          source: "apps/browser-extension/src/page-script.ts"
        },
        plan.entrypoints[3]
      ]
    }))).toThrow(/page_script entrypoint/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        action: {
          ...plan.manifest.action,
          default_popup: "popup.html"
        }
      }
    }))).toThrow(/popup html/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      entrypoints: [
        plan.entrypoints[0],
        plan.entrypoints[1],
        plan.entrypoints[2],
        {
          ...plan.entrypoints[3],
          output: "popup.js"
        }
      ]
    }))).toThrow(/action_popup entrypoint/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        web_accessible_resources: undefined
      }
    }))).toThrow(/page script/u);
    expect(() => assertBrowserExtensionPackagePlan(tamperedPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        web_accessible_resources: [{
          resources: ["page-script.js"],
          matches: ["https://example.com/*"]
        }]
      }
    }))).toThrow(/web-accessible/u);
  });
});
