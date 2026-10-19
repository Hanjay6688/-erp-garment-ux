"""Review saved source-lineage evidence; no product or test execution."""
from pathlib import Path
from decimal import Decimal
from hashlib import sha256
import argparse
import json
from prepare_mutable_review import artifact, counts, reviewed_case

A = Path(__file__).resolve().parents[1]
TARGET = 'run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor'

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('artifact_id', type=int); parser.add_argument('job_id', type=int)
    args = parser.parse_args()
    run = 39200571137
    q, receipt = artifact(args.artifact_id, 'SOL_R4_PAYROLL_DETECTOR_DISPUTE.json')
    assert q['manifest_sha256'] == sha256((A / 'PAYROLL_DETECTOR_DISPUTE_PREEXECUTION_MANIFEST.json').read_bytes()).hexdigest()
    assert q['evidence_protocol_complete'] is True and q['opening_phase_manifest_binding'] is True
    expected_ids = {'SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM', 'SOL_R4_D01_OPENING_DERIVED_STATUS'}
    assert set(q['native']['cases']) == expected_ids
    p = A / 'ci_receipts/sol_artifacts' / str(args.artifact_id) / 'files'
    before_identity = json.loads((p / 'SOL_R4_IDENTITY_BEFORE.json').read_text())
    assert int(before_identity['run_id']) == run and before_identity['workflow_sha'] == '7f7e1b83a596f3f9c700a6c739d5dc998568a8c8'
    fp = q['native']['cases']['SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM']
    assert fp['full_boundary_restored'] is True and fp['full_subject_and_protected_restore'] is True
    assert fp['contract_expected_delta'] == {} and fp['expected_normal_alarm_count'] == 0
    phases = {}
    for name in ['before', 'after_native_repair_sources', 'after_draft', 'after_valid_post', 'after_rollback']:
        phases[name] = counts(fp[name])
    zero = phases['before']
    assert len(zero) == 167 and all(v == 0 for v in zero.values())
    assert all(set(v) == set(zero) for v in phases.values())
    assert phases['after_native_repair_sources'] == phases['after_draft'] == phases['after_rollback'] == zero
    delta = {k: phases['after_valid_post'][k] - zero[k] for k in zero if phases['after_valid_post'][k] != zero[k]}
    assert delta == fp['observed_delta'] and delta in ({}, {TARGET: 2})
    header = fp['payroll_header']
    assert header[1] == fp['contractor_id'] and header[2] == 'CALCULATED' and Decimal(header[3]) == Decimal(header[4]) == 6000
    resolved = fp['resolved_actual_FG_REPAIR_rows']
    assert len(resolved) == 2 and sorted(Decimal(r[3]) for r in resolved) == [1, 2]
    for r in resolved:
        assert r[1] == 'FG_REPAIR' and r[6] == r[7] == header[1] and r[8] == r[9]
        assert Decimal(r[3]) == Decimal(r[10]) and Decimal(r[4]) == Decimal(r[11]) == 2000
        assert Decimal(r[5]) == Decimal(r[12]) == Decimal(r[3]) * 2000
        assert r[13] == r[14] == 'POSTED' and r[15] in fp['receipt_ids']
    assert sum(Decimal(r[5]) for r in resolved) == 6000
    assert fp['resolved_contractor_component_qty_rate_amount_all_correct'] is True and fp['Nota_draft_post_added_no_stock_HPP_journal'] is True
    false_alarm = delta == {TARGET: 2}
    assert fp['false_alarm_reproduced'] is false_alarm
    assert fp['status'] == ('COUNTEREXAMPLE' if false_alarm else 'PASS')
    assert fp['contract_satisfied'] is (not false_alarm)
    opening = q['native']['cases']['SOL_R4_D01_OPENING_DERIVED_STATUS']
    assert opening['actual_opening'] == ['65.00', '0.00', 'OPEN']
    assert opening['fixture_scope'] == 'Opening-only accepted import, no unrelated Nota/payroll allocation.'
    expected = {f + ':V2620M_OPENING_SUBLEDGER_STATE': 1 for f in ['run_v267_financial_truth_checks', 'run_v268_financial_report_checks']}
    assert opening['phases'][0]['expected_deltas'] == expected and len(opening['phases']) == 1
    opening_review = reviewed_case('SOL_R4_D01_OPENING_DERIVED_STATUS', opening, run, args.artifact_id)
    assert opening['full_subject_row_restored'] is True
    fp_review = dict(case_id='SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM', run_id=run, artifact_id=args.artifact_id,
                     group='/native', raw_status=fp['status'], canonical_for_candidate=True, case_kind='NATIVE_BUSINESS_CONTRACT',
                     oracle_origin=fp['oracle_origin'], fixture_origin=fp['fixture_origin'], expected_alarm_count=0,
                     observed_alarm_count=phases['after_valid_post'][TARGET], actual_source_lineage_valid=True,
                     no_direct_fact_or_guard_change=True, full_boundary_restored=True)
    result = dict(state='READ_COUNTEREXAMPLE_WITH_ACTUAL_LINEAGE_AND_QUALIFIED_OPENING' if false_alarm else 'READ_HEALTHY_CONTROL_AND_QUALIFIED_OPENING',
                  run_id=run, job_id=args.job_id, artifact_id=args.artifact_id, archive_sha256=receipt['archive_sha256'],
                  selected_members_rehashed=len(receipt['selected_files']), raw_counts=q['counts'], raw_status=q['status'],
                  evidence_protocol_complete=True, full_primary_restore=True, first_run_preserved=39199375501,
                  first_opening_still_INCOMPLETE=True, false_alarm_reproduced=false_alarm,
                  false_alarm_disposition=dict(identity=TARGET, expected_healthy_count=0, observed_count=phases['after_valid_post'][TARGET],
                       status='COUNTEREXAMPLE_S1_VALID_FG_REPAIR' if false_alarm else 'PASS_HEALTHY_CONTROL', run_id=run, artifact_id=args.artifact_id,
                       case_id=fp_review['case_id'], source_type='FG_REPAIR', actual_header=header, resolved_source_rows=resolved,
                       phase_counts={name:{k:v for k,v in values.items() if v} for name,values in phases.items()}, all167_each_phase=True,
                       contractor_component_qty_rate_amount_correct=True, severity_source='ProMaxINV-D02',
                       Native_money_wrong=False, period_close_UI_blocked='NOT_VERIFIED', alarm_silenced=False),
                  canonical_cases=[fp_review, opening_review],
                  qualification_reason='First opening counter never started because a valid Nota predecessor raised two alarms. Isolated BB fixture proves the unchanged opening control; separate dispute preserves and resolves the valid-source false alarm.',
                  opening_qualified_same_literal65_0_OPEN=True, earlier8PASS_not_repeated=True,
                  protected_facts_observation_limit='Pinned runtime compares actual fingerprints before/after publicNota and rollback; the raw report exports the success assertion, not every fingerprint value. Actual PWI/wage/header rows and all167 detector rows are exported.',
                  limits=['No direct PWI, wage, source, journal, grant, guard or trigger edit. Nota allocations use accepted public Native commands.',
                          'The inherited identity recorder still exports static CP17 required counts341, declaration53fb2f86 and WRITER_DECLARED_CASES. Those fields are not the executed declaration or case count for this run. The separate qualification report binds the actual own manifest SHA256 and exactly two observed case IDs; before/after candidate/tree/product/workflow/run identities are valid.',
                          'This proves the diagnostic falseCRITICAL and audit/integrity gate violation, not an application period-close/payment blocker or a wrong6000financial value.',
                          'First9 group remains8PASS/1INCOMPLETE. New dispute COUNTEREXAMPLE is not renamedPASS and opening-only counter is a separately declared qualification.'])
    (A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['state'], q['counts'], 'false_alarm', false_alarm)

if __name__ == '__main__': main()
