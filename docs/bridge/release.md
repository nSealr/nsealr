# SDK release policy

`@nsealr/sdk` is the sole public package. Internal modules, apps, fixture tooling
and `@nsealr/dev-signer` stay private. The current package is pre-release; there
is no compatibility obligation for experimental APIs. External Nostr protocol
interoperability and source/license provenance remain required.

Before publication, `make ci`, `make integration` and `pnpm release-artifacts`
must pass against the exact reviewed source. The generated API digest and
boundary review must match. The tarball includes dist, README, MIT notice and
package metadata, with no test signer, fixture loader or unpublished dependency.
Its root/browser/Node entrypoints must pass isolated runtime and type consumers.
Release output paths reject source directories and traversal before cleanup.

Publication, version selection and trusted-publishing configuration are later
coordinator actions. Migration rehearsals generate local artifacts only and do
not publish to a registry. Software acceptance does not imply installed-browser,
relay, hardware, production custody or physical security qualification.
