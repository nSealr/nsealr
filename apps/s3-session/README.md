# Native LilyGO S3 public request flow

This native ESP-IDF5.3 app carries the existing nsealr1f/version-2 request through
the unchanged Rust engine, complete local display and physical input to a
public-fixture signature. Only known published scalar3 is compiled in. No
arbitrary scalar/nsec, recovery export or production entropy endpoint exists.

Locally press/release GPIO14 to enable the public identity. The complete actual
public key appears on screen. Data pages use GPIO14 Next and GPIO0 Back.
On the separate final page, hold GPIO14 alone for1.5seconds to Approve; GPIO0
Rejects. Holding both for1.5seconds locks, with precedence over Approve.
Every new page requires released inputs after its complete DMA commit.
GPIO0 in the Idle/Locked menu rotates180degrees and remains Locked. This RAM-only
choice is fixed throughout a request; GPIO functions do not change. The banner
identifies the expected buttons-left/right edge. Root must observe both views.
After settlement, a new local enable is required. RESULT QUEUED means accepted
by the USB driver, not delivered to the host. Already queued public bytes cannot
be recalled by Lock/disconnect. A queue failure requires reset, with no automatic
retry. A finite public metric reports DMA frames, elapsed time including human
wait, and minimum free main stack since boot. All screens identify PUBLIC TEST KEY.

The explicit clock unit is real monotonic seconds from esp_timer_get_time.
The unchanged100tick core expiry is intake_seconds+100; flooring may expire
up to1second before100.000 elapsed seconds. It is never paused or rescaled.
The deterministic auxiliary fixture belonged to the historical public images. In the previous
public image a0ea67e0 (delivery a1e9052a), USB Serial/JTAG remained active and
unqualified for secrets; SOF loss was detectable but serial-port close was not.
This newer image uses the OTG CDC transport described below. ROM, physical reset,
debug and PHY mux domains remain separate and unqualified for secrets.

The single factory-app SDK/config and framebuffer/DMA ownership are inherited
from the source-frozen foundation packet. No NVS/FS/OTA state or identity
persistence is added. Rust panic still spins; no secret-session panic/reset
qualification is claimed. Default product readiness/capabilities remain unavailable.

See docs/restart/implementation/D01/native-session-contract.md for exact bounds,
UI, tests and future OTG/entropy/internal-RAM/recovery admission gates. Build/test
results must name the actual candidate; this README alone records no success.
Foundation packet bcad72fa/a159db50 remains unchanged.


The next public experiment uses USB OTG Full Speed CDC ACM through the exact
esp_tinyusb 3.0.0 input in tinyusb-source.json. Set
NSEALR_S3_TINYUSB_COMPONENT to the existing external component directory named
esp_tinyusb (a symlink to the admitted source is sufficient). CMake pins its
manifest only; full integrity of all 439 members is checked by the recorded
preflight and bound to the complete archive/member closure in the packet.
USB Serial/JTAG driver, console, VFS CDC and automatic reboot helpers are absent
from the application. CDC descriptors carry no serial number or unique ID.
This describes the application only: reset, ROM, debug and PHY mux domains are
not disabled by eFuse and remain outside any secret-custody claim.

The main stack is 98304 bytes INTERNAL; the separate USB task uses 4096 bytes.
Bus reset, detach, suspend and DTR-low events observed by the actual stack revoke
the locally granted generation. Resume/configure/DTR-high never authorize a
request. ISR/task/main state uses the ESP-IDF safe critical section; Enable never clears
a revocation epoch or acknowledges a later event. Saturation permanently closes authorization until CPU restart.
Checks follow DMA/drain and signing and precede/follow nonblocking response TX.
An event racing TX may leave a prefix or full public response already queued;
TX UNCERTAIN is terminal and no byte-recall or host-delivery claim is made.

Three fixed 64-byte public patterns sample internal NOLOAD RAM, RTC NOLOAD RAM
and ordinary BSS. Their previous validity is captured after SDK startup, before
OTG install, then a new public pattern is written. The checksums detect accidental
changes only. Invalid means unknown; zero does not prove full-memory erasure.
The diagnostics report the PHY mux, reset reason, coalesced event counters,
stack minima and internal heap. USB callbacks do no Rust/display/writer work.
The TinyUSB bus-reset hook runs only after its fixed event queue accepted the
event: queue overflow and unavailable VBUS detection limit observation. Detach
can also mean SetConfiguration(0); suspend does not prove physical unplug.

Locked only: short GPIO0 still rotates 180 degrees; holding GPIO0 alone for
5 seconds shows PUBLIC RESTART and calls esp_restart for a distinct causal test.
Both has Lock precedence. Restart requires fresh release and is unavailable in
Ready/review/sign. The request gesture helper and Rust source are unchanged.
Only fixed public diagnostics can be sent without local Enable; no host command
or arbitrary memory selector is added. Real identities, entropy and recovery
remain gated separately. Physical evidence for the previous Serial/JTAG image
remains historical and does not qualify this OTG image.

