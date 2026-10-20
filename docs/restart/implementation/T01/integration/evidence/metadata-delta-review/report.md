# T01 metadata delta review

**PASS_metadata_component_delta_only** on author candidate
`24b0b58a6ee085d8176a801a7bad5595d39965b7`, tree
`5a2d3a6e724bb952a3db6e1eb82d3e2d9bfc2df4`. No blocking finding remains in
this bounded delta. This is not full T01, criterion, source-pin, integration,
provider or physical acceptance. No product file was changed by this review.

The exact 18-file perimeter comes from preread
`e554a785242e3de08ec3c1568f7a4327e1444b09` on source751. Eleven mode/blob
bindings are identical; seven changed: the two capabilities TS files,
profile-requirements/request/response/error schemas and signing-v2.md. The
unchanged files retain the earlier substantive reading. `source-bindings.json`
binds both versions, all nine original review files and all 13 unchanged
historical author evidence files. The earlier findings and missing-dist typecheck
exit2 remain historical; later build success is not relabelled as this review's
execution. Pi and the two provenance scripts are entirely excluded.

## Finding resolution and changed semantics

**T01-META-01 resolved here.** The actual requirements schema now combines eight
individual mandatory common-group `contains` constraints with the profile
condition: esp32_no_se/custom_board require exactly nine unique groups including
R-MSG; pi_qr/p4_qr require exactly eight and exclude R-MSG. The existing closed
enum and top-level required fields remain. All 512 subsets of the nine named
groups, plus duplicate/foreign controls, were evaluated for each profile against
the unchanged pre-implementation expected sets. Exactly the expected set passes
for each profile. Both old complete witnesses occur among those rejected sets.

**T01-META-02 resolved here.** Request event_template and response signed_event
now encode kind0..65535 and created_at0..9007199254740991. Manual reading of the
changed prose confirms those distinct bounds, preserving S03 grammar. Thirty-six
scalar boundary observations cover negative, zero, maximum, over-maximum and
fractional values across the four fields. These are schema value constraints;
raw canonical integer spelling remains a separate parser obligation. For example,
JSON Schema integer value1.0 and raw token1.0 have different roles: the actual raw
metadata helper rejects the latter, as recorded in the TS probe.

The two separately attributed author-known deltas are corrected: ID prose now
agrees with the unchanged128 ceiling; all three relevant schemas accept ASCII
ID lengths1/64/128 and reject0/129 under their literal constraints. The error enum
preserves all prior entries and adds only signing_disabled. Its numeric version2
and response error reference remain coherent. Schema validation does not prove a
returned event's signature, local consent or an available signing provider.

The lexical refactor imports the existing parseStrictJson helper from encoding.ts,
whose blob is identical to source751. Native JSON.parse supplies syntax/value
parsing; the shared nonrecursive walk rejects decoded duplicate keys. The metadata
layer retains its stricter byte/type/BOM/Unicode, unsigned safe integer, depth,
member and UTF8 key bounds. It introduces no report-to-evidence conversion and
does not change immutable profile/reference resolution or method/custody semantics.
Probe rejection includes shared parser Error/SyntaxError; a uniform exception
subclass is not claimed.

The other executable delta extracts the previous method-limit validation body,
then applies it to both intersection endpoints and the result. This rejects
invalid retention, foreign units and arithmetic overflow even when callers bypass
parseLimitsManifest. Valid intersection returns a distinct object, keeps every
numeric dimension at or below both endpoints, preserves allowed zero queues and
caches, and does not mutate inputs. The two added author assertions are covered
by independent direct-call negatives here.

## Actual evidence and scope limits

`probe.ts` imports the exact local source directly and reuses the earlier32
controls, adding33 for the lexical and direct-limit deltas. **65 controls pass:
55 expected rejections and ten positive controls.** These include decoded aliases,
UTF8/scalar/BOM failures, malformed numbers and syntax, exact8/9 depth,32/33 members,
128/129-byte keys,8192/8193 bytes, invalid caller bounds, nested delimiter strings,
overflow, retention and dimension mismatch. No signing or transport is executed.
The pinned Node/tsx tool is borrowed only as a launcher; no dist, package build,
installation or author-worktree write occurs. Local capabilities.ts and encoding.ts
hashes are recorded in the actual command receipt.

`schema-probe.py` is a finite evaluation of the inspected changed keyword
constraints:2056 requirement-set observations,36 scalar and15 ID observations.
It is not a general JSON Schema engine or full object/reference validator. The
schema structure and retained references were read directly; no phrase-presence
test or new product verifier was added. This limit is explicit in the receipts.

All42 case objects retain their original values and order from semantic source
bb20; the current case file and all four conformance records are also byte-exact
to source751. This is preservation, not a fresh execution claim for all42 cases.
Synthetic reported availability still does not establish local verification,
authority, firmware identity or provider qualification. Consumer/wire cutover,
the final provenance literal, full T01 gates, protected PR/main CI and release
acceptance remain with their separately assigned reviews and coordinator.
