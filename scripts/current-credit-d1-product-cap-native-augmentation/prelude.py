"""Prepared actual Native preludes. Executed only by root's existing strict group.

No server is opened here. Masters/period are labelled administrative fixtures;
stock, sale, payment, settlement and correction effects use retained APIs.
"""
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('d1_cap_native_prelude_guard',HERE/'guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
CAP='REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP'


def dependencies(business,api):
    import cp7_ow04_restore_bundle as catalog
    n=business.native;initial=business.fixture.retained.signed.initial
    values=dict(retained=business,native=n,initial=initial,note=n.note,drafts=n.note.drafts,
                command=n.cmd,payments=n.payments,returns=n.returns,correction=business.correction,catalog=catalog,
                financial_truth=n.b)
    for key,module in values.items():guard.module(module,key,api)
    return SimpleNamespace(**values)


@contextmanager
def utc(cur,d):
    d.native.b.api.admin(cur);old=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local timezone='UTC'")
    try:yield
    finally:cur.execute("select set_config('TimeZone',%s,true)",(old,))


def capture(cur,d,label):
    with utc(cur,d):
        catalog=d.catalog._catalog_rows(cur);data=d.catalog._data(cur)
        assert len(catalog)==22
        rows={}
        with d.catalog._catalog(cur):
            names=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                "where c.relkind in('r','p','m')and "+d.catalog.NAMESPACE+' order by 1,2').fetchall()
            for schema,table in names:
                key=schema+'.'+table
                quoted='"'+schema.replace('"','""')+'"."'+table.replace('"','""')+'"'
                raw=d.native._array(cur,quoted,'true',())
                assert len(raw['document'])==data[key][0] and raw['sha256']==data[key][1],key
                rows[key]=raw
        assert set(rows)=={k for k in data if not k.startswith('sequence:')}
        identity=cur.execute("select current_user::text,session_user::text,current_setting('request.jwt.claims',true)").fetchone()
        locks=cur.execute("select classid::text,objid::text,objsubid,mode,granted from pg_locks where locktype='advisory'and pid=pg_backend_pid()order by 1,2,3,4").fetchall()
        value=dict(catalog=catalog,data_and_sequences=data,all_rows=rows,identity=identity,advisory_locks=locks)
    path=ROOT/'cp6-proof/t3'/('D1_PRODUCT_CAP_'+label+'_'+uuid.uuid4().hex+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,indent=2,sort_keys=True,default=str)+'\n').encode();path.write_bytes(raw)
    return value,dict(path=str(path),bytes=len(raw),sha256=sha256(raw).hexdigest(),
        catalog_groups=22,current_tables=len(rows),sequence_keys=sum(k.startswith('sequence:')for k in data),
        complete_raw_rows=True,dropped_catalog_fields=[],dropped_data_keys=[])


def check_rollback(before,after):
    assert after['catalog']==before['catalog'] and after['all_rows']==before['all_rows']
    assert after['identity']==before['identity'] and after['advisory_locks']==before['advisory_locks']
    a,b=before['data_and_sequences'],after['data_and_sequences']
    assert {k:v for k,v in a.items()if not k.startswith('sequence:')}=={k:v for k,v in b.items()if not k.startswith('sequence:')}
    # Native positive operations legitimately allocate sequences inside the
    # rolled-back savepoint. Preserve all observed prefix changes, never reseed.
    assert set(a)==set(b)
    return {k:dict(before=a[k],after=b[k])for k in a if a[k]!=b[k]}


