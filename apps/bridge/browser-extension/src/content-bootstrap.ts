import {
  createBrowserExtensionContentScriptRuntimeRequester,
  type BrowserExtensionContentScriptRuntimeMessageSender
} from "./content-script.js";
import {
  installBrowserExtensionContentWindowBridgeListener,
  type BrowserExtensionContentWindowEventTarget,
  type BrowserExtensionContentWindowListenerHandle,
  type BrowserExtensionContentWindowResponsePoster
} from "./content-window.js";

export type BrowserExtensionContentScriptRuntimeBridgeInstallOptions = {
  target: BrowserExtensionContentWindowEventTarget;
  expectedSource: unknown;
  expectedOrigin: string;
  sender: unknown;
  sendRuntimeMessage: BrowserExtensionContentScriptRuntimeMessageSender;
  postResponse: BrowserExtensionContentWindowResponsePoster;
  abortSignal?: AbortSignal;
  onError?: (error: unknown) => void;
};

export function installBrowserExtensionContentScriptRuntimeBridge(
  options: BrowserExtensionContentScriptRuntimeBridgeInstallOptions
): BrowserExtensionContentWindowListenerHandle {
  return installBrowserExtensionContentWindowBridgeListener({
    target: options.target,
    expectedSource: options.expectedSource,
    expectedOrigin: options.expectedOrigin,
    sender: options.sender,
    requestBackground: createBrowserExtensionContentScriptRuntimeRequester({
      sendRuntimeMessage: options.sendRuntimeMessage,
      ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
    }),
    postResponse: options.postResponse,
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}
