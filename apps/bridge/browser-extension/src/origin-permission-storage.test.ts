import { describe, expect, it } from "vitest";
import {
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval,
  type BrowserExtensionOriginPermissionReview
} from "./pairing.js";
import {
  createBrowserExtensionOriginPermissionStore
} from "./origin-permission-store.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
  parseBrowserExtensionOriginPermissionStorageWriteResult,
  readBrowserExtensionOriginPermissionStoreFromStorage,
  removeBrowserExtensionOriginPermissionStoreFromStorage,
  revokeBrowserExtensionOriginPermissionApprovalInStorage,
  upsertBrowserExtensionOriginPermissionApprovalInStorage,
  writeBrowserExtensionOriginPermissionStoreToStorage,
  type BrowserExtensionOriginPermissionStorageArea
} from "./origin-permission-storage.js";

const digestA = "a".repeat(64);
const digestB = "b".repeat(64);

class FakeOriginPermissionStorage implements BrowserExtensionOriginPermissionStorageArea {
  readonly getCalls: unknown[] = [];
  readonly setCalls: unknown[] = [];
  readonly removeCalls: unknown[] = [];
  private stored: Record<string, unknown> = {};

  constructor(initial: unknown = undefined) {
    if (initial !== undefined) {
      this.stored[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY] = initial;
    }
  }

  get(key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY): unknown {
    this.getCalls.push(key);
    if (!(key in this.stored)) return {};
    return {
      [key]: this.stored[key]
    };
  }

  set(items: {
    [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: unknown;
  }): void {
    this.setCalls.push(items);
    this.stored[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY] =
      items[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY];
  }

  remove(key: typeof BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY): void {
    this.removeCalls.push(key);
    delete this.stored[key];
  }
}

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

describe("browser extension origin permission storage adapter", () => {
  it("loads a deterministic empty store when the storage key is absent", async () => {
    const storage = new FakeOriginPermissionStorage();

    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(storage, {
      emptyUpdatedAt: 1_900_000_700
    })).resolves.toEqual({
      format: "nsealr-browser-origin-permission-store-v0",
      updated_at: 1_900_000_700,
      approvals: [],
      requires_user_approval: true,
      writes_extension_storage: false,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(storage.getCalls).toEqual([BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]);
    expect(storage.setCalls).toEqual([]);
  });

  it("loads and validates an existing secretless approval store", async () => {
    const existing = createBrowserExtensionOriginPermissionStore([
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_701)
    ], {
      updatedAt: 1_900_000_702
    });
    const storage = new FakeOriginPermissionStorage(existing);

    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(storage)).resolves.toEqual(existing);
  });

  it("writes only the validated store artifact and returns explicit storage-write metadata", async () => {
    const store = createBrowserExtensionOriginPermissionStore([
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_701)
    ], {
      updatedAt: 1_900_000_702
    });
    const storage = new FakeOriginPermissionStorage();

    await expect(writeBrowserExtensionOriginPermissionStoreToStorage(storage, store)).resolves.toEqual({
      format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
      storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
      store_format: "nsealr-browser-origin-permission-store-v0",
      updated_at: 1_900_000_702,
      approval_count: 1,
      requires_user_approval: true,
      reads_extension_storage: false,
      writes_extension_storage: true,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false,
      contains_secret_material: false
    });
    expect(storage.setCalls).toEqual([{
      [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: store
    }]);
    expect(parseBrowserExtensionOriginPermissionStorageWriteResult({
      format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
      storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
      store_format: "nsealr-browser-origin-permission-store-v0",
      updated_at: 1_900_000_702,
      approval_count: 1,
      requires_user_approval: true,
      reads_extension_storage: false,
      writes_extension_storage: true,
      creates_grants: false,
      dispatches_signers: false,
      stores_production_secrets: false,
      contains_secret_material: false
    })).toMatchObject({
      updated_at: 1_900_000_702,
      approval_count: 1,
      writes_extension_storage: true,
      dispatches_signers: false
    });
  });

  it("upserts and revokes approvals without mutating unrelated origins", async () => {
    const existing = createBrowserExtensionOriginPermissionStore([
      approval("https://other.example", "extension@nsealr.dev", digestB, 1_900_000_701)
    ], {
      updatedAt: 1_900_000_702
    });
    const storage = new FakeOriginPermissionStorage(existing);
    const nextApproval = approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_703);

    await expect(upsertBrowserExtensionOriginPermissionApprovalInStorage(
      storage,
      nextApproval,
      {
        emptyUpdatedAt: 1_900_000_700,
        updatedAt: 1_900_000_704
      }
    )).resolves.toMatchObject({
      updated_at: 1_900_000_704,
      approval_count: 2,
      reads_extension_storage: true,
      writes_extension_storage: true,
      stores_production_secrets: false
    });

    const storedAfterUpsert = await readBrowserExtensionOriginPermissionStoreFromStorage(storage);
    expect(storedAfterUpsert.approvals.map((entry) => entry.origin)).toEqual([
      "https://example.com",
      "https://other.example"
    ]);

    await expect(revokeBrowserExtensionOriginPermissionApprovalInStorage(storage, {
      origin: "https://example.com",
      extensionId: "extension@nsealr.dev",
      localPairingDigest: digestA
    }, {
      updatedAt: 1_900_000_705
    })).resolves.toMatchObject({
      updated_at: 1_900_000_705,
      approval_count: 1,
      reads_extension_storage: true
    });
    const storedAfterRevoke = await readBrowserExtensionOriginPermissionStoreFromStorage(storage);
    expect(storedAfterRevoke.approvals.map((entry) => entry.origin)).toEqual([
      "https://other.example"
    ]);
  });

