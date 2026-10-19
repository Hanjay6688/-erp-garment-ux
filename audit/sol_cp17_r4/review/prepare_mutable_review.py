"""Read existing text artifacts; never execute a product case."""
from pathlib import Path
from hashlib import sha256
import json

A = Path(__file__).resolve().parents[1]

def artifact(aid, filename):
    p = A / 'ci_receipts/sol_artifacts' / str(aid)
    receipt = json.loads((p / 'DOWNLOAD_RECEIPT.json').read_text())
    for row in receipt['selected_files']:
        assert sha256((p / 'files' / row['path']).read_bytes()).hexdigest() == row['sha256']
    before = json.loads((p / 'files/SOL_R4_IDENTITY_BEFORE.json').read_text())
    after = json.loads((p / 'files/SOL_R4_IDENTITY_AFTER.json').read_text())
    for key, expected in [('candidate_sha', '663f6faefcbb9c70f0f99bbc7e78164e03521329'),
                          ('candidate_tree', '023f3554432f80f994439f5d0b8cc164846a2041')]:
        assert before[key] == after[key] == expected
    assert before['product_roots'] == after['product_roots']
    assert before['product_worktree_clean'] is after['product_worktree_clean'] is True
    data = json.loads((p / 'files' / filename).read_text())
    assert data['cp6_restored'] is True and all(v is True for v in data['restore_components'].values())
    assert data['native']['complete_boundary_restored'] is True and data['native']['missing'] == []
    return data, receipt

def counts(rows):
    out = {r['function'] + ':' + r['check_name']: r['issue_count'] for r in rows}
    assert len(rows) == len(out) == 167
    return out

def reviewed_case(cid, row, run, aid):
    assert row['status'] == 'PASS' and row['full_boundary_restored'] is True
    before, after = counts(row['before']), counts(row['after_rollback'])
    assert all(v == 0 for v in before.values()) and after == before
    phases = []
    for p in row['phases']:
        during = counts(p['rows'])
        assert set(during) == set(before)
        delta = {k: during[k] - before[k] for k in before if during[k] != before[k]}
        assert delta == p['expected_deltas'] == p['observed_deltas']
        assert all(v == 1 for v in delta.values())
        phases.append(dict(name=p['name'], exact_deltas=delta, other_counts_unchanged=True))
    for key in ['all_nine_functions_each_phase', 'all167rows_each_phase',
                'immutable_facts_and_guard_definitions_unchanged', 'no_trigger_privilege_or_function_change']:
        assert row[key] is True
    assert row['session_leaks'] == {'advisory_locks': 0, 'advisory_lock_keys': [], 'other_sessions': []}
    return dict(case_id=cid, run_id=run, artifact_id=aid, raw_status='PASS', case_kind='DETECTOR_CONTROL',
                oracle_origin=row['oracle_origin'], fixture_origin=row['fixture_origin'], phases=phases,
                counts_each_phase=167, all_other_counts_unchanged=True, protected_facts_and_guards_unchanged=True,
                full_boundary_restored=True, canonical_for_candidate=True, group='/native')

def main():
    data, receipt = artifact(12162647072, 'SOL_R4_MUTABLE_DETECTOR_CONTROLS.json')
    assert data['counts'] == {'PASS': 3, 'INCOMPLETE': 1}
    cases = []
    for cid, row in data['native']['cases'].items():
        if row['status'] == 'PASS':
            cases.append(reviewed_case(cid, row, 39197469845, 12162647072))
    failed = data['native']['cases']['SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY']
    assert failed['status'] == 'INCOMPLETE' and 'character varying(60)' in failed['error']
    assert "clone_material(cur,'SOLR4-DETECTOR-MASTER')" in failed['traceback']
    assert len('Z-AUD-SOLR4-DETECTOR-MASTER-' + '0' * 36) == 64
    assert len('Z-AUD-SR4DC-' + '0' * 36) == 48
    result = dict(state='READ_ORIGINAL_AND_RECALCULATED_THREE_CONTROLS', first_run_id=39197469845,
                  first_artifact_id=12162647072, first_counts=data['counts'],
                  first_archive_sha256=receipt['archive_sha256'], selected_members_rehashed=len(receipt['selected_files']),
                  canonical_cases=cases, first_failure_preserved=True,
                  first_failure=dict(case_id='SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY', raw_status='INCOMPLETE',
                                     classification='AUDITOR_FIXTURE_SKU_PREFIX_TOO_LONG', generated_length=64,
                                     column_maximum=60, fixture_created=False, detector_counter_phase_executed=False,
                                     product_bug_inferred=False, qualified_prefix_length=48),
                  qualified_accessory_state='PENDING_ORIGINAL_READ',
                  limits=['Administrative mutable queue/cache/master counterfixtures are not ordinary user CRUD.',
                          'No protected fact, trigger, grant or guard was altered during a counter phase.',
                          'Twelve identities require the separate accessory qualified Original; normal zeros do not close all167.'])
    qualified, qr = artifact(12162817995, 'SOL_R4_ACCESSORY_DETECTOR_Q2.json')
    assert qualified['counts'] == {'PASS': 1}
    cid = 'SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY'
    assert set(qualified['native']['cases']) == {cid}
    accessory = qualified['native']['cases'][cid]
    original = accessory['original_master']
    assert original['material_type'] == 'FABRIC' and original['accessory_category_id'] is None and original['is_active'] is True
    assert len(original['material_sku']) == 48 and original['cached_stock_qty'] == original['moving_average_cost'] == 0
    assert accessory['changed_master'] == [['ACCESSORY', None, True]]
    assert accessory['ordinary_master_CRUD_claim'] is False and accessory['full_master_row_restored'] is True
    expected = {'run_v24_accessory_integrity_checks:ACCESSORY_WITHOUT_CATEGORY': 1,
                'run_v266_gudang_accessory_fg_checks:v266_accessory_material_category_mismatch': 1}
    assert len(accessory['phases']) == 1 and accessory['phases'][0]['expected_deltas'] == expected
    cases.append(reviewed_case(cid, accessory, 39198198716, 12162817995))
    result.update(state='READ_FIRST_AND_QUALIFIED_ORIGINALS_FOUR_UNIQUE_CONTROLS',
                  qualified_accessory_state='PASS_SEPARATE_GENUINE_FIXTURE_PREFIX_QUALIFICATION',
                  qualified_run_id=39198198716, qualified_job_id=117885441312, qualified_artifact_id=12162817995,
                  qualified_archive_sha256=qr['archive_sha256'], qualified_counts={'PASS': 1},
                  selected_members_rehashed=len(receipt['selected_files']) + len(qr['selected_files']),
                  canonical_cases=cases, unique_case_ids=4,
                  limits=['Administrative mutable queue/cache/master counterfixtures are not ordinary user CRUD.',
                          'No protected fact, trigger, grant or guard was altered during a counter phase.',
                          'Four unique control cases here, with eight exact detector identities; initial accessory failure remains INCOMPLETE.',
                          'Global INV-D01 remains incomplete: clean zero rows are not negative controls for the remaining identities.'])
    (A / 'MUTABLE_DETECTOR_RESULT_REVIEW.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Mutable first 3PASS/1INCOMPLETE + separate accessory1PASS; four unique controls reviewed.')

if __name__ == '__main__':
    main()
