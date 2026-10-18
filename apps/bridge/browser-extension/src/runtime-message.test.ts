import { describe, expect, it } from "vitest";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import { type BrowserNativeMessageSender } from "@nsealr/browser-provider";
import { createBrowserExtensionBackgroundController } from "./background.js";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import {
  browserExtensionSenderFromRuntimeSender,
  handleBrowserExtensionRuntimeMessage,
  installBrowserExtensionRuntimeMessageListener,
  type BrowserExtensionRuntimeMessageListener,
  type BrowserExtensionRuntimeMessageResponder
} from "./runtime-message.js";
import { createBrowserExtensionPendingRequestLifecycle } from "./pending-request.js";
import { BROWSER_EXTENSION_CONTROL_PROTOCOL } from "./pending-control.js";

const publicKey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
const routeRequest = {
  account_id: "esp32-usb-slot-0",
  method: "sign_event",
  route_type: "esp32_usb_nip46" as const
};

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
    if (message.operation === "select_account_route") return routeSelectionResponse(message);
    return handleLocalServiceRequest(message);
  };
}

function getPublicKeyRequest(requestId: string): {
  protocol: typeof BROWSER_EXTENSION_MESSAGE_PROTOCOL;
  version: 1;
  request_id: string;
  method: "get_public_key";
} {
  return {
    protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "get_public_key"
  };
}

