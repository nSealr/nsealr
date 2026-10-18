import { BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE } from "./entrypoints.js";

export const BROWSER_EXTENSION_PAGE_SCRIPT_FILE = BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE;
export const BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID = "nsealr-page-script";

export type BrowserExtensionInjectedPageScriptElement = {
  id: string;
  type: string;
  async: boolean;
  src: string;
  remove(): void;
};

export type BrowserExtensionPageScriptParent = {
  appendChild(element: BrowserExtensionInjectedPageScriptElement): unknown;
};

export type BrowserExtensionPageScriptDocument = {
  createElement(tagName: "script"): BrowserExtensionInjectedPageScriptElement;
  getElementById(id: string): unknown;
  documentElement?: BrowserExtensionPageScriptParent | null;
  head?: BrowserExtensionPageScriptParent | null;
};

export type BrowserExtensionPageScriptUrlResolver = (path: string) => string;

export type BrowserExtensionPageScriptInjectionOptions = {
  document: BrowserExtensionPageScriptDocument;
  resolveExtensionUrl: BrowserExtensionPageScriptUrlResolver;
  elementId?: string;
  scriptFile?: string;
};

export type BrowserExtensionPageScriptInjectionHandle = {
  element: BrowserExtensionInjectedPageScriptElement;
  dispose(): void;
};

function requireElementId(value: string | undefined): string {
  const elementId = value ?? BROWSER_EXTENSION_PAGE_SCRIPT_ELEMENT_ID;
  if (!/^[A-Za-z][A-Za-z0-9._:-]{0,127}$/u.test(elementId)) {
    throw new Error("browser page-script injection element id is invalid");
  }
  return elementId;
}

function requireScriptFile(value: string | undefined): string {
  const scriptFile = value ?? BROWSER_EXTENSION_PAGE_SCRIPT_FILE;
  if (!/^[A-Za-z0-9._-]{1,64}\.js$/u.test(scriptFile)) {
    throw new Error("browser page-script injection file is invalid");
  }
  return scriptFile;
}

function requireExtensionScriptUrl(value: string, scriptFile: string): string {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("browser page-script injection URL is invalid");
  }
  if (!["chrome-extension:", "moz-extension:", "safari-web-extension:"].includes(url.protocol)) {
    throw new Error("browser page-script injection URL protocol is unsupported");
  }
  if (!url.pathname.endsWith(`/${scriptFile}`)) {
    throw new Error("browser page-script injection URL path is invalid");
  }
  return url.toString();
}

function requireParent(document: BrowserExtensionPageScriptDocument): BrowserExtensionPageScriptParent {
  const parent = document.documentElement ?? document.head;
  if (parent === undefined || parent === null) {
    throw new Error("browser page-script injection parent is unavailable");
  }
  return parent;
}

export function injectBrowserExtensionPageScript(
  options: BrowserExtensionPageScriptInjectionOptions
): BrowserExtensionPageScriptInjectionHandle {
  const elementId = requireElementId(options.elementId);
  const scriptFile = requireScriptFile(options.scriptFile);
  if (options.document.getElementById(elementId) !== null) {
    throw new Error("browser page-script injection element already exists");
  }
  const scriptUrl = requireExtensionScriptUrl(options.resolveExtensionUrl(scriptFile), scriptFile);
  const element = options.document.createElement("script");
  element.id = elementId;
  element.type = "module";
  element.async = false;
  element.src = scriptUrl;
  requireParent(options.document).appendChild(element);

  let disposed = false;
  return Object.freeze({
    element,
    dispose(): void {
      if (disposed) return;
      disposed = true;
      element.remove();
    }
  });
}
