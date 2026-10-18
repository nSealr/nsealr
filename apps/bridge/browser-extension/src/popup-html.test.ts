import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";
import {
  BROWSER_EXTENSION_POPUP_LIST_ID,
  BROWSER_EXTENSION_POPUP_REFRESH_ID,
  BROWSER_EXTENSION_POPUP_ROOT_ID,
  BROWSER_EXTENSION_POPUP_STATUS_ID,
  browserExtensionPopupHtml
} from "./popup-html.js";

describe("browser extension popup HTML", () => {
  it("renders a deterministic popup document without external assets", () => {
    const html = browserExtensionPopupHtml();

    expect(html).toContain("<!doctype html>");
    expect(html).toContain(`id="${BROWSER_EXTENSION_POPUP_ROOT_ID}"`);
    expect(html).toContain(`id="${BROWSER_EXTENSION_POPUP_STATUS_ID}"`);
    expect(html).toContain(`id="${BROWSER_EXTENSION_POPUP_LIST_ID}"`);
    expect(html).toContain(`id="${BROWSER_EXTENSION_POPUP_REFRESH_ID}"`);
    expect(html).toContain(`src="${BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE}"`);
    expect(html).not.toContain("http://");
    expect(html).not.toContain("https://");
    expect(BROWSER_EXTENSION_POPUP_HTML_FILE).toBe("nsealr-popup.html");
  });
});
