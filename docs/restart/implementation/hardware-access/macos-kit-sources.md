# Source and verification note — 2026-10-25

Scope: the [Mac operator guide](macos-kit-identification.md), prepared from
nSealr commit `24621023f0c5d181ba41f1a2679a7608e2cdd20a`. It supplies practical
resource preparation for D01/V01 (commercial ESP32) and QP02/Q03 (P4). It changes
no task acceptance/dependency/resource set or release path. The existing S04
platform/document block remains in force.

## Authority and sample limits

The maintainer's direct 25 October update identifies SKU33360 and an S3 kit with
a non-touch display, two buttons, no battery and no SE; it explicitly authorizes
erasing/reflashing/developing on both without backup or further confirmation.
This supersedes any earlier inferred preservation restriction for these two
kits. It authorizes no other Mac device/data or irreversible eFuse operation.

The private support note `/home/tux/nsealr-hardware-confirmations-2026-10-25.txt`
is background; the newer direct authorization above controls. No private raw
inventory, hardware serial, credential or support transcript is imported here.
Actual Mac access and an operator session remain unestablished. No target
command has run on either kit. Pending support questions are not duplicated.

## Primary sources

All sources below were checked on 2026-10-25. Versioned source links are pinned;
the manufacturer manual and current documentation links can change.

| Source | Exact use and limit |
| --- | --- |
| [Espressif esptool v5.6.0 release](https://github.com/espressif/esptool/releases/tag/v5.6.0), published 2026-10-15 | Current stable release observed on the check date; tag object `5739c8454d25a3fdb7275b9734e55e56a3a73659`, peeled source commit `e970488de2c8f1906ca9b08de681b3f9dc58b2d5`. The guide pins 5.6.0 rather than a moving latest version. |
| [Pinned Python requirements](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/pyproject.toml), [official installation instructions](https://docs.espressif.com/projects/esptool/en/latest/esp32p4/installation.html) | Python >=3.10; isolated virtual environment; no global SDK/tool replacement. |
| [Pinned CLI](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/esptool/__init__.py), [operations](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/esptool/cmds.py), [configuration](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/esptool/config.py) | Explicit port/chip/baud/reset options; `chip-id`, `read-mac`, `get-security-info`; `chip-id` MAC fallback; explicit config override. `--no-stub` suppresses stub upload, not every volatile register write. |
| [Pinned P4 target](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/esptool/targets/esp32p4.py), [changelog](https://github.com/espressif/esptool/blob/e970488de2c8f1906ca9b08de681b3f9dc58b2d5/CHANGELOG.md) | Revision decoding, v1/v3 stub distinction, ECO5/v3.0, ECO6/v3.1 and ECO7/v3.2 support and later fixes. P4 connection may adjust watchdog/flash-power registers. This is tooling source evidence, not physical qualification. |
| [Espressif P4 revision identification](https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32p4/01-chip-identification/index.html), [errata summary](https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32p4/02-errata-summary/index.html) | Published revisions v0.0, v1.0, v1.3, v3.0, v3.1, v3.2. Major revision changes require compatible software; exact minor revision and applicable errata must also be retained. No unknown revision is admitted by this guide. |
| [Espressif AR2026-004 v1.0, 2026-05-15](https://documentation.espressif.com/AR2026-004_Compatibility_Advisory_for_ESP32-P4_Chip_Revision_v3.2_EN.html) | v3.2 flashing-tool compatibility and ROM watchdog/ESP-IDF issue. Its minimum esptool development versions are superseded by the pinned 5.6.0 release; firmware compatibility still requires its own check. |
| [Official esptool options](https://docs.espressif.com/projects/esptool/en/latest/esp32p4/esptool/advanced-options.html), [flash commands](https://docs.espressif.com/projects/esptool/en/latest/esp32p4/esptool/basic-commands.html) | Reset/no-stub semantics, exact offset/file pairs, `write-flash --erase-all`, and built-in write verification. No image offset is inferred. |
| [Waveshare manual](https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-3.5) | Explicit SKU33360/product association, C6H8 radio, ST7796 SPI/FT6336 I2C, USB TO UART versus USB OTG, BOOT/reset and battery behavior. PCB revision and actual wiring remain sample observations. The manual was available through the web reader; a separate direct HTML snapshot request returned HTTP403 and was not bypassed. |
| [SeedSigner MicroPython builder README at a9f865c68b20457692ab4547e3394785114b507f](https://github.com/kdmukai/seedsigner-micropython-builder/blob/a9f865c68b20457692ab4547e3394785114b507f/README.md) | Separate test-firmware/work-in-progress reference. Its board support table and firmware instructions are not nSealr compatibility, security, or image approval. No image was downloaded or selected. |

## Checks actually performed

Checks ran on the Linux development server, **not on the Mac or a kit**. An
isolated environment installed the exact PyPI release `esptool==5.6.0`, which
reported `esptool v5.6.0`, using CPython3.12.13. Local help confirmed the global
options and the three identification commands, plus future
`write-flash --erase-all`; `serial.tools.list_ports --help` confirmed `-v`.
Help requests do not open a serial port. No enumeration/probe, stub upload,
flash erase/write, firmware download or eFuse command was executed.

The first server `python3 -m venv` attempt failed because its CPython3.13 lacks
`ensurepip`; no OS change was made. A separate local `uv venv --seed` environment
was used for these help checks. This does not establish the Mac's prerequisites.
Local source snapshots, version/help receipts and dependency versions
are retained privately under
`/home/tux/nsealr/.restart-tools/goal/mac-kit-identification-private/`.

The original `b1dc18a6de90421b396eba4a7e27122804dd3844` guide's Bash blocks were
checked with `bash -n`; explicit argument forms were checked through CLI
`--help`, and its scope/diff was checked for whitespace and unintended changes.
Those original CLI checks remain applicable: the follow-up changes only shell
failure handling, log capture and recovery, leaving esptool arguments unchanged.

The follow-up adds grouped dependent preparation with `set -e`, guarded expected
disconnect/probe statuses, explicit stops after failed probes/writes, and private
write output/status capture. Changed shell syntax was checked with server
`bash -n` and reviewed for Mac Bash3.2 compatibility (`set -e`, brace groups,
`if`, `printf`, `exit` and the already-used indexed array); no Mac/Bash3.2 runtime
execution is claimed. Only the affected syntax and source/diff checks were repeated: no pip
reinstall, full test suite, device command or CI observation. No
documentation-phrase test or custom hardware verifier/parser was introduced.
Distinct affected-change review and root integration remain required.

Pinned source SHA-256 receipts (source files, not firmware):

| File at esptool source e970488de2c8f1906ca9b08de681b3f9dc58b2d5 | SHA-256 |
| --- | --- |
| `pyproject.toml` | `bc6c9ee0d977f51b0fbc11c924e765593bf56bc9668e3e2c9eefa20bc0ba4f01` |
| `esptool/__init__.py` | `953617e9031f3ece9d7e64a123001a116d59e8365972a1a85386c020b83a3596` |
| `esptool/cmds.py` | `8ec37315593cd255c924fd4c7fc7c0b9de5ca167b17a137464f96c966485c405` |
| `esptool/targets/esp32p4.py` | `459b5643fd5fe33079c286a09edab825088cb67532ef92708e42b560251f37f5` |
| `CHANGELOG.md` | `705da1e2307ccf8524eee8d0e6b4ef8243ea60a9fec76317394abc9edb15a0de` |
