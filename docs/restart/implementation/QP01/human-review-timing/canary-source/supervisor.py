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
        if event != 'guard':
            row['at_ns'] = time.monotonic_ns()
        size = len(json.dumps(row, separators=(',', ':'), ensure_ascii=True).encode()) + 1
        require(self.bytes + size <= TRACE_CAP - 8192, 'trace-cap')
        self.bytes += size
        self.rows.append(row)
        return row


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
        self.wait_baseline_stats = None
        self.wait_baseline_event = None
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
        self.sink_commits = self.wait_acks_queued = self.resume_acks_queued = 0
        self.stdout_observed = self.stderr_observed = 0
        self.checkpoint_count = self.max_gap_ns = 0
        self.last_guard = self.guard_failure = self.retention = None
        self.invalidated_snapshot = self.evidence = None
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

    def fault(self, name, **witness):
        self.faults.add(name)
        self.trace.add('fault-injected', name=name, phase=self.phase, current=self.current, **witness)

    def ledger(self, now):
        active = self.active_accum + (now - self.active_started if self.phase == 'ACTIVE' else 0)
        return {'at_ns': now, 'phase': self.phase, 'active_accum_ns': self.active_accum,
                'active_started_ns': self.active_started, 'active_ns': active,
                'wait_cpu_ns': self.wait_cpu, 'charged_ns': active + self.wait_cpu,
                'remaining_ns': ACTIVE_NS - active - self.wait_cpu}

    def checkpoint(self, label='checkpoint', finalize_wait=False):
        started = time.monotonic_ns()
        previous = self.last_checkpoint
        if self.revoked:
            self.last_checkpoint = started
            return started
        stats, cpu_upper, observation_error = {}, {}, None
        try:
            for pid, original in self.identities.items():
                if pid == self.child.pid and self.raw_wait is not None:
                    continue
                value = process_stat(pid)
                stats[pid] = value  # Preserve even the identity/counter that fails.
                require(value['start'] == original['start'] and value['threads'] == 1, 'actor-identity-or-threads')
                expected = (self.child.pid,) if pid == os.getpid() and self.raw_wait is None else ()
                require(value['children'] == expected, 'unexpected-descendant')
            if self.phase == 'WAIT' or finalize_wait:
                require(self.child.pid in stats and self.wait_base is not None, 'wait-actor-lost')
                for pid, baseline in self.wait_base.items():
                    delta = stats[pid]['cpu'] - baseline
                    require(delta >= 0, 'cpu-counter-rollback')
                    cpu_upper[pid] = delta * 10_000_000 + QUANTIZATION_NS
                self.wait_cpu = sum(cpu_upper.values())
                require(cpu_upper[self.child.pid] <= CPU_R_NS, 'wait-cpu-R')
                require(cpu_upper[os.getpid()] <= CPU_S_NS, 'wait-cpu-S')
        except BaseException as error:
            observation_error = str(error)[:160]
        # Heavy trace preparation and the admitted delay occur BEFORE the final
        # clock sample. Placeholder sizes reserve all later scalar substitutions.
        record = (self.phase == 'WAIT' or finalize_wait or observation_error is not None
                  or label in ('wait-admission', 'resume-ready', 'queue-ack', 'retention'))
        row = None
        if record:
            try:
                row = self.trace.add('guard', label=label, started_ns=started, previous_ns=previous,
                                     phase=self.phase,
                                     raw_cpu=[stats.get(os.getpid(), {}).get('cpu'), stats.get(self.child.pid, {}).get('cpu')],
                                     baseline_event=self.wait_baseline_event,
                                     completed_ns=(1 << 64) - 1, active_ns=(1 << 64) - 1,
                                     charged_ns=(1 << 64) - 1, failure='?' * max(14, len(observation_error or '')))
            except Refusal as error:
                observation_error = str(error)
        if label == 'retention' and self.case['id'] == 27:
            self.fault('supervisor-gap-in-guard', started_ns=started)
            time.sleep(0.075)  # Real delay inside the final guard; never a frozen clock.
        completed = time.monotonic_ns()  # Includes /proc, accounting and trace work.
        charge = self.ledger(completed)
        gap = completed - previous
        failure = ('clock-rollback' if completed < started or started < previous else
                   'monitor-gap' if gap > GAP_NS else
                   'deadline' if completed >= self.deadline else observation_error or
                   ('active-budget' if charge['charged_ns'] > ACTIVE_NS else None))
        if row is not None:
            row.update(completed_ns=completed, active_ns=charge['active_ns'],
                       charged_ns=charge['charged_ns'], failure=failure)
        elif failure is not None:
            # This path already fails: emitting its telemetry cannot enable an ACK.
            row = self.trace.add('guard', label=label, started_ns=started, previous_ns=previous,
                                 phase=self.phase, completed_ns=completed,
                                 raw_cpu=[stats.get(os.getpid(), {}).get('cpu'), stats.get(self.child.pid, {}).get('cpu')],
                                 baseline_event=self.wait_baseline_event,
                                 active_ns=charge['active_ns'], charged_ns=charge['charged_ns'], failure=failure)
        self.checkpoint_count += 1
        self.max_gap_ns = max(self.max_gap_ns, gap)
        self.last_guard = {'label': label, 'started_ns': started, 'completed_ns': completed,
                           'previous_ns': previous, 'gap_ns': gap, 'ledger': charge,
                           'failure': failure, 'raw_cpu': {str(pid): value['cpu'] for pid, value in stats.items()},
                           'baseline_cpu': self.wait_base, 'upper_cpu': cpu_upper}
        if failure is not None:
            self.guard_failure = self.last_guard
            raise Refusal(failure)
        self.last_checkpoint = completed
        return completed

    def queue(self, opcode, invocation, epoch, payload=b'', nonce=None):
        self.checkpoint('queue-ack' if opcode in (WAIT_ACK, RESUME_ACK) else 'queue')
        require(not self.revoked and not self.stdin_closed, 'queue-after-revoke')
        require(self.pending_records < 2 and self.sequence_out < 4096, 'outgoing-record-cap')
        body = HEADER.pack(b'HRT1', self.sequence_out + 1, opcode, self.nonce if nonce is None else nonce,
                           invocation, epoch) + payload
        require(HEADER.size <= len(body) <= MAX_RECORD - 4, 'record-length')
        require(len(self.sent_raw) + len(self.pending) + 4 + len(body) <= STREAM_CAP - 64, 'stdin-stream-cap')
        self.sequence_out += 1
        self.pending.extend(PREFIX.pack(len(body)) + body)
        self.pending_records += 1
        if opcode == WAIT_ACK:
            self.wait_acks_queued += 1
        elif opcode == RESUME_ACK:
            self.resume_acks_queued += 1
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
        if self.case['id'] == 3:
            self.fault('partial-draw', invocation=self.current[0], index=self.current[3])
            raise Refusal('partial-draw')
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
        self.sink_commits += 1
        self.trace.add('sink-commit', invocation=self.current[0], epoch=self.current[1],
                       index=frame['index'], cells=len(cells), sha256=receipt)

    def resume(self, invocation, epoch, action, serial, cycle=7, nonce=None):
        require(self.phase == 'ACTIVE' and self.resume_armed and self.sink_committed, 'resume-before-arm')
        self.checkpoint()
        self.queue(RESUME_ACK, invocation, epoch, struct.pack('>BIB', action, serial, cycle), nonce)
        self.trace.add('resume-queued', invocation=invocation, epoch=epoch, serial=serial, action=action)

    def acknowledge_cycle(self):
        now = self.checkpoint('resume-start')
        if self.phase == 'WAIT':
            self.active_started = now
            self.phase = 'ACTIVE'
            self.wait_elapsed = now - self.wait_started
            self.trace.add('phase-wait-to-active', ns=now, wait_started_ns=self.wait_started,
                           active_accum_ns=self.active_accum, wait_elapsed_ns=self.wait_elapsed)
            # Sample again after the transition. This final WAIT-CPU upper bound
            # conservatively overlaps newly charged ACTIVE work; no ACK yet.
            self.checkpoint('resume-final', finalize_wait=True)
        self.resume_armed = True
        self.checkpoint('resume-ready')
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
                self.wait_baseline_stats = {pid: process_stat(pid) for pid in self.identities}
                self.wait_base = {pid: value['cpu'] for pid, value in self.wait_baseline_stats.items()}
                baseline_row = self.trace.add('cpu-baseline', raw=self.wait_baseline_stats)
                self.wait_baseline_event = baseline_row['i']
                now = self.checkpoint('wait-admission')
                self.active_accum += now - self.active_started
                self.wait_started = now
                self.wait_used = True
                self.phase = 'WAIT'
                self.trace.add('phase-active-to-wait', ns=now, active_started_ns=self.active_started,
                               active_accum_ns=self.active_accum, baseline_cpu=self.wait_base)
                self.queue(WAIT_ACK, invocation, epoch)
                self.trace.add('wait-ack-queued', ns=str(now), invocation=invocation, epoch=epoch)
            else:
                self.acknowledge_cycle()
        elif opcode == WAIT_READY:
            require(self.phase == 'WAIT' and self.current is not None and (invocation, epoch) == self.current[:2]
                    and not self.wait_ready and payload == b'', 'unexpected-record')
            self.wait_ready = True
            self.trace.add('wait-ready', invocation=invocation, epoch=epoch)
            if self.case['id'] == 11:
                self.fault('resume-before-arm')
                self.resume(invocation, epoch, 0, 1)
            elif self.case['id'] == 26:
                self.fault('child-stop')
                signal.pidfd_send_signal(self.pidfd, signal.SIGSTOP)
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
                self.fault('post-core-cancel', result_bytes=len(payload), result_sha256=sha(payload))
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
        if name == 'stdout':
            self.stdout_observed += len(value)
        else:
            self.stderr_observed += len(value)
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
        self.invalidated_snapshot = {'phase': self.phase, 'current': self.current,
                                     'sink_committed': self.sink_committed, 'sink_commits': self.sink_commits,
                                     'wait_used': self.wait_used, 'wait_ready': self.wait_ready,
                                     'resume_armed': self.resume_armed, 'wait_acks_queued': self.wait_acks_queued,
                                     'resume_acks_queued': self.resume_acks_queued,
                                     'ledger': self.ledger(self.invalidated)}
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
                        stopped = process_stat(self.child.pid)
                        if stopped['state'] in ('T', 't'):
                            self.trace.add('actual-child-stopped', raw=stopped)
                            raise Refusal('child-stop')
                    elif self.case['id'] not in (2, 10, 12):
                        delay = WAIT_NS if self.case['id'] in (0, 27) else 0
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
        # Bounded in-memory reconstruction after wait/EOF; it can recover count
        # evidence after revocation but can never restore result authority.
        try:
            if not self.revoked:
                self.checkpoint('forensic-before')
            self.evidence = reconstruct_evidence(self)
            if not self.revoked:
                self.checkpoint('forensic-after')
                require(self.exit_code == 0 and self.terminal is not None and self.terminal['status'] == 0,
                        'missing-terminal-or-exit')
                require(self.result is not None and self.terminal['sign_entries'] == self.terminal['auxiliary_calls'] == 1,
                        'missing-private-result')
                require(self.wait_elapsed is not None and self.wait_elapsed >= WAIT_NS, 'real-wait-too-short')
                # Existing case27 now delays this actual last guard, after /proc.
                self.checkpoint('retention')
                require(self.case['id'] == 0, 'negative-produced-candidate')
                retained = time.monotonic_ns()
                final = self.ledger(retained)
                require(retained >= self.last_checkpoint and retained - self.last_checkpoint <= GAP_NS, 'monitor-gap')
                require(retained < self.deadline, 'deadline')
                require(final['charged_ns'] <= ACTIVE_NS, 'active-budget')
                self.retention = final  # No IO/callback/await after the fresh seal check.
                self.trace.add('private-retention', **final)
        except BaseException as error:
            self.revoke(str(error)[:160])
        if self.evidence is None:
            self.evidence = reconstruct_evidence(self)
        self.selected.close()
        if self.pidfd is not None:
            os.close(self.pidfd)
        return not self.revoked


