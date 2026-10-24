"""Affected source-aware capture checker for the cold gate and Python consumer.

Extends the accepted 7d5 cold verifier; original generic completed-capture
verifier stays separately mandatory and unchanged. This proposal never polls,
triggers CI, or retroactively changes expectations for historical captures.
CLI: CAPTURE_DIRECTORY SOURCE_HEAD REPOSITORY.
"""
from pathlib import Path
import ast,base64,collections,hashlib,json,re,subprocess,sys,zipfile

if sys.flags.optimize:
    raise RuntimeError("capture checker requires assertions enabled")

ORIGIN_SHA256 = "7d5a1669ee2ff366ef34b710e8e8b3bdf25531d6e72ca3fc35442acc653f354d"
EXPECTED_PI_TESTS = 211
PYTHON_OWNER_ADAPTER_SHA256 = "da6f36c966e2b27407e1025456d1f72c6d061d9463eb9ad25af85f594bf5a203"
WORKER_UNIT_SOURCE_SHA256 = "2ce1310dfc3eb596e4bdd03c4c2386b1d61a104e99e87337edc00f2a2325fa19"
EXPECTED_FIRST_CASES = set(['FG0_C_handshake_failure', 'FG0_C_library_ready_failure', 'FG0_actual_pre_admission_refusal', 'FG0_pre_presentation_assertion', 'FG0_startup_unused', 'FG1_normal259', 'FG2_elapsed_deadline_before_timer_callback', 'FG2_timeout_late', 'FG2_timeout_preG', 'FG3_cancel_late', 'FG3_cancel_preG', 'FG3_cancel_preP', 'FG4_generation', 'FG5_C_SIGKILL_preG', 'FG5_C_early_exit_before_P', 'FG6_control_EOF_preG', 'FG6_duplicate_P', 'FG6_invalid_opcode', 'FG6_premature_G', 'FG7_contradictory-IO', 'FG7_duplicate-key', 'FG7_duplicate-terminal', 'FG7_phase-after-terminal', 'FG7_ready-extra', 'FG7_ready-missing', 'FG7_relation_decoded-stderr-overflow', 'FG7_relation_decoded-stderr-truncation', 'FG7_relation_decoded-stdout-count-mismatch', 'FG7_relation_decoded-stdout-overflow', 'FG7_relation_decoded-stdout-retained-result-mismatch', 'FG7_relation_phase-after-Q', 'FG7_relation_phase-before-P', 'FG7_relation_unused-with-phase', 'FG7_relation_unused-with-worker', 'FG7_status-missing', 'FG7_status-overflow', 'FG7_status-truncated', 'FG7_wrong-owner', 'FG7_wrong-worker'])

EXPECTED_CASE_ROW_COUNTS = {'FG0_C_handshake_failure': 1, 'FG0_C_library_ready_failure': 1, 'FG0_actual_pre_admission_refusal': 1, 'FG0_pre_presentation_assertion': 1, 'FG0_startup_unused': 1, 'FG1_normal259': 3, 'FG2_elapsed_deadline_before_timer_callback': 4, 'FG2_timeout_late': 5, 'FG2_timeout_preG': 5, 'FG3_cancel_late': 3, 'FG3_cancel_preG': 3, 'FG3_cancel_preP': 1, 'FG4_generation': 3, 'FG5_C_SIGKILL_preG': 3, 'FG5_C_early_exit_before_P': 1, 'FG6_control_EOF_preG': 3, 'FG6_duplicate_P': 1, 'FG6_invalid_opcode': 1, 'FG6_premature_G': 1, 'FG7_contradictory-IO': 1, 'FG7_duplicate-key': 1, 'FG7_duplicate-terminal': 1, 'FG7_phase-after-terminal': 1, 'FG7_ready-extra': 1, 'FG7_ready-missing': 1, 'FG7_relation_decoded-stderr-overflow': 1, 'FG7_relation_decoded-stderr-truncation': 1, 'FG7_relation_decoded-stdout-count-mismatch': 1, 'FG7_relation_decoded-stdout-overflow': 1, 'FG7_relation_decoded-stdout-retained-result-mismatch': 1, 'FG7_relation_phase-after-Q': 1, 'FG7_relation_phase-before-P': 1, 'FG7_relation_unused-with-phase': 1, 'FG7_relation_unused-with-worker': 1, 'FG7_status-missing': 1, 'FG7_status-overflow': 1, 'FG7_status-truncated': 1, 'FG7_wrong-owner': 1, 'FG7_wrong-worker': 1}

def verify_product(raw, head, repo, run_id=None):
    lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ?', '',s) for s in raw.decode().splitlines()]
    text='\n'.join(lines)
    objects=[]
    decoder=json.JSONDecoder()
    for i,line in enumerate(lines):
        if line.startswith('{'):
            try: value,_=decoder.raw_decode('\n'.join(lines[i:]))
            except json.JSONDecodeError: continue
            if isinstance(value,dict): objects.append(value)
    builds=[o for o in objects if o.get('role')=='public fixture build, not hardware qualification']
    assert len(builds)==1
    b=builds[0]
    assert b['argv']==['cargo','build','-p','nsealr-pi-engine-fixture','--locked','--offline','--release','--message-format=json']
    paths={'Cargo.toml','Cargo.lock','crates/nsealr-pi-engine-fixture/Cargo.toml','crates/nsealr-pi-engine-fixture/src/lib.rs'}
    assert set(b['source'])==paths
    for path,digest in b['source'].items():
        data=subprocess.check_output(['git','-C',repo,'show',head+':'+path])
        assert hashlib.sha256(data).hexdigest()==digest
    assert Path(b['library']).is_absolute() and b['library'].endswith('/release/libnsealr_pi_engine_fixture.so')
    assert re.fullmatch('[0-9a-f]{64}',b['sha256'])
    if b['CARGO_TARGET_DIR'] is not None:
        assert Path(b['CARGO_TARGET_DIR']).is_absolute()
        assert Path(b['library']).is_relative_to(b['CARGO_TARGET_DIR'])
    ready=[o for o in objects if o.get('readiness_controls')==5]
    assert len(ready)==1
    for key,value in {'request_bytes_sent':0,'native_reports':0,'children':5,'collected':5}.items(): assert ready[0][key]==value
    clients=[o for o in objects if o.get('scope')=='actual client + public-fixture host adapter only']
    assert len(clients)==1
    c=clients[0]
    for key,value in {'positive':2,'valid_shape_verifier_negatives':5,'post_native_currentness_negatives':5,'actual_unsettled_child_timeout_no_early_reuse_then_fresh':True,'children':14,'collected':14}.items(): assert c[key]==value
    assert len(c['reports'])==14
    observations=[o['native_observation'] for o in objects if 'native_observation' in o]
    assert observations==c['reports']
    for o in c['reports']:
        assert o['library']==b['library'] and o['sha256']==b['sha256']
        assert 0<o['input_bytes']<=947 and 0<o['output_bytes']<=947
        assert all(re.fullmatch('[0-9a-f]{64}',o[k]) for k in ['input_sha256','output_sha256'])
        assert len(o['synthetic_complete_review'])>1
    assert sum(bool(re.fullmatch(rf'Ran {EXPECTED_PI_TESTS} tests in .+s',s)) for s in lines)==1
    coverage=[tuple(map(float,m.groups())) for s in lines if (m:=re.fullmatch(r'nsealr-pi-engine-fixture\s+([0-9.]+)%\s+([0-9.]+)%\s+ok',s))]
    assert coverage==[(100.0,100.0)]
    control="python3 -B -m unittest discover -s docs/restart/implementation/R00/audit-data -p 'test_audit_rust.py'"
    assert lines.count(control)==1 and lines.count('python3 scripts/audit_rust.py')==1
    start,end=lines.index(control),lines.index('python3 scripts/audit_rust.py')
    assert start<end
    assert any(re.fullmatch(r'Ran 4 tests in .+s',s) for s in lines[start:end]) and 'OK' in lines[start:end]
    audit=lines[end+1:]
    commands=[s for s in audit if s.startswith('cargo deny --locked --config ')]
    assert len(commands)==6 and commands[0].endswith('Cargo.toml fetch index db') and commands[1].endswith('apps/desktop-simulator/Cargo.toml fetch index') and commands[2].endswith('apps/pi/qr-worker/Cargo.toml fetch index')
    assert all(s.endswith(' --offline check --deny index-failure') for s in commands[3:])
    assert audit.count('advisories ok, bans ok, licenses ok, sources ok')==3
    first_proof=verify_first(objects,b,head,repo)
    out={'run':int(run_id) if run_id is not None else None,'source_head':head,'product_log_sha256':hashlib.sha256(raw).hexdigest(),'native_build':b,'native_source_bindings':4,'actual_full_Pi_tests':EXPECTED_PI_TESTS,'automatic_readiness_controls':ready[0],'client':{k:v for k,v in c.items() if k!='reports'},'all14_native_observations_match_actual_provisioned_library':True,'fixture_coverage_actual_and_floor':coverage[0],'additional_audit_controls':4,'three_complete_fresh_audits':True,'audit_commands':commands,'limits':'Original completed CI source/build/trace binding only; the ELF itself is not downloaded, no cdylib reproducibility or target/device/custody/physical qualification claim. The original17-step/check/bootstrap/capture verifier remains separately mandatory.'}
    out.update(first_proof)
    out.update(verify_python_owner(objects, first_proof['worker_build'], head, repo))
    out.update(verify_qh01_composition(objects, lines, first_proof['worker_build'], head, repo, full_product=True))
    out.update(verify_qh01_lifecycle(objects))
    out.update(verify_qh01_request_engine(objects, head, repo))
    out['proof_role']='local_makeci_source_addon_no_GitHub_claim' if run_id is None else 'completed_capture_source_addon_requires_generic_receipt_job_check_verifier'
    if run_id is None:
        out['limits']='Local stable makeci source/build/trace proof only; no GitHub run, receipt, job, check, protected integration or device claim. Hosted acceptance separately requires the unchanged mandatory completed-capture verifier with RUN HEAD CHECKRUNS_JSON, plus this source addon. No ELF reproducibility or physical qualification.'
    return out


