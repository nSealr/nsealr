import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE,
  browserExtensionPackagedEntrypointFiles
} from "./entrypoints.js";

describe("browser extension packaged entrypoint filenames", () => {
  it("keeps packaged entrypoints distinct from internal pure module filenames", () => {
    const entrypoints = browserExtensionPackagedEntrypointFiles();

    expect(entrypoints).toEqual({
      backgroundServiceWorker: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
      contentScript: BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
      pageScript: BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
      popup: BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
      popupHtml: BROWSER_EXTENSION_POPUP_HTML_FILE
    });
    expect(new Set(Object.values(entrypoints)).size).toBe(5);
    expect(Object.values(entrypoints)).not.toContain("background.js");
    expect(Object.values(entrypoints)).not.toContain("content-script.js");
    expect(Object.values(entrypoints)).not.toContain("page-script.js");
    expect(Object.values(entrypoints)).not.toContain("popup.js");
  });
});
