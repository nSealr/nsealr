# Identify the two ESP32 kits on the operator's Mac

Prepared 2026-10-25 against nSealr source
`24621023f0c5d181ba41f1a2679a7608e2cdd20a`. This is an operator procedure,
not a Mac connection receipt or a hardware result. Mac access, its OS/runtime,
and an available operator are still prerequisites; their follow-up is already
pending in the support thread. Guided local commands are sufficient. No
credentials, remote service, tunnel, or additional inventory questions are needed.

The maintainer explicitly authorized development, complete flash erasure and
firmware installation/reinstallation on **these two kits** on 25 October. No
backup or preservation of their current software is required, and that
authorization need not be requested again. It does not cover other Mac devices
or data, production keys, or irreversible eFuse operations. This procedure does
not resolve or bypass the existing S04 platform/document block.

| Operator label | Maintainer identification | Still to establish on the sample |
| --- | --- | --- |
| `P4` | Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5, SKU33360; camera, battery, touchscreen | PCB marking/revision, actual ESP32-P4 silicon revision, host interface and device identity |
| `S3` | ESP32-S3 kit; display without touch, two buttons, no battery or SE | Exact manufacturer/model/PCB revision, button functions, interfaces and device identity |

SKU33360 has an ESP32-C6H8 radio coprocessor; the documented display is ST7796
over SPI and touch FT6336 over I2C. Those are vendor specifications, not observed
sample properties or an offline guarantee. See the [sources and checks](macos-kit-sources.md).

## 1. Prepare isolated tools and private evidence

Use an existing Python **3.10 or newer** with `venv` and pip. If it is unavailable,
stop at that prerequisite; do not change the OS, install drivers, disable a host
security control, or substitute an older esptool. Close any serial monitor using
the selected kit. Use a USB **data** cable.

Open a clean Bash session, then run the following on the **Mac**, one block at a
time. Keep `set -e` enabled: an unhandled failure exits this clean Bash before the
next command. The preparation group is read as one command before it runs, so
its remaining pasted lines cannot fall through into the parent shell.
`KIT_WORK` is a new private local directory; retain it outside
public repositories and cloud-shared folders. Its location is printed before
tool preparation begins.

```bash
/bin/bash --noprofile --norc
```

```bash
set -e
{
    umask 077
    KIT_WORK=$(mktemp -d "$HOME/nsealr-kit-id.XXXXXX")
    printf 'Private evidence directory: %s\n' "$KIT_WORK"
    cd "$KIT_WORK"
    sw_vers > mac-os.txt
    uname -m > mac-architecture.txt
    command -v python3 > python-path.txt
    python3 --version > python-version.txt 2>&1
    python3 -m venv "$KIT_WORK/tools" > venv.txt 2>&1
    KIT_PY="$KIT_WORK/tools/bin/python"
    "$KIT_PY" -m pip --isolated install --index-url https://pypi.org/simple 'esptool==5.6.0' > install.txt 2>&1
    "$KIT_PY" -m pip check > pip-check.txt 2>&1
    "$KIT_PY" -m pip freeze > installed-packages.txt
    printf '[esptool]\n' > "$KIT_WORK/esptool.cfg"
    export ESPTOOL_CFGFILE="$KIT_WORK/esptool.cfg"
    export ESPTOOL_OPEN_PORT_ATTEMPTS=1
    export NO_COLOR=1
    "$KIT_PY" -m esptool version > esptool-version.txt 2>&1
    cat python-version.txt esptool-version.txt
}
```

Require `esptool v5.6.0` and a successful `pip check`. The empty explicit
configuration prevents a pre-existing reset configuration being selected.
Dependencies are recorded, not claimed to be a reproducible SDK/toolchain lock.

### Recovery only: if the clean Bash exits

Stop; do not paste the next block into the parent shell. Keep the printed
directory and its original logs. After resolving the failed prerequisite or
assessing the failed probe, open a fresh `/bin/bash --noprofile --norc`, then
restore the exact printed directory below:

```bash
set -e
{
    umask 077
    KIT_WORK='/REPLACE_WITH_EXACT_PRINTED_PRIVATE_DIRECTORY'
    cd "$KIT_WORK"
    KIT_PY="$KIT_WORK/tools/bin/python"
    export ESPTOOL_CFGFILE="$KIT_WORK/esptool.cfg"
    export ESPTOOL_OPEN_PORT_ATTEMPTS=1
    export NO_COLOR=1
}
```

For a preparation failure, resume at the failed command and finish the remaining
preparation checks, using a new output filename for any retry so the failure log
survives. For an identification retry, repeat step 2: it creates a fresh kit-log
directory and rebinds the port before `KIT_ROM` is rebuilt. A failed erase/install
requires assessment before any further write or boot; this recovery block does
not resume that operation.

## 2. Bind one exact host port to one physical kit