def verify_qh01_composition(objects, lines, worker, head, repo, full_product=False):
    """Require the new real composition in addition to every existing gate."""
    def blob(path):
        return subprocess.check_output(['git', '-C', repo, 'show', head + ':' + path])
    def paths(prefix):
        return subprocess.check_output(['git', '-C', repo, 'ls-tree', '-r', '--name-only', head, '--', prefix], text=True).splitlines()
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    def integers(values):
        assert all(type(v) is int for v in values)
    def one(key):
        rows = [o[key] for o in objects if key in o]
        assert len(rows) == 1
        return rows[0]
    c, command = (one(k) for k in ['qh01_composition_case', 'qh01_composition_command'])
    builds = [o['bridge_service_build'] for o in objects if 'bridge_service_build' in o]
    positions = lambda key: [i for i, line in enumerate(lines) if line.startswith('{"' + key + '":')]
    build_positions = positions('bridge_service_build')
    command_positions, case_positions = positions('qh01_composition_command'), positions('qh01_composition_case')
    assert len(command_positions) == len(case_positions) == 1
    assert len(builds) == len(build_positions) == (15 if full_product else 1)
    command_at, case_at = command_positions[0], case_positions[0]
    assert build_positions[0] < command_at < case_at
    b = builds[0]
    # Source oracle2db4: one pre-case build, then14 mandatory CLI rebuilds.
    # Validate every occurrence; identical payloads are never deduplicated.
    assert all(json.dumps(record, sort_keys=True) == json.dumps(b, sort_keys=True) for record in builds)
    if full_product:
        runner = ast.parse(blob('tests/integration/run.py'))
        assignments = [n for n in runner.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'PRODUCT_STEPS' for t in n.targets)]
        assert len(assignments) == 1
        steps = ast.literal_eval(assignments[0].value)
        assert len(steps) == 17
        expected = [f'[{i}/17 original {original}] {module}' for i, (original, module) in enumerate(steps, 1)]
        markers = [(i, line) for i, line in enumerate(lines) if re.fullmatch(r'\[\d+/17 original \d+\] \w+', line)]
        assert [line for _, line in markers] == expected and case_at < markers[0][0]
        finish = 'All 17 retained product integration steps passed. External hardware and optional physical resources are separate.'
        endings = [i for i, line in enumerate(lines) if line == finish]
        assert len(endings) == 1 and markers[-1][0] < endings[0]
        assert len([i for i in build_positions if i < command_at]) == 1
        for number, (begin, _label) in enumerate(markers, 1):
            end = markers[number][0] if number < 17 else endings[0]
            assert sum(begin < i < end for i in build_positions) == (1 if number in {*range(3, 16), 17} else 0)
        assert all(i < endings[0] for i in build_positions)
    assert not any('qh01_composition_failure' in o for o in objects)
    integers([b['v'], c['v'], command['v'], b['status']])
    assert b['v'] == c['v'] == command['v'] == 1 and b['status'] == 0
    assert b['signal'] is None and b['error'] is None and b['role'] == 'current_checkout_compiler_artifacts_only'
    assert c['id'] == 'bridge_rgb_kind1_basic' and c['scope'] == 'QH01_HOST_COMPOSITION_CI_V1'
    assert c['role'] == 'public_host_fixture_synthetic_client_clock'
    root = Path(b['cwd'])
    assert root.is_absolute() and '..' not in root.parts
    service = sorted(p for p in paths('apps/bridge/service/src') if p.endswith('.ts') and not p.endswith('.test.ts'))
    assert len(service) == 5
    assert b['source_before'] == b['source_after'] == {p: digest(blob(p)) for p in service}
    options = ['pnpm', 'exec', 'tsc', '--ignoreConfig', '--target', 'ES2022', '--module', 'NodeNext',
               '--moduleResolution', 'NodeNext', '--strict', '--esModuleInterop', '--forceConsistentCasingInFileNames',
               '--skipLibCheck', '--resolveJsonModule', '--types', 'node', '--declaration',
               '--rootDir', 'apps/bridge/service/src', '--outDir', 'apps/bridge/service/dist']
    assert b['argv'] == options + service
    assert b['compiler']['version'] == json.loads(blob('package.json'))['devDependencies']['typescript'] == '6.0.3'
    assert Path(b['compiler']['path']).is_relative_to(root / 'node_modules')
    assert b['compiler']['path'].endswith('/typescript/bin/tsc') and re.fullmatch('[0-9a-f]{64}', b['compiler']['sha256'])
    prefix = 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/'
    source = ['tools/bridge/build_packages.mjs', 'pnpm-lock.yaml', 'apps/bridge/service/package.json',
              'docs/restart/implementation/QP01/request-engine/exchange.py', 'apps/pi/tests/test_engine_adapter.py',
              'apps/pi/app/nsealr_vault/qr_owner_adapter.py', 'apps/pi/app/nsealr_vault/qr_worker.py']
    source += [prefix + p for p in ['run-composition.py', 'bridge-child.mjs', 'test_attention_reporting.py']] + service
    packages = ['client', 'core', 'policy', 'protocol', 'qr', 'transport', 'framing']
    package_sources = [p for name in packages for p in paths('packages/' + name + '/src') if p.endswith('.ts')]
    source += package_sources
    assert c['source_before'] == c['source_after'] == {p: digest(blob(p)) for p in source}
    outputs = {p.replace('/src/', '/dist/')[:-3] + suffix for p in service for suffix in ['.js', '.d.ts']}
    generated = outputs | {p.replace('/src/', '/dist/')[:-3] + suffix for p in package_sources
                           if not p.endswith('.test.ts') for suffix in ['.js', '.d.ts']}
    assert set(b['outputs']) == outputs and set(c['generated_before']) == generated
    assert c['generated_before'] == c['generated_after']
    assert all(re.fullmatch('[0-9a-f]{64}', h) for h in c['generated_before'].values())
    assert b['outputs'] == {p: c['generated_before'][p] for p in outputs}
    assert c['worker_initialization'] == {'path': worker['worker'], 'sha256': worker['sha256']}
    argv = c['argv']
    assert len(argv) == 15 and argv == command['argv'] and argv[:3] == [str(root / 'apps/pi/.venv/bin/python'), '-B', str(root / (prefix + 'run-composition.py'))]
    assert argv[3] == '--output' and argv[4] == command['output']
    output = Path(argv[4])
    assert output.is_absolute() and output.name == 'case' and output.parent.name.startswith('nsealr-qh01-composition-')
    assert argv[5:10] == ['--worker', worker['worker'], '--sha256', worker['sha256'], '--node']
    assert Path(argv[10]).is_absolute() and Path(argv[10]).name == 'node'
    assert argv[11:] == ['--bridge', str(root / 'apps/bridge/service/dist'), '--reuse', str(root)]
    native = 'docs/restart/implementation/QH01/native-qr-probe/'
    request, response = [blob(native + 'expected/' + p + '-kind-1-basic.envelope') for p in ['request', 'response']]
    image = blob(native + 'execution-01/request-kind-1-basic.rgb')
    frame = lambda raw: {'bytes': len(raw), 'sha256': digest(raw)}
    assert c['frames'] == {'presented': frame(request), 'decoded': frame(request), 'scanned': frame(response)}
    assert len(request) == 259 and len(response) == 611 and len(image) == 172800
    assert c['decoded_request'] == json.loads(blob('protocols/contracts/v1/vectors/transports/qr-envelope-kind-1-basic.json'))['decoded']
    a, collection = c['actual'], c['collection']
    assert a['result'] == 'PASS_FIRST_HOST_COMPOSITION_ONLY' and a['physical_claim'] is False
    ids = [a[k] for k in ['parent_pid', 'node_pid', 'owner_pid', 'worker_pid']]
    integers(ids)
    assert len(set(ids)) == 4 and min(ids) > 1 and a['worker_sha256'] == worker['sha256']
    integers([a[k] for k in ['presented_bytes', 'decoded_bytes', 'scanned_bytes']])
    assert [a[k] for k in ['presented_bytes', 'decoded_bytes', 'scanned_bytes']] == [259, 259, 611]
    assert collection['node_pid'] == a['node_pid'] and type(collection['node_wait_raw']) is int and collection['node_wait_raw'] == 0
    assert collection['node_EOF'] == ['stderr', 'stdout'] and collection['node_observed']['stderr'] == 0
    assert collection['parent_fd_before'] == collection['parent_fd_after'] == [0, 1, 2]
    assert collection['runtime_strong_reference'] is True
    o = collection['B3']; t = o['terminal']; p = o['phase']; wait = t['worker_wait']
    integers(collection['parent_fd_before'] + collection['parent_fd_after'] + o['EOF'])
    integers([p[k] for k in ['v', 'owner_pid', 'worker_pid', 'ppid', 'sid', 'pgid', 'G_bytes', 'image_bytes_sent']])
    integers([t[k] for k in ['v', 'owner_pid', 'worker_pid', 'input_bytes_received', 'G_bytes', 'image_bytes_sent',
                            'stdout_observed', 'stdout_retained', 'stderr_observed', 'stderr_retained', 'result_bytes']])
    integers([o[k] for k in ['owner_pid', 'image_bytes_written', 'output_bytes']])
    integers([f['fd'] for f in p['fds']] + [n for pair in p['limits'].values() for n in pair])
    assert p['v'] == t['v'] == 1 and p['kind'] == 'worker_ready' and t['kind'] == 'terminal'
    assert o['state'] == 'settled' and o['owner_pid'] == a['owner_pid'] == t['owner_pid'] == p['owner_pid'] == p['ppid']
    integers([o['owner_wait_raw'], o['owner_exit_code'], wait['raw_status'], wait['exit_code'], wait['collector_pid']])
    assert o['owner_wait_raw'] == o['owner_exit_code'] == wait['raw_status'] == wait['exit_code'] == 0
    assert wait['collector_pid'] == o['owner_pid'] and p['worker_pid'] == t['worker_pid'] == a['worker_pid']
    assert p['sid'] == p['pgid'] == p['worker_pid'] and p['exe_sha256'] == worker['sha256']
    assert p['limits'] == {'AS': [268435456, 268435456], 'CPU': [1, 2], 'CORE': [0, 0]}
    assert p['G_bytes'] == p['image_bytes_sent'] == 0 and [f['fd'] for f in p['fds']] == [0, 1, 2]
    assert len({(f['dev'], f['ino']) for f in p['fds']}) == 3
    assert o['EOF'] == [1, 2, 4, 5] and o['parent_owned_fds'] == [] and o['commands'] == ['P', 'G']
    assert o['taken'] is o['closed'] is True and o['fault'] is o['transport_error'] is None
    assert o['ready_hex'] == '52' and o['diagnostic_base64'] == ''
    assert t['outcome'] == 'decoded' and t['ownership'] == 'settled' and t['session_policy_verified'] is True
    assert all(t['worker_io'][k] is True for k in ['stdin_closed', 'stdout_eof', 'stderr_eof', 'owned_fds_closed'])
    assert t['input_bytes_received'] == t['image_bytes_sent'] == o['image_bytes_written'] == len(image)
    assert t['input_sha256'] == digest(image) and t['G_bytes'] == 1
    assert t['result_bytes'] == o['output_bytes'] == t['stdout_observed'] == t['stdout_retained'] == len(request)
    assert t['result_sha256'] == o['output_sha256'] == digest(request)
    assert t['final_worker_eligible'] is True and t['cancel_observed'] is False
    clock = t['timing']
    assert clock['invalidated_ns'] is clock['cleanup_deadline_ns'] is None
    assert int(clock['begin_ns']) <= int(clock['settled_ns']) <= int(clock['final_admission_ns']) < int(clock['begin_ns']) + 8000000000
    wire = base64.b64decode(o['status_wire_base64'], validate=True)
    assert base64.b64encode(wire).decode('ascii') == o['status_wire_base64']
    assert [json.loads(row) for row in wire.splitlines()] == [p, t]
    rows = c['node_records']
    assert len(rows) == 4 and [r['event'] for r in rows] == ['present', 'scan', 'close', 'result']
    assert all(type(r['v']) is int and r['v'] == 1 for r in rows)
    assert rows[0]['frame'].encode('ascii') == request and rows[0]['timer_args'] == [100] and rows[0]['clock'] == 99
    assert rows[1]['frame'].encode('ascii') == response and rows[2] == {'v': 1, 'event': 'close'}
    result = rows[3]
    integers(result['timer_args'] + result['clock_steps'] + [result['clear_calls'], result['deadline_fires']])
    assert result['timer_args'] == [100] and result['clock_steps'] == [0, 99, 100] and result['clear_calls'] == 1 and result['deadline_fires'] == 0
    assert result['native_response_base64'] == c['native_response_base64']
    wire = base64.b64decode(c['native_response_base64'], validate=True)
    assert base64.b64encode(wire).decode('ascii') == c['native_response_base64'] and len(wire) >= 4
    assert int.from_bytes(wire[:4], 'little') == len(wire) - 4 and json.loads(wire[4:]) == c['service_response']
    fixture = json.loads(blob('protocols/contracts/v1/examples/response-kind-1-basic.json'))
    key = json.loads(blob('protocols/contracts/v1/examples/response-get-public-key.json'))['result']['public_key']
    assert c['expected_public_key'] == fixture['result']['event']['pubkey'] == key
    assert c['service_response'] == {'version': 1, 'request_id': 'qh01.composition', 'ok': True, 'result': {'signer_response': fixture}}
    assert type(c['service_response']['version']) is int and c['service_response']['ok'] is True
    methods = ['both_fail', 'observation_failure', 'print_failure', 'reporting_base_exception', 'serialization_failure', 'write_failure']
    for method in methods:
        line = 'test_' + method + ' (__main__.AttentionReportingTests.test_' + method + ') ... ok'
        assert lines.count(line) == 1
    return {'qh01_composition_cases': 1, 'qh01_compiler_outputs_cross_bound': len(outputs),
            'qh01_build_records_verified': len(builds), 'qh01_post_case_CLI_build_intervals': 14 if full_product else 0,
            'qh01_dynamic_source_bindings': len(source), 'qh01_same_checkout_generated_bindings': len(generated),
            'qh01_actual_O_W_Node_collected': True, 'qh01_frame_bytes': [259, 259, 611],
            'qh01_attention_pure_controls': 6, 'qh01_clock': 'synthetic100; actualO8/shared4',
            'qh01_limits': 'New host fixture composition only; real timeout/cancel seam, camera/physical/key/provider gates remain open.'}


