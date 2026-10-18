import { describe, expect, it } from "vitest";
import { type LocalServiceRequest } from "@nsealr/client";
import {
  NATIVE_HOST_NAME,
  type BrowserNativeMessageSender
} from "@nsealr/browser-provider";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  handleBrowserExtensionSenderRequest
} from "./handler.js";
import { createBrowserExtensionNativeMessagingProviderSelector } from "./local-service.js";

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
const eventTemplate = {
  kind: 1,
  created_at: 1_710_000_000,
  tags: [],
  content: "browser extension native messaging test"
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

function dispatchUnavailableResponse(request: LocalServiceRequest): unknown {
  return {
    version: 1,
    request_id: request.request_id,
    ok: false,
    error: {
      code: "signer_route_unavailable",
      message: "signer dispatch is not configured",
      retryable: false
    }
  };
}

describe("browser extension native-messaging local-service provider selector", () => {
  it("routes sender-derived identity to the native-messaging local service before returning a public key", async () => {
    const hosts: string[] = [];
    const requests: LocalServiceRequest[] = [];
    const sendNativeMessage: BrowserNativeMessageSender = (hostName, message) => {
      hosts.push(hostName);
      requests.push(message);
      return routeSelectionResponse(message);
    };

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-native-get-public-key",
      method: "get_public_key"
    }, sender, {
      providerForClient: createBrowserExtensionNativeMessagingProviderSelector({
        sendNativeMessage,
        routeRequest,
        nextServiceRequestId: () => "native-route-selection"
      })
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-native-get-public-key",
      ok: true,
      result: {
        pubkey: publicKey
      }
    });

    expect(hosts).toEqual([NATIVE_HOST_NAME]);
    expect(requests).toHaveLength(1);
    expect(requests[0]).toMatchObject({
      request_id: "native-route-selection",
      operation: "select_account_route",
      params: {
        client: {
          surface: "browser_extension",
          origin: "https://example.com",
          app_name: "nSealr Browser Extension",
          instance_id: "extension@nsealr.dev"
        },
        route_request: routeRequest
      }
    });
  });

  it("routes sign_event through local-service dispatch while signer dispatch is unavailable", async () => {
    const operations: string[] = [];
    const sendNativeMessage: BrowserNativeMessageSender = (_hostName, message) => {
      operations.push(message.operation);
      if (message.operation === "dispatch_signer_request") return dispatchUnavailableResponse(message);
      throw new Error(`unexpected operation ${message.operation}`);
    };

    await expect(handleBrowserExtensionSenderRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-native-sign-event",
      method: "sign_event",
      params: {
        event_template: eventTemplate
      }
    }, sender, {
      providerForClient: createBrowserExtensionNativeMessagingProviderSelector({
        sendNativeMessage,
        routeRequest,
        nextSignerRequestId: () => "native-signer-request"
      })
    })).resolves.toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-native-sign-event",
      ok: false,
      error: {
        code: "provider_request_failed",
        message: "browser provider sign_event failed",
        retryable: false
      }
    });

    expect(operations).toEqual(["dispatch_signer_request"]);
  });

  it("rejects invalid native host names before contacting browser native messaging", () => {
    let called = false;

    expect(() => createBrowserExtensionNativeMessagingProviderSelector({
      hostName: "bad host name",
      routeRequest,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    })).toThrow(/native host name/u);
    expect(called).toBe(false);
  });
});
