# nSealr integration gates; embedded and host Cargo graphs remain separate.
.PHONY: test lint audit docs ci cargo-fmt cargo-clippy cargo-test cargo-deny \
	coverage-ratchet vector-harness repro-build rust-ci

RISCV_TARGET := riscv32imafc-unknown-none-elf
RUST_COVERAGE_JSON := build/rust-core-coverage.json
HOST_COVERAGE_JSON := build/rust-host-coverage.json
HOST_MANIFEST := apps/desktop-simulator/Cargo.toml

# ---------------------------------------------------------------------------
# Generic (toolchain-agnostic) Python gates.
# ---------------------------------------------------------------------------
test:
	python3 scripts/verify_repo.py
	python3 scripts/validate_restart_plan.py
	python3 scripts/verify_evidence.py
	python3 scripts/verify_contracts.py
	python3 -m unittest discover -s scripts -p 'test_contracts.py'
	python3 -m unittest discover -s scripts -p 'test_evidence.py'
	python3 -m unittest discover -s scripts -p 'test_validate_restart_plan.py'
	python3 -m unittest discover -s scripts -p 'test_verify_repo.py'
	python3 -m unittest discover -s tools/baseline -p 'test_*.py'

lint:
	python3 scripts/verify_repo.py
	python3 -m compileall -q scripts

audit:
	python3 scripts/verify_repo.py
	python3 scripts/validate_firmware.py

docs:
	python3 scripts/verify_repo.py
	python3 scripts/validate_firmware.py

# ---------------------------------------------------------------------------
# Rust workspace gates (EXECUTION-ETHICS.md Section C). The `std` cargo feature
# is proven non-inert by the std-gated test in `cargo-test`.
# ---------------------------------------------------------------------------
cargo-fmt:
	cargo fmt --all --check
	cargo fmt --manifest-path $(HOST_MANIFEST) --all --check

cargo-clippy:
	cargo clippy --all-targets -- -D warnings -D dead_code
	cargo clippy --all-targets --all-features -- -D warnings -D dead_code
	cargo clippy --manifest-path $(HOST_MANIFEST) --all-targets --all-features -- -D warnings -D dead_code

cargo-test:
	cargo test --workspace
	cargo test -p nsealr-core --features std
	cargo build -p nsealr-core --target $(RISCV_TARGET)

cargo-deny:
	python3 -B -m unittest discover -s docs/restart/implementation/R00/audit-data -p 'test_audit_rust.py'
	python3 scripts/audit_rust.py

# The desktop-simulator parity oracle: exhaustively replays every in-scope
# specs/vectors/<category>/*.json file through nsealr-core's public API and
# enforces the category completeness rule (Phase 03 Task 04). Every Rust app in
# this workspace must pass this gate before claiming vector compliance.
vector-harness:
	cargo test --manifest-path $(HOST_MANIFEST) --locked --offline

coverage-ratchet:
	@mkdir -p build
	cargo llvm-cov --workspace --all-features --summary-only --json --output-path $(RUST_COVERAGE_JSON)
	cargo llvm-cov --manifest-path $(HOST_MANIFEST) --workspace --all-features --summary-only --json --output-path $(HOST_COVERAGE_JSON)
	python3 ci/check_coverage_ratchet.py $(RUST_COVERAGE_JSON) ci/ratchet.json $(HOST_COVERAGE_JSON)

# Reproducible-build gate: two clean release builds must be byte-identical, and
# the nsealr-core device rlib must reproduce byte-for-byte from a second checkout
# at a different filesystem path (offline against `vendor/`, pinned toolchain,
# `--remap-path-prefix`). See docs/reproducible-build.md and ci/repro_build.sh.
repro-build:
	bash ci/repro_build.sh

rust-ci: cargo-fmt cargo-clippy cargo-test vector-harness cargo-deny coverage-ratchet repro-build

contract-ci:
	$(MAKE) -C protocols/contracts/v1 ci

bridge-ci:
	pnpm run ci

pi-ci:
	$(MAKE) -C apps/pi ci

integration-tests:
	python3 -B -m unittest discover -s tests/integration -p 'test_*.py' -v

integration:
	python3 -B -m tests.integration.run

product-gates:
	python3 scripts/check_product_gates.py
	python3 -B -m unittest discover -s scripts -p 'test_product_gates.py' -v

.PHONY: contract-ci bridge-ci pi-ci integration-tests integration product-gates
ci: test lint audit docs rust-ci contract-ci bridge-ci pi-ci integration-tests product-gates integration
