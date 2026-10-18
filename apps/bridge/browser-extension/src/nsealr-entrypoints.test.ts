import { NATIVE_HOST_NAME } from "@nsealr/browser-provider";
import { type LocalServiceRequest } from "@nsealr/client";
import { describe, expect, it } from "vitest";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL, type BrowserExtensionResponse } from "./handler.js";
import { type BrowserExtensionRequest } from "./messages.js";
import { BROWSER_EXTENSION_CONTROL_PROTOCOL } from "./pending-control.js";
import { BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT } from "./pending-request.js";
import {
  BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
  type BrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";
import {
  BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
  BROWSER_EXTENSION_PAGE_SCRIPT_FILE,
  type BrowserExtensionInjectedPageScriptElement,
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";
import { BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT } from "./route-config.js";
import {
  type BrowserExtensionRuntimeMessageListener,
  type BrowserExtensionRuntimeMessageResponse
} from "./runtime-message.js";
import { installNsealrBackgroundEntrypoint } from "./nsealr-background-entrypoint.js";
import { installNsealrContentScriptEntrypoint } from "./nsealr-content-script-entrypoint.js";
import { installNsealrPageScriptEntrypoint } from "./nsealr-page-script-entrypoint.js";
import {
  createNsealrPopupEntrypoint,
  installNsealrPopupEntrypoint,
  installNsealrPopupOriginPermissionEntrypoint
} from "./nsealr-popup-entrypoint.js";
import { approveBrowserExtensionOriginPermissionReview } from "./pairing.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
  createBrowserExtensionOriginPermissionStore
} from "./origin-permission-store.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT
} from "./origin-permission-storage.js";
import {
  BROWSER_EXTENSION_POPUP_LIST_ID,
  BROWSER_EXTENSION_POPUP_REFRESH_ID,
  BROWSER_EXTENSION_POPUP_ROOT_ID,
  BROWSER_EXTENSION_POPUP_STATUS_ID
} from "./popup-html.js";
import {
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const routeRequest = {
  account_id: "esp32-usb-slot-0",
  method: "sign_event",
  route_type: "esp32_usb_nip46" as const
};
const localPairingDigest = "d".repeat(64);

type WindowMessageListener = (event: unknown) => void;

class FakePopupElement implements BrowserExtensionPopupElement {
  textContent: string | null = null;
  className = "";
  disabled = false;
  dataset: Record<string, string> = {};
  readonly attributes = new Map<string, string>();
  readonly children: FakePopupElement[] = [];
  readonly listeners = new Map<string, Array<() => void>>();

  appendChild(child: BrowserExtensionPopupElement): unknown {
    this.children.push(child as FakePopupElement);
    return child;
  }

  replaceChildren(...children: BrowserExtensionPopupElement[]): void {
    this.children.splice(0, this.children.length, ...(children as FakePopupElement[]));
  }

  addEventListener(type: "click", listener: () => void): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: "click", listener: () => void): void {
    this.listeners.set(type, (this.listeners.get(type) ?? []).filter((candidate) => candidate !== listener));
  }

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
  }
}

function routeConfig(): unknown {
  return {
    format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
    account_id: routeRequest.account_id,
    route_type: routeRequest.route_type
  };
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
        route_type: routeRequest.route_type,
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

function getPublicKeyRequest(requestId: string): BrowserExtensionRequest {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "get_public_key"
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

function signEventRequest(requestId: string): BrowserExtensionRequest {
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
        content: "packaged background origin permission denial"
      }
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
      approvedAt: 1_900_000_060
    })
  ], {
    updatedAt: 1_900_000_061
  });
}

function createPopupDocument(): {
  document: BrowserExtensionPopupDocument;
  root: FakePopupElement;
  status: FakePopupElement;
  list: FakePopupElement;
  refresh: FakePopupElement;
} {
  const root = new FakePopupElement();
  const status = new FakePopupElement();
  const list = new FakePopupElement();
  const refresh = new FakePopupElement();
  const elements = new Map<string, FakePopupElement>([
    [BROWSER_EXTENSION_POPUP_ROOT_ID, root],
    [BROWSER_EXTENSION_POPUP_STATUS_ID, status],
    [BROWSER_EXTENSION_POPUP_LIST_ID, list],
    [BROWSER_EXTENSION_POPUP_REFRESH_ID, refresh]
  ]);
  return {
    document: {
      getElementById(id: string): unknown {
        return elements.get(id);
      },
      createElement(): BrowserExtensionPopupElement {
        return new FakePopupElement();
      }
    },
    root,
    status,
    list,
    refresh
  };
}

