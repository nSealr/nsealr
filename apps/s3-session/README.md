# Native LilyGO S3 public foundation

This is the first native SDK consumer, using ESP-IDF5.3 at e0991fac and the
unchanged shared Rust engine. It replaces no historical probe artifacts.
Only public fixture3 is used: no real identity, signing, entropy collection,
import UI, or persistent data service is present.

The native app draws an RGBW border/pattern, numbered corners and two local
button counters (last decimal digit on screen, full count over USB). GPIO0/14 require a release after a held startup state and use
the already-tested40ms debounce helper. USB Serial/JTAG reports cached public
ABI output and physical button status once per second. It ignores received
bytes, up to64 per iteration, without logging content or accepting commands.

The SDK is built from source. Its own config uses a single factory-app partition,
no NVS/filesystem/OTA-state/dump partition, coredumpnone, silent panic restart,
no console logger and no radio initialization. These source settings require
generated-config, symbol, image and physical checks; they do not qualify key
custody or debug isolation. USB/JTAG remains explicitly unqualified for secrets.

Set NSEALR_S3_NATIVE_CORE_ARCHIVE to the admitted new native-core static archive,
built from core/Cargo.toml with the pinned Xtensa Rust compiler and matching
rust-src/sysroot closure. This reuses the earlier public ABI function source;
its lock is resolved against the separately admitted crypto-bigint0.7.9 vendor.
Do not copy the frozen Arduino probe lock or link its0.7.6 binary.

Use IDF5.3 with a separate build directory and sdkconfig path. Root alone reviews
and flashes the exact images/offsets/hash. Require the public output to match the
existing independent hashlib/BIP340 vector0 oracle, negative1/guards1, readable
numbered pattern and both physical inputs. Runtime ABI is first tested here,
not inferred from Arduino compile/link evidence.

Next secret-session implementation requires a separate concrete contract for
debug/entropy/internalRAM, local checksum entry/recovery, reset/lock/disconnect
and real monotonic review time. No timer scaling or deterministic entropy
fallback is selected by this public foundation.
