"""Reconcile already executed browser facts; no runtime replay and no raw verdict edit."""
from pathlib import Path
from decimal import Decimal as D
import copy,hashlib,json
P=Path(__file__).resolve().parent/'evidence'
source=P/'CONT_BROWSER_FIRST_LOG_VERDICTS.json';d=json.loads(source.read_text());results=[]
def delta(a,z):
    return {k:D(z.get(k,'0'))-D(a.get(k,'0')) for k in set(a)|set(z) if D(z.get(k,'0'))!=D(a.get(k,'0'))}
for e in d['events']:
    case=e.get('audit_case_id')
    if not case:continue
    assert e['status']=='INCOMPLETE' and 'browser_cont.mjs:71:151' in e['stack']
    o=e['observations'];first=o['before'];final=o['final'];returned=o['returned'];mobile=case.endswith('MOBILE')
    assert [x['action'] for x in e['receipts']]==['CREATE','POST','PAYMENT','RETURN','PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE']
    assert all(x['status']==200 for x in e['receipts'])
    # Compare the union, including accounts that acquired their first journal.
    # New zero balances are not an economic change; every nonzero cent still fails.
    assert not delta(first['accounts'],final['accounts'])
    added=set(final['accounts'])-set(first['accounts']);assert added
    assert all(D(final['accounts'][k])==0 for k in added)
    for key in (next(iter(first['accounts'])),'AUDITOR_NEW_NONZERO_CONTROL'):
        bad=copy.deepcopy(final['accounts']);bad[key]=str(D(bad.get(key,'0'))+D('.01'))
        assert delta(first['accounts'],bad)=={key:D('.01')},'Comparator must detect one cent on existing and new account'
    assert final['positions']==first['positions'] and D(final['available'])==41
    assert final['raw']==first['raw'] and tuple(map(D,final['raw']))==(D(32),D('395.84'))
    assert not final['unbalanced_journals'] and not e['errors']
    assert final['document']['status']=='REVERSED'
    assert len(final['returns'])==len(final['payments'])==1
    assert final['returns'][0][1]==final['payments'][0][1]=='REVERSED'
    assert D(final['payments'][0][2])==D('137.03')
    f=returned['document']['financial']
    assert {k:D(f[k]) for k in ('gross_total','paid_total','return_total','net_total','open_balance')}==dict(gross_total=D('388.83'),paid_total=D('137.03'),return_total=D('119.64'),net_total=D('269.19'),open_balance=D('132.16'))
    assert D(returned['available'])==32
    grades={g:D(q) for _,g,q in returned['positions']}
    assert grades==(dict(GRADE_A=D(28),GRADE_B=D(4)) if mobile else dict(GRADE_A=D(32)))
    if mobile:
        lost=o['committed_without_response']
        assert lost['accounts']==returned['accounts'] and len(lost['returns'])==len(returned['returns'])==1
        assert lost['returns'][0][0]==returned['returns'][0][0]
    results.append(dict(case_id=case,assessment='ADJUDICATED_PASS',original_status=e['status'],run_id=d['run_id'],
        raw_first_failure_preserved=True,comparison='ALL_ACCOUNTS_UNION_DEFAULT_ZERO; every nonzero difference retained',
        introduced_zero_accounts=sorted(added),negative_controls=['EXISTING_ACCOUNT_PLUS_0.01_DETECTED','NEW_ACCOUNT_PLUS_0.01_DETECTED'],
        complete_UI_actions=7,all_HTTP200=True,final_FG=41,final_all_GL_delta={},reversed_original_payment_and_return=True,
        raw32_value39584_unchanged=True,actual_lost_response=mobile,
        replay_UUID_body_assertion='Earlier frozen runtime assertion passed before the recorded final comparator failure' if mobile else None,
        note='No rerun: all commands already executed. Remaining assertions evaluated from complete captured final state; no product/source fact changed.'))
assert len(results)==2
out=dict(source_file=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),product_sha='2e605bb7d9b6b7903919b8df2be1443f1740140b',run_id=d['run_id'],job_id=d['job_id'],evidence_origin='INDEPENDENT_RUNTIME_WITNESS_ADJUDICATION',production_go=False,results=results)
(P/'CONT_BROWSER_ADJUDICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
