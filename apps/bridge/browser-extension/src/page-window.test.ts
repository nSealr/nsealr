import { describe, expect, it } from "vitest";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import { type BrowserNativeMessageSender } from "@nsealr/browser-provider";
import { createBrowserExtensionBackgroundController } from "./background.js";
import { installBrowserExtensionContentWindowBridgeListener } from "./content-window.js";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  createBrowserExtensionPageBridgeBackgroundRequester,
  type BrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import {
  createBrowserExtensionPageWindowBridgeExchange,
  type BrowserExtensionPageWindowMessageListener
} from "./page-window.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const routeRequest = {
  account_id: "esp32-usb-slot-0",
  method: "sign_event",
  route_type: "esp32_usb_nip46" as const
};
const sender = {
  extension_id: "extension@nsealr.dev",
  page_url: "https://example.com/app"
};

function routeSelectionResponse(request: LocalServiceRequest): unknown {
  return {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      route_selection: {
        format: "nsealr-route-selection-v0",
        account_id: routeRequest.account_id,
        public_key: publicKey,
        route_type: "esp32_usb_nip46",
        repository: "firmware",
        transport: "usb",
        custody: "device_persistent",
        trusted_review: "device_display",
        policy_support: "scoped_automation",
        policy_profile_id: "policy-manual-only-persistent-device",
        physical_review: true,
        physical_approval: true,
        persistent_grants: true,
        contains_secret_material: false
      }
    }
  };
}

function nativeResponder(requests: LocalServiceRequest[]): BrowserNativeMessageSender {
  return (_hostName, message) => {
    requests.push(message);
    if (message.operation === "select_account_route") return routeSelectionResponse(message);
    return handleLocalServiceRequest(message);
  };
}

function createInjectedPageWindow(origin = "https://example.com"): {
  pageWindow: {
    addEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    removeEventListener(type: "message", listener: BrowserExtensionPageWindowMessageListener): void;
    postMessage(message: BrowserExtensionPageBridgeRequest | BrowserExtensionPageBridgeResponse, targetOrigin: string): void;
  };
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionPageWindowMessageListener>();
  const pageWindow = {
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

function getPublicKeyRequest(requestId: string): BrowserExtensionRequest {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "get_public_key"
  };
}

describe("browser extension page-window bridge exchange", () => {
  it("round-trips page bridge messages through the injected window and content listener", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const errors: unknown[] = [];
    const injectedWindow = createInjectedPageWindow();
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "page-window-route"
    });
    installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: (request, requestSender, options) => controller.handleRequest(request, requestSender, options),
      postResponse: (response, target) => {
        expect(target.source).toBe(injectedWindow.pageWindow);
        injectedWindow.pageWindow.postMessage(response, target.origin);
      },
      onError: (error) => {
        errors.push(error);
      }
    });
    const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
      exchangeBridgeMessage: createBrowserExtensionPageWindowBridgeExchange({
        target: injectedWindow.pageWindow,
        expectedSource: injectedWindow.pageWindow,
        expectedOrigin: "https://example.com"
      })
    });

    await expect(requestBackground(getPublicKeyRequest("page-window-get-public-key"), {})).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-window-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    });
    expect(nativeRequests.map((request) => request.operation)).toEqual(["select_account_route"]);
    expect(errors).toEqual([]);
    expect(injectedWindow.listenerCount()).toBe(1);
  });

  it("ignores unrelated responses and rejects malformed matching responses", async () => {
    const injectedWindow = createInjectedPageWindow();
    const exchangeBridgeMessage = createBrowserExtensionPageWindowBridgeExchange({
      target: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com"
    });
    const request = {
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-window-malformed-response",
      request: getPublicKeyRequest("page-window-malformed-response")
    } as const;

    const response = exchangeBridgeMessage(request, {});
    injectedWindow.pageWindow.postMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "other-request",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "other-request",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    }, "https://example.com");
    injectedWindow.pageWindow.postMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "page-window-malformed-response",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "page-window-malformed-response",
        ok: true
      }
    } as never, "https://example.com");

    await expect(response).rejects.toThrow(/result/u);
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("rejects already-cancelled requests before posting", async () => {
    const injectedWindow = createInjectedPageWindow();
    const abortController = new AbortController();
    abortController.abort();
    const exchangeBridgeMessage = createBrowserExtensionPageWindowBridgeExchange({
      target: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com",
      abortSignal: abortController.signal
    });

    await expect(exchangeBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-window-cancelled",
      request: getPublicKeyRequest("page-window-cancelled")
    }, {})).rejects.toThrow(/cancelled/u);
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("forwards request aborts and cleans up the response listener", async () => {
    const injectedWindow = createInjectedPageWindow();
    const abortController = new AbortController();
    const exchangeBridgeMessage = createBrowserExtensionPageWindowBridgeExchange({
      target: injectedWindow.pageWindow,
      expectedSource: injectedWindow.pageWindow,
      expectedOrigin: "https://example.com"
    });

    const response = exchangeBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-window-request-abort",
      request: getPublicKeyRequest("page-window-request-abort")
    }, {
      abortSignal: abortController.signal
    });
    expect(injectedWindow.listenerCount()).toBe(1);
    abortController.abort();

    await expect(response).rejects.toThrow(/cancelled/u);
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("rejects timeout and postMessage failures with listener cleanup", async () => {
    const silentWindow = createInjectedPageWindow();
    const timeoutExchange = createBrowserExtensionPageWindowBridgeExchange({
      target: silentWindow.pageWindow,
      expectedSource: silentWindow.pageWindow,
      expectedOrigin: "https://example.com",
      responseTimeoutMs: 1
    });
    await expect(timeoutExchange({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-window-timeout",
      request: getPublicKeyRequest("page-window-timeout")
    }, {})).rejects.toThrow(/timed out/u);
    expect(silentWindow.listenerCount()).toBe(0);

    const throwingWindow = createInjectedPageWindow();
    const postFailure = new Error("postMessage failed");
    const failingTarget = {
      ...throwingWindow.pageWindow,
      postMessage: (): void => {
        throw postFailure;
      }
    };
    const failingExchange = createBrowserExtensionPageWindowBridgeExchange({
      target: failingTarget,
      expectedSource: throwingWindow.pageWindow,
      expectedOrigin: "https://example.com"
    });
    await expect(failingExchange({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "page-window-post-failure",
      request: getPublicKeyRequest("page-window-post-failure")
    }, {})).rejects.toBe(postFailure);
    expect(throwingWindow.listenerCount()).toBe(0);
  });

  it("rejects unsafe page-window exchange options", () => {
    expect(() => createBrowserExtensionPageWindowBridgeExchange({
      target: createInjectedPageWindow().pageWindow,
      expectedSource: {},
      expectedOrigin: "https://example.com/path"
    })).toThrow(/expected origin/u);
    expect(() => createBrowserExtensionPageWindowBridgeExchange({
      target: createInjectedPageWindow().pageWindow,
      expectedSource: {},
      expectedOrigin: "https://example.com",
      responseTimeoutMs: 0
    })).toThrow(/timeout/u);
  });
});
