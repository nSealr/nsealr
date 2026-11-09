// Data extraction only. Generated files are included exclusively under cfg(test).
use std::{env, path::PathBuf, process::Command};
fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let script = root.join("tests/core/project_fixtures.py");
    println!("cargo:rerun-if-changed={}", script.display());
    println!(
        "cargo:rerun-if-changed={}",
        root.join("tests/core/projections.json").display()
    );
    println!(
        "cargo:rerun-if-changed={}",
        root.join("tests/core/contracts").display()
    );
    println!(
        "cargo:rerun-if-changed={}",
        root.join("tests/core/authorization-vectors.json").display()
    );
    let status = Command::new("python3")
        .arg(script)
        .arg(env::var_os("OUT_DIR").unwrap())
        .status()
        .expect("Python 3 is required for test-data projection");
    assert!(status.success(), "contract test-data projection failed");
}
