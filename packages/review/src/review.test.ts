import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  approvalDigestForRequest,
  REVIEW_DETAIL_BODY_LINE_STYLES,
  renderReviewDetailPages,
  reviewEventTemplate,
  screenReviewForRequest,
  type EventReview,
  type ReviewDetailPage,
  type ReviewDetailPageLimits,
  type ScreenReview
} from "./review.js";

const specsRoot = resolveSpecsRoot();

function resolveSpecsRoot(preferredRoot = resolve("../specs")): string {
  if (existsSync(resolve(preferredRoot, "vectors")) && existsSync(resolve(preferredRoot, "examples"))) {
    return preferredRoot;
  }
  const fallbackRoot = resolve(process.cwd(), "tests/fixtures/specs");
  if (existsSync(resolve(fallbackRoot, "vectors")) && existsSync(resolve(fallbackRoot, "examples"))) {
    return fallbackRoot;
  }
  return preferredRoot;
}

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

function loadVectorDirectory(directory: string): Array<Record<string, unknown>> {
  return readdirSync(directory)
    .filter((entry) => entry.endsWith(".json"))
    .sort()
    .map((entry) => loadJson(resolve(directory, entry)) as Record<string, unknown>);
}

type ReviewVector = {
  name: string;
  request: unknown;
  review: EventReview;
};

type ReviewScreenVector = {
  request: unknown;
  screen_review: ScreenReview;
};

type ReviewDetailPageVector = {
  source_review_vector: string;
  approval_digest: string;
  limits: ReviewDetailPageLimits;
  pages: ReviewDetailPage[];
};

describe("trusted review model", () => {
  it("exports only the shared review detail-page body styles", () => {
    expect(REVIEW_DETAIL_BODY_LINE_STYLES).toEqual(["meta", "normal", "value"]);
  });

  it("matches every shared trusted-review vector", () => {
    const reviews = loadVectorDirectory(resolve(specsRoot, "vectors/review")) as ReviewVector[];

    for (const vector of reviews) {
      const request = vector.request as {
        params: { event_template: unknown };
      };

      expect(reviewEventTemplate(request.params.event_template)).toEqual(vector.review);
    }
  });

  it("matches every shared trusted review-screen vector and approval digest", () => {
    const reviewScreens = loadVectorDirectory(resolve(specsRoot, "vectors/review-screens")) as ReviewScreenVector[];

    for (const vector of reviewScreens) {
      expect(screenReviewForRequest(vector.request)).toEqual(vector.screen_review);
      expect(approvalDigestForRequest(vector.request)).toBe(vector.screen_review.approval_digest);
    }
  });

  it("matches every shared review detail-page vector", () => {
    const reviews = loadVectorDirectory(resolve(specsRoot, "vectors/review")) as ReviewVector[];
    const reviewDetailPages = loadVectorDirectory(resolve(specsRoot, "vectors/review-detail-pages")) as ReviewDetailPageVector[];

    for (const vector of reviewDetailPages) {
      const reviewVector = reviews.find((review) => review.name === vector.source_review_vector);
      expect(reviewVector).toBeDefined();
      expect(renderReviewDetailPages(reviewVector!.review, vector.limits)).toEqual(vector.pages);
      expect(approvalDigestForRequest(reviewVector!.request)).toBe(vector.approval_digest);
    }
  });

  it("renders decoded JSON control characters as visible escapes", () => {
    const pages = renderReviewDetailPages(
      {
        kind: 1,
        created_at: 1710000480,
        author_pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
        content: "line 1\nline 2\tTabbed\rCarriage\bBackspace\fFormfeed",
        content_utf8_bytes: 48,
        tag_count: 2,
        tags: [
          ["t", "line\nbreak"],
          ["subject", "tab\tvalue", "carriage\rreturn"]
        ]
      },
      {
        max_title_chars: 18,
        max_body_lines: 5,
        max_line_chars: 26,
        max_compact_body_lines: 9,
        max_compact_line_chars: 48
      }
    );

    expect(pages[1].lines).toContain("line 1\\nline 2\\tTabbed\\rCarriage\\bBackspace\\fFor");
    expect(pages[2].lines).toContain("line\\nbreak");
    expect(pages[2].lines).toContain("tab\\tvalue");
    expect(pages[2].lines).toContain("carriage\\rreturn");
  });
});
