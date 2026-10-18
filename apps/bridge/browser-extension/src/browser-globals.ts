import {
  type BrowserExtensionBackgroundBrowserRuntimeApi
} from "./background-browser.js";
import {
  type BrowserExtensionContentRuntimeApi
} from "./content-runtime.js";
import {
  type BrowserExtensionPopupRuntimeApi
} from "./popup-control.js";
import {
  type BrowserExtensionOriginPermissionStorageArea
} from "./origin-permission-storage.js";
import {
  type BrowserExtensionPopupTabsApi
} from "./popup-tab.js";
import {
  type BrowserExtensionPopupDocument
} from "./popup-dom.js";
import {
  type BrowserExtensionContentScriptBrowserLocation,
  type BrowserExtensionContentScriptBrowserPageWindow
} from "./content-browser.js";
import {
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";
import {
  type BrowserExtensionPageScriptBrowserWindow
} from "./page-browser.js";

export type BrowserExtensionPackagedGlobalScope = {
  browser?: {
    runtime?: unknown;
    storage?: unknown;
    tabs?: unknown;
  };
  chrome?: {
    runtime?: unknown;
    storage?: unknown;
    tabs?: unknown;
  };
  document?: unknown;
  window?: unknown;
  location?: unknown;
};

export type BrowserExtensionPackagedPageWindow =
  BrowserExtensionContentScriptBrowserPageWindow &
  BrowserExtensionPageScriptBrowserWindow;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireGlobalScope(value: BrowserExtensionPackagedGlobalScope): BrowserExtensionPackagedGlobalScope {
  if (!isRecord(value)) {
    throw new Error("browser extension packaged global scope is invalid");
  }
  return value;
}

function optionalRuntimeContainer(value: unknown, label: string): unknown {
  if (value === undefined) return undefined;
  if (!isRecord(value)) {
    throw new Error(`${label} runtime container is invalid`);
  }
  return value.runtime;
}

function requireExtensionRuntimeGlobal(
  value: BrowserExtensionPackagedGlobalScope,
  label: string
): unknown {
  const globalScope = requireGlobalScope(value);
  const browserRuntime = optionalRuntimeContainer(globalScope.browser, "browser");
  const chromeRuntime = optionalRuntimeContainer(globalScope.chrome, "chrome");
  if (browserRuntime !== undefined && chromeRuntime !== undefined && browserRuntime !== chromeRuntime) {
    throw new Error(`${label} runtime global is ambiguous`);
  }
  const runtime = browserRuntime ?? chromeRuntime;
  if (runtime === undefined) {
    throw new Error(`${label} runtime global is unavailable`);
  }
  return runtime;
}

function requireRuntimeId(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._@+-]{1,128}$/u.test(value)) {
    throw new Error(`${label} runtime id is invalid`);
  }
  return value;
}

function optionalStorageContainer(value: unknown, label: string): unknown {
  if (value === undefined) return undefined;
  if (!isRecord(value)) {
    throw new Error(`${label} storage container is invalid`);
  }
  return value.storage;
}

function optionalTabsContainer(value: unknown, label: string): unknown {
  if (value === undefined) return undefined;
  if (!isRecord(value)) {
    throw new Error(`${label} tabs container is invalid`);
  }
  return value.tabs;
}

function requireExtensionStorageLocalGlobal(
  value: BrowserExtensionPackagedGlobalScope,
  label: string
): BrowserExtensionOriginPermissionStorageArea {
  const globalScope = requireGlobalScope(value);
  const browserStorage = optionalStorageContainer(globalScope.browser, "browser");
  const chromeStorage = optionalStorageContainer(globalScope.chrome, "chrome");
  if (browserStorage !== undefined && chromeStorage !== undefined && browserStorage !== chromeStorage) {
    throw new Error(`${label} storage global is ambiguous`);
  }
  const storage = browserStorage ?? chromeStorage;
  if (!isRecord(storage) || !isRecord(storage.local)) {
    throw new Error(`${label} storage global is unavailable`);
  }
  const local = storage.local;
  if (typeof local.get !== "function" || typeof local.set !== "function") {
    throw new Error(`${label} storage local global is invalid`);
  }
  if (local.remove !== undefined && typeof local.remove !== "function") {
    throw new Error(`${label} storage local remove global is invalid`);
  }
  return local as BrowserExtensionOriginPermissionStorageArea;
}

