import { describe, expect, it } from "vitest";
import { type BrowserExtensionOriginPermissionReview } from "./pairing.js";
import {
  requestBrowserExtensionPopupActiveTabOriginPermissionReview,
  type BrowserExtensionPopupOriginPermissionReviewControls
} from "./popup-origin-permission.js";
import { type BrowserExtensionPopupOriginPermissionReviewResult } from "./popup-control.js";
import { type BrowserExtensionPopupTabsApi } from "./popup-tab.js";

const digest = "d".repeat(64);

function tabsApi(result: unknown, calls: unknown[]): BrowserExtensionPopupTabsApi {
  return {
    query(queryInfo: { active: true; currentWindow: true }): unknown {
      calls.push(queryInfo);
      return result;
    }
  };
}

function originReview(origin = "https://example.com"): BrowserExtensionOriginPermissionReview {
  return {
    format: "nsealr-browser-origin-permission-review-v0",
    origin,
    app_name: "Example App",
    extension_id: "extension@nsealr.dev",
    requested_methods: [
      {
        method: "get_public_key",
        label: "Read public key",
        effect: "The page can read the selected account public key through the browser provider."
      },
      {
        method: "sign_event",
        label: "Request event signatures",
        effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
      }
    ],
    local_pairing_digest: digest,
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  };
}

describe("browser extension popup active-tab origin permission review", () => {
  it("requests review metadata for the normalized active tab without browser storage or grants", async () => {
    const tabCalls: unknown[] = [];
    const requestedSenders: unknown[] = [];
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview(sender) {
        requestedSenders.push(sender);
        return {
          origin_review: originReview(),
          stores_production_secrets: false,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false
        };
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 11, url: "https://example.com/app", title: "Example" }], tabCalls),
      controls,
      extensionId: "extension@nsealr.dev",
      appName: "Example App"
    })).resolves.toEqual({
      active_tab: {
        tab_id: 11,
        tab_title: "Example",
        page_url: "https://example.com/app",
        page_origin: "https://example.com",
        extension_id: "extension@nsealr.dev",
        app_name: "Example App",
        stores_browser_secrets: false,
        contains_secret_material: false
      },
      origin_review: originReview(),
      stores_browser_secrets: false,
      contains_secret_material: false,
      writes_browser_storage: false,
      creates_grants: false,
      injects_provider: false,
      dispatches_signers: false
    });
    expect(tabCalls).toEqual([{ active: true, currentWindow: true }]);
    expect(requestedSenders).toEqual([{
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      page_url: "https://example.com/app",
      app_name: "Example App"
    }]);
  });

  it("rejects mismatched review metadata before rendering or approval", async () => {
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview() {
        return {
          origin_review: originReview("https://attacker.example"),
          stores_production_secrets: false,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false
        };
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 11, url: "https://example.com/app" }], []),
      controls,
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/origin/u);
  });

  it("rejects mismatched app metadata before rendering or approval", async () => {
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview() {
        return {
          origin_review: {
            ...originReview(),
            app_name: "Different App"
          },
          stores_production_secrets: false,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false
        };
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 11, url: "https://example.com/app" }], []),
      controls,
      extensionId: "extension@nsealr.dev",
      appName: "Example App"
    })).rejects.toThrow(/app name/u);
  });

  it("rejects authorizing or secret-carrying review results even when controls are injected", async () => {
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview() {
        return {
          origin_review: originReview(),
          stores_production_secrets: true,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false
        } as unknown as BrowserExtensionPopupOriginPermissionReviewResult;
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 11, url: "https://example.com/app" }], []),
      controls,
      extensionId: "extension@nsealr.dev",
      appName: "Example App"
    })).rejects.toThrow(/secretless/u);
  });

  it("rejects unsupported review result fields even when controls are injected", async () => {
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview() {
        return {
          origin_review: originReview(),
          stores_production_secrets: false,
          contains_secret_material: false,
          creates_grants: false,
          injects_provider: false,
          writes_browser_storage: true
        } as unknown as BrowserExtensionPopupOriginPermissionReviewResult;
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 11, url: "https://example.com/app" }], []),
      controls,
      extensionId: "extension@nsealr.dev",
      appName: "Example App"
    })).rejects.toThrow(/unsupported fields/u);
  });

  it("rejects unsupported active tabs before contacting popup controls", async () => {
    let called = false;
    const controls: BrowserExtensionPopupOriginPermissionReviewControls = {
      async requestOriginPermissionReview() {
        called = true;
        throw new Error("unsupported tab must not request review");
      }
    };

    await expect(requestBrowserExtensionPopupActiveTabOriginPermissionReview({
      tabs: tabsApi([{ id: 1, url: "chrome://extensions/" }], []),
      controls,
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/origin|scheme|url/u);
    expect(called).toBe(false);
  });
});
