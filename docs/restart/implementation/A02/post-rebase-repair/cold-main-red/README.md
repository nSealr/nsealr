# Actual cold-main RED before repair admission

This read-only reproduction fetched only exact protected main
`d931277bebbc5f43514b0e8438d65fb60603fa35` from the public repository into an
absent owned repository. It has only `refs/heads/cold-main`, no configured remote,
extra refs, alternates, shallow/graft history or hardlinked/symlinked objects.
All 8,679 stored objects are reachable from the 331-commit selected history.
The repository itself remains ignored and is not public evidence intake.

The [summary](summary.json) and [actual commands](commands.json) record the
untouched checker source, environment and logs. Historical `86569e0` and
`5cb16cb` commit objects are absent with actual exit128. Adopted `68508ea` and
`59653fc` are present ancestors. Manifest `initial_import_commit` still contains
the literal historical `86569e0` value; it was not rewritten.

The current checker actually exits1; its caught Git subprocess exits128 while
loading the historical baseline manifest. A separate direct Git-show command
preserves that exact exit128 and stderr. This is the intended pre-repair RED,
not an accepted failure or a corrected result. No checker/test/artifact changed,
no suite or CI was retried, and no future repair approval is inferred.
