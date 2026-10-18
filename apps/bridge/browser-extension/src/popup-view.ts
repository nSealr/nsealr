import { type BrowserExtensionPendingRequestState } from "./pending-request.js";
import { type BrowserExtensionPopupPendingRequestControls } from "./popup-control.js";
import {
  createBrowserExtensionPopupText,
  reportBrowserExtensionPopupError,
  requireBrowserExtensionPopupElementById,
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";
import {
  BROWSER_EXTENSION_POPUP_LIST_ID,
  BROWSER_EXTENSION_POPUP_REFRESH_ID,
  BROWSER_EXTENSION_POPUP_ROOT_ID,
  BROWSER_EXTENSION_POPUP_STATUS_ID
} from "./popup-html.js";

export type BrowserExtensionPopupViewOptions = {
  document: BrowserExtensionPopupDocument;
  controls: BrowserExtensionPopupPendingRequestControls;
  rootId?: string;
  statusId?: string;
  listId?: string;
  refreshId?: string;
  onError?: (error: unknown) => void;
};

export type BrowserExtensionPopupViewHandle = {
  refresh(): Promise<void>;
  dispose(): void;
};

function methodLabel(value: BrowserExtensionPendingRequestState["method"]): string {
  if (value === "get_public_key") return "Get public key";
  return "Sign event";
}

function statusLabel(value: BrowserExtensionPendingRequestState["status"]): string {
  if (value === "pending") return "Pending";
  if (value === "resolved") return "Resolved";
  if (value === "cancelled") return "Cancelled";
  return "Rejected";
}

function pendingRequestMetaLines(state: BrowserExtensionPendingRequestState): string[] {
  const lines = [
    state.app_name ?? "nSealr",
    state.page_origin,
    ...(state.route_account_id !== undefined ? [`Route account ${state.route_account_id}`] : []),
    ...(state.route_type !== undefined ? [`Route type ${state.route_type}`] : []),
    `Request ${state.request_id}`,
    `Started ${state.started_at}`,
    `Updated ${state.updated_at}`
  ];
  return lines;
}

export function installBrowserExtensionPopupView(
  options: BrowserExtensionPopupViewOptions
): BrowserExtensionPopupViewHandle {
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

  function createText(tagName: "div" | "span", className: string, text: string): BrowserExtensionPopupElement {
    return createBrowserExtensionPopupText(options.document, tagName, className, text);
  }

  function renderEmpty(text: string): void {
    const empty = createText("div", "nsealr-popup__empty", text);
    list.replaceChildren(empty);
  }

  function renderRequest(state: BrowserExtensionPendingRequestState): BrowserExtensionPopupElement {
    const item = options.document.createElement("div");
    item.className = "nsealr-popup__request";

    const head = options.document.createElement("div");
    head.className = "nsealr-popup__request-head";
    head.appendChild(createText("span", "nsealr-popup__method", methodLabel(state.method)));
    head.appendChild(createText("span", "nsealr-popup__badge", statusLabel(state.status)));

    const meta = options.document.createElement("div");
    meta.className = "nsealr-popup__meta";
    for (const line of pendingRequestMetaLines(state)) {
      meta.appendChild(createText("div", "nsealr-popup__meta-line", line));
    }

    const chips = options.document.createElement("div");
    chips.className = "nsealr-popup__chips";
    chips.appendChild(createText("span", "nsealr-popup__chip", "No keys"));
    chips.appendChild(createText("span", "nsealr-popup__chip", "No event payload"));

    item.appendChild(head);
    item.appendChild(meta);
    item.appendChild(chips);
    if (state.status === "pending") {
      const actions = options.document.createElement("div");
      actions.className = "nsealr-popup__actions";
      const cancel = options.document.createElement("button");
      cancel.className = "nsealr-popup__button nsealr-popup__button--danger";
      cancel.textContent = "Cancel";
      cancel.setAttribute("type", "button");
      cancel.setAttribute("data-pending-request-id", state.request_id);
      if (cancel.dataset !== undefined) {
        cancel.dataset.pendingRequestId = state.request_id;
      }
      cancel.addEventListener("click", () => {
        cancel.disabled = true;
        void options.controls.cancelPendingRequest(state.request_id)
          .then(() => refresh())
          .catch((error: unknown) => {
            reportBrowserExtensionPopupError(error, options.onError);
            setStatus("Unavailable");
            cancel.disabled = false;
          });
      });
      actions.appendChild(cancel);
      item.appendChild(actions);
    }
    return item;
  }

  function renderPending(states: readonly BrowserExtensionPendingRequestState[]): void {
    if (states.length === 0) {
      renderEmpty("Ready");
      setStatus("Ready");
      return;
    }
    list.replaceChildren(...states.map(renderRequest));
    const pendingCount = states.filter((state) => state.status === "pending").length;
    setStatus(`${pendingCount} pending`);
  }

  async function refresh(): Promise<void> {
    if (disposed) return;
    setStatus("Loading");
    refreshButton.disabled = true;
    try {
      const states = await options.controls.listPendingRequests();
      if (!disposed) renderPending(states);
    } catch (error) {
      reportBrowserExtensionPopupError(error, options.onError);
      if (!disposed) {
        renderEmpty("Unavailable");
        setStatus("Unavailable");
      }
    } finally {
      if (!disposed) refreshButton.disabled = false;
    }
  }

  const refreshListener = () => {
    void refresh();
  };
  root.setAttribute("data-nsealr-popup", "ready");
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
