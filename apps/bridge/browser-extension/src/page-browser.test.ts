import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import {
  installBrowserExtensionPageScriptBrowserProvider
} from "./page-browser.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  type BrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import { type BrowserExtensionPageWindowMessageListener } from "./page-window.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

function isPageBridgeRequest(value: unknown): value is BrowserExtensionPageBridgeRequest {
  return typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    (value as Record<string, unknown>).protocol === BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL &&
    (value as Record<string, unknown>).direction === "page_to_extension";
}

function createInjectedPageWindow(origin = "https://example.com"): {
  pageWindow: {
    nostr?: unknown;
    addEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    removeEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    postMessage(message: BrowserExtensionPageBridgeRequest | BrowserExtensionPageBridgeResponse, targetOrigin: string): void;
  };
  bridgeRequests: BrowserExtensionPageBridgeRequest[];
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionPageWindowMessageListener>();
  const bridgeRequests: BrowserExtensionPageBridgeRequest[] = [];
  const pageWindow = {
    nostr: undefined as unknown,
    addEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void {
      expect(type).toBe("message");
      listeners.add(listener);
    },
    removeEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void {
      expect(type).toBe("message");
      listeners.delete(listener);
    },
    postMessage(message: BrowserExtensionPageBridgeRequest | BrowserExtensionPageBridgeResponse, targetOrigin: string): void {
      expect(targetOrigin).toBe(origin);
      if (!isPageBridgeRequest(message)) return;
      bridgeRequests.push(message);
      for (const listener of listeners) {
        listener({
          source: pageWindow,
          origin,
          data: {
            protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
            version: 1,
            direction: "extension_to_page",
            request_id: message.request_id,
            response: {
              protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
              version: 1,
              request_id: message.request_id,
              ok: true,
              result: {
                pubkey: publicKey
              }
            }
          }
        });
      }
    }
  };
  return {
    pageWindow,
    bridgeRequests,
    listenerCount(): number {
      return listeners.size;
    }
  };
}

describe("browser extension page-script browser provider entrypoint", () => {
  it("installs NIP-07 over explicit browser-like window and location dependencies", async () => {
    const injectedWindow = createInjectedPageWindow();
    const provider = installBrowserExtensionPageScriptBrowserProvider({
      pageWindow: injectedWindow.pageWindow,
      location: { origin: "https://example.com" },
      nextRequestId: () => "page-browser-get-public-key"
    });

    await expect(provider.getPublicKey()).resolves.toBe(publicKey);
    expect(injectedWindow.pageWindow.nostr).toBe(provider);
    expect(injectedWindow.bridgeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-browser-get-public-key",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "page-browser-get-public-key",
        method: "get_public_key"
      }
    }]);
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("rejects invalid browser-like dependencies before provider injection", () => {
    const injectedWindow = createInjectedPageWindow();

    expect(() => installBrowserExtensionPageScriptBrowserProvider({
      pageWindow: injectedWindow.pageWindow,
      location: { origin: "https://example.com/path" }
    })).toThrow(/origin/u);
    expect(injectedWindow.pageWindow.nostr).toBeUndefined();

    expect(() => installBrowserExtensionPageScriptBrowserProvider({
      pageWindow: { nostr: undefined } as never,
      location: { origin: "https://example.com" }
    })).toThrow(/window/u);
  });
});
