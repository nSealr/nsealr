import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
  type BrowserExtensionPendingRequestState
} from "./pending-request.js";
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
import {
  installBrowserExtensionPopupView
} from "./popup-view.js";

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
    this.listeners.set(type, (this.listeners.get(type) ?? []).filter((candidate) => candidate !== listener));
  }

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
  }

  click(): void {
    for (const listener of this.listeners.get("click") ?? []) listener();
  }
}

function createFakeDocument(): {
  document: BrowserExtensionPopupDocument;
  root: FakeElement;
  status: FakeElement;
  list: FakeElement;
  refresh: FakeElement;
} {
  const elements = new Map<string, FakeElement>();
  const root = new FakeElement();
  const status = new FakeElement();
  const list = new FakeElement();
  const refresh = new FakeElement();
  elements.set(BROWSER_EXTENSION_POPUP_ROOT_ID, root);
  elements.set(BROWSER_EXTENSION_POPUP_STATUS_ID, status);
  elements.set(BROWSER_EXTENSION_POPUP_LIST_ID, list);
  elements.set(BROWSER_EXTENSION_POPUP_REFRESH_ID, refresh);
  return {
    document: {
      getElementById(id: string): unknown {
        return elements.get(id);
      },
      createElement(): BrowserExtensionPopupElement {
        return new FakeElement();
      }
    },
    root,
    status,
    list,
    refresh
  };
}

function pendingState(): BrowserExtensionPendingRequestState {
  return {
    format: BROWSER_EXTENSION_PENDING_REQUEST_STATE_FORMAT,
    request_id: "pending-popup-view",
    method: "sign_event",
    extension_id: "extension@nsealr.dev",
    page_origin: "https://example.com",
    app_name: "Example",
    route_account_id: "esp32-usb-slot-0",
    route_type: "esp32_usb_nip46",
    status: "pending",
    started_at: 1_900_000_500,
    updated_at: 1_900_000_500,
    stores_production_secrets: false,
    includes_event_template: false
  };
}

async function flushAsync(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("browser extension popup view", () => {
  it("renders pending requests and cancels them through injected controls", async () => {
    const fake = createFakeDocument();
    const states = [pendingState()];
    const cancelled: string[] = [];
    const handle = installBrowserExtensionPopupView({
      document: fake.document,
      controls: {
        async listPendingRequests(): Promise<readonly BrowserExtensionPendingRequestState[]> {
          return states;
        },
        async cancelPendingRequest(pendingRequestId: string) {
          cancelled.push(pendingRequestId);
          states.splice(0, states.length);
          return {
            pending_request_id: pendingRequestId,
            cancelled: true,
            stores_production_secrets: false as const,
            contains_secret_material: false as const
          };
        }
      }
    });

    await flushAsync();
    expect(fake.root.attributes.get("data-nsealr-popup")).toBe("ready");
    expect(fake.status.textContent).toBe("1 pending");
    expect(fake.list.children).toHaveLength(1);
    expect(fake.list.children[0].children[0].children[0].textContent).toBe("Sign event");
    expect(fake.list.children[0].children[1].children.map((child) => child.textContent)).toEqual([
      "Example",
      "https://example.com",
      "Route account esp32-usb-slot-0",
      "Route type esp32_usb_nip46",
      "Request pending-popup-view",
      "Started 1900000500",
      "Updated 1900000500"
    ]);
    expect(fake.list.children[0].children[2].children.map((child) => child.textContent)).toEqual([
      "No keys",
      "No event payload"
    ]);
    const cancelButton = fake.list.children[0].children[3].children[0];
    expect(cancelButton.textContent).toBe("Cancel");
    expect(cancelButton.dataset.pendingRequestId).toBe("pending-popup-view");

    cancelButton.click();
    await flushAsync();
    await flushAsync();

    expect(cancelled).toEqual(["pending-popup-view"]);
    expect(fake.status.textContent).toBe("Ready");
    expect(fake.list.children[0].textContent).toBe("Ready");
    handle.dispose();
  });

  it("renders unavailable state without leaking control errors", async () => {
    const fake = createFakeDocument();
    const errors: unknown[] = [];
    installBrowserExtensionPopupView({
      document: fake.document,
      controls: {
        async listPendingRequests(): Promise<readonly BrowserExtensionPendingRequestState[]> {
          throw new Error("runtime unavailable");
        },
        async cancelPendingRequest() {
          throw new Error("not reached");
        }
      },
      onError: (error) => {
        errors.push(error);
      }
    });

    await flushAsync();

    expect(errors).toHaveLength(1);
    expect(fake.status.textContent).toBe("Unavailable");
    expect(fake.list.children[0].textContent).toBe("Unavailable");
  });

  it("does not render cancel actions for already settled states", async () => {
    const fake = createFakeDocument();
    installBrowserExtensionPopupView({
      document: fake.document,
      controls: {
        async listPendingRequests(): Promise<readonly BrowserExtensionPendingRequestState[]> {
          return [{
            ...pendingState(),
            status: "resolved"
          }];
        },
        async cancelPendingRequest() {
          throw new Error("settled state must not expose cancel");
        }
      }
    });

    await flushAsync();

    expect(fake.status.textContent).toBe("0 pending");
    expect(fake.list.children[0].children[0].children[1].textContent).toBe("Resolved");
    expect(fake.list.children[0].children).toHaveLength(3);
  });
});
