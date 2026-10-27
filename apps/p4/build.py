#!/usr/bin/env python3
"""Pinned Linux P4 public-fixture build; no device access or private lab imports."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

APP = Path(__file__).resolve().parent
REPO = APP.parents[1]
RECIPE = APP / "recipe"
PINS = json.loads((RECIPE / "pins.json").read_text())
TARGET = "riscv32imafc-unknown-none-elf"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2) + "\n")


def clean_env(work):
    # Deliberately do not inherit compiler/package-manager options or tool paths.
    env = {k: os.environ[k] for k in ("HOME", "USER") if k in os.environ}
    env.update(PATH="/usr/bin:/bin", LANG="C.UTF-8", LC_ALL="C.UTF-8",
               PYTHONNOUSERSITE="1", GIT_TERMINAL_PROMPT="0", CCACHE_DISABLE="1",
               XDG_CACHE_HOME=str(work / "cache"),
               TMPDIR=str(work / "tmp"), UV_PYTHON_DOWNLOADS="never",
               PYTHONPYCACHEPREFIX=str(work / "cache/pycache"))
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    return env


def run(work, label, argv, env, cwd=APP):
    folder = work / "logs" / (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + label)
    folder.mkdir(parents=True)
    record = dict(argv=list(map(str, argv)), cwd=str(cwd), environment=env,
                  source_head=subprocess.check_output(
                      ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
                  start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(folder / "command.json", record)
    print("START", label, folder, flush=True)
    start = time.monotonic()
    try:
        with (folder / "stdout.log").open("w") as out, (folder / "stderr.log").open("w") as err:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=err, timeout=1200)
        record["exit"] = result.returncode
    except subprocess.TimeoutExpired:
        record["exit"] = "TIMEOUT"
        raise
    finally:
        record["elapsed_seconds"] = time.monotonic() - start
        record["logs"] = {x: sha(folder / x) for x in ("stdout.log", "stderr.log")}
        write(folder / "result.json", record)
    print("END", label, record["exit"], record["elapsed_seconds"], flush=True)
    if result.returncode:
        print((folder / "stdout.log").read_text(errors="replace")[-4000:])
        print((folder / "stderr.log").read_text(errors="replace")[-4000:])
        raise subprocess.CalledProcessError(result.returncode, argv)


def obtain(item, work, caches):
    """Use an authenticated existing download or fetch exactly the pinned URL."""
    filename = item["url"].rsplit("/", 1)[-1]
    filename = urllib.parse.unquote(filename)
    destination = work / "downloads" / filename
    candidates = [Path(c) / filename for c in caches] + [destination]
    for candidate in candidates:
        if candidate.is_file() and sha(candidate) == item["sha256"]:
            return candidate.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with urllib.request.urlopen(item["url"], timeout=60) as source, temporary.open("wb") as out:
        shutil.copyfileobj(source, out)
    require(sha(temporary) == item["sha256"], "Download SHA256 mismatch: " + filename)
    temporary.replace(destination)
    return destination


def verify_sdk(work, sdk, env):
    """Authenticate the same SDK/checker/constraints before executing SDK Python."""
    sdk = Path(sdk).resolve()
    require(sha(RECIPE / "python-constraints.txt") == PINS["constraints_sha256"],
            "Admitted constraint body changed")
    for field, relative in (
            ("python_checker_sha256", "tools/check_python_dependencies.py"),
            ("idf_tools_sha256", "tools/idf_tools.py"),
            ("core_requirements_sha256", "tools/requirements/requirements.core.txt")):
        require(sha(sdk / relative) == PINS["sdk"][field],
                "Unpinned SDK dependency checker/input: " + relative)
    require(subprocess.check_output(["git", "-C", str(sdk), "rev-parse", "HEAD"],
        text=True).strip() == PINS["sdk"]["commit"], "SDK commit changed")
    require(not subprocess.check_output(["git", "-C", str(sdk), "status", "--porcelain",
        "--untracked-files=no"], text=True).strip(), "SDK tracked source changed")
    links = subprocess.check_output(["git", "-C", str(sdk), "submodule", "status", "--recursive"], text=True)
    require(links and all(line.startswith(" ") for line in links.splitlines()),
            "Missing or changed SDK submodule")
    # Validate submodule bodies too, rather than trusting checkout IDs alone.
    run(work, "sdk-submodule-clean", ["git", "-C", str(sdk), "submodule", "foreach",
        "--recursive", "git diff --quiet && git diff --cached --quiet"], env)
    write(work / "sdk-gitlinks.json", dict(commit=PINS["sdk"]["commit"], gitlinks=links.splitlines()))


def bootstrap(args, work):
    require(args.base_python and args.uv and args.sdk, "python stage requires --base-python, --uv and --sdk")
    require(sha(args.uv) == PINS["uv"]["binary_sha256"], "Unpinned uv binary")
    env = clean_env(work)
    base = Path(args.base_python).resolve()
    require(sha(base) == PINS["python"]["binary_sha256"], "Unpinned base Python binary")
    version = subprocess.check_output([str(base), "--version"], env=env, text=True).strip()
    require(version == "Python 3.12.15", "This wheel closure requires Python3.12.15")
    packages = work / "packages"
    packages.mkdir(exist_ok=True)
    for item in json.loads((RECIPE / "python-sources.json").read_text()):
        source = obtain(item, work, args.download_cache)
        target = packages / source.name
        if target.is_symlink():
            require(target.resolve() == source, "Different package-cache binding")
        else:
            require(not target.exists(), "Refuse replacing a package-cache entry")
            target.symlink_to(source)
    python_env = Path(args.python_env).resolve() if args.python_env else work / "python"
    require(not python_env.exists(), "python stage requires an absent, fresh environment")
    uv = [str(Path(args.uv).resolve()), "--offline", "--no-config",
          "--cache-dir", str(work / "cache/uv")]
    run(work, "python-venv", uv + ["venv", "--no-project", "--no-python-downloads",
        "--python", str(base), str(python_env)], env)
    common = ["--python", str(python_env / "bin/python"), "--no-index",
              "--find-links", str(packages), "--require-hashes", "--no-build-isolation"]
    run(work, "python-bootstrap", uv + ["pip", "install", "--no-deps"] + common +
        ["-r", str(RECIPE / "python-bootstrap.lock")], env)
    # esptool is rebuilt from the authenticated publisher sdist. The old local
    # wheel hash is historical only. No source build other than esptool is selected.
    run(work, "python-sync", uv + ["pip", "sync"] + common +
        [str(RECIPE / "python-requirements.lock")], env)
    run(work, "python-compatibility", uv + ["pip", "check",
        "--python", str(python_env / "bin/python")], env)
    # uv hash-file parsing does not accept upstream range constraints. The
    # unchanged SDK checker enforces their full body immediately after sync.
    verify_sdk(work, args.sdk, env)
    run(work, "python-sdk-constraints", [str(python_env / "bin/python"),
        str(Path(args.sdk).resolve() / "tools/check_python_dependencies.py"),
        "-r", str(Path(args.sdk).resolve() / "tools/requirements/requirements.core.txt"),
        "-c", str(RECIPE / "python-constraints.txt")], env)
    (python_env / "idf_version.txt").write_text("6.0\n")
    write(work / "python-environment.json", dict(python_env=str(python_env), base=str(base),
        base_sha256=sha(base), source_lock_sha256=sha(RECIPE / "python-requirements.lock"),
        note="esptool source-derived; historical wheel bit identity is not required"))


def environment(args, work):
    require(all((args.sdk, args.idf_tools, args.rust_toolchain)),
            "Select --sdk, --idf-tools and --rust-toolchain explicitly")
    sdk, tools, rust = map(lambda x: Path(x).resolve(),
                           (args.sdk, args.idf_tools, args.rust_toolchain))
    pyenv = Path(args.python_env).resolve() if args.python_env else work / "python"
    require(pyenv.is_dir(), "Run python stage or select a pinned --python-env")
    gcc = tools / "tools/riscv32-esp-elf/esp-15.2.0_20251204/riscv32-esp-elf/bin"
    cmake = tools / "tools/cmake/4.0.3/bin"
    ninja = tools / "tools/ninja/1.12.1"
    binaries = dict(gcc=gcc / "riscv32-esp-elf-gcc", cmake=cmake / "cmake",
                    ninja=ninja / "ninja", rustc=rust / "bin/rustc", cargo=rust / "bin/cargo")
    for name, path in binaries.items():
        require(sha(path) == PINS["tool_binaries"][name], "Unpinned " + name + " binary")
    own_tools = work / "idf-tools"
    own_tools.mkdir(exist_ok=True)
    shutil.copyfile(RECIPE / "python-constraints.txt", own_tools / "espidf.constraints.v6.0.txt")
    env = clean_env(work)
    env.update(IDF_PATH=str(sdk), IDF_TOOLS_PATH=str(own_tools),
        IDF_PYTHON_ENV_PATH=str(pyenv), VIRTUAL_ENV=str(pyenv),
        PYTHON=str(pyenv / "bin/python"), ESP_IDF_VERSION="6.0",
        ESP_ROM_ELF_DIR=str(tools / "tools/esp-rom-elfs/20241011"),
        IDF_COMPONENT_CACHE_PATH=str(Path(args.component_cache).resolve()
                                    if args.component_cache else work / "cache/components"),
        P4_COMPONENT_ROOT=str(work / "components"),
        CARGO_HOME=str(work / "cargo-home"), CARGO_TARGET_DIR=str(work / "rust-target"),
        RUSTC=str(binaries["rustc"]), RUSTDOC=str(rust / "bin/rustdoc"),
        RUSTFLAGS="-C force-frame-pointers=yes",
        PATH=":".join(map(str, (pyenv / "bin", gcc, cmake, ninja, rust / "bin",
                                sdk / "tools", Path("/usr/bin"), Path("/bin")))))
    return env, binaries


def verify_lock(path):
    import yaml
    expected = yaml.safe_load((APP / "dependencies.lock").read_text())
    actual = yaml.safe_load(Path(path).read_text())
    require(set(expected["dependencies"]) == set(actual["dependencies"]), "Component set changed")
    for name, pin in expected["dependencies"].items():
        value = actual["dependencies"][name]
        require(value["version"] == pin["version"], "Component version changed: " + name)
        require(value.get("component_hash") == pin.get("component_hash"),
                "Component hash changed: " + name)


def prepare(args, work, env):
    import yaml
    from idf_component_tools.hash_tools.validate import validate_hash_eq_hashdir
    from idf_component_tools.manifest.models import SolvedComponent
    from idf_component_tools.sources.web_service import WebServiceSource
    sdk = Path(env["IDF_PATH"])
    verify_sdk(work, sdk, env)
    want = {}
    for line in (RECIPE / "python-requirements.lock").read_text().splitlines():
        name, version = line.split(" --hash=", 1)[0].split("==")
        want[re.sub(r"[-_.]+", "-", name).lower()] = version
    actual = {re.sub(r"[-_.]+", "-", x.metadata["Name"]).lower(): x.version
              for x in importlib.metadata.distributions()}
    require(actual == want, "Python package/version closure differs from the pinned57")
    require(sys.version_info[:3] == (3, 12, 15), "Use the selected pinned Python to run this recipe")
    run(work, "idf-python-dependencies", [env["PYTHON"], str(sdk / "tools/idf_tools.py"),
        "check-python-dependencies"], env)
    lock = yaml.safe_load((APP / "dependencies.lock").read_text())
    adapter = PINS["adapter"]
    adapter_dir = work / "components/esp_lvgl_adapter"
    # The adapter is an explicit local override of the identical admitted patch.
    if not adapter_dir.exists():
        adapter_dir.parent.mkdir(parents=True, exist_ok=True)
        source = WebServiceSource(registry_url="https://components.espressif.com/")
        component = SolvedComponent(name=adapter["name"], version=adapter["version"],
            source=source, component_hash=adapter["component_hash"])
        source.download(component, str(adapter_dir))
        validate_hash_eq_hashdir(adapter_dir, adapter["component_hash"])
        require(sha(adapter_dir / adapter["patched_file"]) == adapter["before_sha256"],
                "Adapter patch input changed")
        run(work, "adapter-public-headers", ["patch", "--batch", "--fuzz=0", "-p1",
            "-i", str(RECIPE / adapter["patch"])], env, cwd=adapter_dir)
        # Do not present the original registry marker as patched-source integrity.
        for marker in (".component_hash", "CHECKSUMS.json"):
            (adapter_dir / marker).unlink(missing_ok=True)
    require(sha(adapter_dir / adapter["patched_file"]) == adapter["after_sha256"],
            "Patched adapter changed")
    validate_hash_eq_hashdir(adapter_dir, adapter["patched_component_hash"])
    # Copy the lock to the selected build workspace. IDF may update its manifest
    # binding/local absolute path, but every version/hash is checked after configure.
    lock["dependencies"]["espressif/esp_lvgl_adapter"]["source"]["path"] = str(adapter_dir)
    (work / "dependencies.lock").write_text(yaml.safe_dump(lock, sort_keys=False))
    managed = APP / "managed_components"
    target = work / "managed_components"
    target.mkdir(exist_ok=True)
    if managed.is_symlink():
        require(managed.resolve() == target, "Remove the old managed_components symlink explicitly first")
    else:
        require(not managed.exists(), "Use an absent managed_components path; never overwrite a store")
        managed.symlink_to(target, target_is_directory=True)
    write(work / "prepared.json", dict(work=str(work), adapter=adapter,
        versioned_lock_sha256=sha(APP / "dependencies.lock"),
        sdkconfig_base_sha256=sha(RECIPE / "sdkconfig.base")))


def configure(args, work, env, bins):
    require((work / "prepared.json").exists(), "Run prepare first")
    require(sha(RECIPE / "sdkconfig.base") == PINS["baseline_sha256"], "Baseline config changed")
    overrides = dict(line.split("=", 1) for line in (APP / "sdkconfig.public").read_text().splitlines()
                     if line.startswith("CONFIG_"))
    lines = []
    for line in (RECIPE / "sdkconfig.base").read_text().splitlines():
        key = line.removeprefix("# ").split("=", 1)[0].split(" ", 1)[0]
        if key == "CONFIG_TASK_WDT_PANIC":
            continue
        if key in overrides:
            value = overrides.pop(key)
            lines.append("# " + key + " is not set" if value == "n" else key + "=" + value)
        else:
            lines.append(line)
    for key, value in overrides.items():
        lines.append("# " + key + " is not set" if value == "n" else key + "=" + value)
    (work / "sdkconfig").write_text("\n".join(lines) + "\n")
    library = work / "rust-target" / TARGET / "release/libnsealr_p4_optical.a"
    run(work, "configure", [str(bins["cmake"]), "-S", str(APP), "-B", str(work / "build"),
        "-G", "Ninja", "-DIDF_TARGET=esp32p4", "-DSDKCONFIG=" + str(work / "sdkconfig"),
        "-DPYTHON=" + env["PYTHON"], "-DNSEALR_P4_LOCK_FILE=" + str(work / "dependencies.lock"),
        "-DRUST_LIBRARY=" + str(library), "-DP4_WDT_PROBE_MODE=" + str(args.probe_mode),
        "-DP4_ENTROPY_FIXED_UNAVAILABLE=" + str(int(args.entropy_mode == "fixed-unavailable"))], env)
    verify_lock(work / "dependencies.lock")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["python", "prepare", "rust", "configure", "app", "all"])
    parser.add_argument("--work-dir", type=Path, required=True, help="Own generated cache/output root")
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--idf-tools", type=Path, help="Exact installed IDF tools root (tools/...)")
    parser.add_argument("--rust-toolchain", type=Path, help="Exact1.95.0 toolchain directory (bin/,lib/)")
    parser.add_argument("--python-env", type=Path, help="Defaults to WORK/python, never a lab path")
    parser.add_argument("--base-python", type=Path)
    parser.add_argument("--uv", type=Path)
    parser.add_argument("--download-cache", action="append", default=[], type=Path)
    parser.add_argument("--component-cache", type=Path)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--probe-mode", choices=["normal", "busy-cpu", "blocking-wait", "c6-reset"], default="normal")
    parser.add_argument("--host-proof", action="store_true")
    parser.add_argument("--entropy-mode", choices=["normal", "fixed-unavailable"], default="normal")
    args = parser.parse_args()
    args.probe_mode = {"normal": 0, "busy-cpu": 1, "blocking-wait": 2, "c6-reset": 3}[args.probe_mode]
    work = args.work_dir.resolve()
    require(not work.is_relative_to(APP), "Keep build/cache output outside apps/p4")
    require(1 <= args.jobs <= 8, "This recipe admits1..8 build jobs")
    require(not (args.probe_mode and args.entropy_mode == "fixed-unavailable"),
            "Unavailable requires normal guard mode")
    work.mkdir(parents=True, exist_ok=True)
    if args.stage == "python":
        bootstrap(args, work)
        return
    env, bins = environment(args, work)
    # Manager settings read the process environment when imported in prepare.
    os.environ.clear()
    os.environ.update(env)
    stages = ["prepare", "rust", "configure", "app"] if args.stage == "all" else [args.stage]
    for stage in stages:
        if stage == "prepare":
            prepare(args, work, env)
        elif stage == "rust":
            argv = [str(bins["cargo"]), "build", "--release", "--offline", "--locked", "--target", TARGET]
            if args.host_proof:
                argv += ["--target", "x86_64-unknown-linux-gnu"]
            run(work, "rust", argv, env, cwd=APP / "rust")
        elif stage == "configure":
            configure(args, work, env, bins)
        else:
            cache = (work / "build/CMakeCache.txt").read_text()
            require("P4_WDT_PROBE_MODE:STRING=" + str(args.probe_mode) + "\n" in cache,
                    "Configure the requested probe mode first")
            require("P4_ENTROPY_FIXED_UNAVAILABLE:STRING=" +
                    str(int(args.entropy_mode == "fixed-unavailable")) + "\n" in cache,
                    "Configure the requested entropy mode first")
            verify_lock(work / "dependencies.lock")
            run(work, "app", [str(bins["ninja"]), "-C", str(work / "build"),
                "-j", str(args.jobs), "all"], env)


if __name__ == "__main__":
    main()
