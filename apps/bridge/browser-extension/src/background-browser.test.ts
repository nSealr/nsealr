import { describe, expect, it } from "vitest";
import { NATIVE_HOST_NAME } from "@nsealr/browser-provider";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import {
  createBrowserExtensionBackgroundBrowserNativeMessageSender,
  installBrowserExtensionBackgroundBrowserEntrypoint
} from "./background-browser.js";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import { BROWSER_EXTENSION_CONTROL_PROTOCOL } from "./pending-control.js";
import { BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT } from "./route-config.js";
import {
  type BrowserExtensionRuntimeMessageListener,
  type BrowserExtensionRuntimeMessageResponder
} from "./runtime-message.js";
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
const localPairingDigest = "c".repeat(64);

class FakeOriginPermissionStorage implements BrowserExtensionOriginPermissionStorageArea {
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
    this.stored[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY] =
      items[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY];
  }
}

function getPublicKeyRequest(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "get_public_key"
  };
}

function signEventRequest(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "sign_event",
    params: {
      event_template: {
        kind: 1,
        created_at: 1_710_000_000,
        tags: [],
        content: "browser entrypoint origin permission denial"
      }
    }
  };
}

function listPendingRequests(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "list_pending_requests"
  };
}

function requestOriginPermissionReview(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "request_origin_permission_review",
    params: {
      sender: {
        extension_id: "extension@nsealr.dev",
        page_url: "https://example.com/app"
      }
    }
  };
}

function approveOriginPermission(requestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "approve_origin_permission",
    params: {
      origin_review: {
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
      },
      reviewed_local_pairing_digest: localPairingDigest
    }
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
      approvedAt: 1_900_000_050
    })
  ], {
    updatedAt: 1_900_000_051
  });
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

function createInjectedRuntime(): {
  runtime: {
    onMessage: {
      addListener(listener: BrowserExtensionRuntimeMessageListener): void;
      removeListener(listener: BrowserExtensionRuntimeMessageListener): void;
    };
    sendNativeMessage(hostName: string, message: unknown): unknown;
  };
  nativeMessages: Array<{ hostName: string; message: unknown }>;
  emit(value: unknown, sender: unknown, sendResponse: BrowserExtensionRuntimeMessageResponder): true | undefined;
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionRuntimeMessageListener>();
  const nativeMessages: Array<{ hostName: string; message: unknown }> = [];
  return {
    runtime: {
      onMessage: {
        addListener(listener: BrowserExtensionRuntimeMessageListener): void {
          listeners.add(listener);
        },
        removeListener(listener: BrowserExtensionRuntimeMessageListener): void {
          listeners.delete(listener);
        }
      },
      sendNativeMessage(hostName: string, message: unknown): unknown {
        nativeMessages.push({ hostName, message });
        if ((message as LocalServiceRequest).operation === "request_pairing") {
          return handleLocalServiceRequest(message as LocalServiceRequest);
        }
        return routeSelectionResponse(message as LocalServiceRequest);
      }
    },
    nativeMessages,
    emit(value: unknown, sender: unknown, sendResponse: BrowserExtensionRuntimeMessageResponder): true | undefined {
      const [listener] = listeners;
      return listener?.(value, sender, sendResponse);
    },
    listenerCount(): number {
      return listeners.size;
    }
  };
}

