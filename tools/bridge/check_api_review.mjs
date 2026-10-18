#!/usr/bin/env node
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { publicPackages, root } from "./package_set.mjs";

const apiDocsPath = join(root, "docs", "api.md");
const reviewPath = join(root, "docs", "api-review.md");

const apiDocs = readFileSync(apiDocsPath, "utf-8");
const review = readFileSync(reviewPath, "utf-8");
const normalizedReview = review.replace(/\s+/gu, " ");
const digest = createHash("sha256").update(apiDocs).digest("hex");

assert(
  review.includes(`API surface digest: \`sha256:${digest}\``),
  "docs/api-review.md must record the current docs/api.md digest"
);

for (const packageName of publicPackages) {
  assert(
    review.includes(`## ${packageName}`),
    `docs/api-review.md must include a review section for ${packageName}`
  );
}

assert(
  review.includes("@nsealr/dev-signer") && review.includes("private and test-only"),
  "docs/api-review.md must keep @nsealr/dev-signer private and test-only"
);
assert(
  !apiDocs.includes("SmartcardSimulator"),
  "docs/api.md must not expose the test-only smartcard simulator through a public package"
);
assert(
  normalizedReview.includes("Test-only APDU simulation lives in the private") &&
    normalizedReview.includes("does not expose software signing helpers"),
  "docs/api-review.md must record that smartcard simulation is private test-only code"
);
assert(
  normalizedReview.includes("parses relay event envelopes") &&
    normalizedReview.includes("evaluates relay request and response steps") &&
    normalizedReview.includes("relay request/response steps") &&
    normalizedReview.includes("digest-bound connect review and approval artifacts") &&
    normalizedReview.includes("verifies signed relay event ids/signatures") &&
    normalizedReview.includes("verifies signed-event result ids/signatures") &&
    normalizedReview.includes("without decrypting NIP-44 content") &&
    normalizedReview.includes("without opening relays"),
  "docs/api-review.md must preserve the current NIP-46 boundary"
);

console.log("companion API review is up to date");
