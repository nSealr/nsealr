import {
  BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE,
  BROWSER_EXTENSION_POPUP_HTML_FILE
} from "./entrypoints.js";

export const BROWSER_EXTENSION_NAME = "nSealr";
export const BROWSER_EXTENSION_DESCRIPTION = "nSealr browser bridge for external Nostr signers";
export const BROWSER_EXTENSION_VERSION = "0.1.0";

export type BrowserExtensionTarget = "chromium" | "firefox";
export type BrowserExtensionPopupMode = "pending_requests" | "origin_permission_approval";
export type BrowserExtensionOriginPermissionStorageMode = "none" | "extension";
export type BrowserExtensionManifestPermission = "nativeMessaging" | "activeTab" | "storage";

export type BrowserExtensionManifestOptions = {
  target: BrowserExtensionTarget;
  name?: string;
  description?: string;
  version?: string;
  firefoxExtensionId?: string;
  contentScriptMatches?: string[];
  popupMode?: BrowserExtensionPopupMode;
  originPermissionStorageMode?: BrowserExtensionOriginPermissionStorageMode;
};

export type BrowserExtensionContentScriptManifest = {
  matches: string[];
  js: [typeof BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE];
  run_at: "document_start";
  all_frames: false;
  match_about_blank: false;
};

export type BrowserExtensionWebAccessibleResourcesManifest = {
  resources: [typeof BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE];
  matches: string[];
};

export type BrowserExtensionManifest = {
  manifest_version: 3;
  name: string;
  description: string;
  version: string;
  permissions: BrowserExtensionManifestPermission[];
  background: {
    service_worker: typeof BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE;
    type: "module";
  };
  action: {
    default_title: string;
    default_popup: typeof BROWSER_EXTENSION_POPUP_HTML_FILE;
  };
  content_scripts?: [BrowserExtensionContentScriptManifest];
  web_accessible_resources?: [BrowserExtensionWebAccessibleResourcesManifest];
  browser_specific_settings?: {
    gecko: {
      id: string;
    };
  };
};

function requireName(value: string | undefined): string {
  const name = value ?? BROWSER_EXTENSION_NAME;
  if (name.length === 0 || name.length > 45) {
    throw new Error("browser extension name is invalid");
  }
  return name;
}

function requireDescription(value: string | undefined): string {
  const description = value ?? BROWSER_EXTENSION_DESCRIPTION;
  if (description.length === 0 || description.length > 132) {
    throw new Error("browser extension description is invalid");
  }
  return description;
}

function requireVersion(value: string | undefined): string {
  const version = value ?? BROWSER_EXTENSION_VERSION;
  if (!/^[0-9]+(?:\.[0-9]+){0,3}$/u.test(version)) {
    throw new Error("browser extension version is invalid");
  }
  return version;
}

function requirePopupMode(value: BrowserExtensionPopupMode | undefined): BrowserExtensionPopupMode {
  const popupMode = value ?? "pending_requests";
  if (popupMode !== "pending_requests" && popupMode !== "origin_permission_approval") {
    throw new Error("browser extension popup mode is unsupported");
  }
  return popupMode;
}

function requireOriginPermissionStorageMode(
  value: BrowserExtensionOriginPermissionStorageMode | undefined
): BrowserExtensionOriginPermissionStorageMode {
  const mode = value ?? "none";
  if (mode !== "none" && mode !== "extension") {
    throw new Error("browser extension origin permission storage mode is unsupported");
  }
  return mode;
}

function requireFirefoxExtensionId(value: string | undefined): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._@+-]{1,128}$/u.test(value)) {
    throw new Error("firefox extension id is invalid");
  }
  return value;
}

const EXPLICIT_HTTPS_CONTENT_SCRIPT_MATCH =
  /^https:\/\/([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\/\*$/u;
const LOCAL_HTTP_CONTENT_SCRIPT_MATCH =
  /^http:\/\/(?:localhost|127\.0\.0\.1)(?::([0-9]{1,5}))?\/\*$/u;

function isValidTcpPort(value: string): boolean {
  if (!/^[1-9][0-9]{0,4}$/u.test(value)) return false;
  return Number(value) <= 65535;
}

function isReviewedContentScriptMatch(value: string): boolean {
  if (value === "<all_urls>" || value.includes("*://") || value.includes("://*")) {
    return false;
  }
  if (EXPLICIT_HTTPS_CONTENT_SCRIPT_MATCH.test(value)) return true;
  const localHttpMatch = LOCAL_HTTP_CONTENT_SCRIPT_MATCH.exec(value);
  if (localHttpMatch === null) return false;
  const port = localHttpMatch[1];
  return port === undefined || isValidTcpPort(port);
}

function requireContentScriptMatches(value: string[] | undefined): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value) || value.length === 0 || value.length > 32) {
    throw new Error("browser extension content script matches are invalid");
  }
  const matches: string[] = [];
  for (const match of value) {
    if (typeof match !== "string" || !isReviewedContentScriptMatch(match)) {
      throw new Error("browser extension content script match is unsupported");
    }
    if (matches.includes(match)) {
      throw new Error("browser extension content script match is duplicated");
    }
    matches.push(match);
  }
  return matches;
}

export function buildBrowserExtensionManifest(options: BrowserExtensionManifestOptions): BrowserExtensionManifest {
  const name = requireName(options.name);
  const contentScriptMatches = requireContentScriptMatches(options.contentScriptMatches);
  const popupMode = requirePopupMode(options.popupMode);
  const originPermissionStorageMode = requireOriginPermissionStorageMode(options.originPermissionStorageMode);
  const permissions: BrowserExtensionManifestPermission[] = ["nativeMessaging"];
  if (popupMode === "origin_permission_approval") permissions.push("activeTab");
  if (originPermissionStorageMode === "extension") permissions.push("storage");
  const manifest: BrowserExtensionManifest = {
    manifest_version: 3,
    name,
    description: requireDescription(options.description),
    version: requireVersion(options.version),
    permissions,
    background: {
      service_worker: BROWSER_EXTENSION_BACKGROUND_ENTRYPOINT_FILE,
      type: "module"
    },
    action: {
      default_title: name,
      default_popup: BROWSER_EXTENSION_POPUP_HTML_FILE
    }
  };
  if (contentScriptMatches !== undefined) {
    manifest.content_scripts = [{
      matches: contentScriptMatches,
      js: [BROWSER_EXTENSION_CONTENT_SCRIPT_ENTRYPOINT_FILE],
      run_at: "document_start",
      all_frames: false,
      match_about_blank: false
    }];
    manifest.web_accessible_resources = [{
      resources: [BROWSER_EXTENSION_PAGE_SCRIPT_ENTRYPOINT_FILE],
      matches: contentScriptMatches
    }];
  }

  if (options.target === "chromium") {
    return manifest;
  }
  if (options.target === "firefox") {
    return {
      ...manifest,
      browser_specific_settings: {
        gecko: {
          id: requireFirefoxExtensionId(options.firefoxExtensionId)
        }
      }
    };
  }
  throw new Error("browser extension target is unsupported");
}

export function browserExtensionManifestJson(options: BrowserExtensionManifestOptions): string {
  return `${JSON.stringify(buildBrowserExtensionManifest(options), null, 2)}\n`;
}
