import { describe, expect, it } from "vitest";
import { NATIVE_HOST_NAME } from "@nsealr/client";
import {
  BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
  BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT
} from "./package-plan.js";
import {
  browserExtensionPackagePlanJsonFromArgs
} from "./package-plan-cli.js";

describe("browser extension package-plan CLI", () => {
  it("renders a deterministic Chromium package plan from args", () => {
    const plan = JSON.parse(browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*"
    ]));

    expect(plan).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
      target: "chromium",
      native_host_name: NATIVE_HOST_NAME,
      installs_native_host_manifest: false,
      writes_extension_storage: false,
      stores_production_secrets: false,
      dispatches_signers: false
    });
    expect(plan.manifest.content_scripts).toEqual([{
      matches: ["https://example.com/*"],
      js: ["nsealr-content-script-entrypoint.js"],
      run_at: "document_start",
      all_frames: false,
      match_about_blank: false
    }]);
    expect(plan.manifest.web_accessible_resources).toEqual([{
      resources: ["nsealr-page-script-entrypoint.js"],
      matches: ["https://example.com/*"]
    }]);
    expect(plan.manifest.action.default_popup).toBe("nsealr-popup.html");
  });

  it("renders a Firefox package plan only with an explicit extension id", () => {
    const plan = JSON.parse(browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "firefox",
      "--firefox-extension-id",
      "extension@nsealr.dev"
    ]));

    expect(plan.target).toBe("firefox");
    expect(plan.manifest.browser_specific_settings.gecko.id).toBe("extension@nsealr.dev");
  });

  it("renders an explicit extension-storage origin approval package plan", () => {
    const plan = JSON.parse(browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*",
      "--origin-permission-mode",
      "extension-storage"
    ]));

    expect(plan).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
      target: "chromium",
      popup_mode: "origin_permission_approval",
      writes_extension_storage: false,
      uses_extension_storage: true,
      uses_active_tab_permission: true,
      stores_production_secrets: false,
      dispatches_signers: false
    });
    expect(plan.manifest.permissions).toEqual(["nativeMessaging", "activeTab", "storage"]);
    expect(plan.manifest.content_scripts[0].matches).toEqual(["https://example.com/*"]);
    expect("host_permissions" in plan.manifest).toBe(false);
  });

  it("keeps embedded origin-permission package plans storage-free", () => {
    const plan = JSON.parse(browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*",
      "--origin-permission-mode",
      "embedded"
    ]));

    expect(plan.popup_mode).toBe("pending_requests");
    expect(plan.uses_extension_storage).toBe(false);
    expect(plan.uses_active_tab_permission).toBe(false);
    expect(plan.manifest.permissions).toEqual(["nativeMessaging"]);
  });

  it("renders a review envelope with the package-plan digest", () => {
    const review = JSON.parse(browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*",
      "--review"
    ]));

    expect(review).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_REVIEW_FORMAT,
      package_plan_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
      requires_user_review: true,
      installs_native_host_manifest: false,
      writes_extension_storage: false,
      stores_production_secrets: false,
      dispatches_signers: false
    });
    expect(review.package_plan).toMatchObject({
      format: BROWSER_EXTENSION_PACKAGE_PLAN_FORMAT,
      target: "chromium"
    });
  });

  it("rejects unsupported or incomplete package-plan args before JSON output", () => {
    expect(() => browserExtensionPackagePlanJsonFromArgs([])).toThrow(/target is required/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "safari"
    ])).toThrow(/chromium or firefox/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match"
    ])).toThrow(/requires a value/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "<all_urls>"
    ])).toThrow(/content script match/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--target",
      "firefox"
    ])).toThrow(/specified only once/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--firefox-extension-id",
      "extension@nsealr.dev"
    ])).toThrow(/only valid for Firefox/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "firefox",
      "--firefox-extension-id",
      "extension@nsealr.dev",
      "--firefox-extension-id",
      "other@nsealr.dev"
    ])).toThrow(/specified only once/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--review",
      "--review"
    ])).toThrow(/specified only once/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--origin-permission-mode",
      "extension-storage"
    ])).toThrow(/content-script match/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*",
      "--origin-permission-mode",
      "none"
    ])).toThrow(/embedded or extension-storage/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--content-script-match",
      "https://example.com/*",
      "--origin-permission-mode",
      "embedded",
      "--origin-permission-mode",
      "extension-storage"
    ])).toThrow(/specified only once/u);
    expect(() => browserExtensionPackagePlanJsonFromArgs([
      "--target",
      "chromium",
      "--write"
    ])).toThrow(/unsupported/u);
  });
});
