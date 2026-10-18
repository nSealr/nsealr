import { describe, expect, it } from "vitest";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import { type BrowserNativeMessageSender } from "@nsealr/browser-provider";
import {
  createBrowserExtensionBackgroundController,
  type BrowserExtensionBackgroundRequestOptions
} from "./background.js";
import {
  createBrowserExtensionContentWindowResponsePoster,
  handleBrowserExtensionContentWindowBridgeEvent,
  installBrowserExtensionContentWindowBridgeListener,
  type BrowserExtensionContentWindowMessageListener
} from "./content-window.js";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL, type BrowserExtensionResponse } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import { BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL } from "./page-bridge.js";

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

function pageBridgeRequest(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
    version: 1,
    direction: "page_to_extension",
    request_id: requestId,
    request: {
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: requestId,
      method: "get_public_key"
    }
  };
}

function getPublicKeyResponse(requestId: string): BrowserExtensionResponse {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    ok: true,
    result: {
      pubkey: publicKey
    }
  };
}

function createInjectedWindowTarget(): {
  target: {
    addEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
    removeEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
  };
  dispatch(event: unknown): void;
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionContentWindowMessageListener>();
  return {
    target: {
      addEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void {
        expect(type).toBe("message");
        listeners.add(listener);
      },
      removeEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void {
        expect(type).toBe("message");
        listeners.delete(listener);
      }
    },
    dispatch(event: unknown): void {
      for (const listener of listeners) {
        listener(event);
      }
    },
    listenerCount(): number {
      return listeners.size;
    }
  };
}

