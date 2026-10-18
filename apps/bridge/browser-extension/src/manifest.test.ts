import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_DESCRIPTION,
  BROWSER_EXTENSION_NAME,
  BROWSER_EXTENSION_VERSION,
  browserExtensionManifestJson,
  buildBrowserExtensionManifest
} from "./manifest.js";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";

describe("browser extension manifest boundary", () => {
  it("builds a minimal Chromium manifest without page or storage permissions", () => {
    const manifest = buildBrowserExtensionManifest({ target: "chromium" });
    expect(manifest).toEqual({
      manifest_version: 3,
      name: BROWSER_EXTENSION_NAME,
      description: BROWSER_EXTENSION_DESCRIPTION,
      version: BROWSER_EXTENSION_VERSION,
      permissions: ["nativeMessaging"],
      background: {
        service_worker: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
        type: "module"
      },
      action: {
        default_title: BROWSER_EXTENSION_NAME,
        default_popup: BROWSER_EXTENSION_POPUP_HTML_FILE
      }
    });
    expect("host_permissions" in manifest).toBe(false);
    expect("optional_host_permissions" in manifest).toBe(false);
    expect("content_scripts" in manifest).toBe(false);
    expect("web_accessible_resources" in manifest).toBe(false);
    expect(manifest.permissions).not.toContain("storage");
  });

  it("builds an explicit-origin content-script manifest without wildcard host access", () => {
    const manifest = buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: [
        "https://example.com/*",
        "http://localhost:5173/*"
      ]
    });
    expect(manifest.permissions).toEqual(["nativeMessaging"]);
    expect("host_permissions" in manifest).toBe(false);
    expect("optional_host_permissions" in manifest).toBe(false);
    expect(manifest.content_scripts).toEqual([{
      matches: [
        "https://example.com/*",
        "http://localhost:5173/*"
      ],
      js: [BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE],
      run_at: "document_start",
      all_frames: false,
      match_about_blank: false
    }]);
    expect(manifest.web_accessible_resources).toEqual([{
      resources: [BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE],
      matches: [
        "https://example.com/*",
        "http://localhost:5173/*"
      ]
    }]);
    expect(manifest.permissions).not.toContain("storage");
  });

  it("builds an explicit popup-origin approval manifest without broad host access", () => {
    const manifest = buildBrowserExtensionManifest({
      target: "chromium",
      popupMode: "origin_permission_approval",
      originPermissionStorageMode: "extension",
      contentScriptMatches: ["https://example.com/*"]
    });
    expect(manifest.permissions).toEqual(["nativeMessaging", "activeTab", "storage"]);
    expect("host_permissions" in manifest).toBe(false);
    expect("optional_host_permissions" in manifest).toBe(false);
    expect(manifest.content_scripts?.[0].matches).toEqual(["https://example.com/*"]);
  });

  it("builds a Firefox manifest only with an explicit reviewed extension id", () => {
    const manifest = buildBrowserExtensionManifest({
      target: "firefox",
      firefoxExtensionId: "extension@nsealr.dev"
    });
    expect(manifest).toMatchObject({
      manifest_version: 3,
      permissions: ["nativeMessaging"],
      browser_specific_settings: {
        gecko: {
          id: "extension@nsealr.dev"
        }
      }
    });
    expect("host_permissions" in manifest).toBe(false);
    expect("optional_host_permissions" in manifest).toBe(false);
  });

  it("renders deterministic manifest JSON", () => {
    expect(JSON.parse(browserExtensionManifestJson({ target: "chromium" }))).toEqual(
      buildBrowserExtensionManifest({ target: "chromium" })
    );
  });

  it("rejects ambiguous packaging inputs", () => {
    expect(() => buildBrowserExtensionManifest({
      target: "firefox"
    })).toThrow(/firefox extension id/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      name: ""
    })).toThrow(/name/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      version: "0.1.0-beta"
    })).toThrow(/version/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["<all_urls>"]
    })).toThrow(/content script match/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["https://*.example.com/*"]
    })).toThrow(/content script match/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["http://example.com/*"]
    })).toThrow(/content script match/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["http://localhost:0/*"]
    })).toThrow(/content script match/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["http://localhost:65536/*"]
    })).toThrow(/content script match/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      contentScriptMatches: ["https://example.com/*", "https://example.com/*"]
    })).toThrow(/duplicated/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      popupMode: "unsupported" as never
    })).toThrow(/popup mode/u);
    expect(() => buildBrowserExtensionManifest({
      target: "chromium",
      originPermissionStorageMode: "unsupported" as never
    })).toThrow(/storage mode/u);
  });
});
