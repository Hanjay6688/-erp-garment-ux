"""Lossless bd2 failed originals; the unarchived full cost census stays missing."""
from pathlib import Path
from hashlib import sha256
import gzip
import json

HERE = Path(__file__).resolve().parent
BASE = 'bd2cd02c0b724f87f6f1d8628f8227dd30c513a4'
RUN = 40928155690
ARTIFACT = 12924775397
ZIP_SHA = '014400fd25c7134055a73a761a5c7079f29d0eed686964d8fc077fc221b32196'
NAMES = ('CP7_SKU_COMBINED_FOLLOWUP23.json', 'CP7_SKU_PAIR_CONVERSION_NATIVE7.json',
         'CP7_SKU_GROUP_COST_NATIVE3.json', 'T3_PACKAGE_INSTALL.json',
         'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json')


def originals(folder=HERE / 'retainedbd2'):
    receipt = json.loads((folder / 'RECEIPT.json').read_bytes())
    assert receipt['head'] == BASE and receipt['run_id'] == RUN and receipt['artifact_id'] == ARTIFACT
    assert receipt['zip_bytes'] == 4485191 and receipt['zip_sha256'] == ZIP_SHA
    assert receipt['zip_members'] == 131 and receipt['archived_SKU_COST_full_census_members'] == []
    assert receipt['full_cost_before_after_census_retained'] is False and receipt['usable_prerequisite'] is False
    assert set(receipt['files']) == set(NAMES)
    result = {}
    for name, pin in receipt['files'].items():
        encoded = (folder / (name + '.gz')).read_bytes()
        value = gzip.decompress(encoded)
        assert len(encoded) == pin['gzip_bytes'] and sha256(encoded).hexdigest() == pin['gzip_sha256'], name
        assert len(value) == pin['raw_bytes'] and sha256(value).hexdigest() == pin['raw_sha256'], name
        result[name] = value
    return result


def observe(values):
    outer, core, cost, package, drill, files = (values[name] for name in NAMES)
    child = outer['committed']['SKU_BASE_NATIVE7_COST_NATIVE3_RACES3_NATIVE_WAITS6_AUTH_BROWSER4']
    assert outer['status'] == child['status'] == 'INCOMPLETE' and outer['qualification_commit'] == BASE
    assert outer['native'] == {} and outer['required_case_ids_pass'] is False and outer['observed_case_count'] == 1
    assert child['fresh_base_native7']['native'] == core and core['counts'] == {'PASS': 7}
    assert child['fresh_base_native7']['used_guard_refused_before_DDL'] is True
    assert child['fresh_cost_native3']['native'] == cost and cost['counts'] == {'INCOMPLETE': 2, 'PASS': 1}
    assert core['complete_boundary_restored'] is True and cost['complete_boundary_restored'] is True
    assert all(c['full_boundary_restored'] is True for group in (core, cost) for c in group['cases'].values())
    safety = cost['cases']['SKU29_COST_GROUP_RETURN_OVER_FIRST_PART_SAFETY_REFUSAL_ONLY']
    atomic = cost['cases']['SKU29_COST_FIRST_PART_ACTIVE_USAGE_ATOMIC_GROUP_INVERSE']
    assert safety['status'] == 'INCOMPLETE' and 'BC_DATE_INVALID' in safety['error'] and 'YYYY-MM-DDTHH:MM:SS+07:00' in safety['error']
    assert cost['cases']['SKU29_COST_BOTH_PARTS_USAGE_LATE_INVOICE_SOLD_AND_DESCENDANT']['status'] == 'PASS'
    assert atomic['status'] == 'INCOMPLETE' and 'SKU_COST_CURRENT_CENSUS_CHANGED' in atomic['error']
    assert "'catalog_groups': []" in atomic['error']
    assert "'data_or_sequences': ['sequence:erp.audit_logs_id_seq', 'sequence:erp.fg_stock_book_order_seq']" in atomic['error']
    assert '_FULL_CURRENT_CENSUS.json' in atomic['error']
    assert outer.get('used_guard_refused_before_DDL') is None
    assert 'fresh_callbacks9' not in child and 'fresh_real_Auth_browser4' not in child
    for key in ('baseline_full22_all_rows_all_sequences_equal', 'restore_raw_public_equal', 'cp6_restored', 'baseline_advisors_equal', 'advisor_gate'):
        assert outer[key] is True, key
    assert outer['baseline_role_cleanup']['baseline_roles_exact'] is True and all(outer['restore_components'].values())
    assert outer['advisor_disposition']['gate'] is True and outer['advisor_disposition']['unexplained'] == []
    assert outer['baseline_restore']['only_pg_cron_errors'] is True and outer['baseline_restore']['unexplained'] == []
    assert package['status'] == 'ALL_STAGES_INSTALLED' and package['writer_runtime']['status'] == 'INCOMPLETE'
    assert package['gate'] == dict(installed=True, primary_unchanged=True, backup_restore_drill=True, security_advisors=True, writer_runtime=False)
    assert package['auth_users_before'] == package['auth_users_after'] == 0
    assert drill['status'] == 'RESTORED_IDENTICAL' and all(drill['checks'].values())
    assert files['status'] == 'ALL_FILES_INSTALLED'
    return dict(status='EXACT_BD2_FAILURE_AND_FULL_RESTORE_RETAINED', run_id=RUN, artifact_id=ARTIFACT,
        fresh_base_Native_counts={'PASS': 7}, cost_Native_counts={'PASS': 1, 'INCOMPLETE': 2},
        downstream_not_reached=13, historical_only=True, usable_prerequisite=False,
        first_sequence_mismatch_preserved_in_strict3_error=True, full_cost_before_after_census_retained=False,
        all22_rows_sequences_roles_CP6_advisors_restored=True, Auth_before=0, Auth_after=0,
        package_writer_gate=False, actual_successor_cases=0, production_go=False, independent_acceptance=False)


def verified():
    return observe({name: json.loads(value) for name, value in originals().items()})
