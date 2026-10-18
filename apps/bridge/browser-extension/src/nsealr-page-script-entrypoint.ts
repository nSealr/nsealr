import {
  installBrowserExtensionPageScriptBrowserProvider,
  type BrowserExtensionPageScriptBrowserProviderOptions
} from "./page-browser.js";
import {
  type BrowserExtensionPageProvider
} from "./page-provider.js";
import {
  requireBrowserExtensionLocationGlobal,
  requireBrowserExtensionPageWindowGlobal,
  type BrowserExtensionPackagedGlobalScope
} from "./browser-globals.js";

export type NsealrPageScriptEntrypointOptions = Omit<
  BrowserExtensionPageScriptBrowserProviderOptions,
  "pageWindow" | "location"
> & {
  globalScope: BrowserExtensionPackagedGlobalScope;
};

export function installNsealrPageScriptEntrypoint(
  options: NsealrPageScriptEntrypointOptions
): BrowserExtensionPageProvider {
  return installBrowserExtensionPageScriptBrowserProvider({
    pageWindow: requireBrowserExtensionPageWindowGlobal(options.globalScope),
    location: requireBrowserExtensionLocationGlobal(options.globalScope),
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    ...(options.responseTimeoutMs !== undefined ? { responseTimeoutMs: options.responseTimeoutMs } : {})
  });
}
