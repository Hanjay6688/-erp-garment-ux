"""Retained b0 original bytes: failure evidence, never prerequisite PASS credit."""
from hashlib import sha256
from pathlib import Path
import gzip
import json

HERE = Path(__file__).resolve().parent
PINS = {
    'CP7_S05_ACCESSORY_STANDARD_NATIVE10.json': (805672, '56408d4a2708c9fc66689ae660df6594c961774d101dc70f95801aaeb21bc728'),
    'T3_PACKAGE_INSTALL.json': (360447, '12b497782d737e7be38882bbe2b1322f4aa893d83a99804c782be89358c4d624'),
    'T3_PACKAGE_FILES_INSTALL.json': (1806, '14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
    'T3_BACKUP_RESTORE_DRILL.json': (1470, '3e0aeb67ceffef567251893cd2db37dea95fc53019a4db8c7c621c6bd82baafe'),
}


def checked(here=HERE):
    here = Path(here)
    values, pins = {}, {}
    for name, (size, digest) in PINS.items():
        raw = gzip.decompress((here/'retained-b0'/(name+'.gz')).read_bytes())
        if len(raw) != size or sha256(raw).hexdigest() != digest:
            raise ValueError('S05_B0_ORIGINAL_BYTES_CHANGED: '+name)
        values[name] = json.loads(raw)
        pins[name] = dict(bytes=size, sha256=digest)
    original = values['CP7_S05_ACCESSORY_STANDARD_NATIVE10.json']
    child = original['committed']['S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE']
    if (original['qualification_commit'], original['status'], original['observed_case_count'],
            child['actual_Native_cases'], child['status'], original['native']) != (
            'b0e5ac05e2024d5673126b6fe7759591293b9b96', 'INCOMPLETE', 1, 0, 'INCOMPLETE', {}):
        raise ValueError('S05_B0_ZERO_NATIVE_FAILURE_REQUIRED')
    signature = 'public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)'
    if original['error'] != 'S05_UNEXPECTED_INSTALLER_FUNCTION_GRANT: '+signature:
        raise ValueError('S05_B0_EXACT_FUNCTION_GRANT_FAILURE_REQUIRED')
    if (original['baseline_full22_all_rows_all_sequences_equal'] is not True
            or original['restore_raw_public_equal'] is not True
            or original['cp6_restored'] is not True or original['baseline_advisors_equal'] is not True
            or not original['restore_components'] or not all(v is True for v in original['restore_components'].values())):
        raise ValueError('S05_B0_COMPLETE_OUTER_RESTORATION_REQUIRED')
    expected = dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
                    security_advisors=True, writer_runtime=False)
    if values['T3_PACKAGE_INSTALL.json']['gate'] != expected:
        raise ValueError('S05_B0_FAILED_WRITER_GATE_MUST_REMAIN_FALSE')
    if values['T3_BACKUP_RESTORE_DRILL.json']['status'] != 'RESTORED_IDENTICAL':
        raise ValueError('S05_B0_BACKUP_RESTORE_DRILL_REQUIRED')
    return dict(status='RETAINED_B0_FAILURE_NOT_ACCEPTANCE', run_id=40931612668, job_id=123651202210,
        observed_outer_wrapper=1, actual_S05_Native_cases=0, Native_PASS_credit=0,
        actual_CI_extra_tuple_identity_proven=False, package_gates=expected,
        full_outer_restoration=True, original_bytes=pins,
        independent_acceptance=False, production_go=False)