def verify_qh01_lifecycle(objects):
    """Bind the three automatic refusals to the already verified positive run."""
    def same(actual, expected):
        assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
    def integers(values):
        assert all(type(x) is int and abs(x) <= 9007199254740991 for x in values)
    def decimal(value):
        assert type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value)
        assert int(value) <= 18446744073709551615
    def occurrences(key):
        return [(i, o[key]) for i, o in enumerate(objects) if key in o]
    ids = ['scan_null_after_settlement', 'scan_pending_timeout_after_settlement', 'fixture_cancel_B3_verified_preG']
    positive = occurrences('qh01_composition_case')
    assert len(positive) == 1
    positive_at, positive = positive[0]
    commands = occurrences('qh01_lifecycle_command')
    results = occurrences('qh01_lifecycle_result')
    cases = occurrences('qh01_lifecycle_case')
    assert len(commands) == len(results) == len(cases) == 3
    assert [c['id'] for _, c in commands] == [c['id'] for _, c in cases] == ids
    assert [r['case'] for _, r in results] == ids
    assert not occurrences('qh01_lifecycle_failure')
    outputs = [positive['argv'][4]] + [command['output'] for _, command in commands]
    assert len(set(outputs)) == 4
    prior = positive_at
    reference = positive['collection']['B3']
    worker = positive['worker_initialization']
    for name, (command_at, command), (result_at, result), (case_at, case) in zip(ids, commands, results, cases):
        assert prior < command_at < result_at < case_at
        prior = case_at
        assert type(case['v']) is type(command['v']) is int and case['v'] == command['v'] == 1
        assert case['scope'] == 'QH01_HOST_LIFECYCLE_CI_V1' and case['role'] == positive['role']
        for field in ['source_before', 'source_after', 'generated_before', 'generated_after', 'worker_initialization', 'expected_public_key']:
            same(case[field], positive[field])
        argv = case['argv']
        assert argv == command['argv'] and argv[:4] == positive['argv'][:4] and argv[4] == command['output']
        assert argv[5:] == positive['argv'][5:] + ['--case', name]
        output = Path(argv[4])
        assert output.is_absolute() and output.name == 'case' and output.parent.name.startswith('nsealr-qh01-composition-')
        a, collection = case['actual'], case['collection']
        same(result, a)
        cancelled, timeout = name == ids[2], name == ids[1]
        error = 'signer_transport_timeout' if timeout else 'signer_transport_failed'
        assert a['result'] == 'PASS_HOST_COMPOSITION_LIFECYCLE_CASE' and a['case'] == name and a['physical_claim'] is False
        assert a['service_error'] == error and a['B3_outcome'] == ('cancelled' if cancelled else 'decoded')
        pids = [a[k] for k in ['parent_pid', 'node_pid', 'owner_pid', 'worker_pid']]
        integers(pids)
        assert min(pids) > 1 and len(set(pids)) == 4 and a['worker_sha256'] == worker['sha256']
        integers([a[k] for k in ['presented_bytes', 'decoded_bytes', 'scanned_bytes', 'caller_released_bytes']])
        assert a['presented_bytes'] == 259 and a['decoded_bytes'] == a['caller_released_bytes'] == (0 if cancelled else 259)
        assert a['scanned_bytes'] == (611 if timeout else 0)
        frames = {'presented': positive['frames']['presented'], 'decoded': None if cancelled else positive['frames']['decoded'],
                  'scanned': None, 'late_scan': positive['frames']['scanned'] if timeout else None}
        same(case['frames'], frames)
        same(case['decoded_request'], None if cancelled else positive['decoded_request'])
        if cancelled:
            same(case['cancel_refusals'], {'take_result_refused': True, 'reservation_before_close_refused': True, 'caller_released_bytes': 0})
        else:
            assert case['cancel_refusals'] is None
        assert collection['node_pid'] == a['node_pid'] and type(collection['node_wait_raw']) is int and collection['node_wait_raw'] == 0
        for key in ['node_EOF', 'parent_fd_before', 'parent_fd_after', 'runtime_strong_reference']:
            same(collection[key], positive['collection'][key])
        integers(collection['node_observed'].values())
        assert collection['node_observed']['stderr'] == 0
        o = collection['B3']; p = o['phase']; t = o['terminal']; wait = t['worker_wait']
        assert list(p) == ['v', 'kind', 'owner_pid', 'worker_pid', 'ppid', 'sid', 'pgid',
                           'exe_sha256', 'limits', 'G_bytes', 'image_bytes_sent', 'fds']
        assert list(t) == ['v', 'kind', 'owner_pid', 'outcome', 'ownership', 'worker_pid',
                          'worker_wait', 'worker_io', 'session_policy_verified', 'input_bytes_received',
                          'input_sha256', 'G_bytes', 'image_bytes_sent', 'stdout_observed', 'stdout_retained',
                          'stderr_observed', 'stderr_retained', 'worker_stderr_base64', 'result_bytes',
                          'result_sha256', 'final_worker_eligible', 'cancel_observed', 'timing']
        assert list(wait) == ['raw_status', 'exit_code', 'collector_pid']
        assert list(t['worker_io']) == ['stdin_closed', 'stdout_eof', 'stderr_eof', 'owned_fds_closed']
        assert list(p['limits']) == ['AS', 'CPU', 'CORE']
        # The positive block already binds these common policy values to Git and
        # the actual provisioned worker. Every refusal must preserve them.
        for key in ['state', 'EOF', 'parent_owned_fds', 'fault', 'transport_error', 'ready_hex', 'diagnostic_base64', 'closed']:
            same(o[key], reference[key])
        for key in ['v', 'kind', 'exe_sha256', 'limits', 'G_bytes', 'image_bytes_sent']:
            same(p[key], reference['phase'][key])
        for key in ['v', 'kind', 'ownership', 'worker_io', 'session_policy_verified']:
            same(t[key], reference['terminal'][key])
        integers([o[k] for k in ['owner_pid', 'owner_wait_raw', 'owner_exit_code', 'image_bytes_written', 'output_bytes']])
        integers([p[k] for k in ['owner_pid', 'worker_pid', 'ppid', 'sid', 'pgid']] + [f['fd'] for f in p['fds']])
        integers([t[k] for k in ['owner_pid', 'worker_pid', 'input_bytes_received', 'G_bytes', 'image_bytes_sent',
                                'stdout_observed', 'stdout_retained', 'stderr_observed', 'stderr_retained', 'result_bytes']])
        integers([wait[k] for k in ['raw_status', 'exit_code', 'collector_pid']])
        assert o['owner_pid'] == t['owner_pid'] == p['owner_pid'] == p['ppid'] == a['owner_pid']
        assert p['worker_pid'] == p['sid'] == p['pgid'] == t['worker_pid'] == a['worker_pid']
        assert wait['collector_pid'] == o['owner_pid'] and [f['fd'] for f in p['fds']] == [0, 1, 2]
        for fd in p['fds']:
            assert list(fd) == ['fd', 'target', 'dev', 'ino']
            decimal(fd['dev']); decimal(fd['ino'])
            assert fd['target'] == 'pipe:[' + fd['ino'] + ']' and len(fd['target']) <= 27
        assert len({(f['dev'], f['ino']) for f in p['fds']}) == 3
        assert o['commands'] == (['P', 'X'] if cancelled else ['P', 'G'])
        assert o['owner_exit_code'] == (2 if cancelled else 0) and o['owner_wait_raw'] == (512 if cancelled else 0)
        assert (wait['exit_code'], wait['raw_status']) in ({(71, 18176), (-9, 9)} if cancelled else {(0, 0)})
        assert o['taken'] is (not cancelled)
        for key in ['image_bytes_written']:
            same(o[key], reference[key])
        for key in ['input_bytes_received', 'input_sha256']:
            same(t[key], reference['terminal'][key])
        assert t['outcome'] == a['B3_outcome'] and t['cancel_observed'] is cancelled and t['final_worker_eligible'] is (not cancelled)
        assert t['G_bytes'] == (0 if cancelled else 1) and t['image_bytes_sent'] == (0 if cancelled else 172800)
        assert t['result_bytes'] == o['output_bytes'] == t['stdout_observed'] == t['stdout_retained'] == (0 if cancelled else 259)
        stderr = base64.b64decode(t['worker_stderr_base64'], validate=True)
        assert base64.b64encode(stderr).decode('ascii') == t['worker_stderr_base64']
        assert len(stderr) == t['stderr_retained'] == t['stderr_observed'] <= 512
        if cancelled:
            assert not stderr  # W exits71 before G, or is killed before G; neither emits diagnostics.
        else:
            for key in ['stderr_observed', 'stderr_retained', 'worker_stderr_base64']:
                same(t[key], reference['terminal'][key])
        same(o['output_sha256'], None if cancelled else reference['output_sha256'])
        same(t['result_sha256'], None if cancelled else reference['terminal']['result_sha256'])
        clock = t['timing']
        assert list(clock) == ['begin_ns', 'invalidated_ns', 'cleanup_deadline_ns', 'settled_ns', 'final_admission_ns']
        for value in clock.values():
            if value is not None:
                decimal(value)
        assert int(clock['begin_ns']) <= int(clock['settled_ns']) <= int(clock['final_admission_ns']) < int(clock['begin_ns']) + 8000000000
        if cancelled:
            assert int(clock['begin_ns']) <= int(clock['invalidated_ns']) <= int(clock['settled_ns'])
            assert int(clock['cleanup_deadline_ns']) == int(clock['invalidated_ns']) + 4000000000
        else:
            assert clock['invalidated_ns'] is clock['cleanup_deadline_ns'] is None
        status = base64.b64decode(o['status_wire_base64'], validate=True)
        assert base64.b64encode(status).decode('ascii') == o['status_wire_base64']
        assert len(status) <= 4096
        assert status == b''.join((json.dumps(row, separators=(',', ':')) + '\n').encode('ascii') for row in [p, t])
        same([json.loads(row) for row in status.splitlines()], [p, t])
        rows = case['node_records']
        events = ['present', 'close', 'result'] if cancelled else (['present', 'scan_pending', 'timeout', 'close', 'result'] if timeout else ['present', 'scan', 'close', 'result'])
        assert [row['event'] for row in rows] == events and all(type(row['v']) is int and row['v'] == 1 for row in rows)
        same(rows[0], positive['node_records'][0])
        same(rows[-2], {'v': 1, 'event': 'close'})
        if not cancelled and not timeout:
            same(rows[1], {'v': 1, 'event': 'scan', 'frame': None})
        final = rows[-1]
        same(final['timer_args'], [100]); same(final['clock_steps'], [0, 99, 100])
        same(final['clear_calls'], 1); same(final['deadline_fires'], 1 if timeout else 0)
        life = {'case': name, 'opens': 1, 'scans': 0 if cancelled else 1, 'closes': 1,
                'abort_observed': True, 'underlying_settled': True, 'late_scan_bytes': 611 if timeout else 0,
                'late_scan_sha256': positive['frames']['scanned']['sha256'] if timeout else None,
                'pending_retry_error': 'runtime_unavailable' if timeout else None}
        same(final['lifecycle'], life)
        assert final['native_response_base64'] == case['native_response_base64']
        if timeout:
            same(rows[1], {'v': 1, 'event': 'scan_pending', 'clock': 99})
            expected_timeout = {'v': 1, 'event': 'timeout', 'native_response_base64': case['native_response_base64'],
                                'timer_args': [100], 'clear_calls': 1, 'deadline_fires': 1, 'clock': 100,
                                'opens': 1, 'scans': 1, 'closes': 0, 'abort_observed': True,
                                'underlying_settled': False, 'pending_retry_error': 'runtime_unavailable'}
            same(rows[2], expected_timeout)
        wire_rows = [(json.dumps(row, separators=(',', ':')) + '\n').encode('ascii') for row in rows]
        assert max(map(len, wire_rows)) <= 2048 and sum(map(len, wire_rows)) == collection['node_observed']['stdout'] <= 4096
        native = base64.b64decode(case['native_response_base64'], validate=True)
        assert base64.b64encode(native).decode('ascii') == case['native_response_base64'] and len(native) >= 4
        assert int.from_bytes(native[:4], 'little') == len(native) - 4
        same(json.loads(native[4:]), case['service_response'])
        service = case['service_response']
        assert type(service['version']) is int and service['version'] == 1 and service['ok'] is False and 'result' not in service
        assert service['request_id'] == positive['service_response']['request_id'] and service['error']['code'] == error
        assert service['error']['retryable'] is False and type(service['error']['message']) is str
    return {'qh01_automatic_lifecycle_cases': ids, 'qh01_lifecycle_original_actor_statuses_and_source_bound': True,
            'qh01_lifecycle_timeout_close0_then_close1_verified': True, 'qh01_lifecycle_precancel_API_release_bytes': 0,
            'qh01_lifecycle_limits': 'Fixed trusted host fixtures; synthetic client100 and actual O8/shared4. No decoder counter, external clientAbort/UI, camera/physical/key/provider qualification.'}


