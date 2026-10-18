import { type Nip07Provider } from "@nsealr/browser-provider";
import {
  createBrowserExtensionPageBridgeBackgroundRequester,
  type BrowserExtensionPageBridgeMessageExchange
} from "./page-bridge.js";
import {
  createBrowserExtensionPageProvider,
  installBrowserExtensionPageProvider,
  type BrowserExtensionPageProviderTarget
} from "./page-provider.js";
import {
  createBrowserExtensionPageWindowBridgeExchange,
  type BrowserExtensionPageWindowTarget
} from "./page-window.js";

export type BrowserExtensionPageScriptInstallOptions = {
  target: BrowserExtensionPageProviderTarget;
  exchangeBridgeMessage: BrowserExtensionPageBridgeMessageExchange;
  nextRequestId?: () => string;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionPageScriptWindowInstallOptions = {
  providerTarget: BrowserExtensionPageProviderTarget;
  windowTarget: BrowserExtensionPageWindowTarget;
  expectedSource: unknown;
  expectedOrigin: string;
  nextRequestId?: () => string;
  abortSignal?: AbortSignal;
  responseTimeoutMs?: number;
};

export function installBrowserExtensionPageScriptProvider(
  options: BrowserExtensionPageScriptInstallOptions
): Nip07Provider {
  const requestBackground = createBrowserExtensionPageBridgeBackgroundRequester({
    exchangeBridgeMessage: options.exchangeBridgeMessage,
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
  const provider = createBrowserExtensionPageProvider({
    requestBackground,
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
  return installBrowserExtensionPageProvider(options.target, provider);
}

export function installBrowserExtensionPageScriptWindowProvider(
  options: BrowserExtensionPageScriptWindowInstallOptions
): Nip07Provider {
  return installBrowserExtensionPageScriptProvider({
    target: options.providerTarget,
    exchangeBridgeMessage: createBrowserExtensionPageWindowBridgeExchange({
      target: options.windowTarget,
      expectedSource: options.expectedSource,
      expectedOrigin: options.expectedOrigin,
      ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
      ...(options.responseTimeoutMs !== undefined ? { responseTimeoutMs: options.responseTimeoutMs } : {})
    }),
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
}
