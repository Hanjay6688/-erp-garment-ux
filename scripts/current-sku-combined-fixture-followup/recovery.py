"""Verify the six actual failed c163 Originals without turning them into PASS."""
from hashlib import sha256
from pathlib import Path
import gzip
import json

HERE = Path(__file__).resolve().parent
BASE = 'c163c1e9ff8f00b8dd8859c32aee0c2069766ad6'
PINS = {
    'CP7_SKU_COMBINED_FOLLOWUP23.json': (4748461, 'e646d0543599a81a5a76527996b2fde0af2adae80315e33eb7849073fd392daa'),
    'CP7_SKU_PAIR_CONVERSION_NATIVE7.json': (20821, '536d6f8a502f7cd7c4aab4e38e159a8683d65d7214b4ac60676b56e282f2cf3e'),
    'CP7_SKU_GROUP_COST_NATIVE3.json': (13193, 'b412f56167f0985d1268b09c8b90fb2a5c91aa9a21a80316267b47f0e46c05a1'),
    'T3_PACKAGE_INSTALL.json': (360443, 'e84b15966b575a47d08c302f3461a1603337553c1173ef64e4b82113664f924e'),
    'T3_BACKUP_RESTORE_DRILL.json': (1470, '9cadba1d85aefdf6f9bbaa287c774dac48c58f1f2b6ba0517bc1957dbad6342a'),
    'T3_PACKAGE_FILES_INSTALL.json': (1806, '14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
}


def originals(folder=HERE / 'retainedc163'):
    receipt = json.loads((folder / 'RECEIPT.json').read_bytes())
    assert receipt['head'] == BASE and receipt['usable_prerequisite'] is False
    assert receipt['run_id'] == 40915783203 and receipt['job_id'] == 123595497083
    assert receipt['artifact_id'] == 12918725781 and receipt['zip_bytes'] == 4422255
    assert receipt['zip_sha256'] == '9954499c21b8b4416e781a8785812296761b217000fa55b0d199f106eaf67aa2'
    result = {}
    for name, (size, digest) in PINS.items():
        encoded = (folder / (name + '.gz')).read_bytes()
        raw = gzip.decompress(encoded)
        pin = receipt['files'][name]
        assert len(encoded) == pin['gzip_bytes'] and sha256(encoded).hexdigest() == pin['gzip_sha256'], name
        assert len(raw) == size == pin['raw_bytes'] and sha256(raw).hexdigest() == digest == pin['raw_sha256'], name
        result[name] = raw
    return result


def observe(values):
    outer = values['CP7_SKU_COMBINED_FOLLOWUP23.json']
    first = values['CP7_SKU_PAIR_CONVERSION_NATIVE7.json']
    cost = values['CP7_SKU_GROUP_COST_NATIVE3.json']
    package = values['T3_PACKAGE_INSTALL.json']
    child = outer['committed']['SKU_BASE_NATIVE7_COST_NATIVE3_RACES3_NATIVE_WAITS6_AUTH_BROWSER4']
    assert outer['status'] == child['status'] == 'INCOMPLETE' and outer['qualification_commit'] == BASE
    assert outer['native'] == {} and outer['required_case_ids_pass'] is False and outer['observed_case_count'] == 1
    assert child['fresh_base_native7']['native'] == first and first['counts'] == {'PASS': 7}
    assert child['fresh_base_native7']['used_guard_refused_before_DDL'] is True
    assert child['fresh_cost_native3']['native'] == cost and cost['counts'] == {'INCOMPLETE': 3}
    assert first['complete_boundary_restored'] is True and cost['complete_boundary_restored'] is True
    for row in cost['cases'].values():
        assert row['status'] == 'INCOMPLETE' and row['full_boundary_restored'] is True
        assert row['public_schema_unchanged'] is True and row['session_leaks']['advisory_locks'] == 0
        assert row['session_leaks']['other_sessions'] == []
        assert 'brands_brand_name_key' in row['error'] and 'SKU29 different brand' in row['error']
        assert 'custom_group_products' in row['traceback'] and 'fixture.py\", line 71' in row['traceback']
    assert outer.get('used_guard_refused_before_DDL') is None
    assert 'fresh_callbacks9' not in child and 'fresh_real_Auth_browser4' not in child
    for key in ('baseline_full22_all_rows_all_sequences_equal', 'restore_raw_public_equal', 'cp6_restored', 'baseline_advisors_equal', 'advisor_gate'):
        assert outer[key] is True, key
    assert outer['baseline_role_cleanup']['baseline_roles_exact'] is True
    assert all(outer['restore_components'].values())
    # advisor_delta describes the installed stack, not the later restored
    # baseline. Preserve its reviewed private INFO findings; restoration is
    # proved separately by baseline_advisors_equal above.
    assert outer['advisor_disposition']['gate'] is True and outer['advisor_disposition']['unexplained'] == []
    restore = outer['baseline_restore']
    assert restore['exit'] == 1 and restore['error_count'] == 19 and restore['unexplained'] == []
    assert restore['only_pg_cron_errors'] is True
    assert package['status'] == 'ALL_STAGES_INSTALLED' and package['writer_runtime']['status'] == 'INCOMPLETE'
    assert package['gate'] == dict(installed=True, primary_unchanged=True, backup_restore_drill=True, security_advisors=True, writer_runtime=False)
    assert package['auth_users_before'] == package['auth_users_after'] == 0
    assert values['T3_BACKUP_RESTORE_DRILL.json']['status'] == 'RESTORED_IDENTICAL'
    assert all(values['T3_BACKUP_RESTORE_DRILL.json']['checks'].values())
    assert values['T3_PACKAGE_FILES_INSTALL.json']['status'] == 'ALL_FILES_INSTALLED'
    return dict(status='EXACT_C163_FIRST_INCOMPLETE_AND_FULL_RESTORE_RETAINED',
        fresh_base_Native_counts={'PASS': 7}, cost_Native_counts={'INCOMPLETE': 3},
        downstream_not_reached=13, inner_used_guard_observed=True, outer_used_guard_observed=False,
        all22_rows_sequences_roles_CP6_advisors_restored=True, Auth_before=0, Auth_after=0,
        package_writer_gate=False, usable_prerequisite=False, production_go=False, independent_acceptance=False)


def verified():
    return observe({name: json.loads(raw) for name, raw in originals().items()})


if __name__ == '__main__':
    print(json.dumps(verified(), indent=2))
