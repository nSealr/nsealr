import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL, type BrowserExtensionResponse } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import { installBrowserExtensionContentScriptRuntimeBridge } from "./content-bootstrap.js";
import {
  type BrowserExtensionContentWindowMessageListener,
  type BrowserExtensionContentWindowResponseTarget
} from "./content-window.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const sender = {
  extension_id: "extension@nsealr.dev",
  page_url: "https://example.com/app"
};

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

async function flushAsyncListeners(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("browser extension content-script runtime bridge bootstrap", () => {
  it("installs a window listener that forwards accepted page requests to runtime messaging", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const runtimeRequests: unknown[] = [];
    const responses: Array<{
      response: BrowserExtensionPageBridgeResponse;
      target: BrowserExtensionContentWindowResponseTarget;
    }> = [];
    const handle = installBrowserExtensionContentScriptRuntimeBridge({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      sendRuntimeMessage: (request, options) => {
        runtimeRequests.push({
          request,
          abortSignalForwarded: options.abortSignal !== undefined
        });
        return getPublicKeyResponse(request.request_id);
      },
      postResponse: (response, target) => {
        responses.push({ response, target });
      }
    });
    expect(injectedWindow.listenerCount()).toBe(1);

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-bootstrap-get-public-key")
    });
    await flushAsyncListeners();

    expect(runtimeRequests).toEqual([{
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-bootstrap-get-public-key",
        method: "get_public_key"
      },
      abortSignalForwarded: false
    }]);
    expect(responses).toEqual([{
      response: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-bootstrap-get-public-key",
        response: getPublicKeyResponse("content-bootstrap-get-public-key")
      },
      target: {
        source: pageWindow,
        origin: "https://example.com"
      }
    }]);

    handle.dispose();
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("forwards cancellation into the injected runtime sender", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const abortController = new AbortController();
    let seenSignal: AbortSignal | undefined;
    installBrowserExtensionContentScriptRuntimeBridge({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      abortSignal: abortController.signal,
      sendRuntimeMessage: (request, options) => {
        seenSignal = options.abortSignal;
        return getPublicKeyResponse(request.request_id);
      },
      postResponse: () => undefined
    });

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-bootstrap-cancellation")
    });
    await flushAsyncListeners();

    expect(seenSignal).toBe(abortController.signal);
  });

  it("reports malformed accepted page envelopes and ignores unrelated messages", async () => {
    const pageWindow = {};
    const injectedWindow = createInjectedWindowTarget();
    const errors: unknown[] = [];
    const runtimeRequests: BrowserExtensionRequest[] = [];
    const responses: unknown[] = [];
    installBrowserExtensionContentScriptRuntimeBridge({
      target: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      sendRuntimeMessage: (request) => {
        runtimeRequests.push(request);
        return getPublicKeyResponse(request.request_id);
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
      data: pageBridgeRequest("content-bootstrap-wrong-source")
    });
    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "unsupported_direction",
        request_id: "content-bootstrap-malformed",
        request: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-bootstrap-malformed",
          method: "get_public_key"
        }
      }
    });
    await flushAsyncListeners();

    expect(runtimeRequests).toEqual([]);
    expect(responses).toEqual([]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect((errors[0] as Error).message).toMatch(/direction/u);
  });
});
