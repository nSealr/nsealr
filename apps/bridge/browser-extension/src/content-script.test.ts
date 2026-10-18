import { describe, expect, it } from "vitest";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import { type BrowserNativeMessageSender } from "@nsealr/browser-provider";
import { createBrowserExtensionBackgroundController } from "./background.js";
import {
  createBrowserExtensionContentScriptRuntimeRequester,
  handleBrowserExtensionContentScriptBridgeMessage
} from "./content-script.js";
import { BROWSER_EXTENSION_MESSAGE_PROTOCOL } from "./handler.js";
import { BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL } from "./page-bridge.js";

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

function getPublicKeyResponse(requestId: string): unknown {
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

describe("browser extension content-script bridge boundary", () => {
  it("bridges page envelopes to an injected background requester with sender binding", async () => {
    const nativeRequests: LocalServiceRequest[] = [];
    const controller = createBrowserExtensionBackgroundController({
      sendNativeMessage: nativeResponder(nativeRequests),
      routeRequest,
      nextServiceRequestId: () => "content-script-route"
    });

    await expect(handleBrowserExtensionContentScriptBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "content-script-get-public-key",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-script-get-public-key",
        method: "get_public_key"
      }
    }, {
      sender,
      requestBackground: (request, requestSender, options) => controller.handleRequest(request, requestSender, options)
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-script-get-public-key",
      response: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-script-get-public-key",
        ok: true,
        result: {
          pubkey: publicKey
        }
      }
    });
    expect(nativeRequests.map((request) => request.operation)).toEqual(["select_account_route"]);
  });

  it("rejects malformed page envelopes before contacting the background", async () => {
    let called = false;
    await expect(handleBrowserExtensionContentScriptBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-script-wrong-direction",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-script-wrong-direction",
        method: "get_public_key"
      }
    }, {
      sender,
      requestBackground: () => {
        called = true;
        return {};
      }
    })).rejects.toThrow(/direction/u);
    expect(called).toBe(false);
  });

  it("forwards cancellation to the injected background requester", async () => {
    const abortController = new AbortController();
    let seenSignal: AbortSignal | undefined;
    await expect(handleBrowserExtensionContentScriptBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "content-script-cancellation",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-script-cancellation",
        method: "get_public_key"
      }
    }, {
      sender,
      abortSignal: abortController.signal,
      requestBackground: (_request, _sender, options) => {
        seenSignal = options.nativeMessageAbortSignal;
        return {
          protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
          version: 1,
          request_id: "content-script-cancellation",
          ok: true,
          result: {
            pubkey: publicKey
          }
        };
      }
    })).resolves.toMatchObject({
      request_id: "content-script-cancellation"
    });
    expect(seenSignal).toBe(abortController.signal);
  });

  it("rejects cancelled messages before contacting the background", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    await expect(handleBrowserExtensionContentScriptBridgeMessage({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "page_to_extension",
      request_id: "content-script-cancelled",
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-script-cancelled",
        method: "get_public_key"
      }
    }, {
      sender,
      abortSignal: abortController.signal,
      requestBackground: () => {
        called = true;
        return {};
      }
    })).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);
  });

  it("bridges page envelopes through an injected runtime message sender", async () => {
    const runtimeRequests: unknown[] = [];
    await expect(handleBrowserExtensionContentScriptBridgeMessage(
      pageBridgeRequest("content-runtime-get-public-key"),
      {
        sender: { ignored: true },
        requestBackground: createBrowserExtensionContentScriptRuntimeRequester({
          sendRuntimeMessage: (request, options) => {
            runtimeRequests.push({
              request,
              abortSignalForwarded: options.abortSignal !== undefined
            });
            return getPublicKeyResponse(request.request_id);
          }
        })
      }
    )).resolves.toEqual({
      protocol: BROWSER_EXTENSION_PAGE_BRIDGE_PROTOCOL,
      version: 1,
      direction: "extension_to_page",
      request_id: "content-runtime-get-public-key",
      response: getPublicKeyResponse("content-runtime-get-public-key")
    });
    expect(runtimeRequests).toEqual([{
      request: {
        protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
        version: 1,
        request_id: "content-runtime-get-public-key",
        method: "get_public_key"
      },
      abortSignalForwarded: false
    }]);
  });

  it("forwards bridge cancellation to the injected runtime message sender", async () => {
    const abortController = new AbortController();
    let seenSignal: AbortSignal | undefined;
    await expect(handleBrowserExtensionContentScriptBridgeMessage(
      pageBridgeRequest("content-runtime-cancellation"),
      {
        sender,
        abortSignal: abortController.signal,
        requestBackground: createBrowserExtensionContentScriptRuntimeRequester({
          sendRuntimeMessage: (request, options) => {
            seenSignal = options.abortSignal;
            return getPublicKeyResponse(request.request_id);
          }
        })
      }
    )).resolves.toMatchObject({
      request_id: "content-runtime-cancellation"
    });
    expect(seenSignal).toBe(abortController.signal);
  });

  it("rejects already-cancelled runtime requests before sending", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const requestBackground = createBrowserExtensionContentScriptRuntimeRequester({
      abortSignal: abortController.signal,
      sendRuntimeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "content-runtime-cancelled",
      method: "get_public_key"
    }, sender, {})).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);
  });

  it("rejects in-flight runtime requests when cancellation wins", async () => {
    const abortController = new AbortController();
    let seenSignal: AbortSignal | undefined;
    const requestBackground = createBrowserExtensionContentScriptRuntimeRequester({
      sendRuntimeMessage: (_request, options) => {
        seenSignal = options.abortSignal;
        return new Promise(() => undefined);
      }
    });

    const response = requestBackground({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "content-runtime-in-flight-cancelled",
      method: "get_public_key"
    }, sender, {
      nativeMessageAbortSignal: abortController.signal
    });
    abortController.abort();

    await expect(response).rejects.toThrow(/cancelled/u);
    expect(seenSignal).toBe(abortController.signal);
  });
});
