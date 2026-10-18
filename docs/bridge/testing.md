# Bridge verification

Run `pnpm run ci` from the product root after the frozen dependency install. This
executes build/type checking, all retained Vitest cases, consumer/examples/README
checks, generated API and boundary review checks, registry/import/browser gates,
release-output safety and an actual isolated packed SDK consumer.

The packed check installs the tarball outside the workspace and verifies Node
behavior, root/browser namespace boundaries, strict TypeScript imports, browser
bundling/execution without Node globals and rejected hidden imports. Runtime
external imports must each have an explicit production dependency. Browser VM
execution is not installed-browser qualification.

`make integration` executes all seventeen retained product integration steps in
one invocation, including the independent Pi review/sign/verify flow. Source
and contract tamper controls, optional Chromium/serial helper unit tests and
admitted production-claim, validator-ownership, CLI-guide and recipe guardrails
run in ordinary product CI. Optional actual browser/device commands are separate.

Card implementation cases are deliberately retired; retained ordinary route
checks and new card-command/route rejection cases preserve active safety bounds.
The exact before/after case correspondence is migration evidence, not a replacement
for running tests. The unchanged live-relay case requires explicit
`NSEALR_LIVE_E2E=1` and a real local Docker relay; its default skip stays visible.
No passing unit test closes physical resource or security admission gates.
