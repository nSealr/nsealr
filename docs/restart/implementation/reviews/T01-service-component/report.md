# T01 service component — confirmed finding checkpoint

**REQUEST_CHANGES** on candidate `104f5e369244dcdc3afe87bb91074067c6ad8ac7`,
tree `cea265276082e920d1b067e3d2ed7cca92ddc01e`. Reviewer `/root/h01_sol`,
Sol6.1 xhigh; author `/root/a02_sol`. This checkpoint publishes the confirmed
finding immediately while the remaining assigned service review finishes.
It is not a completed T01/component PASS, source-pin review or adoption.

**T01-SERVICE-01:** `handleLocalServiceRequestAsync` directly invokes async
signer dispatch for `dispatch_signer_request` without `authorizeClient`.
The synchronous handler applies that mandatory permission check. This defect
already exists in dbad; it is not introduced by the24→104f delta. It remains a
real bypass in the current service path under review.

The paired `reproduce-authorization.ts` uses fixed public request/independent
signed-response/account fixtures and a synthetically valid exact local
route/capability/limits/review-plan snapshot. The actual path is
handleAsync→prepareSignerDispatch→createServiceRouteDispatcher→
SerialLineTransport→recording port, with no device or physical I/O. An unpaired,
revoked, expired or wrong-operation client is rejected by the synchronous API
with the exact `unauthorized_client` reason and zero opens/writes. For each of
the same contexts, the async API returns success after one open, one operation
write and one close. A properly authorized positive also succeeds.
`authorization.stdout.log` records all five scenarios and `authorization.command.json`
binds the actual command and reproduction hash; `source-bindings-checkpoint.json`
binds the source and independent inputs. Correct the async permission path
without removing the existing route/compatibility/resource/response checks;
retain meaningful denied/no-write and authorized positive regressions.

An initial reproduction used a synthetic path outside the accepted serial-device
path grammar. The parser correctly refused before dispatch. That failed setup
and original source are retained as `authorization-attempt-01.*` and
`reproduce-authorization-attempt-01.ts`. Only the synthetic path was corrected
to an accepted spelling; the opener always remains a recording fake. This setup
correction is separate from the confirmed bypass.

No product file changed. An offline frozen dependency install reused84 cached
packages with zero downloads; the existing package build prepares exact local
imports for these targeted checks. No broad test/CI, all42/all170+3, metadata,
Pi/provenance, hardware, current artifact/source PASS or release was assessed.
The remaining assigned slot/deadline/capacity/staleness perimeter is still being
reviewed; later findings or completion will be separately bound to this exact
candidate without rewriting this checkpoint commit.
