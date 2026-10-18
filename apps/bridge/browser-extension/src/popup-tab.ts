import {
  browserExtensionClientContextFromSender,
  type BrowserExtensionSenderInput
} from "./sender.js";
import { BROWSER_EXTENSION_NAME } from "./manifest.js";

export type BrowserExtensionPopupTabsApi = {
  query(queryInfo: { active: true; currentWindow: true }): Promise<unknown> | unknown;
};

export type BrowserExtensionPopupActiveTabOrigin = {
  tab_id: number;
  tab_title?: string;
  page_url: string;
  page_origin: string;
  extension_id: string;
  app_name: string;
  stores_browser_secrets: false;
  contains_secret_material: false;
};

export type BrowserExtensionPopupActiveTabOriginOptions = {
  tabs: BrowserExtensionPopupTabsApi;
  extensionId: string;
  appName?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireTabsApi(value: BrowserExtensionPopupTabsApi): BrowserExtensionPopupTabsApi {
  if (!isRecord(value) || typeof value.query !== "function") {
    throw new Error("browser extension popup tabs API is invalid");
  }
  return value;
}

function requireTabId(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    throw new Error("browser extension popup active tab id is invalid");
  }
  return value;
}

function requireTabUrl(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 2048) {
    throw new Error("browser extension popup active tab url is invalid");
  }
  return value;
}

function optionalTabTitle(value: unknown): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || value.length === 0 || value.length > 160) {
    throw new Error("browser extension popup active tab title is invalid");
  }
  return value;
}

function requireSingleActiveTab(value: unknown): Record<string, unknown> {
  if (!Array.isArray(value) || value.length !== 1 || !isRecord(value[0])) {
    throw new Error("browser extension popup active tab selection is ambiguous");
  }
  return value[0];
}

function defaultAppName(): string {
  return `${BROWSER_EXTENSION_NAME} Browser Extension`;
}

export function browserExtensionSenderFromPopupActiveTabOrigin(
  selection: BrowserExtensionPopupActiveTabOrigin
): BrowserExtensionSenderInput {
  return {
    extension_id: selection.extension_id,
    page_origin: selection.page_origin,
    page_url: selection.page_url,
    app_name: selection.app_name
  };
}

export async function selectBrowserExtensionPopupActiveTabOrigin(
  options: BrowserExtensionPopupActiveTabOriginOptions
): Promise<BrowserExtensionPopupActiveTabOrigin> {
  const tabs = requireTabsApi(options.tabs);
  const tab = requireSingleActiveTab(await tabs.query({ active: true, currentWindow: true }));
  const tabId = requireTabId(tab.id);
  const pageUrl = requireTabUrl(tab.url);
  const tabTitle = optionalTabTitle(tab.title);
  const sender: BrowserExtensionSenderInput = {
    extension_id: options.extensionId,
    page_url: pageUrl,
    app_name: options.appName ?? defaultAppName()
  };
  const context = browserExtensionClientContextFromSender(sender);
  return Object.freeze({
    tab_id: tabId,
    ...(tabTitle !== undefined ? { tab_title: tabTitle } : {}),
    page_url: pageUrl,
    page_origin: context.page_origin,
    extension_id: context.extension_id,
    app_name: context.client.app_name ?? defaultAppName(),
    stores_browser_secrets: false,
    contains_secret_material: false
  });
}
