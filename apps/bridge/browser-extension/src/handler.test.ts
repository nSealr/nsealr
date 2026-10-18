import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  handleBrowserExtensionRequest,
  handleBrowserExtensionSenderRequest,
  type BrowserExtensionHandlerOptions
} from "./handler.js";
import {
  approveBrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  createBrowserExtensionOriginPermissionStore
} from "./origin-permission-store.js";

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
const sender = {
  extension_id: "extension@nsealr.dev",
  page_url: "https://example.com/app"
};
const localPairingDigest = "d".repeat(64);

function originPermissionStore(methods: Array<"get_public_key" | "sign_event"> = ["get_public_key", "sign_event"]): unknown {
  const requestedMethods = methods.map((method) => {
    if (method === "get_public_key") {
      return {
        method,
        label: "Read public key",
        effect: "The page can read the selected account public key through the browser provider."
      };
    }
    return {
      method,
      label: "Request event signatures",
      effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
    };
  });
  return createBrowserExtensionOriginPermissionStore([
    approveBrowserExtensionOriginPermissionReview({
      format: "nsealr-browser-origin-permission-review-v0",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      extension_id: "extension@nsealr.dev",
      requested_methods: requestedMethods,
      local_pairing_digest: localPairingDigest,
      requires_user_approval: true,
      stores_production_secrets: false,
      creates_grants: false,
      injects_provider: false
    }, {
      reviewedLocalPairingDigest: localPairingDigest,
      approvedAt: 1_900_000_020
    })
  ], {
    updatedAt: 1_900_000_021
  });
}

