# T01 service corrections — affected review

**PASS_service_component_only** on candidate
`21137d6177d1fe62b29f29cf59707bd7988527c3`, tree
`a90145c1ced097086f18f1e60dcf112b28ad0924`. Reviewer `/root/h01_sol`,
`gpt-6.1-sol` xhigh; author `/root/a02_sol`. T01-SERVICE-01/02/03 are resolved
within the assigned service component. This is not T01/artifact/source-pin
acceptance, ownership hand-back, protected delivery or release qualification.

The [prior REQUEST_CHANGES](https://github.com/nSealr/nsealr/blob/bd155e9e0f258e96d66150984aeecdddb625b25c/docs/restart/implementation/reviews/T01-service-component/final-report.md)
continues to bind104f unchanged. I reviewed the seven-path correction delta and
its proof, reusing the earlier stable source conclusions only after checking
its byte bindings. The separate artifact four-file delta belongs to root and
is outside this verdict.

T01-SERVICE-01: the async entry now calls the existing `authorizeClient` before
preparation, compatibility observations or adapter dispatch. The actual driver
[authorization witness](authorization-witness.command.json) confirms that
unpaired, revoked, expired and wrong-operation contexts have zero port opens,
writes and closes, with the same deterministic permission refusals as sync.
The authorized positive performs one open/write/close and succeeds. Exact local
route/snapshot and fixed independent public request/response inputs remain valid;
no device consent or attestation is inferred.

T01-SERVICE-02: the driver passes the effective frame ceiling into
SerialLineTransport. Its constructor requires a positive safe integer no greater
than the unchanged1024 global ceiling, and accounting checks both encoded string
length and actual UTF8 bytes before output write or incoming frame decode.
The cumulative work ceiling remains independently enforced. The actual
[capacity witness](capacity-lifecycle-witness.stdout.log) now rejects the original
431-byte error frame under226, even though its296 JSON bytes fit704, with the
expected protocol error. The independent fixed inputs give67/142 JSON bytes and
125/226 framed bytes. The targeted transport regression rejects below-cap
requests/responses, passes exact226 and above227, and preserves invalid-cap
rejection. The real narrowed driver positive still succeeds and closes; its
oversized valid peer error rejects and closes.

T01-SERVICE-03: the wrapped Promise gets a rejection observer immediately,
before post-dispatch current-state validation can return early. This observer
does not settle the underlying operation or release its reservation. The original
late-rejection [witness](capacity-lifecycle-witness.command.json) now records no
unhandled rejection, while the stale operation fails, its hook is revoked and
zero writes occur. The affected regression confirms a retry is denied before
settlement and succeeds afterward. Two retained controls also verify that an
unsettled async timeout or incompatible sync API keeps its finite slot until
settlement and then recovers. Immediate revocation/abort behavior remains intact.

I independently ran the two retained adapted witnesses and only **six affected
test methods** (four additions plus two retained reservation controls), all PASS.
The author's complete85-method run is reused from its original receipt/logs;
removing exactly the four added `it` blocks restores the prior four test files
byte for byte, preserving the81 previously reviewed methods. No full85 repeat,
broad CI or whole-source review was needed.

The [binding evidence](bindings.json) verifies12 primary objects, all15 unchanged
prior primary bindings outside the seven-path delta, the seventeen relevant
author service receipts and raw log hashes, and all26 original reviewer files
copied under their proper checkpoint/final Git identities. The pre-fix REDs
still demonstrate missing authorization, actual frame overrun and unhandled
rejection. Author receipts retain104f plus their actual dirty-diff hashes; they
are not relabelled as clean21137 executions. This review's witnesses run against
exact21137 package imports built locally from the frozen offline dependency set.

Two harness corrections are substantive and bounded. The first frame test
miscounted the unchanged `nsealr1f:` prefix as eight characters; independent
standard UTF8/Base64URL calculation confirms nine and the125/226 expectations.
The preserved corrected RED still rejects the old missing frame guard. Separately,
the original source-service import plus the driver's public compiled-client
import creates distinct `SignerTransportError` constructor identities. The
fixed witness changes only the client import to the same public module used by
the driver, retaining its inputs and protocol-error expectation. Its failed
mixed-module attempts remain preserved. Neither correction changes a product
requirement or weakens a negative. The typed `pendingResponse` local resolves
the recorded TypeScript narrowing failure; the serial-frame error wording keeps
the existing deterministic protocol-error mapping. Build/typecheck receipts are
preserved with their actual outcomes.

A read-only binding inspection initially assumed every copy source had a commit
and all26 review files shared the finalbd155 source identity. The actual inventory
also has public-safe receipt records and correctly pins thirteen earlierfae
files plus thirteen finalbd155 files. The failed assumptions and corrected
selection are retained in [inspection-correction.json](inspection-correction.json).
No product, evidence identity, runtime check or acceptance requirement changed.

No blocking finding remains in these three corrections. Unchanged diagnostic
reported data and complete-plan observations still provide consistency/capacity
checks, never consent, a signing authority or physical qualification. No other
metadata/schema, Pi, provenance, hardware, all42/all170+3, full stable T01,
artifact pin, actual rebase/main-only or main CI gate is approved here. Root
retains final pin, full gates, exact delivery review, protected integration and
any ownership/state decision.

[Whitespace evidence](whitespace.json) preserves the raw-log observation and
the successful non-log review-proof check; no raw output is normalized.
