# T01 provenance: Git mode correction

Author correction ready for distinct affected review. This does not accept the
current artifact or complete T01.

The independent review at `910425654c6a6d65b348e4285a5d6d35ab049525`
requested changes to checkpoint `0c4c223c94fb0b4b33e3a9fd571cf5fd88cfa4f4`.
Finding **T01-PROV-01** showed that the checker accepted an approved executable
LICENSE after `chmod 0645`, although actual Git reported and staged `100644`.
`review-finding-binding.json` binds that unchanged review and all 15 paired files
to their original public Git objects; its historical verdict remains unchanged.

Commit `faa784fc18bbb588c6956b83ce506c2714ed4697` fixes the expected answers and
adds two regression methods before the verifier correction. The preserved
`before-owner-bit-fix/` run exited 1 with two failures and two errors. Expected
modes come from actual `git add` and `git ls-files --stage`, compared with the
approved `git ls-tree` mode in disposable repositories with `core.filemode=true`.

Product commit `9e2bf3ddfc8968c384cefa7801e6a513efa0a395` changes one verifier
expression: use `stat.S_IXUSR` rather than any execute bit. The ten Git observations
cover removal of owner execution while another class remains executable, retained
owner execution, and permissions that leave Git's `100644` classification intact.
The same observations occur in the RED and GREEN logs. These are Git mode checks;
they do not guarantee preservation of all POSIX permissions, ownership or ACLs.

Actual checks on the committed product:

- `after-owner-bit-fix/`: both new regression methods pass.
- `component-tests-final/`: all 38 methods pass, including all 36 previous methods.
- `source-unbound-final/`: the real source checker exits 1 with the required
  unbound subtree refusal. `ARTIFACT_TREE_OID` remains `None`.

`source-invariants.json` binds both scripts, proves all previous 36 method bodies
and 22 proof files unchanged, and checks that removing the two added methods leaves
the complete prior test AST intact. Existing historical source roles and all other
product paths remain unchanged. Each runtime receipt records the committed product,
script hashes, pinned environment, actual exit and raw logs.

Only the two assigned scripts and this new proof directory change from checkpoint
`0c4c223c94fb0b4b33e3a9fd571cf5fd88cfa4f4`. The prior reports and failures remain
historical. The stable artifact literal, its distinct review, full T01 obligations,
protected integration and actual-main CI remain pending and root-owned. No Pi,
artifact, manifest, recipe, dependency, gate, hardware or K01 changes are included.
