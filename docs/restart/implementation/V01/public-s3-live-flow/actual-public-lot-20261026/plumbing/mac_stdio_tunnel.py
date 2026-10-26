#!/usr/bin/env python3
"""Root lab plumbing: reviewed Mac USB relay Unix stream <-> one SSH stdio."""
import argparse, datetime, json, os, pathlib, select, socket, subprocess, sys, time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mac-socket', required=True)
p.add_argument('--linux-socket', required=True)
p.add_argument('--linux-script', required=True)
p.add_argument('--linux-report', required=True)
p.add_argument('--report', required=True)
a = p.parse_args()
report = pathlib.Path(a.report); assert not report.exists()
for value in (a.linux_socket, a.linux_script, a.linux_report):
    assert value.startswith('/') and all(c.isalnum() or c in '/._-' for c in value)
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
argv = ['ssh', '-T', 'tux', 'python3', a.linux_script, '--socket', a.linux_socket, '--report', a.linux_report]
r = {'scope': 'one publicfixture raw SSH stdio tunnel only; no Nostr parsing or approval', 'started_utc': now(), 'argv': argv, 'usb_to_ssh': 0, 'ssh_to_usb': 0, 'reason': 'not-started'}
child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    conn.settimeout(1); conn.connect(a.mac_socket)
    r['mac_stream_opened'] = True
    os.set_blocking(child.stdin.fileno(), False); os.set_blocking(child.stdout.fileno(), False)
    until = time.monotonic() + 180; diagnostics = 0; readers = [conn, child.stdout, child.stderr]
    while time.monotonic() < until:
        ready, _, _ = select.select(readers, [], [], .05)
        if child.stderr in ready:
            data = os.read(child.stderr.fileno(), 1024)
            if not data: readers.remove(child.stderr)
            else:
                diagnostics += len(data)
                if diagnostics > 16384: raise ValueError('SSH diagnostic byte limit')
                sys.stderr.buffer.write(data); sys.stderr.buffer.flush()
        if conn in ready:
            data = conn.recv(1024)
            if not data: r['reason'] = 'Mac-relay-stream-EOF'; break
            r['usb_to_ssh'] += len(data)
            if r['usb_to_ssh'] > 65536: raise ValueError('USB to SSH byte limit')
            if not select.select([], [child.stdin], [], 1)[1] or os.write(child.stdin.fileno(), data) != len(data): raise OSError('SSH stdin write unavailable or partial; no retry')
        if child.stdout in ready:
            data = os.read(child.stdout.fileno(), 1024)
            if not data: r['reason'] = 'SSH-stdout-EOF'; break
            r['ssh_to_usb'] += len(data)
            if r['ssh_to_usb'] > 65536: raise ValueError('SSH to USB byte limit')
            conn.sendall(data)
    else: r['reason'] = 'plumbing-lease-expired'
except BaseException as error:
    r['reason'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    conn.close(); r['mac_stream_close_returned'] = True
    child.stdin.close()
    try: r['ssh_exit'] = child.wait(timeout=4)
    except subprocess.TimeoutExpired:
        child.terminate()
        try: r['ssh_exit'] = child.wait(timeout=4)
        except subprocess.TimeoutExpired: child.kill(); r['ssh_exit'] = child.wait()
    r['ended_utc'] = now()
    with report.open('x') as f: json.dump(r, f, indent=2); f.write('\n')
    print(json.dumps(r), flush=True)
