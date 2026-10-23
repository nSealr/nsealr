"""Three-case host ownership experiment; never a production coordinator."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import select
import signal
import socket
import sys
import time
import traceback

ROOT = Path('/home/tux/nsealr/.restart-tools/goal/qh01-rgb-input-review')
QR = ROOT / 'docs/restart/implementation/QH01/rgb-input'
BINARY = Path('/home/tux/nsealr/.restart-tools/goal/qh01-linux-worker-experiment/docs/restart/implementation/QH01/rgb-input/.runtime/target/release/nsealr-qh01-rust-qr-worker')
PYTHON = Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3')
ELF_HASH = '1a4af26b3c738807fb0f1a2e6fb7fcca9d480057642150357ad3c5bf774e6542'
INPUT_HASH = '1b56f2926382c7da914a877db899494414988d311c65ff459e2f78a8ab4f0216'
OUTPUT_HASH = 'dae39f12a7744d3c82e2d3e1050b02948a3b72612e5835c237054dabc3d8f3cf'
PINS = {
    QR / 'controller.py': '548ddea7c7344956a8aaca86db7bfa280e9e525401b9d7ba47f2d2b7b4a7d0b2',
    QR / 'src/main.rs': 'e60b3bc2baec2eded7ee474e101cfa8debd1a88be76d6d7cffce31b4e3e1dcf1',
    QR / 'Cargo.lock': 'eb00e1c6ebaa1e241e64574a62902a7ede995c7582cf11bc9d4620bfb4baf243',
    QR / 'Cargo.toml': '0f0fd52a1c47054f3b092f84585fe585908ad4aef7e401b59f27aff1b2c96de3',
    QR / 'parameters.json': '373a6ffe05a2a6175467deb686490cefefca9d953cc097a9d999f5103c482e98',
    QR / 'expectations.json': 'b6ba5bcd11bd36b0686315b295abf2437bf47a05bfac0cee24dae8da2e95bf1d',
    QR.parent / 'linux-worker-experiment/experiment.py': '97fa6da85a1f83c5535050f6c77c588800a069a26ed9a7cd7470f616352a76eb',
    BINARY: ELF_HASH,
    PYTHON.resolve(): 'eaaa308032c4aa063df5880c4c293cd458b4629d503fbc2c03ec163d71f7f790',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def identity(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, state=fields[0], ppid=int(fields[1]), pgid=int(fields[2]),
                sid=int(fields[3]), start_ticks=int(fields[19]))


def peek():
    # None is NOT empty: only ECHILD establishes no waitable/live children.
    try:
        event = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        return ('event', event.si_pid) if event else ('live', None)
    except ChildProcessError:
        return 'empty', None


def packet(sock, value):
    data = json.dumps(value).encode()
    if len(data) > 4096:
        raise RuntimeError('control message bound')
    if sock.send(data) != len(data):
        raise RuntimeError('partial control message')


def receive(sock, allow_eof=False):
    data, _anc, flags, _addr = sock.recvmsg(4096)
    if not data and allow_eof:
        return None
    if flags & socket.MSG_TRUNC or not data:
        raise RuntimeError('control message truncated/closed')
    return json.loads(data)


def preflight():
    if sys.version_info[:2] != (3, 12) or Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError('pinned R00 Python required')
    hashes = {str(path): digest(path) for path in PINS}
    if any(hashes[str(path)] != expected for path, expected in PINS.items()):
        raise RuntimeError('frozen source/tool/ELF mismatch')
    spec = importlib.util.spec_from_file_location('frozen_rgb_controller', QR / 'controller.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = [c for c in module.CASES if c['image_sha256'] == INPUT_HASH and c['expected_sha256'] == OUTPUT_HASH]
    if len(cases) != 1:
        raise RuntimeError('ambiguous original fixture')
    case = cases[0]
    for key, size in [('image', 172800), ('expected', 198)]:
        path = ROOT / case[key + '_path']
        if len(path.read_bytes()) != size or digest(path) != case[key + '_sha256']:
            raise RuntimeError('fixture byte identity')
        hashes[str(path)] = digest(path)
    if len(list(Path('/proc/self/task').iterdir())) != 1 or peek()[0] != 'empty':
        raise RuntimeError('dedicated single-threaded observer without children required')
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise RuntimeError('default SIGCHLD required')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    libc.prctl.restype = ctypes.c_int
    value = ctypes.c_int()
    if libc.prctl(37, ctypes.addressof(value), 0, 0, 0) != 0 or value.value != 0:
        raise RuntimeError('unexpected preexisting subreaper/error')
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
    if libc.prctl(37, ctypes.addressof(value), 0, 0, 0) != 0 or value.value != 1:
        raise RuntimeError('subreaper readback failed')
    # No children exist if any precondition above fails.
    return module, case, hashes


def coordinator(module, case, mode, sock, out, deadline):
    """Trusted test fixture C; the imported controller/worker bytes are unchanged."""
    journal = out / 'coordinator-events.jsonl'
    def log(event):
        with journal.open('a') as stream:
            stream.write(json.dumps(event) + '\n')
    def trace(frame, event, _arg):
        if (mode == 'early-exit' and event == 'line' and
                frame.f_code is module.supervise.__code__ and frame.f_lineno == 108):
            record = frame.f_locals['record']
            # Disk receipt is inspected AFTER kernel adoption, never used to find W.
            write(out / 'early-exit.json', dict(kind='early-exit-before-late-handoff',
                  pid=frame.f_locals['pid'], fault_at=time.monotonic(),
                  control_bytes=record['control_bytes'], image_bytes=record['image_bytes']))
            os._exit(73)  # Real C exit; no supervisor finally, no W PID message to O.
        if event == 'line' and frame.f_code is module.supervise.__code__ and frame.f_lineno == 160:
            record = frame.f_locals['record']
            message = dict(kind='policy', pid=frame.f_locals['pid'], policy=record['policy'],
                           control_bytes=record['control_bytes'], image_bytes=record['image_bytes'])
            log(message)
            packet(sock, message)
            sock.settimeout(max(0.001, deadline - time.monotonic()))
            instruction = receive(sock)
            if mode == 'held-kill' and instruction == {'kind': 'collect-stop'}:
                while time.monotonic() < deadline:
                    got, status, usage = os.wait4(message['pid'], os.WNOHANG | os.WUNTRACED)
                    if got:
                        if got != message['pid'] or not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGSTOP:
                            raise RuntimeError('actual worker SIGSTOP status missing')
                        stopped = dict(kind='stopped', pid=got, raw_status=status,
                                       stop_signal=os.WSTOPSIG(status),
                                       user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
                                       control_bytes=record['control_bytes'], image_bytes=record['image_bytes'])
                        log(stopped)
                        packet(sock, stopped)
                        # C is terminated here by O; no G/image ever sent in this mode.
                        receive(sock)
                        raise RuntimeError('held coordinator unexpectedly resumed')
                    time.sleep(0.002)
                raise RuntimeError('stop observation exceeded activation deadline')
            if mode != 'normal' or instruction != {'kind': 'continue'}:
                raise RuntimeError('unexpected test instruction')
        return trace
    try:
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        if receive(sock) != {'kind': 'start'}:
            raise RuntimeError('missing initial owned-C handshake')
        sys.settrace(trace)
        try:
            record = module.supervise(case, module.base.Owner(), out, binary=BINARY)
        finally:
            sys.settrace(None)
        packet(sock, {'kind': 'complete', 'passed': record['passed']})
        log({'kind': 'complete', 'passed': record['passed']})
        sock.close()
        os._exit(0 if record['passed'] else 1)
    except BaseException:
        sys.settrace(None)
        (out / 'coordinator-error.txt').write_text(traceback.format_exc())
        sock.close()
        os._exit(74)


class Observer:
    def __init__(self, module, out):
        self.module, self.out = module, out
        self.owned = {}
        self.started = time.monotonic()
        self.deadline = self.started + module.P['wall_eligibility_deadline']
        self.cleanup_deadline = None
        self.quarantined = False
        self.cpid = None
        self.wpid = None
        self.events = []
        self.reservation = module.base.Owner()
        if not self.reservation.acquire():
            raise RuntimeError('observer reservation unavailable')

    def event(self, kind, **details):
        item = dict(kind=kind, elapsed=time.monotonic() - self.started, **details)
        self.events.append(item)
        with (self.out / 'observer-events.jsonl').open('a') as stream:
            stream.write(json.dumps(item) + '\n')

    def adopt_handle(self, pid, role, parent):
        if pid <= 1 or pid == os.getpid() or pid in self.owned:
            raise RuntimeError('invalid/duplicate owned identity')
        before = identity(pid)
        if before['ppid'] != parent:
            raise RuntimeError('kernel parentage not owned')
        fd = os.pidfd_open(pid, 0)
        self.owned[pid] = dict(role=role, fd=fd, initial=before, wait=None, collected_by_C=False)
        after = identity(pid)
        if after['start_ticks'] != before['start_ticks'] or after['ppid'] != parent:
            raise RuntimeError('identity changed while acquiring handle')
        self.event('initial-owned-handle', pid=pid, role=role, identity=after, pidfd=fd)
        return self.owned[pid]

    def refuse_reuse(self, phase):
        if self.reservation.acquire():
            raise RuntimeError('unsafe observer reservation reuse')
        self.event('reuse-refused', phase=phase, quarantined=self.reservation.quarantined)

    def invalidate(self, reason, fault_at=None):
        self.quarantined = True
        self.reservation.settle(False)
        if self.cleanup_deadline is None:
            self.cleanup_deadline = (time.monotonic() if fault_at is None else fault_at) + self.module.P['cleanup_observation_window']
            self.event('invalidated-no-reuse', reason=reason, cleanup_deadline=self.cleanup_deadline)

    def signal_owned(self, pid, sig):
        row = self.owned[pid]
        if row['wait'] is not None or row['collected_by_C']:
            return
        try:
            signal.pidfd_send_signal(row['fd'], sig, None, 0)
            self.event('signal', pid=pid, signal=int(sig), pidfd=row['fd'])
        except ProcessLookupError:
            self.event('signal-ESRCH-await-real-status', pid=pid, signal=int(sig))

    def discover_and_collect(self):
        # Kernel-proven direct children only. Candidate enumeration is NOT an empty proof.
        hints = Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()
        for name in hints:
            pid = int(name)
            if pid not in self.owned:
                self.adopt_handle(pid, 'adopted-worker', os.getpid())
        while True:
            state, pid = peek()
            if state != 'event':
                return state
            if pid not in self.owned:
                self.adopt_handle(pid, 'adopted-worker', os.getpid())
            row = self.owned[pid]
            got, status, usage = os.wait4(pid, os.WNOHANG)
            if got != pid or not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                raise RuntimeError('actual terminal wait missing')
            row['wait'] = dict(pid=pid, raw_status=status, exitcode=os.waitstatus_to_exitcode(status),
                               user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
                               maxrss_kernel_units=usage.ru_maxrss)
            self.event('actual-terminal-wait4', **row['wait'])

    def check_policy(self, msg):
        if msg['control_bytes'] != 0 or msg['image_bytes'] != 0:
            raise RuntimeError('pre-G phase violated')
        self.wpid = int(msg['pid'])
        row = self.adopt_handle(self.wpid, 'worker-late-handoff', self.cpid)
        current = identity(self.wpid)
        if current['sid'] != self.wpid or current['pgid'] != self.wpid:
            raise RuntimeError('session not established')
        if digest(Path(f'/proc/{self.wpid}/exe')) != ELF_HASH:
            raise RuntimeError('actual executable mismatch')
        readback = {str(k): list(resource.prlimit(self.wpid, k)) for k in self.module.base.LIMITS}
        if any(tuple(readback[str(k)]) != limits for k, limits in self.module.base.LIMITS.items()):
            raise RuntimeError('actual policy mismatch')
        row['verified_policy'] = readback
        self.event('pre-G-executable-session-policy-verified', pid=self.wpid, identity=current,
                   executable_sha256=ELF_HASH, policy=readback)

    def cleanup(self):
        if self.cleanup_deadline is None:
            self.cleanup_deadline = time.monotonic() + self.module.P['cleanup_observation_window']
            self.event('final-settlement-window', cleanup_deadline=self.cleanup_deadline)
        # C first: its exit makes any pre-handoff W adoptable. Keep one deadline.
        if self.cpid in self.owned and self.owned[self.cpid]['wait'] is None:
            self.signal_owned(self.cpid, signal.SIGKILL)
        while time.monotonic() < self.cleanup_deadline:
            state = self.discover_and_collect()
            for pid, row in list(self.owned.items()):
                if pid != self.cpid and row['wait'] is None and not row['collected_by_C']:
                    self.signal_owned(pid, signal.SIGKILL)
            if state == 'empty' and all(r['wait'] or r['collected_by_C'] for r in self.owned.values()):
                self.reservation.settle(True)
                self.event('actual-ECHILD-all-known-statuses-settled')
                return True
            time.sleep(0.002)
        return False


def run(mode, out):
    out.mkdir(parents=True, exist_ok=False)
    module, case, hashes = preflight()
    baseline = module.base.open_fds()
    context = dict(time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   argv=sys.argv, cwd=os.getcwd(), python=sys.version, executable=sys.executable,
                   kernel=list(os.uname()), uid=os.getuid(), observer_pid=os.getpid(),
                   runner_sha256=digest(Path(__file__)), bindings=hashes, parameters=module.P,
                   core_bytes=0, subreaper_readback=1, initial_FDs=baseline,
                   initial_sid=os.getsid(0), initial_pgid=os.getpgrp(),
                   initial_limits={str(k): list(resource.getrlimit(k)) for k in module.base.LIMITS})
    write(out / 'environment.json', context)
    observer = Observer(module, out)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    success = False
    error = None
    try:
        pid = os.fork()
        if pid == 0:
            parent.close()
            coordinator(module, case, mode, child, out, observer.deadline)
            os._exit(75)
        observer.cpid = pid
        child.close()
        observer.adopt_handle(pid, 'coordinator', os.getpid())
        observer.refuse_reuse('live-coordinator-before-start')
        packet(parent, {'kind': 'start'})
        stopped = None
        channel_open = True
        while time.monotonic() < observer.deadline:
            observer.discover_and_collect()
            if observer.owned[pid]['wait']:
                break
            if select.select([parent] if channel_open else [], [], [], 0.002)[0]:
                msg = receive(parent, allow_eof=True)
                if msg is None:
                    channel_open = False
                    observer.event('control-EOF-not-terminal-status')
                    continue
                observer.event('control-message', message=msg)
                if msg['kind'] == 'policy':
                    observer.check_policy(msg)
                    if mode == 'held-kill':
                        observer.signal_owned(observer.wpid, signal.SIGSTOP)
                        packet(parent, {'kind': 'collect-stop'})
                    elif mode == 'normal':
                        packet(parent, {'kind': 'continue'})
                    else:
                        raise RuntimeError('early case reached late handoff')
                elif msg['kind'] == 'stopped' and mode == 'held-kill':
                    if (msg['pid'] != observer.wpid or not os.WIFSTOPPED(msg['raw_status'])
                            or os.WSTOPSIG(msg['raw_status']) != signal.SIGSTOP
                            or msg['control_bytes'] != 0 or msg['image_bytes'] != 0):
                        raise RuntimeError('stopped witness invalid')
                    now_identity = identity(observer.wpid)
                    if (now_identity['ppid'], now_identity['sid'], now_identity['pgid'], now_identity['state']) != (pid, observer.wpid, observer.wpid, 'T'):
                        raise RuntimeError('held identity changed before coordinator kill')
                    stopped = msg
                    observer.invalidate('controlled-coordinator-kill')
                    observer.signal_owned(pid, signal.SIGKILL)
                    break
                elif msg['kind'] == 'complete':
                    # Wait for actual C status, not socket EOF.
                    break
                else:
                    raise RuntimeError('unexpected message')
        until = observer.cleanup_deadline or observer.deadline
        while time.monotonic() < until and observer.owned[pid]['wait'] is None:
            observer.discover_and_collect()
            time.sleep(0.002)
        if observer.owned[pid]['wait'] is None:
            raise RuntimeError('coordinator status missing')
        if mode == 'normal':
            record = json.loads((out / (case['id'] + '.json')).read_text())
            if (not record['passed'] or record['owner_wait']['exitcode'] != 0
                    or record['pid'] != observer.wpid or record['control_bytes'] != 1
                    or record['image_bytes'] != 172800 or record['stdout_observed'] != 198
                    or record['input_sha256'] != INPUT_HASH or not record['parent_FDs_restored']
                    or not record['actual_status_acquired'] or record['owner_quarantined']
                    or digest(out / (case['id'] + '.stdout.bin')) != OUTPUT_HASH
                    or observer.owned[pid]['wait']['exitcode'] != 0):
                raise RuntimeError('normal smoke evidence failed')
            observer.owned[observer.wpid]['collected_by_C'] = record['owner_wait']
        elif mode == 'early-exit':
            proof = json.loads((out / 'early-exit.json').read_text())
            observer.invalidate('early-coordinator-exit', proof['fault_at'])
            while time.monotonic() < observer.cleanup_deadline and len(observer.owned) < 2:
                observer.discover_and_collect()
                if len(observer.owned) < 2:
                    time.sleep(0.002)
            adopted = [p for p in observer.owned if p != pid]
            if (observer.owned[pid]['wait']['exitcode'] != 73 or adopted != [proof['pid']]
                    or proof['control_bytes'] != 0 or proof['image_bytes'] != 0
                    or any(e['kind'] == 'pre-G-executable-session-policy-verified' for e in observer.events)):
                raise RuntimeError('early exit/adoption witness failed')
            observer.refuse_reuse('early-exit-invalidated')
            observer.event('early-exit-kernel-adoption-verified', proof=proof, adopted=adopted)
        else:
            if stopped is None or observer.owned[pid]['wait']['exitcode'] != -signal.SIGKILL:
                raise RuntimeError('held coordinator kill not exercised')
            observer.discover_and_collect()
            wrow = observer.owned[observer.wpid]
            live = wrow['wait'] is None
            state = identity(observer.wpid) if live else None
            if state is not None and state['ppid'] != os.getpid():
                raise RuntimeError('held worker not adopted')
            observer.refuse_reuse('C-collected-W-not-yet-cleaned')
            observer.event('discriminant', coordinator_collected=True, worker_terminal_status=wrow['wait'],
                           worker_still_live=live, worker_identity=state,
                           pidfd_readable=bool(select.select([wrow['fd']], [], [], 0)[0]))
        success = True
    except BaseException:
        error = traceback.format_exc()
        (out / 'observer-error.txt').write_text(error)
        observer.invalidate('case-failed')
    finally:
        parent.close()
        child.close()
        try:
            # Preserve actual status written by the unchanged supervisor even if
            # another harness assertion failed after its wait/IO settlement.
            record_path = out / (case['id'] + '.json')
            if observer.wpid in observer.owned and record_path.exists():
                status_record = json.loads(record_path.read_text())
                waited = status_record.get('owner_wait')
                if (status_record.get('actual_status_acquired') and waited
                        and waited['pid'] == observer.wpid and status_record['pid'] == observer.wpid
                        and (os.WIFEXITED(waited['raw_status']) or os.WIFSIGNALED(waited['raw_status']))):
                    observer.owned[observer.wpid]['collected_by_C'] = waited
            cleaned = observer.cleanup()
        except BaseException:
            cleaned = False
            (out / 'cleanup-error.txt').write_text(traceback.format_exc())
        if not cleaned:
            write(out / 'quarantine.json', dict(observer_pid=os.getpid(), owned=observer.owned,
                  error=error, reason='Missing terminal status/ownership; retain this live O. No new case.'))
            print('QUARANTINE: live observer', os.getpid(), str(out), flush=True)
            # Explicitly no watchdog/automatic exit, no new signals or experiments.
            while True:
                time.sleep(1)
        for row in observer.owned.values():
            os.close(row['fd'])
    final_fds = module.base.open_fds()
    checks = dict(case_outcome=success, actual_child_settlement=cleaned,
                  exactly_C_and_W=len(observer.owned) == 2,
                  single_threaded=len(list(Path('/proc/self/task').iterdir())) == 1,
                  no_remaining_children=peek()[0] == 'empty', FDs_restored=final_fds == baseline,
                  parent_identity_unchanged=(os.getsid(0), os.getpgrp()) == (context['initial_sid'], context['initial_pgid']),
                  parent_limits_unchanged={str(k): list(resource.getrlimit(k)) for k in module.base.LIMITS} == context['initial_limits'])
    result = dict(mode=mode, checks=checks, passed=all(checks.values()), owned=observer.owned,
                  quarantined_during_settlement=observer.quarantined, final_FDs=final_fds,
                  duration_seconds=time.monotonic() - observer.started, events=observer.events)
    write(out / 'result.json', result)
    print(mode, 'PASS' if result['passed'] else 'FAIL', 'actual children', len(observer.owned), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['normal', 'early-exit', 'held-kill'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.case, args.out))
