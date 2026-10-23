# Rust QR worker: source and proof correspondence

Root reviewed frozen author candidate
`5fa5ec3afd0cf1f343743fe347b61728a242b15c`, tree
`938646d04c397c60989273b1b413142e732a5670`. A02 independently owns the
new source review, a fresh offline build and one five-case runtime campaign.

The [audit](audit.py) exited zero on its first invocation. [Validation](validation.json)
binds all 117 manifest members plus the manifest, their modes/sizes/hashes, and
the exclusive addition of 118 files. All other sources, including the original
controller and its parameters, are unchanged. Five pre-code files match their
committed expectations. Nine original public asset bindings match their Git
identities and bytes; no new image corpus was introduced.

All 11 registry packages match Cargo.lock, the retained official archive bytes
and checksums, and normalized Cargo.toml metadata. All 22 committed license
bodies match their original archive members exactly. The four runtime source
files match executed commit `142135cd70f920e104aa01841ceeeca794256440`.
The retained author ELF is 669048 bytes and matches its recorded hash. The build
command and three source-bound run receipts match; the five final case traces
match their recorded bindings. Root performed no build or worker execution.

The author observed exact 98/259/198-byte outputs, a distinct writer-cap refusal
for the 611-byte fixture with zero stdout, and a distinct no-QR refusal for blank.
The 512-byte ceiling belongs to this experiment; it removes no product requirement.
The pre-code controller binding's pending-review observation remains historical:
the later bounded controller acceptance is `8e4c27eb7a7b77f515e526a90a10119ced5902d3`.
No old supervisor campaign is relabelled as a test of the new adaptation.

Replaying this correspondence audit requires the retained author archive cache
and ELF described in runtime-retention.json. It does not establish a fresh offline
bootstrap or general reproducibility. This review grants no product decoder,
route, all-input safety, secret isolation, ARM/Pi/P4, physical or task acceptance.
Independent source/build/runtime review and any protected integration remain
separate gates.
