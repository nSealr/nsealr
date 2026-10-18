import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL, type BrowserExtensionResponse } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import { installBrowserExtensionContentScriptEntrypoint } from "./content-entrypoint.js";
import {
  type BrowserExtensionContentWindowMessageListener,
  type BrowserExtensionContentWindowResponseTarget
} from "./content-window.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import {
  BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
  BROWSER_EXTENSION_PAGE_SCRIPT_FILE,
  type BrowserExtensionInjectedPageScriptElement,
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const sender = {
  extension_id: "extension@nsealr.dev",
  page_url: "https://example.com/app"
};

function createInjectedDocument(options: {
  existingElementIds?: string[];
} = {}): {
  document: BrowserExtensionPageScriptDocument;
  appended: BrowserExtensionInjectedPageScriptElement[];
  removed: BrowserExtensionInjectedPageScriptElement[];
} {
  const existingElementIds = new Set(options.existingElementIds ?? []);
  const appended: BrowserExtensionInjectedPageScriptElement[] = [];
  const removed: BrowserExtensionInjectedPageScriptElement[] = [];
  return {
    document: {
      createElement(tagName: "script"): BrowserExtensionInjectedPageScriptElement {
        expect(tagName).toBe("script");
        return {
          id: "",
          type: "",
          async: true,
          src: "",
          remove(): void {
            removed.push(this);
          }
        };
      },
      getElementById(id: string): unknown {
        return existingElementIds.has(id) ? { id } : null;
      },
      documentElement: {
        appendChild(element: BrowserExtensionInjectedPageScriptElement): unknown {
          appended.push(element);
          return element;
        }
      }
    },
    appended,
    removed
  };
}

function createInjectedWindowTarget(options: {
  failOnAdd?: boolean;
} = {}): {
  target: {
    addEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
    removeEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void;
  };
  dispatch(event: unknown): void;
  addCalls(): number;
  listenerCount(): number;
} {
  let addCalls = 0;
  const listeners = new Set<BrowserExtensionContentWindowMessageListener>();
  return {
    target: {
      addEventListener(type: "message", listener: BrowserExtensionContentWindowMessageListener): void {
        expect(type).toBe("message");
        addCalls += 1;
        if (options.failOnAdd === true) {
          throw new Error("content entrypoint listener unavailable");
        }
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
    addCalls(): number {
      return addCalls;
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

describe("browser extension content-script entrypoint wiring", () => {
  it("injects the page script and bridges accepted page requests to runtime messaging", async () => {
    const pageWindow = {};
    const injectedDocument = createInjectedDocument();
    const injectedWindow = createInjectedWindowTarget();
    const runtimeRequests: BrowserExtensionRequest[] = [];
    const responses: Array<{
      response: BrowserExtensionPageBridgeResponse;
      target: BrowserExtensionContentWindowResponseTarget;
    }> = [];

    const handle = installBrowserExtensionContentScriptEntrypoint({
      document: injectedDocument.document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`,
      windowTarget: injectedWindow.target,
      expectedSource: pageWindow,
      expectedOrigin: "https://example.com",
      sender,
      sendRuntimeMessage: (request) => {
        runtimeRequests.push(request);
        return getPublicKeyResponse(request.request_id);
      },
      postResponse: (response, target) => {
        responses.push({ response, target });
      }
    });

    expect(injectedDocument.appended).toHaveLength(1);
    expect(handle.pageScript.element).toEqual(expect.objectContaining({
      id: BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
      type: "module",
      async: false,
      src: `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`
    }));
    expect(injectedWindow.listenerCount()).toBe(1);

    injectedWindow.dispatch({
      source: pageWindow,
      origin: "https://example.com",
      data: pageBridgeRequest("content-entrypoint-get-public-key")
    });
    await flushAsyncListeners();

    expect(runtimeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "content-entrypoint-get-public-key",
      method: "get_public_key"
    }]);
    expect(responses).toEqual([{
      response: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-entrypoint-get-public-key",
        response: getPublicKeyResponse("content-entrypoint-get-public-key")
      },
      target: {
        source: pageWindow,
        origin: "https://example.com"
      }
    }]);

    handle.dispose();
    handle.dispose();
    expect(injectedWindow.listenerCount()).toBe(0);
    expect(injectedDocument.removed).toEqual([handle.pageScript.element]);
  });

  it("removes the page script if runtime bridge installation fails", () => {
    const injectedDocument = createInjectedDocument();
    const injectedWindow = createInjectedWindowTarget({ failOnAdd: true });

    expect(() => installBrowserExtensionContentScriptEntrypoint({
      document: injectedDocument.document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`,
      windowTarget: injectedWindow.target,
      expectedSource: {},
      expectedOrigin: "https://example.com",
      sender,
      sendRuntimeMessage: () => getPublicKeyResponse("unused"),
      postResponse: () => undefined
    })).toThrow(/listener unavailable/u);

    expect(injectedDocument.appended).toHaveLength(1);
    expect(injectedDocument.removed).toEqual([injectedDocument.appended[0]]);
    expect(injectedWindow.listenerCount()).toBe(0);
  });

  it("rejects duplicate page-script injection before adding a content listener", () => {
    const injectedWindow = createInjectedWindowTarget();

    expect(() => installBrowserExtensionContentScriptEntrypoint({
      document: createInjectedDocument({
        existingElementIds: [BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID]
      }).document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`,
      windowTarget: injectedWindow.target,
      expectedSource: {},
      expectedOrigin: "https://example.com",
      sender,
      sendRuntimeMessage: () => getPublicKeyResponse("unused"),
      postResponse: () => undefined
    })).toThrow(/already exists/u);

    expect(injectedWindow.addCalls()).toBe(0);
  });
});
