import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_MESSAGE_PROTOCOL,
  browserExtensionErrorResponse,
  parseBrowserExtensionRequest
} from "./messages.js";

const eventTemplate = {
  kind: 1,
  created_at: 1_710_000_000,
  tags: [],
  content: "browser extension message test"
};

describe("browser extension message boundary", () => {
  it("parses get_public_key requests without granting extra methods", () => {
    expect(parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-get-pubkey-1",
      method: "get_public_key"
    })).toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-get-pubkey-1",
      method: "get_public_key"
    });

    expect(() => parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-nip44-1",
      method: "nip44_encrypt"
    })).toThrow(/method is unsupported/u);
  });

  it("parses sign_event requests through the shared signer-request validator", () => {
    expect(parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sign-event-1",
      method: "sign_event",
      params: { event_template: eventTemplate }
    })).toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sign-event-1",
      method: "sign_event",
      params: { event_template: eventTemplate }
    });

    expect(() => parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-sign-event-unsafe",
      method: "sign_event",
      params: {
        event_template: {
          ...eventTemplate,
          pubkey: "0".repeat(64)
        }
      }
    })).toThrow(/forbidden fields/u);
  });

  it("rejects malformed envelopes before background logic can route them", () => {
    expect(() => parseBrowserExtensionRequest({
      protocol: "other-protocol",
      version: 1,
      request_id: "browser-bad-protocol",
      method: "get_public_key"
    })).toThrow(/protocol/u);
    expect(() => parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "bad request id",
      method: "get_public_key"
    })).toThrow(/request_id/u);
    expect(() => parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-extra-field",
      method: "get_public_key",
      origin: "https://example.com"
    })).toThrow(/unsupported fields/u);
    expect(() => parseBrowserExtensionRequest({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-get-pubkey-params",
      method: "get_public_key",
      params: {}
    })).toThrow(/must not include params/u);
  });

  it("creates deterministic secretless error responses", () => {
    expect(browserExtensionErrorResponse(
      "browser-error-1",
      "native_host_unavailable",
      "native host is not connected"
    )).toEqual({
      protocol: BROWSER_EXTENSION_MESSAGE_PROTOCOL,
      version: 1,
      request_id: "browser-error-1",
      ok: false,
      error: {
        code: "native_host_unavailable",
        message: "native host is not connected",
        retryable: false
      }
    });
    expect(() => browserExtensionErrorResponse(
      "browser-error-2",
      "Bad Code",
      "native host is not connected"
    )).toThrow(/error code/u);
    expect(() => browserExtensionErrorResponse(
      "browser-error-3",
      "native_host_unavailable",
      ""
    )).toThrow(/error message/u);
  });
});