describe("browser extension request handler", () => {
  it("returns validated get_public_key responses from the injected provider", async () => {
    await expect(handleBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-get-pubkey-handler",
      method: "get_public_key"
    }, { provider })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-get-pubkey-handler",
      ok: true,
      result: {
        pubkey: signedEvent.pubkey
      }
    });
  });

  it("returns verified sign_event responses from the injected provider", async () => {
    await expect(handleBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sign-handler",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }, { provider })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sign-handler",
      ok: true,
      result: {
        event: signedEvent
      }
    });
  });

  it("rejects malformed requests before contacting the provider", async () => {
    let called = false;
    const response = await handleBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "bad request id",
      method: "get_public_key"
    }, {
      provider: {
        getPublicKey: async () => {
          called = true;
          return signedEvent.pubkey;
        },
        signEvent: async () => {
          called = true;
          return signedEvent;
        }
      }
    });

    expect(called).toBe(false);
    expect(response).toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "invalid-browser-extension-request",
      ok: false,
      error: {
        code: "invalid_request",
        message: "browser extension request is invalid",
        retryable: false
      }
    });
  });

  it("rejects malformed provider outputs without returning them to browser callers", async () => {
    await expect(handleBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-bad-pubkey",
      method: "get_public_key"
    }, {
      provider: {
        getPublicKey: async () => "not-a-pubkey",
        signEvent: async () => signedEvent
      }
    })).resolves.toMatchObject({
      request_id: "browser-bad-pubkey",
      ok: false,
      error: { code: "provider_request_failed" }
    });

    await expect(handleBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-bad-event",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }, {
      provider: {
        getPublicKey: async () => signedEvent.pubkey,
        signEvent: async () => ({
          ...signedEvent,
          content: "tampered"
        })
      }
    })).resolves.toMatchObject({
      request_id: "browser-bad-event",
      ok: false,
      error: { code: "provider_request_failed" }
    });
  });

  it("binds browser requests to validated sender-derived client identity before provider selection", async () => {
    const seenOrigins: string[] = [];
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sender-get-pubkey",
      method: "get_public_key"
    }, sender, {
      providerForClient: (context) => {
        seenOrigins.push(context.client.origin);
        return provider;
      }
    })).resolves.toMatchObject({
      request_id: "browser-sender-get-pubkey",
      ok: true,
      result: {
        pubkey: signedEvent.pubkey
      }
    });

    expect(seenOrigins).toEqual(["https://example.com"]);
  });

  it("enforces configured origin permissions before provider selection", async () => {
    let selected = false;
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-get-public-key",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        store: originPermissionStore(["get_public_key"]),
        localPairingDigest
      }
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-get-public-key",
      ok: true
    });
    expect(selected).toBe(true);

    selected = false;
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-sign-event-denied",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        store: originPermissionStore(["get_public_key"]),
        localPairingDigest
      }
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-sign-event-denied",
      ok: false,
      error: {
        code: "origin_permission_denied",
        message: "browser extension origin permission denied",
        retryable: false
      }
    });
    expect(selected).toBe(false);
  });

  it("loads origin permissions asynchronously before provider selection", async () => {
    let selected = false;
    let loadCount = 0;
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-loaded",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        async loadStore() {
          loadCount += 1;
          return originPermissionStore(["get_public_key"]);
        },
        localPairingDigest
      }
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-loaded",
      ok: true
    });
    expect(loadCount).toBe(1);
    expect(selected).toBe(true);

    selected = false;
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-loader-failed",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        async loadStore() {
          throw new Error("storage unavailable");
        },
        localPairingDigest
      }
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-loader-failed",
      ok: false,
      error: {
        code: "origin_permission_denied"
      }
    });
    expect(selected).toBe(false);

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-loader-ambiguous",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        store: originPermissionStore(),
        loadStore: () => originPermissionStore(),
        localPairingDigest
      } as never
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-loader-ambiguous",
      ok: false,
      error: {
        code: "origin_permission_denied"
      }
    });
    expect(selected).toBe(false);
  });

  it("rejects stale or malformed origin permission stores before provider selection", async () => {
    let selected = false;
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-stale-digest",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        store: originPermissionStore(),
        localPairingDigest: "e".repeat(64)
      }
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-stale-digest",
      ok: false,
      error: {
        code: "origin_permission_denied"
      }
    });
    expect(selected).toBe(false);

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-origin-permission-malformed-store",
      method: "get_public_key"
    }, sender, {
      providerForClient: () => {
        selected = true;
        return provider;
      },
      originPermissions: {
        store: { format: "wrong" },
        localPairingDigest
      }
    })).resolves.toMatchObject({
      request_id: "browser-origin-permission-malformed-store",
      ok: false,
      error: {
        code: "origin_permission_denied"
      }
    });
    expect(selected).toBe(false);
  });

  it("rejects invalid request or sender before provider selection", async () => {
    let selected = false;
    const options = {
      providerForClient: () => {
        selected = true;
        return provider;
      }
    };

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "bad request id",
      method: "get_public_key"
    }, {
      extension_id: "extension@nsealr.dev",
      page_url: "https://example.com/app"
    }, options)).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "invalid-browser-extension-request",
      ok: false,
      error: {
        code: "invalid_request",
        message: "browser extension request is invalid",
        retryable: false
      }
    });
    expect(selected).toBe(false);

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-bad-sender",
      method: "get_public_key"
    }, {
      extension_id: "extension@nsealr.dev",
      page_url: "http://localhost.evil.example/app"
    }, options)).resolves.toMatchObject({
      request_id: "browser-bad-sender",
      ok: false,
      error: {
        code: "invalid_sender",
        message: "browser extension sender is invalid"
      }
    });
    expect(selected).toBe(false);
  });

  it("returns deterministic errors when provider selection fails", async () => {
    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-provider-selection-failed",
      method: "get_public_key"
    }, {
      extension_id: "extension@nsealr.dev",
      page_url: "https://example.com/app"
    }, {
      providerForClient: () => {
        throw new Error("route store unavailable");
      }
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-provider-selection-failed",
      ok: false,
      error: {
        code: "provider_selection_failed",
        message: "browser extension provider selection failed",
        retryable: false
      }
    });
  });
});
