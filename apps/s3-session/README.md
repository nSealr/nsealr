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
