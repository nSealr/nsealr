import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** Resolve the one artifact independently of process CWD; no snapshot fallback. */
export function resolveSpecsRoot(preferredRoot?: string): string {
  const root = resolve(preferredRoot ?? process.env.NSEALR_CONTRACTS_ROOT ??
    fileURLToPath(new URL("../../../protocols/contracts/v1/", import.meta.url)));
  const manifest = resolve(root, "manifest.json");
  if (!existsSync(manifest) || !existsSync(resolve(root, "vectors")) || !existsSync(resolve(root, "examples"))) {
    throw new Error(`authoritative contract artifact is missing: ${root}`);
  }
  const identity = JSON.parse(readFileSync(manifest, "utf8"));
  if (identity.artifact_format !== 2 || identity.artifact_id !== "nsealr-contracts-v1") {
    throw new Error("unsupported contract artifact identity");
  }
  return root;
}
