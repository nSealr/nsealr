import {
  installBrowserExtensionContentScriptBrowserEntrypoint,
  type BrowserExtensionContentScriptBrowserEntrypointOptions
} from "./content-browser.js";
import {
  type BrowserExtensionContentScriptEntrypointHandle
} from "./content-entrypoint.js";
import {
  requireBrowserExtensionContentRuntimeGlobal,
  requireBrowserExtensionDocumentGlobal,
  requireBrowserExtensionLocationGlobal,
  requireBrowserExtensionPageWindowGlobal,
  type BrowserExtensionPackagedGlobalScope
} from "./browser-globals.js";

export type NsealrContentScriptEntrypointOptions = Omit<
  BrowserExtensionContentScriptBrowserEntrypointOptions,
  "document" | "pageWindow" | "location" | "runtime"
> & {
  globalScope: BrowserExtensionPackagedGlobalScope;
};

export function installNsealrContentScriptEntrypoint(
  options: NsealrContentScriptEntrypointOptions
): BrowserExtensionContentScriptEntrypointHandle {
  return installBrowserExtensionContentScriptBrowserEntrypoint({
    document: requireBrowserExtensionDocumentGlobal(options.globalScope),
    pageWindow: requireBrowserExtensionPageWindowGlobal(options.globalScope),
    location: requireBrowserExtensionLocationGlobal(options.globalScope),
    runtime: requireBrowserExtensionContentRuntimeGlobal(options.globalScope),
    ...(options.sender !== undefined ? { sender: options.sender } : {}),
    ...(options.elementId !== undefined ? { elementId: options.elementId } : {}),
    ...(options.scriptFile !== undefined ? { scriptFile: options.scriptFile } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}
