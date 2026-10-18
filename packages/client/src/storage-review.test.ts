import { describe, expect, it } from "vitest";
import {
  approveLocalStorageReview,
  createLocalStorageReview,
  LOCAL_STORAGE_APPROVAL_FORMAT,
  LOCAL_STORAGE_REVIEW_FORMAT,
  parseLocalStorageApproval,
  parseLocalStorageReview,
  parseLocalStorageReviewEntry,
  requireLocalStorageApprovalEntry
} from "./storage-review.js";

describe("local storage review", () => {
  it("creates digest-bound review metadata for explicit secretless storage locations", () => {
    const review = createLocalStorageReview([
      {
        purpose: "grant_store",
        path: "/Users/example/Library/Application Support/nSealr/local-grants.json",
        access: "write_new",
        contains_secret_material: false
      },
      {
        purpose: "account_store",
        path: "/Users/example/Library/Application Support/nSealr/accounts.json",
        access: "read_only",
        contains_secret_material: false
      }
    ]);

    expect(review).toEqual({
      format: LOCAL_STORAGE_REVIEW_FORMAT,
      storage_digest: expect.stringMatching(/^[0-9a-f]{64}$/u),
      entries: [
        {
          purpose: "grant_store",
          path: "/Users/example/Library/Application Support/nSealr/local-grants.json",
          access: "write_new",
          contains_secret_material: false
        },
        {
          purpose: "account_store",
          path: "/Users/example/Library/Application Support/nSealr/accounts.json",
          access: "read_only",
          contains_secret_material: false
        }
      ],
      requires_user_approval: true,
      stores_production_secrets: false
    });
    expect(parseLocalStorageReview(review)).toEqual(review);
  });

  it("rejects ambiguous paths and secret-bearing storage claims before review", () => {
    expect(() => parseLocalStorageReviewEntry({
      purpose: "grant_store",
      path: "relative/local-grants.json",
      access: "write_new",
      contains_secret_material: false
    })).toThrow(/absolute/u);
    expect(() => parseLocalStorageReviewEntry({
      purpose: "grant_store",
      path: "~/Library/Application Support/nSealr/local-grants.json",
      access: "write_new",
      contains_secret_material: false
    })).toThrow(/expanded/u);
    expect(() => parseLocalStorageReviewEntry({
      purpose: "grant_store",
      path: "/Users/example/../local-grants.json",
      access: "write_new",
      contains_secret_material: false
    })).toThrow(/relative segments/u);
    expect(() => parseLocalStorageReviewEntry({
      purpose: "grant_store",
      path: "/Users/example/local-grants.json",
      access: "write_new",
      contains_secret_material: true
    })).toThrow(/secret material/u);
  });

  it("rejects duplicate locations and digest tampering", () => {
    const entry = {
      purpose: "grant_store",
      path: "/Users/example/Library/Application Support/nSealr/local-grants.json",
      access: "write_new",
      contains_secret_material: false
    };
    expect(() => createLocalStorageReview([entry, entry])).toThrow(/duplicated/u);

    const review = createLocalStorageReview([entry]);
    expect(() => parseLocalStorageReview({
      ...review,
      entries: [{
        ...review.entries[0],
        path: "/Users/example/Library/Application Support/nSealr/other-grants.json"
      }]
    })).toThrow(/digest mismatch/u);
  });

  it("creates approval artifacts only for an exact reviewed storage digest", () => {
    const review = createLocalStorageReview([{
      purpose: "grant_store",
      path: "/Users/example/Library/Application Support/nSealr/local-grants.json",
      access: "write_new",
      contains_secret_material: false
    }]);
    const approval = approveLocalStorageReview(review, { approvedAt: 1_900_000_000 });

    expect(approval).toEqual({
      format: LOCAL_STORAGE_APPROVAL_FORMAT,
      storage_digest: review.storage_digest,
      approved_at: 1_900_000_000,
      review,
      stores_production_secrets: false
    });
    expect(parseLocalStorageApproval(approval)).toEqual(approval);
    expect(() => parseLocalStorageApproval({
      ...approval,
      review: {
        ...review,
        entries: [{
          ...review.entries[0],
          path: "/Users/example/Library/Application Support/nSealr/other-grants.json"
        }]
      }
    })).toThrow(/digest mismatch/u);
    expect(() => parseLocalStorageApproval({
      ...approval,
      stores_production_secrets: true
    })).toThrow(/production secrets/u);
    expect(() => approveLocalStorageReview(review, { approvedAt: -1 })).toThrow(/approvedAt/u);
  });

  it("requires approved entries before local storage writes can use a path", () => {
    const review = createLocalStorageReview([
      {
        purpose: "grant_store",
        path: "/Users/example/Library/Application Support/nSealr/local-grants-input.json",
        access: "read_only",
        contains_secret_material: false
      },
      {
        purpose: "grant_store",
        path: "/Users/example/Library/Application Support/nSealr/local-grants-output.json",
        access: "write_new",
        contains_secret_material: false
      }
    ]);
    const approval = approveLocalStorageReview(review, { approvedAt: 1_900_000_000 });

    expect(requireLocalStorageApprovalEntry(approval, {
      purpose: "grant_store",
      path: "/Users/example/Library/Application Support/nSealr/local-grants-output.json",
      access: "write_new"
    })).toEqual(approval);
    expect(() => requireLocalStorageApprovalEntry(approval, {
      purpose: "grant_store",
      path: "/Users/example/Library/Application Support/nSealr/other-grants.json",
      access: "write_new"
    })).toThrow(/does not cover/u);
    expect(() => requireLocalStorageApprovalEntry(approval, {
      purpose: "account_store",
      path: "/Users/example/Library/Application Support/nSealr/local-grants-output.json",
      access: "write_new"
    })).toThrow(/does not cover/u);
  });
});
