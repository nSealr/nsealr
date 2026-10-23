The first focused readiness-control invocation on fa93346c failed during
TypeScript transformation, before any child was spawned. The new line comment
accidentally included the closing `},` of `present`; the parser reported the
later `close:` token at line176. Moving that delimiter onto its own line fixes
the syntax. This is a correction-harness authoring error, not a native/client
runtime result. Original stdout/stderr and source-bound receipt are retained;
no control case is counted as executed by this failed invocation.
