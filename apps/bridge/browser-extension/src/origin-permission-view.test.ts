import { describe, expect, it } from "vitest";
import {
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  createBrowserExtensionOriginPermissionReviewCard
} from "./origin-permission-view.js";
import {
  type BrowserExtensionPopupDocument,
  type BrowserExtensionPopupElement
} from "./popup-dom.js";

const digest = "c".repeat(64);

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

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
  }

  click(): void {
    for (const listener of this.listeners.get("click") ?? []) listener();
  }
}

function fakeDocument(): BrowserExtensionPopupDocument {
  return {
    getElementById(): unknown {
      return undefined;
    },
    createElement(): BrowserExtensionPopupElement {
      return new FakeElement();
    }
  };
}

function review(
  requestedMethods: BrowserExtensionOriginPermissionReview["requested_methods"] = [
    {
      method: "get_public_key",
      label: "Read public key",
      effect: "The page can read the selected account public key through the browser provider."
    },
    {
      method: "sign_event",
      label: "Request event signatures",
      effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
    }
  ]
): BrowserExtensionOriginPermissionReview {
  return {
    format: "nsealr-browser-origin-permission-review-v0",
    origin: "https://example.com",
    app_name: "Example Client",
    extension_id: "extension@nsealr.dev",
    requested_methods: requestedMethods,
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

describe("browser extension origin permission review card", () => {
  it("renders a digest-bound permission decision without storage or grant actions", () => {
    const card = createBrowserExtensionOriginPermissionReviewCard({
      document: fakeDocument(),
      review: review(),
      controls: {
        approveOriginPermission() {
          throw new Error("not reached");
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      }
    }) as FakeElement;

    expect(card.className).toBe("nsealr-popup__permission");
    expect(card.attributes.get("data-origin-permission-digest")).toBe(digest);
    expect(card.children[0].children[0].textContent).toBe("Origin access");
    expect(card.children[1].children.map((child) => child.textContent)).toEqual([
      "Example Client",
      "https://example.com",
      digest
    ]);
    expect(card.children[2].children.map((row) => row.children[0].textContent)).toEqual([
      "Read public key",
      "Request event signatures"
    ]);
    expect(card.children[3].children.map((chip) => chip.textContent)).toEqual([
      "No keys",
      "No grants",
      "No storage write"
    ]);
    expect(card.children[4].children.map((button) => button.textContent)).toEqual(["Reject", "Approve"]);
  });

  it("approves only with the reviewed local pairing digest and parsed approval artifact", async () => {
    const approved: BrowserExtensionOriginPermissionApproval[] = [];
    const reviewedDigests: string[] = [];
    const sourceReview = review();
    const card = createBrowserExtensionOriginPermissionReviewCard({
      document: fakeDocument(),
      review: sourceReview,
      controls: {
        approveOriginPermission(_originReview, reviewedLocalPairingDigest: string): BrowserExtensionOriginPermissionApproval {
          reviewedDigests.push(reviewedLocalPairingDigest);
          return approveBrowserExtensionOriginPermissionReview(sourceReview, {
            reviewedLocalPairingDigest,
            approvedAt: 1_900_000_010
          });
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      },
      onApproved(approval) {
        approved.push(approval);
      }
    }) as FakeElement;

    const approve = card.children[4].children[1];
    approve.click();
    await flushAsync();

    expect(reviewedDigests).toEqual([digest]);
    expect(approved).toHaveLength(1);
    expect(approved[0]).toMatchObject({
      approved_methods: ["get_public_key", "sign_event"],
      creates_grants: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(card.children[0].children[1].textContent).toBe("Approved");
    expect(card.children[4].children.every((button) => button.disabled)).toBe(true);
  });

  it("rejects without creating an approval artifact", async () => {
    const rejected: string[] = [];
    const card = createBrowserExtensionOriginPermissionReviewCard({
      document: fakeDocument(),
      review: review([
        {
          method: "get_public_key",
          label: "Read public key",
          effect: "The page can read the selected account public key through the browser provider."
        }
      ]),
      controls: {
        approveOriginPermission() {
          throw new Error("not reached");
        },
        rejectOriginPermission() {
          rejected.push("rejected");
        }
      },
      onRejected() {
        rejected.push("callback");
      }
    }) as FakeElement;

    const reject = card.children[4].children[0];
    reject.click();
    await flushAsync();

    expect(card.children[2].children).toHaveLength(1);
    expect(rejected).toEqual(["rejected", "callback"]);
    expect(card.children[0].children[1].textContent).toBe("Rejected");
  });

  it("restores controls and reports errors on malformed approval output", async () => {
    const errors: unknown[] = [];
    const card = createBrowserExtensionOriginPermissionReviewCard({
      document: fakeDocument(),
      review: review(),
      controls: {
        approveOriginPermission() {
          return {
            format: "wrong"
          };
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      },
      onError(error) {
        errors.push(error);
      }
    }) as FakeElement;

    const approve = card.children[4].children[1];
    approve.click();
    await flushAsync();

    expect(errors).toHaveLength(1);
    expect(card.children[0].children[1].textContent).toBe("Unavailable");
    expect(card.children[4].children.every((button) => button.disabled)).toBe(false);
  });

  it("rejects malformed review data before rendering the decision surface", () => {
    expect(() => createBrowserExtensionOriginPermissionReviewCard({
      document: fakeDocument(),
      review: {
        ...review(),
        creates_grants: true
      },
      controls: {
        approveOriginPermission() {
          throw new Error("not reached");
        },
        rejectOriginPermission() {
          throw new Error("not reached");
        }
      }
    })).toThrow(/create grants/u);
  });
});
