# Native leaf prerequisite review

PASS_NATIVE_LEAF_EXTRACTION_PREREQUISITE_ONLY; findings[]. Exact candidate
`a3a49eeb7cbddcad2b9e7b04aaa16808b8ef0a86`, tree
`1ce8e5fa26af8bfebcdd10cd5e057030343e0775`, base
`0210e6f5f32ac2ea7a0fbde13052c67798d51a2a`.
Actual current-thread runtime metadata confirms `gpt-6.1-sol`, effort `xhigh`.
This review covers only the extracted fixture C leaf, its legacy binding, pure
preflight and source-qualified evidence. It accepts no combined RGB/engine path.

`native-leaf.ts` contains the existing helper, with explicit root/spawn/timers/
counter/report dependencies. Reversing the eight declared substitutions after
the specified dedent/strip normalization gives the exact original helper hash
`1ceb2aecb31ec63194563a184c13a385ef6124d50ab0b0876f6472ba1767a920`.
Restoring the helper binding/import/timer capture makes the surrounding caller
byte-identical. Counter callbacks remain at the old increment locations; report
callbacks retain the same scope/key/record order and observation order. The new
module's only runtime imports are Node assert/crypto/path; child_process/stream
imports are type-only and erased in the bound emitted JS. There is no CLI,
fixture loading or child creation at module import. Dependency callbacks are
trusted capabilities; this is not a general-purpose exception-safe process API.

Readiness still requires exactR plus EOF before sending any request. The same
947-byte input/output and262144-byte diagnostic caps, pre-send output refusal,
one-send state and native source/input/output hash checks remain. `send()` awaits
the same actual child close promise; `dispose()` keeps the original absolute
safety timer active until that close. The uninterrupted5000ms scheduling/kill
attempt starts after C spawn and is cleared at close. The legacy caller captures
real timer references before client operations/mocks and supplies them explicitly.
No client100ms, core tick, worker8s/4s or other budget changes appear in the delta.
Kill scheduling is neither a hard return/collection bound nor device-side recall;
Node code/signal/close observations are not a wait4 raw-status proof.

The pure preflight guards all seven actual child-process helper entry points
before module import, verifies no direct children, and injects only MockChild
without a PID. It captures real timers before enabling MockTimers. Virtual5000
fires the synthetic client100 once and leaves native kills/collection zero;
the real timer then fires once after5004886084ns, with no lower tolerance. The
kill/close/collection here is simulated. Its zero-helper/no-child assertions do
not prove a real C cleanup, EOF, signature or future combined-call permission.

The pre-execution source/prep/oracle freeze is the actual05468 child of0210;
all three executed code postimages remain exact in the candidate. The joined
TSC6.0.3 NodeNext/ES2022 command, compiler hash, exit0/raw0 and three emitted
artifact hashes are bound in the archive. The subsequent one pure Node24.22 run
and one normal `make pi-ci` have distinct commands/statuses/roles. The normal
run records clean source before/after, exit0/raw0, Pi211,70 owner rows,39 final
first-gate cases/62 event rows and four existing QH fixtures. Those70 archived
owner records match the same raw stream, not an invented second execution.

Independent read-only comparison of the raw normal logs confirms all14 legacy
native observations equal the prior source-qualified log, including complete
review pages and input/output/signature-related hashes. All19 legacy settlement
records preserve values/order after removing only actual PID and initialization/
request-to-close timings. Existing14 client C observations and5 readiness children
are separate from the new pure MockChild control. No combined RGB-to-native
signing fixture was introduced or counted here.

The author manifesto is SHA256
`ada36cc9374e88905f0e00902e21b4619b540e5f7209f1c81778a25eca6be71a`:
12 exact Git mode/blob/size/hash members plus itself. Its archive is SHA256
`cd8d3a03c5778965f66611ded0b920412f8f1a520dab8d05d2e275a8145313cb`:
86 regular files,85 independently checked internal manifest bindings plus self.
All14 declared unchanged source bindings retain base/candidate bytes, including
the Pi/Rust adapters, worker, composition code, locks and graph. The complete17-
path delta is only three fixture code files, the brief append and13 proof files.

Reviewer execution: read-only Git/JSON/archive/source comparisons only; zero
compiler, pure timer, product C/O/W/Node, make, full CI or hosted operations.
An initial raw reverse comparison differed by two indentation spaces; applying
the declared normalization before substitution reproduces exact1ceb. This was a
reader normalization issue, with no candidate change or failed runtime result.
Existing source-identical component proofs are reused in their original roles.

No QH wire-to-engine integration, provider/default route, production signing,
physical approval, image/camera/ARM support, custody, reproducibility or release
qualification is accepted. All parent criteria and normal protected integration
gates remain unchanged. The current lifecycle delivery remains a separate scope.
