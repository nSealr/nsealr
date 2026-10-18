# R00 bounded tooling defect: provenance metadata mistaken for a fixture

Observed against tooling candidate `d96bd7b81284709f5fef52cdc5f9b9c5c348915c`,
lab `3303ab17a28ed32419576627d5abb93db3999635`, core input
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d` and specs
`8bb8cca71355bcf8d81a093bcee9f3fe6915b121`. The first cold full integration
invocation fails before behavioral checks with:
`FixtureSnapshotError: firmware: SOURCE.json is missing from specs`.

`SOURCE.json` was added to the core's selected fixture import as provenance;
it is not itself an upstream fixture. The legacy checker compares every
non-hidden snapshot file against specs, without recognizing local provenance.
Deleting the manifest, copying it into upstream specs, disabling snapshot
checks or excluding arbitrary metadata would lose evidence or weaken checks.

The accepted R00 brief permits a narrowly reviewed, hash-bound tooling overlay
on isolated copies. Extend only the lab snapshot checker and its regression
suite: recognize exactly top-level `SOURCE.json`; require its upstream
repository and commit to match the actual specs checkout; require its file map
to cover the exact source and snapshot vector inventories; verify each recorded
SHA-256 against the actual snapshot. Existing byte comparison, required-glob
checks and license comparison continue unchanged for every real fixture.
The public overlay retains original file hashes, source commit and CC0 license
provenance. No private history is copied. Bootstrap records the deliberate
source delta and the runner accepts only that exact declared overlay.

Independent oracles: the pinned specs Git commit, source vector byte contents,
exact vector path sets and existing negative snapshot tests. Add regressions
for valid provenance, wrong source commit, altered manifest digest, an omitted
vector entry and an altered real fixture with apparently correct metadata.
Run these first against the original checker to preserve the failure, then
against the overlay. Repeat the complete integration recipe from its start.
Any further failure remains an executed failure until separately classified.