  it("removes the store only through an explicit remove dependency", async () => {
    const existing = createBrowserExtensionOriginPermissionStore([
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_701)
    ], {
      updatedAt: 1_900_000_702
    });
    const storage = new FakeOriginPermissionStorage(existing);

    await expect(removeBrowserExtensionOriginPermissionStoreFromStorage(storage, {
      removedAt: 1_900_000_706
    })).resolves.toMatchObject({
      updated_at: 1_900_000_706,
      approval_count: 0,
      reads_extension_storage: false,
      writes_extension_storage: true,
      stores_production_secrets: false
    });
    expect(storage.removeCalls).toEqual([BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]);
    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(storage)).resolves.toMatchObject({
      approvals: []
    });
  });

  it("rejects invalid dependencies, malformed reads, secret-looking stores, and stale writes", async () => {
    await expect(readBrowserExtensionOriginPermissionStoreFromStorage({} as never))
      .rejects.toThrow(/storage area/u);

    await expect(readBrowserExtensionOriginPermissionStoreFromStorage({
      get() {
        return {
          [BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY]: createBrowserExtensionOriginPermissionStore([], {
            updatedAt: 0
          }),
          extra: true
        };
      },
      set() {}
    })).rejects.toThrow(/unsupported fields/u);

    await expect(readBrowserExtensionOriginPermissionStoreFromStorage(new FakeOriginPermissionStorage({
      nsec: "nsec1secret"
    }))).rejects.toThrow(/unsupported|format/u);

    const existing = createBrowserExtensionOriginPermissionStore([], {
      updatedAt: 1_900_000_800
    });
    await expect(upsertBrowserExtensionOriginPermissionApprovalInStorage(
      new FakeOriginPermissionStorage(existing),
      approval("https://example.com", "extension@nsealr.dev", digestA, 1_900_000_801),
      {
        updatedAt: 1_900_000_799
      }
    )).rejects.toThrow(/move backward/u);

    await expect(removeBrowserExtensionOriginPermissionStoreFromStorage({
      get() {
        return {};
      },
      set() {}
    }, {
      removedAt: 1_900_000_802
    })).rejects.toThrow(/remove dependency/u);

    await expect(removeBrowserExtensionOriginPermissionStoreFromStorage(
      new FakeOriginPermissionStorage(),
      { removedAt: -1 }
    )).rejects.toThrow(/removedAt/u);

    expect(() => parseBrowserExtensionOriginPermissionStorageWriteResult({
      format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_WRITE_FORMAT,
      storage_key: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
      store_format: "nsealr-browser-origin-permission-store-v0",
      updated_at: 1_900_000_803,
      approval_count: 0,
      requires_user_approval: true,
      reads_extension_storage: false,
      writes_extension_storage: true,
      creates_grants: false,
      dispatches_signers: true,
      stores_production_secrets: false,
      contains_secret_material: false
    })).toThrow(/unsafe effects/u);
  });
});
