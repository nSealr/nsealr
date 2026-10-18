import { describe, expect, it } from "vitest";
import { browserExtensionClientContextFromSender } from "./sender.js";

describe("browser extension sender boundary", () => {
  it("derives a local client identity from explicit page origin", () => {
    expect(browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      app_name: "Reviewed Browser Extension"
    })).toEqual({
      client: {
        surface: "browser_extension",
        origin: "https://example.com",
        app_name: "Reviewed Browser Extension",
        instance_id: "extension@nsealr.dev"
      },
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      origin_source: "page_origin",
      stores_browser_secrets: false
    });
  });

  it("derives page origin from a full page URL without using the URL as identity", () => {
    expect(browserExtensionClientContextFromSender({
      extension_id: "abcdefghijklmnopabcdefghijklmnop",
      page_url: "https://example.com/path?query=1#fragment"
    })).toEqual({
      client: {
        surface: "browser_extension",
        origin: "https://example.com",
        app_name: "nSealr Browser Extension",
        instance_id: "abcdefghijklmnopabcdefghijklmnop"
      },
      extension_id: "abcdefghijklmnopabcdefghijklmnop",
      page_origin: "https://example.com",
      origin_source: "page_url",
      stores_browser_secrets: false
    });
  });

  it("accepts localhost development origins but rejects deceptive localhost names", () => {
    expect(browserExtensionClientContextFromSender({
      extension_id: "dev-extension",
      page_url: "http://localhost:8080/app"
    }).client.origin).toBe("http://localhost:8080");
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "dev-extension",
      page_url: "http://localhost.evil.example/app"
    })).toThrow(/origin scheme/u);
  });

  it("rejects ambiguous or unsupported sender context before pairing", () => {
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      page_url: "https://other.example/path"
    })).toThrow(/does not match/u);
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com/path"
    })).toThrow(/origin scheme/u);
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: 42
    })).toThrow(/page origin/u);
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    })).toThrow(/origin scheme/u);
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "bad extension id",
      page_origin: "https://example.com"
    })).toThrow(/extension id/u);
    expect(() => browserExtensionClientContextFromSender({
      extension_id: "extension@nsealr.dev",
      page_origin: "https://example.com",
      tab_id: 1
    })).toThrow(/unsupported fields/u);
  });
});
