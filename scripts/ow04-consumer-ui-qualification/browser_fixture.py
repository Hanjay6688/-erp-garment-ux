"""Fixed Native setup/read-back operations on the browser copy only."""
from datetime import date,datetime,timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import json
import os
import sys
import uuid

operation=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/ow04-consumer-qualification'),str(REPO/'scripts/ow04-qualification'),str(REPO/'scripts/cp7_customer_credit/consumer')]
import consumer_transport_probe  # Closed owning-import flags only; no DB on import.
import workspace_http_cases as cases
import psycopg

business,native=cases.business,cases.native
OUT=REPO/'cp6-proof/t3/consumer-browser-fixtures'


class Adapter:
    def __init__(self,target):self.target=target
    def connect(self):return psycopg.connect(self.target)


def encoded(v):
    if isinstance(v,dict):return {'t':'dict','v':[[encoded(k),encoded(x)]for k,x in v.items()]}
    if isinstance(v,(set,tuple,list)):return {'t':type(v).__name__,'v':[encoded(x)for x in v]}
    if isinstance(v,(uuid.UUID,Decimal,datetime,date)):return {'t':type(v).__name__,'v':str(v)}
    assert v is None or isinstance(v,(str,int,float,bool)),type(v)
    return v


def decoded(v):
    if not isinstance(v,dict):return v
    assert set(v)=={'t','v'}
    kind,value=v['t'],v['v']
    if kind=='dict':return {decoded(k):decoded(x)for k,x in value}
    if kind in('set','tuple','list'):return {'set':set,'tuple':tuple,'list':list}[kind](decoded(x)for x in value)
    assert kind in('UUID','Decimal','datetime','date')
    return {'UUID':uuid.UUID,'Decimal':Decimal,'datetime':datetime.fromisoformat,'date':date.fromisoformat}[kind](value)


def load(key,want):
    assert str(uuid.UUID(key))==key
    raw=(OUT/(key+'.json')).read_bytes();assert sha256(raw).hexdigest()==want
    return decoded(json.loads(raw))