Work on **one of the two authorized kits at a time**. Disconnect the other kit
from the Mac, leaving unrelated peripherals alone. Record the chosen kit's
product/PCB markings and the connector used. For the P4, the vendor identifies
the programming connector as **USB TO UART**; USB OTG is a separate connector.
Do not identify an unknown S3 board from its two buttons alone.

Connect that kit and take one inventory. Enumeration does not probe every port
with esptool. USB inventories may contain identifiers of unrelated peripherals:
keep the unedited files private.

```bash
{
    KIT_TAG='P4'
    KIT_LOG=$(mktemp -d "$KIT_WORK/$KIT_TAG.XXXXXX")
    printf 'Private kit evidence directory: %s\n' "$KIT_LOG"
    "$KIT_PY" -m serial.tools.list_ports -v > "$KIT_LOG/serial-inventory.txt" 2>&1
    system_profiler SPUSBDataType > "$KIT_LOG/usb-inventory.txt" 2>&1
    cat "$KIT_LOG/serial-inventory.txt"
}
```

Use `S3` instead of `P4` for the other kit. Each attempt gets its own directory.
From the actual inventory, copy **one complete `/dev/cu.*` path** into the
assignment below.
Record its USB VID/PID, serial number if present, location and interface/product
description, correlating them with the USB tree and physical connector. VID/PID
and a product name alone do not uniquely identify a board; USB serial numbers
can also be absent or shared. Never choose the first match, a wildcard, a
Bluetooth port, a `/dev/disk*` node, or a guessed example port.

```bash
KIT_PORT='/dev/cu.REPLACE_WITH_ONE_EXACT_INVENTORY_ENTRY'
ls -l "$KIT_PORT" > "$KIT_LOG/port-connected.txt" 2>&1
```

Check the file: this exact node must exist. Unplug **only that kit's USB cable**,
then run:

```bash
if ls -l "$KIT_PORT" > "$KIT_LOG/port-disconnected.txt" 2>&1; then
    KIT_STATUS=0
else
    KIT_STATUS=$?
fi
printf '%s\n' "$KIT_STATUS" > "$KIT_LOG/port-disconnected.exit"
cat "$KIT_LOG/port-disconnected.txt"
if [ "$KIT_STATUS" -eq 0 ] || [ -e "$KIT_PORT" ]; then
    printf 'Stop: selected port did not disappear.\n' >&2
    exit 1
fi
```

The guarded nonzero `ls` result must be a missing-node error; inspect the raw log
and stop on any other error. Reconnect the same kit through the same connector
and verify its return with `ls -l "$KIT_PORT"`. If this fails because the node
changed, use the recovery path to refresh the inventory and bind the new exact
path. Stop if the physical association is ambiguous. A battery-powered P4 may
keep running when USB is removed; this checks host-port association, not loss of
board power.

## 3. Read ROM identity and security state

The following commands do not erase/program flash or burn eFuses. They reset the
selected MCU and can alter volatile loader/watchdog/power registers; they do not
upload the flasher stub. Reset can lose volatile application state. Record the
observed reset/re-enumeration behavior. `--after no-reset` requests that esptool
leave the MCU in its loader rather than start the application.

Always supply the selected port. `--chip auto` identifies the chip **on that
port**; it is not permission to search other ports. Preserve stdout, stderr and
exit status without editing them.

```bash
KIT_ROM=( "$KIT_PY" -m esptool --chip auto --port "${KIT_PORT:?select the exact port}" --baud 115200 --before default-reset --after no-reset --no-stub --connect-attempts 1 )
if "${KIT_ROM[@]}" chip-id > "$KIT_LOG/chip-id.txt" 2>&1; then
    KIT_STATUS=0
else
    KIT_STATUS=$?
fi
printf '%s\n' "$KIT_STATUS" > "$KIT_LOG/chip-id.exit"
cat "$KIT_LOG/chip-id.txt"
if [ "$KIT_STATUS" -ne 0 ]; then
    printf 'Stop: chip identification failed; retain the logs.\n' >&2
    exit "$KIT_STATUS"
fi
```

Require exit 0, the expected **ESP32-P4** or **ESP32-S3** family and an explicit
revision. `chip-id` may report that the chip has no separate chip ID and print
its MAC instead; the `Chip type` line supplies the family/revision. A numeric
chip-type ID is not a unique board serial number. A P4 connector that reports
ESP32-C6 has not identified the intended P4 target: stop. Do not count a failed
reset or a reported running/reused stub as ROM evidence.

If automatic reset fails, stop and retain the failure. For SKU33360 the vendor
documents holding BOOT during power-up/reset to enter download mode. Only use
buttons positively identified on the sample; the unknown S3 needs its actual
board instructions. After a documented manual entry, recheck the selected port
and replace `--before default-reset` with `--before no-reset` in `KIT_ROM`.
Do not try other devices, speculative button combinations or repeated reset loops.

Once family/revision match, run these two commands, checking each result before
continuing:

