"""Pre-child input/admission checks only; no O/W/kernel success claim."""
import gc
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import weakref

from nsealr_vault.qr_owner_adapter import RgbOwnerRuntime


class OwnerAdapterPreflightTests(unittest.TestCase):
    def config(self):
        path = str(Path(sys.executable).resolve())
        return path, hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def test_untrusted_worker_configuration_has_no_child_effect(self):
        runtime = RgbOwnerRuntime()
        path, digest = self.config()
        with patch("nsealr_vault.qr_owner_adapter.subprocess.Popen") as spawn:
            for candidate, value in (("relative", digest), (path, "A" * 64), (path, "0" * 64)):
                with self.assertRaises(ValueError):
                    runtime.reserve(candidate, value)
            spawn.assert_not_called()
        self.assertIsNone(runtime.operation)

    def test_invalid_rgb_is_refused_before_P_or_child(self):
        runtime = RgbOwnerRuntime()
        op = runtime.reserve(*self.config())
        try:
            with patch("nsealr_vault.qr_owner_adapter.subprocess.Popen") as spawn:
                for value in (b"", b"x" * 172799, b"x" * 172801, bytearray(172800)):
                    with self.assertRaisesRegex(ValueError, "exact packed RGB888"):
                        op.start(value)
                spawn.assert_not_called()
            self.assertIsNone(op.observation()["owner_pid"])
            self.assertEqual(op.observation()["commands"], [])
        finally:
            op.close()

    def test_runtime_strongly_retains_reservation_and_blocks_replacement(self):
        runtime = RgbOwnerRuntime()
        op = runtime.reserve(*self.config())
        reference = weakref.ref(op)
        del op
        gc.collect()
        self.assertIs(reference(), runtime.operation)
        with self.assertRaisesRegex(ValueError, "prior operation"):
            runtime.reserve(*self.config())
        runtime.operation.close()  # Explicit pre-child close, not a destructor.


if __name__ == "__main__":
    unittest.main()