def capture_records(raw, observed, nonce, direction):
    """Read only bounded captured bytes; no live protocol transition is applied."""
    result = {'complete': observed == len(raw), 'records': 0, 'present_count': 0,
              'wait_ready': 0, 'wait_acks': 0, 'resume_acks': 0,
              'resume_first': None, 'resume_last': None,
              'sign_markers': 0, 'aux_markers': 0, 'terminal': None,
              'result': None, 'partial': None, 'error': None, 'init': None}
    offset = sequence = 0
    allowed = {PRESENT, WAIT_READY, RESULT, TERMINAL, SIGN_ENTRY, AUX_ENTRY} if direction == 'R' else {INIT, WAIT_ACK, RESUME_ACK, CANCEL}
    try:
        while offset < len(raw):
            require(result['records'] < 4096 and len(raw) - offset >= 4, 'capture-prefix')
            length = PREFIX.unpack(raw[offset:offset+4])[0]
            require(HEADER.size <= length <= MAX_RECORD - 4, 'capture-length')
            body = raw[offset+4:offset+4+length]
            if len(body) < length:
                result['partial'] = {'declared': length, 'available': len(body)}
                if len(body) >= HEADER.size:
                    magic, seq, opcode, incarnation, inv, epoch = HEADER.unpack(body[:HEADER.size])
                    require(magic == b'HRT1' and incarnation == nonce and seq == sequence + 1, 'capture-partial-envelope')
                    result['partial'].update(opcode=opcode, invocation=inv, epoch=epoch)
                raise Refusal('capture-truncated')
            magic, seq, opcode, incarnation, inv, epoch = HEADER.unpack(body[:HEADER.size])
            require(magic == b'HRT1' and incarnation == nonce and seq == sequence + 1 and opcode in allowed, 'capture-envelope')
            payload = body[HEADER.size:]
            sequence = seq
            result['records'] += 1
            require(result['terminal'] is None, 'capture-after-terminal')
            if opcode == INIT:
                require(direction == 'S' and inv == epoch == 0 and result['init'] is None and len(payload) == 279, 'capture-init')
                origin, deadline, case_id, raw_length = struct.unpack('>QQHH', payload[:20])
                require(raw_length == 259 and sha(payload[20:]) == RAW_SHA, 'capture-original-input')
                result['init'] = {'origin_ns': origin, 'deadline_ns': deadline, 'case_id': case_id, 'raw_sha256': RAW_SHA}
            elif opcode == PRESENT:
                result['present_count'] += 1
            elif opcode == WAIT_READY:
                require(payload == b'', 'capture-wait-ready')
                result['wait_ready'] += 1
            elif opcode == WAIT_ACK:
                require(payload == b'', 'capture-wait-ack')
                result['wait_acks'] += 1
            elif opcode == RESUME_ACK:
                require(len(payload) == 6, 'capture-resume-shape')
                action, serial, cycle = struct.unpack('>BIB', payload)
                ack = dict(invocation=inv, epoch=epoch, action=action, serial=serial, cycle=cycle)
                result['resume_first'] = result['resume_first'] or ack
                result['resume_last'] = ack
                result['resume_acks'] += 1
            elif opcode in (SIGN_ENTRY, AUX_ENTRY):
                require(inv == epoch == 0 and len(payload) == 4 and struct.unpack('>I', payload)[0] == 1, 'capture-marker')
                field = 'sign_markers' if opcode == SIGN_ENTRY else 'aux_markers'
                result[field] += 1
                require(result[field] == 1 and (opcode == SIGN_ENTRY or result['sign_markers'] == 1), 'capture-marker-order')
            elif opcode == RESULT:
                require(inv == epoch == 0 and result['result'] is None and 1 <= len(payload) <= 947, 'capture-result')
                result['result'] = {'bytes': len(payload), 'sha256': sha(payload)}
            elif opcode == TERMINAL:
                require(inv == epoch == 0 and len(payload) == 12, 'capture-terminal')
                status, sign_count, aux_count, reviews = struct.unpack('>HIIH', payload)
                require(sign_count <= 1 and aux_count <= 1 and reviews <= 1024, 'capture-terminal-counts')
                require(sign_count == result['sign_markers'] and aux_count == result['aux_markers'], 'capture-terminal-consistency')
                require(reviews == result['present_count'], 'capture-review-count')
                result['terminal'] = dict(status=status, sign_entries=sign_count, auxiliary_calls=aux_count, review_calls=reviews)
            offset += 4 + length
    except (Refusal, ValueError, struct.error) as error:
        result['complete'], result['error'] = False, str(error)
    return result


