# Exact A02 contract-anchor repair review

**PASS_final_repair_candidate_only**, with no blocking findings, for candidate
`951ed2ad1bb7c7d85a6eaa735a5286022e8fce36`, tree
`0014d51b24ea0b58650d3dee3a5a8616367e6769`, compared with adopted main
`d931277bebbc5f43514b0e8438d65fb60603fa35`. This is a distinct final delivery
review following scope `7618ea42a86a1c25790955090b2dee3350943ff8` and its
preimplementation review `771a35ff4dd5176dd9ee50e566320d4ab68c3844`.
The coordinator admission receipt is exactly SHA256
`974c1517c86dc308af0fa05f0f936f42a4c3fe32785eea415987109e9d6c71d9`.
No source rehearsal, protected CI, merge, task closure or hardware qualification
is substituted by this verdict.

The only four modified existing files are the two admitted Python scripts and
the current restart README/handoff. All 81 additions are regular Git100644
files under `docs/restart/implementation/A02/post-rebase-repair/`; no existing
path is deleted. The 28-file final tail after tested source
`63ada7b48432119c932a35224978f48057e5a99c` is confined to this proof directory.
Both scripts and both current navigation files are byte-identical to that
source. The original brief/audit are unchanged. [The inventory](candidate-inventory.json)
binds all 85 affected paths by Git mode/blob, size and SHA256.

The checker repair preserves literal historical origin/import metadata and its
strict identity rejection. It introduces a separate fixed source-postimage
anchor and replaces the fixed runtime baseline. There is no HEAD selection,
dynamic ancestor search, current-manifest trust, fallback, extra branch fetch
or weakened digest/inventory/consumer check. I independently verified these
whole-tree equalities and that both adopted commits already belong to protected
main's ancestry:

| Historical object | Adopted runtime object | Identical whole tree |
| --- | --- | --- |
| `86569e073da4faec0811d67137bbb0fd4f74c7c6` | `68508ea1eea1e07b0064fadd65b33433d72701f8` | `59008a6e0fdb4475d03bbe4f1761f8514f552e84` |
| `5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0` | `59653fcc15c4cbc21a39d0a0dd5548abe46165b0` | `d3ee175dbdcd91bcd01f1cde50be2451251ebd96` |

Normal future PR rebases atop that main retain these already adopted ancestors;
the repair does not depend on the transient commits of this repair branch.
The manifest still literally names historical import `86569e0…`, with unchanged
SHA256 `16bf215c6f65a5c616c30971cb860351272633ff6a8c75edc8246eab61f8bbeb`.

The added rewritten-history regression builds a separate actual Git history
with equal source/postimage trees and different commit IDs, retains the old ID
in manifest metadata, then fetches only the rewritten main into a fresh
repository. It proves both old objects absent, both adopted anchors ancestral,
and successful real validation. It does not mock Git. Three additional methods
exercise missing runtime anchors, a present source commit with wrong bytes, and
a wrong postimage manifest. All 20 prior test bodies are AST-identical; the
fixture setup separately patches historical identity and runtime source. The
original forgery, byte/inventory, hidden-file, committed-mode, consumer and
duplicate-snapshot obligations remain exercised. These are meaningful controls
of the failure mechanism, rather than prose or heading tests.

I ran all 24 artifact cases independently and `make docs test`, which passed
the actual structure, firmware-profile, graph, contract/evidence gates and
69 tests across its five Python suites. Then [my independent probe](probe.py)
fetched exact final **951**, rather than only the author's earlier source, from
the public GitHub URL into a newly initialized disposable repository. It found
one selected ref, no configured remotes/alternates/shallow boundaries/grafts or
shared/hardlinked objects, and 8,770 objects all reachable from that ref. Strict
Git fsck passed. Both obsolete objects were absent; `68508ea…`, `59653fc…` and
original frozen-evidence source `f2ef70f…` were present ancestors. The actual
contract and 1,508-file evidence checkers passed. Six additional controls
rejected replacement of the literal historical identity, a forged working
manifest, either missing runtime anchor, a present wrong source tree, and a
present wrong postimage without the reviewed manifest. Restoration revalidated
successfully and left the cold source clean. [Results](probe-result.json) and
[actual cold commands](cold-commands.json) preserve these observations.

The entire v1 contract tree (264 tracked entries), whole plan and evidence-index
are byte/mode/blob-identical to adopted main. The unchanged plan preserves all
47 task records, criteria and dependencies, 16 resources, five release paths,
seven closed records, and A02's incomplete status. Every one of the 1,508 frozen
files also matches its bound SHA256 and Git identity. No app, crate, lock,
toolchain, recipe, CI, coverage floor, historical migration template or patch
changed. The current navigation links checked (33) resolve; the handoff states
the actual failure and remaining gates without closing A02 or admitting S03
implementation.

The four copied spec-review files match exact review771a. All 45 selected local
proof copies and four public failed-CI captures match their original files,
sizes, modes and hashes; all nine decompressed ZIP members match their bindings.
Forty recorded commands in six command records have matching log/environment
hashes. The preserved public main log has two actual make failures: the root
test and integration step1 both fail on the same baseline Git lookup with exit128;
the remaining16 integration steps did not run in that failed hosted attempt.
The preserved cold-main RED independently demonstrates that same failure with
the unmodified checker. The author's public source63 GREEN is accurately bound;
the final951 proof append changes no tested source bytes.

I checked the author's complete17-step integration log, command exit0 and pinned
environment binding. It covers every retained step in order and ends with the
actual all17 completion line. Its executable dependency audit's 364 source
hashes match the candidate. Current checker/bootstrap/integration/CI entrypoint
inspection found no other broken fixed historical-object lookup: `f2ef70f…`
remains reachable and was exercised in my cold fetch. These unchanged broad
component suites were not rerun by this reviewer; the exact full protected PR
suite remains a distinct delivery gate. I did not repeat migration48 or the
historical full replay.

All new paths are admitted proof, selected command/source bindings and public
CI captures; none are runtime repositories, caches, manuals, raw private history
or agent sessions. A bounded token/private-key/unmasked-bearer/private-session
scan over the affected text and decompressed ZIP found no matches, supplemented
by inspection of the diff, inventories and log contents. This is bounded public
proof review, not a general security or cryptographic certification.

Failures and diagnostic limits are retained. Failed main CI39408038674 and cold
RED remain failures. The author's first proof-only mode assertion failed because
it confused filesystem0664 with Git100644; the corrected regular nonexecutable
check passed and no product file needed repair. Its earlier staged whitespace
snapshot identified two raw docs/test logs. My exact-final diff check exits2
with **337 trailing-space warnings in four raw log files**: those two logs,
the preserved whitespace diagnostic, and Git's reachable-object listing with
root-tree trailing spaces. Every non-log changed/additional path passes
whitespace checking (exit0). Raw evidence was not cleaned or replaced. This is
an observation of a later bounded input, not a new functional failure.

Actual full protected repair PR CI, normal reviewed integration, actual full
corrected-main CI, and separately reviewed A02 closure remain **pending** here.
S03 implementation also retains its own source/brief admission gates. This
review changed only its new review-evidence directory and performed no merge,
main mutation, CI rerun, self-approval, publication/archival/registry action,
task closure or physical qualification.
