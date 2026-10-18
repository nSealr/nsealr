import {
  type BrowserNativeMessageSender,
  type LocalServiceBrowserProviderBackendOptions
} from "@nsealr/browser-provider";
import {
  createBrowserExtensionBackgroundController,
  type BrowserExtensionBackgroundController
} from "./background.js";
import {
  type BrowserExtensionOriginPermissionAuthorization
} from "./handler.js";
import {
  installBrowserExtensionRuntimeMessageListener,
  type BrowserExtensionRuntimeMessageEventTarget,
  type BrowserExtensionRuntimeMessageListenerHandle
} from "./runtime-message.js";
import {
  createBrowserExtensionPendingRequestLifecycle,
  type BrowserExtensionPendingRequestLifecycle
} from "./pending-request.js";
import {
  parseBrowserExtensionRouteConfig
} from "./route-config.js";
import {
  type BrowserExtensionOriginPermissionStorageArea
} from "./origin-permission-storage.js";

export type BrowserExtensionBackgroundBrowserRuntimeApi = {
  onMessage: BrowserExtensionRuntimeMessageEventTarget;
  sendNativeMessage(hostName: string, message: unknown): Promise<unknown> | unknown;
};

export type BrowserExtensionBackgroundBrowserEntrypointOptions = {
  runtime: BrowserExtensionBackgroundBrowserRuntimeApi;
  routeRequest?: LocalServiceBrowserProviderBackendOptions["routeRequest"];
  routeConfig?: unknown;
  hostName?: string;
  extensionId?: string;
  appName?: string;
  nextServiceRequestId?: () => string;
  nextSignerRequestId?: () => string;
  signingUnavailableMessage?: string;
  nativeMessageTimeoutMs?: number;
  nativeMessageAbortSignal?: AbortSignal;
  pendingRequests?: BrowserExtensionPendingRequestLifecycle;
  originPermissions?: BrowserExtensionOriginPermissionAuthorization;
  originPermissionStorage?: BrowserExtensionOriginPermissionStorageArea;
  originPermissionApprovalNow?: () => number;
  originPermissionStorageEmptyUpdatedAt?: number;
  onError?: (error: unknown) => void;
};

export type BrowserExtensionBackgroundBrowserEntrypointHandle =
  BrowserExtensionRuntimeMessageListenerHandle & {
    controller: BrowserExtensionBackgroundController;
    pendingRequests: BrowserExtensionPendingRequestLifecycle;
  };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireBrowserRuntime(
  value: BrowserExtensionBackgroundBrowserRuntimeApi
): BrowserExtensionBackgroundBrowserRuntimeApi {
  if (
    !isRecord(value) ||
    !isRecord(value.onMessage) ||
    typeof value.onMessage.addListener !== "function" ||
    typeof value.onMessage.removeListener !== "function" ||
    typeof value.sendNativeMessage !== "function"
  ) {
    throw new Error("browser background runtime is invalid");
  }
  return value;
}

function routeRequestFromOptions(
  options: BrowserExtensionBackgroundBrowserEntrypointOptions
): LocalServiceBrowserProviderBackendOptions["routeRequest"] {
  if ((options.routeRequest === undefined) === (options.routeConfig === undefined)) {
    throw new Error("browser background route configuration is invalid");
  }
  return options.routeRequest ?? parseBrowserExtensionRouteConfig(options.routeConfig).route_request;
}

export function createBrowserExtensionBackgroundBrowserNativeMessageSender(
  runtime: BrowserExtensionBackgroundBrowserRuntimeApi
): BrowserNativeMessageSender {
  const browserRuntime = requireBrowserRuntime(runtime);
  return (hostName, message, options) => {
    if (options.abortSignal?.aborted === true) {
      throw new Error("browser background native-message request was cancelled");
    }
    return browserRuntime.sendNativeMessage(hostName, message);
  };
}

export function installBrowserExtensionBackgroundBrowserEntrypoint(
  options: BrowserExtensionBackgroundBrowserEntrypointOptions
): BrowserExtensionBackgroundBrowserEntrypointHandle {
  const runtime = requireBrowserRuntime(options.runtime);
  const routeRequest = routeRequestFromOptions(options);
  const pendingRequests = options.pendingRequests ?? createBrowserExtensionPendingRequestLifecycle({ routeRequest });
  const controller = createBrowserExtensionBackgroundController({
    sendNativeMessage: createBrowserExtensionBackgroundBrowserNativeMessageSender(runtime),
    routeRequest,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextServiceRequestId: options.nextServiceRequestId } : {}),
    ...(options.nextSignerRequestId !== undefined ? { nextSignerRequestId: options.nextSignerRequestId } : {}),
    ...(options.signingUnavailableMessage !== undefined
      ? { signingUnavailableMessage: options.signingUnavailableMessage }
      : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { nativeMessageTimeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {}),
    ...(options.originPermissions !== undefined ? { originPermissions: options.originPermissions } : {}),
    ...(options.originPermissionStorage !== undefined
      ? { originPermissionStorage: options.originPermissionStorage }
      : {}),
    ...(options.originPermissionApprovalNow !== undefined
      ? { originPermissionApprovalNow: options.originPermissionApprovalNow }
      : {}),
    ...(options.originPermissionStorageEmptyUpdatedAt !== undefined
      ? { originPermissionStorageEmptyUpdatedAt: options.originPermissionStorageEmptyUpdatedAt }
      : {})
  });
  const listener = installBrowserExtensionRuntimeMessageListener({
    runtimeOnMessage: runtime.onMessage,
    controller,
    ...(options.extensionId !== undefined ? { extensionId: options.extensionId } : {}),
    ...(options.appName !== undefined ? { appName: options.appName } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {}),
    pendingRequests,
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
  return Object.freeze({
    controller,
    pendingRequests,
    dispose(): void {
      listener.dispose();
    }
  });
}
