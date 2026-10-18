export const BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE = "nsealr-background-entrypoint.js";
export const BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE = "nsealr-content-script-entrypoint.js";
export const BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE = "nsealr-page-script-entrypoint.js";
export const BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE = "nsealr-popup-entrypoint.js";
export const BROWSER_EXTENSION_POPUP_HTML_FILE = "nsealr-popup.html";

const INTERNAL_MODULE_FILENAMES = new Set([
  "background.js",
  "content-script.js",
  "page-script.js",
  "popup.js"
]);

function requirePackagedFilename(value: string, label: string): string {
  if (!/^[A-Za-z0-9._-]{1,64}\.(?:html|js)$/u.test(value)) {
    throw new Error(`${label} is invalid`);
  }
  if (INTERNAL_MODULE_FILENAMES.has(value)) {
    throw new Error(`${label} collides with an internal browser-extension module`);
  }
  return value;
}

export type BrowserExtensionPackagedEntrypointFiles = {
  backgroundServiceWorker: typeof BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE;
  contentScript: typeof BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE;
  pageScript: typeof BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE;
  popup: typeof BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE;
  popupHtml: typeof BROWSER_EXTENSION_POPUP_HTML_FILE;
};

export function browserExtensionPackagedEntrypointFiles(): BrowserExtensionPackagedEntrypointFiles {
  const backgroundServiceWorker = requirePackagedFilename(
    BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
    "browser extension background entrypoint file"
  ) as typeof BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE;
  const contentScript = requirePackagedFilename(
    BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
    "browser extension content-script entrypoint file"
  ) as typeof BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE;
  const pageScript = requirePackagedFilename(
    BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
    "browser extension page-script entrypoint file"
  ) as typeof BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE;
  const popup = requirePackagedFilename(
    BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE,
    "browser extension popup entrypoint file"
  ) as typeof BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE;
  const popupHtml = requirePackagedFilename(
    BROWSER_EXTENSION_POPUP_HTML_FILE,
    "browser extension popup html file"
  ) as typeof BROWSER_EXTENSION_POPUP_HTML_FILE;

  if (new Set([backgroundServiceWorker, contentScript, pageScript, popup, popupHtml]).size !== 5) {
    throw new Error("browser extension packaged entrypoint files must be unique");
  }
  return Object.freeze({
    backgroundServiceWorker,
    contentScript,
    pageScript,
    popup,
    popupHtml
  });
}
