import { describe, expect, it } from "vitest";
import { handleLocalServiceRequest, type LocalServiceRequest } from "@nsealr/client";
import {
  NATIVE_HOST_NAME,
  type BrowserNativeMessageSender
} from "@nsealr/browser-provider";
import {
  BROWSER_EXTENSION_DEFAULT_PAIRING_OPERATIONS,
  approveBrowserExtensionOriginPermissionReview,
  parseBrowserExtensionOriginPermissionApproval,
  parseBrowserExtensionOriginPermissionReview,
  projectBrowserExtensionOriginPermissionReview,
  requestBrowserExtensionNativeMessagingPairingIntent,
  requestBrowserExtensionNativeMessagingPairingReview,
  requestBrowserExtensionNativeMessagingOriginPermissionReview
} from "./pairing.js";

const sender = {
  extension_id: "extension@nsealr.dev",
  page_url: "https://example.com/app"
};

describe("browser extension native-messaging pairing boundary", () => {
  it("requests a digest-bound pairing intent for the sender-derived client identity", async () => {
    const hosts: string[] = [];
    const requests: LocalServiceRequest[] = [];
    const sendNativeMessage: BrowserNativeMessageSender = (hostName, message) => {
      hosts.push(hostName);
      requests.push(message);
      return handleLocalServiceRequest(message);
    };

    const result = await requestBrowserExtensionNativeMessagingPairingIntent(sender, {
      sendNativeMessage,
      nextServiceRequestId: () => "browser-pairing-intent"
    });

    expect(result.context.client).toEqual({
      surface: "browser_extension",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      instance_id: "extension@nsealr.dev"
    });
    expect(result.response).toMatchObject({
      request_id: "browser-pairing-intent",
      ok: true,
      result: {
        pairing_intent: {
          client: result.context.client,
          requested_operations: BROWSER_EXTENSION_DEFAULT_PAIRING_OPERATIONS,
          requires_user_approval: true,
          stores_production_secrets: false
        }
      }
    });
    expect(hosts).toEqual([NATIVE_HOST_NAME]);
    expect(requests).toHaveLength(1);
    expect(requests[0]).toMatchObject({
      operation: "request_pairing",
      params: {
        client: result.context.client,
        requested_operations: BROWSER_EXTENSION_DEFAULT_PAIRING_OPERATIONS
      }
    });
  });

  it("allows explicit operation scope without adding grants or storage", async () => {
    const requests: LocalServiceRequest[] = [];
    const sendNativeMessage: BrowserNativeMessageSender = (_hostName, message) => {
      requests.push(message);
      return handleLocalServiceRequest(message);
    };

    const result = await requestBrowserExtensionNativeMessagingPairingIntent(sender, {
      sendNativeMessage,
      requestedOperations: ["select_account_route"],
      nextServiceRequestId: () => "browser-pairing-route-only"
    });

    expect(result.response).toMatchObject({
      ok: true,
      result: {
        pairing_intent: {
          requested_operations: ["select_account_route"]
        }
      }
    });
    expect(requests[0]).toMatchObject({
      params: {
        requested_operations: ["select_account_route"]
      }
    });
  });

  it("projects native pairing intents into deterministic review metadata", async () => {
    const result = await requestBrowserExtensionNativeMessagingPairingReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      nextServiceRequestId: () => "browser-pairing-review"
    });

    expect(result.response).toMatchObject({
      request_id: "browser-pairing-review",
      ok: true
    });
    expect(result.review).toMatchObject({
      format: "nsealr-local-pairing-review-v0",
      client: result.context.client,
      requested_operations: [
        {
          operation: "select_account_route",
          label: "Read selected account route"
        },
        {
          operation: "dispatch_signer_request",
          label: "Dispatch signer requests"
        }
      ],
      requires_user_approval: true,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    if (result.response.ok !== true || !("pairing_intent" in result.response.result)) {
      throw new Error("pairing intent was not returned");
    }
    expect(result.review.pairing_digest).toBe(result.response.result.pairing_intent.pairing_digest);
  });

  it("projects browser origin permission review without approving grants or injecting providers", async () => {
    const result = await requestBrowserExtensionNativeMessagingOriginPermissionReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      nextServiceRequestId: () => "browser-origin-review"
    });

    expect(result.originReview).toEqual({
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
      local_pairing_digest: result.review.pairing_digest,
      requires_user_approval: true,
      stores_production_secrets: false,
      creates_grants: false,
      injects_provider: false
    });
  });

  it("creates origin permission approvals only after explicit digest confirmation", async () => {
    const result = await requestBrowserExtensionNativeMessagingOriginPermissionReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      nextServiceRequestId: () => "browser-origin-approve"
    });

    expect(parseBrowserExtensionOriginPermissionReview(result.originReview)).toEqual(result.originReview);
    const approval = approveBrowserExtensionOriginPermissionReview(result.originReview, {
      approvedAt: 1_900_000_000,
      reviewedLocalPairingDigest: result.originReview.local_pairing_digest
    });

    expect(approval).toEqual({
      format: "nsealr-browser-origin-permission-approval-v0",
      origin: "https://example.com",
      app_name: "nSealr Browser Extension",
      extension_id: "extension@nsealr.dev",
      approved_methods: ["get_public_key", "sign_event"],
      local_pairing_digest: result.originReview.local_pairing_digest,
      approved_at: 1_900_000_000,
      requires_user_approval: true,
      authorizes_provider_injection: true,
      creates_grants: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(parseBrowserExtensionOriginPermissionApproval(approval)).toEqual(approval);
  });

  it("rejects tampered origin permission review or approval artifacts", async () => {
    const result = await requestBrowserExtensionNativeMessagingOriginPermissionReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      nextServiceRequestId: () => "browser-origin-tamper"
    });

    expect(() => approveBrowserExtensionOriginPermissionReview(result.originReview, {
      approvedAt: 1_900_000_000,
      reviewedLocalPairingDigest: "0".repeat(64)
    })).toThrow(/digest does not match/u);

    expect(() => parseBrowserExtensionOriginPermissionReview({
      ...result.originReview,
      injects_provider: true
    })).toThrow(/must not inject/u);

    expect(() => parseBrowserExtensionOriginPermissionReview({
      ...result.originReview,
      requested_methods: [
        {
          ...result.originReview.requested_methods[0],
          label: "Unsafe rewritten label"
        }
      ]
    })).toThrow(/method text/u);

    const approval = approveBrowserExtensionOriginPermissionReview(result.originReview, {
      approvedAt: 1_900_000_000,
      reviewedLocalPairingDigest: result.originReview.local_pairing_digest
    });
    expect(() => parseBrowserExtensionOriginPermissionApproval({
      ...approval,
      creates_grants: true
    })).toThrow(/must not create grants/u);
    expect(() => parseBrowserExtensionOriginPermissionApproval({
      ...approval,
      approved_methods: ["get_public_key", "get_public_key"]
    })).toThrow(/duplicated/u);
  });

  it("keeps route-only browser origin review scoped to public-key access", async () => {
    const result = await requestBrowserExtensionNativeMessagingOriginPermissionReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      requestedOperations: ["select_account_route"],
      nextServiceRequestId: () => "browser-origin-route-only"
    });

    expect(result.originReview.requested_methods.map((method) => method.method)).toEqual(["get_public_key"]);
  });

  it("rejects origin permission reviews with no page-visible methods", async () => {
    const result = await requestBrowserExtensionNativeMessagingPairingReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest(message),
      requestedOperations: ["verify_signer_response"],
      nextServiceRequestId: () => "browser-origin-no-visible-method"
    });

    expect(() => projectBrowserExtensionOriginPermissionReview(result)).toThrow(/no page-visible methods/u);
  });

  it("rejects operation-mismatched native pairing responses before review", async () => {
    await expect(requestBrowserExtensionNativeMessagingPairingReview(sender, {
      sendNativeMessage: (_hostName, message) => handleLocalServiceRequest({
        version: 1,
        request_id: message.request_id,
        operation: "service_status"
      })
    })).rejects.toThrow(/request_pairing returned unexpected local service result/u);
  });

  it("rejects invalid senders or native host names before contacting native messaging", async () => {
    let called = false;
    const sendNativeMessage: BrowserNativeMessageSender = () => {
      called = true;
      return {};
    };

    await expect(requestBrowserExtensionNativeMessagingPairingIntent({
      extension_id: "extension@nsealr.dev",
      page_url: "http://localhost.evil.example/app"
    }, { sendNativeMessage })).rejects.toThrow(/sender|localhost|origin/u);
    expect(called).toBe(false);

    await expect(requestBrowserExtensionNativeMessagingPairingIntent(sender, {
      hostName: "bad host name",
      sendNativeMessage
    })).rejects.toThrow(/native host name/u);
    expect(called).toBe(false);
  });
});
