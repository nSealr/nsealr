import {
  parseBrowserExtensionOriginPermissionApproval,
  parseBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  createBrowserExtensionPopupText,
  reportBrowserExtensionPopupError,
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";

export type BrowserExtensionOriginPermissionViewControls = {
  approveOriginPermission(
    originReview: BrowserExtensionOriginPermissionReview,
    reviewedLocalPairingDigest: string
  ): Promise<unknown> | unknown;
  rejectOriginPermission(): Promise<void> | void;
};

export type BrowserExtensionOriginPermissionViewOptions = {
  document: BrowserExtensionPopupDocument;
  review: unknown;
  controls: BrowserExtensionOriginPermissionViewControls;
  onApproved?: (approval: BrowserExtensionOriginPermissionApproval) => void;
  onRejected?: () => void;
  onError?: (error: unknown) => void;
};

function createText(
  document: BrowserExtensionPopupDocument,
  tagName: "div" | "span",
  className: string,
  text: string
): BrowserExtensionPopupElement {
  return createBrowserExtensionPopupText(document, tagName, className, text);
}

function setBusy(
  buttons: readonly BrowserExtensionPopupElement[],
  status: BrowserExtensionPopupElement,
  busy: boolean,
  text: string
): void {
  status.textContent = text;
  for (const button of buttons) {
    button.disabled = busy;
  }
}

function appendMethodRows(
  document: BrowserExtensionPopupDocument,
  methods: BrowserExtensionOriginPermissionReview["requested_methods"]
): BrowserExtensionPopupElement {
  const list = document.createElement("div");
  list.className = "nsealr-popup__permission-methods";
  for (const method of methods) {
    const row = document.createElement("div");
    row.className = "nsealr-popup__permission-method";
    row.appendChild(createText(document, "span", "nsealr-popup__method", method.label));
    row.appendChild(createText(document, "div", "nsealr-popup__meta-line", method.effect));
    list.appendChild(row);
  }
  return list;
}

export function createBrowserExtensionOriginPermissionReviewCard(
  options: BrowserExtensionOriginPermissionViewOptions
): BrowserExtensionPopupElement {
  const review = parseBrowserExtensionOriginPermissionReview(options.review);
  const card = options.document.createElement("div");
  card.className = "nsealr-popup__permission";
  card.setAttribute("data-origin-permission-digest", review.local_pairing_digest);

  const header = options.document.createElement("div");
  header.className = "nsealr-popup__request-head";
  header.appendChild(createText(options.document, "span", "nsealr-popup__method", "Origin access"));
  const status = createText(options.document, "span", "nsealr-popup__badge", "Review");
  header.appendChild(status);

  const meta = options.document.createElement("div");
  meta.className = "nsealr-popup__meta";
  meta.appendChild(createText(options.document, "div", "nsealr-popup__meta-line", review.app_name));
  meta.appendChild(createText(options.document, "div", "nsealr-popup__meta-line", review.origin));
  meta.appendChild(createText(
    options.document,
    "div",
    "nsealr-popup__digest",
    review.local_pairing_digest
  ));

  const chips = options.document.createElement("div");
  chips.className = "nsealr-popup__permission-chips";
  chips.appendChild(createText(options.document, "span", "nsealr-popup__chip", "No keys"));
  chips.appendChild(createText(options.document, "span", "nsealr-popup__chip", "No grants"));
  chips.appendChild(createText(options.document, "span", "nsealr-popup__chip", "No storage write"));

  const actions = options.document.createElement("div");
  actions.className = "nsealr-popup__actions";
  const reject = options.document.createElement("button");
  reject.className = "nsealr-popup__button";
  reject.textContent = "Reject";
  reject.setAttribute("type", "button");
  const approve = options.document.createElement("button");
  approve.className = "nsealr-popup__button nsealr-popup__button--primary";
  approve.textContent = "Approve";
  approve.setAttribute("type", "button");
  const buttons = [reject, approve] as const;

  reject.addEventListener("click", () => {
    setBusy(buttons, status, true, "Rejecting");
    void Promise.resolve(options.controls.rejectOriginPermission())
      .then(() => {
        status.textContent = "Rejected";
        options.onRejected?.();
      })
      .catch((error: unknown) => {
        reportBrowserExtensionPopupError(error, options.onError);
        setBusy(buttons, status, false, "Unavailable");
      });
  });
  approve.addEventListener("click", () => {
    setBusy(buttons, status, true, "Approving");
    void Promise.resolve(options.controls.approveOriginPermission(review, review.local_pairing_digest))
      .then((value) => {
        const approval = parseBrowserExtensionOriginPermissionApproval(value);
        status.textContent = "Approved";
        options.onApproved?.(approval);
      })
      .catch((error: unknown) => {
        reportBrowserExtensionPopupError(error, options.onError);
        setBusy(buttons, status, false, "Unavailable");
      });
  });

  actions.appendChild(reject);
  actions.appendChild(approve);
  card.appendChild(header);
  card.appendChild(meta);
  card.appendChild(appendMethodRows(options.document, review.requested_methods));
  card.appendChild(chips);
  card.appendChild(actions);
  return card;
}
