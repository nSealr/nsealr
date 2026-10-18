import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT
} from "./pairing.js";
import {
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT
} from "./origin-permission-store.js";
import {
  browserExtensionOriginPermissionApprovalJsonFromArgs,
  browserExtensionOriginPermissionStoreCreateJsonFromArgs,
  browserExtensionOriginPermissionStoreRevokeJsonFromArgs,
  browserExtensionOriginPermissionStoreUpsertJsonFromArgs
} from "./origin-permission-cli.js";

const localPairingDigest = "a".repeat(64);
const extensionId = "extension@nsealr.dev";

function tempRoot(): { root: string; cleanup(): void } {
  const root = mkdtempSync(join(tmpdir(), "nsealr-origin-permission-cli-"));
  return {
    root,
    cleanup(): void {
      rmSync(root, { recursive: true, force: true });
    }
  };
}

function writeJson(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function review(methods: readonly ("get_public_key" | "sign_event")[] = ["get_public_key", "sign_event"]): unknown {
  return {
    format: BROWSER_EXTENSION_ORIGIN_PERMISSION_REVIEW_FORMAT,
    origin: "https://example.com",
    app_name: "Example",
    extension_id: extensionId,
    requested_methods: methods.map((method) => (
      method === "get_public_key"
        ? {
            method,
            label: "Read public key",
            effect: "The page can read the selected account public key through the browser provider."
          }
        : {
            method,
            label: "Request event signatures",
            effect: "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy."
          }
    )),
    local_pairing_digest: localPairingDigest,
    requires_user_approval: true,
    stores_production_secrets: false,
    creates_grants: false,
    injects_provider: false
  };
}

describe("browser extension origin-permission CLI", () => {
  it("creates an approved origin-permission store without writing browser storage", () => {
    const temp = tempRoot();
    try {
      const reviewPath = join(temp.root, "origin-review.json");
      const approvalPath = join(temp.root, "origin-approval.json");
      const storePath = join(temp.root, "origin-store.json");
      writeJson(reviewPath, review(["get_public_key"]));

      const approval = JSON.parse(browserExtensionOriginPermissionApprovalJsonFromArgs([
        "--review",
        reviewPath,
        "--reviewed-local-pairing-digest",
        localPairingDigest,
        "--approved-at",
        "1900000000"
      ]));
      expect(approval).toMatchObject({
        format: "nsealr-browser-origin-permission-approval-v0",
        origin: "https://example.com",
        extension_id: extensionId,
        approved_methods: ["get_public_key"],
        local_pairing_digest: localPairingDigest,
        requires_user_approval: true,
        authorizes_provider_injection: true,
        creates_grants: false,
        stores_production_secrets: false,
        contains_secret_material: false
      });
      writeJson(approvalPath, approval);

      const emptyStore = JSON.parse(browserExtensionOriginPermissionStoreCreateJsonFromArgs([
        "--updated-at",
        "1900000001"
      ]));
      expect(emptyStore).toEqual({
        format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
        updated_at: 1900000001,
        approvals: [],
        requires_user_approval: true,
        writes_extension_storage: false,
        creates_grants: false,
        dispatches_signers: false,
        stores_production_secrets: false,
        contains_secret_material: false
      });
      writeJson(storePath, emptyStore);

      const updatedStore = JSON.parse(browserExtensionOriginPermissionStoreUpsertJsonFromArgs([
        "--store",
        storePath,
        "--approval",
        approvalPath,
        "--updated-at",
        "1900000002"
      ]));
      expect(updatedStore).toMatchObject({
        format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
        updated_at: 1900000002,
        approvals: [approval],
        writes_extension_storage: false,
        creates_grants: false,
        dispatches_signers: false,
        stores_production_secrets: false,
        contains_secret_material: false
      });
    } finally {
      temp.cleanup();
    }
  });

  it("revokes an exact approved origin-permission key", () => {
    const temp = tempRoot();
    try {
      const reviewPath = join(temp.root, "origin-review.json");
      const approvalPath = join(temp.root, "origin-approval.json");
      const storePath = join(temp.root, "origin-store.json");
      writeJson(reviewPath, review());
      const approval = JSON.parse(browserExtensionOriginPermissionApprovalJsonFromArgs([
        "--review",
        reviewPath,
        "--reviewed-local-pairing-digest",
        localPairingDigest,
        "--approved-at",
        "1900000000"
      ]));
      writeJson(approvalPath, approval);
      writeJson(storePath, JSON.parse(browserExtensionOriginPermissionStoreCreateJsonFromArgs([
        "--updated-at",
        "1900000000"
      ])));
      const store = JSON.parse(browserExtensionOriginPermissionStoreUpsertJsonFromArgs([
        "--store",
        storePath,
        "--approval",
        approvalPath,
        "--updated-at",
        "1900000001"
      ]));
      writeJson(storePath, store);

      const revoked = JSON.parse(browserExtensionOriginPermissionStoreRevokeJsonFromArgs([
        "--store",
        storePath,
        "--origin",
        "https://example.com",
        "--extension-id",
        extensionId,
        "--local-pairing-digest",
        localPairingDigest,
        "--updated-at",
        "1900000002"
      ]));
      expect(revoked).toMatchObject({
        format: BROWSER_EXTENSION_ORIGIN_PERMISSION_STORE_FORMAT,
        updated_at: 1900000002,
        approvals: [],
        writes_extension_storage: false,
        creates_grants: false,
        dispatches_signers: false,
        stores_production_secrets: false,
        contains_secret_material: false
      });
    } finally {
      temp.cleanup();
    }
  });

  it("rejects incomplete, tampered, or backward-moving origin-permission artifacts", () => {
    const temp = tempRoot();
    try {
      const reviewPath = join(temp.root, "origin-review.json");
      const storePath = join(temp.root, "origin-store.json");
      writeJson(reviewPath, review());
      writeJson(storePath, JSON.parse(browserExtensionOriginPermissionStoreCreateJsonFromArgs([
        "--updated-at",
        "1900000002"
      ])));

      expect(() => browserExtensionOriginPermissionApprovalJsonFromArgs([
        "--review",
        reviewPath,
        "--reviewed-local-pairing-digest",
        "b".repeat(64),
        "--approved-at",
        "1900000000"
      ])).toThrow(/digest/u);
      expect(() => browserExtensionOriginPermissionStoreCreateJsonFromArgs([])).toThrow(/updated-at/u);
      expect(() => browserExtensionOriginPermissionStoreUpsertJsonFromArgs([
        "--store",
        storePath,
        "--approval",
        reviewPath,
        "--updated-at",
        "1900000003"
      ])).toThrow(/approval/u);
      expect(() => browserExtensionOriginPermissionStoreRevokeJsonFromArgs([
        "--store",
        storePath,
        "--origin",
        "https://example.com",
        "--extension-id",
        extensionId,
        "--local-pairing-digest",
        localPairingDigest,
        "--updated-at",
        "1900000001"
      ])).toThrow(/backward/u);
      expect(() => browserExtensionOriginPermissionStoreCreateJsonFromArgs([
        "--updated-at",
        "1900000000",
        "--review",
        reviewPath
      ])).toThrow(/not supported/u);
    } finally {
      temp.cleanup();
    }
  });
});
