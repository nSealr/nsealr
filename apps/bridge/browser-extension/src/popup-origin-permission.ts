import {
  parseBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  browserExtensionSenderFromPopupActiveTabOrigin,
  selectBrowserExtensionPopupActiveTabOrigin,
  type BrowserExtensionPopupActiveTabOrigin,
  type BrowserExtensionPopupActiveTabOriginOptions
} from "./popup-tab.js";
import { type BrowserExtensionPopupControls } from "./popup-control.js";

export type BrowserExtensionPopupOriginPermissionReviewControls = Pick<
  BrowserExtensionPopupControls,
  "requestOriginPermissionReview"
>;

export type BrowserExtensionPopupOriginPermissionReviewOptions =
  BrowserExtensionPopupActiveTabOriginOptions & {
    controls: BrowserExtensionPopupOriginPermissionReviewControls;
  };

export type BrowserExtensionPopupOriginPermissionReviewResult = {
  active_tab: BrowserExtensionPopupActiveTabOrigin;
  origin_review: BrowserExtensionOriginPermissionReview;
  stores_browser_secrets: false;
  contains_secret_material: false;
  writes_browser_storage: false;
  creates_grants: false;
  injects_provider: false;
  dispatches_signers: false;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function parseSecretlessReviewResult(value: unknown): BrowserExtensionOriginPermissionReview {
  if (!isRecord(value)) {
    throw new Error("browser extension popup origin review result must be an object");
  }
  if (!hasOnlyKeys(value, [
    "origin_review",
    "stores_production_secrets",
    "contains_secret_material",
    "creates_grants",
    "injects_provider"
  ])) {
    throw new Error("browser extension popup origin review result has unsupported fields");
  }
  if (
    value.stores_production_secrets !== false ||
    value.contains_secret_material !== false ||
    value.creates_grants !== false ||
    value.injects_provider !== false
  ) {
    throw new Error("browser extension popup origin review result must be secretless and non-authorizing");
  }
  return parseBrowserExtensionOriginPermissionReview(value.origin_review);
}

function requireOriginReviewMatch(
  activeTab: BrowserExtensionPopupActiveTabOrigin,
  originReview: BrowserExtensionOriginPermissionReview
): void {
  if (originReview.origin !== activeTab.page_origin) {
    throw new Error("browser extension popup origin review origin does not match active tab");
  }
  if (originReview.extension_id !== activeTab.extension_id) {
    throw new Error("browser extension popup origin review extension id does not match active tab");
  }
  if (originReview.app_name !== activeTab.app_name) {
    throw new Error("browser extension popup origin review app name does not match active tab");
  }
}

export async function requestBrowserExtensionPopupActiveTabOriginPermissionReview(
  options: BrowserExtensionPopupOriginPermissionReviewOptions
): Promise<BrowserExtensionPopupOriginPermissionReviewResult> {
  const activeTab = await selectBrowserExtensionPopupActiveTabOrigin(options);
  const reviewResult = await options.controls.requestOriginPermissionReview(
    browserExtensionSenderFromPopupActiveTabOrigin(activeTab)
  );
  const originReview = parseSecretlessReviewResult(reviewResult);
  requireOriginReviewMatch(activeTab, originReview);
  return Object.freeze({
    active_tab: activeTab,
    origin_review: originReview,
    stores_browser_secrets: false,
    contains_secret_material: false,
    writes_browser_storage: false,
    creates_grants: false,
    injects_provider: false,
    dispatches_signers: false
  });
}