The bus-reset observation additionally closes reset_pending before older queued
callbacks can run. A FIFO barrier in the same pinned TinyUSB queue executes
after its usbd_reset; only the matching reset ticket can clear pending, and it
clears operational flags rather than authorizing an epoch. Only the nonblocking
ISR send is used. A failed barrier enqueue or unexpected task-origin bus reset
leaves authorization closed until CPU restart. A reset event rejected before
the observation hook remains an explicit stack-observation limit.


The current experimental entropy adapter replaces target PublicAux with a
fallible private callback implementing the unchanged core AuxiliarySource.
Only published scalar3 is present. The deterministic0x42 fixture remains in host
tests; the running target has no such fallback. No identity generation, import,
recovery or secret endpoint is added. ADC-183 on S3rev0.2 remains unresolved for
production-source admission: doubleSAR operation and varied output do not close
it. No FIPS/AIS or formal minimum-entropy certification is introduced as a gate.

At startup the diagnostic screen offers0 Skip /14 Run after fresh release and
complete frame commit. Open the public CDC logger first. Run performs at most
four independently acquired32byte public draws, stops on the first failure,
then requires a fresh acknowledgement to enter the known-public fixture. Skip
also enters that fixture. The target permits at most one new auxiliary attempt
for public signing per boot, whether it succeeds or fails; no retry until green.
get_public_key still uses the same known public identity. Diagnostic samples are
never identity/scalar material and are never reused as signing auxiliary.

The provider owns the main task, one generation, one SARADC RCC reference and
an exact closed software consumer set. Busy exits leave foreign counts and
registers unchanged. Enable uses the unmodified e099 helper, then explicitly
restores its APB bus gate under the same reference without pulsing reset. It
verifies declared selectors/dividers/timer/pattern/ref/mux/power fields, and exact
LCD/USB GPIO mux/output-enable/matrix configuration. Disable is followed only
by readable SYSTEM/SENS/internal-analog checks; gated/in-reset digital data is
UNKNOWN, not a zero-valued health or erasure observation. A changed foreign count
is preserved and poisons further provider use; no successful cleanup is claimed.

A50ms between-call deadline and finite settle polling detect specified failures;
SDK helpers/RNG may contain non-cancellable waits, so this is not a hard return
bound for stuck hardware. Retained staging/output32bytes are wiped on failure,
with exact-count and guard checks. The ADC1 completion observer requires two
independent clear-to-observed0-to-new1 sequences around the eight RNG words,
briefly stopping only the trigger timer for each clear. Timer enable is restored
and checked before each RNG word. Initial DONE1 can clear normally; a sticky1,
missing completion or lost owner/deadline refuses. Both phases share the same
50ms budget including claim, settle and cleanup. An in-flight conversion may
complete after clear: this witnesses completion after0, not a conversion started
only after timer restart, ADC2 activity or entropy quality.

The historical08d919c3 refusal saw DATA_STATUS0x14000 twice and supplied0bytes;
its Health result is preserved. Raw last-value equality alone is not a documented
activity/health condition, so it is now diagnostic and cannot substitute for the
two progress witnesses. All-zero/all-FF/repeated-word/duplicate-block screens
remain mandatory. The private report stays384bytes by packing the<=8word count
and two phase bytes into its existing four bytes. The bounded public log adds
progress=pre/post in hex: bit0 initial read,bit1 initial1,bit2 observed clear0,
bit3 fresh1. Successful phases are d or f; phase0 means not reached, while bit0
distinguishes an initial0 reading from an unknown initial value. Core Rust, public request/response ABI and protocol are unchanged.
The API supplies no per-call health report. Private GPIO comparison is exact; its compact logged
signature is only diagnostic. CPU/APB values are configured clock accounting,
not independent physical frequency measurements. S3 clock macros called WIFI_EN
and BT_EN are zero in this SDK: they cannot prove RF state. Radio absence/RF-off
measurement is not claimed from register names or uninitialized RF APIs.

The public log is bounded and may be dropped if the host does not read. Queue
acceptance is still not delivery. Full diagnostic snapshots/samples occupy at
most2048bytes INTERNAL; provider state is at most256bytes, no new task/heap/DMA,
and main/USB stacks remain98304/4096bytes. Source/build/diagnostics qualify only
this public experiment. The S3 product power model is USB-only: no battery,
supercapacitor or independent supply requirement; E5 powered data-only unplug is
not applicable. A future real identity must reload locally after power loss;
this automatically reinitialized fixture proves neither reload nor RAM erasure.
