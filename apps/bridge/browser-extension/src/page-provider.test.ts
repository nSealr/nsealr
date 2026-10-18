import { describe, expect, it } from "vitest";
import { type EventTemplate } from "@nsealr/core";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  handleBrowserExtensionRequest,
  type BrowserExtensionHandlerOptions
} from "./handler.js";
import {
  createBrowserExtensionPageProvider,
  installBrowserExtensionPageProvider,
  type BrowserExtensionBackgroundRequester
} from "./page-provider.js";

const eventTemplate = {
  kind: 1,
  created_at: 1_710_000_000,
  tags: [],
  content: "nSealr fixture: basic kind 1 event."
};

const signedEvent = {
  id: "2977f107ad2668dbd9f09b8594eff3b5276e21bfe098e60ae3e905e3c861e4d3",
  pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
  created_at: 1_710_000_000,
  kind: 1,
  tags: [],
  content: "nSealr fixture: basic kind 1 event.",
  sig: "2eec0351eb1d651140922d4b1f1bd8135f4474aabf42ec5bda7011087c1a072d71be863646dc162e4d96eacf14afeed2618a4acb0e1134a273a2b8e73039e654"
};

const provider: BrowserExtensionHandlerOptions["provider"] = {
  getPublicKey: async () => signedEvent.pubkey,
  signEvent: async () => signedEvent
};

describe("browser extension page provider boundary", () => {
  it("turns NIP-07 getPublicKey into a validated background request", async () => {
    const requests: unknown[] = [];
    const pageProvider = createBrowserExtensionPageProvider({
      nextRequestId: () => "page-get-public-key",
      requestBackground: (request) => {
        requests.push(request);
        return handleBrowserExtensionRequest(request, { provider });
      }
    });

    await expect(pageProvider.getPublicKey()).resolves.toBe(signedEvent.pubkey);
    expect(requests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-get-public-key",
      method: "get_public_key"
    }]);
  });

  it("turns NIP-07 signEvent into a verified signed event", async () => {
    const requests: unknown[] = [];
    const pageProvider = createBrowserExtensionPageProvider({
      nextRequestId: () => "page-sign-event",
      requestBackground: (request) => {
        requests.push(request);
        return handleBrowserExtensionRequest(request, { provider });
      }
    });

    await expect(pageProvider.signEvent(eventTemplate)).resolves.toEqual(signedEvent);
    expect(requests).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "page-sign-event",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }]);
  });

  it("rejects unsafe event templates before contacting the background boundary", async () => {
    let called = false;
    const pageProvider = createBrowserExtensionPageProvider({
      requestBackground: () => {
        called = true;
        return {};
      }
    });

    await expect(pageProvider.signEvent({
      ...eventTemplate,
      pubkey: signedEvent.pubkey
    } as unknown as EventTemplate)).rejects.toThrow(/forbidden fields/u);
    expect(called).toBe(false);
  });

  it("rejects malformed or failed background responses deterministically", async () => {
    const failedProvider = createBrowserExtensionPageProvider({
      nextRequestId: () => "page-background-failed",
      requestBackground: (request) => ({
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: request.request_id,
        ok: false,
        error: {
          code: "provider_request_failed",
          message: "background provider failed",
          retryable: false
        }
      })
    });

    await expect(failedProvider.getPublicKey()).rejects.toThrow(/background provider failed/u);

    const malformedProvider = createBrowserExtensionPageProvider({
      nextRequestId: () => "page-background-malformed",
      requestBackground: () => ({
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "other-request",
        ok: true,
        result: {
          pubkey: signedEvent.pubkey
        }
      })
    });

    await expect(malformedProvider.getPublicKey()).rejects.toThrow(/request_id/u);
  });

  it("passes cancellation to the background requester without touching browser storage", async () => {
    const abortController = new AbortController();
    const seenSignals: AbortSignal[] = [];
    const requestBackground: BrowserExtensionBackgroundRequester = (_request, options) => {
      if (options.abortSignal !== undefined) seenSignals.push(options.abortSignal);
      return {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "page-cancel-signal",
        ok: true,
        result: {
          pubkey: signedEvent.pubkey
        }
      };
    };
    const pageProvider = createBrowserExtensionPageProvider({
      abortSignal: abortController.signal,
      nextRequestId: () => "page-cancel-signal",
      requestBackground
    });

    await expect(pageProvider.getPublicKey()).resolves.toBe(signedEvent.pubkey);
    expect(seenSignals).toEqual([abortController.signal]);

    abortController.abort();
    await expect(pageProvider.getPublicKey()).rejects.toThrow(/cancelled/u);
    expect(seenSignals).toEqual([abortController.signal]);
  });

  it("installs the page provider on an explicit target without overwriting by default", async () => {
    const pageProvider = createBrowserExtensionPageProvider({
      nextRequestId: () => "page-install-provider",
      requestBackground: (request) => handleBrowserExtensionRequest(request, { provider })
    });
    const target: { nostr?: unknown } = {};

    expect(installBrowserExtensionPageProvider(target, pageProvider)).toBe(pageProvider);
    expect(Object.keys(target)).toEqual(["nostr"]);
    expect(target.nostr).toBe(pageProvider);
    expect(() => {
      target.nostr = {};
    }).toThrow();
    await expect((target.nostr as typeof pageProvider).getPublicKey()).resolves.toBe(signedEvent.pubkey);

    expect(() => installBrowserExtensionPageProvider(target, pageProvider)).toThrow(/already has/u);
  });
});
