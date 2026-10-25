#!/usr/bin/env python3
"""Opt-in HRT source candidate. No import starts an actor or imports product code.

Run and verify are separate commands, each requiring distinct later admission.
Only already-public test-key-1 is ever selected by the Rust actor.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
MAX_RECORD = 1024
HEADER = struct.Struct('>4sIB16sII')
PREFIX = struct.Struct('>I')
INIT, PRESENT, WAIT_ACK, WAIT_READY, RESUME_ACK, CANCEL, RESULT, TERMINAL, SIGN_ENTRY, AUX_ENTRY, COMMIT_CLAIM = range(1, 12)
ACTIVE_NS = 5_000_000_000
WAIT_NS = 5_500_000_000
POLL_NS = 25_000_000
GAP_NS = 50_000_000
CPU_R_NS = 100_000_000
CPU_S_NS = 400_000_000
QUANTIZATION_NS = 20_000_000
CLEANUP_NS = 4_000_000_000
STREAM_CAP = 65_536
TRACE_CAP = 131_072
RAW_PATH = 'docs/restart/implementation/QH01/native-qr-probe/expected/request-kind-1-basic.envelope'
RAW_SHA = '88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7'


class Refusal(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Refusal(reason)


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate-json-member')
        value[key] = item
    return value


def bounded_file(path, maximum):
    require(path.is_file() and not path.is_symlink(), 'regular-file')
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, 'file-cap')
    return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def preflight():
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64', 'linux-x86_64-only')
    require(os.sysconf('SC_CLK_TCK') == 100, 'clock-tick-contract')
    freeze_raw = bounded_file(HERE / 'source-freeze.json', 65_536)
    freeze = json.loads(freeze_raw, object_pairs_hook=unique)
    require(freeze['role'] == 'SOURCE_ONLY_NO_BUILD_OR_RUNTIME', 'source-freeze-role')
    require(len(freeze['files']) <= 32, 'source-freeze-cap')
    for row in freeze['files']:
        path = Path(row['path'])
        require(not path.is_absolute() and '..' not in path.parts, 'freeze-relative-path')
        data = bounded_file(ROOT / path, row['bytes'])
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'source-freeze-hash')
    cases = json.loads(bounded_file(HERE / 'cases.json', 65_536), object_pairs_hook=unique)['cases']
    require(len(cases) == 33 and [row['id'] for row in cases] == list(range(33)), 'closed-case-catalog')
    golden = json.loads(bounded_file(HERE / 'inherited-catalog.json', 32_768), object_pairs_hook=unique)
    require(golden['required_new_intake_tick'] == 0 and len(golden['frames']) == 31, 'frozen-catalog-context')
    raw = bounded_file(ROOT / RAW_PATH, 259)
    require(len(raw) == 259 and sha(raw) == RAW_SHA, 'original-raw259')
    return freeze, sha(freeze_raw), cases, golden['frames'], raw


def process_stat(pid):
    path = Path('/proc') / str(pid) / 'stat'
    raw = bounded_file(path, 4096)
    split = raw.rfind(b') ')
    require(split > 0 and raw[:raw.find(b' (')].decode('ascii') == str(pid), 'proc-stat-identity')
    fields = raw[split + 2:].split()
    require(len(fields) >= 20, 'proc-stat-fields')
    cpu = int(fields[11]) + int(fields[12])
    start = int(fields[19])
    require(0 <= cpu < 1 << 64 and 0 <= start < 1 << 64, 'proc-counter-range')
    children = bounded_file(Path('/proc') / str(pid) / 'task' / str(pid) / 'children', 4096).split()
    return {'pid': pid, 'start': start, 'cpu': cpu, 'ppid': int(fields[1]),
            'threads': int(fields[17]), 'state': fields[0].decode('ascii'),
            'children': tuple(int(value) for value in children)}


class Trace:
    def __init__(self):
        self.rows = []
        self.bytes = 2

    def add(self, event, **values):
        row = {'i': len(self.rows), 'event': event, **values}
        size = len(json.dumps(row, separators=(',', ':'), ensure_ascii=True).encode()) + 1
        require(self.bytes + size <= TRACE_CAP - 8192, 'trace-cap')
        self.bytes += size
        self.rows.append(row)


class Supervisor:
    def __init__(self, args, case, frames, raw, freeze_sha):
        require(type(args.origin_ns) is int and 0 <= args.origin_ns < 1 << 64, 'origin-range')
        now = time.monotonic_ns()
        require(args.origin_ns <= now < args.origin_ns + 1_000_000_000, 'trusted-launch-origin')
        self.origin = args.origin_ns
        self.deadline = self.origin + (100_000_000 if case['id'] == 2 else 100_000_000_000)
        require(self.deadline < 1 << 64, 'deadline-overflow')
        self.case = case
        self.frames = frames
        self.freeze_sha = freeze_sha
        self.nonce = os.urandom(16)  # Correlation only, never a signing/entropy provider.
        self.trace = Trace()
        self.sequence_out = self.sequence_in = self.records = self.cycles = 0
        self.phase = 'ACTIVE'
        self.active_started = self.origin
        self.active_accum = self.wait_cpu = 0
        self.wait_started = self.wait_base = None
        self.wait_used = self.wait_ready = False
        self.wait_elapsed = None
        self.current = None
        self.last_index = -1
        self.last_serial = 0
        self.sink_committed = False
        self.resume_armed = False
        self.result = self.terminal = None
        self.sign_entries = self.aux_entries = 0
        self.revoked = False
        self.reason = self.invalidated = self.kill_at = self.cleanup_deadline = None
        self.killed = self.quarantined = False
        self.raw_wait = self.exit_code = None
        self.eof = set()
        self.tail = bytearray()
        self.pending = bytearray()
        self.pending_records = 0
        self.sent_raw = bytearray()
        self.stdout_raw = bytearray()
        self.stderr_raw = bytearray()
        self.faults = set()
        self.selected = selectors.DefaultSelector()
        binary = Path(args.binary)
        require(binary.is_absolute() and binary.resolve(strict=True) == binary, 'absolute-binary')
        binary_bytes = bounded_file(binary, 32 * 1024 * 1024)
        require(binary_bytes[:6] == b'\x7fELF\x02\x01' and binary_bytes[18:20] == b'>\0', 'linux-elf-x86_64')
        require(len(args.binary_sha256) == 64 and sha(binary_bytes) == args.binary_sha256, 'binary-sha256')
        require(time.monotonic_ns() - self.origin < ACTIVE_NS, 'startup-budget')
        self.last_checkpoint = time.monotonic_ns()
        initial_payload = struct.pack('>QQHH', self.origin, self.deadline, case['id'], len(raw)) + raw
        own_stat = process_stat(os.getpid())
        self.child = subprocess.Popen([str(binary), '--hrt-source-admitted-v1'], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        # All subsequent setup is protected by run(); no exception may abandon R.
        self.pidfd = None
        self.stdin_closed = False
        self.identities = {os.getpid(): own_stat}
        self.binary = binary
        self.binary_sha256 = args.binary_sha256
        self.initial_payload = initial_payload

    def startup(self):
        for stream in (self.child.stdin, self.child.stdout, self.child.stderr):
            os.set_blocking(stream.fileno(), False)
        self.selected.register(self.child.stdout, selectors.EVENT_READ, 'stdout')
        self.selected.register(self.child.stderr, selectors.EVENT_READ, 'stderr')
        self.pidfd = os.pidfd_open(self.child.pid)
        self.identities[self.child.pid] = process_stat(self.child.pid)
        require(self.identities[self.child.pid]['ppid'] == os.getpid(), 'direct-child')
        # This explicitly kernel-owned /proc link is the sole symlink read allowed.
        loaded_path = Path('/proc') / str(self.child.pid) / 'exe'
        require(loaded_path.resolve(strict=True) == self.binary, 'loaded-elf-path')
        with loaded_path.open('rb') as stream:
            loaded = stream.read(32 * 1024 * 1024 + 1)
        require(len(loaded) <= 32 * 1024 * 1024 and sha(loaded) == self.binary_sha256, 'loaded-elf-sha256')
        require(sha(bounded_file(self.binary, 32 * 1024 * 1024)) == self.binary_sha256, 'binary-post-spawn-sha256')
        self.trace.add('actor', pid=self.child.pid, start=self.identities[self.child.pid]['start'],
                       source_freeze_sha256=self.freeze_sha, binary_sha256=self.binary_sha256)
        self.checkpoint()
        self.queue(INIT, 0, 0, self.initial_payload)

    def fault(self, name):
        self.faults.add(name)
        self.trace.add('fault-injected', name=name)

    def checkpoint(self):
        now = time.monotonic_ns()
        require(now >= self.last_checkpoint, 'clock-rollback')
        if self.revoked:
            self.last_checkpoint = now
            return now
        require(now - self.last_checkpoint <= GAP_NS, 'monitor-gap')
        self.last_checkpoint = now
        require(now < self.deadline, 'deadline')
        stats = {}
        for pid, original in self.identities.items():
            if pid == self.child.pid and self.raw_wait is not None:
                continue
            value = process_stat(pid)
            require(value['start'] == original['start'] and value['threads'] == 1, 'actor-identity-or-threads')
            expected_children = (self.child.pid,) if pid == os.getpid() and self.raw_wait is None else ()
            require(value['children'] == expected_children, 'unexpected-descendant')
            stats[pid] = value
        if self.phase == 'WAIT':
            require(self.child.pid in stats and self.wait_base is not None, 'wait-actor-lost')
            upper = {}
            for pid, start in self.wait_base.items():
                delta = stats[pid]['cpu'] - start
                require(delta >= 0, 'cpu-counter-rollback')
                upper[pid] = delta * 10_000_000 + QUANTIZATION_NS
            require(upper[self.child.pid] <= CPU_R_NS, 'wait-cpu-R')
            require(upper[os.getpid()] <= CPU_S_NS, 'wait-cpu-S')
            self.wait_cpu = sum(upper.values())
            self.trace.add('wait-cpu', ns=str(now), r=str(upper[self.child.pid]), s=str(upper[os.getpid()]))
        active = self.active_accum + (now - self.active_started if self.phase == 'ACTIVE' else 0)
        require(active + self.wait_cpu <= ACTIVE_NS, 'active-budget')
        return now

    def queue(self, opcode, invocation, epoch, payload=b'', nonce=None):
        self.checkpoint()
        require(not self.revoked and not self.stdin_closed, 'queue-after-revoke')
        require(self.pending_records < 2 and self.sequence_out < 4096, 'outgoing-record-cap')
        body = HEADER.pack(b'HRT1', self.sequence_out + 1, opcode, self.nonce if nonce is None else nonce,
                           invocation, epoch) + payload
        require(HEADER.size <= len(body) <= MAX_RECORD - 4, 'record-length')
        require(len(self.sent_raw) + len(self.pending) + 4 + len(body) <= STREAM_CAP - 64, 'stdin-stream-cap')
        self.sequence_out += 1
        self.pending.extend(PREFIX.pack(len(body)) + body)
        self.pending_records += 1
        try:
            self.selected.modify(self.child.stdin, selectors.EVENT_WRITE, 'stdin')
        except KeyError:
            self.selected.register(self.child.stdin, selectors.EVENT_WRITE, 'stdin')

    def write_turn(self):
        if not self.pending:
            return
        self.checkpoint()
        try:
            amount = os.write(self.child.stdin.fileno(), self.pending[:256])
        except BlockingIOError:
            return
        require(amount > 0, 'stdin-write')
        self.sent_raw.extend(self.pending[:amount])
        require(len(self.sent_raw) <= STREAM_CAP, 'stdin-stream-cap')
        del self.pending[:amount]
        if not self.pending:
            self.pending_records = 0
            self.selected.unregister(self.child.stdin)
        self.checkpoint()

    def draw(self, frame):
        require(self.case['id'] != 3, 'partial-draw')
        cells = []
        for role in ('label', 'body', 'position'):
            value = frame[role]
            require(type(value) is str and value.isascii(), 'whole-frame-ascii')
            for line in value.split('\n'):
                require(len(line) <= 32 and all(32 <= ord(c) <= 126 for c in line), 'whole-frame-fit')
                cells.append((role, line))
        require(len(cells) <= 8, 'whole-frame-lines')
        # S owns this logical synthetic sink. No child COMMIT is trusted.
        receipt = sha(json.dumps(cells, separators=(',', ':')).encode('ascii'))
        self.checkpoint()
        self.sink_committed = True
        self.trace.add('sink-commit', invocation=self.current[0], epoch=self.current[1],
                       index=frame['index'], cells=len(cells), sha256=receipt)

    def resume(self, invocation, epoch, action, serial, cycle=7, nonce=None):
        require(self.phase == 'ACTIVE' and self.resume_armed and self.sink_committed, 'resume-before-arm')
        self.checkpoint()
        self.queue(RESUME_ACK, invocation, epoch, struct.pack('>BIB', action, serial, cycle), nonce)
        self.trace.add('resume-queued', invocation=invocation, epoch=epoch, serial=serial, action=action)

    def acknowledge_cycle(self):
        now = self.checkpoint()
        if self.phase == 'WAIT':
            self.active_started = now
            self.phase = 'ACTIVE'
            final_upper = {}
            for pid, start in self.wait_base.items():
                delta = process_stat(pid)['cpu'] - start
                require(delta >= 0, 'cpu-counter-rollback')
                final_upper[pid] = delta * 10_000_000 + QUANTIZATION_NS
            require(final_upper[self.child.pid] <= CPU_R_NS, 'wait-cpu-R')
            require(final_upper[os.getpid()] <= CPU_S_NS, 'wait-cpu-S')
            self.wait_cpu = sum(final_upper.values())
            self.wait_elapsed = now - self.wait_started
            self.trace.add('wait-ended', elapsed_ns=str(self.wait_elapsed), cpu_charge_ns=str(self.wait_cpu))
        self.resume_armed = True  # ACTIVE timer already covers now through this ACK/write.
        self.checkpoint()
        invocation, epoch, kind, index = self.current
        self.last_serial += 1
        self.cycles += 1
        require(self.cycles <= 1024, 'cycle-cap')
        action, cycle, nonce = (1 if kind else 0), 7, None
        if self.case['id'] == 4:
            epoch -= 1
            self.fault('stale-epoch')
        elif self.case['id'] == 5 and index == 1:
            self.last_serial -= 1
            self.fault('replay-cycle')
        elif self.case['id'] == 6:
            nonce = bytes([self.nonce[0] ^ 1]) + self.nonce[1:]
            self.fault('wrong-incarnation')
        elif self.case['id'] == 7:
            cycle = 2
            self.fault('preheld')
        elif self.case['id'] == 8:
            cycle = 15
            self.fault('simultaneous')
        elif self.case['id'] == 30 and invocation == 1:
            action, cycle, self.last_serial = 4, 0, 0
            self.fault('none-cached')
        elif self.case['id'] == 30:
            invocation, epoch = 1, 1
        elif self.case['id'] == 31 and not kind:
            action = 1
            self.fault('approve-data')
        elif self.case['id'] == 32 and kind:
            action = 0
            self.fault('next-decision')
        self.resume(invocation, epoch, action, self.last_serial, cycle, nonce)

    def record(self, opcode, invocation, epoch, payload):
        self.checkpoint()
        if opcode == PRESENT:
            require(self.terminal is None and not self.revoked and self.phase == 'ACTIVE', 'present-phase')
            require(invocation == (1 if self.current is None else self.current[0] + 1) and epoch == invocation, 'presentation-sequence')
            require(invocation <= 1024 and len(payload) >= 11, 'presentation-cap')
            kind, index, total, a, b, c = struct.unpack('>BHHHHH', payload[:11])
            require(a <= 176 and b <= 264 and c <= 9 and 11 + a + b + c == len(payload), 'presentation-fields')
            label = payload[11:11+a].decode('ascii')
            body = payload[11+a:11+a+b].decode('ascii')
            position = payload[11+a+b:].decode('ascii')
            frame = dict(kind=kind, index=index, total=total, label=label, body=body, position=position)
            require(index < len(self.frames) and frame == self.frames[index], 'inherited-catalog-mismatch')
            repeated_none = self.case['id'] == 30 and invocation == 2 and index == 0
            require(index == self.last_index + 1 or repeated_none, 'page-order')
            self.last_index = index
            self.current = invocation, epoch, kind, index
            self.sink_committed = self.resume_armed = False
            self.draw(frame)
            if not self.wait_used:
                self.checkpoint()
                self.wait_base = {pid: process_stat(pid)['cpu'] for pid in self.identities}
                now = self.checkpoint()
                self.active_accum += now - self.active_started
                self.wait_started = now
                self.wait_used = True
                self.phase = 'WAIT'
                self.queue(WAIT_ACK, invocation, epoch)
                self.trace.add('wait-ack-queued', ns=str(now), invocation=invocation, epoch=epoch)
            else:
                self.acknowledge_cycle()
        elif opcode == WAIT_READY:
            require(self.phase == 'WAIT' and self.current is not None and (invocation, epoch) == self.current[:2]
                    and not self.wait_ready and payload == b'', 'unexpected-record')
            self.wait_ready = True
            if self.case['id'] == 11:
                self.fault('resume-before-arm')
                self.resume(invocation, epoch, 0, 1)
            elif self.case['id'] == 26:
                self.fault('child-stop')
                signal.pidfd_send_signal(self.pidfd, signal.SIGSTOP)
            elif self.case['id'] == 27:
                self.fault('supervisor-gap')
                time.sleep(0.075)  # Intentional elapsed pause, not an OS SIGSTOP claim.
                self.checkpoint()
        elif opcode in (SIGN_ENTRY, AUX_ENTRY):
            require(self.phase == 'ACTIVE' and invocation == epoch == 0 and len(payload) == 4 and self.current is not None
                    and self.current[2] == 1, 'entry-phase')
            count = struct.unpack('>I', payload)[0]
            if opcode == SIGN_ENTRY:
                require(count == 1 and self.sign_entries == 0 and self.aux_entries == 0, 'sign-entry-count')
                self.sign_entries = count
            else:
                require(count == 1 and self.sign_entries == 1 and self.aux_entries == 0, 'aux-entry-count')
                self.aux_entries = count
            self.trace.add('driver-sign-entry' if opcode == SIGN_ENTRY else 'auxiliary-entry', count=count)
        elif opcode == RESULT:
            require(self.phase == 'ACTIVE' and invocation == epoch == 0 and self.result is None
                    and self.terminal is None and self.sign_entries == self.aux_entries == 1, 'result-phase')
            require(1 <= len(payload) <= 947 and payload.startswith(b'nsealr1:'), 'private-result-bounds')
            if self.case['id'] == 28:
                self.fault('post-core-cancel')
                raise Refusal('post-core-cancel')
            self.result = bytes(payload)  # Private only; no client/publication path exists.
            self.trace.add('private-result-staged', bytes=len(payload), sha256=sha(payload))
        elif opcode == TERMINAL:
            require(invocation == epoch == 0 and len(payload) == 12, 'terminal-shape')
            require(self.terminal is None, 'duplicate-terminal')
            status, sign_count, aux_count, reviews = struct.unpack('>HIIH', payload)
            require(sign_count <= 1 and aux_count <= 1 and reviews <= 1024, 'terminal-counts')
            self.terminal = dict(status=status, sign_entries=sign_count, auxiliary_calls=aux_count, review_calls=reviews)
            require(sign_count == self.sign_entries and aux_count == self.aux_entries, 'terminal-entry-consistency')
            self.close_stdin()
            self.trace.add('terminal', **self.terminal)
            if status != 0:
                raise Refusal('child-status:' + str(status))
        else:
            raise Refusal('unexpected-record')

    def parse_turn(self):
        if len(self.tail) < 4:
            return
        length = PREFIX.unpack(self.tail[:4])[0]
        require(HEADER.size <= length <= MAX_RECORD - 4, 'record-length')
        if len(self.tail) < 4 + length:
            return
        body = bytes(self.tail[4:4+length])
        del self.tail[:4+length]
        self.records += 1
        require(self.records <= 4096, 'incoming-record-cap')
        magic, seq, opcode, nonce, invocation, epoch = HEADER.unpack(body[:HEADER.size])
        require(magic == b'HRT1' and nonce == self.nonce and seq == self.sequence_in + 1, 'record-envelope')
        self.sequence_in = seq
        self.record(opcode, invocation, epoch, body[HEADER.size:])
        self.checkpoint()

    def read_turn(self, name):
        self.checkpoint()
        stream = self.child.stdout if name == 'stdout' else self.child.stderr
        try:
            value = os.read(stream.fileno(), 256)
        except BlockingIOError:
            return
        if not value:
            self.eof.add(name)
            self.selected.unregister(stream)
            stream.close()
            return
        target = self.stdout_raw if name == 'stdout' else self.stderr_raw
        cap = STREAM_CAP if name == 'stdout' else 4096
        before = len(target)
        target.extend(value[:max(0, cap - before)])
        require(before + len(value) <= cap, name + '-stream-cap')
        if name == 'stderr':
            raise Refusal('unexpected-stderr')
        self.tail.extend(value)
        require(len(self.tail) <= MAX_RECORD + 255, 'record-buffer-cap')
        if not self.revoked:
            self.parse_turn()  # One completed record at most before the next checkpoint.
        else:
            self.tail.clear()  # Ineligible raw bytes remain bounded in stdout_raw.
        self.checkpoint()

    def collect(self):
        if self.raw_wait is not None or 'stdout' not in self.eof or self.tail:
            return
        try:
            pid, status, _usage = os.wait4(self.child.pid, os.WNOHANG)
        except ChildProcessError as error:
            raise Refusal('wait-status-unknown') from error
        if pid:
            require(pid == self.child.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)), 'wait-status')
            self.raw_wait, self.exit_code = status, os.waitstatus_to_exitcode(status)
            self.child.returncode = self.exit_code  # This exact wait4 already collected R.
            self.trace.add('wait4', raw_status=status, exit_code=self.exit_code)

    def close_stdin(self):
        if self.stdin_closed:
            return
        self.pending.clear()
        self.pending_records = 0
        try:
            self.selected.unregister(self.child.stdin)
        except KeyError:
            pass
        self.child.stdin.close()
        self.stdin_closed = True

    def revoke(self, reason):
        if self.revoked:
            return
        self.revoked = True
        self.reason = reason
        self.invalidated = time.monotonic_ns()
        self.kill_at = self.invalidated + GAP_NS
        self.cleanup_deadline = self.invalidated + CLEANUP_NS
        self.result = None
        self.tail.clear()  # Raw ineligible protocol bytes remain in the bounded capture.
        self.pending.clear()  # Never send queued gestures after invalidation.
        self.pending_records = 0
        try:
            self.trace.add('revoked', reason=reason, ns=str(self.invalidated))
        except Refusal:
            pass
        # Cooperative cancellation is a local closed record, never approval.
        if not self.stdin_closed and self.sequence_out >= 4096:
            self.close_stdin()
        if not self.stdin_closed:
            invocation, epoch = self.current[:2] if self.current is not None else (0, 0)
            self.sequence_out += 1
            body = HEADER.pack(b'HRT1', self.sequence_out, CANCEL, self.nonce, invocation, epoch)
            self.pending.extend(PREFIX.pack(len(body)) + body)
            self.pending_records = 1
            try:
                self.selected.modify(self.child.stdin, selectors.EVENT_WRITE, 'stdin')
            except KeyError:
                self.selected.register(self.child.stdin, selectors.EVENT_WRITE, 'stdin')

    def settled(self):
        return self.raw_wait is not None and self.eof == {'stdout', 'stderr'} and self.stdin_closed

    def run(self):
        try:
            self.startup()
        except BaseException as error:
            self.revoke('startup:' + str(error)[:120])
        while not self.settled():
            try:
                now = self.checkpoint()
                if self.phase == 'WAIT' and self.wait_ready and not self.revoked:
                    if self.case['id'] == 1:
                        self.fault('cancel-wait')
                        raise Refusal('cancel-wait')
                    if self.case['id'] == 26:
                        if process_stat(self.child.pid)['state'] in ('T', 't'):
                            self.trace.add('actual-child-stopped')
                            raise Refusal('child-stop')
                    elif self.case['id'] not in (2, 10, 12, 27):
                        delay = WAIT_NS if self.case['id'] == 0 else 0
                        if now >= self.wait_started + delay:
                            self.acknowledge_cycle()
                if self.revoked and self.raw_wait is None and now >= self.kill_at and not self.killed:
                    self.killed = True  # One attempt; ESRCH is not collection.
                    try:
                        if self.pidfd is not None:
                            signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                        else:
                            # Startup failure only: still-owned direct unreaped PID.
                            os.kill(self.child.pid, signal.SIGKILL)
                        self.trace.add('kill-attempt', pid=self.child.pid, errno=None)
                    except OSError as error:
                        self.trace.add('kill-attempt', pid=self.child.pid, errno=error.errno)
                    # Always continue draining/collecting after a failed signal.
                if self.revoked and now >= self.cleanup_deadline and not self.quarantined:
                    self.quarantined = True
                    self.trace.add('quarantined', reason='unsettled-after-shared4s')
                    # Preserve this live S, original pidfd/channels and reservation.
                    # No replacement/exit/claim of collection follows a report timeout.
                ready = self.selected.select(POLL_NS / 1_000_000_000)
                for key, _mask in ready:
                    self.checkpoint()
                    if key.data == 'stdin':
                        if self.revoked:
                            try:
                                amount = os.write(self.child.stdin.fileno(), self.pending[:256])
                                self.sent_raw.extend(self.pending[:amount])
                                del self.pending[:amount]
                                if not self.pending:
                                    self.close_stdin()
                            except (BlockingIOError, BrokenPipeError):
                                self.close_stdin()
                        else:
                            self.write_turn()
                    else:
                        self.read_turn(key.data)
                    self.checkpoint()
                if not self.revoked:
                    self.parse_turn()  # A buffered complete record cannot wait for another read event.
                if 'stdout' in self.eof and self.tail:
                    complete = len(self.tail) >= 4 and len(self.tail) >= 4 + PREFIX.unpack(self.tail[:4])[0]
                    require(complete, 'partial-record')
                self.collect()
                if self.raw_wait is not None and not self.stdin_closed:
                    self.close_stdin()
            except BaseException as error:
                self.revoke(str(error)[:160])
                if self.stdin_closed:
                    self.pending.clear()
        if not self.revoked:
            try:
                self.checkpoint()
                require(self.exit_code == 0 and self.terminal is not None and self.terminal['status'] == 0,
                        'missing-terminal-or-exit')
                require(self.result is not None and self.terminal['sign_entries'] == self.terminal['auxiliary_calls'] == 1,
                        'missing-private-result')
                require(self.wait_elapsed is not None and self.wait_elapsed >= WAIT_NS, 'real-wait-too-short')
                require(self.case['id'] == 0, 'negative-produced-candidate')
            except Refusal as error:
                self.revoke(str(error))
        self.selected.close()
        if self.pidfd is not None:
            os.close(self.pidfd)
        return not self.revoked


def expected_case(case, owner, eligible):
    if case['id'] == 0:
        return eligible and owner.terminal == dict(status=0, sign_entries=1, auxiliary_calls=1, review_calls=31)
    if eligible or not owner.revoked or not owner.settled() or owner.quarantined:
        return False
    reason = owner.reason
    rules = {
        1: 'cancel-wait', 2: 'deadline', 3: 'partial-draw', 9: 'unexpected-record',
        10: 'wait-cpu-R', 11: 'resume-before-arm', 22: 'partial-record',
        23: 'duplicate-terminal', 24: 'active-budget', 25: 'missing-terminal-or-exit',
        26: 'child-stop', 27: 'monitor-gap', 28: 'post-core-cancel', 29: 'record-length',
    }
    if case['id'] in rules:
        return reason == rules[case['id']]
    metrics = {
        4: (0, 0, 1), 5: (0, 0, 2), 6: (0, 0, 1), 7: (0, 0, 1), 8: (0, 0, 1),
        12: (0, 0, 1), 13: (1, 1, 31), 14: (1, 1, 31), 16: (1, 0, 31),
        17: (1, 1, 31), 18: (0, 0, 1), 19: (0, 0, 1), 20: (0, 0, 1),
        21: (1, 0, 31), 30: (0, 0, 2), 31: (0, 0, 1), 32: (0, 0, 31),
    }
    if case['id'] == 15:
        return reason == 'active-budget' and owner.sign_entries == owner.aux_entries == 1
    terminal = owner.terminal
    return (reason == 'child-status:5' and terminal is not None and terminal['status'] == 5
            and (terminal['sign_entries'], terminal['auxiliary_calls'], terminal['review_calls']) == metrics.get(case['id']))


def save_artifacts(output, owner, eligible, met):
    # Bounded forensic artifact serialization after settlement; never live publication.
    for name, data in [('s-to-r.bin', owner.sent_raw), ('r-to-s.bin', owner.stdout_raw), ('stderr.bin', owner.stderr_raw)]:
        (output / name).write_bytes(data)
    if eligible:
        (output / 'candidate.envelope').write_bytes(owner.result)
    report = {'role': 'PRIVATE_HOST_CANARY_NO_LIVE_PUBLICATION', 'case': owner.case['name'],
              'case_expectation_met': met, 'private_candidate_eligible': eligible,
              'source_freeze_sha256': owner.freeze_sha, 'nonce': owner.nonce.hex(),
              'terminal': owner.terminal, 'driver_sign_entries_observed': owner.sign_entries,
              'auxiliary_entries_observed': owner.aux_entries, 'backend_counter_available': False,
              'reason': owner.reason, 'settled': owner.settled(), 'quarantined': owner.quarantined,
              'raw_wait': owner.raw_wait, 'exit_code': owner.exit_code,
              'wait_elapsed_ns': None if owner.wait_elapsed is None else str(owner.wait_elapsed),
              'candidate_sha256': sha(owner.result) if eligible else None,
              'trace': owner.trace.rows}
    data = json.dumps(report, indent=2).encode('ascii')
    require(len(data) <= TRACE_CAP, 'final-trace-cap')
    (output / 'result.json').write_bytes(data + b'\n')


def verify_artifact(args, freeze_sha):
    report = json.loads(bounded_file(args.artifact / 'result.json', TRACE_CAP), object_pairs_hook=unique)
    require(report['private_candidate_eligible'] is True and report['settled'] is True
            and report['source_freeze_sha256'] == freeze_sha, 'private-artifact-binding')
    frame = bounded_file(args.artifact / 'candidate.envelope', 947)
    require(sha(frame) == report['candidate_sha256'] and frame.startswith(b'nsealr1:'), 'candidate-hash')
    payload = frame[8:]
    require(payload and all(v in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for v in payload), 'base64url')
    decoded = base64.b64decode(payload + b'=' * (-len(payload) % 4), altchars=b'-_', validate=True)
    require(len(decoded) <= 704 and base64.urlsafe_b64encode(decoded).rstrip(b'=') == payload, 'canonical-envelope')
    # Separate post-settlement invocation: import only the existing independent oracle.
    path = ROOT / 'docs/restart/implementation/S03/oracle.py'
    spec = importlib.util.spec_from_file_location('hrt_existing_s03_oracle', path)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    bip = oracle.reference()
    expected = json.loads(bounded_file(ROOT / 'docs/restart/implementation/QP01/request-engine/expectations.json', 65_536))['independent_positive_expectations'][0]
    value = json.loads(decoded, object_pairs_hook=unique)
    if args.mutation != 'none':
        event = value['result']['event']
        if args.mutation == 'key': event['pubkey'] = '0' * 64
        elif args.mutation == 'template': event['content'] += '!'
        elif args.mutation == 'signature': event['sig'] = ('0' if event['sig'][0] != '0' else '1') + event['sig'][1:]
        elif args.mutation == 'id': event['id'] = '0' * 64
        elif args.mutation == 'request-id': value['request_id'] = 'other'
        decoded = json.dumps(value, separators=(',', ':')).encode() + (b'!' if args.mutation == 'trailing' else b'')
    try:
        value = json.loads(decoded, object_pairs_hook=unique)
        require(set(value) == {'version', 'request_id', 'ok', 'result'} and type(value['version']) is int and value['version'] == 2
                and value['ok'] is True and value['request_id'] == expected['request_id'], 'response-correlation')
        require(set(value['result']) == {'event'}, 'response-shape')
        event = value['result']['event']
        require(event == expected['expected_complete_event'], 'independent-preexisting-event-golden')
        template = {key: event[key] for key in ('created_at', 'kind', 'tags', 'content')}
        template = oracle.template(json.dumps(template, separators=(',', ':')).encode())
        digest = hashlib.sha256(oracle.canonical(template, event['pubkey'])).digest()
        require(digest.hex() == event['id'] and bip.schnorr_verify(digest, bytes.fromhex(event['pubkey']), bytes.fromhex(event['sig'])),
                'independent-signature')
    except (ValueError, KeyError, TypeError):
        require(args.mutation != 'none', 'independent-oracle-rejected-positive')
        print(json.dumps({'role': 'POST_CORE_ORACLE_NEGATIVE_ONLY', 'mutation': args.mutation, 'rejected': True}))
        return
    require(args.mutation == 'none', 'mutation-not-rejected')
    print(json.dumps({'role': 'POST_SETTLEMENT_INDEPENDENT_ORACLE_ONLY', 'verified': True, 'live_publication_qualified': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    run = modes.add_parser('run')
    run.add_argument('--binary', required=True)
    run.add_argument('--binary-sha256', required=True)
    run.add_argument('--origin-ns', required=True, type=int)
    run.add_argument('--case', required=True)
    run.add_argument('--output', required=True, type=Path)
    verify = modes.add_parser('verify')
    verify.add_argument('--artifact', required=True, type=Path)
    verify.add_argument('--mutation', choices=['none', 'key', 'template', 'signature', 'id', 'request-id', 'trailing'], default='none')
    args = parser.parse_args()
    _freeze, freeze_sha, cases, frames, raw = preflight()
    if args.mode == 'verify':
        verify_artifact(args, freeze_sha)
        return 0
    selected = [row for row in cases if row['name'] == args.case]
    require(len(selected) == 1, 'known-closed-case')
    require(args.output.is_absolute() and not args.output.exists() and not args.output.is_symlink(), 'new-absolute-output')
    args.output.mkdir(mode=0o700)
    owner = Supervisor(args, selected[0], frames, raw, freeze_sha)
    eligible = owner.run()
    met = expected_case(selected[0], owner, eligible)
    save_artifacts(args.output, owner, eligible, met)
    print(json.dumps({'case': args.case, 'expectation_met': met, 'private_candidate': eligible, 'output': str(args.output)}))
    return 0 if met else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Refusal, OSError, ValueError, KeyError) as error:
        print('HRT closed refusal: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
