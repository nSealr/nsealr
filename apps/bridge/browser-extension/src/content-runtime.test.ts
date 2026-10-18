import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import {
  createBrowserExtensionContentRuntimeMessageSender,
  createBrowserExtensionContentRuntimeUrlResolver,
  type BrowserExtensionContentRuntimeApi
} from "./content-runtime.js";
import { BROWSER_EXTENSION_PAGE_SCRIPT_FILE } from "./page-injection.js";
import { type BrowserExtensionRequest } from "./messages.js";

function getPublicKeyRequest(requestId: string): BrowserExtensionRequest {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "get_public_key"
  };
}

function createRuntimeApi(): {
  runtime: BrowserExtensionContentRuntimeApi;
  resolvedPaths: string[];
  messages: unknown[];
} {
  const resolvedPaths: string[] = [];
  const messages: unknown[] = [];
  return {
    runtime: {
      getURL(path: string): string {
        resolvedPaths.push(path);
        return `chrome-extension://extension-id/${path}`;
      },
      sendMessage(message: unknown): unknown {
        messages.push(message);
        return {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "runtime-adapter-get-public-key",
          ok: true,
          result: {
            pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"
          }
        };
      }
    },
    resolvedPaths,
    messages
  };
}

describe("browser extension content runtime API adapters", () => {
  it("creates a reviewed extension resource URL resolver over injected runtime.getURL", () => {
    const runtimeApi = createRuntimeApi();
    const resolveUrl = createBrowserExtensionContentRuntimeUrlResolver(runtimeApi.runtime);

    expect(resolveUrl(BROWSER_EXTENSION_PAGE_SCRIPT_FILE)).toBe(
      `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`
    );
    expect(runtimeApi.resolvedPaths).toEqual([BROWSER_EXTENSION_PAGE_SCRIPT_FILE]);
  });

  it("rejects unsafe extension resource paths before runtime.getURL", () => {
    for (const path of ["", "/page-script.js", "../page-script.js", "scripts//page.js", "scripts\\page.js"]) {
      const runtimeApi = createRuntimeApi();
      const resolveUrl = createBrowserExtensionContentRuntimeUrlResolver(runtimeApi.runtime);
      expect(() => resolveUrl(path)).toThrow(/resource path/u);
      expect(runtimeApi.resolvedPaths).toEqual([]);
    }
  });

  it("creates a runtime message sender over injected runtime.sendMessage", async () => {
    const runtimeApi = createRuntimeApi();
    const sendRuntimeMessage = createBrowserExtensionContentRuntimeMessageSender(runtimeApi.runtime);
    const request = getPublicKeyRequest("runtime-adapter-get-public-key");

    await expect(Promise.resolve(sendRuntimeMessage(request, {}))).resolves.toMatchObject({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      request_id: "runtime-adapter-get-public-key",
      ok: true
    });
    expect(runtimeApi.messages).toEqual([request]);
  });

  it("rejects already-cancelled messages before runtime.sendMessage", async () => {
    const runtimeApi = createRuntimeApi();
    const sendRuntimeMessage = createBrowserExtensionContentRuntimeMessageSender(runtimeApi.runtime);
    const abortController = new AbortController();
    abortController.abort();

    expect(() => sendRuntimeMessage(
      getPublicKeyRequest("runtime-adapter-cancelled"),
      { abortSignal: abortController.signal }
    )).toThrow(/cancelled/u);
    expect(runtimeApi.messages).toEqual([]);
  });

  it("rejects incomplete runtime API dependencies", () => {
    expect(() => createBrowserExtensionContentRuntimeUrlResolver(
      null as unknown as BrowserExtensionContentRuntimeApi
    )).toThrow(/getURL/u);
    expect(() => createBrowserExtensionContentRuntimeUrlResolver({
      getURL: "missing",
      sendMessage: () => undefined
    } as unknown as BrowserExtensionContentRuntimeApi)).toThrow(/getURL/u);
    expect(() => createBrowserExtensionContentRuntimeMessageSender({
      getURL: () => `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`,
      sendMessage: "missing"
    } as unknown as BrowserExtensionContentRuntimeApi)).toThrow(/sendMessage/u);
  });
});
