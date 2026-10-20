NSEALR_SOURCE_ROOT="$(pwd -P)"
RUSTFLAGS="--remap-path-prefix=${NSEALR_SOURCE_ROOT}=/nsealr" \
  cargo build --release --offline --locked -p nsealr-core \
  --target riscv32imafc-unknown-none-elf --target-dir target/manual/core
RUSTFLAGS="--remap-path-prefix=${NSEALR_SOURCE_ROOT}=/nsealr" \
  cargo build --release --offline --locked \
  --manifest-path apps/desktop-simulator/Cargo.toml --target-dir target/manual/host