def verify_qh01_request_engine(objects, head, repo):
    """Check the joined helper build and both real-engine host CI records."""
    def same(actual, expected):
        assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
    def integers(values):
        assert all(type(v) is int and abs(v) <= 9007199254740991 for v in values)
    def decimal(value):
        assert type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value)
        assert int(value) <= 18446744073709551615
    def occurrences(key):
        return [(i, o[key]) for i, o in enumerate(objects) if key in o]
    def one(key):
        rows = occurrences(key)
        assert len(rows) == 1
        return rows[0]
    def blob(path):
        return subprocess.check_output(['git', '-C', repo, 'show', head + ':' + path])
    def sha(data):
        return hashlib.sha256(data).hexdigest()
    _, positive = one('qh01_composition_case')
    natives = [o for o in objects if o.get('role') == 'public fixture build, not hardware qualification']
    assert len(natives) == 1
    native = natives[0]
    bridge_builds = occurrences('bridge_service_build')
    assert bridge_builds
    bridge_build = bridge_builds[0][1]
    command_at, command = one('qh01_request_engine_build_command')
    build_at, build = one('qh01_request_engine_build')
    prior = occurrences('qh01_lifecycle_case')
    assert len(prior) == 3 and prior[-1][0] < command_at < build_at
    assert not occurrences('qh01_request_engine_build_failure') and not occurrences('qh01_request_engine_failure')
    integers([command['v'], build['v'], build['status']])
    assert command['v'] == build['v'] == 1 and build['status'] == 0
    assert build['scope'] == 'QH01_NATIVE_LEAF_PREPARATION_V1' and build['role'] == 'current_checkout_joined_compiler_artifacts_only'
    root, output = Path(build['cwd']), Path(build['output_dir'])
    assert build['cwd'] == bridge_build['cwd']
    assert root.is_absolute() and '..' not in root.parts
    assert output.is_absolute() and output.name == 'module' and output.parent.name.startswith('nsealr-qh01-native-leaf-')
    assert build['receipt'] == str(output.parent / 'preparation.json')
    leaf = 'docs/restart/implementation/QP01/request-engine/native-leaf.ts'
    source = [leaf, 'package.json', 'pnpm-lock.yaml']
    bindings = {p: sha(blob(p)) for p in source}
    same(build['source_before'], bindings); same(build['source_after'], bindings)
    options = ['pnpm', 'exec', 'tsc', '--ignoreConfig', '--target', 'ES2022', '--module', 'NodeNext',
               '--moduleResolution', 'NodeNext', '--strict', '--esModuleInterop', '--forceConsistentCasingInFileNames',
               '--skipLibCheck', '--resolveJsonModule', '--types', 'node', '--declaration', '--rootDir',
               'docs/restart/implementation/QP01/request-engine', '--outDir', str(output), leaf]
    same(build['argv'], options)
    same(command, {'v': 1, 'argv': options, 'cwd': str(root), 'output_dir': str(output)})
    compiler = build['compiler']
    same(compiler, bridge_build['compiler'])
    assert compiler['version'] == json.loads(blob('package.json'))['devDependencies']['typescript'] == '6.0.3'
    assert Path(compiler['path']).is_relative_to(root / 'node_modules') and compiler['path'].endswith('/typescript/bin/tsc')
    assert re.fullmatch('[0-9a-f]{64}', compiler['sha256'])
    assert list(build['outputs']) == ['native-leaf.js', 'native-leaf.d.ts']
    for name, item in build['outputs'].items():
        assert list(item) == ['path', 'bytes', 'sha256'] and item['path'] == str(output / name)
        integers([item['bytes']]); assert item['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', item['sha256'])
    context = b'{"type":"module"}\n'
    same(build['package_context'], {'path': str(output / 'package.json'), 'bytes': len(context),
                                   'sha256': sha(context), 'value': {'type': 'module'}})
    ids = ['fixture_request_engine', 'fixture_request_engine_loaded_sha_refusal']
    commands, results, cases = [occurrences(k) for k in ['qh01_request_engine_command', 'qh01_request_engine_result', 'qh01_request_engine_case']]
    assert len(commands) == len(results) == len(cases) == 2
    assert [c['id'] for _, c in commands] == [c['id'] for _, c in cases] == ids
    assert len({positive['argv'][4], *[c['argv'][4] for _, c in cases],
                *[c['argv'][4] for _, c in occurrences('qh01_lifecycle_case')]}) == 6
    extra = ['docs/restart/implementation/QP01/request-engine/' + p for p in ['native-leaf.ts', 'client-exchange.ts', 'expectations.json']]
    extra += ['apps/pi/app/nsealr_vault/engine_adapter.py', 'Cargo.toml', 'Cargo.lock',
              'crates/nsealr-pi-engine-fixture/Cargo.toml', 'crates/nsealr-pi-engine-fixture/src/lib.rs']
    expected_source = {**positive['source_before'], **{p: sha(blob(p)) for p in extra}}
    assert len(positive['source_before']) == 60 and len(expected_source) == 68
    expectation = next(row for row in json.loads(blob('docs/restart/implementation/QP01/request-engine/expectations.json'))['independent_positive_expectations'] if row['id'] == 'basic')
    response_sha = '250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded'
    prior = build_at
    ref = positive['collection']['B3']
    for index, ((ci, cmd), (ri, actual_result), (di, case)) in enumerate(zip(commands, results, cases)):
        assert prior < ci < ri < di
        prior = di
        refused = index == 1
        mode = 'loaded-sha-refusal' if refused else 'positive'
        integers([cmd['v'], case['v']]); assert cmd['v'] == case['v'] == 1
        assert case['scope'] == 'QH01_RGB_ENGINE_CI_V1' and case['role'] == positive['role']
        for key in ['source_before', 'source_after']: same(case[key], expected_source)
        for key in ['generated_before', 'generated_after', 'worker_initialization', 'expected_public_key']:
            same(case[key], positive[key])
        argv = case['argv']
        same(argv, cmd['argv']); assert argv[:4] == positive['argv'][:4] and argv[4] == cmd['output']
        case_output = Path(argv[4])
        assert case_output.is_absolute() and case_output.name == 'case' and case_output.parent.name.startswith('nsealr-qh01-composition-')
        suffix = ['--case', ids[0], '--engine-library', native['library'], '--engine-sha256', native['sha256'],
                  '--engine-module', build['outputs']['native-leaf.js']['path'], '--engine-module-sha256',
                  build['outputs']['native-leaf.js']['sha256'], '--engine-preparation', build['receipt']]
        same(argv[5:], positive['argv'][5:] + suffix + (['--engine-refusal'] if refused else []))
        same(case['native_preparation'], build)
        same(case['native_preparation_after'], {'source': bindings, 'compiler_sha256': compiler['sha256'],
                                               'outputs': build['outputs'], 'package_context_sha256': sha(context)})
        a = case['actual']; collection = case['collection']; outcome = case['native_outcome']; status = case['native_settlement']
        same(actual_result, a)
        assert a['result'] == 'PASS_FIRST_HOST_RGB_REQUEST_ENGINE_ONLY' and a['case'] == ids[0] and a['mode'] == mode and a['physical_claim'] is False
        pids = [a[k] for k in ['parent_pid', 'node_pid', 'owner_pid', 'worker_pid', 'C_pid']]
        integers(pids); assert min(pids) > 1 and len(set(pids)) == 5
        integers([a[k] for k in ['presented_bytes', 'decoded_bytes', 'scanned_bytes', 'caller_released_bytes', 'C_code']])
        assert a['worker_sha256'] == positive['worker_initialization']['sha256']
        assert a['presented_bytes'] == a['decoded_bytes'] == a['caller_released_bytes'] == 259
        assert a['scanned_bytes'] == (0 if refused else 611) and a['C_code'] == int(refused) and a['C_signal'] is None
        same(a['service_error'], 'signer_transport_failed' if refused else None)
        expected_frame = None if refused else {'bytes': 611, 'sha256': response_sha}
        same(case['frames'], {'presented': positive['frames']['presented'], 'decoded': positive['frames']['decoded'],
                              'scanned': expected_frame, 'engine_response': expected_frame})
        same(case['decoded_request'], positive['decoded_request'])
        cfg = case['native_initialization']; child_sha = native['sha256']
        if refused: child_sha = ('1' if child_sha[0] == '0' else '0') + child_sha[1:]
        same(cfg, {'v': 1, 'scope': 'QH01_RGB_ENGINE_OPT_IN_V1', 'mode': mode, 'source_root': str(root),
                   'output_dir': str(case_output), 'python': argv[0], 'library': native['library'],
                   'library_sha256': native['sha256'], 'child_expected_sha256': child_sha,
                   'module': build['outputs']['native-leaf.js']['path'], 'module_sha256': build['outputs']['native-leaf.js']['sha256'],
                   'module_source_sha256': bindings[leaf]})
        assert collection['node_pid'] == a['node_pid'] and type(collection['node_wait_raw']) is int and collection['node_wait_raw'] == 0
        for key in ['node_EOF', 'parent_fd_before', 'parent_fd_after', 'runtime_strong_reference']: same(collection[key], positive['collection'][key])
        integers(collection['node_observed'].values()); assert collection['node_observed']['stderr'] == 0
        o = collection['B3']; p = o['phase']; t = o['terminal']; wait = t['worker_wait']
        for key in ['state', 'owner_wait_raw', 'owner_exit_code', 'commands', 'EOF', 'image_bytes_written', 'output_bytes',
                    'output_sha256', 'diagnostic_base64', 'ready_hex', 'fault', 'transport_error', 'parent_owned_fds', 'taken', 'closed']:
            same(o[key], ref[key])
        assert list(p) == ['v', 'kind', 'owner_pid', 'worker_pid', 'ppid', 'sid', 'pgid',
                           'exe_sha256', 'limits', 'G_bytes', 'image_bytes_sent', 'fds']
        assert list(t) == ['v', 'kind', 'owner_pid', 'outcome', 'ownership', 'worker_pid',
                          'worker_wait', 'worker_io', 'session_policy_verified', 'input_bytes_received',
                          'input_sha256', 'G_bytes', 'image_bytes_sent', 'stdout_observed', 'stdout_retained',
                          'stderr_observed', 'stderr_retained', 'worker_stderr_base64', 'result_bytes',
                          'result_sha256', 'final_worker_eligible', 'cancel_observed', 'timing']
        assert list(wait) == ['raw_status', 'exit_code', 'collector_pid']
        assert list(p['limits']) == ['AS', 'CPU', 'CORE']
        assert list(t['worker_io']) == ['stdin_closed', 'stdout_eof', 'stderr_eof', 'owned_fds_closed']
        integers([o['owner_pid'], p['owner_pid'], p['worker_pid'], p['ppid'], p['sid'], p['pgid'], t['owner_pid'], t['worker_pid'], wait['collector_pid']])
        assert o['owner_pid'] == p['owner_pid'] == p['ppid'] == t['owner_pid'] == wait['collector_pid'] == a['owner_pid']
        assert p['worker_pid'] == p['sid'] == p['pgid'] == t['worker_pid'] == a['worker_pid']
        for key in ['v', 'kind', 'exe_sha256', 'limits', 'G_bytes', 'image_bytes_sent']: same(p[key], ref['phase'][key])
        assert len(p['fds']) == 3 and len({(fd['dev'], fd['ino']) for fd in p['fds']}) == 3
        for i, fd in enumerate(p['fds']):
            assert list(fd) == ['fd', 'target', 'dev', 'ino']
            integers([fd['fd']]); assert fd['fd'] == i
            decimal(fd['dev']); decimal(fd['ino']); assert fd['target'] == 'pipe:[' + fd['ino'] + ']' and len(fd['target']) <= 27
        integers([o[k] for k in ['owner_wait_raw', 'owner_exit_code', 'image_bytes_written', 'output_bytes']])
        integers([p[k] for k in ['v', 'G_bytes', 'image_bytes_sent']] + list(p['limits'].values()))
        integers([t[k] for k in ['v', 'input_bytes_received', 'G_bytes', 'image_bytes_sent', 'stdout_observed',
                                'stdout_retained', 'stderr_observed', 'stderr_retained', 'result_bytes']])
        integers([wait['raw_status'], wait['exit_code']])
        for key in ref['terminal']:
            if key not in ['owner_pid', 'worker_pid', 'worker_wait', 'timing']: same(t[key], ref['terminal'][key])
        same(wait['raw_status'], 0); same(wait['exit_code'], 0)
        timing = t['timing']; assert list(timing) == ['begin_ns', 'invalidated_ns', 'cleanup_deadline_ns', 'settled_ns', 'final_admission_ns']
        for key in ['begin_ns', 'settled_ns', 'final_admission_ns']: decimal(timing[key])
        assert timing['invalidated_ns'] is timing['cleanup_deadline_ns'] is None
        assert int(timing['begin_ns']) <= int(timing['settled_ns']) <= int(timing['final_admission_ns']) < int(timing['begin_ns']) + 8000000000
        wire = base64.b64decode(o['status_wire_base64'], validate=True)
        assert base64.b64encode(wire).decode('ascii') == o['status_wire_base64'] and len(wire) <= 4096
        assert wire == b''.join((json.dumps(row, separators=(',', ':')) + '\n').encode('ascii') for row in [p, t])
        assert list(status) == ['pid', 'code', 'signal', 'synthetic_handshake_control', 'sent', 'readiness_hex',
                                'stdout_bytes', 'stderr_bytes', 'overflow', 'initialization_ns', 'request_to_close_ns']
        integers([status[k] for k in ['pid', 'code', 'stdout_bytes', 'stderr_bytes']])
        assert status['pid'] == a['C_pid'] and status['code'] == int(refused) and status['signal'] is None
        assert status['synthetic_handshake_control'] is status['overflow'] is False and status['sent'] is (not refused)
        assert status['readiness_hex'] == ('' if refused else '52') and status['stdout_bytes'] == (0 if refused else 611)
        assert 0 < status['stderr_bytes'] <= 262144
        for key in ['initialization_ns', 'request_to_close_ns']:
            if refused: assert status[key] is None
            else: decimal(status[key])
        integers([outcome[k] for k in ['node_pid', 'spawned', 'collected', 'capability_calls', 'timer_clears', 'response_bytes', 'observation_count']])
        assert outcome['scope'] == 'QH01_RGB_ENGINE_OPT_IN_V1' and outcome['node_pid'] == a['node_pid']
        assert outcome['spawned'] == outcome['collected'] == outcome['capability_calls'] == outcome['timer_clears'] == 1
        same(outcome['timer_args'], [5000]); assert outcome['children_before'] == outcome['children_after'] == ''
        assert set(outcome['fds_before']) >= {'0', '1', '2'}; same(outcome['fds_before'], outcome['fds_after'])
        for fd, info in outcome['fds_before'].items():
            assert re.fullmatch(r'0|[1-9][0-9]*', fd) and list(info) == ['dev', 'ino', 'target']
            decimal(info['dev']); decimal(info['ino']); assert type(info['target']) is str
        same(outcome['spawn'], {'python': argv[0], 'argv': ['-B', str(root / 'docs/restart/implementation/QP01/request-engine/exchange.py'), '--ready-fd', '4'],
                                'cwd': str(root), 'pid': a['C_pid'], 'initialization': {'library': native['library'], 'sha256': child_sha}})
        assert outcome['response_bytes'] == (0 if refused else 611) and outcome['observation_count'] == (0 if refused else 1)
        assert outcome['readiness_refusal'] is refused; same(outcome['response_sha256'], None if refused else response_sha)
        rows = case['node_records']; assert [row['event'] for row in rows] == (['present', 'close', 'result'] if refused else ['present', 'scan', 'close', 'result'])
        assert all(type(row['v']) is int and row['v'] == 1 for row in rows)
        same(rows[0], positive['node_records'][0]); same(rows[-2], {'v': 1, 'event': 'close'})
        final = rows[-1]; same(final['timer_args'], [100]); same(final['clear_calls'], 1); same(final['deadline_fires'], 0); same(final['clock_steps'], [0, 99, 100])
        same(final['engine'], {'mode': mode, 'spawned': 1, 'collected': 1, 'capability_calls': 1, 'pid': a['C_pid'],
                               'code': int(refused), 'signal': None, 'timer_args': [5000], 'timer_clears': 1,
                               'children_after': '', 'fd_restored': True})
        assert final['native_response_base64'] == case['native_response_base64']
        encoded = [(json.dumps(row, separators=(',', ':')) + '\n').encode('ascii') for row in rows]
        assert max(map(len, encoded)) <= 2048 and sum(map(len, encoded)) == collection['node_observed']['stdout'] <= 4096
        native_wire = base64.b64decode(case['native_response_base64'], validate=True)
        assert base64.b64encode(native_wire).decode('ascii') == case['native_response_base64'] and len(native_wire) >= 4
        assert int.from_bytes(native_wire[:4], 'little') == len(native_wire) - 4
        same(json.loads(native_wire[4:]), case['service_response'])
        assert native_wire[4:] == json.dumps(case['service_response'], separators=(',', ':')).encode('ascii')
        service = case['service_response']; assert service['request_id'] == positive['service_response']['request_id']
        if refused:
            same(service, {'version': 1, 'request_id': service['request_id'], 'ok': False,
                           'error': {'code': 'signer_transport_failed', 'message': 'fixture native loaded-SHA readiness refusal', 'retryable': False}})
            assert case['native_observation'] is None and case['native_refusal']['name'] == 'Error'
            assert 'native library SHA256 mismatch' in case['native_refusal']['message']
        else:
            frame = rows[1]['frame'].encode('ascii'); assert len(frame) == 611 and sha(frame) == response_sha
            same(service, {'version': 1, 'request_id': service['request_id'], 'ok': True, 'result': {'signer_response': {
                 'version': 2, 'request_id': expectation['request_id'], 'ok': True, 'result': {'event': expectation['expected_complete_event']}}}})
            assert case['expected_public_key'] == expectation['expected_pubkey'] and case['native_refusal'] is None
            obs = case['native_observation']
            legacy = [o['native_observation'] for o in objects if 'native_observation' in o and
                      o['native_observation']['input_sha256'] == positive['frames']['decoded']['sha256'] and o['native_observation']['output_sha256'] == response_sha]
            assert legacy and all(json.dumps(item, sort_keys=True) == json.dumps(obs, sort_keys=True) for item in legacy)
            assert obs['library'] == native['library'] and obs['sha256'] == native['sha256']
            integers([obs['input_bytes'], obs['output_bytes']]); assert obs['input_bytes'] == 259 and obs['output_bytes'] == 611
            pages = obs['synthetic_complete_review']; assert len(pages) == 31
            for i, page in enumerate(pages):
                integers([page['kind'], page['index'], page['total']]); assert page['index'] == i and page['total'] == 31 and page['position'] == f'{i + 1}/31'
            assert len((json.dumps(obs) + '\n').encode('ascii')) == status['stderr_bytes']
    return {'qh01_automatic_request_engine_cases': ids, 'qh01_current_root_native_leaf_builds': 1,
            'qh01_request_engine_source_bindings': 68, 'qh01_request_engine_actual_C_close_and_FD_restore': True,
            'qh01_request_engine_complete_review_pages': 31, 'qh01_request_engine_actual_response_sha256': response_sha,
            'qh01_request_engine_refusal_C_input_and_output_bytes': 0,
            'qh01_request_engine_limits': 'Host public fixtures/trusted synthetic review and source-configured auxiliary only. Real C5000 scheduling, no rawCwait/hard collection bound or combined expiry/clientAbort/physical/provider qualification.'}


