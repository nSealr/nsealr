# Native S3 public foundation: source-bound build packet

This delivery is a native ESP-IDF public-only peripheral/core check. It has no
identity import, new-key entropy provider, operation parser, authorization UI,
signing endpoint or persistent identity vault. Build/source observations do not
complete D01/D02 or admit secret custody.

The compiled source is a159db50af182d134ffce22d4d92826f24f1a651 on
implementation/s3-native-session. The original author/build operator was
/root/s3_session; /root/s3_native_finish assembled and inspected this packet.
Distinct root review and real-device execution remain pending.

The external packet is s3-probe/artifacts/native-public under the existing active
Linux root. packet.json identifies exact source, tools, locks, artifacts, offsets,
original command/result receipts and independent public oracle. SHA256SUMS covers
all packet members other than itself. The delivery metadata commit changes no
compiled source. The obsolete Arduino e1989219 source/artifacts remain immutable.

## Reused results and corrected failures

Native Rust run 41 passed in 13.7723 s on admitted crypto-bigint0.7.9. The native
consumer lock is versioned (9d04a151), SHA256
28fb1a218de7a16421e156de24b1153c70d6d905af48205a65226148d50b7640.
Root lock and vendor checksum are bound in packet.json to admitted source 563d10b3.
No old 0.7.6 lock or archive is adopted.

SDK run 45 failed while automatically retrieving esp-nimble (connection reset),
before application compilation. Exact parent-tree gitlink retrieval followed;
previous cached commits for six submodules were corrected to parent-tree pins.
run 58 preserves the complete recursive exact-pin closure; run 59 preserves the
clean SDK source status. The first compiler run 60 failed because the public
esp_lcd_panel_io.h declaration was not included. a159db50 adds that public header,
explicit secondary-consoleNONE, and a one-tick yield for the actual 100 Hz RTOS.
run 61 then passed in 5.1579 s. Original failures remain in the execution records.
Existing successful checks 62–68 (images, partition decode, ELF header, nm and ABI
disassembly) were read back, not rerun after the prior agent failed to compact.

The actual app is 293168 bytes, ELF32 little-endian Xtensa. Its public Rust ABI is
real code at 0x4200af50; disassembly calls the shared Rust SHA256/SecretKey/owner
functions. Its entry reserves 0x2e70 bytes of stack; this is not a peak-stack claim.
At runtime stack_raw is the high-water free-stack result. In this exact Xtensa
port StackType_t is uint8_t, so its units are bytes, measured after the public
check; deeper future operations require their own measurement.

## Generated configuration and linked closure

Read source-and-closure.json together with full sdkconfig/sdkconfig.h/json and the
map/nm files in the external packet. The generated main stack is 65536 internal
bytes: task creation uses the standard FreeRTOS dynamic allocator, whose SDK
heap_idf.c explicitly requests INTERNAL|8BIT; external-stack use is disabled.
The framebuffer alone explicitly requests 108800 PSRAM bytes, 64-byte alignment;
one queued transfer and its ISR completion semaphore protect the one framebuffer
from being redrawn during DMA. The LCD callback/bus behavior still needs hardware.

The generated configuration disables the primary and secondary SDK consoles,
bootloader/application default logs, and selects SDK silent panic reboot. There
is no esp_core_dump build component or generated coredump Kconfig symbol (the
default request alone is not evidence). No NVS/filesystem/OTA-state/dump partition
exists: decoded partition binary has one factory app at 0x10000, size 0x300000.

The final defined-code symbol set has no named SDK NVS, flash/partition writer,
OTA writer, or coredump entrypoint from the inspected family. app_update is in
the build closure because startup uses esp_ota_get_running_partition, a reader;
its writer functions are discarded. ROM absolute symbols remain addresses for
chip services. Their presence is not a runtime call or proof of radio operation.
No RF initialization, Wi-Fi or BT component is used by this app. This is not a
claim of physically absent radio or exhaustive proof against arbitrary writes.

nm -u is not empty: __cxx_fatal_exception, start_app and start_app_other_cores are
SDK CMake -u archive-extraction anchors. The real startup code is linked as
esp_startup_start_app/esp_startup_start_app_other_cores. Preserve this output;
do not describe undefined-symbol inspection as zero unresolved names.

C panic's configured silent restart and the reused public Rust helper's panic
are distinct: the latter spins silently and may leave the public check stalled.
Neither has qualified secret clearing/reset guarantees. USB Serial/JTAG remains
active for public diagnostics and explicitly unqualified for secrets.

## Exact flash and physical readback contract

Use the original generated flasher_args.json and packet hashes. Effective flash
parameters are DIO, 80 MHz, 16 MB: bootloader.bin at 0x0, partitions.bin at 0x8000,
firmware.bin at 0x10000. There is no boot_app0.bin. Kconfig selects QIO but defines
the flash-mode string as dio for initial bootloader loading, with boot-time quad
upgrade (ESP-IDF components/esptool_py/Kconfig.projbuild); never substitute qio
for the generated arguments by inference.

Root alone associates the current private USB inventory with this exact S3,
transfers/checks SHA256 on Mac, erases/flashes within existing authorization and
captures runtime. No eFuse writes are requested or authorized. Preserve the
source IDs, board/revision readback, commands, hashes and results privately;
do not publish unique USB IDs or MACs.

Require all of these observations before accepting this public foundation:

1. After boot, readable 320x170 border; RGBW top bars; numbered corners 1/2/3/4 and
   both live button indicators/counters. Judge clipping, geometry and colours
   from actual display evidence, not UART status or compilation.
2. Captured s3-native-abi-v1 has rc=0,negative=1,guards=1 and exactly the 128 hex
   oracle characters (64 bytes) in packet.json. SHA256 abc is from Python hashlib; scalar3's
   public key is from the independent official BIP340 vector 0 source.
3. GPIO 0 and 14 each require release of an initial held state and 40 ms stable
   transition before a press. Physical presses/releases/holds/bounce and reset
   need captured observations; prior helper host tests remain separate evidence.
4. Host input is ignored with a 64-byte per-loop read cap; no bytes echoed and no
   host commands accepted. Exercise a finite oversized/malformed/approval-like
   public payload plus an absent/non-reading host while local IO remains usable.
   TX can block at most 20 ms per call; loop yields one real 10 ms RTOS tick.
5. Reset/reconnect and malformed input must never turn this diagnostic into an
   import/signing interface. Timing and stack output are public-check measures,
   not qualification of future full request workloads or secret handling.

Board pins, ST7789 extra commands and orientation are attributed in app notices;
the packet retains LilyGO MIT notices, nSealr license, SDK/runtime-source
licenses and separate compiler/toolchain notices. licenses.json indexes original
paths/hashes and resolved native Cargo dependency licenses. TFT_eSPI/LVGL are not
part of this native runtime. This engineering packet is not a release SBOM or an
admission to publish firmware for real-identity use.
