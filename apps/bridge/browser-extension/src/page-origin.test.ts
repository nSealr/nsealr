import { describe, expect, it } from "vitest";
import {
  normalizeBrowserExtensionPageOrigin,
  requireBrowserExtensionPageOrigin
} from "./page-origin.js";

describe("browser extension page origin validation", () => {
  it("accepts HTTPS and local HTTP page origins", () => {
    expect(normalizeBrowserExtensionPageOrigin("https://example.com")).toBe("https://example.com");
    expect(normalizeBrowserExtensionPageOrigin("https://sub.example.com:8443")).toBe("https://sub.example.com:8443");
    expect(normalizeBrowserExtensionPageOrigin("http://localhost:5173")).toBe("http://localhost:5173");
    expect(normalizeBrowserExtensionPageOrigin("http://127.0.0.1:5173")).toBe("http://127.0.0.1:5173");
  });

  it("rejects non-origin URLs and unsupported page origins", () => {
    for (const value of [
      "",
      "https://example.com/path",
      "https://example.com?query=1",
      "http://example.com",
      "ftp://example.com",
      "chrome-extension://extension-id",
      "not a url",
      "https://example.com".padEnd(257, "a")
    ]) {
      expect(normalizeBrowserExtensionPageOrigin(value)).toBeUndefined();
    }
  });

  it("throws caller-specific errors for required page origins", () => {
    expect(requireBrowserExtensionPageOrigin("https://example.com", "custom page origin error")).toBe(
      "https://example.com"
    );
    expect(() => requireBrowserExtensionPageOrigin(
      "https://example.com/path",
      "custom page origin error"
    )).toThrow(/custom page origin error/u);
  });
});