def refuse(cur,d,label,operation,message):
    import psycopg
    before,pre=capture(cur,d,label+'_BEFORE')
    point='d1_cap_refusal_'+uuid.uuid4().hex;cur.execute('savepoint '+point)
    try:operation()
    except psycopg.Error as error:
        result=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,
            detail=error.diag.message_detail,hint=error.diag.message_hint,context=error.diag.context)
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point)
        d.native.b.api.admin(cur)
    else:
        cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point)
        raise AssertionError('D1_CAP_NATIVE_EXPECTED_REFUSAL_SUCCEEDED')
    after,post=capture(cur,d,label+'_AFTER')
    assert result['sqlstate']=='P0001'and result['message']==message,result
    assert after==before,'D1_CAP_NATIVE_REFUSAL_CHANGED_FULL_CATALOG_ROWS_SEQUENCES_OR_SESSION'
    return dict(actual_refusal=result,before=pre,after=post,all22_all_rows_all_sequences_and_session_unchanged=True)


def require_abi(cur,d,source):
    d.native.b.api.admin(cur);d.initial._require_installed(cur)
    for signature in (
        'public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)',
        'public.erp_cp7_get_sales_returns_v1(jsonb)',
        'public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb)',
        'public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)',
        'public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)',
        'public.erp_cp7_get_sales_return_correction_v1(jsonb)'):
        assert cur.execute('select to_regprocedure(%s)is not null',(signature,)).fetchone()==(True,),signature
    body=cur.execute("select prosrc from pg_proc where oid='cp7_credit_correction_de.quote_v1(jsonb)'::regprocedure").fetchone()[0]
    assert sha256(body.encode()).hexdigest()==source['required_quote_body_sha256'],'D1_CAP_NATIVE_INSTALLED_QUOTE_BODY_REQUIRED'


def setup(cur,today,d):
    n=d.native;n.b.api.admin(cur);dates,at=n._calendar(cur)
    n.source.fg.ax.boundary.historical.prior.set_open_period(cur,dates['D-2'])
    a=d.note.stock(cur,today,10,at['stock']);b=d.note.stock(cur,today,1,at['stock'])
    assert a['product']!=b['product']and a['location']==b['location']
    a['sale_at']=at['sale'].isoformat()
    p=d.drafts.payload(a,'5','200');p['items']+=d.drafts.payload(b,'1','1000')['items']
    made=d.drafts.create(cur,a,p);assert made['sale_id']==a['sale']
    review,version=d.command.review(cur,a);d.command.command(cur,'POST',review,version)
    a['bank']=str(n.source.bc.bank_account(cur,'D1CAP-'+uuid.uuid4().hex[:12]))
    a['destination']=d.returns.location(cur,'D1 product cap actual Native returns')
    rows=d.returns.read(cur,a)['page']['rows']
    alloc_a=guard.allocation(rows,a['product'],5);alloc_b=guard.allocation(rows,b['product'],1)
    assert len(rows)==2
    a['allocations']=[alloc_a]  # New fixture dict only; no shared module/global patch.
    payment,version=d.payments.payment_payload(cur,a,'2000.00');payment['payment_date']=at['payment'].isoformat()
    received=d.command.command(cur,'PAYMENT',payment,version)
    n.b.api.admin(cur)
    assert cur.execute('select amount,status from erp.sales_payments where id=%s',(received['payment_id'],)).fetchone()==(D('2000.00'),'POSTED')
    for f,allocation,qty,net in ((a,alloc_a,5,D('1000')),(b,alloc_b,1,D('1000'))):
        got=cur.execute('select i.sale_id::text,i.product_id::text,i.qty_pcs,i.line_total,a.qty_pcs,a.lot_id::text,a.unit_hpp_snapshot from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where a.id=%s',(allocation['allocation_id'],)).fetchone()
        assert got==(a['sale'],f['product'],qty,net,qty,f['lot'],D('10')),got
    pair=dict(source=dict(f=a),ar=dict(source=d.command.mapping(cur,'AR_CUSTOMER')))
    return dict(a=a,b=b,allocation=alloc_a,at=at,pair=pair,payment_id=received['payment_id'],credits=[])


