import {
  parseLocalClientIdentity,
  type LocalClientIdentity
} from "@nsealr/client/browser";
import { BROWSER_EXTENSION_NAME } from "./manifest.js";

export type BrowserExtensionSenderInput = {
  extension_id: string;
  page_origin?: string;
  page_url?: string;
  app_name?: string;
};

export type BrowserExtensionClientContext = {
  client: LocalClientIdentity;
  extension_id: string;
  page_origin: string;
  origin_source: "page_origin" | "page_url";
  stores_browser_secrets: false;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requireExtensionId(value: unknown): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._@+-]{1,128}$/u.test(value)) {
    throw new Error("browser extension id is invalid");
  }
  return value;
}

function requireAppName(value: unknown): string {
  if (value === undefined) return `${BROWSER_EXTENSION_NAME} Browser Extension`;
  if (typeof value !== "string" || value.length === 0 || value.length > 80) {
    throw new Error("browser extension app_name is invalid");
  }
  return value;
}

function originFromUrl(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 2048) {
    throw new Error("browser extension page_url is invalid");
  }
  try {
    const url = new URL(value);
    if (url.origin === "null") {
      throw new Error("opaque origin");
    }
    return url.origin;
  } catch {
    throw new Error("browser extension page_url is invalid");
  }
}

function resolvePageOrigin(value: Record<string, unknown>): {
  origin: string;
  source: BrowserExtensionClientContext["origin_source"];
} {
  if (value.page_origin !== undefined && typeof value.page_origin !== "string") {
    throw new Error("browser extension page origin is invalid");
  }
  if (typeof value.page_origin === "string") {
    if (value.page_url !== undefined && originFromUrl(value.page_url) !== value.page_origin) {
      throw new Error("browser extension page origin does not match page_url");
    }
    return { origin: value.page_origin, source: "page_origin" };
  }
  if (value.page_url !== undefined) {
    return { origin: originFromUrl(value.page_url), source: "page_url" };
  }
  throw new Error("browser extension page origin is required");
}

export function browserExtensionClientContextFromSender(value: unknown): BrowserExtensionClientContext {
  if (!isRecord(value)) throw new Error("browser extension sender must be an object");
  if (!hasOnlyKeys(value, ["extension_id", "page_origin", "page_url", "app_name"])) {
    throw new Error("browser extension sender has unsupported fields");
  }
  const extensionId = requireExtensionId(value.extension_id);
  const page = resolvePageOrigin(value);
  const client = parseLocalClientIdentity({
    surface: "browser_extension",
    origin: page.origin,
    app_name: requireAppName(value.app_name),
    instance_id: extensionId
  });
  return {
    client,
    extension_id: extensionId,
    page_origin: client.origin,
    origin_source: page.source,
    stores_browser_secrets: false
  };
}
