"""Reconcile finite captured results; keep original failures and evidence origins."""
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'ci_receipts/sol_artifacts'


def read(artifact,name):
    path=RAW/str(artifact)/'files'/name
    body=path.read_bytes()
    return json.loads(body),dict(artifact_id=artifact,path=str(path.relative_to(ROOT)),bytes=len(body),sha256=sha256(body).hexdigest())


def save(name,body):
    (ROOT/name).write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n')


def main():
    x,source=read(12180497090,'CP7_CP17_FIXES.json')
    rows={}
    for group in ('native','races','http','browser','browser_enteng'):
        g=x[group];actual=g['races' if group=='races' else 'cases']
        assert set(actual)==set(x['required_case_ids'][group]) and len(actual)==x['required_case_counts'][group]
        assert all(r['status']=='PASS' for r in actual.values())
        assert not g.get('missing') and g.get('database_remaining',0)==0
        assert not g.get('cleanup_failures') and not g.get('auth_cleanup_failures')
        rows[group]=dict(count=len(actual),raw_status_counts=dict(Counter(r['status']for r in actual.values())),
                         all_ids_match_declaration=True,all_pass=True,cleanup_recorded_clean=True)
    assert x['status']=='PASS' and sum(r['count']for r in rows.values())==345
    assert x['cp6_restored'] and all(x['restore_components'].values()) and x['advisor_gate']
    cases=x['native']['cases'];valid=cases['CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL'];negative=cases['CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR']
    assert valid['baseline_all_zero'] and valid['detector_identities']==167 and valid['observed_delta']=={}
    assert valid['checker_before_r5_01']==dict(before=0,after=2)
    assert negative['wage_of_another_contractor_counted']==negative['missing_wage_counted']=={'run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor':1}
    save('CP17_RESULT_REVIEW.json',dict(state='FINAL_FINITE_INDEPENDENT_CP17_REVIEW',candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',run_id=39236711065,source=source,
         evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='WRITER_DECLARED_OR_ADOPTED_PRIOR_AUDITOR_ORACLES',fixture_origin='WRITER_SYNTHETIC_LOOPBACK',
         groups=rows,declared_case_count=345,observed_pass=345,cp6_restore_components=x['restore_components'],
         all_other_predecessor_definitions_and_owners_unchanged=x['all_other_predecessor_definitions_and_owners_unchanged'],
         r5_valid_repair=valid,r5_negative_control=negative,
         limitations=['39 scheduled-race cases do not imply39 independently qualified overlap/barrier proofs.',
                     'Enteng frontend build uses isolated local API interception; no hosted execution or installation credit.',
                     'Negative repair controls temporarily disable the immutable-wage trigger only during the declared corrupting write, then re-enable it before detection and roll back.',
                     'Writer valid-repair implementation records baseline_all_zero but does not assert it; actual value here is true and the separate unchanged Sol oracle asserts all167zero.',
                     'All11 writer reader comparisons use copied individual bodies with installed nested callees. The separate Sol full canonical graph comparison closes that finite coverage gap.']))
    base,bs=read(12180340258,'SOL_R5_ORIGINAL_CONTROLS.json')
    assert base['status']=='PASS' and base['counts']=={'PASS':11} and base['observed_unique_ids']==10 and base['cp6_restored']
    strict=base['groups']['dispute']['cases']['SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM']
    assert strict['status']=='PASS' and strict['observed_delta']=={} and strict['full_subject_and_protected_restore']
    for key in ('before','after_native_repair_sources','after_draft','after_valid_post','after_rollback'):
        values={r['function']+':'+r['check_name']:r['issue_count']for r in strict[key]}
        assert len(values)==167 and all(v==0 for v in values.values()),key
    native,ns=read(12181191212,'SOL_R5_READER_GRAPH.json')
    good=native['groups']['reader_graph']['cases']
    full=good['SOL_R5_READER_FULL_GRAPH_PO_SALE_RETURN'];rev=good['SOL_R5_VALID_REPAIR_REVERSED_AND_REALLOCATED_ZERO_ALARM']
    assert full['status']==rev['status']=='PASS' and native['counts']=={'PASS':2,'INCOMPLETE':1} and native['cp6_restored']
    for phase in full['graph_comparisons']:
        assert phase['installed_answers']==phase['legacy_graph_answers'] and len(phase['installed_answers'])==11
        assert phase['graph_restored'] and phase['protected_facts_and_guards_unchanged']
    assert [tuple(D(v)for v in r['observed'])for r in full['literal_book_oracles']]==[(D(120),D(0),D(0)),(D(96),D(24),D(0)),(D(108),D(12),D(0))]
    assert D(full['sale_lifecycle']['observed'])==24 and D(full['return_lifecycle']['observed'])==-12
    assert len(full['all_nine_detector_outputs_after_lawful_chain'])==167 and all(r['issue_count']==0 for r in full['all_nine_detector_outputs_after_lawful_chain'])
    assert len(rev['phases'])==5 and all(len(p['rows'])==167 and all(r['issue_count']==0 for r in p['rows'])for p in rev['phases'])
    mapping,ms=read(12182475716,'SOL_R5_READER_MAPPING_Q3.json')
    row=mapping['groups']['reader_mapping_q3']['cases']['SOL_R5_READER_PREPARED_MAPPING_FRESHNESS_Q3']
    assert mapping['status']=='PASS' and mapping['counts']=={'PASS':1} and mapping['cp6_restored']
    assert [D(str(p['observed']['fg_value']))for p in row['prepared_samples']]==[D(120),D(0),D(120)]
    assert all(p['installed_answers']==p['legacy_graph_answers'] and p['graph_restored']for p in row['graph_comparisons'])
    assert len(row['refusals'])==2 and all(p['observed']['sqlstate']=='P0001' for p in row['refusals'])
    capture,cs=read(12181651792,'SOL_R5_MULTIROW_CAPTURE_Q2.json')
    assert capture['status']=='PASS' and capture['native_case_credit_added']==0 and capture['original_raw_case_status']=='INCOMPLETE'
    assert capture['all11_graph_answers_equal'] and capture['all11_empty_queries_return_no_rows'] and capture['lifecycle_literal_rows']==['24.00','-12.00',None,'24.00']
    save('READER_AND_DETECTOR_RESULT_REVIEW.json',dict(state='FINAL_BOUNDED_READER_AND_DETECTOR_REVIEW',evidence_origin='INDEPENDENT_NATIVE_RERUN',candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',
         original_controls=dict(run_id=39237249873,source=bs,raw_counts=base['counts'],occurrences=11,unique_ids=10,case_code_byte_identical=True,full_restore=True),
         original_Sol_S1_reproduction=dict(case_id='SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM',status='PASS',all167zero_at_five_stages=True,observed_delta={},resolved_source_amount='6000',no_guard_or_fact_edit=True),
         full_graph=dict(run_id=39239045650,source=ns,status='PASS',all11_full_old_graph_compared_at_three_stages=True,literal_book_oracles=full['literal_book_oracles'],sale_lifecycle=full['sale_lifecycle'],return_lifecycle=full['return_lifecycle'],all167_actual_Owner_detector_counts_zero=True),
         reversed_repair=dict(run_id=39239045650,status='PASS',five_stages_all167zero=True,stock_HPP_journal_unchanged=rev['stock_HPP_journal_unchanged']),
         prepared_mapping=dict(run_id=39242137321,source=ms,status='PASS',prepared_samples=row['prepared_samples'],refusals=row['refusals'],all11_old_new_graph_equal_at_three_mapping_states=True,manual_prepare_deallocated=True,full_restore=True),
         single_statement_capture=dict(run_id=39240123342,qualification_run_id=39241538078,source=cs,raw_case_status='INCOMPLETE',classification=capture['classification'],capture_review_status='PASS',native_case_credit_added=0,all11_same_and_empty=True,po_literal_rows=capture['po_literal_rows'],lifecycle_literal_rows=capture['lifecycle_literal_rows'],final_inner_fingerprint_assertion_executed=False,strict_outer_and_case_restore=True),
         role_scope='Internal canonical readers run in the database-owner administrative session with Owner JWT claims; proper Owner detector outputs and public Auth proofs are separate. No UI authorization claim from canonical-reader comparisons.',
         limits=['Finite inputs, not a universal equivalence proof.','A deliberate mapping change can intentionally make books inconsistent; all collateral detector output is preserved and not claimed healthy.','Original raw audit-tool failures remain INCOMPLETE and provider FAILURE.','The read-only capture qualifier adds zero Native executions.']))
    docs=json.loads((ROOT/'CASE_LEDGER.json').read_text())['documents']
    f03=[]
    for d in docs:
        if (d['label'] or '').startswith('CP7_F03_FULL_'):
            body=json.loads((ROOT/d['path']).read_text())
            assert body['status']=='PASS' and body['groups_complete']
            assert body['observed_group_count']==body['predeclared_group_count'] and body['observed_case_count']==body['expected_case_count']
            assert body['observed_smoke_count']==body['expected_smoke_count'] and body['cp6_restored'] and all(body['restore_components'].values())
            f03.append(dict(bucket=body['bucket'],source=d,declared_cases=body['expected_case_count'],observed_cases=body['observed_case_count'],smoke=body['observed_smoke_count'],groups=body['observed_group_count'],all_three_restore_components=True,payroll_delta=body['payroll_checks'],reader_delta=body['report_accounts']))
    assert len(f03)==8
    p21,ps=read(12180282234,'CP7_P21_FULL_REHEARSAL.json');steps={s['step']:s for s in p21['steps']}
    assert p21['status']=='PASS' and steps['PREUSE_ROLLBACK']['restored_exactly'] and steps['REINSTALL']['identical_to_first']
    assert steps['POSTUSE_ROLLBACK']['status']=='REFUSED' and steps['USED_BACKUP_RESTORE']['data_differ']=={} and steps['USED_BACKUP_RESTORE']['cp7_catalog_equal']
    assert steps['ROLLBACK_BY_PREINSTALL_RESTORE']['data_differ']=={} and steps['ROLLBACK_BY_PREINSTALL_RESTORE']['cp7_objects_absent']
    assert p21['restore_components']['erp_platform_auth_schema_acl'] is False and p21['harness_restore']['exact'] is False
    cleanup,ks=read(12180955196,'CP7_K3_CLEANUP.json');boundary=cleanup['races']['races']['K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID']['B_replaced_before_restore']
    assert 'restore wrote into the replacement' in boundary['boundary']
    save('REGRESSION_AND_RESTORE_REVIEW.json',dict(state='FINAL_AFFECTED_F03_AND_RESTORE_REVIEW',evidence_origin='INDEPENDENT_NATIVE_RERUN',
         full_f03=f03,all8_full_f03_buckets_pass=True,source_scope='Exact r4 workflow templates retargeted to pinned r5; external bootstrap attempts4->2, no application budget or business oracle raised.',
         p21_full=dict(run_id=39237719084,source=ps,preuse_rollback_exact=True,reinstall_same_catalog=True,postuse_uninstall_refused=True,used_backup_new_copy_590_tables_equal=True,preinstall_backup_new_copy_equal=True,
                       postuse_harness_exact_restore=False,postuse_restore_components=p21['restore_components'],postuse_business_tables_changed=len(p21['harness_restore']['erp_data_changed_by_use']),cluster_roles_after_preinstall_restore=steps['ROLLBACK_BY_PREINSTALL_RESTORE']['cluster_roles_still_present']),
         k3_known_boundary=dict(run_id=39237719026,source=ks,raw_status='PASS',replacement_write_before_mismatch=True,boundary=boundary,disposition='KNOWN_OWNER_DEFERRED_CP7C_NOT_APPLIED'),
         limits=['P21 PASS does not mean post-use uninstall restores committed data. Use the demonstrated new-copy backup restore.','No hosted/Enteng installation, physical cutover, Drive offsite or shadow period is claimed.','K3 expected refusal is not proof that replacement received no write.']))
    negative,nsource=read(12183518429,'SOL_R5_REPAIR_NEGATIVE_VECTOR.json')
    nr=negative['groups']['repair_negative_vector']['cases']['SOL_R5_REPAIR_CHECKER_FULL_167_NEGATIVE_VECTORS']
    assert negative['status']=='PASS' and negative['counts']=={'PASS':1} and negative['cp6_restored']
    assert nr['all167_vectors_exported'] and len(nr['phases'])==6
    for phase in nr['phases']:
        actual={v['function']+':'+v['check_name']:v['issue_count']for v in phase['rows']}
        assert len(actual)==167 and {k:v for k,v in actual.items()if v}==phase['expected_nonzero']
    reviewed=json.loads((ROOT/'READER_AND_DETECTOR_RESULT_REVIEW.json').read_text())
    reviewed['strict_repair_negative_vectors']=dict(run_id=39246794670,source=nsource,status='PASS',absolute0_1_0_on_wrong_and_missing=True,
        phases=[dict(label=p['label'],exported_identities=len(p['rows']),actual_nonzero={v['function']+':'+v['check_name']:v['issue_count']for v in p['rows']if v['issue_count']})for p in nr['phases']],
        complete_boundary_restored=nr['full_boundary_restored'],trigger_enabled_at_detection=True,
        control_fixture_exception='One immutable-wage guard disabled only for each legacy inconsistency write, re-enabled before detection and restored by rollback; not a permission or guard-prevention proof.')
    reviewed['strict_target_sensitivity_uses_new_Sol_full_vectors_not_CP17_delta_only']=True
    save('READER_AND_DETECTOR_RESULT_REVIEW.json',reviewed)
    print(json.dumps(dict(cp17_pass=345,original_controls_pass=11,new_full_graph_pass=True,reversed_repair_pass=True,prepared_mapping_pass=True,multirow_capture_qualified_without_replay=True,f03_buckets=8,p21_new_copy_restore=True,original_auditor_tool_failures_preserved=3)))


if __name__=='__main__':main()
