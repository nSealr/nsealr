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
The deterministic auxiliary fixture is public-test-only. USB Serial/JTAG remains
active and unqualified for secrets; SOF loss is detectable, serial-port close is not.

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
manifest; the delivery packet binds the complete archive/member closure.
USB Serial/JTAG driver, console, VFS CDC and automatic reboot helpers are absent
from the application. CDC descriptors carry no serial number or unique ID.
This describes the application only: reset, ROM, debug and PHY mux domains are
not disabled by eFuse and remain outside any secret-custody claim.

The main stack is 98304 bytes INTERNAL; the separate USB task uses 4096 bytes.
Bus reset, detach, suspend and DTR-low events observed by the actual stack revoke
the locally granted generation. Resume/configure/DTR-high never authorize a
request. ISR/task/main state uses the ESP-IDF safe critical section; no pending
bit is cleared. Saturation permanently closes authorization until CPU restart.
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
