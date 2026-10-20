"""Exercise the actual admitted lint recipe using valid/invalid disposable sources."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[6]
RECIPE = ROOT / "protocols/contracts/v1/Makefile"
results = []
with tempfile.TemporaryDirectory(prefix="t01-compileall-") as temporary:
    base = Path(temporary)
    for name, source, expected in (("valid", "value = 1\n", 0), ("invalid", "def invalid(:\n", 1)):
        checkout = base / name
        cache_parent = base / (name + "-cache")
        cache_parent.mkdir()
        (checkout / "scripts").mkdir(parents=True)
        (checkout / "tests").mkdir()
        (checkout / "Makefile").write_bytes(RECIPE.read_bytes())
        (checkout / "scripts/example.py").write_text(source)
        (checkout / "tests/example.py").write_text("value = 2\n")
        before = {str(path.relative_to(checkout)): hashlib.sha256(path.read_bytes()).hexdigest() for path in checkout.rglob("*") if path.is_file()}
        recipe = subprocess.check_output(["make", "--no-print-directory", "-n", "lint"], cwd=checkout, text=True)
        env = dict(os.environ, TMPDIR=str(cache_parent))
        outcome = subprocess.run(["/bin/sh", "-c", recipe], cwd=checkout, env=env, capture_output=True, text=True)
        after = {str(path.relative_to(checkout)): hashlib.sha256(path.read_bytes()).hexdigest() for path in checkout.rglob("*") if path.is_file()}
        assert outcome.returncode == expected, (name, outcome.returncode, outcome.stdout, outcome.stderr)
        assert before == after, (name, "source mutation")
        assert not list(cache_parent.iterdir()), (name, "cache not cleaned")
        results.append({"case": name, "compiler_recipe_exit": outcome.returncode, "source_unchanged": True, "external_cache_cleaned": True, "stdout": outcome.stdout, "stderr": outcome.stderr})
print(json.dumps({"makefile_sha256": hashlib.sha256(RECIPE.read_bytes()).hexdigest(), "controls": results}, indent=2))
