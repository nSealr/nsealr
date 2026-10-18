import {
  createBrowserExtensionPopupControls,
  type BrowserExtensionPopupControlOptions,
  type BrowserExtensionPopupControls
} from "./popup-control.js";
import {
  requireBrowserExtensionPopupDocumentGlobal,
  requireBrowserExtensionPopupRuntimeGlobal,
  requireBrowserExtensionRuntimeIdGlobal,
  requireBrowserExtensionPopupTabsGlobal,
  type BrowserExtensionPackagedGlobalScope
} from "./browser-globals.js";
import {
  installBrowserExtensionPopupView,
  type BrowserExtensionPopupViewHandle
} from "./popup-view.js";
import {
  installBrowserExtensionPopupOriginPermissionView,
  type BrowserExtensionPopupOriginPermissionViewHandle,
  type BrowserExtensionPopupOriginPermissionViewOptions
} from "./popup-origin-permission-view.js";

export type NsealrPopupEntrypointOptions = Omit<
  BrowserExtensionPopupControlOptions,
  "runtime"
> & {
  globalScope: BrowserExtensionPackagedGlobalScope;
};

export function createNsealrPopupEntrypoint(
  options: NsealrPopupEntrypointOptions
): BrowserExtensionPopupControls {
  return createBrowserExtensionPopupControls({
    runtime: requireBrowserExtensionPopupRuntimeGlobal(options.globalScope),
    ...(options.nextRequestId !== undefined ? { nextRequestId: options.nextRequestId } : {}),
    ...(options.abortSignal !== undefined ? { abortSignal: options.abortSignal } : {})
  });
}

export function installNsealrPopupEntrypoint(
  options: NsealrPopupEntrypointOptions & {
    onError?: (error: unknown) => void;
  }
): BrowserExtensionPopupViewHandle {
  return installBrowserExtensionPopupView({
    document: requireBrowserExtensionPopupDocumentGlobal(options.globalScope),
    controls: createNsealrPopupEntrypoint(options),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}

export type NsealrPopupOriginPermissionEntrypointOptions = Omit<
  BrowserExtensionPopupOriginPermissionViewOptions,
  "document" | "controls" | "extensionId" | "tabs"
> &
  NsealrPopupEntrypointOptions & {
    extensionId?: string;
  };

export function installNsealrPopupOriginPermissionEntrypoint(
  options: NsealrPopupOriginPermissionEntrypointOptions
): BrowserExtensionPopupOriginPermissionViewHandle {
  const controls = createNsealrPopupEntrypoint(options);
  return installBrowserExtensionPopupOriginPermissionView({
    document: requireBrowserExtensionPopupDocumentGlobal(options.globalScope),
    controls: {
      ...controls,
      rejectOriginPermission(): void {
        return undefined;
      }
    },
    tabs: requireBrowserExtensionPopupTabsGlobal(options.globalScope),
    extensionId: options.extensionId ?? requireBrowserExtensionRuntimeIdGlobal(options.globalScope),
    ...(options.appName !== undefined ? { appName: options.appName } : {}),
    ...(options.rootId !== undefined ? { rootId: options.rootId } : {}),
    ...(options.statusId !== undefined ? { statusId: options.statusId } : {}),
    ...(options.listId !== undefined ? { listId: options.listId } : {}),
    ...(options.refreshId !== undefined ? { refreshId: options.refreshId } : {}),
    ...(options.onApproved !== undefined ? { onApproved: options.onApproved } : {}),
    ...(options.onRejected !== undefined ? { onRejected: options.onRejected } : {}),
    ...(options.onError !== undefined ? { onError: options.onError } : {})
  });
}
