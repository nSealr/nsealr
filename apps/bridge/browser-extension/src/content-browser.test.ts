import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL, type BrowserExtensionResponse } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import { installBrowserExtensionContentScriptBrowserEntrypoint } from "./content-browser.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL
} from "./page-bridge.js";
import {
  BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
  BROWSER_EXTENSION_PAGE_SCRIPT_FILE,
  type BrowserExtensionInjectedPageScriptElement,
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

function createInjectedDocument(): {
  document: BrowserExtensionPageScriptDocument;
  appended: BrowserExtensionInjectedPageScriptElement[];
  removed: BrowserExtensionInjectedPageScriptElement[];
} {
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
      getElementById(): unknown {
        return null;
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

type WindowMessageListener = (event: unknown) => void;

function createInjectedPageWindow(): {
  window: {
    addEventListener(type: "message", listener: WindowMessageListener): void;
    removeEventListener(type: "message", listener: WindowMessageListener): void;
    postMessage(message: unknown, targetOrigin: string): void;
  };
  dispatch(event: unknown): void;
  postMessages: unknown[];
  listenerCount(): number;
} {
  const listeners = new Set<WindowMessageListener>();
  const postMessages: unknown[] = [];
  const window = {
    addEventListener(type: "message", listener: WindowMessageListener): void {
      expect(type).toBe("message");
      listeners.add(listener);
    },
    removeEventListener(type: "message", listener: WindowMessageListener): void {
      expect(type).toBe("message");
      listeners.delete(listener);
    },
    postMessage(message: unknown, targetOrigin: string): void {
      postMessages.push({ message, targetOrigin });
    }
  };
  return {
    window,
    dispatch(event: unknown): void {
      for (const listener of listeners) {
        listener(event);
      }
    },
    postMessages,
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

describe("browser extension content-script browser entrypoint", () => {
  it("wires browser-like dependencies into page injection, runtime messaging, and response posting", async () => {
    const injectedDocument = createInjectedDocument();
    const pageWindow = createInjectedPageWindow();
    const resolvedPaths: string[] = [];
    const runtimeRequests: BrowserExtensionRequest[] = [];

    const handle = installBrowserExtensionContentScriptBrowserEntrypoint({
      document: injectedDocument.document,
      pageWindow: pageWindow.window,
      location: { origin: "https://example.com" },
      runtime: {
        getURL(path: string): string {
          resolvedPaths.push(path);
          return `chrome-extension://extension-id/${path}`;
        },
        sendMessage(message: unknown): BrowserExtensionResponse {
          runtimeRequests.push(message as BrowserExtensionRequest);
          return getPublicKeyResponse((message as BrowserExtensionRequest).request_id);
        }
      }
    });

    expect(resolvedPaths).toEqual([BROWSER_EXTENSION_PAGE_SCRIPT_FILE]);
    expect(injectedDocument.appended).toHaveLength(1);
    expect(handle.pageScript.element).toEqual(expect.objectContaining({
      id: BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
      type: "module",
      async: false,
      src: `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`
    }));
    expect(pageWindow.listenerCount()).toBe(1);

    pageWindow.dispatch({
      source: pageWindow.window,
      origin: "https://example.com",
      data: pageBridgeRequest("content-browser-get-public-key")
    });
    await flushAsyncListeners();

    expect(runtimeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "content-browser-get-public-key",
      method: "get_public_key"
    }]);
    expect(pageWindow.postMessages).toEqual([{
      message: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "extension_to_page",
        request_id: "content-browser-get-public-key",
        response: getPublicKeyResponse("content-browser-get-public-key")
      },
      targetOrigin: "https://example.com"
    }]);

    handle.dispose();
    expect(pageWindow.listenerCount()).toBe(0);
    expect(injectedDocument.removed).toEqual([handle.pageScript.element]);
  });

  it("rejects invalid browser-like dependencies before page injection", () => {
    const injectedDocument = createInjectedDocument();
    const pageWindow = createInjectedPageWindow();
    const runtime = {
      getURL: (path: string) => `chrome-extension://extension-id/${path}`,
      sendMessage: () => getPublicKeyResponse("unused")
    };

    expect(() => installBrowserExtensionContentScriptBrowserEntrypoint({
      document: injectedDocument.document,
      pageWindow: pageWindow.window,
      location: { origin: "https://example.com/path" },
      runtime
    })).toThrow(/page origin/u);
    expect(injectedDocument.appended).toEqual([]);
    expect(pageWindow.listenerCount()).toBe(0);

    expect(() => installBrowserExtensionContentScriptBrowserEntrypoint({
      document: injectedDocument.document,
      pageWindow: { postMessage: () => undefined } as never,
      location: { origin: "https://example.com" },
      runtime
    })).toThrow(/page window/u);
    expect(injectedDocument.appended).toEqual([]);
    expect(pageWindow.listenerCount()).toBe(0);
  });
});
