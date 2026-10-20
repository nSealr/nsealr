# T01 provenance Git mode correction — affected review

**PASS_component_before_final_pin** on candidate
`38a82b9cbac3981fc6b70c16163529de0cf42bf7`, tree
`029e0967bca00f7457714500f30848de221e18d6`. Reviewer `/root/h01_sol`,
`gpt-6.1-sol` xhigh; author `/root/b01_final_review`. Finding **T01-PROV-01** is
resolved. This verdict covers the corrected two-script component before its
real artifact pin. It does not accept the current artifact or T01 delivery.

The historical [REQUEST_CHANGES at9104256](https://github.com/nSealr/nsealr/blob/910425654c6a6d65b348e4285a5d6d35ab049525/docs/restart/implementation/reviews/T01-provenance-component/report.md)
continues to bind candidate0c4 unchanged. I reviewed only the correction and
affected proof, and reuse its other source conclusions only after verifying the
unchanged source and evidence perimeter. No historical approval is rebound.

The verifier delta is exactly one expression in `inventory()`: `mode & 0o111`
becomes `mode & stat.S_IXUSR`. This matches the real Git executable
classification. Both added regression methods derive expected answers from
actual `git add`, `git ls-files --stage` and approved `git ls-tree`, with
`core.filemode=true` in disposable repositories. They correctly reject removal
of owner execution from approved100755 despite another class retaining execution,
accept retained owner execution, and accept nonowner/other permission changes
that leave an approved100644 Git mode unchanged. No claim about all POSIX
permission bits, owner identity, ACLs, SUID or sticky state is introduced.

The tests/expectations are fixed at `faa784fc18bbb588c6956b83ce506c2714ed4697`
while the verifier still has its old bytes. Product
`9e2bf3ddfc8968c384cefa7801e6a513efa0a395` contains the fix. The preserved RED
receipt binds those old verifier/new test hashes and reports two failures plus
two errors. Its ten actual Git classification rows are byte-equivalent as JSON
to the subsequent GREEN observations. The [independent reviewer run](new-mode-tests.command.json)
passes both new methods and reproduces the same ten actual Git classifications.
The author's complete38-method PASS is bound to the exact corrected script
hashes and original raw logs. I reused that sufficient complete run; I did not
repeat the36 unchanged tests already executed in the first distinct review.

The [unchanged original reproduction](replay-original-reproduction.py) is loaded
from its immutable9104256 Git blob and verified against its original SHA256.
Executed against the corrected scripts, it now stops at the second validation,
after the original approved755 positive and `chmod0645`, with
`ValueError: contract byte/mode tamper: LICENSE`. The expected raw exit1 and
[trace](original-reproduction.stderr.log) establish that the former false
acceptance now rejects. Neither the old reproduction nor production files or
constants are edited.

The [binding evidence](source-bindings.json) independently establishes:

- The entire verifier equals the prior reviewed source with only that expression
  replaced. All36 previous test method source segments are byte exact; removing
  the two additions leaves the complete old test AST identical, including helper
  and fixture setup code.
- All22 previous author proof files have identical Git mode/blob objects. The
  author's reference to all15 historical reviewer proof files matches those
  exact immutable Git objects. The17 new paired author artifacts and each runtime
  receipt's source/log hashes verify.
- All other paths outside the two scripts and18 new author proof paths remain
  unchanged from0c4. Both current scripts equal product9e2. The selected-A
  authority, strict schema/disposition/whole-tree/consumer semantics, historical
  source constants and replacement-ref protection are unchanged and reuse the
  earlier review's source conclusions, with the corrected mode comparison.

`ARTIFACT_TREE_OID` remains `None`. The actual reviewer [source command](source-unbound.command.json)
still exits1 with the mandatory unbound-literal refusal before reading an
untrusted artifact. This is required fail-closed behavior, **not source PASS**.
The author's preserved RED unittest log has two trailing-space observations;
its full-delta whitespace result2 and non-log result0 remain honestly recorded,
without normalizing failure evidence or changing a gate.

No blocking finding remains within this component perimeter. The exact stable
a02 artifact inventory/modes/consumers and final literal pin still require root's
distinct delta/pin review before adoption. Complete stable T01 acceptance,
all42 cases, all170 semantic projections/three helpers, actual protected
integration/rebase/main-only reachability and actual-main CI remain root-owned
existing gates. No full `make ci`, artifact/Pi acceptance, source/adoption/task
closure, hardware research or release qualification is claimed here. Ownership
hand-back remains root's decision.
