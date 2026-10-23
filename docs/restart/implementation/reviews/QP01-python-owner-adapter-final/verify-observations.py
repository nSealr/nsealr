"""Read the one completed replay; never spawn, signal, or replay a case."""
import base64
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RAW = HERE / ".runtime/targeted-01"
NEGATIVE = ROOT / "docs/restart/implementation/QP01/python-owner-adapter/negative"


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


command = read(RAW / "command.json")
preflight = read(RAW / "preflight.json")
expectations = read(NEGATIVE / "expectations.json")
assert command["exit_code"] == 0
assert command["source_status_before"] == command["source_status_after"] == ""
assert command["worker_sha256_after"] == preflight["worker_rechecked_before_any_frame"]["sha256"]
stderr = (RAW / "stderr.log").read_text()
assert stderr.count(" ... ok\n") == 17 and "Ran 17 tests in 9.114s" in stderr and stderr.endswith("\nOK\n")
paths = sorted((RAW / "cases").glob("*.json"))
assert len(paths) == 70
records = {(row["id"], row["event"]): row for row in map(read, paths)}
assert len(records) == 70
stdout_rows = [json.loads(line)["python_owner_case"] for line in (RAW / "stdout.log").read_text().splitlines() if line]
assert len(stdout_rows) == 70
assert {(row["id"], row["event"]): row for row in stdout_rows} == records
owners, workers, helpers = set(), set(), set()
cases = []
for case in [*expectations["real_lifecycle_cases"], {"id": "normal259_release_once"}]:
    name = case["id"]
    positive = name == "normal259_release_once"
    row = records[name, "released" if positive else "settled"]
    observation = row["observation"]
    terminal = observation["terminal"]
    owner, worker = observation["owner_pid"], terminal["worker_pid"]
    owners.add(owner)
    assert observation["state"] == "settled"
    assert observation["EOF"] == [1, 2, 4, 5] and observation["parent_owned_fds"] == []
    assert observation["owner_wait_raw"] == (observation["owner_exit_code"] << 8)
    assert observation["fault"] is None and observation["diagnostic_base64"] == ""
    assert observation["ready_hex"] == "52"
    ready = records[name, "ready"]["observation"]
    assert ready["output_bytes"] == 0 and ready["phase"] is None and ready["terminal"] is None
    wire = [json.loads(line) for line in base64.b64decode(observation["status_wire_base64"]).splitlines()]
    assert wire[-1] == terminal
    if worker is not None:
        workers.add(worker)
        phase = observation["phase"]
        assert wire == [phase, terminal]
        assert phase["worker_pid"] == phase["sid"] == phase["pgid"] == worker
        assert phase["owner_pid"] == phase["ppid"] == owner
        assert phase["exe_sha256"] == command["worker_sha256_after"]
        assert phase["limits"] == {"AS": [268435456, 268435456], "CPU": [1, 2], "CORE": [0, 0]}
        assert phase["G_bytes"] == phase["image_bytes_sent"] == 0
        assert [fd["fd"] for fd in phase["fds"]] == [0, 1, 2]
        identities = {(fd["dev"], fd["ino"]) for fd in phase["fds"]}
        assert len(identities) == 3
        assert identities.isdisjoint({(fd["dev"], fd["ino"]) for fd in observation["pipe_identities"]})
        assert terminal["worker_wait"]["collector_pid"] == owner
        assert terminal["worker_io"] == {"stdin_closed": True, "stdout_eof": True,
                                         "stderr_eof": True, "owned_fds_closed": True}
    else:
        assert observation["phase"] is None and terminal["worker_wait"] is None
        assert wire == [terminal]
    if positive:
        assert row["caller_released_bytes"] == terminal["result_bytes"] == 259
        assert terminal["result_sha256"] == "88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7"
        assert terminal["outcome"] == "decoded" and terminal["worker_wait"]["raw_status"] == 0
        assert observation["taken"] is True and row["second_take_refused"] and row["reservation_before_close_refused"]
    else:
        assert row["caller_released_bytes"] == 0 and observation["taken"] is False
        assert terminal["outcome"] == case["terminal_outcome"]
        assert observation["owner_exit_code"] == case["O_exit"]
        assert observation["output_bytes"] == case["O_private_bytes"]
        assert terminal["cancel_observed"] == case["O_cancel_observed"]
        if "accepted_W_wait_pairs" in case:
            wait = terminal["worker_wait"]
            assert {key: wait[key] for key in ("exit_code", "raw_status")} in case["accepted_W_wait_pairs"]
            assert terminal["G_bytes"] == terminal["image_bytes_sent"] == terminal["result_bytes"] == 0
    if name == "wall8_preG":
        timing = terminal["timing"]
        assert int(timing["invalidated_ns"]) >= int(timing["begin_ns"]) + 8000000000
        assert int(timing["cleanup_deadline_ns"]) == int(timing["invalidated_ns"]) + 4000000000
    cases.append({"id": name, "O": owner, "W": worker, "owner_raw_status": observation["owner_wait_raw"],
                  "worker_wait": terminal["worker_wait"], "outcome": terminal["outcome"],
                  "private_bytes": observation["output_bytes"], "released_bytes": row["caller_released_bytes"],
                  "EOF": observation["EOF"], "parent_owned_fds": observation["parent_owned_fds"]})
