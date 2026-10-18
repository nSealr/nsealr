export const LOCAL_CLIENT_SURFACES = [
  "browser_extension",
  "desktop_app",
  "cli",
  "sdk",
  "native_host_test"
] as const;

export type LocalClientSurface = (typeof LOCAL_CLIENT_SURFACES)[number];

export type LocalClientIdentity = {
  surface: LocalClientSurface;
  origin: string;
  app_name?: string;
  instance_id?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function isLocalClientSurface(value: unknown): value is LocalClientSurface {
  return typeof value === "string" && LOCAL_CLIENT_SURFACES.includes(value as LocalClientSurface);
}

function isSupportedOrigin(origin: string): boolean {
  if (origin.startsWith("extension:")) return true;
  if (origin.startsWith("app:")) return true;
  if (origin.startsWith("cli:")) return true;
  if (origin.startsWith("sdk:")) return true;
  try {
    const url = new URL(origin);
    if (url.origin !== origin) return false;
    if (url.protocol === "https:") return true;
    if (url.protocol === "http:" && (url.hostname === "localhost" || url.hostname === "127.0.0.1")) return true;
  } catch {
    return false;
  }
  return false;
}

export function parseLocalClientIdentity(value: unknown): LocalClientIdentity {
  if (!isRecord(value)) throw new Error("client identity must be an object");
  if (!hasOnlyKeys(value, ["surface", "origin", "app_name", "instance_id"])) {
    throw new Error("client identity contains unsupported fields");
  }
  if (!isLocalClientSurface(value.surface)) throw new Error("client surface is unsupported");
  if (typeof value.origin !== "string" || value.origin.length === 0 || value.origin.length > 256) {
    throw new Error("client origin is invalid");
  }
  if (!isSupportedOrigin(value.origin)) throw new Error("client origin scheme is unsupported");
  if ("app_name" in value && (typeof value.app_name !== "string" || value.app_name.length > 80)) {
    throw new Error("client app_name is invalid");
  }
  if ("instance_id" in value && (typeof value.instance_id !== "string" || !/^[A-Za-z0-9._:@+-]{1,128}$/u.test(value.instance_id))) {
    throw new Error("client instance_id is invalid");
  }
  return {
    surface: value.surface,
    origin: value.origin,
    ...(typeof value.app_name === "string" ? { app_name: value.app_name } : {}),
    ...(typeof value.instance_id === "string" ? { instance_id: value.instance_id } : {})
  };
}
