#!/usr/bin/env python3
"""Read exact Git objects and retained raw evidence; write only this review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FINAL = "f4c35c1c455528501c91747eb503dc78b4050f9d"
SOURCE = "7a32eed82f542e818fad1c48d6815a38930eac32"
OLD = "41f5d2d193e4a00227737e1f8d71ce57e39ea889"
FINDING = "30ae87dd31c3c292b22f4758d4fad9fea63a7b37"
BASE = "docs/restart/implementation/S01/"
FRESH = BASE + "followup-evidence/fresh/"
RUNTIME = Path("/home/tux/nsealr/.restart-tools/goal/s01-integration/docs/restart/implementation/S01/.work/current-default")


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd)


def blob(path, commit=FINAL, repo=ROOT):
    return git("show", f"{commit}:{path}", cwd=repo)


def document(path, commit=FINAL):
    return json.loads(blob(path, commit))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    changes = git("diff", "--name-status", SOURCE, FINAL).decode().splitlines()
    assert len(changes) == 115 and all(line.startswith("A\t" + BASE) for line in changes)
    sources = git("diff", "--name-only", SOURCE + "^", SOURCE).decode().splitlines()
    assert len(sources) == 8
    bindings = {path: digest(blob(path)) for path in sources}
    assert all(blob(path) == blob(path, SOURCE) for path in sources)
    artifacts = document(BASE + "provenance-followup-artifacts.json")
    assert len(artifacts) == 131 and len({row['path'] for row in artifacts}) == 131
    for row in artifacts:
        assert digest(blob(row['path'])) == row['sha256'], row
    old_artifacts = document(BASE + "artifacts.json")
    assert len(old_artifacts) == 75
    for row in old_artifacts:
        assert digest(blob(row['path'])) == row['sha256']
        assert blob(row['path']) == blob(row['path'], FINDING)
    for path in ("tools/baseline/overlays/lab-provenance.patch", "tools/baseline/overlays/lab-provenance.json",
                 BASE + "lab-metadata-v1.patch", BASE + "lab-metadata-v1.json"):
        assert blob(path) == blob(path, FINDING)
    before = document("tools/baseline/inputs.json", SOURCE + "^")
    after = document("tools/baseline/inputs.json")
    for name, commit in (("specs", "45f8b6ff1123f3f55be4ce457fd1008e91043cc2"),
                         ("companion", "678796900e462f5504e47fe934e2e5f23d85824f")):
        before['repositories'][name]['commit'] = commit
    assert before == after
    old_objects = git("ls-tree", OLD).decode().splitlines()
    objects = [line for line in old_objects if line.split("\t")[1] not in ('docs', 'tools')]
    final_objects = git("ls-tree", FINAL).decode().splitlines()
    assert all(line in final_objects for line in objects)
    assert blob("tools/baseline/run.py") == blob("tools/baseline/run.py", OLD)
    manifest = document("tests/fixtures/specs/SOURCE.json")
    repo = Path('/home/tux/nsealr/specs')
    tracked = git('ls-tree', '-rz', '--full-tree', manifest['commit'], '--', 'vectors/', cwd=repo)
    paths = []
    for entry in filter(None, tracked.split(b'\0')):
        header, path = entry.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        relative = path.decode()
        assert kind == 'blob' and mode in ('100644', '100755')
        raw = git('cat-file', 'blob', oid, cwd=repo)
        assert raw == blob('tests/fixtures/specs/' + relative)
        assert digest(raw) == manifest['files'][relative]
        paths.append(relative)
    assert len(paths) == 221 and set(paths) == set(manifest['files'])
    command_count, raw_count = 0, 0
    for row in artifacts:
        path = row['path']
        if path.endswith('/commands.json'):
            for command in document(path):
                raw = blob(str(Path(path).parent / command['log']))
                assert digest(raw) == command['sha256']
                assert datetime.fromisoformat(command['ended']) >= datetime.fromisoformat(command['started'])
                assert command['exit_code'] == (1 if command['label'] == 'original-reviewer-red' else 0), command
                command_count += 1
        if path.startswith(FRESH):
            assert (RUNTIME / path.removeprefix(FRESH)).read_bytes() == blob(path)
            raw_count += 1
    affected = document(FRESH + 'evidence/affected/commands.json')
    assert [c['label'] for c in affected] == ['core-ci', 'lab-ci', 'fixture-parity', 'v1-discovery', 'full-integration']
    log = blob(FRESH + 'evidence/affected/04-full-integration.log').decode()
    makefile = blob('Makefile', '3303ab17a28ed32419576627d5abb93db3999635', Path('/home/tux/nsealr/lab')).decode()
    recipe = makefile.split('integration-pnpm:\n')[1].split('\n\n')[0]
    expected = re.findall(r'scripts/(\S+\.py)', recipe)
    observed = re.findall(r'^\.venv/bin/python scripts/(\S+\.py)$', log, re.M)
    assert len(expected) == 20 and expected == observed
    assert 'snapshot check passed (547 files)' in log
    for name in ('with-credentials', 'with-fragment', 'wrong-scheme'):
        assert 'relay-step-response-auth-url-' + name in log
    source_before = document(FRESH + 'evidence/affected/source-before.json')
    source_after = document(FRESH + 'evidence/affected/source-after.json')
    assert all(source_before[k]['diff_sha256'] == source_after[k]['diff_sha256'] for k in source_before)
    for name, commit in document(FRESH + 'source-commits.json').items():
        directory = RUNTIME / ('firmware' if name == 'nsealr' else name)
        assert git('rev-parse', 'HEAD', cwd=directory).decode().strip() == commit
        assert digest(git('diff', '--binary', cwd=directory)) == source_after[name]['diff_sha256']
    original_review_path = 'docs/restart/implementation/reviews/S01-integration/review-result.json'
    assert digest(blob(original_review_path, FINDING)) == 'ed89cabb9708bf4d985bb83091dd46a79f68e32abe1bfc6e8f71a238a02db20f'
    red = document('docs/restart/implementation/reviews/S01-integration/probe-result.json', FINDING)
    assert len(red['cases']) == 20 and sum(row['pass'] for row in red['cases']) == 17
    remote = git('ls-remote', 'origin', 'refs/tags/evidence/r00-full-20261018', 'refs/tags/evidence/r00-reviewed-20261018').decode()
    for ref in ('f853757a5080003036aacb797999410398816f16', '303b4c9d9386147220abaf2cf754c5c47e458dff'):
        assert ref in remote
        assert digest(blob('tools/baseline/inputs.json', ref)) == '546067e92916c93d58ac7e063f79ba7b279eca7f73be9d7f86baec97e6642e59'
    result = dict(candidate=FINAL, tested_source=SOURCE, recorded_at=datetime.now(timezone.utc).isoformat(),
                  source_bindings=bindings, metadata_only_additions=len(changes), final_artifacts_verified=len(artifacts),
                  final_logs_verified=sum(row['path'].endswith('.log') for row in artifacts),
                  command_log_hashes_and_exit_codes_verified=command_count, raw_runtime_artifacts_matched=raw_count,
                  original_artifacts_unchanged=75, unchanged_product_top_level_objects=objects,
                  original_probe_passes=17, original_probe_bypasses=3, old_overlays_unchanged=True,
                  exact_complete_vector_files=221, hidden_paths=[p for p in paths if Path(p).name.startswith('.')],
                  current_input_change='specs and companion commits only', runtime_and_other_pins_unchanged=True,
                  executed_integration_steps=observed, full_log_sha256=digest(log.encode()),
                  source_states_after_execution_match_retained_runtime=True, historical_remote_refs=remote,
                  historical_inputs_sha256='546067e92916c93d58ac7e063f79ba7b279eca7f73be9d7f86baec97e6642e59', passed=True)
    (HERE / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
