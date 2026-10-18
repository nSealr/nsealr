import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import {
  NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
  NATIVE_HOST_INSTALL_PLAN_FORMAT,
  NATIVE_HOST_NAME,
  nativeHostInstallApprovalJsonFromArgs,
  nativeHostInstallExecutionJsonFromArgs,
  nativeHostInstallPlanJsonFromArgs,
  nativeHostManifestJsonFromArgs
} from "./manifest.js";

const chromiumExtensionId = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const hostPath = "/Applications/nSealr/nsealr-service";
const manifestPath = "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts/dev.nsealr.companion.json";

describe("native host manifest CLI args", () => {
  it("renders manifest JSON from service CLI arguments", () => {
    expect(JSON.parse(nativeHostManifestJsonFromArgs([
      "--",
      "--native-host-manifest",
      "chromium",
      "--host-path",
      hostPath,
      "--extension-id",
      chromiumExtensionId
    ]))).toEqual({
      name: NATIVE_HOST_NAME,
      description: "nSealr companion native messaging host",
      path: hostPath,
      type: "stdio",
      allowed_origins: [`chrome-extension://${chromiumExtensionId}/`]
    });
  });

  it("renders dry-run native-host install plans from service CLI arguments", () => {
    const plan = JSON.parse(nativeHostInstallPlanJsonFromArgs([
      "--",
      "--native-host-install-plan",
      "chromium",
      "--host-path",
      hostPath,
      "--manifest-path",
      manifestPath,
      "--extension-id",
      chromiumExtensionId
    ]));

    expect(plan).toEqual({
      format: NATIVE_HOST_INSTALL_PLAN_FORMAT,
      install_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
      browser: "chromium",
      manifest_path: manifestPath,
      manifest: {
        name: NATIVE_HOST_NAME,
        description: "nSealr companion native messaging host",
        path: hostPath,
        type: "stdio",
        allowed_origins: [`chrome-extension://${chromiumExtensionId}/`]
      },
      would_create_directories: [{
        purpose: "native_host_manifest_parent",
        path: "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts",
        access: "ensure_directory",
        contains_secret_material: false
      }],
      would_write_files: [{
        purpose: "native_host_manifest",
        path: manifestPath,
        access: "write_new",
        contains_secret_material: false
      }],
      requires_user_approval: true,
      writes_files: false,
      stores_production_secrets: false
    });
  });

  it("renders native-host install approval artifacts from service CLI arguments", () => {
    const temp = mkdtempSync(join(tmpdir(), "nsealr-native-host-install-"));
    try {
      const plan = JSON.parse(nativeHostInstallPlanJsonFromArgs([
        "--native-host-install-plan",
        "chromium",
        "--host-path",
        hostPath,
        "--manifest-path",
        manifestPath,
        "--extension-id",
        chromiumExtensionId
      ]));
      const planPath = join(temp, "install-plan.json");
      writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`, "utf8");

      expect(JSON.parse(nativeHostInstallApprovalJsonFromArgs([
        "--native-host-install-approval",
        planPath,
        "--reviewed-install-digest",
        plan.install_digest,
        "--approved-at",
        "1900000000"
      ]))).toEqual({
        format: NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
        install_digest: plan.install_digest,
        approved_at: 1_900_000_000,
        plan,
        requires_user_approval: true,
        writes_files: false,
        stores_production_secrets: false
      });
    } finally {
      rmSync(temp, { recursive: true, force: true });
    }
  });

  it("executes native-host installs only from approved digest-confirmed artifacts", async () => {
    const temp = mkdtempSync(join(tmpdir(), "nsealr-native-host-execute-"));
    try {
      const targetPath = join(temp, "NativeMessagingHosts", "dev.nsealr.companion.json");
      const plan = JSON.parse(nativeHostInstallPlanJsonFromArgs([
        "--native-host-install-plan",
        "chromium",
        "--host-path",
        hostPath,
        "--manifest-path",
        targetPath,
        "--extension-id",
        chromiumExtensionId
      ]));
      const planPath = join(temp, "install-plan.json");
      writeFileSync(planPath, `${JSON.stringify(plan, null, 2)}\n`, "utf8");
      const approval = JSON.parse(nativeHostInstallApprovalJsonFromArgs([
        "--native-host-install-approval",
        planPath,
        "--reviewed-install-digest",
        plan.install_digest,
        "--approved-at",
        "1900000000"
      ]));
      const approvalPath = join(temp, "install-approval.json");
      writeFileSync(approvalPath, `${JSON.stringify(approval, null, 2)}\n`, "utf8");

      const execution = JSON.parse(await nativeHostInstallExecutionJsonFromArgs([
        "--native-host-install-execute",
        approvalPath,
        "--reviewed-install-digest",
        approval.install_digest
      ], {
        async ensureDirectory(path) {
          await mkdir(path, { recursive: true });
        },
        writeFileNew: (path, contents) => writeFile(path, contents, { encoding: "utf8", flag: "wx" })
      }));

      expect(execution).toMatchObject({
        format: "nsealr-native-host-install-execution-v0",
        install_digest: approval.install_digest,
        approved_at: 1_900_000_000,
        manifest_path: targetPath,
        requires_user_approval: true,
        writes_files: true,
        stores_production_secrets: false
      });
      expect(execution.directories_ensured).toEqual(plan.would_create_directories);
      expect(execution.files_written[0]).toMatchObject({
        purpose: "native_host_manifest",
        path: targetPath,
        access: "write_new",
        contains_secret_material: false
      });
      expect(existsSync(targetPath)).toBe(true);
      expect(JSON.parse(readFileSync(targetPath, "utf8"))).toEqual(plan.manifest);

      await expect(nativeHostInstallExecutionJsonFromArgs([
        "--native-host-install-execute",
        approvalPath,
        "--reviewed-install-digest",
        approval.install_digest
      ], {
        ensureDirectory() {},
        writeFileNew() {
          throw new Error("file already exists");
        }
      })).rejects.toThrow(/file already exists/u);
    } finally {
      rmSync(temp, { recursive: true, force: true });
    }
  });

  it("rejects unsafe or ambiguous manifest inputs", async () => {
    expect(() => nativeHostManifestJsonFromArgs([
      "--native-host-manifest",
      "chromium",
      "--host-path"
    ])).toThrow(/host-path requires/u);
    expect(() => nativeHostManifestJsonFromArgs([
      "--native-host-manifest",
      "chromium",
      "--host-path",
      hostPath,
      "--extension-id",
      "bad-extension"
    ])).toThrow(/chromium extension id/u);
    expect(() => nativeHostInstallPlanJsonFromArgs([
      "--native-host-install-plan",
      "chromium",
      "--host-path",
      hostPath,
      "--manifest-path",
      "/Users/example/native-host.txt",
      "--extension-id",
      chromiumExtensionId
    ])).toThrow(/must end with .json/u);
    expect(() => nativeHostInstallApprovalJsonFromArgs([
      "--native-host-install-approval",
      "/tmp/missing-plan.json",
      "--reviewed-install-digest",
      "not-hex",
      "--approved-at",
      "1900000000"
    ])).toThrow(/reviewed-install-digest/u);
    expect(() => nativeHostInstallApprovalJsonFromArgs([
      "--native-host-install-approval",
      "/tmp/missing-plan.json",
      "--reviewed-install-digest",
      "0".repeat(64),
      "--approved-at",
      "9007199254740992"
    ])).toThrow(/approved-at/u);
    await expect(nativeHostInstallExecutionJsonFromArgs([
      "--native-host-install-execute",
      "/tmp/missing-approval.json",
      "--reviewed-install-digest",
      "not-hex"
    ], {
      ensureDirectory() {},
      writeFileNew() {}
    })).rejects.toThrow(/reviewed-install-digest/u);
  });

  it("rejects duplicated singleton native-host CLI options", async () => {
    expect(() => nativeHostManifestJsonFromArgs([
      "--native-host-manifest",
      "chromium",
      "--native-host-manifest",
      "firefox",
      "--host-path",
      hostPath,
      "--extension-id",
      chromiumExtensionId
    ])).toThrow(/native-host-manifest is duplicated/u);
    expect(() => nativeHostInstallPlanJsonFromArgs([
      "--native-host-install-plan",
      "chromium",
      "--host-path",
      hostPath,
      "--host-path",
      "/Applications/nSealr/other-service",
      "--manifest-path",
      manifestPath,
      "--extension-id",
      chromiumExtensionId
    ])).toThrow(/host-path is duplicated/u);
    expect(() => nativeHostInstallPlanJsonFromArgs([
      "--native-host-install-plan",
      "chromium",
      "--host-path",
      hostPath,
      "--manifest-path",
      manifestPath,
      "--manifest-path",
      "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts/other.json",
      "--extension-id",
      chromiumExtensionId
    ])).toThrow(/manifest-path is duplicated/u);
    expect(() => nativeHostInstallApprovalJsonFromArgs([
      "--native-host-install-approval",
      "/tmp/install-plan-a.json",
      "--native-host-install-approval",
      "/tmp/install-plan-b.json",
      "--reviewed-install-digest",
      "0".repeat(64),
      "--approved-at",
      "1900000000"
    ])).toThrow(/native-host-install-approval is duplicated/u);
    expect(() => nativeHostInstallApprovalJsonFromArgs([
      "--native-host-install-approval",
      "/tmp/install-plan.json",
      "--reviewed-install-digest",
      "0".repeat(64),
      "--reviewed-install-digest",
      "1".repeat(64),
      "--approved-at",
      "1900000000"
    ])).toThrow(/reviewed-install-digest is duplicated/u);
    expect(() => nativeHostInstallApprovalJsonFromArgs([
      "--native-host-install-approval",
      "/tmp/install-plan.json",
      "--reviewed-install-digest",
      "0".repeat(64),
      "--approved-at",
      "1900000000",
      "--approved-at",
      "1900000001"
    ])).toThrow(/approved-at is duplicated/u);
    await expect(nativeHostInstallExecutionJsonFromArgs([
      "--native-host-install-execute",
      "/tmp/install-approval-a.json",
      "--native-host-install-execute",
      "/tmp/install-approval-b.json",
      "--reviewed-install-digest",
      "0".repeat(64)
    ], {
      ensureDirectory() {},
      writeFileNew() {}
    })).rejects.toThrow(/native-host-install-execute is duplicated/u);
    await expect(nativeHostInstallExecutionJsonFromArgs([
      "--native-host-install-execute",
      "/tmp/install-approval.json",
      "--reviewed-install-digest",
      "0".repeat(64),
      "--reviewed-install-digest",
      "1".repeat(64)
    ], {
      ensureDirectory() {},
      writeFileNew() {}
    })).rejects.toThrow(/reviewed-install-digest is duplicated/u);
  });
});
