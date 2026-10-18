import {
  type BrowserExtensionOriginPermissionApproval
} from "./pairing.js";
import {
  createBrowserExtensionOriginPermissionReviewCard,
  type BrowserExtensionOriginPermissionViewControls
} from "./origin-permission-view.js";
import {
  requestBrowserExtensionPopupActiveTabOriginPermissionReview,
  type BrowserExtensionPopupOriginPermissionReviewControls,
  type BrowserExtensionPopupOriginPermissionReviewOptions
} from "./popup-origin-permission.js";
import {
  BROWSER_EXTENSION_POPUP_LIST_ID,
  BROWSER_EXTENSION_POPUP_REFRESH_ID,
  BROWSER_EXTENSION_POPUP_ROOT_ID,
  BROWSER_EXTENSION_POPUP_STATUS_ID
} from "./popup-html.js";
import {
  createBrowserExtensionPopupText,
  reportBrowserExtensionPopupError,
  requireBrowserExtensionPopupElementById,
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";

export type BrowserExtensionPopupOriginPermissionViewControls =
  BrowserExtensionPopupOriginPermissionReviewControls &
  BrowserExtensionOriginPermissionViewControls;

export type BrowserExtensionPopupOriginPermissionViewOptions =
  Omit<BrowserExtensionPopupOriginPermissionReviewOptions, "controls"> & {
    document: BrowserExtensionPopupDocument;
    controls: BrowserExtensionPopupOriginPermissionViewControls;
    rootId?: string;
    statusId?: string;
    listId?: string;
    refreshId?: string;
    onApproved?: (approval: BrowserExtensionOriginPermissionApproval) => void;
    onRejected?: () => void;
    onError?: (error: unknown) => void;
  };

export type BrowserExtensionPopupOriginPermissionViewHandle = {
  refresh(): Promise<void>;
  dispose(): void;
};

function createText(
  document: BrowserExtensionPopupDocument,
  className: string,
  text: string
): BrowserExtensionPopupElement {
  return createBrowserExtensionPopupText(document, "div", className, text);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function approvalFromControlResult(value: unknown): unknown {
  if (isRecord(value) && "approval" in value) return value.approval;
  return value;
}

export function installBrowserExtensionPopupOriginPermissionView(
  options: BrowserExtensionPopupOriginPermissionViewOptions
): BrowserExtensionPopupOriginPermissionViewHandle {
  const root = requireBrowserExtensionPopupElementById(
    options.document,
    options.rootId ?? BROWSER_EXTENSION_POPUP_ROOT_ID,
    "browser extension popup root"
  );
  const status = requireBrowserExtensionPopupElementById(
    options.document,
    options.statusId ?? BROWSER_EXTENSION_POPUP_STATUS_ID,
    "browser extension popup status"
  );
  const list = requireBrowserExtensionPopupElementById(
    options.document,
    options.listId ?? BROWSER_EXTENSION_POPUP_LIST_ID,
    "browser extension popup list"
  );
  const refreshButton = requireBrowserExtensionPopupElementById(
    options.document,
    options.refreshId ?? BROWSER_EXTENSION_POPUP_REFRESH_ID,
    "browser extension popup refresh"
  );
  let disposed = false;

  function setStatus(value: string): void {
    status.textContent = value;
  }

  function renderEmpty(text: string): void {
    list.replaceChildren(createText(options.document, "nsealr-popup__empty", text));
  }

  function renderUnavailable(error: unknown): void {
    reportBrowserExtensionPopupError(error, options.onError);
    renderEmpty("Unavailable");
    setStatus("Unavailable");
  }

  async function refresh(): Promise<void> {
    if (disposed) return;
    setStatus("Loading");
    refreshButton.disabled = true;
    try {
      const result = await requestBrowserExtensionPopupActiveTabOriginPermissionReview({
        tabs: options.tabs,
        controls: options.controls,
        extensionId: options.extensionId,
        ...(options.appName !== undefined ? { appName: options.appName } : {})
      });
      if (disposed) return;
      const card = createBrowserExtensionOriginPermissionReviewCard({
        document: options.document,
        review: result.origin_review,
        controls: {
          async approveOriginPermission(originReview, reviewedLocalPairingDigest) {
            return approvalFromControlResult(await options.controls.approveOriginPermission(
              originReview,
              reviewedLocalPairingDigest
            ));
          },
          rejectOriginPermission() {
            return options.controls.rejectOriginPermission();
          }
        },
        onApproved(approval) {
          setStatus("Approved");
          options.onApproved?.(approval);
        },
        onRejected() {
          setStatus("Rejected");
          options.onRejected?.();
        },
        onError(error) {
          renderUnavailable(error);
        }
      });
      list.replaceChildren(card);
      setStatus("Review origin");
    } catch (error) {
      if (!disposed) renderUnavailable(error);
    } finally {
      if (!disposed) refreshButton.disabled = false;
    }
  }

  const refreshListener = () => {
    void refresh();
  };
  root.setAttribute("data-nsealr-popup-origin-permission", "ready");
  refreshButton.addEventListener("click", refreshListener);
  void refresh();

  return Object.freeze({
    refresh,
    dispose(): void {
      if (disposed) return;
      disposed = true;
      refreshButton.removeEventListener?.("click", refreshListener);
    }
  });
}
