import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL
} from "./handler.js";
import { createBrowserExtensionBackgroundController } from "./background.js";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import { type BrowserNativeMessageSender } from "@nsealr/browser-provider";
import { approveBrowserExtensionOriginPermissionReview } from "./pairing.js";
import { createBrowserExtensionOriginPermissionStore } from "./origin-permission-store.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  readBrowserExtensionOriginPermissionStoreFromStorage,
  type BrowserExtensionOriginPermissionStorageArea
} from "./origin-permission-storage.js";

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
const localPairingDigest = "f".repeat(64);

class FakeOriginPermissionStorage implements BrowserExtensionOriginPermissionStorageArea {
  readonly setCalls: unknown[] = [];
  private stored: Record<string, unknown> = {};

  get(key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY): unknown {
    if (!(key in this.stored)) return {};
    return {
      [key]: this.stored[key]
    };
  }

  set(items: {
    [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: unknown;
  }): void {
    this.setCalls.push(items);
    this.stored[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY] =
      items[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY];
  }
}

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
    if (message.operation === "request_pairing") return handleLocalServiceRequest(message);
    if (message.operation === "select_account_route") return routeSelectionResponse(message);
    throw new Error(`unexpected operation ${message.operation}`);
  };
}

function routeOnlyOriginPermissionStore(): unknown {
  return createBrowserExtensionOriginPermissionStore([
    approveBrowserExtensionOriginPermissionReview({
      format: "nsealr-browser-origin-permission-review-v0",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      extension_id: "extension@nsealr.dev",
      requested_methods: [
        {
          method: "get_public_key",
          label: "Read public key",
          effect: "The page can read the selected account public key through the browser provider."
        }
      ],
      local_pairing_digest: localPairingDigest,
      requires_user_approval: true,
      stores_production_secrets: false,
      creates_grants: false,
      injects_provider: false
    }, {
      reviewedLocalPairingDigest: localPairingDigest,
      approvedAt: 1_900_000_040
    })
  ], {
    updatedAt: 1_900_000_041
  });
}