def settle(cur,d,f,qty,amount,ordinal):
    a=f['a'];p,version=d.returns.payload(cur,a,qty=str(qty),refund=amount,
        allocation=f['allocation']['allocation_id'],destination=a['destination'])
    p['physical_at']=(f['at']['returned']+timedelta(seconds=ordinal-1)).isoformat()
    query=dict(sale_id=a['sale'],expected_version=version,review_token=p['review_token'],
        return_payload={k:p[k]for k in('return_number','physical_at','notes','items','change_reason')},
        settlement=dict(mode=None,credit_account_id=None,cash_account_id=None,refund_physical_at=None,reference=None))
    first=d.native.call_quote(cur,query)
    assert first['readiness']['state']=='CHOICE_REQUIRED'and first['current_credit_amount']==amount,first
    credit=d.initial._credit_master(cur);query['settlement'].update(mode='CREDIT',credit_account_id=credit['id'])
    quote=d.native.call_quote(cur,query)
    assert quote['readiness']==dict(state='READY',issues=[])and quote['current_credit_amount']==amount,quote
    envelope=d.initial._envelope(query,quote);key=uuid.uuid4();result=d.initial._settle(cur,envelope,key)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred');d.native.b.api.admin(cur)
    assert(result['kind'],result['action'],result['return_status'],result['family_ordinal'])==('COMMITTED_OUTCOME','RETURN_SETTLEMENT','POSTED',str(ordinal)),result
    assert not result['refund_event_id']
    line=cur.execute('select product_id::text,lot_id::text,location_id::text,qty_pcs,refund_amount,unit_hpp_snapshot from erp.sales_return_items where return_id=%s',(result['return_id'],)).fetchall()
    assert line==[(a['product'],a['lot'],a['destination'],qty,D(amount),D('10'))],line
    f['credits'].append(credit['id'])
    return dict(query=query,quote=quote,envelope=envelope,request_id=str(key),outcome=result)


def financial(cur,d,f,issued,per_family):
    out=d.retained.profile(cur,f['pair'],issued,issued);n=d.native;n.b.api.admin(cur)
    actual=cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s and customer_id=%s',(f['pair']['ar']['source'],f['a']['customer'])).fetchone()[0]
    assert actual==0,actual
    for account,amount in zip(f['credits'],per_family):
        value=cur.execute('select coalesce(sum(credit-debit),0)from erp.journal_lines where account_id=%s and customer_id=%s',(account,f['a']['customer'])).fetchone()[0]
        assert value==D(amount),(value,amount)
    targets={}
    for x in(f['a'],f['b']):
        target=cur.execute('select *from erp.compute_non_po_product_hpp_targets_v2620f(%s)',(x['product'],)).fetchone()
        book=cur.execute('select *from erp.compute_non_po_product_hpp_book_v2620f(%s)',(x['product'],)).fetchone()
        assert target==book,(target,book);targets[x['product']]=[str(v)for v in target]
    return dict(source=out,all_unique_customer_AR_lines='0.00',per_credit_liability=[str(x)for x in per_family],Native_HPP_targets_books=targets)


def invariants(cur,d,f,return_ids):
    n=d.native;n.b.api.admin(cur)
    ids=[f['a']['lot'],f['b']['lot']]
    return dict(sale=d.note.unchanged_facts(cur,f['a']['sale']),
        allocations=n._raw(cur,"select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s",(f['a']['sale'],)),
        original_HPP=n._array(cur,'erp.hpp_versions','lot_id=any(%s::uuid[])',(ids,)),
        payments=n._array(cur,'erp.sales_payments','sale_id=%s',(f['a']['sale'],)),
        payment_facts=n._array(cur,'erp.sales_payment_posting_facts','payment_id=%s',(f['payment_id'],)),
        returns={r:d.correction.original_fact(cur,r)for r in return_ids},
        journals={r:n._raw(cur,"select coalesce(jsonb_agg(cp7_credit.materialized_journal_payload(j.id)order by j.id),'[]')from erp.journal_entries j where j.source_type='SALES_RETURN'and j.source_id=%s and j.reversal_of_id is null",(r,))for r in return_ids})


