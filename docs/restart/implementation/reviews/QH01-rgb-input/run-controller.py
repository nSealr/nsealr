"""Bind the unchanged RGB controller to this review's separately built ELF."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / "docs/restart/implementation/QH01/rgb-input/controller.py"
CONTEXT = json.loads((HERE / "binary-context.json").read_text())
BINARY = Path(CONTEXT["binary_path"])
EXPECTED_SOURCE = "548ddea7c7344956a8aaca86db7bfa280e9e525401b9d7ba47f2d2b7b4a7d0b2"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if digest(SOURCE) != EXPECTED_SOURCE:
    raise RuntimeError("candidate controller source mismatch")
if digest(BINARY) != CONTEXT["binary_sha256"]:
    raise RuntimeError("independent binary mismatch")
spec = importlib.util.spec_from_file_location("qh01_rgb_review_controller", SOURCE)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
# Only the experiment input path changes. main passes it explicitly to supervise.
controller.BINARY = BINARY
sys.argv = [str(SOURCE), "--out", str(HERE / "stable-6")]
result = controller.main()
if digest(BINARY) != CONTEXT["binary_sha256"] or digest(SOURCE) != EXPECTED_SOURCE:
    raise RuntimeError("input changed during campaign")
raise SystemExit(result)
