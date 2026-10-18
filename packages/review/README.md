# @nsealr/review

Deterministic review projections for nSealr signing requests.

## Purpose

- Produce host-side review summaries from event templates.
- Produce digest-bound screen and detail-page data used by conformance tests.
- Keep review rendering behavior consistent across companion, Raspberry, ESP32,
  and smartcard-adjacent flows.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import {
  approvalDigestForRequest,
  renderReviewDetailPages,
  reviewEventTemplate
} from "@nsealr/review";

const authorPubkey = "1".repeat(64);
const eventTemplate = {
  created_at: 1_710_000_000,
  kind: 1,
  tags: [],
  content: "review this event"
};
const request = {
  version: 1,
  request_id: "readme-review",
  method: "sign_event",
  params: { event_template: eventTemplate }
};

const review = reviewEventTemplate(eventTemplate, authorPubkey);
const pages = renderReviewDetailPages(review, {
  max_title_chars: 18,
  max_body_lines: 5,
  max_line_chars: 26,
  max_compact_body_lines: 9,
  max_compact_line_chars: 48
});

assert(pages.length > 0);
assert.equal(approvalDigestForRequest(request, authorPubkey).length, 64);
```

## Boundary

Companion review output is not a trusted approval surface. Trusted review must
happen on the signer hardware or on the appropriate external review surface for
display-less routes.