def quantities(cur,d,f):
    result={}
    for x,total in ((f['a'],10),(f['b'],0)):
        rows=d.returns.positions(cur,x)
        assert sum(rows.values())==total,(rows,total)
        result[x['product']]=[dict(location=location,grade=grade,qty=qty)for(location,grade),qty in sorted(rows.items())]
    return result


def intent(cur,d,f,return_id,amount):
    w=d.correction.workspace(cur,f['a'],return_id)
    document=w['document'];lines=[{k:i[k]for k in('allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes')}for i in document['items']]
    assert len(lines)==1 and lines[0]['allocation_id']==f['allocation']['allocation_id']
    lines[0]['refund_amount']=amount
    p=dict(sale_id=f['a']['sale'],return_id=return_id,review_token=w['source']['review_token'],return_review_token=w['return_review_token'],
        replacement=dict(physical_at=document['physical_at'],notes=document['notes'],items=lines),change_reason='Native product aggregate boundary reviewed')
    q=d.correction.workspace(cur,f['a'],return_id,proposed=dict(replacement=p['replacement'],change_reason=p['change_reason']))['credit_correction']
    p['credit_review_token']=q['review_token'];return p,w['source']['row_version'],q


def post(cur,d,p,version):
    key=uuid.uuid4();out=d.correction.correct(cur,p,version,key)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred');d.native.b.api.admin(cur)
    assert out['kind']=='COMMITTED_OUTCOME'and out['action']=='RETURN_CORRECT'and out['original_return_id']==p['return_id']
    assert out['original_return_status']=='REVERSED'and out['return_status']=='POSTED'
    return out,key


def boundary_prelude(cur,today,d):
    f=setup(cur,today,d);first=settle(cur,d,f,2,'200.00',1);peer=settle(cur,d,f,3,'600.00',2)
    old,other=first['outcome']['return_id'],peer['outcome']['return_id']
    before_profile=financial(cur,d,f,'800.00',['200.00','600.00']);stock=quantities(cur,d,f)
    immutable=invariants(cur,d,f,[old,other]);truth=d.native.b.all_truth(cur)
    peer_before=d.native._array(cur,'erp.sales_returns','id=%s',(other,))
    p,v,q=intent(cur,d,f,old,'400.01');assert q['state']=='REFUSE'and q['issues']==[CAP],q
    refusal=refuse(cur,d,'AGGREGATE_40001',lambda:d.correction.correct(cur,p,v),'CP7_CREDIT_DE_REVIEW_REFUSED')
    p,v,equal=intent(cur,d,f,old,'400.00');assert equal['state']=='READY'and equal['issues']==[],equal
    assert equal['before_available']=='800.00'and equal['after_available']=='1000.00',equal
    out,key=post(cur,d,p,v)
    immutable_after=invariants(cur,d,f,[old,other]);assert immutable_after==immutable
    assert d.native._array(cur,'erp.sales_returns','id=%s',(other,))==peer_before
    assert quantities(cur,d,f)==stock
    after_profile=financial(cur,d,f,'1000.00',['400.00','600.00'])
    truth_after=d.native.b.all_truth(cur);assert d.native.b.truth_quiet(truth,truth_after)
    before,pre=capture(cur,d,'EQUALITY_REPLAY_BEFORE')
    assert d.correction.correct(cur,p,v,key)==out
    after,post_receipt=capture(cur,d,'EQUALITY_REPLAY_AFTER');assert after==before
    return dict(status='PASS',first=first,peer=peer,over_quote=q,actual_refusal=refusal,equality_quote=equal,
        equality_outcome=out,request_id=str(key),before_profile=before_profile,after_profile=after_profile,
        physical=stock,immutable_before=immutable,immutable_after=immutable_after,
        financial_truth_before=truth,financial_truth_after=truth_after,
        immutable_old_source_peer_HPP_payment_history=True,Native_financial_truth_no_new_findings=True,
        exact_replay=dict(before=pre,after=post_receipt,all22_all_rows_all_sequences_and_session_unchanged=True))


