"""Carry the sealed r4 scope explicitly; never relabel old execution as r5."""
from collections import Counter,defaultdict
from hashlib import sha256
import argparse
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CANDIDATE='17fa25075ba77f0853c3c16f504288ace03eec35'
SEAL='ecb44425710a0a29203835076f32ef83f7d436d2'
BASE='663f6faefcbb9c70f0f99bbc7e78164e03521329'


def write(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def main(prior):
    prior=Path(prior)
    ledger=json.loads((ROOT/'CASE_LEDGER.json').read_text());by_id=defaultdict(list)
    for row in ledger['cases']:
        if row['raw_status']=='PASS':by_id[row['case_id']].append(row)
    def witness(ident):
        return [dict(case_id=r['case_id'],raw_status=r['raw_status'],artifact_id=r['artifact_id'],document=r['document'],group_pointer=r['group_pointer'],document_sha256=r['document_sha256'],evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin=r['oracle_origin'],fixture_origin=r['fixture_origin'])for r in by_id.get(ident,[])][:4]
    original=json.loads((ROOT/'ci_receipts/sol_artifacts/12180340258/files/SOL_R5_ORIGINAL_CONTROLS.json').read_text())
    current_controls=defaultdict(list)
    for group,g in original['groups'].items():
        for ident,row in g['cases'].items():
            for phase in row.get('phases',[]):
                for key,value in phase.get('observed_deltas',{}).items():
                    if value==1:current_controls[key].append(dict(case_id=ident,phase=phase['name'],run_id=39237249873,artifact_id=12180340258,trigger_or_guard_disabled=False,expected_delta=1,observed_delta=1,all167_outputs_retained=True))
    target='run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor'
    strict_negative=json.loads((ROOT/'ci_receipts/sol_artifacts/12183518429/files/SOL_R5_REPAIR_NEGATIVE_VECTOR.json').read_text())
    neg=strict_negative['groups']['repair_negative_vector']['cases']['SOL_R5_REPAIR_CHECKER_FULL_167_NEGATIVE_VECTORS']
    assert neg['status']=='PASS' and neg['all167_vectors_exported'] and len(neg['phases'])==6
    for phase in neg['phases']:
        actual={r['function']+':'+r['check_name']:r['issue_count']for r in phase['rows']}
        assert len(actual)==167 and {k:v for k,v in actual.items()if v}==phase['expected_nonzero']
    current_controls[target].append(dict(case_id='SOL_R5_REPAIR_CHECKER_FULL_167_NEGATIVE_VECTORS',run_id=39246794670,artifact_id=12183518429,expected_delta=1,observed_delta=1,fixtures=['WRONG_CONTRACTOR','MISSING_WAGE'],absolute_zero_one_zero=True,all167_vectors_exported=True,trigger_temporarily_disabled_during_fixture_write=True,trigger_reenabled_before_detector=True,rollback_verified=True,not_UI_auth_or_guard_prevention_proof=True))
    assert len(current_controls)==11
    old=json.loads((prior/'DETECTOR_DISPOSITIONS.json').read_text())
    active=json.loads((ROOT/'ci_receipts/sol_artifacts/12180340258/files/SOL_R5_ORIGINAL_CONTROL_FUNCTIONS.json').read_text())
    old_controlled={r['identity']for r in old['rows']if r['negative_control_disposition']=='PASS_EXACT_0_1_0'}
    union=old_controlled|set(current_controls)
    assert len(old_controlled)==21 and len(union)==22
    detector_rows=[]
    for oldrow in old['rows']:
        ident=oldrow['identity'];fn=oldrow['function'];definition=active[fn]
        row=dict(identity=ident,function=fn,check_name=oldrow['check_name'],
                 active_runtime_function=dict(artifact_id=12180340258,path='ci_receipts/sol_artifacts/12180340258/files/SOL_R5_ORIGINAL_CONTROL_FUNCTIONS.json',sha256=sha256(definition.encode()).hexdigest(),binding='CURRENT_R5_PG_GET_FUNCTIONDEF_MATCHED_TO_PREDECLARED_R5_TRANSFORMS'),
                 retained_r4_predicate_sql=oldrow['predicate_sql'],retained_r4_predicate_origin=oldrow['predicate_origin'],
                 retained_r4_predicate_is_not_relabelled_as_current_body=True,
                 source_review='R5 changes only declared scalar lookup wrappers in run_v267/run_v268 and the FG_REPAIR contractor resolver; other six exported checker bodies are byte-identical to pinned r4 definitions. See static impact/retest manifests.',
                 normal_current_zero_observed=True,normal_current_zero_source=witness('SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM'),
                 current_negative_control_disposition='PASS_EXACT_0_1_0' if ident in current_controls else 'TIDAK_TERUJI_PADA_R5',
                 current_negative_controls=current_controls.get(ident,[]),
                 retained_r4_negative_disposition=oldrow['negative_control_disposition'],retained_r4_runtime_credit_r5=0,
                 across_rounds_ever_qualified=ident in union,
                 current_missing_control_classification=None if ident in current_controls else oldrow.get('classification'),
                 current_predicate_fact_lineage_next_action=None if ident in current_controls else 'Design/review the exact single-fact negative fixture and expected collateral counts before execution; retain all167 before/during/rollback. Existing held access designs remain held. No product fault inferred from missing sensitivity proof.')
        detector_rows.append(row)
    write('DETECTOR_DISPOSITIONS.json',dict(state='FINAL_CURRENT_AND_RETAINED_SENSITIVITY_DIMENSIONS_SEPARATE',candidate_sha=CANDIDATE,denominator=167,
          current_r5_counts=dict(PASS_EXACT_0_1_0=11,TIDAK_TERUJI_PADA_R5=156),across_rounds_counts=dict(EVER_QUALIFIED=22,NEVER_QUALIFIED=145),
          retained_control_union_is_not_current_runtime_credit=True,global_INV_D01_closed=False,audit_complete=False,
          retained_source=dict(seal=SEAL,path='audit/sol_cp17_r4/DETECTOR_DISPOSITIONS.json',sha256=sha256((prior/'DETECTOR_DISPOSITIONS.json').read_bytes()).hexdigest()),rows=detector_rows))
    invariant_count=None
    for name,key in [('INVARIANT_MATRIX.json','invariant'),('SCENARIO_MATRIX.json','scenario'),('CHAIN_MATRIX.json','id')]:
        old=json.loads((prior/name).read_text());rows=[]
        for oldrow in old['rows']:
            ident=oldrow.get(key) or oldrow.get('id') or oldrow.get('invariant') or oldrow.get('scenario')
            assert ident is not None
            fresh=[]
            for w in oldrow.get('current_witness_examples',[]):fresh.extend(witness(w.get('case_id')))
            row={key:ident,'requirement':oldrow['requirement'],'status':oldrow['status'],
                 'current_scope':'Retained r4 bounded scope, with fresh r5 witnesses below where actually executed: '+oldrow['current_scope'],
                 'current_witness_examples':fresh[:8],
                 'retained_r4_status':oldrow['status'],'retained_r4_scope':oldrow['current_scope'],
                 'retained_r4_witness_examples':oldrow.get('current_witness_examples',[]),
                 'retained_r4_runtime_credit_r5':0,'retained_r4_seal':SEAL,
                 'evidence_origins':(['INDEPENDENT_NATIVE_RERUN'] if fresh else [])+['INDEPENDENT_SOURCE_REVIEW','REUSED_AUDITOR_LOG_READ'],
                 'qualification':'PASS is limited to the written current/retained scope. Unchanged source and old execution do not become fresh r5 execution or whole-ERP acceptance.'}
            for field in ('next_action','negative_sensitivity_dimension','positive_healthy_book_dimension'):
                if field in oldrow:row[field]=copy.deepcopy(oldrow[field])
            if ident in ('INV-D01','INV-D02','INV-D03','S3'):
                row['current_witness_examples']=witness('SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM')+witness('CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR')+witness('SOL_R5_VALID_REPAIR_REVERSED_AND_REALLOCATED_ZERO_ALARM')
                row['evidence_origins']=['INDEPENDENT_NATIVE_RERUN','INDEPENDENT_SOURCE_REVIEW','REUSED_AUDITOR_LOG_READ']
                row['next_action']=None
                if ident=='INV-D01':
                    row.update(status='INCOMPLETE',current_scope='The valid FG_REPAIR false alarm is closed. Current exact negative sensitivity is11/167;156 lack a fresh r5 negative control. Across Sol rounds22 are qualified and145 still lack a qualified negative. Normal zeros and Native guard prevention are not sensitivity proof.',negative_sensitivity_dimension=dict(status='INCOMPLETE',current_r5=dict(PASS=11,TIDAK_TERUJI=156),across_rounds=dict(EVER_QUALIFIED=22,NEVER_QUALIFIED=145)),positive_healthy_book_dimension='PASS_FOR_RETESTED_VALID_REPAIR_AND_LAWFUL_PO_CHAIN',next_action=dict(owner='Auditor/consolidation',classification='PER_PREDICATE_NEGATIVE_PROOF_MISSING',action='Use DETECTOR_DISPOSITIONS per identity; preserve held access boundaries; do not close global INV-D01.',executable_now=False))
                elif ident=='INV-D02':row.update(status='PASS',current_scope='Original Sol healthy Nota2+1PCS at2000 gives6000 and all167zero before/source/DRAFT/POST/rollback. Old checker still+2; wrong/missing repair each+1. REVERSED then replacement Nota6000 also all167zero. Closed SOL-R4-001 within these finite paths.')
                elif ident=='INV-D03':row.update(status='PASS',current_scope='Actual installed checker resolves current FG_REPAIR wage contractor through the declared join/coalesce; original production/rework branches and other two checks are unchanged. Exact runtime fingerprints, healthy Nota, wrong/missing controls and REVERSED/reallocation verified.')
                else:row.update(status='PASS',current_scope='Financial attendance/Nota/payroll/cash lifecycle retained and rerun via full F03P12. The former FG_REPAIR integrity failure is closed by original Sol strict zero oracle and negative controls. No claim that old payment/period-close UI was blocked, and no one-browser universal journey claimed.')
            if ident=='SKN-19':
                row['current_scope']='Append-only refusals retained; valid FG_REPAIR false alarm closed on r5. Current exact detector negative controls11/167; across Sol rounds22/167, not universal sensitivity. Full167 vectors exported for valid repair and wrong/missing wage, then rollback.'
                row['next_action']=dict(classification='PARTIAL_SENSITIVITY_NOT_A_CURRENT_FALSE_ALARM',owner='Auditor/consolidation',action='Use DETECTOR_DISPOSITIONS per identity:11 current controls,156 without a fresh r5 negative;22 ever qualified,145 never qualified. Keep guard prevention separate and preserve held access boundaries. SOL-R4-001 is closed on installed r5.',executable_now=False)
            rows.append(row)
        counts=dict(Counter(r['status']for r in rows))
        if key=='invariant':assert counts=={'PASS':74,'INCOMPLETE':8};invariant_count=counts
        if key=='id':assert counts=={'PASS':20}
        if key=='scenario':assert counts=={'PASS':22,'INCOMPLETE':7}
        body=dict(candidate_sha=CANDIDATE,state='FINAL_R5_RETEST_WITH_EXPLICIT_RETAINED_SCOPE',audit_complete=False,denominator=len(rows),status_counts=counts,
                  retained_source=dict(seal=SEAL,candidate=BASE,path='audit/sol_cp17_r4/'+name,sha256=sha256((prior/name).read_bytes()).hexdigest(),runtime_credit_r5=0),
                  method='Current witness IDs navigate independently captured r5 rows; old scope is retained explicitly. Source impact, runtime row details and body fingerprints are reviewed separately. Counts are not ERP progress percentages.',all20_one_browser_chain_proven=False,rows=rows)
        write(name,body)
        title={'invariant':'Invarian','scenario':'Skenario','id':'Sambungan'}[key]
        text='# '+title+' Sol r5\n\nStatus mencakup lingkup r4 yang dipertahankan dan bukti r5 yang disebut. Bukti lama tidak dihitung sebagai eksekusi baru.\n\n|ID|Status|Lingkup|\n|---|---|---|\n'
        for row in rows:text+='|'+str(row[key])+'|'+row['status']+'|'+row['current_scope'].replace('|','/').replace('\n',' ')+'|\n'
        (ROOT/name.replace('.json','.md')).write_text(text)
    old=json.loads((prior/'FUNCTION_DETAIL.json').read_text());functions=[]
    for prior_row in old['rows']:
        row=copy.deepcopy(prior_row);row['retained_r4_seal']=SEAL;row['retained_r4_runtime_credit_r5']=0;row['retained_r4_status']=row['status'];row['r5_current_witnesses_by_dimension']={}
        for dimension in ('positive','refusal','correction_or_revision','downstream'):
            w=row.get(dimension,{});row['r5_current_witnesses_by_dimension'][dimension]=witness(w.get('case_id'))
        row['r5_source_scope']='src/supabase unchanged since r4; only declared additive reader/checker changes. Per-function current witness scope remains finite.'
        if row['id'] in ('FUN-039','FUN-041'):
            row['status']='LIFECYCLE_SCOPED_AND_REPAIR_INTEGRITY_RETEST_PASS'
            row['retained_r4_integrity_counterexample']=row.pop('integrity_counterexample',None)
            row['integrity_finding']='SOL-R4-001_CLOSED_BY_R5'
            row['integrity_retest_witnesses']=witness('SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM')+witness('SOL_R5_VALID_REPAIR_REVERSED_AND_REALLOCATED_ZERO_ALARM')
            row['scope_limit']='Original valid repair Nota6000 all167zero, wrong/missing+1, REVERSED/reallocation zero, and F03P12 lifecycle pass. Other historical scope limits retained; no universal payment/period-close UI claim.'
        functions.append(row)
    write('FUNCTION_DETAIL.json',dict(candidate_sha=CANDIDATE,state='DEFINED_NEEDS_WITH_CURRENT_AND_RETAINED_DIMENSIONS',defined_function_rows=len(functions),screen_rows=len(old['screens']),
          retained_source=dict(seal=SEAL,sha256=sha256((prior/'FUNCTION_DETAIL.json').read_bytes()).hexdigest(),runtime_credit_r5=0),method='57 defined needs and47 screens are denominators of an inventory, not a completed-feature count. Current witnesses are attached only when actually captured.',rows=functions,screens=old['screens']))
    old=json.loads((prior/'OPEN_BOUNDARIES.json').read_text());gaps=copy.deepcopy(old['scope_gaps'])
    inv=json.loads((ROOT/'INVARIANT_MATRIX.json').read_text());d01=next(r for r in inv['rows']if r['invariant']=='INV-D01')
    scenario=json.loads((ROOT/'SCENARIO_MATRIX.json').read_text())
    skn19=next(r for r in scenario['rows']if r['scenario']=='SKN-19')
    for gap in gaps:
        if gap['id']=='SKN-19':
            gap['evidence_scope']=skn19['current_scope'];gap['next_action']=skn19['next_action']
    gaps.append(dict(id='INV-D01',family='INVARIANT',status='INCOMPLETE',requirement=d01['requirement'],evidence_scope=d01['current_scope'],next_action=d01['next_action'],proved_product_bug=False,evidence='DETECTOR_DISPOSITIONS.json'))
    write('OPEN_BOUNDARIES.json',dict(report_state='FINAL_EXPLICIT_R5_SCOPE_BOUNDARIES',candidate_sha=CANDIDATE,feature_complete=False,audit_complete=False,production_go=False,
          retained_r4_seal=SEAL,retained_boundaries_runtime_credit_r5=0,scope_gaps=gaps,extra_limits=old['extra_limits'],known_operating_boundaries=old['known_operating_boundaries'],
          current_operating_retest='K3 replacement still receives restore write before mismatch; patch deferred CP7C. P21 used/new-copy restore verified; post-use uninstall is not exact data restore.',
          production_gate='CP6 accepted closure remains distinct from CP7 completeness, full audit and production approval. Real hosted preflight/cutover/shadow and missing sensitivity/access scope remain open.',
          peer_round_read=False,limits='This is what Sol did not close. Without peer r5 reports, Sol does not claim which items nobody else tested.'))
    print(json.dumps(dict(invariants=invariant_count,scenarios=dict(PASS=22,INCOMPLETE=7),chains=dict(PASS=20),defined_needs=57,screens=47,current_exact_detector_controls=11,ever_qualified=22,never_qualified=145)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior-root',required=True);a=p.parse_args();main(a.prior_root)
