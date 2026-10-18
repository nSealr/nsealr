export function normalizeBrowserExtensionPageOrigin(value: unknown): string | undefined {
  if (typeof value !== "string" || value.length === 0 || value.length > 256) {
    return undefined;
  }
  try {
    const url = new URL(value);
    if (url.origin !== value) return undefined;
    if (url.protocol === "https:") return value;
    if (url.protocol === "http:" && (url.hostname === "localhost" || url.hostname === "127.0.0.1")) {
      return value;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

export function requireBrowserExtensionPageOrigin(value: unknown, errorMessage: string): string {
  const origin = normalizeBrowserExtensionPageOrigin(value);
  if (origin === undefined) {
    throw new Error(errorMessage);
  }
  return origin;
}
