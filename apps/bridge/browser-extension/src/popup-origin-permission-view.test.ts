import { describe, expect, it } from "vitest";
import {
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  installBrowserExtensionPopupOriginPermissionView
} from "./popup-origin-permission-view.js";
import {
  BROWSER_EXTENSION_POPUP_LIST_ID,
  BROWSER_EXTENSION_POPUP_REFRESH_ID,
  BROWSER_EXTENSION_POPUP_ROOT_ID,
  BROWSER_EXTENSION_POPUP_STATUS_ID
} from "./popup-html.js";
import {
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";
import { type BrowserExtensionPopupTabsApi } from "./popup-tab.js";

const digest = "e".repeat(64);

class FakeElement implements BrowserExtensionPopupElement {
  textContent: string | null = null;
  className = "";
  disabled = false;
  dataset: Record<string, string> = {};
  readonly attributes = new Map<string, string>();
  readonly children: FakeElement[] = [];
  readonly listeners = new Map<string, Array<() => void>>();

  appendChild(child: BrowserExtensionPopupElement): unknown {
    this.children.push(child as FakeElement);
    return child;
  }

  replaceChildren(...children: BrowserExtensionPopupElement[]): void {
    this.children.splice(0, this.children.length, ...(children as FakeElement[]));
  }

  addEventListener(type: "click", listener: () => void): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: "click", listener: () => void): void {
    const listeners = this.listeners.get(type) ?? [];
    this.listeners.set(type, listeners.filter((candidate) => candidate !== listener));
  }

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
  }

  click(): void {
    for (const listener of this.listeners.get("click") ?? []) listener();
  }
}

function fakeDocument(elements: Map<string, FakeElement>): BrowserExtensionPopupDocument {
  return {
    getElementById(id: string): unknown {
      return elements.get(id);
    },
    createElement(): BrowserExtensionPopupElement {
      return new FakeElement();
    }
  };
}

function popupElements(): {
  elements: Map<string, FakeElement>;
  root: FakeElement;
  status: FakeElement;
  list: FakeElement;
  refresh: FakeElement;
} {
  const root = new FakeElement();
  const status = new FakeElement();
  const list = new FakeElement();
  const refresh = new FakeElement();
  return {
    root,
    status,
    list,
    refresh,
    elements: new Map([
      [BROWSER_EXTENSION_POPUP_ROOT_ID, root],
      [BROWSER_EXTENSION_POPUP_STATUS_ID, status],
      [BROWSER_EXTENSION_POPUP_LIST_ID, list],
      [BROWSER_EXTENSION_POPUP_REFRESH_ID, refresh]
    ])
  };
}

function tabsApi(result: unknown): BrowserExtensionPopupTabsApi {
  return {
    query(): unknown {
      return result;
    }
  };
}

function originReview(origin = "https://example.com"): BrowserExtensionOriginPermissionReview {
  return {
    format: "nsealr-browser-origin-permission-review-v0",
    origin,
    app_name: "Example App",
    extension_id: "extension@nsealr.dev",
    requested_methods: [
      {
        method: "get_public_key",
        label: "Read public key",
        effect: "The page can read the selected account public key through the browser provider."
      }
    ],
    local_pairing_digest: digest,
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  };
}

async function flushAsync(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("browser extension popup origin permission view", () => {
  it("renders active-tab origin review and delegates digest-bound approval without storage or grants", async () => {
    const popup = popupElements();
    const sourceReview = originReview();
    const reviewedDigests: string[] = [];
    const approvals: BrowserExtensionOriginPermissionApproval[] = [];
    installBrowserExtensionPopupOriginPermissionView({
      document: fakeDocument(popup.elements),
      tabs: tabsApi([{ id: 12, url: "https://example.com/app", title: "Example" }]),
      extensionId: "extension@nsealr.dev",
      appName: "Example App",
      controls: {
        async requestOriginPermissionReview() {
          return {
            origin_review: sourceReview,
            stores_production_secrets: false,
            contains_secret_material: false,
            creates_grants: false,
            injects_provider: false
          };
        },
        approveOriginPermission(_originReview, reviewedLocalPairingDigest: string) {
          reviewedDigests.push(reviewedLocalPairingDigest);
          return approveBrowserExtensionOriginPermissionReview(sourceReview, {
            reviewedLocalPairingDigest,
            approvedAt: 1_900_000_020
          });
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      },
      onApproved(approval) {
        approvals.push(approval);
      }
    });
    await flushAsync();

    expect(popup.root.attributes.get("data-nsealr-popup-origin-permission")).toBe("ready");
    expect(popup.status.textContent).toBe("Review origin");
    expect(popup.list.children).toHaveLength(1);
    expect(popup.list.children[0].attributes.get("data-origin-permission-digest")).toBe(digest);

    const approve = popup.list.children[0].children[4].children[1];
    approve.click();
    await flushAsync();

    expect(reviewedDigests).toEqual([digest]);
    expect(approvals).toHaveLength(1);
    expect(approvals[0]).toMatchObject({
      approved_methods: ["get_public_key"],
      creates_grants: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(popup.status.textContent).toBe("Approved");
  });

  it("renders unavailable when active-tab review metadata does not match", async () => {
    const popup = popupElements();
    const errors: unknown[] = [];
    installBrowserExtensionPopupOriginPermissionView({
      document: fakeDocument(popup.elements),
      tabs: tabsApi([{ id: 12, url: "https://example.com/app" }]),
      extensionId: "extension@nsealr.dev",
      appName: "Example App",
      controls: {
        async requestOriginPermissionReview() {
          return {
            origin_review: originReview("https://attacker.example"),
            stores_production_secrets: false,
            contains_secret_material: false,
            creates_grants: false,
            injects_provider: false
          };
        },
        approveOriginPermission() {
          throw new Error("not reached");
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      },
      onError(error) {
        errors.push(error);
      }
    });
    await flushAsync();

    expect(errors).toHaveLength(1);
    expect(popup.status.textContent).toBe("Unavailable");
    expect(popup.list.children.map((child) => child.textContent)).toEqual(["Unavailable"]);
  });

  it("reuses the popup refresh control and removes it on dispose", async () => {
    const popup = popupElements();
    let reviewCount = 0;
    const handle = installBrowserExtensionPopupOriginPermissionView({
      document: fakeDocument(popup.elements),
      tabs: tabsApi([{ id: 12, url: "https://example.com/app" }]),
      extensionId: "extension@nsealr.dev",
      appName: "Example App",
      controls: {
        async requestOriginPermissionReview() {
          reviewCount += 1;
          return {
            origin_review: originReview(),
            stores_production_secrets: false,
            contains_secret_material: false,
            creates_grants: false,
            injects_provider: false
          };
        },
        approveOriginPermission() {
          throw new Error("not reached");
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      }
    });
    await flushAsync();
    popup.refresh.click();
    await flushAsync();
    handle.dispose();
    popup.refresh.click();
    await flushAsync();

    expect(reviewCount).toBe(2);
  });
});