async function flushAsyncListeners(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("browser extension background browser entrypoint", () => {
  it("installs runtime message handling over explicit browser-like runtime dependencies", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      extensionId: "extension@nsealr.dev",
      nextServiceRequestId: () => "background-browser-route"
    });
    expect(handle.pendingRequests.active()).toEqual([]);
    expect(runtime.listenerCount()).toBe(1);

    expect(runtime.emit(
      getPublicKeyRequest("background-browser-get-public-key"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    expect(handle.pendingRequests.active()).toMatchObject([{
      request_id: "background-browser-get-public-key",
      route_account_id: routeRequest.account_id,
      route_type: routeRequest.route_type,
      includes_event_template: false
    }]);
    await flushAsyncListeners();

    expect(responses).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-browser-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    }]);
    expect(runtime.nativeMessages).toHaveLength(1);
    expect(handle.pendingRequests.active()).toEqual([]);
    expect(runtime.nativeMessages[0]).toMatchObject({
      hostName: NATIVE_HOST_NAME,
      message: {
        request_id: "background-browser-route",
        operation: "select_account_route",
        params: {
          client: {
            surface: "browser_extension",
            origin: "https://example.com",
            instance_id: "extension@nsealr.dev"
          },
          route_request: routeRequest
        }
      }
    });

    handle.dispose();
    expect(runtime.listenerCount()).toBe(0);
  });

  it("owns an in-memory pending lifecycle for extension-internal control queries", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      extensionId: "extension@nsealr.dev"
    });

    expect(runtime.emit(
      listPendingRequests("background-browser-list-empty"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "background-browser-list-empty",
      ok: true,
      result: {
        pending_requests: [],
        stores_production_secrets: false,
        contains_secret_material: false
      }
    }]);
    expect(runtime.nativeMessages).toEqual([]);
    handle.dispose();
  });

  it("routes extension-internal origin permission review control to native pairing", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      extensionId: "extension@nsealr.dev",
      nextServiceRequestId: () => "background-browser-origin-review-service"
    });

    expect(runtime.emit(
      requestOriginPermissionReview("background-browser-origin-review"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toMatchObject([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "background-browser-origin-review",
      ok: true,
      result: {
        origin_review: {
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
          stores_production_secrets: false,
          creates_grants: false,
          injects_provider: false
        },
        stores_production_secrets: false,
        contains_secret_material: false,
        creates_grants: false,
        injects_provider: false
      }
    }]);
    expect(runtime.nativeMessages.map((message) => (message.message as LocalServiceRequest).operation)).toEqual([
      "request_pairing"
    ]);
    handle.dispose();
  });

  it("routes extension-internal origin permission approval control to injected storage", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const storage = new FakeOriginPermissionStorage();
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      extensionId: "extension@nsealr.dev",
      originPermissionStorage: storage,
      originPermissionApprovalNow: () => 1_900_000_070
    });

    expect(runtime.emit(
      approveOriginPermission("background-browser-origin-approve"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toMatchObject([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "background-browser-origin-approve",
      ok: true,
      result: {
        approval: {
          origin: "https://example.com",
          local_pairing_digest: localPairingDigest,
          approved_at: 1_900_000_070,
          creates_grants: false,
          stores_production_secrets: false,
          contains_secret_material: false
        },
        storage_write: {
          writes_extension_storage: true,
          dispatches_signers: false
        }
      }
    }]);
    expect(runtime.nativeMessages).toEqual([]);
    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(storage)).resolves.toMatchObject({
      approvals: [
        {
          origin: "https://example.com",
          local_pairing_digest: localPairingDigest
        }
      ]
    });
    handle.dispose();
  });

  it("enforces injected origin permissions before browser native messaging", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      extensionId: "extension@nsealr.dev",
      originPermissions: {
        store: routeOnlyOriginPermissionStore(),
        localPairingDigest
      }
    });

    expect(runtime.emit(
      signEventRequest("background-browser-origin-permission-denied"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toEqual([{
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "background-browser-origin-permission-denied",
      ok: false,
      error: {
        code: "origin_permission_denied",
        message: "browser extension origin permission denied",
        retryable: false
      }
    }]);
    expect(runtime.nativeMessages).toEqual([]);
    handle.dispose();
  });

  it("rejects invalid browser-like runtime dependencies before listener installation", () => {
    expect(() => installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: {
        onMessage: {},
        sendNativeMessage: () => ({})
      } as never,
      routeRequest
    })).toThrow(/runtime/u);
  });

  it("can derive selected route metadata from a secretless browser route config", async () => {
    const runtime = createInjectedRuntime();
    const responses: unknown[] = [];
    const handle = installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeConfig: {
        format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
        account_id: routeRequest.account_id,
        route_type: routeRequest.route_type
      },
      extensionId: "extension@nsealr.dev",
      nextServiceRequestId: () => "background-browser-config-route"
    });

    expect(runtime.emit(
      getPublicKeyRequest("background-browser-config-get-public-key"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toHaveLength(1);
    expect(runtime.nativeMessages).toEqual([{
      hostName: NATIVE_HOST_NAME,
      message: expect.objectContaining({
        request_id: "background-browser-config-route",
        operation: "select_account_route",
        params: expect.objectContaining({
          route_request: routeRequest
        })
      })
    }]);
    handle.dispose();
  });

  it("rejects ambiguous route configuration before listener installation", () => {
    const runtime = createInjectedRuntime();
    expect(() => installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime,
      routeRequest,
      routeConfig: {
        format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
        account_id: routeRequest.account_id
      }
    })).toThrow(/route configuration/u);
    expect(() => installBrowserExtensionBackgroundBrowserEntrypoint({
      runtime: runtime.runtime
    })).toThrow(/route configuration/u);
    expect(runtime.listenerCount()).toBe(0);
  });

  it("does not call browser native messaging after request cancellation", async () => {
    const runtime = createInjectedRuntime();
    const abortController = new AbortController();
    abortController.abort();
    const sender = createBrowserExtensionBackgroundBrowserNativeMessageSender(runtime.runtime);

    await expect(Promise.resolve().then(() => sender(
      NATIVE_HOST_NAME,
      {
        version: 1,
        request_id: "cancelled-native-message",
        operation: "request_pairing",
        params: {
          client: {
            surface: "browser_extension",
            origin: "https://example.com",
            app_name: "nSealr Browser Extension",
            instance_id: "extension@nsealr.dev"
          },
          requested_operations: ["select_account_route"]
        }
      },
      { abortSignal: abortController.signal }
    ))).rejects.toThrow(/cancelled/u);
    expect(runtime.nativeMessages).toEqual([]);
  });
});
