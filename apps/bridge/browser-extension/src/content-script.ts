import {
  type BrowserExtensionBackgroundRequestOptions
} from "./background.js";
import { type BrowserExtensionRequest } from "./messages.js";
import {
  handleBrowserExtensionPageBridgeRequest,
  type BrowserExtensionPageBridgeResponse
} from "./page-bridge.js";

export type BrowserExtensionContentScriptBackgroundRequester = (
  request: BrowserExtensionRequest,
  sender: unknown,
  options: BrowserExtensionBackgroundRequestOptions
) => Promise<unknown> | unknown;

export type BrowserExtensionContentScriptRuntimeMessageOptions = {
  abortSignal?: AbortSignal;
};

export type BrowserExtensionContentScriptRuntimeMessageSender = (
  request: BrowserExtensionRequest,
  options: BrowserExtensionContentScriptRuntimeMessageOptions
) => Promise<unknown> | unknown;

export type BrowserExtensionContentScriptRuntimeRequesterOptions = {
  sendRuntimeMessage: BrowserExtensionContentScriptRuntimeMessageSender;
  abortSignal?: AbortSignal;
};

export type BrowserExtensionContentScriptBridgeOptions = {
  sender: unknown;
  requestBackground: BrowserExtensionContentScriptBackgroundRequester;
  abortSignal?: AbortSignal;
};

function assertNotCancelled(abortSignal: AbortSignal | undefined): void {
  if (abortSignal?.aborted === true) {
    throw new Error("browser content-script runtime request was cancelled");
  }
}

async function runWithAbortSignal<T>(
  abortSignal: AbortSignal | undefined,
  operation: (abortSignal: AbortSignal | undefined) => Promise<T> | T
): Promise<T> {
  assertNotCancelled(abortSignal);
  const operationPromise = Promise.resolve(operation(abortSignal));
  if (abortSignal === undefined) return operationPromise;

  let abortListener: (() => void) | undefined;
  const abortPromise = new Promise<T>((_resolve, reject) => {
    abortListener = () => reject(new Error("browser content-script runtime request was cancelled"));
    if (abortSignal.aborted) {
      abortListener();
      return;
    }
    abortSignal.addEventListener("abort", abortListener, { once: true });
  });
  try {
    return await Promise.race([operationPromise, abortPromise]);
  } finally {
    if (abortListener !== undefined) {
      abortSignal.removeEventListener("abort", abortListener);
    }
  }
}

async function withContentScriptAbortSignal<T>(
  first: AbortSignal | undefined,
  second: AbortSignal | undefined,
  operation: (abortSignal: AbortSignal | undefined) => Promise<T> | T
): Promise<T> {
  assertNotCancelled(first);
  assertNotCancelled(second);
  if (first === undefined || first === second) return runWithAbortSignal(second ?? first, operation);
  if (second === undefined) return runWithAbortSignal(first, operation);

  const abortController = new AbortController();
  const abort = () => abortController.abort();
  first.addEventListener("abort", abort, { once: true });
  second.addEventListener("abort", abort, { once: true });
  try {
    return await runWithAbortSignal(abortController.signal, operation);
  } finally {
    first.removeEventListener("abort", abort);
    second.removeEventListener("abort", abort);
  }
}

export function createBrowserExtensionContentScriptRuntimeRequester(
  options: BrowserExtensionContentScriptRuntimeRequesterOptions
): BrowserExtensionContentScriptBackgroundRequester {
  return (request, _sender, requestOptions) => withContentScriptAbortSignal(
    options.abortSignal,
    requestOptions.nativeMessageAbortSignal,
    (abortSignal) => options.sendRuntimeMessage(request, {
      ...(abortSignal !== undefined ? { abortSignal } : {})
    })
  );
}

export async function handleBrowserExtensionContentScriptBridgeMessage(
  value: unknown,
  options: BrowserExtensionContentScriptBridgeOptions
): Promise<BrowserExtensionPageBridgeResponse> {
  return handleBrowserExtensionPageBridgeRequest(value, {
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {}),
    requestBackground: (request, requestOptions) => options.requestBackground(request, options.sender, {
      ...(requestOptions.abortSignal !== undefined
        ? { nativeMessageAbortSignal: requestOptions.abortSignal }
        : {})
    })
  });
}