function requireExtensionTabsGlobal(
  value: BrowserExtensionPackagedGlobalScope,
  label: string
): BrowserExtensionPopupTabsApi {
  const globalScope = requireGlobalScope(value);
  const browserTabs = optionalTabsContainer(globalScope.browser, "browser");
  const chromeTabs = optionalTabsContainer(globalScope.chrome, "chrome");
  if (browserTabs !== undefined && chromeTabs !== undefined && browserTabs !== chromeTabs) {
    throw new Error(`${label} tabs global is ambiguous`);
  }
  const tabs = browserTabs ?? chromeTabs;
  if (!isRecord(tabs) || typeof tabs.query !== "function") {
    throw new Error(`${label} tabs global is unavailable`);
  }
  return tabs as BrowserExtensionPopupTabsApi;
}

export function requireBrowserExtensionBackgroundRuntimeGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionBackgroundBrowserRuntimeApi {
  const runtime = requireExtensionRuntimeGlobal(value, "browser extension background");
  if (
    !isRecord(runtime) ||
    !isRecord(runtime.onMessage) ||
    typeof runtime.onMessage.addListener !== "function" ||
    typeof runtime.onMessage.removeListener !== "function" ||
    typeof runtime.sendNativeMessage !== "function"
  ) {
    throw new Error("browser extension background runtime global is invalid");
  }
  return runtime as BrowserExtensionBackgroundBrowserRuntimeApi;
}

export function requireBrowserExtensionContentRuntimeGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionContentRuntimeApi {
  const runtime = requireExtensionRuntimeGlobal(value, "browser extension content-script");
  if (
    !isRecord(runtime) ||
    typeof runtime.getURL !== "function" ||
    typeof runtime.sendMessage !== "function"
  ) {
    throw new Error("browser extension content-script runtime global is invalid");
  }
  return runtime as BrowserExtensionContentRuntimeApi;
}

export function requireBrowserExtensionPopupRuntimeGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionPopupRuntimeApi {
  const runtime = requireExtensionRuntimeGlobal(value, "browser extension popup");
  if (!isRecord(runtime) || typeof runtime.sendMessage !== "function") {
    throw new Error("browser extension popup runtime global is invalid");
  }
  return runtime as BrowserExtensionPopupRuntimeApi;
}

export function requireBrowserExtensionRuntimeIdGlobal(
  value: BrowserExtensionPackagedGlobalScope
): string {
  const runtime = requireExtensionRuntimeGlobal(value, "browser extension");
  if (!isRecord(runtime)) {
    throw new Error("browser extension runtime global is invalid");
  }
  return requireRuntimeId(runtime.id, "browser extension");
}

export function requireBrowserExtensionOriginPermissionStorageGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionOriginPermissionStorageArea {
  const storage = requireExtensionStorageLocalGlobal(value, "browser extension origin permission");
  return {
    get(key) {
      return storage.get(key);
    },
    set(items) {
      return storage.set(items);
    },
    ...(storage.remove !== undefined
      ? {
          remove(key) {
            return storage.remove?.(key);
          }
        }
      : {})
  };
}

export function requireBrowserExtensionPopupTabsGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionPopupTabsApi {
  const tabs = requireExtensionTabsGlobal(value, "browser extension popup");
  return {
    query(queryInfo) {
      return tabs.query(queryInfo);
    }
  };
}

export function requireBrowserExtensionPopupDocumentGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionPopupDocument {
  const globalScope = requireGlobalScope(value);
  if (
    !isRecord(globalScope.document) ||
    typeof globalScope.document.createElement !== "function" ||
    typeof globalScope.document.getElementById !== "function"
  ) {
    throw new Error("browser extension popup document global is invalid");
  }
  return globalScope.document as BrowserExtensionPopupDocument;
}

export function requireBrowserExtensionDocumentGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionPageScriptDocument {
  const globalScope = requireGlobalScope(value);
  if (
    !isRecord(globalScope.document) ||
    typeof globalScope.document.createElement !== "function" ||
    typeof globalScope.document.getElementById !== "function"
  ) {
    throw new Error("browser extension document global is invalid");
  }
  return globalScope.document as BrowserExtensionPageScriptDocument;
}

export function requireBrowserExtensionPageWindowGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionPackagedPageWindow {
  const globalScope = requireGlobalScope(value);
  if (
    !isRecord(globalScope.window) ||
    typeof globalScope.window.addEventListener !== "function" ||
    typeof globalScope.window.removeEventListener !== "function" ||
    typeof globalScope.window.postMessage !== "function"
  ) {
    throw new Error("browser extension window global is invalid");
  }
  return globalScope.window as BrowserExtensionPackagedPageWindow;
}

export function requireBrowserExtensionLocationGlobal(
  value: BrowserExtensionPackagedGlobalScope
): BrowserExtensionContentScriptBrowserLocation {
  const globalScope = requireGlobalScope(value);
  if (!isRecord(globalScope.location)) {
    throw new Error("browser extension location global is invalid");
  }
  return { origin: globalScope.location.origin };
}
