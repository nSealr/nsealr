#!/usr/bin/env node
import assert from "node:assert/strict";
import { rmSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { packageDirName, publicPackages, root, run } from "./package_set.mjs";

const marker = "nsealr-readme-example";
const tempParent = join(root, "apps", "sdk-examples", ".tmp");
const tempRoot = join(tempParent, "readme-examples");

function readmePath(packageName) {
  return join(root, "packages", packageDirName(packageName), "README.md");
}

function extractExamples(packageName) {
  const path = readmePath(packageName);
  const lines = readFileSync(path, "utf-8").split(/\r?\n/u);
  const examples = [];
  let current = null;

  for (const line of lines) {
    const fence = line.match(/^```([^\s`]*)?(?:\s+(.*))?$/u);
    if (fence) {
      if (current === null) {
        const language = fence[1] ?? "";
        const info = fence[2] ?? "";
        current = info.split(/\s+/u).includes(marker)
          ? { language, lines: [] }
          : { language: "", lines: null };
        continue;
      }

      if (current.lines !== null) {
        assert.equal(current.language, "ts", `${packageName} README examples must use TypeScript fences`);
        examples.push(current.lines.join("\n"));
      }
      current = null;
      continue;
    }

    if (current !== null && current.lines !== null) {
      current.lines.push(line);
    }
  }

  assert.equal(current, null, `${packageName} README has an unclosed fenced code block`);
  return examples;
}

rmSync(tempRoot, { recursive: true, force: true });
mkdirSync(tempRoot, { recursive: true });

let count = 0;
try {
  for (const packageName of publicPackages) {
    const examples = extractExamples(packageName);
    assert(examples.length > 0, `${packageName} README must include at least one ${marker} snippet`);
    for (const [index, source] of examples.entries()) {
      const examplePath = join(tempRoot, `${packageDirName(packageName)}-${index + 1}.ts`);
      writeFileSync(examplePath, `${source.trimEnd()}\n`, "utf-8");
      run("node", ["--no-warnings", "--import", "tsx/esm", examplePath]);
      count += 1;
    }
  }

  console.log(`nSealr README examples passed (${count} snippets)`);
} finally {
  rmSync(tempParent, { recursive: true, force: true });
}