def reconstruct_evidence(owner):
    received = capture_records(bytes(owner.stdout_raw), owner.stdout_observed, owner.nonce, 'R')
    sent = capture_records(bytes(owner.sent_raw), len(owner.sent_raw), owner.nonce, 'S')
    counts = {'availability': 'unavailable', 'sign_attempts': None, 'auxiliary_calls': None}
    if owner.settled() and owner.stderr_observed == 0 and received['complete']:
        terminal = received['terminal']
        if terminal is not None:
            counts = {'availability': 'complete-terminal', 'sign_attempts': terminal['sign_entries'],
                      'auxiliary_calls': terminal['auxiliary_calls']}
        elif received['sign_markers'] == received['aux_markers'] == 0 and received['result'] is None:
            # In this exact source SIGN_ENTRY write_all+flush MUST finish before
            # the public sign call; auxiliary can only be reached through it.
            # Thus a truly complete EOF/wait capture with no marker proves zero.
            counts = {'availability': 'source-write-before-sign-barrier', 'sign_attempts': 0, 'auxiliary_calls': 0}
    init_bound = sent['init'] == {'origin_ns': owner.origin, 'deadline_ns': owner.deadline,
                                 'case_id': owner.case['id'], 'raw_sha256': RAW_SHA}
    return {'received': received, 'sent': sent, 'counts': counts, 'init_bound': init_bound,
            'presence_is_only_attempt_witness_without_terminal': True}


