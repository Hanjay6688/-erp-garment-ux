"""Fail closed on the exact Native13/cron Original, before database access."""
from hashlib import sha256
import json

GATES = ('installed', 'primary_unchanged', 'backup_restore_drill',
         'security_advisors', 'writer_runtime')
REQUIRED = ('required_case_ids_pass', 'cp6_restored', 'advisor_gate',
            'baseline_full22_all_rows_all_sequences_equal',
            'baseline_advisors_equal', 'used_guard_refused_before_DDL',
            'focused_composition_qualified', 'actual_cron_claim')


def accepted(binding, raw, package_raw, expected_source, expected_installation):
    if binding.get('status') != 'PASS':
        raise ValueError('FOLLOWUP_PARENT_NOT_ACCEPTED')
    if len(raw) != binding['bytes'] or sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('FOLLOWUP_PARENT_ORIGINAL_CHANGED')
    if (len(package_raw) != binding['package_bytes']
            or sha256(package_raw).hexdigest() != binding['package_sha256']):
        raise ValueError('FOLLOWUP_PARENT_PACKAGE_ORIGINAL_CHANGED')
    actual = json.loads(raw)
    package = json.loads(package_raw)
    if actual['status'] != 'PASS' or actual['qualification_commit'] != binding['head']:
        raise ValueError('FOLLOWUP_PARENT_STATUS_OR_HEAD_CHANGED')
    if package['gate'] != {key: True for key in GATES}:
        raise ValueError('FOLLOWUP_PARENT_PACKAGE_NOT_PASS')
    for key in REQUIRED:
        if actual.get(key) is not True:
            raise ValueError('FOLLOWUP_PARENT_REQUIRED_PROOF:' + key)
    if (actual['production_go'] is not False or actual['independent_acceptance'] is not False
            or actual['default_adopted'] is not False
            or actual['full_combined_final_qualification'] is not False):
        raise ValueError('FOLLOWUP_PARENT_SCOPE_CHANGED')
    declaration = actual['source_declaration']
    if (declaration['qualification'] != expected_source
            or declaration['current_installation'] != expected_installation):
        raise ValueError('FOLLOWUP_PARENT_SOURCE_CHANGED')
    ids = expected_source['case_ids']
    native, committed = actual['native'], actual['committed']
    cases = {**native['cases'], **committed}
    if (len(ids) != len(set(ids)) or len(ids) != 14 or len(native['cases']) != 13
            or len(committed) != 1 or set(native['cases']) & set(committed)
            or set(cases) != set(ids) or any(c.get('status') != 'PASS' for c in cases.values())):
        raise ValueError('FOLLOWUP_PARENT_CASES_CHANGED')
    if actual['observed_case_count'] != 14 or actual['expected_case_count'] != 14:
        raise ValueError('FOLLOWUP_PARENT_CASE_COUNT_CHANGED')
    if (native['status'] != 'PASS' or native['counts'] != {'PASS': 13}
            or native['complete_boundary_restored'] is not True
            or actual['full_parent_inverse_repeated'] is not False
            or actual['focused_preuse_removal']['full_parent_inverse_repeated'] is not False
            or actual['baseline_role_cleanup']['baseline_roles_exact'] is not True):
        raise ValueError('FOLLOWUP_PARENT_RESTORATION_CHANGED')
    return dict(head=binding['head'], original_sha256=binding['sha256'],
                package_sha256=binding['package_sha256'], exact_native13_cron1=True,
                full_parent_inverse_repeated=False, all_package_gates=True,
                production_go=False, independent_acceptance=False)
