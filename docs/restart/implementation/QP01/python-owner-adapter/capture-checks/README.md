# Python owner capture checks

This extends the accepted cold capture checker7d5 for the new Python consumer.
The existing `verify_first` function is AST-identical; original39 cases,64 child
identities, native/client/readiness, coverage and all three audit graphs remain
required. The Pi count is211: original194 plus3 pre-child and14 lifecycle/wire
methods. The new section requires70 structured rows: ten real operations with
five workers, eleven exact no-worker helpers, nine synthetic relation controls,
27 wire rejections and the real pipe-only513-byte control. Synthetic PIDs never
count as workers. The automatic positive releases259 bytes once; all nine
negative paths release zero. The actual eight-second wall deadline and the
source-derived pre-G wait pairs remain required.

`result.json` records the first completed source-addon check on original author
source dc0b7c81a12bf83d70b6ce9ecd65b49ce55fc082 and its unchanged full makeci log.
It binds the actual checker/driver/source/log hashes and Python3.12.15. Fourteen
single-defect synthetic log mutations are rejected, including missing/duplicate
cases, foreign ELF/collector, pre-collection release, leaked negative bytes,
early wall expiry, helper/real-worker confusion, boolean waits, the old194 count
and a missing original FG0 final. Optimized Python is explicitly refused because
the checker uses assertions. These controls execute no product O/W/native/client
processes and do not rerun makeci or CI. Original source/log bytes remain exact.

To repeat the verifier tests, supply a new, absent output directory:

```sh
python3 -B docs/restart/implementation/QP01/python-owner-adapter/capture-checks/checker-controls.py \
  docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py \
  ORIGINAL_MAKECI_LOG SOURCE_HEAD REPOSITORY NEW_OUTPUT_DIRECTORY
```

The old7d5 checker is preserved on actual main8f and its source-specific original
reports/manifests remain unchanged. The active checker is a new source revision;
its211 expectation must not relabel historical194 captures. This local proof is
not protected delivery, a GitHub run, ARM/physical/production qualification or a
reproducibility claim. Final adoption still requires distinct review, the normal
protected PR and actual-main checks, the unchanged generic completed-capture
verifier, this source addon and actual integrated-source provenance checks.
