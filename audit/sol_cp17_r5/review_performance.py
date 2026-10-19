"""Separate measured latency/capacity from the raw scale-suite PASS label."""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    copies=sorted((ROOT/'ci_receipts/sol_artifacts').glob('*/files/CP7_P19_SCALE.json'))
    assert copies,'P19_SCALE_ARTIFACT_NOT_COLLECTED'
    raw=copies[0].read_bytes();assert all(p.read_bytes()==raw for p in copies)
    r=json.loads(raw);source=dict(artifact_id=int(copies[0].parts[-3]),path=str(copies[0].relative_to(ROOT)),sha256=sha256(raw).hexdigest(),bytes=len(raw))
    groups={g:r[g]['cases'] for g in ('native','browser')}
    assert len(groups['native'])==1 and len(groups['browser'])==4
    counts=dict(Counter(c['status'] for g in groups.values()for c in g.values()))
    rows=[];profile=[]
    for ident,c in groups['browser'].items():
        assert c['size'] in (100,300,1000,5000)
        for m in c.get('measurements',[]):
            ms=m.get('click_to_complete_ms');assert isinstance(ms,(int,float)) and math.isfinite(ms) and ms>=0
            rows.append(dict(case_id=ident,measurement_id='P19S_BROWSER_'+str(c['size'])+'_'+str(m['history_days'])+'_'+m['control'],
                             size=c['size'],history_days=m['history_days'],control=m['control'],ui_status=m['ui_status'],elapsed_ms=ms,
                             target_ms=3000,meets_3s=ms<=3000,first_visible_ms=m.get('click_to_first_status_ms'),
                             progress_ms=m.get('click_to_segment_progress_ms'),computing_since_ms=m.get('click_to_computing_since_ms'),owner_budgets=m.get('owner_budgets'),staged=m.get('staged'),completed_open=m.get('completed_open'),
                             verdict=m['verdict'],refusal=m.get('refusal'),refusal_code=m.get('refusal_code'),refusal_sqlstate=m.get('refusal_sqlstate'),
                             original_sha256=m.get('original_sha256'),original_utf8_bytes=m.get('original_utf8_bytes'),witness=m.get('witness'),
                             product_caps_unchanged=not c.get('limits_raised'),data_not_sampled_or_truncated=not c.get('data_sampled_or_truncated'),
                             named_exception=m.get('owner_budgets',{}).get('owner_named_background_exception')))
        diagnosis=(c.get('sql_ladder') or {}).get('capture_diagnosis')
        if diagnosis:profile.append(dict(size=c['size'],diagnosis=diagnosis,application_latency=False))
    finance100=[m for m in rows if m['size']==100 and m['control']=='CAPTURE_WITH_FINANCE']
    assert len(finance100)==3 and {m['history_days']for m in finance100}=={1,30,100}
    direct300=[m for m in rows if m['size']==300 and m['control'].startswith('CAPTURE')]
    staged5000=[m for m in rows if m['size']==5000 and m['control'].startswith('STAGED')]
    complete_staged=[m for m in staged5000 if m['ui_status']=='RESULT_RENDERED']
    violations=[m for m in rows if m['control'].startswith('CAPTURE') and not m['meets_3s']]
    result=dict(state='FINAL_BOUNDED_INDEPENDENT_SCALE_LATENCY_REVIEW',candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',run_id=39237719026,job_id=118010759185,source=source,
                evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='OWNER_RECORDED_3000MS_BOUND_PLUS_WRITER_MEASUREMENT_CONTRACT_EXECUTED_BY_SOL',
                raw_report_status=r['status'],raw_case_status_counts=counts,raw_declared_cases=5,
                finite_direct_finance_100=finance100,direct_300=direct300,staged_5000=staged5000,
                direct_latency_violations=violations,direct_latency_target_reached_for_all_measured_points=not violations,
                known_S2_remains_open=bool(violations),all_measurements=rows,
                diagnostic_function_profiles=profile,
                assertions=dict(source_model_consistency_all_sizes=all(c.get('source_model_consistent')is True for c in groups['browser'].values()),
                                all_product_caps_unchanged=all(m['product_caps_unchanged']for m in rows),
                                all_data_not_sampled_or_truncated=all(m['data_not_sampled_or_truncated']for m in rows),
                                scale5_status_is_not_latency_acceptance=True),
                named_staged_exception_completed_samples=len(complete_staged),
                full_P19_acceptance=False,factory_capacity_or_SLA=False,owner_latency_acceptance=False,production_go=False,
                limits=['CI loopback measurements on synthetic Native writer fixtures, not factory/network/physical-phone SLA.',
                        'An honest refusal is not successful capacity; a named staged/background exception does not make the whole computation3s.',
                        'A phase profile and capture function diagnostic are not browser application latency.',
                        'Separate r4/r5 runs use the same declared runner class and workload; they are not a paired same-VM causal benchmark.',
                        'Warm/generic plans and every possible mapping/state permutation are not universally certified by the finite reader controls.'])
    (ROOT/'PERFORMANCE_RESULT_REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(raw_report_status=r['status'],raw_case_counts=counts,finance100=[dict(days=m['history_days'],ms=m['elapsed_ms'],meets=m['meets_3s'],ui_status=m['ui_status'])for m in finance100],direct300=[dict(days=m['history_days'],control=m['control'],ms=m['elapsed_ms'],ui_status=m['ui_status'],refusal=m['refusal_code'])for m in direct300],staged5000_complete=len(complete_staged),known_S2_open=bool(violations)),ensure_ascii=False))


if __name__=='__main__':main()