describe("browser extension background controller boundary", () => {
  it("composes request handling and pairing intent over the same native-messaging boundary", async () => {
    const requests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(requests),
      routeRequest,
      nextServiceRequestId: (() => {
        let next = 0;
        return () => {
          next += 1;
          return `background-service-${next}`;
        };
      })()
    });

    await expect(controller.requestPairing(sender)).resolves.toMatchObject({
      context: {
        client: {
          surface: "browser_extension",
          origin: "https://example.com",
          instance_id: "extension@nsealr.dev"
        }
      },
      response: {
        request_id: "background-service-1",
        ok: true,
        result: {
          pairing_intent: {
            requires_user_approval: true,
            stores_production_secrets: false
          }
        }
      }
    });

    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-get-public-key",
      method: "get_public_key"
    }, sender)).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    });

    expect(requests.map((request) => request.operation)).toEqual([
      "request_pairing",
      "select_account_route"
    ]);
    expect(requests.map((request) => request.request_id)).toEqual([
      "background-service-1",
      "background-service-2"
    ]);
    expect(requests[0]).toMatchObject({
      operation: "request_pairing",
      params: {
        client: {
          surface: "browser_extension",
          origin: "https://example.com",
          app_name: "nSealr Browser Extension",
          instance_id: "extension@nsealr.dev"
        },
        requested_operations: [
          "select_account_route",
          "dispatch_signer_request"
        ]
      }
    });
    expect(requests[1]).toMatchObject({
      operation: "select_account_route",
      params: {
        route_request: routeRequest
      }
    });
  });

  it("rejects malformed browser requests before native messaging", async () => {
    let called = false;
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "bad request id",
      method: "get_public_key"
    }, sender)).resolves.toMatchObject({
      request_id: "invalid-browser-extension-request",
      ok: false,
      error: {
        code: "invalid_request"
      }
    });
    expect(called).toBe(false);
  });

  it("rejects origin-permission-denied requests before native messaging", async () => {
    const requests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: nativeResponder(requests),
      originPermissions: {
        store: routeOnlyOriginPermissionStore(),
        localPairingDigest
      }
    });

    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-origin-permission-denied",
      method: "sign_event",
      params: {
        event_template: {
          kind: 1,
          created_at: 1_710_000_000,
          tags: [],
          content: "denied before native messaging"
        }
      }
    }, sender)).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-origin-permission-denied",
      ok: false,
      error: {
        code: "origin_permission_denied",
        message: "browser extension origin permission denied",
        retryable: false
      }
    });
    expect(requests).toEqual([]);
  });

  it("can load origin permissions before browser native messaging", async () => {
    const requests: LocalServiceRequest[] = [];
    let loadCount = 0;
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: nativeResponder(requests),
      originPermissions: {
        loadStore() {
          loadCount += 1;
          return routeOnlyOriginPermissionStore();
        },
        localPairingDigest
      }
    });

    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-origin-permission-loader-denied",
      method: "sign_event",
      params: {
        event_template: {
          kind: 1,
          created_at: 1_710_000_000,
          tags: [],
          content: "storage-backed denied before native messaging"
        }
      }
    }, sender)).resolves.toMatchObject({
      request_id: "background-origin-permission-loader-denied",
      ok: false,
      error: {
        code: "origin_permission_denied"
      }
    });
    expect(loadCount).toBe(1);
    expect(requests).toEqual([]);
  });

  it("projects pairing review metadata without browser storage or grants", async () => {
    const requests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(requests),
      routeRequest,
      nextServiceRequestId: () => "background-pairing-review"
    });

    await expect(controller.requestPairingReview(sender)).resolves.toMatchObject({
      response: {
        request_id: "background-pairing-review",
        ok: true
      },
      review: {
        format: "nsealr-local-pairing-review-v0",
        client: {
          surface: "browser_extension",
          origin: "https://example.com",
          instance_id: "extension@nsealr.dev"
        },
        requested_operations: [
          {
            operation: "select_account_route"
          },
          {
            operation: "dispatch_signer_request"
          }
        ],
        requires_user_approval: true,
        stores_production_secrets: false,
        contains_secret_material: false
      }
    });
    expect(requests.map((request) => request.operation)).toEqual(["request_pairing"]);
  });

  it("projects origin permission review metadata without injecting providers", async () => {
    const requests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(requests),
      routeRequest,
      nextServiceRequestId: () => "background-origin-permission-review"
    });

    await expect(controller.requestOriginPermissionReview(sender)).resolves.toMatchObject({
      response: {
        request_id: "background-origin-permission-review",
        ok: true
      },
      originReview: {
        format: "nsealr-browser-origin-permission-review-v0",
        origin: "https://example.com",
        extension_id: "extension@nsealr.dev",
        requested_methods: [
          {
            method: "get_public_key"
          },
          {
            method: "sign_event"
          }
        ],
        requires_user_approval: true,
        stores_production_secrets: false,
        creates_grants: false,
        injects_provider: false
      }
    });
    expect(requests.map((request) => request.operation)).toEqual(["request_pairing"]);
  });

  it("approves origin permission reviews into injected storage without native messaging", async () => {
    const requests: LocalServiceRequest[] = [];
    const storage = new FakeOriginPermissionStorage();
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(requests),
      routeRequest,
      originPermissionStorage: storage,
      originPermissionApprovalNow: () => 1_900_000_090,
      originPermissionStorageEmptyUpdatedAt: 1_900_000_080
    });
    const review = {
      format: "nsealr-browser-origin-permission-review-v0",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      extension_id: "extension@nsealr.dev",
      requested_methods: [
        {
          method: "get_public_key",
          label: "Read public key",
          effect: "The page can read the selected account public key through the browser provider."
        }
      ],
      local_pairing_digest: localPairingDigest,
      requires_user_approval: true,
      stores_production_secrets: false,
      creates_grants: false,
      injects_provider: false
    } as const;

    await expect(controller.approveOriginPermission(
      review,
      localPairingDigest
    )).resolves.toMatchObject({
      approval: {
        origin: "https://example.com",
        approved_methods: ["get_public_key"],
        approved_at: 1_900_000_090,
        creates_grants: false,
        stores_production_secrets: false,
        contains_secret_material: false
      },
      storageWrite: {
        updated_at: 1_900_000_090,
        approval_count: 1,
        writes_extension_storage: true,
        dispatches_signers: false
      }
    });
    expect(requests).toEqual([]);
    expect(storage.setCalls).toHaveLength(1);
    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(storage)).resolves.toMatchObject({
      approvals: [
        {
          origin: "https://example.com",
          local_pairing_digest: localPairingDigest
        }
      ],
      writes_extension_storage: false,
      stores_production_secrets: false
    });
  });

  it("keeps silent native messaging deterministic without approving grants", async () => {
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      nativeMessageTimeoutMs: 1,
      sendNativeMessage: () => new Promise(() => undefined)
    });

    await expect(controller.requestPairingReview(sender)).rejects.toThrow(/response timed out/u);
    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-timeout-get-public-key",
      method: "get_public_key"
    }, sender)).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-timeout-get-public-key",
      ok: false,
      error: {
        code: "provider_request_failed",
        message: "browser provider get_public_key failed",
        retryable: false
      }
    });
  });

  it("honors request-scoped cancellation without approving grants or contacting native messaging", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(controller.requestPairingReview(sender, {
      nativeMessageAbortSignal: abortController.signal
    })).rejects.toThrow(/cancelled/u);
    await expect(controller.handleRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-cancelled-get-public-key",
      method: "get_public_key"
    }, sender, {
      nativeMessageAbortSignal: abortController.signal
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-cancelled-get-public-key",
      ok: false,
      error: {
        code: "provider_request_failed",
        message: "browser provider get_public_key failed",
        retryable: false
      }
    });
    expect(called).toBe(false);
  });
});
