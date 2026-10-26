# Fallible S3 SARADC provider: public experiment only

Base83331c5a preserved; main99332719 merged in the same worktree as a5159582.
App/core/lock/vendor blobs were unchanged by the merge. Contract22caf7fb and
root review a98ce2cc authorize this narrow public lot, not identity admission.
One source is used through the existing core AuxiliarySource, no new engine/API
or changed100second clock semantics. Only scalar3 exists; no import/generation/
backup or entropy_ok/production capability. Four diagnostic32byte draws and at
most one new auxiliary attempt per boot; failure never retries until green.

The SDK APIs expose no per-call health/failure result. RCC claim/refcount/owner,
register expectations, source activity, typed failure, full32byte wipe and stopped
writes are necessary supporting evidence. Gross screens are not entropy proof.
ADC-183 affects rev0.2 DIGADC2 and the SDK helper uses doubleSAR: absence of DMA
is not an exemption. Exact primary followup was limited to TRM1.8 chapter25 and
39 plus the erratum/helper path; no per-SAR bypass guarantee was established.
Applicable manufacturer evidence or another reviewed supported path remains
necessary before production source admission. No unrequested certification or
formal minimum-entropy campaign is added as a hidden requirement.

The private RCC operations are the pinned e099 shared lock/reference primitives.
Busy acquire exits without increment; owned post-helper APB gate is restored
without a reset pulse. Changed/underflowed foreign counts remain untouched and
cause terminal cleanup failure, with balanced locks. SDK enable/disable source
is unchanged. Post-disable digital registers are not meaningful, so readable
bank tags distinguish omitted fields from zero data. RNG/RC entropy clocks left
running by SDK disable are explicit, and do not mean RF initialization.

SAR data status variation is a gross activity check, not a guarantee of analog
health. Configured CPU/APB rates and real selectors/dividers are logged; these
are not independent physical frequency measurements. TRM1.8 nominal20MHz and
legacy DIG_CLK8M/SDK8MHz naming differ. Preserve the S3 SDK1778APBcycle rate limit.
WIFI_EN/BT_EN masks are zero in the S3 SDK; no false RF-off check uses them.
No RF/ADC/I2S/temperature/battery client or other runtime RNG consumer may join
this closed source set without a new affected review. LCD I80 is LCD_CAM, with
completed DMA before sampling; USB remains active and its epoch cancels output.

Focused tests cover the exact shared RCC transaction policies, foreign count
preservation/lock balance, all declared active-field checks, error/short/oversize,
stuck/constant/repeated source, ownership loss, cleanup failure, cancellation,
rollback/timeout/frozen clock, full destination/staging guards, and the private
Rust callback path. The core suite is unchanged and is not replayed. Build/ELF/
macro/callgraph and root-only hardware observations remain separate gates.

Power model amendment belongs to the current docs/product requirements/threats,
D01 contract and D01 checkpoint only; historic P01/PR53 evidence remains immutable.
Root separately reviewed new document bytes in receipt5a9238d6; source bindings
must cite that amendment rather than relabel the old reviews. Pi/P4 unaffected.
