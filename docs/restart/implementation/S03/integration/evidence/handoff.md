# S03 combined implementation delivery

The reviewed S03 behavior is ported onto product input
`b1c90139a651895284b2624da7d12903cf16bc9d`, retaining its OUT_DIR fixtures,
separate core/host workspaces and exact contract bytes. The admitted specification
is `e95eaaf8e3fd76ede797f128f0cc7de43ab2bb03`; its distinct review and root
admission are copied in [spec-review](spec-review/review.json) and
[implementation-admission.json](implementation-admission.json). The five admitted
specification files retain their historical preparation wording and exact bytes;
the actual admission supersedes their former implementation hold.

Actual full `make ci` passed on clean
`dda66f3e4d0d25f2fa3f3ee2b5cb5aacfdd122d3`. That includes both workspaces,
embedded/std builds, doctests, dependency audits, coverage, reproducibility,
Bridge/Pi/SDK consumers, product controls and all 17 uninterrupted retained
integration steps. Coverage was 100.00% core and 76.76% host against unchanged
100.00/76.70 floors. See [combined acceptance](combined-acceptance.json) and the
complete [command receipt](commands/combined-make-ci/command.json). Offline
yanked-status warnings remain in its raw stderr; no online check is claimed.

The distinct pre-read then found misleading serial preview comments. Only two
Rustdoc blocks changed in product checkpoint
`7eee22fbc269033756e53020b1370fc6671da3ab`: they now explicitly deny signing
authority and preserve the historical C++ method name. All non-Rustdoc lines are
byte-identical to the full-tested checkpoint. Rustfmt, doctests and fresh
same-tree/cross-path reproduction passed. The current device rlib hash is
`590e38bc45a96e78ff81b83b130e4dac31576b4d8e5c58705c5734b96cca2ee5`;
the full run's earlier artifact hash remains historical. See the exact
[comment correction](serial-preview-comment-correction.json). Later delivery
changes are scoped evidence only; the final commit identity is reported
externally to avoid a self-hash.

The [result](result.json), [final port reconciliation](final-port-reconciliation.json),
[consumer case ledger](consumer-reconciliation.json) and
[artifact manifest](artifact-manifest.json) bind the actual source, controls and
durable proof. The 80 original historical files remain byte exact, including old
failures, oracle/vectors/licenses and source-only reviews. New observations and
review/admission copies are separate. All 170 current projections and three
generated helpers retain their expected bytes; the additional S03 output copies
the unchanged independent vector file as data only. Both locks retain 26 old
identities and add exactly 21 reviewed registry identities. Original vendor bytes,
checksums and licenses are preserved; supported Cargo re-vendoring metadata
differences are recorded, not overlaid onto source.

The final exact implementation review, protected PR/full CI and resulting actual
main CI remain pending. This delivery changes no graph, criterion, task status,
closed record, frozen historical index, checker, v1 expected data or coverage
floor. The admitted product input remains b1. Later actual main
`503719d5c607bdbcd1da30a89b0c3c6f5983c01b` contains only129 A02 closure
metadata/proof paths; that exact delta is independently classified in the
[later-main observation](later-main-metadata-observation.json). Its resulting-main
CI was still pending when reported. No source or graph is substituted here;
normal final integration must reconcile that metadata explicitly. No S03
criterion is closed here.

Production signing remains unavailable and transport signing stays disabled.
The fixture signer is private under `cfg(test)`. The consuming owner retains the
reviewed odd-Y scalar limitation; it cannot recover the original imported nsec.
Host-executed semantics, static size bounds and reproduced artifacts qualify no
physical UI/input, entropy, isolation, timing or device. D02/K01 and actual-device
gates remain separate.
