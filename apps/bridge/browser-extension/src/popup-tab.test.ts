import { describe, expect, it } from "vitest";
import {
  browserExtensionSenderFromPopupActiveTabOrigin,
  selectBrowserExtensionPopupActiveTabOrigin,
  type BrowserExtensionPopupTabsApi
} from "./popup-tab.js";

function tabsApi(result: unknown, calls: unknown[]): BrowserExtensionPopupTabsApi {
  return {
    query(queryInfo: { active: true; currentWindow: true }): unknown {
      calls.push(queryInfo);
      return result;
    }
  };
}

describe("browser extension popup active-tab origin selection", () => {
  it("selects one active tab origin without storing browser secrets", async () => {
    const calls: unknown[] = [];
    const selection = await selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([
        {
          id: 7,
          url: "https://example.com/path?q=1",
          title: "Example"
        }
      ], calls),
      extensionId: "extension@nsealr.dev",
      appName: "Example App"
    });

    expect(calls).toEqual([{ active: true, currentWindow: true }]);
    expect(selection).toEqual({
      tab_id: 7,
      tab_title: "Example",
      page_url: "https://example.com/path?q=1",
      page_origin: "https://example.com",
      extension_id: "extension@nsealr.dev",
      app_name: "Example App",
      stores_browser_secrets: false,
      contains_secret_material: false
    });
    expect(browserExtensionSenderFromPopupActiveTabOrigin(selection)).toEqual({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      page_url: "https://example.com/path?q=1",
      app_name: "Example App"
    });
  });

  it("allows local development HTTP origins but rejects unsupported browser pages", async () => {
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([{ id: 1, url: "http://localhost:5173/" }], []),
      extensionId: "extension@nsealr.dev"
    })).resolves.toMatchObject({
      page_origin: "http://localhost:5173",
      app_name: "nSealr Browser Extension",
      stores_browser_secrets: false,
      contains_secret_material: false
    });

    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([{ id: 1, url: "chrome://extensions/" }], []),
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/origin|scheme|url/u);
  });

  it("rejects ambiguous, malformed, or unsafe active tab selections", async () => {
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([], []),
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/ambiguous/u);
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([{ id: 1, url: "https://example.com/" }, { id: 2, url: "https://example.org/" }], []),
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/ambiguous/u);
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([{ id: -1, url: "https://example.com/" }], []),
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/tab id/u);
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: tabsApi([{ id: 1, url: "https://example.com/" }], []),
      extensionId: "bad extension id"
    })).rejects.toThrow(/extension id/u);
    await expect(selectBrowserExtensionPopupActiveTabOrigin({
      tabs: { query: "not-a-function" } as unknown as BrowserExtensionPopupTabsApi,
      extensionId: "extension@nsealr.dev"
    })).rejects.toThrow(/tabs API/u);
  });
});
