#!/usr/bin/env python3
"""Root lab plumbing: one tux-owned Unix connection over this SSH stdio."""
import argparse, datetime, json, os, pathlib, select, socket, sys, time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--socket', required=True)
p.add_argument('--report', required=True)
a = p.parse_args()
endpoint = pathlib.Path(a.socket)
report_path = pathlib.Path(a.report)
assert endpoint.is_absolute() and endpoint.name.startswith('nsealr-s3-public-') and endpoint.suffix == '.sock'
assert not endpoint.exists() and not endpoint.is_symlink() and not report_path.exists()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
r = {'scope': 'one publicfixture raw Unix/SSH stdio connection only', 'started_utc': now(), 'uid': os.getuid(), 'socket_to_ssh': 0, 'ssh_to_socket': 0, 'reason': 'not-started'}
listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
owned = None
try:
    listener.bind(str(endpoint)); os.chmod(endpoint, 0o600); owned = endpoint.lstat()
    listener.listen(1); listener.settimeout(120)
    r['socket_inode'] = owned.st_ino; r['socket_device'] = owned.st_dev
    print(json.dumps({'linux_user_socket_ready': str(endpoint), 'uid': owned.st_uid, 'mode': oct(owned.st_mode & 0o777)}), file=sys.stderr, flush=True)
    conn, _ = listener.accept()
    with conn:
        conn.settimeout(1)
        os.set_blocking(0, False); os.set_blocking(1, False)
        until = time.monotonic() + 180
        while time.monotonic() < until:
            ready, _, _ = select.select([conn, 0], [], [], .05)
            if conn in ready:
                data = conn.recv(1024)
                if not data: r['reason'] = 'service-stream-EOF'; break
                r['socket_to_ssh'] += len(data)
                if r['socket_to_ssh'] > 65536: raise ValueError('socket byte limit')
                if not select.select([], [1], [], 1)[1] or os.write(1, data) != len(data): raise OSError('SSH stdout write unavailable or partial; no retry')
            if 0 in ready:
                data = os.read(0, 1024)
                if not data: r['reason'] = 'SSH-stdin-EOF'; break
                r['ssh_to_socket'] += len(data)
                if r['ssh_to_socket'] > 65536: raise ValueError('SSH byte limit')
                conn.sendall(data)
        else: r['reason'] = 'plumbing-lease-expired'
    r['service_socket_close_returned'] = True
except BaseException as error:
    r['reason'] = type(error).__name__ + ': ' + str(error)
    raise
finally:
    listener.close()
    if owned is not None:
        try:
            current = endpoint.lstat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino): endpoint.unlink()
        except FileNotFoundError: pass
    r['ended_utc'] = now()
    with report_path.open('x') as f: json.dump(r, f, indent=2); f.write('\n')
    print(json.dumps(r), file=sys.stderr, flush=True)
