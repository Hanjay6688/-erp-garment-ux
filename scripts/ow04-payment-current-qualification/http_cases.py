"""Actual Auth retained16 and positive existing-cohort corrections2."""
from copy import deepcopy
from pathlib import Path
import importlib.util,json,uuid
import cp7_payment_correction_cases as payment
import consumer_http_cases as credit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('current_retained_payment_http16',ROOT/'ow04-payment-http-bound-qualification/http_cases.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
NEW_IDS=('OW04_CURRENT_HTTP_APPLY100_RESTORE1000_REPLAY_REVOKE',
         'OW04_CURRENT_HTTP_REFUND100_RESTORE1000_REPLAY_REVOKE')
IDS=old.IDS+NEW_IDS
assert len(IDS)==len(set(IDS))==18
PHYSICAL=('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements','inventory_balances',
 'opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events','nonpo_hpp_events','hpp_journals','hpp_balances')


def compact(http,pair):
    a=credit.profiles(http,pair);s,t=a['source'],a['target']
    return dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
        source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=a['cash'])


def positive(http,today,index):
    action=('APPLY','REFUND')[index]
    gold=json.loads((ROOT/'ow04-payment-positive-qualification/EXPECTED.json').read_bytes())['cases'][1 if index==0 else 3]
    user=http.login('OWNER',label='current-positive-'+action.lower());pair=credit.prepared(http,today)
    first,first_args=credit.committed(http,user,credit.quoted(http,user,credit.payload(pair,action,'80.00')))
    down=old.correction_review(http,user,pair);lowered=credit.response(user.rpc(old.COMMAND,deepcopy(down)))
    second,_=credit.committed(http,user,credit.quoted(http,user,credit.payload(pair,action,'20.00')))
    before=credit.snapshot(http)
    w=credit.response(user.rpc(old.READ,dict(p_query=dict(sale_id=down['p_payload']['sale_id'],payment_id=lowered['payment_id']))))
    assert credit.snapshot(http)==before
    assert w['contract_version']=='cp7.sales-payment-correction-workspace.v2'
    assert w['replacement_capacity']==dict(maximum_amount='1000.00',basis='EXISTING_RETURN_COHORT',
        source_sale_id=down['p_payload']['sale_id'],payment_id=lowered['payment_id'],row_version=w['row_version'])
    d=w['document'];up=dict(p_payload=dict(sale_id=w['sale_id'],payment_id=d['id'],review_token=w['review_token'],
        change_reason='Pembayaran sumber dipulihkan setelah saldo dan riwayat diperiksa',
        replacement=dict(payment_number=d['number'],payment_date=d['physical_at'],amount='1000.00',
            cash_account_id=d['cash_account_id'],payment_method=d['method'],reference_number=d['reference'],notes=d['notes'])),
        p_expected=w['row_version'],p_request=str(uuid.uuid4()))
    with http.connect()as conn,conn.cursor()as cur:
        credit.native.b.api.admin(cur)
        p0=payment.payment_fact(cur,pair['source']['f']['payment']);p9=payment.payment_fact(cur,lowered['payment_id'])
        physical=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(pair['source']['f']['sale'],)).fetchone()[0]
        journals={e['journal_id']:credit.native.journal(cur,e['journal_id'])for e in(first,second)}
        conn.rollback()
    result=credit.response(user.rpc(old.COMMAND,deepcopy(up)))
    assert result['original_payment_id']==lowered['payment_id']and result['request_id']==up['p_request']
    assert compact(http,pair)==gold['after_restore']
    with http.connect()as conn,conn.cursor()as cur:
        credit.native.b.api.admin(cur)
        assert payment.payment_fact(cur,pair['source']['f']['payment'])==p0
        assert payment.payment_fact(cur,lowered['payment_id'])==p9
        now=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(pair['source']['f']['sale'],)).fetchone()[0]
        assert {k:now[k]for k in PHYSICAL}=={k:physical[k]for k in PHYSICAL}
        for ident,journal in journals.items():assert credit.native.journal(cur,ident)==journal
        assert cur.execute('select payload,expected_version,response from cp7_payment_correction.requests where actor=%s and request_id=%s',
            (user.auth_user_id,up['p_request'])).fetchone()==(up['p_payload'],up['p_expected'],result)
        op=cur.execute("select operation_id from cp7_credit.source_operation_materializations_v1 where actor=%s and request_id=%s and action='PAYMENT_CORRECT'",(user.auth_user_id,up['p_request'])).fetchone()[0]
        cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(op,));conn.rollback()
    before=credit.snapshot(http)
    assert credit.response(user.rpc(old.COMMAND,deepcopy(up)))==result
    assert credit.response(user.rpc(old.COMMAND,deepcopy(down)))==lowered
    credit.replay(http,user,first_args,first)
    assert credit.snapshot(http)==before
    changed=deepcopy(up);changed['p_payload']['replacement']['amount']='999.99'
    old.refused_unchanged(http,user,changed,'CP7_SALES_REQUEST_CHANGED')
    stale=deepcopy(up);stale['p_request']=str(uuid.uuid4())
    old.refused_unchanged(http,user,stale,'CP7_SALES_REVIEW_CHANGED')
    for name,args in((old.READ,dict(p_query=dict(sale_id=w['sale_id'],payment_id=result['payment_id']))),(old.COMMAND,up)):
        assert http.anon_rpc(name,deepcopy(args))['status']in(401,403)
    assert credit.snapshot(http)==before
    with http.connect()as conn,conn.cursor()as cur:
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
    try:
        old.refused_unchanged(http,user,up,'CP7_SALES_ACCESS_DENIED',403)
        old.refused_unchanged(http,user,stale,'CP7_SALES_ACCESS_DENIED',403)
    finally:
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(user.auth_user_id,));assert cur.rowcount==1;conn.commit()
    before=credit.snapshot(http)
    assert credit.response(user.rpc(old.COMMAND,deepcopy(up)))==result
    assert credit.snapshot(http)==before
    return dict(status='PASS',actual_Auth_and_PostgREST=True,all_credit_and_correction_writes_from_real_Auth=True,
        actual_actor_request_and_closed_source_operation=True,source_bound_v2_capacity=True,
        exact_old_and_current_replay_zero_effects=True,changed_UUID_and_stale_rejected=True,
        anon_and_actual_revoked_member_fresh_and_replay_denied=True,original_P1000_P900_C_journals_stock_HPP_retained=True,
        expected=gold['after_restore'],observed=compact(http,pair),production_go=False)


def http_cases(http,today):
    return old.http_cases(http,today)+[(key,lambda index=index:positive(http,today,index))for index,key in enumerate(NEW_IDS)]