function createRuntimeGlobal(): {
  runtime: {
    onMessage: {
      addListener(listener: BrowserExtensionRuntimeMessageListener): void;
      removeListener(listener: BrowserExtensionRuntimeMessageListener): void;
    };
    getURL(path: string): string;
    sendMessage(message: unknown): unknown;
    sendNativeMessage(hostName: string, message: unknown): unknown;
  };
  nativeMessages: Array<{ hostName: string; message: unknown }>;
  runtimeMessages: unknown[];
  resolvedPaths: string[];
  emit(
    value: unknown,
    sender: unknown,
    sendResponse: (response: BrowserExtensionRuntimeMessageResponse) => void
  ): true | undefined;
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionRuntimeMessageListener>();
  const nativeMessages: Array<{ hostName: string; message: unknown }> = [];
  const runtimeMessages: unknown[] = [];
  const resolvedPaths: string[] = [];
  const runtime = {
    id: "extension@nsealr.dev",
    onMessage: {
      addListener(listener: BrowserExtensionRuntimeMessageListener): void {
        listeners.add(listener);
      },
      removeListener(listener: BrowserExtensionRuntimeMessageListener): void {
        listeners.delete(listener);
      }
    },
    getURL(path: string): string {
      resolvedPaths.push(path);
      return `chrome-extension://extension-id/${path}`;
    },
    sendMessage(message: unknown): unknown {
      runtimeMessages.push(message);
      return getPublicKeyResponse((message as BrowserExtensionRequest).request_id);
    },
    sendNativeMessage(hostName: string, message: unknown): unknown {
      nativeMessages.push({ hostName, message });
      return routeSelectionResponse(message as LocalServiceRequest);
    }
  };
  return {
    runtime,
    nativeMessages,
    runtimeMessages,
    resolvedPaths,
    emit(value, sender, sendResponse): true | undefined {
      const [listener] = listeners;
      return listener?.(value, sender, sendResponse);
    },
    listenerCount(): number {
      return listeners.size;
    }
  };
}

