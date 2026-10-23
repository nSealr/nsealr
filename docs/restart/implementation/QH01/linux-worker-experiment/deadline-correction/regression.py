"""Single real scheduling-delay regression; no internal harness hook or fakeclock."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    prefix = Path(__file__).resolve().parent.parent
    source = prefix / 'experiment.py'
    raw_source = source.read_bytes()
    expectation = json.loads((prefix / 'deadline-correction/expectation.json').read_text())
    module_spec = importlib.util.spec_from_file_location('qh01_actual_experiment', source)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    parsed = ast.parse(raw_source)
    function = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'run_case')
    anchors = []
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == 'record' and isinstance(target.slice, ast.Constant) and target.slice.value == 'eligible':
                    anchors.append(node.lineno)
    if len(anchors) != 1:
        raise RuntimeError('ambiguous eligibility assignment; no source alteration/fallback')
    line = anchors[0]
    context = module.context()
    context['regression_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    context['harness_sha256'] = hashlib.sha256(raw_source).hexdigest()
    module.json_write(args.out / 'environment.json', context)
    owner = module.Owner()
    image = (module.ROOT / module.SOURCES['public_RGB']['path']).read_bytes()
    expected = (module.ROOT / module.SOURCES['predetermined_public_output']['path']).read_bytes()
    case = next(c for c in module.EXPECTATIONS['cases'] if c['id'] == 'positive')
    witness = {'source_path': str(source), 'source_sha256': context['harness_sha256'],
               'assignment_line': line, 'assignment_source': raw_source.decode().splitlines()[line - 1],
               'pause_count': 0, 'budget_seconds': module.P['wall_eligibility_deadline'],
               'requested_real_pause_seconds': expectation['controlled_pause_seconds'],
               'clock_replaced': False, 'record_mutated_by_probe': False, 'actual_QR_decode': False}
    def trace(frame, event, arg):
        if frame.f_code is module.run_case.__code__ and event == 'line' and frame.f_lineno == line:
            local = frame.f_locals
            record = local['record']
            assertions = {
                'actual_status0': record['own_status_acquired'] and record['owner_wait']['exitcode'] == 0,
                'all_parent_IO_FDs_closed': record['all_parent_IO_closed'] and record['final_open_fds_equal_initial'],
                'actual_input_complete': record['image_bytes_sent'] == 172800 and record['control_bytes_sent'] == 1,
                'actual_expected_output198': local['out'] == expected and len(expected) == 198,
                'known_owner_released': not owner.busy and not owner.quarantined,
                'no_earlier_error': local['reason'] is None and 'harness_error' not in record,
                'unchanged8s_budget': module.P['wall_eligibility_deadline'] == 8.0,
                'single_pause': witness['pause_count'] == 0,
            }
            witness['pre_pause_assertions'] = assertions
            if not all(assertions.values()):
                raise RuntimeError('pause boundary masked: ' + str(assertions))
            witness['pause_count'] += 1
            witness['case_start_monotonic'] = local['start']
            witness['pause_begin_monotonic'] = time.monotonic()
            time.sleep(expectation['controlled_pause_seconds'])
            witness['pause_end_monotonic'] = time.monotonic()
            witness['actual_pause_seconds'] = witness['pause_end_monotonic'] - witness['pause_begin_monotonic']
            witness['actual_elapsed_before_admission_seconds'] = witness['pause_end_monotonic'] - local['start']
        return trace
    sys.settrace(trace)
    try:
        result = module.run_case(case, owner, image, expected, args.out)
    finally:
        sys.settrace(None)
    witness['observed_eligible'] = result['eligible']
    witness['observed_boundary'] = result['boundary']
    witness['original_positive_validator_disposition'] = result['disposition']
    witness['checks'] = {
        'exactly_one_real_pause_after_verified_cleanup': witness['pause_count'] == 1 and all(witness.get('pre_pause_assertions', {}).values()),
        'actual_pause_crosses_unchanged_deadline': witness.get('actual_pause_seconds', 0) >= 8.25 and witness.get('actual_elapsed_before_admission_seconds', 0) >= 8.0,
        'actual_child_collected_and_IO_settled': result['owned_child_collected'] and result['own_status_acquired'] and result['all_parent_IO_closed'] and result['final_open_fds_equal_initial'],
        'known_owner_remains_reusable': not owner.busy and not owner.quarantined,
        'expired_result_rejected': result['eligible'] is False,
    }
    witness['passed'] = all(witness['checks'].values())
    module.json_write(args.out / 'regression.json', witness)
    print(json.dumps(witness, indent=2), flush=True)
    return 0 if witness['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
