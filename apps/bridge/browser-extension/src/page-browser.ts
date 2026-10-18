import { requireBrowserExtensionPageOrigin } from "./page-origin.js";
import {
  installBrowserExtensionPageScriptWindowProvider
} from "./page-script.js";
import {
  type BrowserExtensionPageProvider,
  type BrowserExtensionPageProviderTarget
} from "./page-provider.js";
import {
  type BrowserExtensionPageWindowTarget
} from "./page-window.js";

export type BrowserExtensionPageScriptBrowserWindow =
  BrowserExtensionPageProviderTarget &
  BrowserExtensionPageWindowTarget;

export type BrowserExtensionPageScriptBrowserLocation = {
  origin: unknown;
};

export type BrowserExtensionPageScriptBrowserProviderOptions = {
  pageWindow: BrowserExtensionPageScriptBrowserWindow;
  location: BrowserExtensionPageScriptBrowserLocation;
  nextRequestId?: () => string;
  abortSignal?: AbortSignal;
  responseTimeoutMs?: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireBrowserPageWindow(
  value: BrowserExtensionPageScriptBrowserWindow
): BrowserExtensionPageScriptBrowserWindow {
  if (
    !isRecord(value) ||
    typeof value.addEventListener !== "function" ||
    typeof value.removeEventListener !== "function" ||
    typeof value.postMessage !== "function"
  ) {
    throw new Error("browser page-script window is invalid");
  }
  return value;
}

function requireBrowserPageOrigin(location: BrowserExtensionPageScriptBrowserLocation): string {
  if (!isRecord(location)) {
    throw new Error("browser page-script location is invalid");
  }
  return requireBrowserExtensionPageOrigin(
    location.origin,
    "browser page-script origin is invalid"
  );
}

export function installBrowserExtensionPageScriptBrowserProvider(
  options: BrowserExtensionPageScriptBrowserProviderOptions
): BrowserExtensionPageProvider {
  const pageWindow = requireBrowserPageWindow(options.pageWindow);
  const pageOrigin = requireBrowserPageOrigin(options.location);
  return installBrowserExtensionPageScriptWindowProvider({
    providerTarget: pageWindow,
    windowTarget: pageWindow,
    expectedSource: pageWindow,
    expectedOrigin: pageOrigin,
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    ...(options.responseTimeoutMs !== undefined ? { responseTimeoutMs: options.responseTimeoutMs } : {})
  });
}
