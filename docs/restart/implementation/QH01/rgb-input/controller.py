"""Fixed-six RGB experiment; minimal source copy of verified5fa supervision."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = HERE.parent / 'linux-worker-experiment/experiment.py'
if hashlib.sha256(OLD.read_bytes()).hexdigest() != '97fa6da85a1f83c5535050f6c77c588800a069a26ed9a7cd7470f616352a76eb':
    raise RuntimeError('corrected06d source mismatch; no alternate controller')
spec = importlib.util.spec_from_file_location('qh01_corrected_supervisor', OLD)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
P = json.loads((HERE / 'parameters.json').read_text())['baseline']
if P != base.P:
    raise RuntimeError('baseline changed')
CASES = json.loads((HERE / 'expectations.json').read_text())['cases']
BINARY = HERE / '.runtime/target/release/nsealr-qh01-rust-qr-worker'


def supervise(case, owner, directory, *, image_bytes=None, binary=BINARY):
    record = {'id': case['id'], 'expected': case['expected'], 'events': [], 'eligible': False,
              'control_bytes': 0, 'image_bytes': 0, 'owner_wait': None, 'signals': [], 'actual_QR_decode': True}
    start = time.monotonic()
    deadline = start + P['wall_eligibility_deadline']
    initial = base.open_fds()
    if not owner.acquire():
        raise RuntimeError('owner unavailable')
    record['owner_generation'] = owner.generation
    image = (ROOT / case['image_path']).read_bytes() if image_bytes is None else image_bytes
    record['input_in_memory'] = image_bytes is not None
    record['input_sha256'] = base.digest(image)
    expected = (ROOT / case['expected_path']).read_bytes() if case.get('expected_path') else None
    if len(image) != 172800 or len(image) > P['raw_input_bytes'] or 240 > P['maximum_width'] or 240 > P['maximum_height'] or 240 * 240 > P['maximum_pixels']:
        raise RuntimeError('fixed input relation/bounds failed before spawn')
    if base.digest(image) != case['image_sha256'] or (expected is not None and base.digest(expected) != case['expected_sha256']):
        raise RuntimeError('immutable fixture mismatch')
    selector = selectors.DefaultSelector()
    fds = set()
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    totals = {'stdout': 0, 'stderr': 0}
    eof = set()
    pid = None
    collected = False
    lost_status = False
    ready = False
    session = False
    sent_signal = False
    error = None
    cleanup_deadline = None
    input_fd = None
    maxread = maxwrite = 0
    def event(name, **fields):
        record['events'].append({'event': name, 't': time.monotonic() - start, **fields})
    def second_refusal(where):
        if owner.acquire():
            raise RuntimeError('second owner acquired')
        record.setdefault('second_refusals', []).append(where)
    def close(fd):
        if fd in fds:
            try:
                selector.unregister(fd)
            except KeyError:
                pass
            os.close(fd)
            fds.remove(fd)
    def stop(reason):
        nonlocal error, cleanup_deadline
        if error is None:
            error = reason
            cleanup_deadline = time.monotonic() + P['cleanup_observation_window']
            event('invalidated', reason=reason)
        if input_fd is not None:
            close(input_fd)
    def kill_owned():
        nonlocal sent_signal
        if pid is None or collected or lost_status or sent_signal:
            return
        if pid <= 1 or pid in (os.getpid(), os.getpgrp()) or record.get('pid') != pid:
            raise RuntimeError('unowned signal target')
        try:
            os.kill(pid, signal.SIGKILL)
            record['signals'].append({'pid': pid, 'signal': 9})
        except ProcessLookupError:
            event('signal-ESRCH-await-status')
        sent_signal = True
    try:
        pipes = [os.pipe2(os.O_CLOEXEC) for _ in range(3)]
        for pair in pipes:
            fds.update(pair)
        child_in, input_fd = pipes[0]
        outfd, child_out = pipes[1]
        errfd, child_err = pipes[2]
        actions = [(os.POSIX_SPAWN_DUP2, child_in, 0), (os.POSIX_SPAWN_DUP2, child_out, 1), (os.POSIX_SPAWN_DUP2, child_err, 2)]
        inherited = {fd for fd in initial if fd > 2 and os.get_inheritable(fd)}
        actions += [(os.POSIX_SPAWN_CLOSE, fd) for fd in sorted(fds | inherited)]
        record['argv'] = [str(binary)]
        event('spawn-begin')
        pid = os.posix_spawn(str(binary), record['argv'], base.CHILD_ENV, file_actions=actions,
                             setsigmask=(), setsigdef=(signal.SIGPIPE, signal.SIGXCPU, signal.SIGTERM))
        record['pid'] = pid
        record['initial_kernel_identity'] = {'sid': os.getsid(pid), 'pgid': os.getpgid(pid)}
        event('spawn-return', pid=pid)
        for fd in (child_in, child_out, child_err):
            close(fd)
        for fd, name in [(outfd, 'stdout'), (errfd, 'stderr')]:
            os.set_blocking(fd, False)
            selector.register(fd, selectors.EVENT_READ, name)
        os.set_blocking(input_fd, False)
        second_refusal('live-child')
        record['session_polls'] = 0
        while True:
            now = time.monotonic()
            if error is None and now >= deadline:
                stop('wall')
            if error:
                kill_owned()
                if now >= cleanup_deadline:
                    break
            if not collected:
                try:
                    waited = base.raw_wait(pid)
                except ChildProcessError:
                    lost_status = True
                    stop('unknown-status')
                    break
                if waited:
                    collected = True
                    record['owner_wait'] = waited
                    event('actual-wait', status=waited['raw_status'])
                    second_refusal('status-before-IO-settlement')
            if not ready and error is None and not collected:
                sid, pgid = os.getsid(pid), os.getpgid(pid)
                record['session_polls'] += 1
                record['kernel_identity'] = {'pid': pid, 'sid': sid, 'pgid': pgid}
                if sid == pid and pgid == pid and pid > 1 and pid != os.getpgrp():
                    session = True
                    event('kernel-session-established', pid=pid, sid=sid, pgid=pgid)
                    vm = next(int(line.split()[1]) * 1024 for line in Path(f'/proc/{pid}/status').read_text().splitlines() if line.startswith('VmSize:'))
                    record['bootstrap_VmSize_bytes'] = vm
                    if vm >= P['worker_AS_bytes']:
                        stop('impossible-bootstrap-AS')
                    else:
                        policy = {}
                        for key, limits in base.LIMITS.items():
                            old = resource.prlimit(pid, key, limits)
                            actual = resource.prlimit(pid, key)
                            policy[str(key)] = {'previous': old, 'requested': limits, 'readback': actual}
                            if actual != limits:
                                raise RuntimeError('prlimit readback mismatch')
                        record['policy'] = policy
                        event('policy-readback-before-G')
                        ready = True
                        selector.register(input_fd, selectors.EVENT_WRITE, 'stdin')
            if collected and eof == {'stdout', 'stderr'}:
                break
            for key, _mask in selector.select(0.01):
                fd, name = key.fd, key.data
                if fd not in fds:
                    continue
                if name == 'stdin':
                    if not ready or not session or (os.getsid(pid), os.getpgid(pid)) != (pid, pid):
                        raise RuntimeError('session/policy not current before write')
                    record['identity_checks_before_writes'] = record.get('identity_checks_before_writes', 0) + 1
                    block = memoryview(b'G') if record['control_bytes'] == 0 else memoryview(image)[record['image_bytes']:record['image_bytes'] + P['fixed_IO_chunk_bytes']]
                    if not block:
                        close(fd)
                        continue
                    try:
                        sent = os.write(fd, block)
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        stop('input-broken')
                        continue
                    maxwrite = max(maxwrite, len(block))
                    if record['control_bytes'] == 0:
                        record['control_bytes'] = sent
                        event('G-sent')
                    else:
                        if record['image_bytes'] == 0:
                            event('first-image-write')
                        record['image_bytes'] += sent
                    if record['image_bytes'] == len(image):
                        close(fd)
                else:
                    cap = P[name + '_bytes']
                    count = min(P['fixed_IO_chunk_bytes'], max(1, cap - len(streams[name]) + 1))
                    try:
                        block = os.read(fd, count)
                    except BlockingIOError:
                        continue
                    maxread = max(maxread, len(block))
                    if not block:
                        close(fd)
                        eof.add(name)
                        continue
                    totals[name] += len(block)
                    remaining = cap - len(streams[name])
                    streams[name].extend(block[:remaining])
                    if len(block) > remaining:
                        stop(name + '-parent-overflow')
    except BaseException as exc:
        record['harness_error'] = {'type': type(exc).__name__, 'message': str(exc)}
        stop('harness-error')
    finally:
        if pid is not None and not collected and not lost_status:
            kill_owned()
            until = cleanup_deadline if cleanup_deadline is not None else time.monotonic() + P['cleanup_observation_window']
            while time.monotonic() < until:
                try:
                    waited = base.raw_wait(pid)
                except ChildProcessError:
                    lost_status = True
                    break
                if waited:
                    collected = True
                    record['owner_wait'] = waited
                    break
                time.sleep(0.01)
        for fd in list(fds):
            close(fd)
        selector.close()
        known = collected and not lost_status and base.open_fds() == initial
        owner.settle(known)
        record.update(actual_status_acquired=collected and not lost_status, parent_FDs_restored=base.open_fds() == initial,
                      owner_quarantined=owner.quarantined, callbacks_settled=True)
        event('settled', known=known)
    out, err = bytes(streams['stdout']), bytes(streams['stderr'])
    waited = record['owner_wait']
    common = error is None and record['control_bytes'] == 1 and record['image_bytes'] == 172800 and ready and session and known and not owner.busy and not owner.quarantined
    admission_now = None
    if case['expected'] == 'exact':
        accepted = common and out == expected and waited['exitcode'] == 0 and b'status=decoded ' in err and (admission_now := time.monotonic()) < deadline
        record['eligible'] = accepted
    elif case['expected'] == 'output-overflow':
        accepted = common and out == b'' and waited['exitcode'] == 42 and b'status=output_overflow ' in err and b'limit=512' in err and (admission_now := time.monotonic()) < deadline
    else:
        accepted = common and out == b'' and waited['exitcode'] == 20 and b'status=no_qr grids=0' in err and (admission_now := time.monotonic()) < deadline
    record.update(boundary=error or case['expected'], stdout_observed=totals['stdout'], stderr_observed=totals['stderr'],
                  stdout_retained=len(out), stderr_retained=len(err), max_read_chunk=maxread, max_write_chunk=maxwrite,
                  admission_elapsed_seconds=None if admission_now is None else admission_now-start, duration_seconds=time.monotonic()-start)
    record['checks'] = {'intended_decode_outcome': accepted, 'actual_status_IO_cleanup': known,
                        'bounded_streams_chunks': len(out) <= 512 and len(err) <= 512 and maxread <= 4096 and maxwrite <= 4096,
                        'second_owner_refused': len(record.get('second_refusals', [])) == 2}
    record['passed'] = all(record['checks'].values())
    for name, data in streams.items():
        (directory / (case['id'] + '.' + name + '.bin')).write_bytes(data)
    base.json_write(directory / (case['id'] + '.json'), record)
    return record


def tint_input():
    metadata = json.loads((HERE / 'expectations.json').read_text())['metamorphism']
    original = (ROOT / metadata['source_path']).read_bytes()
    if base.digest(original) != metadata['source_sha256'] or len(original) != 172800:
        raise RuntimeError('original tint source mismatch')
    result = bytearray()
    for at in range(0, len(original), 3):
        pixel = original[at:at + 3]
        if pixel == bytes((0, 0, 0)):
            result.extend((0, 16, 0))
        elif pixel == bytes((255, 255, 255)):
            result.extend((240, 255, 255))
        else:
            raise RuntimeError('unadmitted original pixel; no transformation fallback')
    data = bytes(result)
    if len(data) != metadata['derived_bytes'] or base.digest(data) != metadata['derived_sha256']:
        raise RuntimeError('independent derived hash mismatch')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--case', choices=[c['id'] for c in CASES])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    environment = base.context()
    environment.update(binary_path=str(BINARY), binary_sha256=base.digest(BINARY.read_bytes()),
                       controller_sha256=base.digest(Path(__file__).read_bytes()), source_controller_06d_sha256=base.digest(OLD.read_bytes()))
    base.json_write(args.out/'environment.json', environment)
    owner = base.Owner()
    before_fds = base.open_fds()
    before_identity = [os.getsid(0), os.getpgrp()]
    before_limits = {str(k): resource.getrlimit(k) for k in base.LIMITS}
    records = []
    cases = [c for c in CASES if not args.case or c['id'] == args.case]
    for case in cases:
        image = tint_input() if case.get("derived_in_memory") else None
        record = supervise(case, owner, args.out, image_bytes=image, binary=BINARY)
        records.append(record)
        print(case['id'], 'PASS' if record['passed'] else 'NOT_EXERCISED', record['boundary'], flush=True)
        if not record['passed']:
            break
    status = dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    summary = {'cases': [{'id': r['id'], 'passed': r['passed']} for r in records], 'not_exercised': [c['id'] for c in cases[len(records):]],
               'all_created_PIDs_collected': all(r['actual_status_acquired'] for r in records),
               'FDs_equal_initial': base.open_fds()==before_fds, 'parent_identity_unchanged': [os.getsid(0),os.getpgrp()]==before_identity,
               'parent_limits_unchanged': {str(k):resource.getrlimit(k) for k in base.LIMITS}==before_limits, 'actual_final_threads':int(status['Threads']),
               'owned_PIDs':[r.get('pid') for r in records], 'actual_QR_decode':True, 'no_keys_or_signing':True}
    summary['passed'] = len(records)==len(cases) and all(r['passed'] for r in records) and all(summary[k] for k in ['all_created_PIDs_collected','FDs_equal_initial','parent_identity_unchanged','parent_limits_unchanged']) and summary['actual_final_threads']==1
    base.json_write(args.out/'summary.json',summary)
    return 0 if summary['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
