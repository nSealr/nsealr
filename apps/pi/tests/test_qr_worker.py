"""Focused real-kernel checks for the finite owner, not its host gate matrix."""
import os
import sys
import unittest
from unittest.mock import patch

from nsealr_vault.qr_worker import CAP, CLEANUP_NS, Owner, RAW, sha


class WorkerOwnerTests(unittest.TestCase):
    def owner(self):
        owner = Owner(sys.executable, sha(sys.executable))
        self.addCleanup(owner.selector.close)
        return owner

    def pipe(self, owner):
        read, write = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        owner.fds.update((read, write))
        self.addCleanup(lambda: [owner.close(fd) for fd in list(owner.fds)])
        return read, write

    def test_observed_status_is_real_wait4_exit_not_default_zero(self):
        owner = self.owner()
        pid = os.posix_spawn(sys.executable, [sys.executable, "-c", "raise SystemExit(23)"], {},
                             file_actions=[(os.POSIX_SPAWN_OPEN, 0, "/dev/null", os.O_RDONLY, 0),
                                           (os.POSIX_SPAWN_OPEN, 1, "/dev/null", os.O_WRONLY, 0),
                                           (os.POSIX_SPAWN_OPEN, 2, "/dev/null", os.O_WRONLY, 0)])
        owner.pid = pid
        # WNOWAIT observes actual terminal readiness without stealing its status.
        os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
        owner.poll_wait()
        self.assertEqual(owner.wait, {"raw_status": 23 << 8, "exit_code": 23, "collector_pid": os.getpid()})
        self.assertEqual(owner.reason, "worker_error")
        with self.assertRaises(ChildProcessError):
            os.wait4(pid, os.WNOHANG)

    def test_actual_stolen_status_is_unknown_never_zero(self):
        owner = self.owner()
        pid = os.posix_spawn(sys.executable, [sys.executable, "-c", "raise SystemExit(17)"], {})
        owner.pid = pid
        actual = os.wait4(pid, 0)
        self.assertEqual(actual[1], 17 << 8)
        owner.poll_wait()
        self.assertTrue(owner.lost)
        self.assertIsNone(owner.wait)
        self.assertFalse(owner.known())
        self.assertEqual(owner.reason, "cleanup_unknown")
        # Child is already truly collected by this test's explicit other waiter.
        # No quarantine process is killed, no claim of recovery from unknown wait.

    def test_retention_cap_overflow_and_true_eof_are_distinct(self):
        owner = self.owner()
        read, write = self.pipe(owner)
        os.write(write, b"x" * (CAP + 1))
        owner.worker_io(read, "stdout")
        self.assertEqual(owner.totals["stdout"], CAP + 1)
        self.assertEqual(len(owner.streams["stdout"]), CAP)
        self.assertEqual(owner.reason, "worker_error")
        self.assertNotIn("stdout", owner.eof)
        owner.close(write)
        owner.worker_io(read, "stdout")
        self.assertIn("stdout", owner.eof)
        self.assertNotIn(read, owner.fds)

    def test_input_overrun_is_rejected_before_extra_byte_is_retained(self):
        owner = self.owner()
        read, write = self.pipe(owner)
        owner.sequence = "P"
        owner.image = bytearray(b"x" * RAW)
        owner.input_count = RAW
        os.write(write, b"z")
        actual_read = os.read
        # Redirect only fixed stdin0 to this real pipe, not a fabricated read result.
        with patch("nsealr_vault.qr_worker.os.read", side_effect=lambda fd, n: actual_read(read if fd == 0 else fd, n)):
            owner.ingress()
        self.assertEqual(owner.input_count, RAW + 1)
        self.assertEqual(len(owner.image), RAW)
        self.assertIsNone(owner.pid)
        self.assertEqual(owner.reason, "input_invalid")

    def test_cleanup_deadline_is_shared_not_renewed(self):
        owner = self.owner()
        owner.invalidate("cancelled")
        first = owner.invalidated
        owner.invalidate("control_lost")
        self.assertEqual(owner.reason, "cancelled")
        self.assertEqual(owner.invalidated, first)
        self.assertEqual(owner.cleanup, first + CLEANUP_NS)


if __name__ == "__main__":
    unittest.main()
