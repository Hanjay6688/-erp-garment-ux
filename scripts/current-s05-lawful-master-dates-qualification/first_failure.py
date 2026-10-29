"""Retain the exact five first-911 Originals; never grant runtime credit."""
from hashlib import sha256
from pathlib import Path
import gzip
import json

HERE = Path(__file__).resolve().parent


def checked(here=HERE):
    retained = Path(here)/'retained-911'
    receipt = json.loads((retained/'RECEIPT.json').read_bytes())
    raw = {}
    for name, pin in receipt['raw'].items():
        data = gzip.decompress((retained/(name+'.gz')).read_bytes())
        if len(data) != pin['bytes'] or sha256(data).hexdigest() != pin['sha256']:
            raise ValueError('S05_911_FIRST_ORIGINAL_CHANGED:'+name)
        raw[name] = json.loads(data)
    main = raw['CP7_S05_ACCESSORY_STANDARD_NATIVE10.json']
    strict = raw['CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json']
    package = raw['T3_PACKAGE_INSTALL.json']
    drill = raw['T3_BACKUP_RESTORE_DRILL.json']
    child = main['committed']['S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE']
    if main['qualification_commit'] != receipt['head'] or main['status'] != 'INCOMPLETE':
        raise ValueError('S05_911_NOT_THE_FIRST_RUNTIME_FAILURE')
    if strict['counts'] != {'INCOMPLETE': 10} or len(strict['cases']) != 10:
        raise ValueError('S05_911_EXACT_TEN_INCOMPLETE_REQUIRED')
    if any(x['status'] != 'INCOMPLETE' or 'BF_HISTORY: master baru hanya mulai sekarang atau mendatang' not in x['error'] for x in strict['cases'].values()):
        raise ValueError('S05_911_EXACT_DATE_GUARD_FAILURE_REQUIRED')
    if (package['gate'] != dict(installed=True, primary_unchanged=True, backup_restore_drill=True, security_advisors=True, writer_runtime=False)
            or package['auth_users_before'] != 0 or package['auth_users_after'] != 0):
        raise ValueError('S05_911_ORIGINAL_PACKAGE_FAILURE_GATES_CHANGED')
    if drill['status'] != 'RESTORED_IDENTICAL' or any(x is not True for x in drill['checks'].values()):
        raise ValueError('S05_911_BACKUP_RESTORE_NOT_PROVEN')
    for key in ('baseline_full22_all_rows_all_sequences_equal', 'cp6_restored', 'baseline_advisors_equal', 'advisor_gate'):
        if main[key] is not True:
            raise ValueError('S05_911_OUTER_RESTORE_NOT_PROVEN:'+key)
    if child['reader_preuse_reinstall']['status'] != 'PASS':
        raise ValueError('S05_911_READER_PREUSE_REINSTALL_NOT_PROVEN')
    return dict(status='EXACT_911_TEN_INCOMPLETE_RETAINED_NOT_ACCEPTED', raw=receipt['raw'],
                observed_case_counts={'INCOMPLETE': 10}, Native_PASS=0,
                complete_outer_restore=True, reader_preuse_reinstall='PASS',
                outer_used_guard_field_present='used_guard_refused_before_DDL' in main,
                separate_committed_witness_field_present='separate_committed_business_witness' in child,
                package_gates=package['gate'], success_prerequisite=False,
                production_go=False, independent_acceptance=False)
