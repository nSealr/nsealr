import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  handleBrowserExtensionRequest,
  type BrowserExtensionHandlerOptions
} from "./handler.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  handleBrowserExtensionPageBridgeRequest
} from "./page-bridge.js";
import { installBrowserExtensionContentScriptRuntimeBridge } from "./content-bootstrap.js";
import {
  installBrowserExtensionPageScriptProvider,
  installBrowserExtensionPageScriptWindowProvider
} from "./page-script.js";
import { type BrowserExtensionPageWindowMessageListener } from "./page-window.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const eventTemplate = {
  kind: 1,
  created_at: 1_710_000_000,
  tags: [],
  content: "nSealr fixture: basic kind 1 event."
};
const signedEvent = {
  id: "2977f107ad2668dbd9f09b8594eff3b5276e21bfe098e60ae3e905e3c861e4d3",
  pubkey: publicKey,
  created_at: 1_710_000_000,
  kind: 1,
  tags: [],
  content: "nSealr fixture: basic kind 1 event.",
  sig: "2eec0351eb1d651140922d4b1f1bd8135f4474aabf42ec5bda7011087c1a072d71be863646dc162e4d96eacf14afeed2618a4acb0e1134a273a2b8e73039e654"
};

const provider: BrowserExtensionHandlerOptions["provider"] = {
  getPublicKey: async () => publicKey,
  signEvent: async () => signedEvent
};

function createInjectedPageWindow(origin = "https://example.com"): {
  pageWindow: {
    nostr?: unknown;
    addEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    removeEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    postMessage(message: unknown, targetOrigin: string): void;
  };
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionPageWindowMessageListener>();
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
    postMessage(message: unknown, targetOrigin: string): void {
      expect(targetOrigin).toBe(origin);
      for (const listener of listeners) {
        listener({
          source: pageWindow,
          origin,
          data: message
        });
      }
    }
  };
  return {
    pageWindow,
    listenerCount(): number {
      return listeners.size;
    }
  };
}

describe("browser extension page-script provider bootstrap", () => {
  it("installs a NIP-07 provider over the injected page bridge exchange", async () => {
    const target: { nostr?: unknown } = {};
    const bridgeRequests: unknown[] = [];
    const pageProvider = installBrowserExtensionPageScriptProvider({
      target,
      nextRequestId: () => "page-script-get-public-key",
      exchangeBridgeMessage: (bridgeRequest) => {
        bridgeRequests.push(bridgeRequest);
        return handleBrowserExtensionPageBridgeRequest(bridgeRequest, {
          requestBackground: (request) => handleBrowserExtensionRequest(request, { provider })
        });
      }
    });

    await expect(pageProvider.getPublicKey()).resolves.toBe(publicKey);
    expect(target.nostr).toBe(pageProvider);
    expect(bridgeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-script-get-public-key",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "page-script-get-public-key",
        method: "get_public_key"
      }
    }]);
  });

  it("routes signEvent through the same bridge without accepting bad responses", async () => {
    const pageProvider = installBrowserExtensionPageScriptProvider({
      target: {},
      nextRequestId: () => "page-script-sign-event",
      exchangeBridgeMessage: (bridgeRequest) => handleBrowserExtensionPageBridgeRequest(bridgeRequest, {
        requestBackground: (request) => handleBrowserExtensionRequest(request, { provider })
      })
    });

    await expect(pageProvider.signEvent(eventTemplate)).resolves.toEqual(signedEvent);
  });

  it("does not overwrite an existing page provider", () => {
    expect(() => installBrowserExtensionPageScriptProvider({
      target: { nostr: {} },
      exchangeBridgeMessage: () => ({})
    })).toThrow(/already has a nostr provider/u);
  });

  it("rejects cancelled page-provider calls before bridge exchange", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const pageProvider = installBrowserExtensionPageScriptProvider({
      target: {},
      abortSignal: abortController.signal,
      exchangeBridgeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(pageProvider.getPublicKey()).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);
  });

  it("installs a NIP-07 provider over the page-window bridge and content runtime bridge", async () => {
    const injectedWindow = createInjectedPageWindow();
    const runtimeRequests: unknown[] = [];
    installBrowserExtensionContentScriptRuntimeBridge({
      target: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com",
      sender: {
        extension_id: "extension@nsealr.dev",
        page_url: "https://example.com/app"
      },
      sendRuntimeMessage: (request) => {
        runtimeRequests.push(request);
        if (request.method === "get_public_key") {
          return {
            protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
            version: 1,
            request_id: request.request_id,
            ok: true,
            result: {
              pubkey: publicKey
            }
          };
        }
        return handleBrowserExtensionRequest(request, { provider });
      },
      postResponse: (response, target) => {
        expect(target.source).toBe(injectedWindow.pageWindow);
        injectedWindow.pageWindow.postMessage(response, target.origin);
      }
    });

    const pageProvider = installBrowserExtensionPageScriptWindowProvider({
      providerTarget: injectedWindow.pageWindow,
      windowTarget: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com",
      nextRequestId: () => "page-window-provider-get-public-key"
    });

    await expect(pageProvider.getPublicKey()).resolves.toBe(publicKey);
    expect(injectedWindow.pageWindow.nostr).toBe(pageProvider);
    expect(runtimeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-window-provider-get-public-key",
      method: "get_public_key"
    }]);
    expect(injectedWindow.listenerCount()).toBe(1);
  });
});
