# Release Policy

The companion package set is pre-release. No `@nsealr/*` package should be
published until the package, policy, and access-surface gates are green.

## Versioning

- Public companion packages use one synchronized version.
- Current version: `0.1.0`.
- Breaking API changes are allowed before the first public release.
- After publication, SemVer applies to public package exports.
- Private `@nsealr/dev-signer` is not a production package and is never a public
  signing route.

## Public Package Set

- `@nsealr/browser-provider`
- `@nsealr/client`
- `@nsealr/core`
- `@nsealr/fixtures`
- `@nsealr/framing`
- `@nsealr/nip46`
- `@nsealr/policy`
- `@nsealr/protocol`
- `@nsealr/qr`
- `@nsealr/review`
- `@nsealr/sdk`
- `@nsealr/smartcard`
- `@nsealr/transport`

## Release Gates

Before any npm publication:

- `make ci` must pass in `nSealr/companion`.
- `make integration` must pass in `nSealr/lab`.
- Package tarballs must contain only `dist`, README, and package metadata.
- Public package manifests must declare npm-facing descriptions, keywords,
  repository directories, issue tracker, homepage, MIT license, and public
  provenance `publishConfig`.
- `make package-registry` must confirm the publishable package set is derived
  from package manifests and excludes private/test-only packages from every
  public package manifest field.
- Packed tarballs must install into a temporary consumer project and import by
  package name.
- Executable SDK examples must pass against built package entrypoints.
- Public package README snippets must pass against built package entrypoints.
- `docs/api.md` must match the exported symbols of every public package
  entrypoint through `make api-docs`.
- `docs/api-review.md` must record the current `docs/api.md` digest through
  `make api-review`.
- The changelog must describe the release.
- No package may contain production private-key custody. Public package
  manifests and production code must not reference private `@nsealr/dev-signer`.
- Public claims must remain pre-production unless real signer acceptance gates
  are complete.

## Rehearsal Workflow

`.github/workflows/package-release.yml` is a manual package release rehearsal.
It runs `make ci`, renders the digest-bound package release plan with
`make release-plan`, prepares checked package tarballs with
`make release-artifacts`, and uploads those tarballs plus a manifest as a
GitHub Actions artifact.

This workflow does not publish to npm. It is the reviewed artifact-preparation
path that a later publication workflow must build on. The release plan records
the exact public package set, synchronized version, tarball names, provenance
requirements, required local gates, and the rule that local npm publication is
not allowed. The uploaded manifest includes the `release_plan_digest`, then
records every package name, version, tarball filename, byte count, and SHA-256
digest so reviewers can verify that downloaded rehearsal artifacts match the
reviewed package plan exactly.

The release artifact helper may delete and recreate only a child directory
under `release-artifacts/`. `make release-artifacts-safety` is part of CI and
proves dangerous output paths, missing `--out` values, duplicated `--out`
options, and unknown release-artifact options are rejected before cleanup.

## Provenance

Publication should happen only from a reviewed GitHub Actions release workflow
using npm trusted publishing or `npm publish --provenance`.

Local `npm publish` is not an accepted release path. The first public package
publication still requires a separate reviewed workflow change that enables npm
trusted publishing or `npm publish --provenance` from CI.