def invariant(cur,pair):
    return {str(sale):cur.execute('select cp7_credit.consumer_native_invariant_v1(%s)',(sale,)).fetchone()[0]
            for sale in(pair['source']['f']['sale'],pair['target']['sale'])}


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser'
    assert operation in('prepare','verify','snapshot','revoke','restore')
    p=json.loads(sys.stdin.read());http=Adapter(target);gold=cases.expected()
    if operation=='prepare':
        action=p['action'];assert action in('APPLY','REFUND','UNDO')
        today=date.fromisoformat(p['today']);mode='REFUND'if action=='UNDO'else'CREDIT'
        with http.connect()as conn,conn.cursor()as cur:
            assert cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]==today
            conn.rollback()
        pair=business.prepared(http,today,mode)
        original=pair['initial_result'].get('refund_event_id')if action=='UNDO'else None
        prospective=business.payload(pair,action,original=original)
        # NEW operator input for the browser, after the actual source instant.
        # Existing economic/book days and all original financial gold stay fixed.
        at=datetime.fromisoformat(prospective['physical_at'])+timedelta(milliseconds=1)
        at=at.replace(microsecond=(at.microsecond//1000)*1000).astimezone(ZoneInfo('Asia/Jakarta'))
        local=at.isoformat(timespec='milliseconds')[:23]
        prospective['physical_at']=at.isoformat(timespec='milliseconds')
        with http.connect()as conn,conn.cursor()as cur:
            native.b.api.admin(cur)
            source=cur.execute('select sale_number from erp.sales_headers where id=%s',(pair['source']['f']['sale'],)).fetchone()[0]
            saved=dict(pair=pair,action=action,native_before=invariant(cur,pair),prospective_payload=prospective)
            conn.rollback()
        key=str(uuid.uuid4());OUT.mkdir(parents=True,exist_ok=True);raw=json.dumps(encoded(saved),separators=(',',':')).encode()
        with(OUT/(key+'.json')).open('xb')as stream:stream.write(raw)
        bank=cases.bank(http,pair)
        out=dict(fixture=key,fixture_sha256=sha256(raw).hexdigest(),action=action,source_id=str(pair['source']['f']['sale']),
                 source_number=source,target_id=str(pair['target']['sale']),target_number=cases.target_number(http,pair),
                 cohort_id=str(pair['initial_result']['credit_id']),original_event_id=str(original)if original is not None else None,
                 bank_id=bank[0],bank_code=bank[1],bank_name=bank[2],physical_local=local,prospective_payload=prospective,
                 sku=pair['source']['f']['sku'])
    elif operation=='snapshot':out=business.snapshot(http)
    elif operation in('revoke','restore'):
        actor=uuid.UUID(p['auth_user_id'])
        with http.connect()as conn,conn.cursor()as cur:
            cur.execute("update erp.app_users set is_active=%s where auth_user_id=%s and full_name like 'Auditor browser ow04-consumer-%%'",
                        (operation=='restore',actor));assert cur.rowcount==1;conn.commit()
        out=dict(status='COMMITTED',active=operation=='restore')
    else:
        saved=load(p['fixture'],p['fixture_sha256']);pair=saved['pair'];args=p['args'];result=p['outcome'];review=p['review'];input=p['review_input']
        action=saved['action'];assert args['p_payload']=={**input,'quote_sha256':review['quote_sha256']}
        assert input==saved['prospective_payload'],'BROWSER_EXPLICIT_OPERATOR_INPUT_DIFFERS_FROM_DECLARED_FIXTURE'
        assert args['p_expected_versions']==review['expected_versions']
        assert review['selection']['source_sale_id']==str(pair['source']['f']['sale'])
        assert review['selection']['action']==action and result['action']==action
        expected=gold['after_apply80']if action=='APPLY'else gold['after_refund80']if action=='REFUND'else gold['after_named_full_undo']
        with http.connect()as conn,conn.cursor()as cur:
            native.b.api.admin(cur);request=uuid.UUID(args['p_request']);actor=uuid.UUID(p['actor'])
            row=cur.execute('select action,payload,expected_versions,response from cp7_credit.consumer_requests_v1 where actor=%s and request_id=%s',
                            (actor,request)).fetchone()
            assert row==(action,args['p_payload'],args['p_expected_versions'],result)
            assert cur.execute('select actor,request_id from cp7_credit.consumer_operations_v1 where id=%s',(result['operation_id'],)).fetchone()==(actor,request)
            assert cur.execute('select count(*)from cp7_credit.consumer_operations_v1 where actor=%s and request_id=%s',(actor,request)).fetchone()==(1,)
            assert cur.execute('select response from cp7_credit.consumer_completions_v1 where operation_id=%s',(result['operation_id'],)).fetchone()==(result,)
            cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(result['operation_id'],))
            assert invariant(cur,pair)==saved['native_before'],'BROWSER_CONSUMER_CHANGED_NATIVE_STOCK_HPP_OR_ORIGINAL_PAYMENT'
            assert native.payment_snapshot(cur,pair['source']['f']['payment'])==pair['source']['payment_before']
            assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone()==(0,)
            conn.rollback()
        actual=business.profiles(http,pair);assert actual==expected,(actual,expected)
        day=str(datetime.fromisoformat(input['physical_at']).astimezone(ZoneInfo('Asia/Jakarta')).date())
        assert result['economic_date']==result['transaction_date']==day
        out=dict(status='PASS',actual_Auth_actor_proven=True,one_committed_request_operation_event_and_journal=True,
                 Native_stock_HPP_original_payments_unchanged=True,original_target_payment_rows=0,
                 expected=expected,observed=actual,exact_open_economic_book_pair=day,production_go=False)
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
