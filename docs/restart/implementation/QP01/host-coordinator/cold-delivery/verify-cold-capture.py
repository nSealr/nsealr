"""Proposed affected source-aware capture checker for the cold host gate only.

Derived from the existing PR45/46 verifier; original generic completed-capture
verifier stays separately mandatory and unchanged. This proposal never polls,
triggers CI, or retroactively changes expectations for historical captures.
CLI: CAPTURE_DIRECTORY SOURCE_HEAD REPOSITORY.
"""
from pathlib import Path
import collections,hashlib,json,re,subprocess,sys,zipfile

ORIGIN_SHA256 = "1e71c5f9d88e0eb614b5679185485e3c556841e0074a80f4b04270cb3e4d030e"
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
    assert sum(bool(re.fullmatch(r'Ran 194 tests in .+s',s)) for s in lines)==1
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
    out={'run':int(run_id) if run_id is not None else None,'source_head':head,'product_log_sha256':hashlib.sha256(raw).hexdigest(),'native_build':b,'native_source_bindings':4,'actual_full_Pi_tests':194,'automatic_readiness_controls':ready[0],'client':{k:v for k,v in c.items() if k!='reports'},'all14_native_observations_match_actual_provisioned_library':True,'fixture_coverage_actual_and_floor':coverage[0],'additional_audit_controls':4,'three_complete_fresh_audits':True,'audit_commands':commands,'limits':'Original completed CI source/build/trace binding only; the ELF itself is not downloaded, no cdylib reproducibility or target/device/custody/physical qualification claim. The original17-step/check/bootstrap/capture verifier remains separately mandatory.'}
    out.update(first_proof)
    out['proof_role']='local_makeci_source_addon_no_GitHub_claim' if run_id is None else 'completed_capture_source_addon_requires_generic_receipt_job_check_verifier'
    if run_id is None:
        out['limits']='Local stable makeci source/build/trace proof only; no GitHub run, receipt, job, check, protected integration or device claim. Hosted acceptance separately requires the unchanged mandatory completed-capture verifier with RUN HEAD CHECKRUNS_JSON, plus this source addon. No ELF reproducibility or physical qualification.'
    return out

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
