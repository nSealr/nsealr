# K01 portable signing engine candidate

Owner `/root/b01_final_review`; branch `implementation/k01-engine`. Runtime
source is frozen at `bf51d414f9dfc5f23c863dff51c3128dffa2dcad`, on actual adopted
T01 main `7f00138902526a63dc590ad4cd09dc40ab9b9700`. The final test-only proof
addition is `4bab1c86c0145a44bc5fefdd2f38d80e3336bcfb`; its three production
files are byte-identical to that runtime source. Root admission
`939da2f3e6eeba925426e8acdd124c4914093eb3` and its once-only API review are copied
exactly in [evidence/admission/](evidence/admission/). This is an authored source
candidate; distinct final review and normal protected PR/resulting-main gates
remain required. No task graph, transport readiness or device release is enabled.

The engine now retains original scalar custody, consumes local consent before
fresh clock/provider calls, requires exactly32 fallible auxiliary bytes, signs
and release-verifies the raw event ID, and stages a separately bounded complete
signed result. Its seven-kind inspector renders complete values and roles.
[Runtime design and limits](evidence/runtime-design.md) records actual ownership,
copy/scratch/cleanup and device obligations. The original transport entry point
still consumes and returns SigningUnavailable.

Read [evidence/result.json](evidence/result.json) for the final local command,
source, criterion and artifact bindings, and [evidence/handoff.md](evidence/handoff.md)
for delivery/review scope. Source-bound raw failures and their dispositions remain
in [development notes](evidence/development-notes.md). Public scalar fixtures,
local display simulations, static target sizes and link-only ELF are not physical
confirmation, entropy, stack/latency, bootability or real-key qualification.

The six accepted preparation files are exact copies from
`822c6390a929d3c490e9fa02f6e17191e84958c5`. Their dated dbad/T01-pending/review
statements remain historical, including K01-SPEC-01 and its corrected checker
instructions. The distinct specification review
`a0ad781346dd4fe5319397c3461db8bc705441f6` remains in
[reconciliation/spec-review/](reconciliation/spec-review/). The once-needed
[API reconciliation](reconciliation/api-reconciliation.json) and
[copy inventory](reconciliation/copy-inventory.json) preserve exact old roles;
they are source-preparation observations, not runtime acceptance.

Original8 S03 and new13 K01 independent mathematical controls stay separate.
The immutable70-case expected-input/first-RED component received distinct review
`2aaed50ae7c47a303ce79d3e0deae5d98a1d365b`,
[PASS_independent_expectation_component_only](https://github.com/nSealr/nsealr/blob/2aaed50ae7c47a303ce79d3e0deae5d98a1d365b/docs/restart/implementation/reviews/K01-independent-cases/review.json).
Later actual role/layer/effect assertions do not relabel that admission-only RED.
The original S03 oracle, vectors, T01 artifact/projections/checkers, locks,
vendor, P01, frozen1508, global gates and thresholds remain unchanged.