def stale_prelude(cur,today,d):
    f=setup(cur,today,d);first=settle(cur,d,f,2,'200.00',1);peer=settle(cur,d,f,3,'600.00',2)
    old,other=first['outcome']['return_id'],peer['outcome']['return_id']
    financial(cur,d,f,'800.00',['200.00','600.00']);stock=quantities(cur,d,f)
    stale_payload,_,stale_quote=intent(cur,d,f,old,'250.00');assert stale_quote['state']=='READY'
    immutable=invariants(cur,d,f,[old,other]);truth=d.native.b.all_truth(cur)
    p,v,q=intent(cur,d,f,other,'600.01');assert q['state']=='READY',q
    peer_out,key=post(cur,d,p,v)
    immutable_after=invariants(cur,d,f,[old,other]);assert immutable_after==immutable and quantities(cur,d,f)==stock
    changed_profile=financial(cur,d,f,'800.01',['200.00','600.01'])
    fresh,version,fresh_quote=intent(cur,d,f,old,'250.00')
    assert fresh_quote['state']=='READY'and fresh_quote['issues']==[]
    assert fresh_quote['review_token']!=stale_quote['review_token']
    assert fresh_quote['before_available']=='800.01'and fresh_quote['after_available']=='850.01'
    fresh['credit_review_token']=stale_payload['credit_review_token']
    stale=refuse(cur,d,'READY_PEER_STALE_INNER',lambda:d.correction.correct(cur,fresh,version),'CP7_CREDIT_DE_STALE_REVIEW')
    p,version,over=intent(cur,d,f,old,'400.00');assert over['state']=='REFUSE'and over['issues']==[CAP],over
    guard_order=refuse(cur,d,'PEER_OVER_PRODUCT_CAP',lambda:d.correction.correct(cur,p,version),'CP7_CREDIT_DE_REVIEW_REFUSED')
    truth_after=d.native.b.all_truth(cur);assert d.native.b.truth_quiet(truth,truth_after)
    return dict(status='PASS',first=first,original_peer=peer,peer_correction=peer_out,peer_correction_request=str(key),
        old_READY_quote=stale_quote,fresh_still_READY_quote=fresh_quote,actual_stale_inner_token=stale,
        fresh_over_cap_quote=over,REFUSE_before_token_guard_order=guard_order,after_peer_profile=changed_profile,
        immutable_before=immutable,immutable_after=immutable_after,financial_truth_before=truth,financial_truth_after=truth_after,
        immutable_old_source_peer_HPP_payment_history=True,physical=stock,Native_financial_truth_no_new_findings=True)


def run(cur,today,business,source,api):
    d=dependencies(business,api);require_abi(cur,d,source)
    results=[]
    for name,operation in (('BOUNDARY_AND_EQUALITY',boundary_prelude),('PEER_READY_INNER_STALE',stale_prelude)):
        before,pre=capture(cur,d,name+'_ISOLATION_BEFORE')
        with d.native.isolated(cur):value=operation(cur,today,d)
        after,post_receipt=capture(cur,d,name+'_ISOLATION_AFTER')
        prefixes=check_rollback(before,after)
        results.append(dict(name=name,actual=value,rows_and_catalog_restored=True,
            before=pre,after=post_receipt,observed_sequence_prefix_changes=prefixes,
            sequence_reset_performed=False,complete_sequence_restore_requires_outer_full_database_backup_restore=True))
    return dict(status='PASS',actual_preludes=results,original13_callback_count_unchanged=True,
        real_Auth_browser_claim=False,outer_full_database_backup_restore_and_all_five_package_gates_required=True,
        production_go=False,independent_acceptance=False)
