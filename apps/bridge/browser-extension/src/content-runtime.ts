import {
  type BrowserExtensionContentScriptRuntimeMessageOptions,
  type BrowserExtensionContentScriptRuntimeMessageSender
} from "./content-script.js";
import { type BrowserExtensionPageScriptUrlResolver } from "./page-injection.js";

export type BrowserExtensionContentRuntimeApi = {
  getURL(path: string): string;
  sendMessage(message: unknown): Promise<unknown> | unknown;
};

function requireRuntimeApi(value: BrowserExtensionContentRuntimeApi): BrowserExtensionContentRuntimeApi {
  if (typeof value !== "object" || value === null || typeof value.getURL !== "function") {
    throw new Error("browser content runtime getURL is unavailable");
  }
  if (typeof value.sendMessage !== "function") {
    throw new Error("browser content runtime sendMessage is unavailable");
  }
  return value;
}

function requireRuntimeResourcePath(value: string): string {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.length > 128 ||
    value.startsWith("/") ||
    value.includes("\\") ||
    value.includes("//") ||
    value.split("/").includes("..") ||
    !/^[A-Za-z0-9._/-]+$/u.test(value)
  ) {
    throw new Error("browser content runtime resource path is invalid");
  }
  return value;
}

function assertNotCancelled(options: BrowserExtensionContentScriptRuntimeMessageOptions): void {
  if (options.abortSignal?.aborted === true) {
    throw new Error("browser content runtime message was cancelled");
  }
}

export function createBrowserExtensionContentRuntimeUrlResolver(
  runtime: BrowserExtensionContentRuntimeApi
): BrowserExtensionPageScriptUrlResolver {
  const runtimeApi = requireRuntimeApi(runtime);
  return (path) => runtimeApi.getURL(requireRuntimeResourcePath(path));
}

export function createBrowserExtensionContentRuntimeMessageSender(
  runtime: BrowserExtensionContentRuntimeApi
): BrowserExtensionContentScriptRuntimeMessageSender {
  const runtimeApi = requireRuntimeApi(runtime);
  return (request, options = {}) => {
    assertNotCancelled(options);
    return runtimeApi.sendMessage(request);
  };
}
