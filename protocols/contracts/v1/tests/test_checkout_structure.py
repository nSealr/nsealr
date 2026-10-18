"""Exercise the real structure checker from a renamed disposable checkout."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CheckoutStructureTests(unittest.TestCase):
    def test_identity_survives_checkout_rename_and_retains_license_and_directory_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "arbitrary-worktree"
            (root / "scripts").mkdir(parents=True)
            source = Path(__file__).resolve().parents[1] / "scripts" / "verify_repo.py"
            shutil.copyfile(source, root / "scripts" / "verify_repo.py")
            for name in ("README.md", "LICENSE", "Makefile", ".pre-commit-config.yaml",
                         "docs/architecture.md", "docs/testing.md", "docs/roadmap.md",
                         "docs/audit-checklist.md", ".github/workflows/ci.yml"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("## License\n" if name == "README.md" else "fixture\n")
            for name in ("protocols", "schemas", "vectors", "examples", "docs", "scripts"):
                (root / name).mkdir(exist_ok=True)
            def run():
                return subprocess.run([sys.executable, str(root / "scripts" / "verify_repo.py")],
                                      capture_output=True, text=True)
            (root / "LICENSE").write_text("Creative Commons CC0 1.0 Universal\n")
            self.assertEqual(run().returncode, 0)
            (root / "LICENSE").write_text("MIT License\n")
            bad_license = run()
            self.assertNotEqual(bad_license.returncode, 0)
            self.assertIn("LICENSE does not contain expected marker: Creative Commons CC0", bad_license.stdout)
            (root / "LICENSE").write_text("Creative Commons CC0 1.0 Universal\n")
            (root / "vectors").rmdir()
            missing_directory = run()
            self.assertNotEqual(missing_directory.returncode, 0)
            self.assertIn("missing required directory: vectors", missing_directory.stdout)
