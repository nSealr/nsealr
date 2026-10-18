# Repositories and source migration

Five active repositories are the target. Boundaries follow release ownership and independent consumers, not individual boards or implementation languages.

Keep the repository name **`board-sdk`**. It serves embedded firmware authors; the public TypeScript integration package (proposed `@nsealr/sdk`, subject to package ownership checks before publication) serves client/Bridge developers inside `nsealr`. An unqualified repository named `sdk` would blur these two boundaries. Neither name limits the Board SDK to Nostr: it must build a standalone non-Nostr example without importing the product engine. There is no technical prohibition on `sdk`; the more explicit name is the adopted navigation choice.

| Current source | Destination | Disposition |
| --- | --- | --- |
| `firmware` | `nsealr` | Same GitHub repository renamed; keep history and three stars |
| `companion` | `nsealr` | Select useful Bridge code; simplify package/API surface; archive after verified migration |
| `raspberry` | `nsealr` | Select adapters, UI and differential tests; qualify shared-engine integration; archive afterwards |
| `specs` | `nsealr` | Contracts and vectors colocated with implementation; retain applicable license/provenance |
| `lab` (private) | selected material in `nsealr` / `hardware` | Review and publish only selected non-sensitive research; preserve private history |
| `workspace` (private) | `nsealr` | Canonical plan, evidence conventions and integration ownership move here; archive after handoff |
| `hardware` | `hardware` | Revalidate components and design; no endorsement of inherited PCB/BOM |
| new | `board-sdk` | Generic platform boundaries, drivers, lifecycle and non-Nostr examples |
| `website` | `website` | User/developer docs and compatibility generated from qualified releases |
| `.github` | `.github` | Organization profile and concise community metadata |
| `smartcard` | public archive | Retired from active scope; preserve research and its community star |
| `hardware-legacy-tropic01-universal` (private archive) | unchanged archive | Circuit reference only, not a validated design |

The old `firmware` URL redirects. Never recreate that slug; doing so would replace the redirect. Do not toggle the starred public repository private: GitHub documents loss of stars/watchers across visibility changes.

## Target tree, created as implementation lands

```text
nsealr/
  crates/             portable Nostr engine and concrete Rust adapters
  apps/               embedded, Linux and Bridge applications
  packages/           public TypeScript SDK and owned internal modules
  protocols/          versioned wire contracts and compatibility policy
  tests/              vectors, adversarial tests, integration and device harnesses
  boards/             exact supported-device manifests; no generic-board CAD
  docs/               product, security, architecture and decisions
  plan/               task state and generated next-work view after migration
  scripts/            build/verification tools
hardware/
  boards/             board-revision KiCad sources and project libraries
  components/         exact parts, manuals, errata and approved substitutions
  mechanics/          enclosure and assembly sources
  tests/              netlist assertions, bring-up and production-test definitions
  releases/           reviewed manufacturing manifests
board-sdk/
  crates/             board support and generic device drivers as implemented
  examples/           standalone non-Nostr applications as implemented
  tools/              provisioning, recovery and developer tooling
  docs/               interfaces, lifecycle and measured support
```

Do not create empty crates or application folders just to imitate the target tree. `plan/work-items.json` is the canonical foundation graph; there must be one canonical task state, not copied status tables.

## Migration gates

1. Pin input commits and inventory consumers/licenses. Record retain, repair, replace or retire for each selected module.
2. Preserve Git bundles and source references. Do not import private histories into public Git.
3. Rehearse in an isolated checkout. Introduce new versioned contracts; update retained consumers together. Old experimental APIs can be removed without a compatibility layer.
4. Preserve useful independent vectors and add tests for corrected behavior. Run builds, browser/Node boundaries and affected integrations from the new layout.
5. Review the final candidate independently. Remove replaced active implementations, repair links/CI and record provenance.
6. Archive the old repository only after its migrated or deliberately retired content has a verified disposition. Update navigation and website status to the actual result.

GitHub primary references: [rename behavior](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository), [visibility effects](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
