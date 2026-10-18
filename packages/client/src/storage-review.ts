import { sha256Utf8Hex } from "@nsealr/core";

export const LOCAL_STORAGE_REVIEW_FORMAT = "nsealr-local-storage-review-v0";
export const LOCAL_STORAGE_APPROVAL_FORMAT = "nsealr-local-storage-approval-v0";

export const LOCAL_STORAGE_PURPOSES = [
  "grant_store",
  "account_store",
  "route_driver_store"
] as const;

export const LOCAL_STORAGE_ACCESS_MODES = [
  "read_only",
  "write_new"
] as const;

export type LocalStoragePurpose = (typeof LOCAL_STORAGE_PURPOSES)[number];
export type LocalStorageAccessMode = (typeof LOCAL_STORAGE_ACCESS_MODES)[number];

export type LocalStorageReviewEntry = {
  purpose: LocalStoragePurpose;
  path: string;
  access: LocalStorageAccessMode;
  contains_secret_material: false;
};

export type LocalStorageReview = {
  format: typeof LOCAL_STORAGE_REVIEW_FORMAT;
  storage_digest: string;
  entries: LocalStorageReviewEntry[];
  requires_user_approval: true;
  stores_production_secrets: false;
};

export type LocalStorageApproval = {
  format: typeof LOCAL_STORAGE_APPROVAL_FORMAT;
  storage_digest: string;
  approved_at: number;
  review: LocalStorageReview;
  stores_production_secrets: false;
};

export type LocalStorageApprovalRequirement = {
  purpose: LocalStoragePurpose;
  path: string;
  access: LocalStorageAccessMode;
};

type LocalStorageReviewWithoutDigest = Omit<LocalStorageReview, "storage_digest">;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, allowedKeys: string[]): boolean {
  return Object.keys(value).every((key) => allowedKeys.includes(key));
}

function requirePurpose(value: unknown): LocalStoragePurpose {
  if (typeof value !== "string" || !LOCAL_STORAGE_PURPOSES.includes(value as LocalStoragePurpose)) {
    throw new Error("local storage purpose is unsupported");
  }
  return value as LocalStoragePurpose;
}

function requireAccessMode(value: unknown): LocalStorageAccessMode {
  if (typeof value !== "string" || !LOCAL_STORAGE_ACCESS_MODES.includes(value as LocalStorageAccessMode)) {
    throw new Error("local storage access mode is unsupported");
  }
  return value as LocalStorageAccessMode;
}

function isAbsoluteStoragePath(path: string): boolean {
  if (path.startsWith("/")) return true;
  if (/^[A-Za-z]:[\\/]/u.test(path)) return true;
  return path.startsWith("\\\\");
}

function normalizeStoragePath(value: unknown): string {
  if (typeof value !== "string") throw new Error("local storage path must be a string");
  const path = value.trim();
  if (path.length === 0) throw new Error("local storage path must not be empty");
  if (path.length > 4096) throw new Error("local storage path exceeds max length");
  if (/[\0\r\n]/u.test(path)) throw new Error("local storage path contains unsupported control characters");
  if (path.startsWith("~")) throw new Error("local storage path must be expanded before review");
  if (!isAbsoluteStoragePath(path)) throw new Error("local storage path must be absolute");

  const segments = path.split(/[\\/]+/u).filter((segment) => segment.length > 0);
  if (segments.length < 2) throw new Error("local storage path must include a directory and file name");
  if (segments.some((segment) => segment === "." || segment === "..")) {
    throw new Error("local storage path must not contain relative segments");
  }
  return path;
}

function storageReviewDigest(review: LocalStorageReviewWithoutDigest): string {
  return sha256Utf8Hex(JSON.stringify(review));
}

function requireNonNegativeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer`);
  }
  return value;
}

export function parseLocalStorageReviewEntry(value: unknown): LocalStorageReviewEntry {
  if (!isRecord(value)) throw new Error("local storage entry must be an object");
  if (!hasOnlyKeys(value, ["purpose", "path", "access", "contains_secret_material"])) {
    throw new Error("local storage entry has unsupported fields");
  }
  if (value.contains_secret_material !== false) {
    throw new Error("local storage entry must not contain secret material");
  }
  return {
    purpose: requirePurpose(value.purpose),
    path: normalizeStoragePath(value.path),
    access: requireAccessMode(value.access),
    contains_secret_material: false
  };
}

export function createLocalStorageReview(entries: unknown): LocalStorageReview {
  if (!Array.isArray(entries)) throw new Error("local storage entries must be an array");
  if (entries.length === 0) throw new Error("local storage review requires at least one location");
  if (entries.length > 16) throw new Error("local storage review has too many locations");

  const parsedEntries = entries.map(parseLocalStorageReviewEntry);
  const seen = new Set<string>();
  for (const entry of parsedEntries) {
    const key = `${entry.purpose}\0${entry.access}\0${entry.path}`;
    if (seen.has(key)) throw new Error("local storage location is duplicated");
    seen.add(key);
  }

  const withoutDigest: LocalStorageReviewWithoutDigest = {
    format: LOCAL_STORAGE_REVIEW_FORMAT,
    entries: parsedEntries,
    requires_user_approval: true,
    stores_production_secrets: false
  };
  return {
    ...withoutDigest,
    storage_digest: storageReviewDigest(withoutDigest)
  };
}

export function parseLocalStorageReview(value: unknown): LocalStorageReview {
  if (!isRecord(value)) throw new Error("local storage review must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "storage_digest",
    "entries",
    "requires_user_approval",
    "stores_production_secrets"
  ])) {
    throw new Error("local storage review has unsupported fields");
  }
  if (value.format !== LOCAL_STORAGE_REVIEW_FORMAT) {
    throw new Error("local storage review format is unsupported");
  }
  if (typeof value.storage_digest !== "string" || !/^[0-9a-f]{64}$/u.test(value.storage_digest)) {
    throw new Error("local storage review digest is invalid");
  }
  if (value.requires_user_approval !== true) {
    throw new Error("local storage review must require user approval");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("local storage review must not store production secrets");
  }
  if (!Array.isArray(value.entries)) {
    throw new Error("local storage review entries must be an array");
  }
  const review = createLocalStorageReview(value.entries);
  if (review.storage_digest !== value.storage_digest) {
    throw new Error("local storage review digest mismatch");
  }
  return review;
}

export function approveLocalStorageReview(
  review: unknown,
  options: { approvedAt: number }
): LocalStorageApproval {
  const parsedReview = parseLocalStorageReview(review);
  const approvedAt = requireNonNegativeInteger(options.approvedAt, "approvedAt");
  return {
    format: LOCAL_STORAGE_APPROVAL_FORMAT,
    storage_digest: parsedReview.storage_digest,
    approved_at: approvedAt,
    review: parsedReview,
    stores_production_secrets: false
  };
}

export function parseLocalStorageApproval(value: unknown): LocalStorageApproval {
  if (!isRecord(value)) throw new Error("local storage approval must be an object");
  if (!hasOnlyKeys(value, [
    "format",
    "storage_digest",
    "approved_at",
    "review",
    "stores_production_secrets"
  ])) {
    throw new Error("local storage approval has unsupported fields");
  }
  if (value.format !== LOCAL_STORAGE_APPROVAL_FORMAT) {
    throw new Error("local storage approval format is unsupported");
  }
  if (typeof value.storage_digest !== "string" || !/^[0-9a-f]{64}$/u.test(value.storage_digest)) {
    throw new Error("local storage approval digest is invalid");
  }
  const approvedAt = requireNonNegativeInteger(value.approved_at, "local storage approval approved_at");
  const review = parseLocalStorageReview(value.review);
  if (review.storage_digest !== value.storage_digest) {
    throw new Error("local storage approval digest mismatch");
  }
  if (value.stores_production_secrets !== false) {
    throw new Error("local storage approval must not store production secrets");
  }
  return {
    format: LOCAL_STORAGE_APPROVAL_FORMAT,
    storage_digest: value.storage_digest,
    approved_at: approvedAt,
    review,
    stores_production_secrets: false
  };
}

export function requireLocalStorageApprovalEntry(
  approval: unknown,
  requirement: LocalStorageApprovalRequirement
): LocalStorageApproval {
  const parsedApproval = parseLocalStorageApproval(approval);
  const requiredEntry = parseLocalStorageReviewEntry({
    ...requirement,
    contains_secret_material: false
  });
  const matches = parsedApproval.review.entries.some((entry) => (
    entry.purpose === requiredEntry.purpose &&
    entry.access === requiredEntry.access &&
    entry.path === requiredEntry.path
  ));
  if (!matches) {
    throw new Error("local storage approval does not cover requested location");
  }
  return parsedApproval;
}