def expected_case(case, owner, eligible):
    """Only the finite15-case first tranche is graded; other selectors stay RED."""
    first = {0, 1, 2, 3, 4, 10, 11, 12, 13, 16, 21, 22, 26, 27, 28}
    if case['id'] not in first or not owner.settled() or owner.quarantined or owner.evidence is None:
        return False
    e, snap = owner.evidence, owner.invalidated_snapshot
    incoming, sent, counts = e['received'], e['sent'], e['counts']
    if not e['init_bound']:
        return False
    terminal = incoming['terminal']
    count_available = counts['availability'] in ('complete-terminal', 'source-write-before-sign-barrier')
    zero = count_available and counts['sign_attempts'] == counts['auxiliary_calls'] == 0
    no_resume = sent['complete'] and sent['resume_acks'] == owner.resume_acks_queued == 0
    first_wait = (snap is not None and snap['phase'] == 'WAIT' and snap['current'] == (1, 1, 0, 0)
                  and incoming['wait_ready'] == 1 and sent['wait_acks'] == 1 and snap['wait_ready'])
    full_review = (incoming['present_count'] == 31 and owner.last_index == 30
                   and sent['complete'] and sent['resume_acks'] == owner.resume_acks_queued == 31)
    complete_one = (counts['availability'] == 'complete-terminal' and counts['sign_attempts'] == counts['auxiliary_calls'] == 1
                    and terminal is not None and terminal['review_calls'] == 31)
    events = owner.trace.rows
    fault_names = {row.get('name') for row in events if row['event'] == 'fault-injected'}
    if case['id'] == 0:
        seal = owner.retention
        return (eligible and not owner.revoked and full_review and complete_one and terminal['status'] == 0
                and owner.wait_elapsed is not None and owner.wait_elapsed >= WAIT_NS
                and seal is not None and seal['charged_ns'] <= ACTIVE_NS and seal['at_ns'] < owner.deadline
                and owner.guard_failure is None and owner.max_gap_ns <= GAP_NS)
    if eligible or not owner.revoked or snap is None:
        return False
    reason = owner.reason
    if case['id'] == 1:
        return reason == 'cancel-wait' and first_wait and no_resume and zero and 'cancel-wait' in fault_names
    if case['id'] == 2:
        failure = owner.guard_failure
        return (reason in ('deadline', 'startup:deadline') and no_resume and zero
                and owner.deadline == owner.origin + 100_000_000
                and failure is not None and failure['failure'] == 'deadline' and failure['completed_ns'] >= owner.deadline)
    if case['id'] == 3:
        return (reason == 'partial-draw' and 'partial-draw' in fault_names and no_resume and zero
                and incoming['present_count'] == 1 and snap['sink_commits'] == 0
                and not snap['sink_committed'] and not snap['wait_used'] and sent['wait_acks'] == 0)
    if case['id'] == 4:
        ack = sent['resume_first']
        return (reason == 'child-status:5' and zero and incoming['present_count'] == 1
                and terminal is not None and terminal['status'] == 5 and sent['complete']
                and sent['resume_acks'] == 1 and ack is not None and ack['invocation'] == 1 and ack['epoch'] == 0
                and 'stale-epoch' in fault_names)
    if case['id'] == 10:
        failed = owner.guard_failure
        return (reason == 'wait-cpu-R' and first_wait and no_resume and zero and failed is not None
                and failed['upper_cpu'].get(owner.child.pid, 0) > CPU_R_NS
                and str(owner.child.pid) in failed['raw_cpu'] and failed['baseline_cpu'] is not None)
    if case['id'] == 11:
        return reason == 'resume-before-arm' and first_wait and no_resume and zero and 'resume-before-arm' in fault_names and not snap['resume_armed']
    if case['id'] == 12:
        return reason == 'child-status:5' and first_wait and no_resume and zero and terminal is not None and terminal['status'] == 5 and terminal['review_calls'] == 1
    if case['id'] in (13, 16, 21):
        aux = 1 if case['id'] == 13 else 0
        return (reason == 'child-status:5' and full_review and counts['availability'] == 'complete-terminal'
                and terminal is not None and terminal['status'] == 5
                and counts['sign_attempts'] == 1 and counts['auxiliary_calls'] == aux)
    if case['id'] == 22:
        partial = incoming['partial']
        return (reason == 'partial-record' and full_review and counts['availability'] == 'unavailable'
                and incoming['sign_markers'] == incoming['aux_markers'] == 1
                and partial is not None and partial.get('opcode') == RESULT
                and partial.get('invocation') == partial.get('epoch') == 0
                and partial['available'] < partial['declared'] and owner.exit_code == 0)
    if case['id'] == 26:
        stopped = any(row['event'] == 'actual-child-stopped' and row['raw']['state'] in ('T', 't') for row in events)
        return reason == 'child-stop' and first_wait and no_resume and zero and stopped and 'child-stop' in fault_names and owner.exit_code == -signal.SIGKILL
    if case['id'] == 27:
        failed = owner.guard_failure
        return (reason == 'monitor-gap' and full_review and complete_one and terminal['status'] == 0
                and 'supervisor-gap-in-guard' in fault_names and failed is not None and failed['label'] == 'retention'
                and failed['completed_ns'] - failed['started_ns'] >= 75_000_000
                and failed['gap_ns'] > GAP_NS and owner.retention is None)
    if case['id'] == 28:
        observed = incoming['result']
        witness = [row for row in events if row['event'] == 'fault-injected' and row.get('name') == 'post-core-cancel']
        return (reason == 'post-core-cancel' and full_review and complete_one and observed is not None and len(witness) == 1
                and witness[0]['result_sha256'] == observed['sha256'] and witness[0]['result_bytes'] == observed['bytes'])
    return False


