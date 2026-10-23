"""Reviewer-local executable binding; unchanged author controller and five cases."""
import hashlib
import importlib.util
from pathlib import Path
import sys

source, binary, binary_sha, output = sys.argv[1:]
source, binary, output = Path(source).resolve(), Path(binary).resolve(), Path(output).resolve()
assert hashlib.sha256(source.read_bytes()).hexdigest() == "81a1b8c2a607f6aa918a62af98c1d6a2e9ec110dce6a4f5c076b02255b1cc142"
assert hashlib.sha256(binary.read_bytes()).hexdigest() == binary_sha
spec = importlib.util.spec_from_file_location("qh01_reviewed_rust_controller", source)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
controller.BINARY = binary
sys.argv = [str(source), "--out", str(output)]
exit_code = controller.main()
assert hashlib.sha256(binary.read_bytes()).hexdigest() == binary_sha
raise SystemExit(exit_code)
