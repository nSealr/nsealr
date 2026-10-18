// Data extraction only. Generated files are included exclusively under cfg(test).
use std::{env, path::PathBuf, process::Command};
fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let script = root.join("ci/project_core_fixtures.py");
    println!("cargo:rerun-if-changed={}", script.display());
    println!("cargo:rerun-if-changed={}", root.join("ci/core-test-projections.json").display());
    println!("cargo:rerun-if-changed={}", root.join("protocols/contracts/v1").display());
    let status = Command::new("python3").arg(script).arg(env::var_os("OUT_DIR").unwrap())
        .status().expect("pinned Python is required for test-data projection");
    assert!(status.success(), "contract test-data projection failed");
}
