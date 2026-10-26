# Normal public P4 C6 pad guard

Author: p4_optical_review. Root owns the distinct review, CI and USB/flash.
The previous product813e98cc and evidence delivery69ed53a2 remain unchanged in
history. Current main99332719 was merged in the same worktree as ebd27264;
the merge receipt proves identical app/core/crypto/SDK input and Rust archive.
No separate checkout or engine was created.

Root approved the bounded contract df7f6ec5; its current review receipt is
da27fbcf0e1795203360f5c12e9004b513a8ea1971f6821eddec28407b911b19.
This change admits only the existing public11x32 identity and22aux fixture.
It does not add entropy, secret import, custody or a new clock/ACTIVE API.

## Normal mode

Only mode0 starts a fixed GPIO54 guard before BOOT check or engine init.
It preloads output0, selects software GPIO output enable without inversion,
configures INPUT_OUTPUT without software pulls/open-drain, then reads the
actual pad and configuration. Admission requires input/output enabled, level0,
GPIO function/simple GPIO signal, no peripheral OE, inversion, open-drain or
software pull. A RAM ACTIVE flag alone cannot admit a check.

The worker checks before/after engine init and each operation, page commit,
decision return and aux fixture, before/after response commit and publication,
during response waiting and before cooperative WDT feed. Deadline and button
timestamps are sampled after the added guard IO where they authorize a return.
The core100tick deadline, physical1500..5000ms plus release FSM, fresh input,
touch navigation, DMA ACK and watchdog ownership are unchanged.

Failure is sticky for the boot. It cannot resume after repairing a pin.
Owned response bytes are cleared at the affected output boundary, the lamp is
turned off best-effort, and fatal stops new work. Task fatal attempts low again
and reports real pad/config/API errors. Its cleanup has no UI/feed/fatal calls,
and reentry cannot recurse. A successful cleanup does not restore ACTIVE.
An already displayed/scanned public QR cannot be revoked by this software.

Only SDK POWERON reset reason permits the public normal session; all other
reasons hold the guarded pad and stay UNAVAILABLE before engine/key init.
This is not authentication of a human, an external power cycle or USB topology.
There is no SDIO/CIS/Hosted/radio init or release/recovery in normal. Old mode3
probe artifacts and measurements remain on813, with no replay or new claim.

## Pinned OE detail and focused proof

IDF6.0.2/7101770d components/soc/esp32p4/register/hw_ver3/soc/gpio_reg.h
defines GPIO54 OEN_SEL reset0 and OEN_INV_SEL reset0. In the same SDK,
gpio_output_enable/gpio_config select data/function and enable output, but
do not normalize those OE bits; gpio_output_disable would, while releasing
the output. The old probe's initial INPUT happened to normalize the bits.

The normal guard instead performs one read/modify/write of the documented
GPIO_FUNC54_OUT_SEL_CFG_REG: set OEN_SEL and clear OEN_INV_SEL, preserving all
other bits. It occurs after latch0 and before INPUT_OUTPUT, with no disable or
input-only/release step. Public gpio_get_io_config/gpio_get_level then confirm
the real state. No private HAL API, SDK patch or generic pin-control layer.

The first GPIO stub assumed software OE by default. Its preliminary GREEN is
retained as history. Correcting that stub to the actual SDK reset state produced
the preserved RED before the OE fix. The same final fixture then passes:
27 cases of the actual helper with GPIO/register stubs under ASan/UBSan cover
set/config/read failure, disabled input/output, high pad, mux/signal/OE/pull
mismatch, sticky failure, no release, cleanup failure, abort before begin and
an abort racing the transition to ACTIVE. These are source-model tests, not
hardware/reset/RF measurements. Affected feed and response-clear tests also
check no feed/continuation and zero owned response before fatal. Unchanged
core/crypto/quirc/button/ACK suites and WDT canaries are reused, not replayed.

## USB, battery and remaining domains

Pinned vendor870588e6 schematic SHA3d8b63f8f2a5a89d00c54eaf9798658f3147774e8d3383a1b0a96d5fb9c82d30:
H1 native USB and H5 CH343 share USB0_5V, also exposed on J6pin2.
H1 data reaches P4 dedicated DP50/DM49; H5 data reaches CH343.
P4 GPIO24/25 USB1 reaches J6pin6/8 via R72/R70. USB0_5V reaches
VCC_5V through Q2/U13 and AXP2101 VBUS37; battery is BAT33/J1.
Thus no direct GPIO VBUS sense does not mean no possible PMIC detector.

Current BSP2.0.2 public headers/source expose no PMIC/VBUS status API.
Its USB host power-mode argument is not a VBUS measurement. No PMIC/USB driver
is added here. Future reviewed PMIC VBUS status could block VBUS-present, but
cannot prove data-host absence, which connector supplied it, J6 isolation,
charge-only wiring or absence of reconnect races.

CH343 VBUS9 sees USB0_5V while VIO1/VDD5pin3/V3pin6 use ESP_3V3.
Its DTR/RTS-to-BOOT35/ESP_EN path remains distinct. No inactive bridge output
or trusted human consent is inferred on battery or from an application flag.
Future offline use requires battery plus physically disconnected relevant USB
data paths as an operator precondition still to qualify.

Root measured one causal813/mode3 sequence: baseline0092:6666/CCCR32/CIS39B,
pad1/ie1/oe0; low timeout263, one release recovered the same endpoint, reassert
timeout263 and final pad0/ie1/oe1, cleanup0. Raw SHA
07b184166a51af337131ce6d0e2a69bff5f7fbab2c1cbf84885033aea8d892af.
The1942ms marker span is not a hardware minimum or RF proof. It is reused.

The maintainer confirmed battery operation/PWR and readable four-line decision
text/Reject on the old normal. The combined PWR reply does not prove CPU
continuity. The P4 has since been reconnected and root associated the same USB
bridge/path; current testing topology is USB connected. No new connection
request is needed. Root alone flashes after distinct source/packet review.

This is sampled software enforcement of the P4 pad on one pinned board.
Glitches between samples, real C6 pin4 voltage/PCB revision, die/firmware, RF,
USB host absence, panic/WDT/EN/brownout/power reset hold, RAM erasure, debug/log
safety, entropy and production/offline custody remain open. C6 may run during
ROM/early startup before this guard, with no engine initialized. Reset can
bypass task cleanup and release the pad. Nothing here closes S04 or a release.
