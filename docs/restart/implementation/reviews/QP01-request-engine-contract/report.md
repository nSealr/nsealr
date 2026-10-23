# Pi request-engine pre-code review

PASS for the bounded contract `e8ffed4ed4643c1e74b598c742b81ca718118cf4`; findings none. **No runtime was executed or qualified.** Root reviewed B01's three-file contract independently.

[Validation](validation.json) verifies19 exact source bindings/34 ranges, five relevant subtrees identical on actual-main14d5, two original event vectors and source length calculations. The existing basic/tagged requests are188/288 JSON bytes and259/392 static-frame bytes; complete responses452/552 JSON and611/744 frame bytes. Root also verifies their full expected events/IDs/signatures against the original vectors. All47 formal task/acceptance/dependency/resource/release data are unchanged.

The proposed new member uses the root Cargo.lock and existing audit. A thin Python caller preserves original bytes and delegates review/consuming authorization/signing to the real Rust owner; public fixture11×32 has the actual expected4f35 identity. Trusted C-call pointer preconditions and cooperative callbacks are explicit. Bounds704/947 differ from the separate image experiment512. Production keys, custody, real entropy, optics, physical UI and target ABI remain unqualified.

The frozen provisioning contract addresses a concrete initial gap: default CI must build the real native member, discover its Cargo artifact path/hash with the existing target-dir override, run the **whole existing Pi CI once**, then the actual client exchange. No skipped/mocked library, duplicated Pi/Bridge suite or nominal-only gate marker is accepted. A new100% crate floor preserves existing floors and checker semantics.

A02 may implement the finite proposed edit set after importing exact preparation bytes, preserving actual failing tests and the23 precommitted case groups. B01 remains the distinct final source/runtime reviewer; root owns integration. This is permission for the next engineering implementation, not profile readiness or task/release completion. [Review scope and conditions](review.json).
