# Distinct source review of the first ownership gate

**Changes requested for exact candidate `1ba98c9b6767eba82ed5ff231ae3d35abcf17337`.**
The [review record](review.json) binds all four implementation/test source files,
the two findings and the exact correction/proof required. Root is distinct from
the implementation author; no reviewer runtime was run before correcting these
source-established gaps.

F1: the new harness supplies a constant monotonic clock to the actual client.
The real100ms timer runs, but the client currentness deadline never advances.
Use the real monotonic source and prove expiry before a delayed timer callback
can run, with zero C input. Synthetic fixture wall metadata remains explicit.

F2: the channel parser checks shapes without all promised phase/counter
relations. A pre-P/unused operation must not name a worker, and decoded records
must agree with bounded observed/retained/result counts. Add only discriminating
negative controls for those contradictions, preserving late-cancel semantics.

The author matrix/early/default/unit reports and original false-green FG7 remain
unchanged historical evidence. This does not allege a real O leak or a secret
exposure, and does not qualify the component, device, hardware or release.