async function flushAsyncListeners(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("browser extension content-window bridge boundary", () => {
  it("posts extension responses to the reviewed page response target", () => {
    const postMessages: unknown[] = [];
    const pageWindow = {
      postMessage(message: unknown, targetOrigin: string): void {
        postMessages.push({ message, targetOrigin });
      }
    };
    const postResponse = createBrowserExtensionContentWindowResponsePoster();
    const response = {
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-window-response-poster",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-window-response-poster",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    } as const;

    postResponse(response, {
      source: pageWindow,
      origin: "https://example.com"
    });

    expect(postMessages).toEqual([{
      message: response,
      targetOrigin: "https://example.com"
    }]);
  });

  it("rejects unsafe response targets before posting", () => {
    const postResponse = createBrowserExtensionContentWindowResponsePoster();
    const response = {
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-window-response-poster-invalid",
      response: getPublicKeyResponse("content-window-response-poster-invalid")
    } as const;

    expect(() => postResponse(response, {
      source: {},
      origin: "https://example.com"
    })).toThrow(/response target/u);
    expect(() => postResponse(response, {
      source: { postMessage: () => undefined },
      origin: "https://example.com/path"
    })).toThrow(/response origin/u);
  });

  it("accepts page bridge events only from the expected source and origin", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const pageWindow = {};
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "content-window-route"
    });

    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-window-get-public-key")
    }, {
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: (request, requestSender, options) => controller.handleRequest(request, requestSender, options)
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-window-get-public-key",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-window-get-public-key",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    });
    expect(nativeRequests.map((request) => request.operation)).toEqual(["select_account_route"]);
  });

  it("ignores unrelated or untrusted page messages without contacting background", async () => {
    const expectedSource = {};
    const nativeRequests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest
    });
    const options = {
      expectedSource,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: (
        request: BrowserExtensionRequest,
        requestSender: unknown,
        requestOptions: BrowserExtensionBackgroundRequestOptions
      ) =>
        controller.handleRequest(request, requestSender, requestOptions)
    };

    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: {},
      origin: "https://example.com",
      data: pageBridgeRequest("wrong-source")
    }, options)).resolves.toBeUndefined();
    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: expectedSource,
      origin: "https://evil.example",
      data: pageBridgeRequest("wrong-origin")
    }, options)).resolves.toBeUndefined();
    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: expectedSource,
      origin: "https://example.com",
      data: { protocol: "other-protocol" }
    }, options)).resolves.toBeUndefined();
    expect(nativeRequests).toEqual([]);
  });

  it("rejects malformed nSealr page bridge events before contacting background", async () => {
    const pageWindow = {};
    let called = false;
    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: pageWindow,
      origin: "https://example.com",
      data: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "unsupported_direction",
        request_id: "content-window-wrong-direction",
        request: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-window-wrong-direction",
          method: "get_public_key"
        }
      }
    }, {
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => {
        called = true;
        return {};
      }
    })).rejects.toThrow(/direction/u);
    expect(called).toBe(false);
  });

  it("rejects non-object content-window events before bridge handling", async () => {
    await expect(handleBrowserExtensionContentWindowBridgeEvent(null, {
      expectedSource: {},
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => ({})
    })).rejects.toThrow(/event must be an object/u);
  });

  it("rejects invalid expected origins before bridge handling", async () => {
    const pageWindow = {};
    await expect(handleBrowserExtensionContentWindowBridgeEvent({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("invalid-expected-origin")
    }, {
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com/path",
      sender,
      requestBackground: () => ({})
    })).rejects.toThrow(/expected origin/u);
  });

  it("installs an injected window listener and posts accepted bridge responses", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const responses: unknown[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "content-window-listener-route"
    });

    const handle = installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: (request, requestSender, options) => controller.handleRequest(request, requestSender, options),
      postResponse: (response, target) => {
        responses.push({ response, target });
      }
    });
    expect(injectedWindow.listenerCount()).toBe(1);

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-window-listener")
    });
    await flushAsyncListeners();

    expect(responses).toEqual([{
      response: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-window-listener",
        response: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-window-listener",
          ok: true,
          result: {
            pubkey: publicKey
          }
        }
      },
      target: {
        source: pageWindow,
        origin: "https://example.com"
      }
    }]);
    expect(nativeRequests.map((request) => request.operation)).toEqual(["select_account_route"]);

    handle.dispose();
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("posts deterministic listener failures for accepted bridge requests", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const responses: unknown[] = [];
    const errors: unknown[] = [];
    const backgroundFailure = new Error("background bridge failed");

    installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => {
        throw backgroundFailure;
      },
      postResponse: (response, target) => {
        responses.push({ response, target });
      },
      onError: (error) => {
        errors.push(error);
      }
    });

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-window-listener-failure")
    });
    await flushAsyncListeners();

    expect(errors).toEqual([backgroundFailure]);
    expect(responses).toEqual([{
      response: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-window-listener-failure",
        response: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-window-listener-failure",
          ok: false,
          error: {
            code: "content_window_bridge_failed",
            message: "browser content-window bridge request failed",
            retryable: false
          }
        }
      },
      target: {
        source: pageWindow,
        origin: "https://example.com"
      }
    }]);
  });

  it("ignores unrelated listener messages and extension responses", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const responses: unknown[] = [];
    const errors: unknown[] = [];

    installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => {
        throw new Error("background must not be contacted");
      },
      postResponse: (response) => {
        responses.push(response);
      },
      onError: (error) => {
        errors.push(error);
      }
    });

    injectedWindow.dispatch({
      source: {},
      origin: "https://example.com",
      data: pageBridgeRequest("content-window-listener-wrong-source")
    });
    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-window-listener-response",
        response: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-window-listener-response",
          ok: true,
          result: {
            pubkey: publicKey
          }
        }
      }
    });
    await flushAsyncListeners();

    expect(responses).toEqual([]);
    expect(errors).toEqual([]);
  });

  it("reports malformed incoming nSealr envelopes", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const responses: unknown[] = [];
    const errors: unknown[] = [];

    installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => {
        throw new Error("background must not be contacted");
      },
      postResponse: (response) => {
        responses.push(response);
      },
      onError: (error) => {
        errors.push(error);
      }
    });

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "unsupported_direction",
        request_id: "content-window-listener-malformed",
        request: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-window-listener-malformed",
          method: "get_public_key"
        }
      }
    });
    await flushAsyncListeners();

    expect(responses).toEqual([]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect((errors[0] as Error).message).toMatch(/direction/u);
  });

  it("does not receive events after disposal", async () => {
    const injectedWindow = createInjectedWindowTarget();
    const pageWindow = {};
    const handle = installBrowserExtensionContentWindowBridgeListener({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      requestBackground: () => {
        throw new Error("disposed listener must not be called");
      },
      postResponse: () => {
        throw new Error("disposed listener must not post");
      }
    });
    handle.dispose();
    expect(injectedWindow.listenerCount()).toBe(0);

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-window-disposed")
    });
    await flushAsyncListeners();
  });
});
