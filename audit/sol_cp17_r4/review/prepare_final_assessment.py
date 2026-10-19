"""Compose the assessment from already reviewed evidence; no runtime execution."""
from pathlib import Path
from collections import Counter
import json

A = Path(__file__).resolve().parents[1]
SHA = '663f6faefcbb9c70f0f99bbc7e78164e03521329'
TREE = '023f3554432f80f994439f5d0b8cc164846a2041'

def load(name): return json.loads((A / name).read_text())
def save(name, value): (A / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    canonical = [json.loads(line) for line in (A / 'ci_receipts/SOL_QUALIFIED_CASE_INDEX.jsonl').read_text().splitlines()]
    receipt = load('ci_receipts/OWN_CI_RECEIPT_FINAL.json')
    register = load('ci_receipts/ROOT_RUN_REGISTER.json')
    dispute = load('PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json')
    assert dispute['false_alarm_reproduced'] is True and dispute['evidence_protocol_complete'] is True
    assert receipt['terminal_run_count'] == len(register) == 60
    state = 'FINAL_LIMITED_SCOPE_ASSESSMENT'
    matrices = {name: load(name + '_MATRIX.json') for name in ['INVARIANT', 'SCENARIO', 'CHAIN']}
    gaps = []
    for family, data in matrices.items():
        key = 'invariant' if family == 'INVARIANT' else 'id'
        for row in data['rows']:
            if row['status'] == 'INCOMPLETE':
                gaps.append(dict(id=row[key], family=family, status='INCOMPLETE', requirement=row['requirement'],
                                 evidence_scope=row['current_scope'], next_action=row['next_action'],
                                 proved_product_bug=False, evidence='{}_MATRIX.json'.format(family)))
    first_failures = [
        (39185988432, 'AUDITOR_FIXTURE_ROLE_CODE_CUSTOM', 'OWNER/ADMIN 2PASS retained; STAFF stopped before guard calls.', 'FRESH_TX_RESULT_REVIEW.json'),
        (39188635131, 'AUDITOR_FIXTURE_DUPLICATE_INACTIVE_STAFF', 'STAFF compatibility role exists inactive; no third attempt or profile activation.', 'FRESH_TX_RESULT_REVIEW.json'),
        (39191503650, 'AUDITOR_PREREQUISITE_JSONSCHEMA_IMPORT', 'Product installation prerequisite completed; zero metadata cases. One declared prerequisite retry supplied dependency4.25.1.', 'Q1_STATE_RESULT_REVIEW.json'),
        (39193178808, 'AUDITOR_DRAFT_INVOICE_READBACK_TABLE', '3INCOMPLETE preserved; successful BD DRAFT was read from wrong core table before POST.', 'JOURNEY_INITIAL_RESULT_REVIEW.json'),
        (39193738642, 'AUDITOR_CLAIM_PREINVOICE_ORACLE', 'Claim128 omitted fifth-piece estimate2; source contract130. Separate free-rewash firstPASS never repeated.', 'JOURNEY_INITIAL_RESULT_REVIEW.json'),
        (39195171465, 'AUDITOR_FORM_STATE_AND_LABEL_OBSERVATION', '4INCOMPLETE preserved. Undo reasons reset after remount; claim main_text0 is observer fallback, not proved crash. Q3 separate qualified PASS.', 'JOURNEY_Q2_RESULT_REVIEW.json'),
        (39195943779, 'AUDITOR_THREE_FINITE_ORACLE_OR_API_ERRORS', '5PASS preserved; rawAP/GL-cent mismatch, TypeScript7 legacy API assumption, nonexistent daily selector fixed only in3qualified IDs.', 'FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json'),
        (39197469845, 'AUDITOR_ACCESSORY_PREFIX_64_EXCEEDS_VARCHAR60', '3PASS retained; accessory stopped before fixture/counter. Qualified prefix48 kept source/predicates/expected unchanged.', 'MUTABLE_DETECTOR_RESULT_REVIEW.json')]
    known = [
      dict(id='KNOWN-P19-DIRECT-LATENCY', severity='S2', status='OPEN_MEASURED_PERFORMANCE_GAP', novelty='KNOWN_NOT_NEW_BLIND_DISCOVERY',
           first_seen_sha='b53b5acdf260b03ebac3474e9ae837fcef6f6eb1', retested_sha=SHA, evidence_origin='INDEPENDENT_SOL_EXECUTION_OF_WRITER_MEASUREMENT_CONTRACT',
           run_id=39185235564, artifact_id=12159513142, evidence='PERFORMANCE_RESULT_REVIEW.json',
           exact_measurement_ids=['P19S_BROWSER_100_1_CAPTURE_WITH_FINANCE', 'P19S_BROWSER_100_30_CAPTURE_WITH_FINANCE', 'P19S_BROWSER_100_100_CAPTURE_WITH_FINANCE'],
           observed_ms=['4296.9', '4251.8', '4664.5'], threshold_ms=3000, direct_300_ms_range=['5453.6', '7022.9'],
           source_expected='D17-2 preserves ordinary/direct3s target; named BACKGROUND/STAGED exceptions are separately assessed. Per-call8s/caps unchanged.',
           staged_5000=dict(completed_targets=5000, pages=26, elapsed_ms=['76509.1', '98373.9'], progress_ms=['2439.4', '2904.3'], reopen_ms=['1342', '1398.6'], whole_journey_three_second_PASS=False),
           remedy='Writer next on a separate branch perD17-2: profile report/readiness/repeated work, optimize complete current projections, remeasure exact same IDs/sizes with current authority/source/hash/caps. Do not raise timeout, sample or truncate data as a fix.', owner='WRITER_NEXT_SEPARATE_BRANCH_THEN_AUDITOR', owner_question_needed=False),
      dict(id='KNOWN-POOL-PUBLIC-ENTRYPOINTS', severity='UNASSIGNED_REMAINING_NATIVE_SCOPE', status='DATA_API_CLOSED_NATIVE_DB_SCOPE_OWNER_DEFERRED_CP7C',
           first_seen_sha='b53b5acdf260b03ebac3474e9ae837fcef6f6eb1', retested_sha=SHA, evidence='CP17_RESULT_REVIEW.json; SOURCE_REVIEW.md',
           proved='Four public legacy pool wrappers are among25AuthDataAPI closures with403/42501; current facade positive controls pass. Native DB sessions/grants are deliberately unchanged.',
           not_proven='No fresh mutating closed-period bypass via a DB session. Prior held pool counterfixture was not resumed.',
           owner_decision='D14-9 preserves Native DB compatibility untilCP7C; r4 route closure fixes the prior public DataAPI boundary.',
           remedy='Retain DataAPI first-statement closure; operator/writerCP7C must execute the already-defined Native entrypoint/grant installation boundary.', owner='WRITER_OPERATOR_CP7C'),
      dict(id='KNOWN-BACKUP-REPLACEMENT-WRITE', severity='UNASSIGNED_KNOWN_OPERATIONAL_BOUNDARY', status='OWNER_DEFERRED_CP7C_NOT_APPLIED',
           first_seen_sha='b53b5acdf260b03ebac3474e9ae837fcef6f6eb1', retested_sha=SHA, evidence='RESULT_REVIEW.json; REHEARSAL_RESULT_REVIEW.json',
           proved='K3boundaryB writes to replacement scratch beforeBACKUP_SCRATCH_REPLACED; replacement remains. Current candidate has no KNOWN_REPLACEMENT patch.',
           owner_decision='D13-9a: patch prepared forCP7C, not applied during this audit.', remedy='Apply/qualify target-ownership replacement protection atCP7C; keep mismatch first result and replacement identity. Use proved new-copy restore for data recovery.', owner='WRITER_OPERATOR_CP7C'),
      dict(id='KNOWN-HISTORICAL-KNOWLEDGE-QUERY', severity='UNASSIGNED_EXPLICIT_CAPABILITY_BOUNDARY', status='GENERAL_AS_KNOWN_NOT_IMPLEMENTED',
           retested_sha=SHA, evidence='INVARIANT_MATRIX.json:INV-T04; FUNCTION_DETAIL.json',
           proved='Immutable filed/captured Original is retained and current reads state historical knowledge NOT_RECONSTRUCTED; arbitrary general as_known reconstruction is not accepted.',
           remedy='Specify and implement the required general historical-knowledge query before claiming that capability; do not rewrite filed Original.', owner='WRITER_CONTRACT_SOURCE')]
    finding = dict(id='SOL-R4-001',severity='S1',status='OPEN_PROVED_COUNTEREXAMPLE',
          title='Valid FG_REPAIR Nota produces false CRITICAL wrong-contractor alarms',
          first_seen_sha=SHA,introduced_sha='UNKNOWN_NOT_CLAIMED_INTRODUCED_IN_R4',
          evidence_origins=['INDEPENDENT_NATIVE_RERUN','INDEPENDENT_SOURCE_REVIEW'],
          evidence_level='NATIVE_QUALIFIED',first_run_id=39199375501,first_artifact_id=12163127220,
          confirming_run_id=dispute['run_id'],confirming_job_id=dispute['job_id'],confirming_artifact_id=dispute['artifact_id'],
          evidence='PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json',case_id='SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM',
          raw_status='COUNTEREXAMPLE',severity_basis='ProMax INV-D02 explicitly assigns S1 to a false alarm on a correct book.',
          detector=dispute['false_alarm_disposition']['identity'],expected_healthy_count=0,observed_count=2,observed_severity='CRITICAL',
          locations=[dict(path='supabase/migrations/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql',line=187,role='Original checker resolves only PRODUCTION/REWORK; actual installed body separately exported.'),
                     dict(path='scripts/cp6_ax_build.py',line=101,role='Native assembly adds supported FG_REPAIR eligibility/validator/merge but not this checker resolver.'),
                     dict(path='scripts/cp7-src/payroll/source.sql',line=41,role='Current CP7 source resolver supports FG_REPAIR wage/receipt.'),
                     dict(path='scripts/cp7_nota_cases.py',line=39,role='Accepted positive SAVE/POST precedent.')],
          reproduction=['Create accepted Native repair wages for2PCS and1PCS at2000 each.',
                        'Save and post one public CP7 Nota selecting the two correct source cards; actual payroll CALCULATED amount6000.',
                        'Resolve each actual PWI against FG_REPAIR wage/receipt: source and payroll contractor/component equal, quantities1/2, amounts2000/4000, source statusPOSTED.',
                        'Observe all167 detector identities: before/after Native repair/after draft all0; after validPOST only wrong_contractor2; afterrollback all0.'],
          impact_chain='Valid FG_REPAIR source -> Nota -> payroll_work_items -> unsupported detector contractor resolution -> two false CRITICAL audit/integrity findings.',
          affected_invariants=['INV-D01','INV-D02','INV-D03'],affected_chain='S3',affected_function_needs=['FUN-039','FUN-041'],
          financial_amount_wrong=False,period_close_or_payment_UI_blocked='NOT_VERIFIED',
          native_source_rows=dispute['false_alarm_disposition']['resolved_source_rows'],
          full_boundary_restored=True,no_fact_guard_or_grant_bypass=True,
          remedy='Extend the Native checker source resolver for supported FG_REPAIR wage/receipt contractor/component/status. Preserve real wrong-contractor/orphan checks. Update proper AX/installer replaced-definition pins/capture/restore; do not silence/filter the alarm or arbitrarily edit a frozen historical migration.',
          required_retest=['The valid two-line6000 case must reproduce2 before fix and0 after, with all167 counts exported.',
                           'Retain legitimate wrong-contractor and orphan refusal/detector controls and no false positives for supported PRODUCTION/REWORK/FG_REPAIR.',
                           'Verify install/capture/restore definitions and Nota/payroll financial/stock/HPP invariants.'],
          owner='WRITER_NATIVE_DETECTOR_AND_INSTALLER_THEN_INDEPENDENT_AUDITOR',owner_question_needed=False)
    findings = dict(report_state=state, candidate_sha=SHA, candidate_tree=TREE, product_fixes_made=False,
                    peer_r4_read=False, cross_check_after_seal_results=[], new_product_findings=[finding],
                    severity_summary=dict(S0=0,S1_new=1,S2_known_open=1,S3_new=0),
                    new_product_findings_limit='One root cause, not three findings for three affected invariants. It is first confirmed on the candidate; introduction in r4 is not claimed. Financial6000 is correct; application payment/period-close blocking is not verified.',
                    potential_product_findings=[],
                    known_open_product_or_operating_gaps=known, closed_findings_reference='RETEST_DISPOSITIONS.json',
                    audit_evidence_gaps=gaps,
                    extra_unexecuted_controls=[dict(id='STAFF_FRESH_TX_ALLOW', status='NOT_EXECUTED_AFTER_TWO_AUDITOR_FIXTURE_FAILURES', evidence='FRESH_TX_RESULT_REVIEW.json', owner='AUDITOR', product_bug_inferred=False),
                                                dict(id='HELD_R3_THREE_DESIGNS', status='NOT_EXECUTED_PRIOR_SESSION_SCOPE_HOLD', owner='AUDIT_COORDINATOR', action='Do not resume through changed values, renamed jobs or another transport; no current PASS or bug credit.')],
                    original_provider_failures=[dict(run_id=r, classification='AUDITOR_TOOL', detail_classification=k, disposition=t, review=f, raw_provider_status='failure', original_preserved=True) for r,k,t,f in first_failures] +
                       [dict(run_id=39199375501,classification='PRODUCT_ALARM_ON_VALID_PREDECESSOR',disposition='8PASS/1INCOMPLETE remains; opening counter did not start because valid Nota raised2 false CRITICAL alarms. It is not an auditor fixture error.',review='DERIVED_DETECTOR_RESULT_REVIEW.json',raw_provider_status='failure',original_preserved=True),
                        dict(run_id=39200571137,classification='PRODUCT_COUNTEREXAMPLE',disposition='1COUNTEREXAMPLE/1PASS, evidence protocol complete. Confirmed S1 is not renamed PASS.',review='PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json',raw_provider_status='failure',original_preserved=True)],
                    feature_complete=False, audit_complete=False, production_go=False, owner_questions_reopened=False)
    save('FINDINGS.json', findings)
    old = load('ci_receipts/retained_r3/RETEST_DISPOSITIONS.json')
    items = []
    for row in old['items']:
        item = dict(id=row['id'], prior_status=row['status'], status='RETAINED_PRIOR_CLOSED_SCOPE',
                    retained_seal='ff6374ad6edef19896c32258e3f30172a95069bd', prior_candidate=old['candidate_sha'],
                    prior_record=row, runtime_credit_r4_for_prior_record=0, current_candidate=SHA)
        if row['id'] == 'SOL-R2-001':
            item.update(status='CLOSED_CURRENT_PO_NUMBER_BOUNDARIES', current_evidence='CP17_RESULT_REVIEW.json',
                        current_proof='999/1000/999→1000/1001/10000 exact bounded response; UUID replay once. Originalr2three-second counterexample retained.')
        if row['id'] == 'SOL-R1-001':
            item.update(status='RETAINED_CLOSED_PLUS_CURRENT_CASH_DATE_CONTROLS', current_evidence='CP17_RESULT_REVIEW.json; DOCUMENT_RECALCULATIONS.json',
                        bookkeeping='Old stale INV-POL03 cash-open text was corrected at r3seal. It is not reopened here; current cash economic/book/accrual guards independently rerun.')
        if row['id'] in ['SOL-R1-004', 'SOL-R1-005', 'KNOWN-UI-MODE']:
            item.update(current_evidence='INITIAL_RESULT_REVIEW.json; CP17_RESULT_REVIEW.json; FUNCTION_DETAIL.json',
                        current_proof='Current47menu census/connected Enteng views are separately witnessed; old hidden-menu permission is superseded byD16-1 connected scope.')
        items.append(item)
    for ident, status, proof, review in [
       ('R4-01','CLOSED_TESTED_DATA_API_SCOPE','25legacy route HTTP403/42501 plus valid facade200; Native DB boundary remains distinct.','CP17_RESULT_REVIEW.json'),
       ('R4-02','CLOSED_TESTED_ACTIVE_USAGE_SCOPE','10+2−2=10/HPP120÷10; active usage2 refuses and cancel releases.','CP17_RESULT_REVIEW.json'),
       ('R4-03','CLOSED_TESTED_LATE_COMMIT_SCHEDULE','Low uncommitted ID below high cutoff later commits; marker changes/filter control/reload exact.','CP17_RESULT_REVIEW.json'),
       ('R4-04','CLOSED_MEASURED_47_MENU_SCOPE','47menus exact,290WIP ratios minimum5.1718195 versus4.5; helper exclusions and overwritten ordinary detail retained.','CP17_RESULT_REVIEW.json'),
       ('R4-05','QUALIFIED_OWNER_ADMIN_BRANCH_STAFF_UNEXECUTED','Assigned writer8calls plus own OWNER/ADMIN8calls withNULL entry; STAFF never executed after two tool failures.','FRESH_TX_RESULT_REVIEW.json'),
       ('R4-Q1','CLOSED_FOUR_METADATA_ID_SCOPE','5cron rows all succeeded/ended/start ordered, waitTrue, cleanup exact; initial dependency failure retained.','Q1_STATE_RESULT_REVIEW.json'),
       ('B5-B6','CLOSED_DEFINED_BROWSER_LINEAGES','ordinary3+claimQ3 and separate first free-rewashPASS. Literal costs/lineage/cash/AP/inverse checked.','JOURNEY_Q3_RESULT_REVIEW.json; JOURNEY_INITIAL_RESULT_REVIEW.json'),
       ('SKN-24-26','CLOSED_DEFINED_FINITE_BOUNDARIES','Eight unique canonical IDs from initial5PASS plus qualified3PASS,27actual client helper controls; no global numeric N/A.','FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json')]:
        items.append(dict(id=ident,status=status,retested_sha=SHA,evidence_origin='INDEPENDENT_SOL_EXECUTION_WITH_EXPLICIT_ORACLE_ORIGINS',proof=proof,evidence=review))
    save('RETEST_DISPOSITIONS.json',dict(report_state=state,candidate_sha=SHA,prior_seal='ff6374ad6edef19896c32258e3f30172a95069bd',items=items,
                                        r3_runtime_not_relabelled=True,old_cash_bookkeeping_corrected=True,product_fixes_made=False,peer_r4_read=False))
    save('OPEN_BOUNDARIES.json',dict(report_state=state,candidate_sha=SHA,feature_complete=False,audit_complete=False,production_go=False,
                                   scope_gaps=gaps,extra_limits=findings['extra_unexecuted_controls'],known_operating_boundaries=[x for x in known if x['id']!='KNOWN-P19-DIRECT-LATENCY'],
                                   production_gate='CP6 CLOSED accepted does not equal CP7 integration acceptance or production GO. Real hosted/cutover/shadow/source reconciliation remains operatorCP7C scope.',
                                   detector_detail='DETECTOR_DISPOSITIONS.json; all167identities have source predicates, specific classification and next action. Prevention-only is not sensitivity PASS.'))
    save('ASSESSMENT_COUNTS.json',dict(report_state=state,candidate_sha=SHA,own_registered_runs=len(register),own_reconciled_runs=receipt['terminal_run_count'],
                                     provider_status_counts=receipt['provider_conclusions'],provider_job_count=receipt['provider_job_count'],provider_artifacts=receipt['provider_artifact_count'],
                                     downloaded_ZIP_receipts=receipt['downloaded_archive_count'],exact_decoded_logs=receipt['exact_completed_decoded_logs'],
                                     CP17=dict(canonical_occurrences=341,unique_id_strings=341,Native=161,race_schedules=39,Auth_HTTP=27,ordinary_browser=57,Enteng_build_browser=57),
                                     broad_current=dict(reports=66,business_runs=40,case_occurrences=2121,unique_id_strings=1487,source_oracle='WRITER_DECLARED; SOL_EXECUTION_AND_DOCUMENT_ARITHMETIC'),
                                     Sol_contract_qualified=dict(unique_ids=len(canonical),raw_status_counts=dict(Counter(r['raw_status'] for r in canonical)),business=sum('BUSINESS' in r['case_kind'] for r in canonical),pure_helpers=sum(r['case_kind']=='CLIENT_PURE_HELPER' for r in canonical),detector_controls=sum(r['case_kind']=='DETECTOR_CONTROL' for r in canonical),prevention_only=sum(r['case_kind']=='GUARD_PREVENTION_ONLY' for r in canonical)),
                                     metadata_Q1=dict(ids=4,cron_rows=5,runtime_business_credit=0),fresh_tx=dict(PASS_ids=2,INCOMPLETE_ids=1,PASS_calls=8,STAFF_calls=0),
                                     coverage={k:dict(denominator=v['denominator'],status_counts=v['status_counts']) for k,v in matrices.items()},
                                     detector=load('DETECTOR_DISPOSITIONS.json')['status_counts'],counts_are_not_ERP_percent=True,feature_complete=False,audit_complete=False,production_go=False))
    print(state, len(gaps), 'matrix gaps; canonical IDs', len(canonical))

if __name__ == '__main__': main()
