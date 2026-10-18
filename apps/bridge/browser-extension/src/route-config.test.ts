import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT,
  BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
  BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
  BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT,
  approveBrowserExtensionRouteConfigReview,
  createBrowserExtensionRouteConfigReview,
  parseBrowserExtensionRouteConfig,
  parseBrowserExtensionRouteConfigApproval,
  parseBrowserExtensionRouteConfigReview
} from "./route-config.js";

describe("browser extension selected-route config", () => {
  it("parses a secretless selected account route into a sign_event route request", () => {
    expect(parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "esp32-usb-slot-0",
      route_type: "esp32_usb_nip46"
    })).toEqual({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      route_config: {
        format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
        account_id: "esp32-usb-slot-0",
        route_type: "esp32_usb_nip46"
      },
      route_request: {
        account_id: "esp32-usb-slot-0",
        method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
        route_type: "esp32_usb_nip46"
      },
      stores_production_secrets: false
    });
  });

  it("rejects malformed, unsupported, or secret-looking route config fields", () => {
    expect(() => parseBrowserExtensionRouteConfig(null)).toThrow(/object/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "selected-account"
    })).toThrow(/route_type is required/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: "nsealr-wrong-format",
      account_id: "selected-account"
    })).toThrow(/format/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "selected-account",
      route_type: "unknown"
    })).toThrow(/route_type/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "selected-account",
      route_type: "raspberry_qr_vault"
    })).toThrow(/not browser-dispatchable/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "selected-account",
      route_type: "smartcard"
    })).toThrow(/not browser-dispatchable/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "selected-account",
      nsec: "nsec1..."
    })).toThrow(/unsupported fields/u);
    expect(() => parseBrowserExtensionRouteConfig({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "",
      route_type: "esp32_usb_nip46"
    })).toThrow(/account_id/u);
  });

  it("creates digest-bound route config review and approval artifacts", () => {
    const routeConfig = {
      format: BROWSER_EXTENSION_ROUTE_CONFIG_FORMAT,
      account_id: "esp32-usb-slot-0",
      route_type: "esp32_usb_nip46"
    };
    const review = createBrowserExtensionRouteConfigReview(routeConfig);
    expect(review).toEqual({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT,
      route_config_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
      route_config: routeConfig,
      route_request: {
        account_id: "esp32-usb-slot-0",
        method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
        route_type: "esp32_usb_nip46"
      },
      requires_user_approval: true,
      writes_extension_storage: false,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false
    });
    expect(parseBrowserExtensionRouteConfigReview(review)).toEqual(review);
    expect(parseBrowserExtensionRouteConfigReview({
      ...review,
      route_request: {
        route_type: "esp32_usb_nip46",
        method: BROWSER_EXTENSION_ROUTE_CONFIG_METHOD,
        account_id: "esp32-usb-slot-0"
      }
    })).toEqual(review);

    const approval = approveBrowserExtensionRouteConfigReview(review, {
      reviewedRouteConfigDigest: review.route_config_digest,
      approvedAt: 1_900_000_000
    });
    expect(approval).toEqual({
      format: BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT,
      route_config_digest: review.route_config_digest,
      approved_at: 1_900_000_000,
      review,
      requires_user_approval: true,
      writes_extension_storage: false,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false
    });
    expect(parseBrowserExtensionRouteConfigApproval(approval)).toEqual(approval);
    expect(() => approveBrowserExtensionRouteConfigReview(review, {
      reviewedRouteConfigDigest: "0".repeat(64),
      approvedAt: 1_900_000_000
    })).toThrow(/digest does not match/u);
    expect(() => parseBrowserExtensionRouteConfigReview({
      ...review,
      route_request: {
        ...review.route_request,
        account_id: "other-account"
      }
    })).toThrow(/route request mismatch/u);
    expect(() => parseBrowserExtensionRouteConfigApproval({
      ...approval,
      writes_extension_storage: true
    })).toThrow(/extension storage/u);
  });
});