for case in expectations["helper_cases"]:
    row = records["FG7_" + case["mode"], "rejected-collected"]
    observation = row["observation"]
    helpers.add(observation["owner_pid"])
    assert row["helper_sha256"] == case["sha256"]
    assert row["actual_W_count"] == row["caller_released_bytes"] == 0
    assert observation["owner_wait_raw"] == observation["owner_exit_code"] == 0
    assert observation["EOF"] == [1, 2, 4, 5] and observation["diagnostic_base64"] == ""
    assert observation["ready_hex"] == case["expected_ready_hex"]
    assert observation["commands"] == [case["intended_control"]]
    assert observation["state"] == "quarantined" and observation["output_bytes"] == 0
    assert observation["taken"] is False and observation["fault"] is not None
assert (len(owners), len(workers), len(helpers)) == (10, 5, 11)
assert len(owners | workers | helpers) == 26
assert all(not (Path("/proc") / str(pid)).exists() for pid in owners | workers | helpers)
assert records["types-canonicality", "rejected"]["rejected_controls"] == 27
assert records["pipe-cap", "rejected"]["retained_bytes"] == 513
assert sum(row["role"] == "PURE_SYNTHETIC_RELATION_ZERO_PROCESSES" for row in records.values()) == 9
evidence = HERE / "replay"
evidence.mkdir()
for name in ("preflight.json", "command.json", "stdout.log", "stderr.log"):
    shutil.copyfile(RAW / name, evidence / name)
members = [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())} for path in paths]
archive_path = evidence / "cases.tar.gz"
with archive_path.open("wb") as file, gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as gz:
    with tarfile.open(fileobj=gz, mode="w") as archive:
        for path in paths:
            data = path.read_bytes()
            info = tarfile.TarInfo(path.name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
        data = (json.dumps({"role": "Exact70 records of ONE independent17-method run", "members": members}, indent=2) + "\n").encode()
        info = tarfile.TarInfo("manifest.json")
        info.size, info.mode, info.mtime = len(data), 0o644, 0
        archive.addfile(info, io.BytesIO(data))
write(HERE / "verification.json", {
    "role": "Read-only review of exact completed targeted evidence; no additional runtime",
    "verified_utc": datetime.now(timezone.utc).isoformat(), "candidate": preflight["candidate"],
    "execution_source": command["source"], "exit_code": 0, "test_methods": 17,
    "unittest_elapsed_seconds": 9.114, "wrapper_elapsed_seconds": command["elapsed_seconds"],
    "structured_records": 70, "stdout_matches_case_files": True,
    "real_lifecycle": cases, "unique_O_PIDs": sorted(owners), "unique_W_PIDs": sorted(workers),
    "unique_no_fork_helper_PIDs": sorted(helpers), "unique_kernel_diagnostic_processes": 26,
    "synthetic_PIDs_are_excluded": [99, 10001, 10002],
    "all26_proc_paths_absent_after_source_proven_wait_collection": True,
    "helper_quarantine": "Actual helper wait0/all EOF, no-W source bound; poison/strong runtime reference preserved. Only known-collected helper test closes residual parent descriptors. No live O/W recovery inferred.",
    "pure_controls": {"relation_mutations": 9, "wire_types": 27, "pipe_only_cap": 1},
    "ready_no_output_and_preG_zero_counters": True, "worker_hash_session_limits_and_pipe_relations_verified": True,
    "actual_O_ECHILD": "Asserted by each real lifecycle/helper method after actual wait; no new wait attempted by reader",
    "source_clean_before_after": True, "cases_archive_sha256": sha(archive_path.read_bytes()),
    "new_builds": 0, "Node": 0, "native_C": 0, "full_component_CI": 0,
    "limits": "Host-only selected consumer cases; no unknown-owner cleanup, O-death, hard deadline/recovery, hostile isolation, target/ARM/physical or task-release qualification."})
print(json.dumps({"verified": True, "methods": 17, "records": 70, "O": 10, "W": 5, "no_fork_helpers": 11}))
