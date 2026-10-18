import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  handleBrowserExtensionRequest,
  type BrowserExtensionHandlerOptions
} from "./handler.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  createBrowserExtensionPageBridgeBackgroundRequester,
  handleBrowserExtensionPageBridgeRequest,
  parseBrowserExtensionPageBridgeRequest,
  parseBrowserExtensionPageBridgeResponse
} from "./page-bridge.js";

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

describe("browser extension page bridge boundary", () => {
  it("parses a page-to-extension bridge request around a validated browser request", () => {
    expect(parseBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "bridge-get-public-key",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-get-public-key",
        method: "get_public_key"
      }
    })).toMatchObject({
      request_id: "bridge-get-public-key",
      request: {
        method: "get_public_key"
      }
    });
  });

  it("bridges valid page requests to an injected background requester", async () => {
    const requests: unknown[] = [];
    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "bridge-sign-event",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-sign-event",
        method: "sign_event",
        params: {
          event_template: eventTemplate
        }
      }
    }, {
      requestBackground: (request) => {
        requests.push(request);
        return handleBrowserExtensionRequest(request, { provider });
      }
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-sign-event",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-sign-event",
        ok: true,
        result: {
          event: signedEvent
        }
      }
    });
    expect(requests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "bridge-sign-event",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }]);
  });

  it("creates a page-side background requester over an injected bridge exchange", async () => {
    const bridgeRequests: unknown[] = [];
    const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
      exchangeBridgeMessage: async (bridgeRequest, options) => {
        bridgeRequests.push({
          bridgeRequest,
          abortSignalForwarded: options.abortSignal !== undefined
        });
        const bridgeResponse = await handleBrowserExtensionPageBridgeRequest(bridgeRequest, {
          requestBackground: (request) => handleBrowserExtensionRequest(request, { provider }),
          ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
        });
        return bridgeResponse;
      }
    });

    await expect(requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-get-public-key",
      method: "get_public_key"
    }, { abortSignal: new AbortController().signal })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    });
    expect(bridgeRequests).toEqual([{
      bridgeRequest: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "page_to_extension",
        request_id: "page-requester-get-public-key",
        request: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "page-requester-get-public-key",
          method: "get_public_key"
        }
      },
      abortSignalForwarded: true
    }]);
  });

  it("parses bridge responses around validated browser responses", () => {
    expect(parseBrowserExtensionPageBridgeResponse({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-response-parse",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-response-parse",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    }, "bridge-response-parse")).toEqual({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-response-parse",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-response-parse",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    });
  });

  it("rejects malformed page bridge requests before contacting the background", async () => {
    let called = false;
    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "wrong-direction",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "wrong-direction",
        method: "get_public_key"
      }
    }, {
      requestBackground: () => {
        called = true;
        return {};
      }
    })).rejects.toThrow(/direction/u);
    expect(called).toBe(false);

    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "outer-request-id",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "inner-request-id",
        method: "get_public_key"
      }
    }, {
      requestBackground: () => {
        called = true;
        return {};
      }
    })).rejects.toThrow(/does not match/u);
    expect(called).toBe(false);
  });

  it("rejects malformed page-side requester input and bridge responses", async () => {
    let called = false;
    const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
      exchangeBridgeMessage: () => {
        called = true;
        return {};
      }
    });
    await expect(requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-unsupported",
      method: "nip04_encrypt"
    } as never, {})).rejects.toThrow(/unsupported/u);
    expect(called).toBe(false);

    const badResponseRequester = createBrowserExtensionPageBridgeBackgroundRequester({
      exchangeBridgeMessage: () => ({
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "page_to_extension",
        request_id: "page-requester-bad-response",
        response: {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "page-requester-bad-response",
          ok: true,
          result: {
            pubkey: publicKey
          }
        }
      })
    });
    await expect(badResponseRequester({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-bad-response",
      method: "get_public_key"
    }, {})).rejects.toThrow(/direction/u);

    expect(() => parseBrowserExtensionPageBridgeResponse({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-response-extra-field",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-response-extra-field",
        ok: true,
        result: {
          pubkey: publicKey
        },
        extra: true
      }
    }, "bridge-response-extra-field")).toThrow(/unsupported fields/u);

    expect(() => parseBrowserExtensionPageBridgeResponse({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-response-missing-result",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-response-missing-result",
        ok: true
      }
    }, "bridge-response-missing-result")).toThrow(/result/u);

    expect(() => parseBrowserExtensionPageBridgeResponse({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "bridge-response-bad-error",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-response-bad-error",
        ok: false,
        error: {
          code: "provider_request_failed",
          message: "failed",
          retryable: true
        }
      }
    }, "bridge-response-bad-error")).toThrow(/retryable/u);
  });

  it("rejects mismatched background responses and forwards cancellation", async () => {
    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "bridge-mismatched-response",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-mismatched-response",
        method: "get_public_key"
      }
    }, {
      requestBackground: () => ({
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "other-response",
        ok: true,
        result: {
          pubkey: publicKey
        }
      })
    })).rejects.toThrow(/request_id/u);

    const abortController = new AbortController();
    const signals: AbortSignal[] = [];
    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "bridge-abort-signal",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-abort-signal",
        method: "get_public_key"
      }
    }, {
      abortSignal: abortController.signal,
      requestBackground: (_request, options) => {
        if (options.abortSignal !== undefined) signals.push(options.abortSignal);
        return handleBrowserExtensionRequest(_request, { provider });
      }
    })).resolves.toMatchObject({
      request_id: "bridge-abort-signal"
    });
    expect(signals).toEqual([abortController.signal]);

    abortController.abort();
    await expect(handleBrowserExtensionPageBridgeRequest({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "bridge-already-cancelled",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "bridge-already-cancelled",
        method: "get_public_key"
      }
    }, {
      abortSignal: abortController.signal,
      requestBackground: () => {
        throw new Error("should not contact background");
      }
    })).rejects.toThrow(/cancelled/u);
  });

  it("rejects already-cancelled page-side requester calls before bridge exchange", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
      abortSignal: abortController.signal,
      exchangeBridgeMessage: () => {
        called = true;
        return {};
      }
    });
    await expect(requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-cancelled",
      method: "get_public_key"
    }, {})).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);
  });

  it("rejects in-flight page-side requester calls when cancellation wins", async () => {
    const abortController = new AbortController();
    let seenSignal: AbortSignal | undefined;
    const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
      exchangeBridgeMessage: (_bridgeRequest, options) => {
        seenSignal = options.abortSignal;
        return new Promise(() => undefined);
      }
    });

    const request = requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-requester-in-flight-cancelled",
      method: "get_public_key"
    }, { abortSignal: abortController.signal });
    abortController.abort();

    await expect(request).rejects.toThrow(/cancelled/u);
    expect(seenSignal).toBe(abortController.signal);
  });
});
