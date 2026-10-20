# Draft source notices — not published

These drafts bind local candidate `daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`
and its [complete original/current path and rights map](final-source-map.json).
Every named destination below exists in that candidate.

These notices are prepared for the coordinator after reviewed migration adoption
and actual main CI. Before applying one, verify every destination against adopted
main, add its exact migration commit and final map link, and refresh recovery of
any advanced source refs. The immutable old history and licenses remain available.
Do not apply these drafts as a claim that the local candidate is already adopted.

## nSealr/companion README insertion

> Bridge development has moved to [nSealr/nsealr](https://github.com/nSealr/nsealr).
> Current applications are under `apps/bridge`, reusable modules under `packages`,
> tooling under `tools/bridge`, and guides under `docs/bridge`. The public client
> surface is `@nsealr/sdk`; internal packages are private workspace modules.
> Existing source and its MIT license remain here for history. Smartcard
> commands and implementations are retired from active product software.
> The migration map records original commits, paths and exact transformations.
> Package publication and physical-device qualification are separate release gates.

## nSealr/specs README insertion

> Active software contracts, schemas, examples and vectors now have one owner at
> [nSealr/nsealr](https://github.com/nSealr/nsealr), under
> `protocols/contracts/v1`. Its manifest and independent verifier define the
> authoritative artifact; Rust, TypeScript and Python consumers use that source.
> The `v1` directory identifies the artifact format, not a blanket change to every
> inherited wire protocol revision. Original CC0 source and history remain here.
> Retired smartcard-specific files and adapted members are identified in the
> migration map.

## nSealr/raspberry README insertion

> Pi source, tests and adapter documentation have moved to
> [nSealr/nsealr](https://github.com/nSealr/nsealr) under `apps/pi`.
> The independent Python signing/crypto implementation remains a reference oracle;
> camera, GPIO and display adapter source is retained. Local software tests do
> not qualify an assembled kit, image, physical approval or a production signer.
> QP01/Q02 and profile release gates own that qualification. Original MIT source
> and history remain here; the migration map records retained and excluded paths.

## Private lab notice

Apply only inside the private source repository; do not publish its full history
or an address list of excluded documents.

> Individually reviewed CC0 product integration helpers and tests moved to
> nSealr/nsealr under `tests/integration`. Seventeen product integration steps now
> run without a sibling private checkout. The separate hardware regression stays
> outside the product prerequisite chain. Private research and unrelated scripts
> remain private and recoverable. The selected-file map, privacy exception and
> per-case disposition records identify exactly what moved and what retired.

## Private workspace notice

Apply only inside the private source repository after its later evidence and
handoffs have been reconciled. Main and the pause branch are distinct captured
inputs; this notice must not erase either.

> Active product implementation state is owned by nSealr/nsealr at
> `plan/work-items.json`. This private repository retains historical research and
> recovery evidence. No full private history or original private manuals were
> imported. Current requirements and public source links must be taken from the
> adopted product, while historical evidence retains its original meaning.
> Archive only after every retained obligation and later branch handoff has a
> verified destination and the current refs have a restored recovery bundle.

## Other owners

Hardware, board-sdk, website and .github retain their separate ownership.
No migration/archival notice is proposed for them merely because the product
uses a five-owner topology. Public smartcard remains its existing archive;
do not rename it, delete it or imply that it provides a supported product route.
Private legacy hardware remains protected recovery-only source.

The coordinator's later notice change should cite adopted source and final map,
verify links, record the repository/ref/settings before and after, and use normal
reviewed changes. Archiving a source requires verified disposition and fresh
recovery; this draft file performs none of those actions.
