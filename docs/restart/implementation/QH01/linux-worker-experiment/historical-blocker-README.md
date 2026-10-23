# Linux worker experiment: platform blocker

The first focused run stopped before creating a worker. The pinned R00 CPython3.12.15 exposes `os.posix_spawn`, but the required `setsid=True` call raised `NotImplementedError: posix_spawn: setsid unavailable on this platform`. The admission requires refusal without fallback, so no dependent run or complete campaign followed.

Expectations and21 concrete rows across12 groups were committed at78372015 before harness code37d112e1 or execution. The clarified admissione287c938 preserves the original28546b89 and fixes seven independent cap rows before execution. The thirteen baseline parameters remain unchanged.

[The original command](focused-01/command.json), [raw stdout](focused-01/controller.stdout.log), [raw stderr](focused-01/controller.stderr.log), [first-row trace](focused-01/positive.json) and [focused summary](focused-01/summary.json) preserve the observed failure. There was one spawn attempt, zero created workers, zero control/image bytes, zero signals and no leaked parent descriptors. Of18 selected rows only the first reached the platform gate; the other17 were masked. The remaining3 were not selected. All21 behavioral rows are **NOT_EXERCISED**, with explicit mapping in [result.json](result.json).

The child was intended to return a predetermined existing public198-byte envelope after consuming the existing172800-byte public RGB input. It contains no decoder or signing operation. The unchanged [harness](experiment.py) is unvalidated beyond the failed spawn gate; source reading cannot substitute for execution of its later policy, CPU/AS, bounded I/O, cancellation, ownership or stolen-status paths.

The exact argv, R00 environment-map input and scoped overrides are in the command receipt. A future admitted rerun would use that pinned interpreter with `-I -B`, the existing environment JSON as a direct mapping, and a fresh `--out` directory. The harness refuses overwriting prior output. No interpreter/build/dependency/global configuration or R00 cache was changed.

Root must resolve this exact platform capability question before dependent execution. No alternative spawn primitive, private fallback, parameter increase, complete campaign or production integration was attempted. All47 criteria remain unchanged. This packet proves no QR/native decoder, resource containment, secret isolation, ARM/Pi, optical, camera, display or physical property.
