import { existsSync } from "node:fs";
import { resolve } from "node:path";

export function resolveSpecsRoot(preferredRoot = resolve("../specs")): string {
  if (existsSync(resolve(preferredRoot, "vectors")) && existsSync(resolve(preferredRoot, "examples"))) {
    return preferredRoot;
  }

  const fallbackRoot = resolve(process.cwd(), "tests/fixtures/specs");
  if (existsSync(resolve(fallbackRoot, "vectors")) && existsSync(resolve(fallbackRoot, "examples"))) {
    return fallbackRoot;
  }

  return preferredRoot;
}
