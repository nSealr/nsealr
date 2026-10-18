import {
  installBrowserExtensionContentScriptRuntimeBridge
} from "./content-bootstrap.js";
import {
  type BrowserExtensionContentScriptRuntimeMessageSender
} from "./content-script.js";
import {
  type BrowserExtensionContentWindowEventTarget,
  type BrowserExtensionContentWindowListenerHandle,
  type BrowserExtensionContentWindowResponsePoster
} from "./content-window.js";
import {
  injectBrowserExtensionPageScript,
  type BrowserExtensionPageScriptDocument,
  type BrowserExtensionPageScriptInjectionHandle,
  type BrowserExtensionPageScriptUrlResolver
} from "./page-injection.js";

export type BrowserExtensionContentScriptEntrypointInstallOptions = {
  document: BrowserExtensionPageScriptDocument;
  resolveExtensionUrl: BrowserExtensionPageScriptUrlResolver;
  windowTarget: BrowserExtensionContentWindowEventTarget;
  expectedSource: unknown;
  expectedOrigin: string;
  sender: unknown;
  sendRuntimeMessage: BrowserExtensionContentScriptRuntimeMessageSender;
  postResponse: BrowserExtensionContentWindowResponsePoster;
  elementId?: string;
  scriptFile?: string;
  abortSignal?: AbortSignal;
  onError?: (error: unknown) => void;
};

export type BrowserExtensionContentScriptEntrypointHandle = {
  pageScript: BrowserExtensionPageScriptInjectionHandle;
  runtimeBridge: BrowserExtensionContentWindowListenerHandle;
  dispose(): void;
};

export function installBrowserExtensionContentScriptEntrypoint(
  options: BrowserExtensionContentScriptEntrypointInstallOptions
): BrowserExtensionContentScriptEntrypointHandle {
  const pageScript = injectBrowserExtensionPageScript({
    document: options.document,
    resolveExtensionUrl: options.resolveExtensionUrl,
    ...(options.elementId !== undefined ? { elementId: options.elementId } : {}),
    ...(options.scriptFile !== undefined ? { scriptFile: options.scriptFile } : {})
  });

  let runtimeBridge: BrowserExtensionContentWindowListenerHandle;
  try {
    runtimeBridge = installBrowserExtensionContentScriptRuntimeBridge({
      target: options.windowTarget,
      expectedSource: options.expectedSource,
      expectedOrigin: options.expectedOrigin,
      sender: options.sender,
      sendRuntimeMessage: options.sendRuntimeMessage,
      postResponse: options.postResponse,
      ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
      ...(options.onError !== undefined ? { onError: options.onError } : {})
    });
  } catch (error) {
    pageScript.dispose();
    throw error;
  }

  let disposed = false;
  return Object.freeze({
    pageScript,
    runtimeBridge,
    dispose(): void {
      if (disposed) return;
      disposed = true;
      runtimeBridge.dispose();
      pageScript.dispose();
    }
  });
}
