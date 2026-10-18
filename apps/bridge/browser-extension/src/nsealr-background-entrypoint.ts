import {
  installBrowserExtensionBackgroundBrowserEntrypoint,
  type BrowserExtensionBackgroundBrowserEntrypointHandle,
  type BrowserExtensionBackgroundBrowserEntrypointOptions
} from "./background-browser.js";
import {
  requireBrowserExtensionBackgroundRuntimeGlobal,
  type BrowserExtensionPackagedGlobalScope
} from "./browser-globals.js";

export type NsealrBackgroundEntrypointOptions = Omit<
  BrowserExtensionBackgroundBrowserEntrypointOptions,
  "runtime" | "routeRequest" | "routeConfig"
> & {
  globalScope: BrowserExtensionPackagedGlobalScope;
  routeConfig: unknown;
};

export function installNsealrBackgroundEntrypoint(
  options: NsealrBackgroundEntrypointOptions
): BrowserExtensionBackgroundBrowserEntrypointHandle {
  return installBrowserExtensionBackgroundBrowserEntrypoint({
    runtime: requireBrowserExtensionBackgroundRuntimeGlobal(options.globalScope),
    routeConfig: options.routeConfig,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.extensionId !== undefined ? { extensionId: options.extensionId } : {}),
    ...(options.appName !== undefined ? { appName: options.appName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextServiceRequestId: options.nextServiceRequestId } : {}),
    ...(options.nextSignerRequestId !== undefined ? { nextSignerRequestId: options.nextSignerRequestId } : {}),
    ...(options.signingUnavailableMessage !== undefined
      ? { signingUnavailableMessage: options.signingUnavailableMessage }
      : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { nativeMessageTimeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {}),
    ...(options.pendingRequests !== undefined ? { pendingRequests: options.pendingRequests } : {}),
    ...(options.originPermissions !== undefined ? { originPermissions: options.originPermissions } : {}),
    ...(options.originPermissionStorage !== undefined
      ? { originPermissionStorage: options.originPermissionStorage }
      : {}),
    ...(options.originPermissionApprovalNow !== undefined
      ? { originPermissionApprovalNow: options.originPermissionApprovalNow }
      : {}),
    ...(options.originPermissionStorageEmptyUpdatedAt !== undefined
      ? { originPermissionStorageEmptyUpdatedAt: options.originPermissionStorageEmptyUpdatedAt }
      : {}),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}
