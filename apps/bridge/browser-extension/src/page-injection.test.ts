import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
  BROWSER_EXTENSION_PAGE_SCRIPT_FILE,
  injectBrowserExtensionPageScript,
  type BrowserExtensionInjectedPageScriptElement,
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";

function createInjectedDocument(options: {
  existingElementIds?: string[];
  parentAvailable?: boolean;
} = {}): {
  document: BrowserExtensionPageScriptDocument;
  appended: BrowserExtensionInjectedPageScriptElement[];
  removed: BrowserExtensionInjectedPageScriptElement[];
} {
  const existingElementIds = new Set(options.existingElementIds ?? []);
  const appended: BrowserExtensionInjectedPageScriptElement[] = [];
  const removed: BrowserExtensionInjectedPageScriptElement[] = [];
  const document: BrowserExtensionPageScriptDocument = {
    createElement(tagName: "script"): BrowserExtensionInjectedPageScriptElement {
      expect(tagName).toBe("script");
      return {
        id: "",
        type: "",
        async: true,
        src: "",
        remove(): void {
          removed.push(this);
        }
      };
    },
    getElementById(id: string): unknown {
      return existingElementIds.has(id) ? { id } : null;
    },
    ...(options.parentAvailable === false
      ? {}
      : {
          documentElement: {
            appendChild(element: BrowserExtensionInjectedPageScriptElement): unknown {
              appended.push(element);
              return element;
            }
          }
        })
  };
  return { document, appended, removed };
}

describe("browser extension page-script injection boundary", () => {
  it("injects the reviewed page script resource through explicit document and URL dependencies", () => {
    const injectedDocument = createInjectedDocument();
    const handle = injectBrowserExtensionPageScript({
      document: injectedDocument.document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`
    });

    expect(injectedDocument.appended).toHaveLength(1);
    expect(handle.element).toBe(injectedDocument.appended[0]);
    expect(handle.element).toEqual(expect.objectContaining({
      id: BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID,
      type: "module",
      async: false,
      src: `chrome-extension://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`
    }));
    expect(injectedDocument.removed).toEqual([]);

    handle.dispose();
    handle.dispose();
    expect(injectedDocument.removed).toEqual([handle.element]);
  });

  it("rejects duplicate or ambiguous injection targets before creating a script", () => {
    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument({
        existingElementIds: [BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID]
      }).document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`
    })).toThrow(/already exists/u);

    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument().document,
      elementId: "1-invalid",
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`
    })).toThrow(/element id/u);

    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument({
        parentAvailable: false
      }).document,
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`
    })).toThrow(/parent/u);
  });

  it("rejects unsafe script files and resolved URLs", () => {
    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument().document,
      scriptFile: "../page-script.js",
      resolveExtensionUrl: (path) => `chrome-extension://extension-id/${path}`
    })).toThrow(/file/u);

    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument().document,
      resolveExtensionUrl: (path) => `https://example.com/${path}`
    })).toThrow(/protocol/u);

    expect(() => injectBrowserExtensionPageScript({
      document: createInjectedDocument().document,
      resolveExtensionUrl: () => "chrome-extension://extension-id/other.js"
    })).toThrow(/path/u);
  });

  it("supports Firefox and Safari extension URL schemes without broad URL access", () => {
    for (const protocol of ["moz-extension", "safari-web-extension"]) {
      const injectedDocument = createInjectedDocument();
      const handle = injectBrowserExtensionPageScript({
        document: injectedDocument.document,
        resolveExtensionUrl: (path) => `${protocol}://extension-id/${path}`
      });
      expect(handle.element.src).toBe(`${protocol}://extension-id/${BROWSER_EXTENSION_PAGE_SCRIPT_FILE}`);
    }
  });
});