def save_artifacts(output, owner, eligible, met):
    # Bounded forensic artifact serialization after settlement; never live publication.
    for name, data in [('s-to-r.bin', owner.sent_raw), ('r-to-s.bin', owner.stdout_raw), ('stderr.bin', owner.stderr_raw)]:
        (output / name).write_bytes(data)
    if eligible:
        (output / 'candidate.envelope').write_bytes(owner.result)
    report = {'role': 'PRIVATE_HOST_CANARY_NO_LIVE_PUBLICATION', 'case': owner.case['name'],
              'case_expectation_met': met, 'private_candidate_eligible': eligible,
              'source_freeze_sha256': owner.freeze_sha, 'nonce': owner.nonce.hex(),
              'terminal': owner.terminal, 'live_sign_entry_markers': owner.sign_entries,
              'live_aux_entry_markers': owner.aux_entries, 'backend_counter_available': False,
              'reason': owner.reason, 'settled': owner.settled(), 'quarantined': owner.quarantined,
              'raw_wait': owner.raw_wait, 'exit_code': owner.exit_code,
              'wait_elapsed_ns': None if owner.wait_elapsed is None else str(owner.wait_elapsed),
              'origin_ns': owner.origin, 'absolute_deadline_ns': owner.deadline,
              'actor_identities': owner.identities, 'cpu_baseline_stats': owner.wait_baseline_stats,
              'checkpoint_count': owner.checkpoint_count, 'max_checkpoint_gap_ns': owner.max_gap_ns,
              'guard_failure': owner.guard_failure, 'last_guard': owner.last_guard,
              'invalidation_snapshot': owner.invalidated_snapshot, 'private_retention': owner.retention,
              'evidence': owner.evidence, 'stdout_observed': owner.stdout_observed,
              'stderr_observed': owner.stderr_observed,
              'candidate_sha256': sha(owner.result) if eligible else None,
              'trace': owner.trace.rows}
    data = json.dumps(report, separators=(',', ':'), ensure_ascii=True).encode('ascii')
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
