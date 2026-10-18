import { describe, expect, it } from "vitest";
import {
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
  createBrowserExtensionOriginPermissionStore,
  findBrowserExtensionOriginPermissionApproval,
  isBrowserExtensionOriginMethodAllowed,
  parseBrowserExtensionOriginPermissionStore,
  revokeBrowserExtensionOriginPermissionApproval,
  upsertBrowserExtensionOriginPermissionApproval
} from "./origin-permission-store.js";

const digestA = "a".repeat(64);
const digestB = "b".repeat(64);

function review(
  origin: string,
  extensionId: string,
  localPairingDigest: string,
  requestedMethods: BrowserExtensionOriginPermissionReview["requested_methods"]
): BrowserExtensionOriginPermissionReview {
  return {
    format: "nsealr-browser-origin-permission-review-v0",
    origin,
    app_name: "nSealr Browser Extension",
    extension_id: extensionId,
    requested_methods: requestedMethods,
    local_pairing_digest: localPairingDigest,
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  };
}

function approval(
  origin: string,
  extensionId: string,
  localPairingDigest: string,
  approvedAt: number,
  methods: BrowserExtensionOriginPermissionReview["requested_methods"] = [
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
): BrowserExtensionOriginPermissionApproval {
  return approveBrowserExtensionOriginPermissionReview(
    review(origin, extensionId, localPairingDigest, methods),
    {
      reviewedLocalPairingDigest: localPairingDigest,
      approvedAt
    }
  );
}

describe("browser extension origin permission store contract", () => {
  it("creates and parses a deterministic secretless approval store", () => {
    const later = approval("https://z.example", "extension@nsealr.dev", digestB, 1_900_000_002);
    const earlier = approval("https://a.example", "extension@nsealr.dev", digestA, 1_900_000_001);

    const store = createBrowserExtensionOriginPermissionStore([later, earlier], {
      updatedAt: 1_900_000_003
    });

    expect(store).toEqual({
      format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
      updated_at: 1_900_000_003,
      approvals: [earlier, later],
      requires_user_approval: true,
      writes_extension_storage: false,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(parseBrowserExtensionOriginPermissionStore(store)).toEqual(store);
  });

  it("allows only exact origin, extension, digest, and method matches", () => {
    const store = createBrowserExtensionOriginPermissionStore([
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001)
    ], {
      updatedAt: 1_900_000_002
    });

    expect(findBrowserExtensionOriginPermissionApproval(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toEqual(store.approvals[0]);
    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "get_public_key"
    })).toBe(true);
    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://sub.example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toBe(false);
    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "other-extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toBe(false);
    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestB,
      method: "sign_event"
    })).toBe(false);
    expect(() => isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com/path",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toThrow(/origin/u);
    expect(() => isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toThrow(/instance_id|extensionId/u);
  });

  it("keeps route-only origin approval scoped to public-key reads", () => {
    const routeOnly = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001, [
      {
        method: "get_public_key",
        label: "Read public key",
        effect: "The page can read the selected account public key through the browser provider."
      }
    ]);
    const store = createBrowserExtensionOriginPermissionStore([routeOnly], {
      updatedAt: 1_900_000_002
    });

    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "get_public_key"
    })).toBe(true);
    expect(isBrowserExtensionOriginMethodAllowed(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toBe(false);
  });

  it("rejects duplicate approval keys before a later approval can shadow an earlier one", () => {
    const first = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001);
    const second = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_002);

    expect(() => createBrowserExtensionOriginPermissionStore([first, second], {
      updatedAt: 1_900_000_003
    })).toThrow(/duplicated/u);
  });

  it("upserts exact approval keys without keeping stale method scopes", () => {
    const routeOnly = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001, [
      {
        method: "get_public_key",
        label: "Read public key",
        effect: "The page can read the selected account public key through the browser provider."
      }
    ]);
    const fullAccess = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_003);
    const otherOrigin = approval("https://other.example", "extension@nsealr.dev", digestB, 1_900_000_002);
    const store = createBrowserExtensionOriginPermissionStore([routeOnly, otherOrigin], {
      updatedAt: 1_900_000_004
    });

    const updated = upsertBrowserExtensionOriginPermissionApproval(store, fullAccess, {
      updatedAt: 1_900_000_005
    });

    expect(updated.updated_at).toBe(1_900_000_005);
    expect(updated.approvals).toHaveLength(2);
    expect(updated.approvals.find((entry) => entry.origin === "https://example.com")).toMatchObject({
      approved_at: 1_900_000_003,
      approved_methods: ["get_public_key", "sign_event"]
    });
    expect(isBrowserExtensionOriginMethodAllowed(updated, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "sign_event"
    })).toBe(true);
    expect(isBrowserExtensionOriginMethodAllowed(updated, {
      origin: "https://other.example",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestB,
      method: "sign_event"
    })).toBe(true);

    const inserted = upsertBrowserExtensionOriginPermissionApproval(
      updated,
      approval("https://a.example", "extension@nsealr.dev", digestB, 1_900_000_006),
      { updatedAt: 1_900_000_007 }
    );
    expect(inserted.approvals.map((entry) => entry.origin)).toEqual([
      "https://a.example",
      "https://example.com",
      "https://other.example"
    ]);
  });

  it("revokes exact approval keys without touching unrelated origins", () => {
    const first = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001);
    const second = approval("https://other.example", "extension@nsealr.dev", digestB, 1_900_000_002);
    const store = createBrowserExtensionOriginPermissionStore([first, second], {
      updatedAt: 1_900_000_003
    });

    const revoked = revokeBrowserExtensionOriginPermissionApproval(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA
    }, {
      updatedAt: 1_900_000_004
    });

    expect(revoked.updated_at).toBe(1_900_000_004);
    expect(revoked.approvals).toEqual([second]);
    expect(isBrowserExtensionOriginMethodAllowed(revoked, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA,
      method: "get_public_key"
    })).toBe(false);
    expect(isBrowserExtensionOriginMethodAllowed(revoked, {
      origin: "https://other.example",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestB,
      method: "sign_event"
    })).toBe(true);
  });

  it("rejects origin permission store mutations that move time backward or use malformed keys", () => {
    const existing = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001);
    const store = createBrowserExtensionOriginPermissionStore([existing], {
      updatedAt: 1_900_000_010
    });

    expect(() => upsertBrowserExtensionOriginPermissionApproval(store, existing, {
      updatedAt: 1_900_000_009
    })).toThrow(/move backward/u);
    expect(() => revokeBrowserExtensionOriginPermissionApproval(store, {
      origin: "https://example.com/path",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA
    }, {
      updatedAt: 1_900_000_011
    })).toThrow(/origin/u);
    expect(() => revokeBrowserExtensionOriginPermissionApproval(store, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: "not-a-digest"
    }, {
      updatedAt: 1_900_000_011
    })).toThrow(/localPairingDigest/u);
  });

  it("rejects malformed or secret-looking store artifacts", () => {
    const store = createBrowserExtensionOriginPermissionStore([
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_001)
    ], {
      updatedAt: 1_900_000_002
    });

    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      nsec: "nsec1..."
    })).toThrow(/unsupported fields/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      writes_extension_storage: true
    })).toThrow(/extension storage/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      creates_grants: true
    })).toThrow(/create grants/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      dispatches_signers: true
    })).toThrow(/dispatch signers/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      stores_production_secrets: true
    })).toThrow(/production secrets/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      contains_secret_material: true
    })).toThrow(/secret material/u);
    expect(() => parseBrowserExtensionOriginPermissionStore({
      ...store,
      updated_at: 1.5
    })).toThrow(/updated_at/u);
  });
});
