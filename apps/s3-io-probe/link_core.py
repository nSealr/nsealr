# SPDX-License-Identifier: MIT
# Build/link only: no Rust compiler installation or source fetching here.
import os
from pathlib import Path
Import("env")
folder = Path(os.environ["NSEALR_S3_CORE_LIB_DIR"]).resolve()
archive = folder / "libnsealr_s3_abi.a"
if not archive.is_file():
    raise RuntimeError("Build the pinned public Rust ABI archive before PlatformIO")
env.Append(LIBPATH=[str(folder)], LIBS=["nsealr_s3_abi"])