def verify_python_owner(objects, worker, head, repo):
    """Verify source-bound automatic cases; helper PIDs are never worker proof."""
    def blob(path):
        return subprocess.check_output(['git', '-C', repo, 'show', head + ':' + path])
    prefix = 'docs/restart/implementation/QP01/python-owner-adapter/negative/'
    expected = json.loads(blob(prefix + 'expectations.json'))
    source_paths = ['apps/pi/app/nsealr_vault/qr_owner_adapter.py',
                    'apps/pi/tests/test_qr_owner_adapter.py',
                    'apps/pi/tests/test_qr_owner_adapter_lifecycle.py', prefix + 'expectations.json']
    bindings = {p: hashlib.sha256(blob(p)).hexdigest() for p in source_paths}
    assert bindings[source_paths[0]] == PYTHON_OWNER_ADAPTER_SHA256
    rows = [o['python_owner_case'] for o in objects if 'python_owner_case' in o]
    assert len(rows) == 70
    negatives = {r['id']: r for r in expected['real_lifecycle_cases']}
    assert set(negatives) == {'unused_Q', 'cancel_preP', 'cancel_preG', 'late_discard',
                             'wall8_preG', 'invalid_Z', 'duplicate_PP', 'premature_G', 'control_EOF_preG'}
    positive = expected['automatic_positive_case']
    assert positive['id'] == 'normal259_release_once'
    helpers = {'FG7_' + r['mode']: r for r in expected['helper_cases']}
    relations = set(expected['pure_relation_cases'])
    assert len(helpers) == 11 and len(relations) == 9
    expected_events = {}
    for case in negatives:
        events = ['ready', 'observed-terminal', 'settled']
        if case in {'cancel_preG', 'late_discard', 'wall8_preG', 'control_EOF_preG'}:
            events.append('phase')
        if case in {'invalid_Z', 'duplicate_PP', 'premature_G'}:
            events.append('wire-injected')
        expected_events.update({(case, event): 1 for event in events})
    expected_events.update({(positive['id'], event): 1 for event in ['ready', 'phase', 'released']})
    expected_events.update({(case, event): 1 for case in helpers
                           for event in ['observed-collected', 'rejected-collected']})
    expected_events.update({(case, 'rejected'): 1 for case in relations | {'types-canonicality', 'pipe-cap'}})
    assert collections.Counter((r['id'], r['event']) for r in rows) == expected_events
    finals = {r['id']: r for r in rows if r['event'] in {'settled', 'released'}}
    owners, workers = set(), set()
    for case, row in finals.items():
        o = row['observation']; t = o['terminal']
        assert o['state'] == 'settled' and o['EOF'] == [1, 2, 4, 5] and o['parent_owned_fds'] == []
        assert o['fault'] is None and o['transport_error'] is None and o['diagnostic_base64'] == ''
        assert o['ready_hex'] == '52' and t['owner_pid'] == o['owner_pid']
        assert type(o['owner_pid']) is int and o['owner_pid'] > 1 and o['owner_pid'] not in owners
        owners.add(o['owner_pid'])
        assert all(type(o[k]) is int for k in ['owner_wait_raw', 'owner_exit_code', 'output_bytes'])
        assert type(row['caller_released_bytes']) is int
        assert all(type(t[k]) is int for k in ['G_bytes', 'image_bytes_sent', 'input_bytes_received', 'result_bytes'])
        assert t['ownership'] == 'settled' and t['worker_io']['owned_fds_closed'] is True
        assert o['owner_wait_raw'] == o['owner_exit_code'] * 256
        if case in negatives:
            e = negatives[case]
            assert row['role'] == 'actual_O_W_lifecycle' and row['caller_released_bytes'] == 0
            assert t['outcome'] == e['terminal_outcome'] and o['owner_exit_code'] == e['O_exit']
            assert o['output_bytes'] == e['O_private_bytes'] and o['taken'] is False
            assert t['cancel_observed'] is e['O_cancel_observed']
        else:
            assert row['role'] == 'actual_O_W_positive_single_use' and row['caller_released_bytes'] == 259
            assert row['second_take_refused'] is True and row['reservation_before_close_refused'] is True
            assert t['outcome'] == 'decoded' and o['owner_exit_code'] == 0 and o['taken'] is True
        if t['worker_pid'] is None:
            assert o['phase'] is None and t['worker_wait'] is None
            assert case in negatives and negatives[case]['W_count'] == 0
        else:
            p = o['phase']; pid = t['worker_pid']; wait = t['worker_wait']
            assert type(pid) is int and pid > 1 and pid not in workers
            workers.add(pid)
            assert p['worker_pid'] == pid and p['owner_pid'] == p['ppid'] == o['owner_pid']
            assert p['sid'] == p['pgid'] == pid and p['exe_sha256'] == worker['sha256']
            assert p['limits'] == {'AS': [268435456, 268435456], 'CPU': [1, 2], 'CORE': [0, 0]}
            assert p['G_bytes'] == p['image_bytes_sent'] == 0 and [f['fd'] for f in p['fds']] == [0, 1, 2]
            assert wait['collector_pid'] == o['owner_pid']
            assert all(type(wait[k]) is int for k in ['raw_status', 'exit_code', 'collector_pid'])
            assert all(t['worker_io'][k] is True for k in ['stdin_closed', 'stdout_eof', 'stderr_eof'])
            if case in {'cancel_preG', 'wall8_preG', 'control_EOF_preG'}:
                assert (wait['exit_code'], wait['raw_status']) in {(71, 18176), (-9, 9)}
                assert t['G_bytes'] == t['image_bytes_sent'] == 0
            else:
                assert wait['exit_code'] == wait['raw_status'] == 0
        if t['outcome'] == 'decoded':
            assert t['result_bytes'] == o['output_bytes'] == 259
            assert t['result_sha256'] == o['output_sha256'] == positive['expected_result_sha256']
            assert t['input_bytes_received'] == t['image_bytes_sent'] == 172800
            assert t['input_sha256'] == positive['input_sha256'] and t['G_bytes'] == 1
        else:
            assert t['result_bytes'] == o['output_bytes'] == 0
    assert len(owners) == 10 and len(workers) == 5 and owners.isdisjoint(workers)
    wall = finals['wall8_preG']['observation']['terminal']['timing']
    assert int(wall['invalidated_ns']) >= int(wall['begin_ns']) + 8000000000
    assert int(wall['cleanup_deadline_ns']) == int(wall['invalidated_ns']) + 4000000000
    helper_pids = set()
    for row in rows:
        case = row['id']
        if row['event'] == 'rejected-collected':
            e = helpers[case]; o = row['observation']; pid = o['owner_pid']
            assert row['role'] == 'actual_exact_no_W_helper_only_not_worker_PASS'
            assert all(type(o[k]) is int for k in ['owner_wait_raw', 'owner_exit_code', 'output_bytes'])
            assert type(row['actual_W_count']) is type(row['caller_released_bytes']) is int
            assert row['actual_W_count'] == row['caller_released_bytes'] == o['output_bytes'] == 0
            assert o['state'] == 'quarantined' and o['owner_wait_raw'] == o['owner_exit_code'] == 0
            assert o['EOF'] == [1, 2, 4, 5] and o['ready_hex'] == e['expected_ready_hex']
            assert o['commands'] == [e['intended_control']] and o['diagnostic_base64'] == ''
            assert row['helper_sha256'] == e['sha256'] == hashlib.sha256(blob(e['path'])).hexdigest()
            assert pid not in helper_pids and pid not in owners | workers and type(pid) is int and pid > 1
            helper_pids.add(pid)
        elif row['event'] == 'rejected':
            if case in relations:
                assert row['role'] == 'PURE_SYNTHETIC_RELATION_ZERO_PROCESSES' and row['fabricated_PIDs'] == [10001, 10002]
            elif case == 'types-canonicality':
                assert row['role'] == 'PURE_WIRE_DATA_ZERO_PROCESSES' and row['rejected_controls'] == 27
            else:
                assert case == 'pipe-cap' and row['role'] == 'REAL_PIPE_ONLY_ZERO_CHILDREN'
                assert row['retained_bytes'] == 513 and row['payload_cap'] == 512
    assert len(helper_pids) == 11
    return {'python_owner_source_bindings': bindings, 'python_owner_telemetry_rows': len(rows),
            'python_owner_actual_owners': 10, 'python_owner_actual_workers': 5,
            'python_owner_actual_no_worker_helpers': 11, 'python_owner_pure_relations': 9,
            'python_owner_pure_wire_rejections': 27, 'python_owner_positive_bytes_released_once': 259,
            'python_owner_negative_bytes_released': 0, 'python_owner_wall8_from_actual_begin_verified': True,
            'python_owner_limits': 'Host public-fixture component only; synthetic parser PIDs are not processes. No physical or production qualification.'}

