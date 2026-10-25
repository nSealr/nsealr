# Affected admission: R1/R2 documentary addendum

**CHANGES_REQUIRED** on author
`503fbf5e23cce7e85f062844aa77143663bcd6a9`, tree
`9bb7b2d6c90681ac2591d409c2d0c25c807e0290`.
One exact R1 command/path inconsistency remains. R2 and the rest of R1 are
sufficiently specified for reuse in the next affected review.

This reviews only the two added files, read in full:

- `admission-addendum.md`, SHA-256
  `7c37bb9127360b36f0ff9015ac048e182619a656cf61a920dfe46db629830195`.
- `addendum-source-proof.json`, SHA-256
  `74c48fefe2fc355b3ec68e094c142c0afd51c6a24c3297b38e5d6451c43ea2b2`.

Original review `c1ffff4a0d79af98fc7b9ba0159d04725a666591` and its report,
receipt and manifest remain immutable. The author delta from a836 contains only
the two additions. Original brief/proof and all 28 source bindings are unchanged;
their prior source/status review is reused rather than repeated. No code, module
import, test, build, actor, native load, flash, audit, device or CI execution took
place. Current PR/main CI is root-owned and was not queried.

## Sole remaining finding: R1 preparation module/receipt paths

The positive command specifies both:

```sh
--engine-module "$PREP/native-leaf.js"
--engine-preparation "$PREP/receipt.json"
```

The unchanged source at
`request-engine/exchange.py:114–140` creates `output = temporary / "module"` and
sets `receipt = temporary / "preparation.json"`. The emitted helper is therefore
`output_dir/native-leaf.js`, while the preparation receipt is a sibling of
`output_dir`, not `output_dir/receipt.json`.
`run-composition.py:55–74` reads the supplied preparation and requires its own
`receipt` field to resolve to that same argument. No such `receipt.json` is
produced by the existing recipe. If `$PREP` denotes the module directory, the
module argument is plausible and the receipt argument is wrong; using the
preparation root instead would make the module argument wrong.

Correct only this documentary argument/variable contract: take the module from
the actual `output_dir`/`outputs['native-leaf.js']['path']` and the preparation
path from the actual `receipt` field, with distinct trusted variables such as
`MODULE_DIR` and `PREPARATION_RECEIPT`. Do not copy, rename or reconstruct the
receipt, invent an alias, or change the compiler/preparation recipe. Freeze the
actual returned fields before actors as already required. This finding is from
source inspection, not an executed failure and not a product defect.

## R1 properties now accepted for reuse

The addendum otherwise identifies one opt-in synthetic enum through the existing
`run-composition.py` engine case. Trusted config/source validation precedes native
readiness/input; one literal synthetic adapter can be selected without an arbitrary
import or request-supplied callable/path. The same Node `createPrepareNative`,
unchanged C argv, pre-mock real 5000ms watchdog, send-once/R+EOF, output caps and
actual close remain. There is no new owner, physical callback mode, direct-CDLL
bypass or default provider. Unknown collection retains original handles and output.

Before/after source/compiler/generated/preparation bindings and config/adapter/
trace identities are specified. The bounded trace distinguishes actual callback,
auxiliary-entry, native return and process-settlement observations from constructed
counters, writes before public output release and preserves failure evidence.
These choices close the original ownership/entrypoint ambiguity once the single
path inconsistency above is corrected.

## R2 closed documentarily

The synthetic 240×240 cell sink defines 6×8 metrics, a 32×8 content area, exact
Rust bytes/wrapping, indexed header and distinct decision footer, whole-frame
preflight and fit-or-refusal. It does not reuse clipping or claim physical glyphs.
A successful commit precedes a neutral/single-press/release cycle associated with
one invocation and presentation epoch. Queued/preheld/stale/duplicate/simultaneous
inputs refuse; Back/None/scroll/bool/unknown refuse explicitly. Redisplay and later
requests require fresh state and actions; no FFI approval handle is invented.

The finite matrix covers real basic31-page/zeroaux/independent611 response and
identity, rejects at data/decision, wrong-phase actions, draw/presenter/input faults,
preheld/queued/stale/duplicate/simultaneous inputs, cancelled-after-commit and an
explicit clock-unavailable fault. Pure fit and cross-request/redisplay controls are
correctly distinguished from native status evidence. Positive uses real
`MonotonicSeconds`; the fault does not claim a 100-second expiry inside C5. Existing
core context/currentness/consume-first and ABI tests retain only their original
scope. No test or runtime pass is claimed by this documentary closure.

The next step is only the two-field/variable documentary correction and its
updated identity receipt, followed by an affected read. The original human
31-page time-domain problem remains OPEN; no timers or budgets change. A future
bounded source/implementation assignment still requires explicit root admission.
No physical callback/full runner, app route, provider, kit test or release is
admitted, and the 47 formal criteria/dependency/resource sets and five release
paths are untouched.
