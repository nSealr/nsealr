import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_CONTROL_PROTOCOL
} from "./pending-control.js";
import {
  BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT
} from "./pending-request.js";
import {
  createBrowserExtensionPopupControls
} from "./popup-control.js";
import {
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT
} from "./origin-permission-storage.js";

const pendingState = Object.freeze({
  format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
  request_id: "pending-popup-visible",
  method: "get_public_key" as const,
  extension_id: "extension@nsealr.dev",
  page_origin: "https://example.com",
  status: "pending" as const,
  started_at: 1_900_000_300,
  updated_at: 1_900_000_300,
  stores_production_secrets: false as const,
  includes_event_template: false as const
});

const originReview: BrowserExtensionOriginPermissionReview = {
  format: "nsealr-browser-origin-permission-review-v0",
  origin: "https://example.com",
  app_name: "Example App",
  extension_id: "extension@nsealr.dev",
  requested_methods: [
    {
      method: "get_public_key",
      label: "Read public key",
      effect: "The page can read the selected account public key through the browser provider."
    }
  ],
  local_pairing_digest: "a".repeat(64),
  requires_user_approval: true,
  stores_production_secrets: false,
  creates_grants: false,
  injects_provider: false
};

const originApproval = approveBrowserExtensionOriginPermissionReview(originReview, {
  reviewedLocalPairingDigest: originReview.local_pairing_digest,
  approvedAt: 1_900_000_410
});

const storageWrite = {
  format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
  storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  store_format: "nsealr-browser-origin-permission-store-v0",
  updated_at: 1_900_000_411,
  approval_count: 1,
  requires_user_approval: true,
  reads_extension_storage: true,
  writes_extension_storage: true,
  creates_grants: false,
  dispatches_signers: false,
  stores_production_secrets: false,
  contains_secret_material: false
} as const;

describe("browser extension popup pending request controls", () => {
  it("lists pending requests through runtime.sendMessage without exposing hidden payloads", async () => {
    const sentMessages: unknown[] = [];
    const controls = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(message: unknown): unknown {
          sentMessages.push(message);
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-list-1",
            ok: true,
            result: {
              pending_requests: [pendingState],
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-list-1"
    });

    await expect(controls.listPendingRequests()).resolves.toEqual([pendingState]);
    expect(sentMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "popup-list-1",
      method: "list_pending_requests"
    }]);
  });

  it("cancels pending requests through the internal control protocol", async () => {
    const sentMessages: unknown[] = [];
    const controls = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(message: unknown): unknown {
          sentMessages.push(message);
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-cancel-1",
            ok: true,
            result: {
              pending_request_id: "pending-popup-visible",
              cancelled: true,
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-cancel-1"
    });

    await expect(controls.cancelPendingRequest("pending-popup-visible")).resolves.toEqual({
      pending_request_id: "pending-popup-visible",
      cancelled: true,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(sentMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "popup-cancel-1",
      method: "cancel_pending_request",
      params: {
        pending_request_id: "pending-popup-visible"
      }
    }]);
  });

  it("requests origin permission review through the internal control protocol", async () => {
    const sentMessages: unknown[] = [];
    const controls = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(message: unknown): unknown {
          sentMessages.push(message);
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-origin-review-1",
            ok: true,
            result: {
              origin_review: {
                format: "nsealr-browser-origin-permission-review-v0",
                origin: "https://example.com",
                app_name: "Example App",
                extension_id: "extension@nsealr.dev",
                requested_methods: [
                  {
                    method: "get_public_key",
                    label: "Read public key",
                    effect: "The page can read the selected account public key through the browser provider."
                  }
                ],
                local_pairing_digest: "a".repeat(64),
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
          };
        }
      },
      nextRequestId: () => "popup-origin-review-1"
    });

    await expect(controls.requestOriginPermissionReview({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      app_name: "Example App"
    })).resolves.toMatchObject({
      origin_review: {
        origin: "https://example.com",
        requested_methods: [
          {
            method: "get_public_key"
          }
        ]
      },
      stores_production_secrets: false,
      contains_secret_material: false,
      creates_grants: false,
      injects_provider: false
    });
    expect(sentMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "popup-origin-review-1",
      method: "request_origin_permission_review",
      params: {
        sender: {
          extension_id: "extension@nsealr.dev",
          page_origin: "https://example.com",
          app_name: "Example App"
        }
      }
    }]);
  });

  it("approves origin permission review through the internal control protocol", async () => {
    const sentMessages: unknown[] = [];
    const controls = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(message: unknown): unknown {
          sentMessages.push(message);
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-origin-approve-1",
            ok: true,
            result: {
              approval: originApproval,
              storage_write: storageWrite,
              requires_user_approval: true,
              writes_extension_storage: true,
              creates_grants: false,
              dispatches_signers: false,
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-origin-approve-1"
    });

    await expect(controls.approveOriginPermission(
      originReview,
      originReview.local_pairing_digest
    )).resolves.toMatchObject({
      approval: {
        origin: "https://example.com",
        approved_methods: ["get_public_key"],
        stores_production_secrets: false,
        contains_secret_material: false
      },
      storage_write: {
        writes_extension_storage: true,
        dispatches_signers: false
      }
    });
    expect(sentMessages).toEqual([{
      protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
      version: 1,
      request_id: "popup-origin-approve-1",
      method: "approve_origin_permission",
      params: {
        origin_review: originReview,
        reviewed_local_pairing_digest: originReview.local_pairing_digest
      }
    }]);
  });

  it("rejects invalid runtime dependencies and invalid response envelopes", async () => {
    expect(() => createBrowserExtensionPopupControls({
      runtime: {} as never
    })).toThrow(/runtime/u);

    const mismatched = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(): unknown {
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "different-request-id",
            ok: true,
            result: {
              pending_requests: [],
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-list-expected"
    });
    await expect(mismatched.listPendingRequests()).rejects.toThrow(/mismatch/u);

    const unsafe = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(): unknown {
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-list-unsafe",
            ok: true,
            result: {
              pending_requests: [{
                ...pendingState,
                includes_event_template: true
              }],
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-list-unsafe"
    });
    await expect(unsafe.listPendingRequests()).rejects.toThrow(/event templates/u);

    const settled = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(): unknown {
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-list-settled",
            ok: true,
            result: {
              pending_requests: [{
                ...pendingState,
                status: "resolved"
              }],
              stores_production_secrets: false,
              contains_secret_material: false
            }
          };
        }
      },
      nextRequestId: () => "popup-list-settled"
    });
    await expect(settled.listPendingRequests()).rejects.toThrow(/must be active/u);
  });

  it("surfaces deterministic control errors and local cancellation", async () => {
    const denied = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(): unknown {
          return {
            protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
            version: 1,
            request_id: "popup-denied",
            ok: false,
            error: {
              code: "invalid_sender",
              message: "browser extension control sender is invalid",
              retryable: false
            }
          };
        }
      },
      nextRequestId: () => "popup-denied"
    });
    await expect(denied.listPendingRequests()).rejects.toThrow(/invalid_sender/u);

    const abortController = new AbortController();
    abortController.abort();
    const cancelled = createBrowserExtensionPopupControls({
      runtime: {
        sendMessage(): unknown {
          throw new Error("aborted popup control must not send");
        }
      },
      nextRequestId: () => "popup-aborted",
      abortSignal: abortController.signal
    });
    await expect(cancelled.listPendingRequests()).rejects.toThrow(/cancelled/u);
  });
});
