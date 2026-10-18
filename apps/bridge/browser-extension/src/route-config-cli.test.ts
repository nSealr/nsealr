import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import {
  browserExtensionRouteConfigApprovalJsonFromArgs,
  browserExtensionRouteConfigReviewJsonFromArgs
} from "./route-config-cli.js";
import {
  BROWSER_EXTENSION_ROUTE_CONFIG_APPROVAL_FORMAT,
  BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT
} from "./route-config.js";

describe("browser extension route-config CLI", () => {
  it("renders review and approval artifacts without writing extension storage", () => {
    const temp = mkdtempSync(join(tmpdir(), "nsealr-route-config-cli-"));
    try {
      const review = JSON.parse(browserExtensionRouteConfigReviewJsonFromArgs([
        "--route-account-id",
        "esp32-usb-slot-0",
        "--route-type",
        "esp32_usb_nip46"
      ]));
      expect(review).toEqual({
        format: BROWSER_EXTENSION_ROUTE_CONFIG_REVIEW_FORMAT,
        route_config_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
        route_config: {
          format: "nsealr-browser-extension-route-config-v0",
          account_id: "esp32-usb-slot-0",
          route_type: "esp32_usb_nip46"
        },
        route_request: {
          account_id: "esp32-usb-slot-0",
          method: "sign_event",
          route_type: "esp32_usb_nip46"
        },
        requires_user_approval: true,
        writes_extension_storage: false,
        creates_grants: false,
        dispatches_signers: false,
        stores_production_secrets: false
      });

      const reviewPath = join(temp, "route-review.json");
      writeFileSync(reviewPath, `${JSON.stringify(review, null, 2)}\n`, "utf8");
      expect(JSON.parse(browserExtensionRouteConfigApprovalJsonFromArgs([
        "--review",
        reviewPath,
        "--reviewed-route-config-digest",
        review.route_config_digest,
        "--approved-at",
        "1900000000"
      ]))).toEqual({
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
    } finally {
      rmSync(temp, { recursive: true, force: true });
    }
  });

  it("rejects malformed review and approval options", () => {
    expect(() => browserExtensionRouteConfigReviewJsonFromArgs([
      "--route-account-id",
      "bad account id",
      "--route-type",
      "esp32_usb_nip46"
    ])).toThrow(/account_id/u);
    expect(() => browserExtensionRouteConfigReviewJsonFromArgs([
      "--route-account-id",
      "esp32-usb-slot-0"
    ])).toThrow(/route-type/u);
    expect(() => browserExtensionRouteConfigReviewJsonFromArgs([
      "--route-account-id",
      "esp32-usb-slot-0",
      "--route-type",
      "esp32_qr_vault"
    ])).toThrow(/browser-dispatchable/u);
    expect(() => browserExtensionRouteConfigReviewJsonFromArgs([
      "--review",
      "/tmp/review.json"
    ])).toThrow(/only supported/u);
    expect(() => browserExtensionRouteConfigApprovalJsonFromArgs([
      "--review",
      "/tmp/missing-review.json",
      "--reviewed-route-config-digest",
      "not-hex",
      "--approved-at",
      "1900000000"
    ])).toThrow(/reviewed-route-config-digest/u);
    expect(() => browserExtensionRouteConfigApprovalJsonFromArgs([
      "--review",
      "/tmp/missing-review.json",
      "--reviewed-route-config-digest",
      "0".repeat(64),
      "--approved-at",
      "9007199254740992"
    ])).toThrow(/approved-at/u);
  });
});