def verify_first(objects,b,head,repo):
    # Only this new candidate's completed logs use initialization v2 and third graph.
    worker_builds=[o for o in objects if o.get('role')=='public RGB worker build, initialization v2, not hardware qualification']
    assert len(worker_builds)==1
    w=worker_builds[0]
    assert w['argv']==['cargo','build','--manifest-path','apps/pi/qr-worker/Cargo.toml','--locked','--offline','--release','--message-format=json']
    worker_paths={'apps/pi/qr-worker/'+p for p in ['Cargo.toml','Cargo.lock','src/main.rs','rust-toolchain.toml']}|{'.cargo/config.toml','rust-toolchain.toml'}
    assert set(w['source'])==worker_paths
    for path,digest in w['source'].items():
        assert hashlib.sha256(subprocess.check_output(['git','-C',repo,'show',head+':'+path])).hexdigest()==digest
    assert w['source']['apps/pi/qr-worker/src/main.rs']=='e60b3bc2baec2eded7ee474e101cfa8debd1a88be76d6d7cffce31b4e3e1dcf1'
    assert Path(w['worker']).is_absolute() and w['worker'].endswith('/release/nsealr-qr-worker')
    assert re.fullmatch('[0-9a-f]{64}',w['sha256'])
    if w['CARGO_TARGET_DIR'] is not None: assert Path(w['worker']).is_relative_to(w['CARGO_TARGET_DIR'])
    unit=subprocess.check_output(['git','-C',repo,'show',head+':apps/pi/tests/test_qr_worker.py'])
    assert hashlib.sha256(unit).hexdigest()==WORKER_UNIT_SOURCE_SHA256
    contract=json.loads(subprocess.check_output(['git','-C',repo,'show',head+':docs/restart/implementation/QP01/host-coordinator/control-contract.json']))
    assert contract['schema_version']==2 and contract['initialization']['version']==2
    assert contract['other_unchanged_bounds']['client_real_deadline_ms']==100
    assert contract['other_unchanged_bounds']['C_safety_from_spawn_ms']==5000
    cases={o['case'] for o in objects if 'case' in o}
    assert cases==EXPECTED_FIRST_CASES
    assert {o['case'] for o in objects if o.get('pass') is True and 'case' in o}==EXPECTED_FIRST_CASES
    case_rows=[o for o in objects if 'case' in o]
    assert collections.Counter(o['case'] for o in case_rows)==EXPECTED_CASE_ROW_COUNTS
    final_cases=[o for o in case_rows if 'pass' in o]
    assert len(final_cases)==39 and all(o['pass'] is True for o in final_cases)
    assert collections.Counter(o['case'] for o in final_cases)==dict.fromkeys(EXPECTED_FIRST_CASES,1)
    summary=[o for o in objects if o.get('scope')=='FG0_through_FG7_host_author_only']
    assert len(summary)==1 and summary[0]['groups']==8 and summary[0]['pass'] is True
    first=[o for o in objects if o.get('scope')=='first_owner_gate_C']
    assert len(first)==1
    for key,value in {'children':21,'collected':21,'native_reports':3}.items(): assert first[0][key]==value
    original_children=[o['child_settlement'] for o in objects if 'child_settlement' in o]
    assert len(original_children)==19
    assert sum(o['scope']=='readiness_controls' for o in original_children)==5
    assert sum(o['scope']=='actual_client' for o in original_children)==14
    cs=[o['first_owner_child_settlement'] for o in objects if 'first_owner_child_settlement' in o]
    osettled=[o['owner_settlement'] for o in objects if 'owner_settlement' in o]
    phases=[o['owner_phase'] for o in objects if 'owner_phase' in o]
    assert len(cs)==21 and len(osettled)==32 and len(phases)==11
    assert all(o['scope']=='first_owner_gate_C' for o in cs)
    assert len({o['pid'] for o in cs+osettled}|{p['worker_pid'] for p in phases})==64
    assert sum(o['synthetic_no_W_helper'] is True for o in osettled)==11
    phase_by_pid={p['worker_pid']:p for p in phases}
    assert len(phase_by_pid)==11
    for phase in phases:
        assert phase['exe_sha256']==w['sha256']
        assert phase['ppid']==phase['owner_pid'] and phase['sid']==phase['pgid']==phase['worker_pid']
        assert phase['limits']==contract['worker_ready_record']['limits']
        assert [fd['fd'] for fd in phase['fds']]==[0,1,2]
        assert phase['G_bytes']==phase['image_bytes_sent']==0
    actual_w=[]
    for owner in osettled:
        assert owner['signal'] is None and owner['readyEOF'] and owner['statusEOF'] and owner['outEOF'] and owner['errEOF']
        if owner['synthetic_no_W_helper']: continue # Bad terminal worker99 is no actual W.
        assert owner['protocol_error'] is None and owner['diagnostic_base64']==''
        terminal=owner['terminal']; assert terminal['owner_pid']==owner['pid']
        assert terminal['ownership']=='settled' and terminal['worker_io']['owned_fds_closed'] is True
        if terminal['worker_pid'] is None:
            assert terminal['worker_wait'] is None
        else:
            pid=terminal['worker_pid'];actual_w.append(pid); assert pid in phase_by_pid
            assert phase_by_pid[pid]['owner_pid']==owner['pid']
            wait=terminal['worker_wait'];raw=wait['raw_status'];low=raw&127
            assert isinstance(raw,int) and 0<=raw<=65535 and low!=127 and raw!=65535
            assert wait['collector_pid']==owner['pid'] and wait['exit_code']==(((raw>>8)&255) if low==0 else -low)
            assert all(terminal['worker_io'][k] is True for k in ['stdin_closed','stdout_eof','stderr_eof'])
            if terminal['outcome']=='decoded': assert terminal['result_sha256']==contract['independent_oracle']['decoded_frame_sha256']
    assert len(actual_w)==11 and set(actual_w)==set(phase_by_pid)
    first_native=[o['first_owner_native_observation'] for o in objects if 'first_owner_native_observation' in o]
    assert len(first_native)==3
    assert all(o['library']==b['library'] and o['sha256']==b['sha256'] for o in first_native)
    clock=[o['synchronous_deadline_guard'] for o in objects if 'synchronous_deadline_guard' in o]
    assert len(clock)==1
    clock=clock[0]
    assert clock['type']=='CapabilityError' and clock['reason']=='runtime_unavailable'
    assert clock['signal_aborted'] is False and clock['actual_hold_ms']>=110
    assert clock['W_O_collected'] is True and clock['private_decoded_bytes']==259 and clock['C_input_bytes']==0
    return {'worker_build':w,'first_owner_cases':len(cases),'first_owner_actual_children':64,
     'first_owner_W':11,'first_owner_native_reports':3,'trusted_initialization_version':2,
     'source_exact_five_added_Pi_unit_controls':True,'real_synchronous_deadline_guard':clock,
     'generic_completed_capture_checker_remains_separately_mandatory':True}

if __name__=='__main__':
    capture,head,repo=sys.argv[1:]
    capture=Path(capture)
    run=json.loads((capture/'run.json').read_bytes())
    assert run['head_sha']==head and run['status']=='completed' and run['conclusion']=='success'
    with zipfile.ZipFile(capture/'logs.zip') as z:
        names=[n for n in z.namelist() if n.startswith('verify/') and '/5_Complete product acceptance' in n]
        assert len(names)==1
        raw=z.read(names[0])
    print(json.dumps(verify_product(raw,head,repo,run['id']),indent=2))
