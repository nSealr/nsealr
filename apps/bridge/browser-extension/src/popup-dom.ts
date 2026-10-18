export type BrowserExtensionPopupElement = {
  textContent: string | null;
  className: string;
  disabled?: boolean;
  dataset?: Record<string, string>;
  appendChild(child: BrowserExtensionPopupElement): unknown;
  replaceChildren(...children: BrowserExtensionPopupElement[]): void;
  addEventListener(type: "click", listener: () => void): void;
  removeEventListener?(type: "click", listener: () => void): void;
  setAttribute(name: string, value: string): void;
};

export type BrowserExtensionPopupDocument = {
  getElementById(id: string): unknown;
  createElement(tagName: "button" | "div" | "span"): BrowserExtensionPopupElement;
};

export function isBrowserExtensionPopupElement(value: unknown): value is BrowserExtensionPopupElement {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    "appendChild" in value &&
    typeof value.appendChild === "function" &&
    "replaceChildren" in value &&
    typeof value.replaceChildren === "function" &&
    "addEventListener" in value &&
    typeof value.addEventListener === "function" &&
    "setAttribute" in value &&
    typeof value.setAttribute === "function"
  );
}

export function requireBrowserExtensionPopupElement(
  value: unknown,
  label: string
): BrowserExtensionPopupElement {
  if (!isBrowserExtensionPopupElement(value)) {
    throw new Error(`${label} is unavailable`);
  }
  return value;
}

export function requireBrowserExtensionPopupElementById(
  document: BrowserExtensionPopupDocument,
  id: string,
  label: string
): BrowserExtensionPopupElement {
  return requireBrowserExtensionPopupElement(document.getElementById(id), label);
}

export function createBrowserExtensionPopupText(
  document: BrowserExtensionPopupDocument,
  tagName: "div" | "span",
  className: string,
  text: string
): BrowserExtensionPopupElement {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

export function reportBrowserExtensionPopupError(
  error: unknown,
  onError: ((error: unknown) => void) | undefined
): void {
  if (onError === undefined) return;
  try {
    onError(error);
  } catch {
    // Popup diagnostics must not break the visible control surface.
  }
}
