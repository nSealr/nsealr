# Final Linux/Rust QR and Pi probe assembly review

**PASS_FINAL_ASSEMBLY_SOURCE_AND_METADATA_ONLY**, findings empty, on candidate
`1be80c8114583627a8eef1952a0cd939f40b84ec`, tree
`15d01e479c1f55af79c876c7e1ee8089daf6ec1a`, based on actual accepted main
`994a8b682ed6cd52bb46608b90794c02d2a9d3cb`.

Root reviewed the final assembly independently of its author A02. Component
reviews remain source-specific: the trusted-worker correction and Rust experiment
were independently executed by A02; root separately reviewed source/provenance
and independently executed the Pi probe correction. This review covers the
assembly, current navigation, claims and sole-graph changes. It performs no
additional decoder, cryptographic, build, corpus, dependency or Pi-suite run.

The [audit](audit.py) exited zero. [Validation](validation.json) binds all 595
selected source postimages to original Git modes/blobs/sizes and SHA256 values.
All 17 source selections match the accepted commits and scope. There are 593
new copied files and exactly two authorized Pi replacements, with verified
main994 preimages and tested69a postimages. All 562 original preparation copies
remain byte-identical. Every one of the 619 manifest members matches; including
the manifest itself, the base delta has 620 paths: 615 additions and five changes.

The five existing changes are the two Pi product/test files, restart README,
execution handoff and task graph. No other existing source is changed. The
entire apps/pi tree equals tested `69a090254738cbf6368b37c2ebb820a99bf83ea4`;
author full Pi CI173 and root70 independent synthetic cases therefore retain
their applicability, without being represented as new executions here.

All six current inner manifests (538 members), 14 original native/input bindings,
17 final gate inputs, four source-bound structural command logs, eight unchanged
preparation receipts and current wrapper hashes match. The four final commands
actually exited zero on stable inputs. Their new raw logs and the earlier raw
outputs retain their exact whitespace; the complete diff-check exit2 remains
distinct from the explicitly scoped authored-file check0. An initial overbroad
reader selection was truncated; necessary records were recovered with a bounded
selection and all source rows were verified directly, not inferred from that
truncated display.

Only QH01/QP01 checkpoint and artifact fields change in the graph. The other45
full records, all47 task states, acceptance/dependency/resource/release sets and
all other root graph fields are unchanged. The14 QH01/QP01/Q02 assessments remain
incomplete. Historical PR43/main994 acceptance is reconciled with its real CI
identities; later measurements are not attributed to that old main.

The descriptions preserve material limits: finite host resource experiments,
fixed equal-channel public images, experimental512-byte staging and611 refusal,
different independent ELF, no general reproducibility, camera/color, final
decoder, framing/profile, route, secrets isolation, ARM/Pi/P4 or physical release
acceptance. The Pi fix remains narrow preliminary file-text and ssh/sshd query
classification. Its tests do not attest a real device or global remote absence.

The candidate is ready for a normal protected PR. This is **not integration
acceptance**: root must verify the actual tested merge/tree, required checks,
normal protected integration method, resulting-main source/tree, complete main
CI and applicable fresh main-only provenance before accepting the delivery.
