"""Read the first nine finite controls without erasing the blocked predecessor."""
from pathlib import Path
import json
from prepare_mutable_review import artifact, reviewed_case, counts

A = Path(__file__).resolve().parents[1]

def main():
    data, receipt = artifact(12163127220, 'SOL_R4_DERIVED_DETECTOR_CONTROLS.json')
    assert data['counts'] == {'PASS': 8, 'INCOMPLETE': 1}
    manifest = json.loads((A / 'DERIVED_DETECTOR_PREEXECUTION_MANIFEST.json').read_text())
    assert set(data['native']['cases']) == {r['id'] for r in manifest['cases']}
    canonical = []
    for plan in manifest['cases']:
        cid = plan['id']; row = data['native']['cases'][cid]
        if row['status'] != 'PASS': continue
        assert {p['name']:p['observed_deltas'] for p in row['phases']} == plan['expected_phases']
        result = reviewed_case(cid, row, 39199375501, 12163127220)
        assert row['full_subject_row_restored'] is True
        if not plan['negative_detector_sensitivity_claim']:
            assert len(row['refusals']) == 2
            for refusal in row['refusals']:
                assert refusal['observed']['sqlstate'] == refusal['expected_sqlstate'] == 'P0001'
                assert refusal['expected_fragment'] in refusal['observed']['message']
            assert row['detector_negative_control_claim'] is False
            assert row['disposition'] == 'GUARD_PREVENTION_ONLY_NOT_0_1_0'
            result.update(case_kind='GUARD_PREVENTION_ONLY', refusals=row['refusals'], negative_sensitivity_claim=False)
        canonical.append(result)
    assert len(canonical) == 8 and sum(r['case_kind'] == 'DETECTOR_CONTROL' for r in canonical) == 6
    cid = 'SOL_R4_D01_OPENING_DERIVED_STATUS'
    stopped = data['native']['cases'][cid]
    assert stopped['status'] == 'INCOMPLETE' and stopped['error'] == 'SOL_MUTABLE_BASELINE_NOT_ZERO'
    path = A / 'ci_receipts/sol_artifacts/12163127220/files' / (cid + '_OBSERVATIONS.json')
    opening = json.loads(path.read_text())
    assert opening['actual_opening'] == ['65.00', '0.00', 'OPEN']
    before = counts(opening['before'])
    assert {k:v for k,v in before.items() if v} == {'run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor': 2}
    assert 'phases' not in opening and 'changed_row' not in opening
    result = dict(state='READ_EIGHT_PASS_AND_PRESERVED_HEALTHY_NOTA_FALSE_ALARM_DISPUTE',
                  first_run_id=39199375501, first_job_id=117888970333, first_artifact_id=12163127220,
                  first_archive_sha256=receipt['archive_sha256'], selected_members_rehashed=len(receipt['selected_files']),
                  raw_counts=data['counts'], canonical_cases=canonical,
                  first_opening_status='INCOMPLETE_BEFORE_COUNTER_NOT_RELABELLED',
                  first_opening_values=['65.00','0.00','OPEN'], first_opening_changed=False,
                  preceding_alarm=dict(identity='run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor', count=2,
                                       observation=str(path.relative_to(A)), classification='POTENTIAL_PRODUCT_FALSE_ALARM_ON_VALID_FG_REPAIR_NOTA_PENDING_ACTUAL_SOURCE_RESOLUTION',
                                       not_classified_as_adversarial_fixture=True,
                                       source_reason='cp7_settlement_read_cases.fixture invokes valid source.repair and publicNotaSAVE/POST. AX and CP7 supportFG_REPAIR; current payroll detector resolves onlyPRODUCTION/REWORK.'),
                  guard_prevention={
                    'run_v24_accessory_integrity_checks:ACCESSORY_CATEGORY_UOM_MISMATCH': dict(case_id='SOL_R4_D01_ACCESSORY_UOM_GUARD_PREVENTION', run_id=39199375501, artifact_id=12163127220, disposition='TWO_NATIVE_GUARD_REFUSALS_NO_ADMIN_BYPASS_NOT_SENSITIVITY'),
                    'run_v267_financial_truth_checks:V267_MISSING_GRNI_MAPPING': dict(case_id='SOL_R4_D01_CORE_GRNI_GUARD_PREVENTION', run_id=39199375501, artifact_id=12163127220, disposition='DELETE_AND_RENAME_NATIVE_GUARD_REFUSED_NOT_SENSITIVITY')},
                  pending_qualification='PAYROLL_DETECTOR_DISPUTE_PREEXECUTION_MANIFEST.json; legitimate Nota source resolution plus isolated acceptedBB opening control. EightPASS cases not repeated.',
                  protected_facts_guards_and_primary_restored=True, product_fix_applied=False)
    dispute_path = A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json'
    if dispute_path.exists():
        dispute = json.loads(dispute_path.read_text())
        assert dispute['false_alarm_reproduced'] is True
        result['preceding_alarm']['initial_classification'] = result['preceding_alarm']['classification']
        result['preceding_alarm']['classification'] = 'PROVED_S1_VALID_FG_REPAIR_FALSE_CRITICAL'
        result['preceding_alarm']['superseded_by'] = 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json'
        result.pop('pending_qualification')
        result['final_qualification'] = dict(run_id=dispute['run_id'], artifact_id=dispute['artifact_id'],
            status='READ_COUNTEREXAMPLE1_PASS1', false_alarm='SOL-R4-001_S1', isolated_opening='QUALIFIED_SAME65_0_OPEN',
            earlier8PASS_repeated=False, first_opening_INCOMPLETE_preserved=True)
    (A / 'DERIVED_DETECTOR_RESULT_REVIEW.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Derived first6 sensitivityPASS+2 preventionPASS preserved; final dispute linked if available.')

if __name__ == '__main__': main()
