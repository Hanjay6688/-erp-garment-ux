"""Read actual Original reports only; never synthesize successful observations."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = 'CP7_S03_ATTENDANCE_CHOICE_NATIVE11'


def checked(report, package, ids):
    if len(ids) != 11 or len(set(ids)) != 11:
        raise ValueError('S03_NATIVE11_EXACT_ELEVEN_IDS_REQUIRED')
    for name in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal',
                 'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL',
                 'required_case_ids_pass'):
        if report.get(name) is not True:
            raise ValueError('S03_NATIVE11_OUTER_GATE_REQUIRED:' + name)
    if report.get('status') != 'PASS' or report.get('label') != LABEL:
        raise ValueError('S03_NATIVE11_OUTER_ACTUAL_PASS_REQUIRED')
    expected_counts = dict(actual_Native_cases=11, actual_two_session_races=0,
                           actual_Auth_HTTP_cases=0, actual_browser_cases=0)
    if any(type(report.get(key)) is not int or report[key] != number for key, number in expected_counts.items()):
        raise ValueError('S03_NATIVE11_EXACT_NATIVE_ONLY_COUNTS_REQUIRED')
    group = report.get('committed', {}).get('S03_ATTENDANCE_NATIVE11_AND_USED_INVERSE', {})
    native = group.get('native', {})
    if (group.get('status') != 'PASS' or group.get('used_guard_refused_before_DDL') is not True
            or native.get('status') != 'PASS' or native.get('counts') != {'PASS': 11}
            or native.get('planned_case_ids') != ids or set(native.get('cases', {})) != set(ids)
            or any(v.get('status') != 'PASS' for v in native.get('cases', {}).values())
            or native.get('complete_boundary_restored') is not True):
        raise ValueError('S03_NATIVE11_ALL_ORIGINAL_IDS_AND_USED_WITNESS_REQUIRED')
    gates = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(gates)
            or any(package['gate'][key] is not True for key in gates)):
        raise ValueError('S03_NATIVE11_EXACT_FIVE_PACKAGE_GATES_REQUIRED')
    return dict(status='PASS', actual_Native_cases=11, actual_two_session_races=0,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, all_five_package_gates=True,
        full_outer_backup_restore_all22_rows_sequences_roles_CP6_advisors_required=True,
        full_S03_acceptance=False, production_go=False, independent_acceptance=False)


def main():
    out = ROOT / 'cp6-proof/t3'
    try:
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        result = checked(json.loads((out / (LABEL + '.json')).read_bytes()),
            json.loads((out / 'T3_PACKAGE_INSTALL.json').read_bytes()), cfg['Native_case_ids'])
    except Exception as error:
        result = dict(status='INCOMPLETE', error=str(error), actual_Native_cases=0,
                      production_go=False, independent_acceptance=False)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'S03_NATIVE11_FINAL_GATE.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