function cancelPendingRequest(requestId: string, pendingRequestId: string): unknown {
  return {
    protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
    version: 1,
    request_id: requestId,
    method: "cancel_pending_request",
    params: {
      pending_request_id: pendingRequestId
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

function createInjectedRuntimeOnMessage(): {
  runtimeOnMessage: {
    addListener(listener: BrowserExtensionRuntimeMessageListener): void;
    removeListener(listener: BrowserExtensionRuntimeMessageListener): void;
  };
  emit(value: unknown, sender: unknown, sendResponse: BrowserExtensionRuntimeMessageResponder): true | undefined;
  listenerCount(): number;
} {
  const listeners = new Set<BrowserExtensionRuntimeMessageListener>();
  return {
    runtimeOnMessage: {
      addListener(listener: BrowserExtensionRuntimeMessageListener): void {
        listeners.add(listener);
      },
      removeListener(listener: BrowserExtensionRuntimeMessageListener): void {
        listeners.delete(listener);
      }
    },
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

describe("browser extension runtime message boundary", () => {
  it("maps browser runtime sender metadata into the internal sender shape", () => {
    expect(browserExtensionSenderFromRuntimeSender({
      id: "extension@nsealr.dev",
      url: "https://example.com/app",
      tab: { id: 42 },
      frameId: 0
    })).toEqual({
      extension_id: "extension@nsealr.dev",
      page_url: "https://example.com/app"
    });
    expect(browserExtensionSenderFromRuntimeSender({
      origin: "https://example.com",
      url: "https://example.com/app"
    }, {
      extensionId: "extension@nsealr.dev",
      appName: "Reviewed Browser Runtime"
    })).toEqual({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      page_url: "https://example.com/app",
      app_name: "Reviewed Browser Runtime"
    });
  });

  it("bridges runtime messages through the background controller without browser APIs", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "runtime-route"
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-get-public-key"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      { controller }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "runtime-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    });
    expect(nativeRequests).toHaveLength(1);
    expect(nativeRequests[0]).toMatchObject({
      operation: "select_account_route",
      params: {
        client: {
          surface: "browser_extension",
          origin: "https://example.com",
          instance_id: "extension@nsealr.dev"
        }
      }
    });
  });

  it("emits secretless pending request state around accepted runtime messages", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const states: unknown[] = [];
    const timestamps = [1_900_000_000, 1_900_000_001];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "runtime-pending-route"
    });
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle({
      now: () => timestamps.shift() ?? 1_900_000_001,
      onState: (state) => {
        states.push(state);
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-pending-get-public-key"),
      {
        id: "extension@nsealr.dev",
        origin: "https://example.com",
        url: "https://example.com/app"
      },
      {
        controller,
        pendingRequests
      }
    )).resolves.toMatchObject({
      request_id: "runtime-pending-get-public-key",
      ok: true
    });

    expect(states).toEqual([
      {
        format: "nsealr-browser-extension-pending-request-state-v0",
        request_id: "runtime-pending-get-public-key",
        method: "get_public_key",
        extension_id: "extension@nsealr.dev",
        page_origin: "https://example.com",
        app_name: "nSealr Browser Extension",
        status: "pending",
        started_at: 1_900_000_000,
        updated_at: 1_900_000_000,
        stores_production_secrets: false,
        includes_event_template: false
      },
      {
        format: "nsealr-browser-extension-pending-request-state-v0",
        request_id: "runtime-pending-get-public-key",
        method: "get_public_key",
        extension_id: "extension@nsealr.dev",
        page_origin: "https://example.com",
        app_name: "nSealr Browser Extension",
        status: "resolved",
        started_at: 1_900_000_000,
        updated_at: 1_900_000_001,
        stores_production_secrets: false,
        includes_event_template: false
      }
    ]);
    expect(pendingRequests.active()).toEqual([]);
  });

  it("returns deterministic invalid_sender responses before native messaging", async () => {
    let called = false;
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-invalid-sender"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        extensionId: "other-extension@nsealr.dev"
      }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "runtime-invalid-sender",
      ok: false,
      error: {
        code: "invalid_sender",
        message: "browser runtime sender is invalid",
        retryable: false
      }
    });
    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-missing-page"),
      { id: "extension@nsealr.dev" },
      { controller }
    )).resolves.toMatchObject({
      request_id: "runtime-missing-page",
      ok: false,
      error: {
        code: "invalid_sender"
      }
    });
    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-origin-mismatch"),
      {
        id: "extension@nsealr.dev",
        origin: "https://example.com",
        url: "https://other.example/app"
      },
      { controller }
    )).resolves.toMatchObject({
      request_id: "runtime-origin-mismatch",
      ok: false,
      error: {
        code: "invalid_sender"
      }
    });
    expect(called).toBe(false);
  });

  it("does not emit pending request state for invalid requests or invalid senders", async () => {
    const states: unknown[] = [];
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        throw new Error("invalid runtime input must not contact native messaging");
      }
    });
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle({
      onState: (state) => {
        states.push(state);
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "runtime-pending-invalid-request",
        method: "get_public_key",
        params: {}
      },
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        pendingRequests
      }
    )).resolves.toMatchObject({
      request_id: "runtime-pending-invalid-request",
      ok: false,
      error: {
        code: "invalid_request"
      }
    });
    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-pending-invalid-sender"),
      {
        id: "other-extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        extensionId: "extension@nsealr.dev",
        pendingRequests
      }
    )).resolves.toMatchObject({
      request_id: "runtime-pending-invalid-sender",
      ok: false,
      error: {
        code: "invalid_sender"
      }
    });

    expect(states).toEqual([]);
    expect(pendingRequests.active()).toEqual([]);
  });

  it("forwards request-scoped cancellation to the background controller", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const states: unknown[] = [];
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    });
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle({
      now: () => 1_900_000_010 + states.length,
      onState: (state) => {
        states.push(state);
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-cancelled"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        nativeMessageAbortSignal: abortController.signal,
        pendingRequests
      }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "runtime-cancelled",
      ok: false,
      error: {
        code: "provider_request_failed",
        message: "browser provider get_public_key failed",
        retryable: false
      }
    });
    expect(called).toBe(false);
    expect(states).toMatchObject([
      {
        request_id: "runtime-cancelled",
        status: "pending",
        includes_event_template: false
      },
      {
        request_id: "runtime-cancelled",
        status: "rejected",
        includes_event_template: false
      }
    ]);
    expect(pendingRequests.active()).toEqual([]);
  });

  it("lets pending request cancellation abort in-flight native messaging without a second rejected state", async () => {
    const states: unknown[] = [];
    const timestamps = [1_900_000_020, 1_900_000_021];
    let seenSignal: AbortSignal | undefined;
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: (_hostName, _message, options) => {
        seenSignal = options.abortSignal;
        return new Promise((_resolve, reject) => {
          options.abortSignal?.addEventListener("abort", () => {
            reject(new Error("native request cancelled by pending UI"));
          }, { once: true });
        });
      }
    });
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle({
      now: () => timestamps.shift() ?? 1_900_000_021,
      onState: (state) => {
        states.push(state);
      }
    });

    const response = handleBrowserExtensionRuntimeMessage(
      getPublicKeyRequest("runtime-pending-ui-cancel"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        pendingRequests
      }
    );
    await flushAsyncListeners();
    expect(pendingRequests.active()).toHaveLength(1);
    expect(seenSignal?.aborted).toBe(false);

    const cancelled = pendingRequests.cancel("runtime-pending-ui-cancel");

    expect(cancelled).toMatchObject({
      request_id: "runtime-pending-ui-cancel",
      status: "cancelled",
      includes_event_template: false
    });
    expect(seenSignal?.aborted).toBe(true);
    await expect(response).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "runtime-pending-ui-cancel",
      ok: false,
      error: {
        code: "provider_request_failed",
        message: "browser provider get_public_key failed",
        retryable: false
      }
    });
    expect(states).toMatchObject([
      {
        request_id: "runtime-pending-ui-cancel",
        status: "pending",
        includes_event_template: false
      },
      {
        request_id: "runtime-pending-ui-cancel",
        status: "cancelled",
        includes_event_template: false
      }
    ]);
    expect(pendingRequests.active()).toEqual([]);
  });

  it("routes extension-internal control messages to the pending cancellation boundary", async () => {
    const states: unknown[] = [];
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle({
      onState: (state) => {
        states.push(state);
      }
    });
    pendingRequests.start(
      getPublicKeyRequest("runtime-control-pending"),
      {
        extension_id: "extension@nsealr.dev",
        page_origin: "https://example.com"
      }
    );
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        throw new Error("control messages must not contact native messaging");
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      cancelPendingRequest("runtime-control-cancel", "runtime-control-pending"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      {
        controller,
        extensionId: "extension@nsealr.dev",
        pendingRequests
      }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "runtime-control-cancel",
      ok: true,
      result: {
        pending_request_id: "runtime-control-pending",
        cancelled: true,
        stores_production_secrets: false,
        contains_secret_material: false
      }
    });
    expect(states).toMatchObject([
      {
        request_id: "runtime-control-pending",
        status: "pending"
      },
      {
        request_id: "runtime-control-pending",
        status: "cancelled"
      }
    ]);
    expect(pendingRequests.active()).toEqual([]);
  });

  it("routes extension-internal control messages to list active pending requests", async () => {
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle();
    const started = pendingRequests.start(
      getPublicKeyRequest("runtime-control-listed"),
      {
        extension_id: "extension@nsealr.dev",
        page_origin: "https://example.com"
      }
    );
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        throw new Error("list control messages must not contact native messaging");
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      listPendingRequests("runtime-control-list"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      {
        controller,
        extensionId: "extension@nsealr.dev",
        pendingRequests
      }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "runtime-control-list",
      ok: true,
      result: {
        pending_requests: [started],
        stores_production_secrets: false,
        contains_secret_material: false
      }
    });
    expect(pendingRequests.active()).toEqual([started]);
  });

  it("routes extension-internal control messages to origin permission review", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "runtime-control-origin-review-service"
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      requestOriginPermissionReview("runtime-control-origin-review"),
      {
        id: "extension@nsealr.dev",
        url: "chrome-extension://extension-id/popup.html"
      },
      {
        controller,
        extensionId: "extension@nsealr.dev"
      }
    )).resolves.toMatchObject({
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "runtime-control-origin-review",
      ok: true,
      result: {
        origin_review: {
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
        },
        stores_production_secrets: false,
        contains_secret_material: false,
        creates_grants: false,
        injects_provider: false
      }
    });
    expect(nativeRequests.map((request) => request.operation)).toEqual(["request_pairing"]);
  });

  it("rejects page-origin control messages before they can cancel pending requests", async () => {
    const pendingRequests = createBrowserExtensionPendingRequestLifecycle();
    const started = pendingRequests.start(
      getPublicKeyRequest("runtime-page-control-pending"),
      {
        extension_id: "extension@nsealr.dev",
        page_origin: "https://example.com"
      }
    );
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        throw new Error("invalid control sender must not contact native messaging");
      }
    });

    await expect(handleBrowserExtensionRuntimeMessage(
      cancelPendingRequest("runtime-page-control-cancel", "runtime-page-control-pending"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      {
        controller,
        extensionId: "extension@nsealr.dev",
        pendingRequests
      }
    )).resolves.toMatchObject({
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      request_id: "runtime-page-control-cancel",
      ok: false,
      error: {
        code: "invalid_sender"
      }
    });
    expect(pendingRequests.active()).toEqual([started]);
  });

  it("installs an injected runtime message listener and sends accepted responses", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const runtime = createInjectedRuntimeOnMessage();
    const responses: unknown[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "runtime-listener-route"
    });

    const handle = installBrowserExtensionRuntimeMessageListener({
      runtimeOnMessage: runtime.runtimeOnMessage,
      controller,
      extensionId: "extension@nsealr.dev"
    });
    expect(runtime.listenerCount()).toBe(1);

    expect(runtime.emit(
      getPublicKeyRequest("runtime-listener-get-public-key"),
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
      request_id: "runtime-listener-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    }]);
    expect(nativeRequests.map((request) => request.operation)).toEqual(["select_account_route"]);

    handle.dispose();
    expect(runtime.listenerCount()).toBe(0);
  });

  it("returns deterministic invalid-sender responses through the listener before native messaging", async () => {
    const runtime = createInjectedRuntimeOnMessage();
    const responses: unknown[] = [];
    const nativeRequests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: nativeResponder(nativeRequests)
    });

    installBrowserExtensionRuntimeMessageListener({
      runtimeOnMessage: runtime.runtimeOnMessage,
      controller,
      extensionId: "extension@nsealr.dev"
    });
    expect(runtime.emit(
      getPublicKeyRequest("runtime-listener-invalid-sender"),
      {
        id: "other-extension@nsealr.dev",
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
      request_id: "runtime-listener-invalid-sender",
      ok: false,
      error: {
        code: "invalid_sender",
        message: "browser runtime sender is invalid",
        retryable: false
      }
    }]);
    expect(nativeRequests).toEqual([]);
  });

  it("returns deterministic listener failures instead of leaving browser callers without a response", async () => {
    const runtime = createInjectedRuntimeOnMessage();
    const responses: unknown[] = [];
    const errors: unknown[] = [];

    installBrowserExtensionRuntimeMessageListener({
      runtimeOnMessage: runtime.runtimeOnMessage,
      controller: {
        async handleRequest() {
          throw new Error("unexpected runtime handler failure");
        },
        async requestOriginPermissionReview() {
          throw new Error("not reached");
        },
        async approveOriginPermission() {
          throw new Error("not reached");
        }
      },
      onError: (error) => {
        errors.push(error);
      }
    });
    expect(runtime.emit(
      getPublicKeyRequest("runtime-listener-handler-failure"),
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
      request_id: "runtime-listener-handler-failure",
      ok: false,
      error: {
        code: "runtime_handler_failed",
        message: "browser extension runtime request failed",
        retryable: false
      }
    }]);
    expect(errors).toHaveLength(1);
    expect((errors[0] as Error).message).toMatch(/unexpected runtime handler failure/u);
  });

  it("does not receive runtime messages after disposal", async () => {
    const runtime = createInjectedRuntimeOnMessage();
    const controller = createBrowserExtensionBackgroundController({
      routeRequest,
      sendNativeMessage: () => {
        throw new Error("disposed listener must not contact native messaging");
      }
    });
    const handle = installBrowserExtensionRuntimeMessageListener({
      runtimeOnMessage: runtime.runtimeOnMessage,
      controller
    });
    handle.dispose();
    expect(runtime.listenerCount()).toBe(0);
    expect(runtime.emit(
      getPublicKeyRequest("runtime-listener-disposed"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      () => {
        throw new Error("disposed listener must not send responses");
      }
    )).toBeUndefined();
    await flushAsyncListeners();
  });

  it("reports runtime listener response failures without unhandled rejections", async () => {
    const runtime = createInjectedRuntimeOnMessage();
    const errors: unknown[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder([]),
      routeRequest,
      nextServiceRequestId: () => "runtime-listener-error-route"
    });

    installBrowserExtensionRuntimeMessageListener({
      runtimeOnMessage: runtime.runtimeOnMessage,
      controller,
      onError: (error) => {
        errors.push(error);
      }
    });
    expect(runtime.emit(
      getPublicKeyRequest("runtime-listener-response-failure"),
      {
        id: "extension@nsealr.dev",
        url: "https://example.com/app"
      },
      () => {
        throw new Error("sendResponse failed");
      }
    )).toBe(true);
    await flushAsyncListeners();

    expect(errors).toHaveLength(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect((errors[0] as Error).message).toMatch(/sendResponse failed/u);
  });
});
