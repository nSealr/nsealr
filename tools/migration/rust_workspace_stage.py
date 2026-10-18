#!/usr/bin/env python3
"""Split actual embedded/host Cargo workspaces and preserve all existing gates."""
import argparse,json,os,shutil,tempfile
from pathlib import Path
from admission import Recorder
from rehearse import canonical
from transforms import Changes


def apply(target,output,environment):
    output.mkdir(mode=0o700);rec=Recorder(output/'lock-generation');c=Changes(target)
    root_manifest=(target/'Cargo.toml').read_text()
    root_manifest=root_manifest[root_manifest.index('[workspace]'):].replace('members = ["crates/nsealr-core", "apps/desktop-simulator"]','members = ["crates/nsealr-core"]\nexclude = ["apps/desktop-simulator"]')
    c.put('Cargo.toml',('# Portable no_std engine workspace. Host tools resolve independently.\n'+root_manifest).encode())
    host_manifest=(target/'apps/desktop-simulator/Cargo.toml').read_text()+'\n[workspace]\nresolver = "2"\nmembers = ["."]\n\n[profile.release]\ncodegen-units = 1\n'
    c.put('apps/desktop-simulator/Cargo.toml',host_manifest.encode())
    toolchain=(target/'rust-toolchain.toml').read_text();toolchain=toolchain[toolchain.index('[toolchain]'):]
    c.put('rust-toolchain.toml',('# Embedded engine compiler and actual RISC-V build target.\n'+toolchain).encode())
    host_toolchain=toolchain.replace('targets = ["riscv32imafc-unknown-none-elf"]\n','')
    c.put('apps/desktop-simulator/rust-toolchain.toml',('# Independently pinned host vector replay toolchain.\n'+host_toolchain).encode())
    c.put('apps/desktop-simulator/.cargo/config.toml',b'[source.crates-io]\nreplace-with = "vendored-sources"\n[source.vendored-sources]\ndirectory = "../../vendor"\n')
    # Generate lockfiles in a protected metadata-only copy before declaring any
    # target mutation. The actual source is tested below, never this scratch.
    with tempfile.TemporaryDirectory(dir=output,prefix='lock-metadata-') as tmp:
        scratch=Path(tmp)
        for rel in ['Cargo.toml','crates/nsealr-core/Cargo.toml','crates/nsealr-core/src/lib.rs','apps/desktop-simulator/Cargo.toml','apps/desktop-simulator/src/lib.rs','apps/desktop-simulator/src/main.rs']:
            p=scratch/rel;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(c.updates[rel][0] if rel in c.updates else (target/rel).read_bytes())
        (scratch/'.cargo').mkdir();(scratch/'.cargo/config.toml').write_text('[source.crates-io]\nreplace-with="vendored-sources"\n[source.vendored-sources]\ndirectory='+json.dumps(str(target/'vendor'))+'\n')
        for manifest,lock in [('Cargo.toml','Cargo.lock'),('apps/desktop-simulator/Cargo.toml','apps/desktop-simulator/Cargo.lock')]:
            rec.run('generate-'+lock.replace('/','-'),['cargo','generate-lockfile','--offline','--manifest-path',manifest],scratch,env=environment)
            c.put(lock,(scratch/lock).read_bytes())
    path='Makefile';text=(target/path).read_text();text=text[text.index('.PHONY:'):]
    text=text.replace('RUST_COVERAGE_JSON := build/rust-coverage.json','RUST_COVERAGE_JSON := build/rust-core-coverage.json\nHOST_COVERAGE_JSON := build/rust-host-coverage.json\nHOST_MANIFEST := apps/desktop-simulator/Cargo.toml')
    text=text.replace('\tcargo fmt --all --check','\tcargo fmt --all --check\n\tcargo fmt --manifest-path $(HOST_MANIFEST) --all --check')
    text=text.replace('\tcargo clippy --all-targets --all-features -- -D warnings -D dead_code','\tcargo clippy --all-targets --all-features -- -D warnings -D dead_code\n\tcargo clippy --manifest-path $(HOST_MANIFEST) --all-targets --all-features -- -D warnings -D dead_code')
    text=text.replace('\tcargo deny check','\tcargo deny check\n\tcargo deny --manifest-path $(HOST_MANIFEST) check --config deny.toml')
    text=text.replace('\tcargo test -p desktop-simulator','\tcargo test --manifest-path $(HOST_MANIFEST) --locked --offline')
    text=text.replace('\tpython3 ci/check_coverage_ratchet.py $(RUST_COVERAGE_JSON) ci/ratchet.json','\tcargo llvm-cov --manifest-path $(HOST_MANIFEST) --workspace --all-features --summary-only --json --output-path $(HOST_COVERAGE_JSON)\n\tpython3 ci/check_coverage_ratchet.py $(RUST_COVERAGE_JSON) ci/ratchet.json $(HOST_COVERAGE_JSON)')
    c.put(path,('# nSealr integration gates; embedded and host Cargo graphs remain separate.\n'+text).encode())
    path='ci/check_coverage_ratchet.py';text=(target/path).read_text()
    text=text.replace('def workspace_packages()','def workspace_packages(manifest="Cargo.toml")')
    text=text.replace('["cargo", "metadata", "--no-deps", "--format-version", "1"]','["cargo", "metadata", "--no-deps", "--format-version", "1", "--manifest-path", manifest]')
    text=text.replace('for pkg in meta["packages"]','for pkg in meta["packages"] if pkg["id"] in meta["workspace_members"]')
    text=text.replace('if len(argv) != 3:','if len(argv) != 4:').replace('<ratchet-json>", file=sys.stderr','<ratchet-json> <host-coverage-json>", file=sys.stderr')
    text=text.replace('roots = workspace_packages()','core_roots = workspace_packages()\n    host_roots = workspace_packages("apps/desktop-simulator/Cargo.toml")\n    roots = {**core_roots, **host_roots}')
    text=text.replace('measured = measured_line_coverage(cov_json, roots)','measured = {**measured_line_coverage(cov_json, core_roots),\n                **measured_line_coverage(Path(argv[3]), host_roots)}')
    # A missing measurement is a failed gate, never vacuous 100% coverage.
    text=text.replace('100.0 if total[name] == 0','0.0 if total[name] == 0')
    c.put(path,text.encode())
    path='ci/repro_build.sh';text=(target/path).read_text()
    text=text.replace('-p desktop-simulator --target-dir "$td"','--manifest-path apps/desktop-simulator/Cargo.toml --target-dir "$td/host"')
    text=text.replace('-p nsealr-core --target "$TRIPLE" --target-dir "$td"','-p nsealr-core --target "$TRIPLE" --target-dir "$td/core"')
    text=text.replace('DS_REL="release/desktop-simulator"','DS_REL="host/release/desktop-simulator"').replace('RLIB_REL="${TRIPLE}/release/libnsealr_core.rlib"','RLIB_REL="core/${TRIPLE}/release/libnsealr_core.rlib"')
    text=text.replace("rsync -a --exclude='/target' --exclude='/.git'", "rsync -a --exclude='target/' --exclude='node_modules/' --exclude='.venv/' --exclude='build/' --exclude='dist/' --exclude='/.git'")
    c.put(path,text.encode())
    return c.apply(output/'transformation','Separate embedded and host Rust workspaces with independent locks and unchanged acceptance floors')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output,json.loads(a.environment.read_bytes())))
