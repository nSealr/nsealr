import {
  installBrowserExtensionContentScriptEntrypoint,
  type BrowserExtensionContentScriptEntrypointHandle
} from "./content-entrypoint.js";
import {
  createBrowserExtensionContentRuntimeMessageSender,
  createBrowserExtensionContentRuntimeUrlResolver,
  type BrowserExtensionContentRuntimeApi
} from "./content-runtime.js";
import {
  createBrowserExtensionContentWindowResponsePoster,
  type BrowserExtensionContentWindowEventTarget
} from "./content-window.js";
import { requireBrowserExtensionPageOrigin } from "./page-origin.js";
import {
  type BrowserExtensionPageScriptDocument
} from "./page-injection.js";

export type BrowserExtensionContentScriptBrowserPageWindow = BrowserExtensionContentWindowEventTarget & {
  postMessage(message: unknown, targetOrigin: string): void;
};

export type BrowserExtensionContentScriptBrowserLocation = {
  origin: unknown;
};

export type BrowserExtensionContentScriptBrowserEntrypointOptions = {
  document: BrowserExtensionPageScriptDocument;
  pageWindow: BrowserExtensionContentScriptBrowserPageWindow;
  location: BrowserExtensionContentScriptBrowserLocation;
  runtime: BrowserExtensionContentRuntimeApi;
  sender?: unknown;
  elementId?: string;
  scriptFile?: string;
  abortSignal?: AbortSignal;
  onError?: (error: unknown) => void;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireBrowserPageWindow(
  value: BrowserExtensionContentScriptBrowserPageWindow
): BrowserExtensionContentScriptBrowserPageWindow {
  if (
    !isRecord(value) ||
    typeof value.addEventListener !== "function" ||
    typeof value.removeEventListener !== "function" ||
    typeof value.postMessage !== "function"
  ) {
    throw new Error("browser content-script page window is invalid");
  }
  return value;
}

function requireBrowserPageOrigin(location: BrowserExtensionContentScriptBrowserLocation): string {
  if (!isRecord(location)) {
    throw new Error("browser content-script location is invalid");
  }
  return requireBrowserExtensionPageOrigin(
    location.origin,
    "browser content-script page origin is invalid"
  );
}

export function installBrowserExtensionContentScriptBrowserEntrypoint(
  options: BrowserExtensionContentScriptBrowserEntrypointOptions
): BrowserExtensionContentScriptEntrypointHandle {
  const pageWindow = requireBrowserPageWindow(options.pageWindow);
  const pageOrigin = requireBrowserPageOrigin(options.location);
  return installBrowserExtensionContentScriptEntrypoint({
    document: options.document,
    resolveExtensionUrl: createBrowserExtensionContentRuntimeUrlResolver(options.runtime),
    windowTarget: pageWindow,
    expectedSource: pageWindow,
    expectedOrigin: pageOrigin,
    sender: options.sender,
    sendRuntimeMessage: createBrowserExtensionContentRuntimeMessageSender(options.runtime),
    postResponse: createBrowserExtensionContentWindowResponsePoster(),
    ...(options.elementId !== undefined ? { elementId: options.elementId } : {}),
    ...(options.scriptFile !== undefined ? { scriptFile: options.scriptFile } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}