function createDocument(): {
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

function isPageBridgeRequest(value: unknown): value is BrowserExtensionPageBridgeRequest {
  return typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    (value as Record<string, unknown>).protocol === BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL &&
    (value as Record<string, unknown>).direction === "page_to_extension";
}

function createPageWindow(origin = "https://example.com"): {
  pageWindow: {
    nostr?: unknown;
    addEventListener(type: "message", listener: WindowMessageListener): void;
    removeEventListener(type: "message", listener: WindowMessageListener): void;
    postMessage(message: BrowserExtensionPageBridgeRequest | BrowserExtensionPageBridgeResponse, targetOrigin: string): void;
  };
  bridgeRequests: BrowserExtensionPageBridgeRequest[];
  postMessages: unknown[];
  dispatch(event: unknown): void;
  listenerCount(): number;
} {
  const listeners = new Set<WindowMessageListener>();
  const bridgeRequests: BrowserExtensionPageBridgeRequest[] = [];
  const postMessages: unknown[] = [];
  const pageWindow = {
    nostr: undefined as unknown,
    addEventListener(type: "message", listener: WindowMessageListener): void {
      expect(type).toBe("message");
      listeners.add(listener);
    },
    removeEventListener(type: "message", listener: WindowMessageListener): void {
      expect(type).toBe("message");
      listeners.delete(listener);
    },
    postMessage(message: BrowserExtensionPageBridgeRequest | BrowserExtensionPageBridgeResponse, targetOrigin: string): void {
      postMessages.push({ message, targetOrigin });
      if (!isPageBridgeRequest(message)) return;
      bridgeRequests.push(message);
      for (const listener of listeners) {
        listener({
          source: pageWindow,
          origin,
          data: {
            protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
            version: 1,
            direction: "extension_to_page",
            request_id: message.request_id,
            response: getPublicKeyResponse(message.request_id)
          }
        });
      }
    }
  };
  return {
    pageWindow,
    bridgeRequests,
    postMessages,
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

describe("packaged browser extension entrypoints", () => {
  it("wires the background packaged entrypoint through browser.runtime and secretless route config", async () => {
    const runtime = createRuntimeGlobal();
    const responses: BrowserExtensionRuntimeMessageResponse[] = [];
    const handle = installNsealrBackgroundEntrypoint({
      globalScope: { browser: { runtime: runtime.runtime } },
      routeConfig: routeConfig(),
      extensionId: "extension@nsealr.dev",
      nextServiceRequestId: () => "packaged-background-route"
    });

    expect(runtime.listenerCount()).toBe(1);
    expect(runtime.emit(
      getPublicKeyRequest("packaged-background-get-public-key"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      (response) => {
        responses.push(response);
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(responses).toEqual([getPublicKeyResponse("packaged-background-get-public-key")]);
    expect(runtime.nativeMessages).toEqual([{
      hostName: NATIVE_HOST_NAME,
      message: expect.objectContaining({
        request_id: "packaged-background-route",
        operation: "select_account_route",
        params: expect.objectContaining({
          route_request: routeRequest
        })
      })
    }]);
    handle.dispose();
    expect(runtime.listenerCount()).toBe(0);
  });

  it("forwards packaged background origin permissions before browser native messaging", async () => {
    const runtime = createRuntimeGlobal();
    const responses: BrowserExtensionRuntimeMessageResponse[] = [];
    const handle = installNsealrBackgroundEntrypoint({
      globalScope: { browser: { runtime: runtime.runtime } },
      routeConfig: routeConfig(),
      extensionId: "extension@nsealr.dev",
      originPermissions: {
        store: routeOnlyOriginPermissionStore(),
        localPairingDigest
      }
    });

    expect(runtime.emit(
      signEventRequest("packaged-background-origin-permission-denied"),
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
      request_id: "packaged-background-origin-permission-denied",
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

  it("uses the browser runtime sender id when no static extension id is configured", async () => {
    const runtime = createRuntimeGlobal();
    const responses: BrowserExtensionRuntimeMessageResponse[] = [];
    const handle = installNsealrBackgroundEntrypoint({
      globalScope: { browser: { runtime: runtime.runtime } },
      routeConfig: routeConfig(),
      originPermissions: {
        store: routeOnlyOriginPermissionStore(),
        localPairingDigest
      }
    });

    expect(runtime.emit(
      getPublicKeyRequest("packaged-background-runtime-id"),
      {
        id: "actual-chromium-runtime-id",
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
      request_id: "packaged-background-runtime-id",
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

  it("wires the content-script packaged entrypoint through chrome.runtime without storage", async () => {
    const runtime = createRuntimeGlobal();
    const document = createDocument();
    const pageWindow = createPageWindow();
    const handle = installNsealrContentScriptEntrypoint({
      globalScope: {
        chrome: { runtime: runtime.runtime },
        document: document.document,
        window: pageWindow.pageWindow,
        location: { origin: "https://example.com" }
      }
    });

    expect(runtime.resolvedPaths).toEqual([BROWSER_EXTENSION_PAGE_SCRIPT_FILE]);
    expect(document.appended).toEqual([expect.objectContaining({
      id: BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
      type: "module",
      async: false,
      src: `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`
    })]);

    pageWindow.dispatch({
      source: pageWindow.pageWindow,
      origin: "https://example.com",
      data: {
        protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
        version: 1,
        direction: "page_to_extension",
        request_id: "packaged-content-get-public-key",
        request: getPublicKeyRequest("packaged-content-get-public-key")
      }
    });
    await flushAsyncListeners();

    expect(runtime.runtimeMessages).toEqual([getPublicKeyRequest("packaged-content-get-public-key")]);
    handle.dispose();
    expect(pageWindow.listenerCount()).toBe(0);
    expect(document.removed).toEqual([document.appended[0]]);
  });

  it("wires the page-script packaged entrypoint over the reviewed page-window provider", async () => {
    const pageWindow = createPageWindow();
    const provider = installNsealrPageScriptEntrypoint({
      globalScope: {
        window: pageWindow.pageWindow,
        location: { origin: "https://example.com" }
      },
      nextRequestId: () => "packaged-page-get-public-key"
    });

    await expect(provider.getPublicKey()).resolves.toBe(publicKey);
    expect(pageWindow.pageWindow.nostr).toBe(provider);
    expect(pageWindow.bridgeRequests).toEqual([{
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "packaged-page-get-public-key",
      request: getPublicKeyRequest("packaged-page-get-public-key")
    }]);
  });

  it("wires the popup control entrypoint through browser.runtime without storage", async () => {
    const runtimeMessages: unknown[] = [];
    const controls = createNsealrPopupEntrypoint({
      globalScope: {
        browser: {
          runtime: {
            id: "extension@nsealr.dev",
            sendMessage(message: unknown): unknown {
              runtimeMessages.push(message);
              return {
                protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
                version: 1,
                request_id: "packaged-popup-list",
                ok: true,
                result: {
                  pending_requests: [{
                    format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
                    request_id: "pending-popup-entrypoint",
                    method: "get_public_key",
                    extension_id: "extension@nsealr.dev",
                    page_origin: "https://example.com",
                    status: "pending",
                    started_at: 1_900_000_400,
                    updated_at: 1_900_000_400,
                    stores_production_secrets: false,
                    includes_event_template: false
                  }],
                  stores_production_secrets: false,
                  contains_secret_material: false
                }
              };
            }
          }
        }
      },
      nextRequestId: () => "packaged-popup-list"
    });

    await expect(controls.listPendingRequests()).resolves.toEqual([{
      format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
      request_id: "pending-popup-entrypoint",
      method: "get_public_key",
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      status: "pending",
      started_at: 1_900_000_400,
      updated_at: 1_900_000_400,
      stores_production_secrets: false,
      includes_event_template: false
    }]);
    expect(runtimeMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "packaged-popup-list",
      method: "list_pending_requests"
    }]);
  });

  it("installs the packaged popup view through browser.runtime and document globals", async () => {
    const runtimeMessages: unknown[] = [];
    const popup = createPopupDocument();
    const handle = installNsealrPopupEntrypoint({
      globalScope: {
        browser: {
          runtime: {
            id: "extension@nsealr.dev",
            sendMessage(message: unknown): unknown {
              runtimeMessages.push(message);
              return {
                protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
                version: 1,
                request_id: "packaged-popup-install-list",
                ok: true,
                result: {
                  pending_requests: [{
                    format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
                    request_id: "pending-popup-install",
                    method: "sign_event",
                    extension_id: "extension@nsealr.dev",
                    page_origin: "https://example.com",
                    app_name: "Example",
                    status: "pending",
                    started_at: 1_900_000_410,
                    updated_at: 1_900_000_410,
                    stores_production_secrets: false,
                    includes_event_template: false
                  }],
                  stores_production_secrets: false,
                  contains_secret_material: false
                }
              };
            }
          }
        },
        document: popup.document
      },
      nextRequestId: () => "packaged-popup-install-list"
    });

    await flushAsyncListeners();

    expect(runtimeMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "packaged-popup-install-list",
      method: "list_pending_requests"
    }]);
    expect(popup.root.attributes.get("data-nsealr-popup")).toBe("ready");
    expect(popup.status.textContent).toBe("1 pending");
    expect(popup.list.children).toHaveLength(1);
    expect(popup.list.children[0].children[0].children[0].textContent).toBe("Sign event");
    handle.dispose();
    expect(popup.refresh.listeners.get("click")).toEqual([]);
  });

  it("installs the packaged origin-permission popup view through runtime, tabs, and document globals", async () => {
    const runtimeMessages: unknown[] = [];
    const popup = createPopupDocument();
    const originReview = {
      format: "nsealr-browser-origin-permission-review-v0",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      extension_id: "extension@nsealr.dev",
      requested_methods: [
        {
          method: "get_public_key",
          label: "Read public key",
          effect: "The page can read the selected account public key through the browser provider."
        },
        {
          method: "sign_event",
          label: "Request event signatures",
          effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
        }
      ],
      local_pairing_digest: localPairingDigest,
      requires_user_approval: true,
      stores_production_secrets: false,
      creates_grants: false,
      injects_provider: false
    };
    const approval = approveBrowserExtensionOriginPermissionReview(originReview, {
      reviewedLocalPairingDigest: localPairingDigest,
      approvedAt: 1_900_000_420
    });
    const nextIds = ["packaged-origin-review", "packaged-origin-approve"];
    const handle = installNsealrPopupOriginPermissionEntrypoint({
      globalScope: {
        browser: {
          runtime: {
            id: "extension@nsealr.dev",
            sendMessage(message: unknown): unknown {
              runtimeMessages.push(message);
              const request = message as { request_id: string; method: string };
              if (request.method === "request_origin_permission_review") {
                return {
                  protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
                  version: 1,
                  request_id: request.request_id,
                  ok: true,
                  result: {
                    origin_review: originReview,
                    stores_production_secrets: false,
                    contains_secret_material: false,
                    creates_grants: false,
                    injects_provider: false
                  }
                };
              }
              if (request.method === "approve_origin_permission") {
                return {
                  protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
                  version: 1,
                  request_id: request.request_id,
                  ok: true,
                  result: {
                    approval,
                    storage_write: {
                      format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
                      storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
                      store_format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
                      updated_at: 1_900_000_420,
                      approval_count: 1,
                      requires_user_approval: true,
                      reads_extension_storage: true,
                      writes_extension_storage: true,
                      creates_grants: false,
                      dispatches_signers: false,
                      stores_production_secrets: false,
                      contains_secret_material: false
                    },
                    requires_user_approval: true,
                    writes_extension_storage: true,
                    creates_grants: false,
                    dispatches_signers: false,
                    stores_production_secrets: false,
                    contains_secret_material: false
                  }
                };
              }
              throw new Error("unexpected popup control request");
            }
          },
          tabs: {
            query(queryInfo: unknown): unknown {
              expect(queryInfo).toEqual({ active: true, currentWindow: true });
              return [{
                id: 7,
                title: "Example",
                url: "https://example.com/client"
              }];
            }
          }
        },
        document: popup.document
      },
      nextRequestId: () => nextIds.shift() ?? "unexpected-popup-request"
    });

    await flushAsyncListeners();
    expect(popup.root.attributes.get("data-nsealr-popup-origin-permission")).toBe("ready");
    expect(popup.status.textContent).toBe("Review origin");
    expect(popup.list.children).toHaveLength(1);
    const approve = popup.list.children[0].children[4].children[1];
    approve.listeners.get("click")?.[0]?.();
    await flushAsyncListeners();

    expect(popup.status.textContent).toBe("Approved");
    expect(runtimeMessages.map((message) => (message as { method?: string }).method)).toEqual([
      "request_origin_permission_review",
      "approve_origin_permission"
    ]);
    handle.dispose();
    expect(popup.refresh.listeners.get("click")).toEqual([]);
  });

  it("rejects ambiguous extension runtime globals before installing listeners or scripts", () => {
    const runtime = createRuntimeGlobal();
    const otherRuntime = createRuntimeGlobal();
    const document = createDocument();

    expect(() => installNsealrBackgroundEntrypoint({
      globalScope: {
        browser: { runtime: runtime.runtime },
        chrome: { runtime: otherRuntime.runtime }
      },
      routeConfig: routeConfig()
    })).toThrow(/ambiguous/u);
    expect(runtime.listenerCount()).toBe(0);

    expect(() => installNsealrContentScriptEntrypoint({
      globalScope: {
        browser: { runtime: runtime.runtime },
        chrome: { runtime: otherRuntime.runtime },
        document: document.document,
        window: createPageWindow().pageWindow,
        location: { origin: "https://example.com" }
      }
    })).toThrow(/ambiguous/u);
    expect(document.appended).toEqual([]);

    expect(() => createNsealrPopupEntrypoint({
      globalScope: {
        browser: { runtime: runtime.runtime },
        chrome: { runtime: otherRuntime.runtime }
      }
    })).toThrow(/ambiguous/u);
  });
});
