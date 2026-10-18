import { describe, expect, it } from "vitest";
import {
  NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
  NATIVE_HOST_INSTALL_EXECUTION_FORMAT,
  NATIVE_HOST_DESCRIPTION,
  NATIVE_HOST_INSTALL_PLAN_FORMAT,
  NATIVE_HOST_NAME,
  approveNativeHostInstallPlan,
  buildNativeHostInstallPlan,
  buildNativeHostManifest,
  executeNativeHostInstallApproval,
  parseNativeHostInstallApproval,
  parseNativeHostInstallExecution,
  parseNativeHostInstallPlan
} from "./index.js";

const chromiumExtensionId = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const hostPath = "/Applications/nSealr/nsealr-service";
const manifestPath = "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts/dev.nsealr.companion.json";
const manifestParent = "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts";

describe("native host manifest contract", () => {
  it("builds a deterministic Chromium native-messaging manifest", () => {
    expect(buildNativeHostManifest({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId, chromiumExtensionId]
    })).toEqual({
      name: NATIVE_HOST_NAME,
      description: NATIVE_HOST_DESCRIPTION,
      path: hostPath,
      type: "stdio",
      allowed_origins: [`chrome-extension://${chromiumExtensionId}/`]
    });
  });

  it("builds a deterministic Firefox native-messaging manifest", () => {
    expect(buildNativeHostManifest({
      browser: "firefox",
      hostPath,
      extensionIds: ["extension@nsealr.dev"]
    })).toEqual({
      name: NATIVE_HOST_NAME,
      description: NATIVE_HOST_DESCRIPTION,
      path: hostPath,
      type: "stdio",
      allowed_extensions: ["extension@nsealr.dev"]
    });
  });

  it("rejects unsafe native-host manifest inputs", () => {
    expect(() => buildNativeHostManifest({
      browser: "chromium",
      hostPath: "relative-service",
      extensionIds: [chromiumExtensionId]
    })).toThrow(/path must be absolute/u);
    expect(() => buildNativeHostManifest({
      browser: "chromium",
      hostPath,
      extensionIds: ["bad-extension"]
    })).toThrow(/chromium extension id/u);
    expect(() => buildNativeHostManifest({
      browser: "firefox",
      hostPath,
      extensionIds: []
    })).toThrow(/at least one extension/u);
  });

  it("builds a dry-run native-host install plan without writing files", () => {
    const manifest = buildNativeHostManifest({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId]
    });

    const plan = buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath
    });

    expect(plan).toEqual({
      format: NATIVE_HOST_INSTALL_PLAN_FORMAT,
      install_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
      browser: "chromium",
      manifest_path: manifestPath,
      manifest,
      would_create_directories: [{
        purpose: "native_host_manifest_parent",
        path: manifestParent,
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
    expect(parseNativeHostInstallPlan(plan)).toEqual(plan);
  });

  it("rejects unsafe native-host install plan paths", () => {
    expect(() => buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath: "NativeMessagingHosts/dev.nsealr.companion.json"
    })).toThrow(/manifest path must be absolute/u);
    expect(() => buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath: "~/Library/Application Support/Google/Chrome/NativeMessagingHosts/dev.nsealr.companion.json"
    })).toThrow(/expanded/u);
    expect(() => buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath: "/Users/example/../NativeMessagingHosts/dev.nsealr.companion.json"
    })).toThrow(/relative segments/u);
    expect(() => buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath: "/Users/example/NativeMessagingHosts/dev.nsealr.companion.txt"
    })).toThrow(/must end with .json/u);
  });

  it("rejects native-host install plan tampering", () => {
    const plan = buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath
    });

    expect(() => parseNativeHostInstallPlan({
      ...plan,
      writes_files: true
    })).toThrow(/must not write/u);
    expect(() => parseNativeHostInstallPlan({
      ...plan,
      manifest: {
        ...plan.manifest,
        description: "tampered native host"
      }
    })).toThrow(/digest mismatch/u);
    expect(() => parseNativeHostInstallPlan({
      ...plan,
      would_create_directories: [{
        ...plan.would_create_directories[0],
        access: "create_parent"
      }]
    })).toThrow(/directory intent/u);
    expect(() => parseNativeHostInstallPlan({
      ...plan,
      would_write_files: [{
        ...plan.would_write_files[0],
        access: "overwrite"
      }]
    })).toThrow(/write intent/u);
  });

  it("creates native-host install approval artifacts only after digest confirmation", () => {
    const plan = buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath
    });
    const approval = approveNativeHostInstallPlan(plan, {
      reviewedInstallDigest: plan.install_digest,
      approvedAt: 1_900_000_000
    });

    expect(approval).toEqual({
      format: NATIVE_HOST_INSTALL_APPROVAL_FORMAT,
      install_digest: plan.install_digest,
      approved_at: 1_900_000_000,
      plan,
      requires_user_approval: true,
      writes_files: false,
      stores_production_secrets: false
    });
    expect(parseNativeHostInstallApproval(approval)).toEqual(approval);
    expect(() => approveNativeHostInstallPlan(plan, {
      reviewedInstallDigest: "0".repeat(64),
      approvedAt: 1_900_000_000
    })).toThrow(/digest does not match/u);
    expect(() => approveNativeHostInstallPlan(plan, {
      reviewedInstallDigest: plan.install_digest,
      approvedAt: Number.MAX_SAFE_INTEGER + 1
    })).toThrow(/approvedAt/u);
    expect(() => parseNativeHostInstallApproval({
      ...approval,
      plan: {
        ...plan,
        install_digest: "0".repeat(64)
      }
    })).toThrow(/digest mismatch/u);
  });

  it("executes approved native-host installs through an explicit write-new adapter", async () => {
    const plan = buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath
    });
    const approval = approveNativeHostInstallPlan(plan, {
      reviewedInstallDigest: plan.install_digest,
      approvedAt: 1_900_000_000
    });
    const ensured: string[] = [];
    const written: Array<{ path: string; contents: string }> = [];

    const result = await executeNativeHostInstallApproval(approval, {
      reviewedInstallDigest: plan.install_digest,
      writer: {
        ensureDirectory(path) {
          ensured.push(path);
        },
        writeFileNew(path, contents) {
          written.push({ path, contents });
        }
      }
    });

    expect(ensured).toEqual([manifestParent]);
    const writtenContents = written[0]?.contents;
    if (writtenContents === undefined) throw new Error("native host manifest was not written");
    expect(written).toEqual([{
      path: manifestPath,
      contents: writtenContents
    }]);
    expect(writtenContents).toBe(`${JSON.stringify(plan.manifest, null, 2)}\n`);
    expect(result).toEqual({
      format: NATIVE_HOST_INSTALL_EXECUTION_FORMAT,
      install_digest: plan.install_digest,
      approved_at: 1_900_000_000,
      browser: "chromium",
      manifest_path: manifestPath,
      directories_ensured: [{
        purpose: "native_host_manifest_parent",
        path: manifestParent,
        access: "ensure_directory",
        contains_secret_material: false
      }],
      files_written: [{
        purpose: "native_host_manifest",
        path: manifestPath,
        access: "write_new",
        bytes: new TextEncoder().encode(writtenContents).byteLength,
        sha256: expect.stringMatching(/^[0-9a-f]{64}$/u),
        contains_secret_material: false
      }],
      requires_user_approval: true,
      writes_files: true,
      stores_production_secrets: false
    });
    expect(parseNativeHostInstallExecution(result)).toEqual(result);
    expect(() => parseNativeHostInstallExecution({
      ...result,
      writes_files: false
    })).toThrow(/file writes/u);
    expect(() => parseNativeHostInstallExecution({
      ...result,
      files_written: [{
        ...result.files_written[0],
        access: "overwrite"
      }]
    })).toThrow(/file report/u);
  });

  it("rejects install execution before writing when the reviewed digest is wrong", async () => {
    const plan = buildNativeHostInstallPlan({
      browser: "chromium",
      hostPath,
      extensionIds: [chromiumExtensionId],
      manifestPath
    });
    const approval = approveNativeHostInstallPlan(plan, {
      reviewedInstallDigest: plan.install_digest,
      approvedAt: 1_900_000_000
    });
    let wrote = false;

    await expect(executeNativeHostInstallApproval(approval, {
      reviewedInstallDigest: "0".repeat(64),
      writer: {
        ensureDirectory() {
          wrote = true;
        },
        writeFileNew() {
          wrote = true;
        }
      }
    })).rejects.toThrow(/digest does not match/u);
    expect(wrote).toBe(false);
  });
});