```bash
if "${KIT_ROM[@]}" read-mac > "$KIT_LOG/read-mac.txt" 2>&1; then
    KIT_STATUS=0
else
    KIT_STATUS=$?
fi
printf '%s\n' "$KIT_STATUS" > "$KIT_LOG/read-mac.exit"
cat "$KIT_LOG/read-mac.txt"
if [ "$KIT_STATUS" -ne 0 ]; then
    printf 'Stop: MAC read failed; retain the logs.\n' >&2
    exit "$KIT_STATUS"
fi
```

```bash
if "${KIT_ROM[@]}" get-security-info > "$KIT_LOG/security-info.txt" 2>&1; then
    KIT_STATUS=0
else
    KIT_STATUS=$?
fi
printf '%s\n' "$KIT_STATUS" > "$KIT_LOG/security-info.exit"
cat "$KIT_LOG/security-info.txt"
if [ "$KIT_STATUS" -ne 0 ]; then
    printf 'Stop: security-state read failed; retain the logs.\n' >&2
    exit "$KIT_STATUS"
fi
```

Require exit 0 and matching identity throughout. Record the factory/base MAC,
full silicon revision, and the reported Secure Boot, flash-encryption and
download-mode flags, retaining all reported fields. These are inventory
observations, not authenticity attestation or proof of secure custody. If
security restrictions prevent a read, a field is unavailable, or identities
disagree, record the limitation and stop before erase/flash. Do not use `--force`,
unlocking/provisioning commands, flash/memory dumps, or any `espefuse` operation.
No seed, key, PIN or existing flash image is needed.

Finish each private record with operator/time, physical label and PCB revision
(or explicitly unknown), connector/cable, exact port and USB fields, ROM
family/revision/MAC, security report and observed disconnect/reset behavior.
Hash the evidence files using `shasum -a 256`; retain failures as well as
successes. Share only the minimum reviewed identity summary through the existing
support path; raw MACs, USB serials and Mac inventory remain private. Disconnect
this kit before repeating steps 2–3 for the other kit. No hardware PASS exists
until an actual operator has supplied these observations.

## 4. Future complete erase and installation: gated by the build record

There is **no selected/approved nSealr image or flash map in this guide**. Existing
erase/reflash authorization applies after the sample is matched and a reviewed
build record supplies its exact board, chip family/revision range, source/build
identity, every image's SHA-256, offsets and required flash parameters. Recheck
the port binding and ROM identity immediately before writing. Stop on an unknown
S3 model or unsupported silicon/security state.

For P4, preserve the full `vM.X` result: v1.x and v3.x are different firmware
compatibility families. Esptool support alone does not make firmware compatible.
The v3.2 ROM also has a documented flashing/tool and ESP-IDF watchdog compatibility
advisory. The pinned tool has explicit v3.0/v3.1/v3.2 handling and a separate
pre-v3 loader; an unfamiliar revision requires a new source check, not an
assumption.

For an approved **single-image** distribution only, set `KIT_CHIP` to the matched
`esp32p4` or `esp32s3`, and set `KIT_IMAGE` and `KIT_OFFSET` from that build record.
Do not guess `0x0`, reuse another board's image, or treat an application binary
as a complete distribution. Hash the actual file first:

```bash
shasum -a 256 "${KIT_IMAGE:?approved image path required}"
```

Compare with the independently retained approved SHA-256. Only after an exact
match and complete compatibility/offset check may the following future command
perform the already-authorized **whole-chip erase followed by installation**.
This form also requires that the approved build use the image's embedded flash
parameters; otherwise prepare the complete reviewed command with its required
parameters first.

```bash
if "$KIT_PY" -m esptool --chip "${KIT_CHIP:?matched chip required}" --port "${KIT_PORT:?exact bound port required}" --baud 115200 --before default-reset --after no-reset --connect-attempts 1 write-flash --erase-all "${KIT_OFFSET:?approved offset required}" "${KIT_IMAGE:?approved image required}" > "$KIT_LOG/write-flash.txt" 2>&1; then
    KIT_STATUS=0
else
    KIT_STATUS=$?
fi
printf '%s\n' "$KIT_STATUS" > "$KIT_LOG/write-flash.exit"
cat "$KIT_LOG/write-flash.txt"
if [ "$KIT_STATUS" -ne 0 ]; then
    printf 'Stop: erase/install failed; do not boot or retry before assessment.\n' >&2
    exit "$KIT_STATUS"
fi
```

For a multi-image build, the reviewed command must instead include **all** exact
offset/file pairs and required flash parameters from its build record. Review
every argument; do not execute an unreviewed `@flash_args` file. Capture the exact
command, tool version, image hashes, output and exit status privately. Require
esptool's successful write/verification result; do not force past security or
revision checks. Any failure stops further writing/booting pending assessment.

Keep the board in the loader until its approved first-boot/test procedure is
ready. This does not disable or isolate the P4's C6 radio, prove secure erasure of
other storage, qualify display/camera/input, or close D01/QP02 or any release gate.
The separate SeedSigner MicroPython port is a work-in-progress reference; its
images and support labels are not nSealr approval.
