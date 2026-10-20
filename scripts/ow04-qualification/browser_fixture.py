"""Fixed operations on cp6_auditor_browser only; no externally chosen SQL/paths."""
from pathlib import Path
from datetime import date,datetime,timezone
from decimal import Decimal
from urllib.parse import urlparse
import hashlib,json,os,sys,uuid
operation=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
import transport_probe as transport
import psycopg
http_cases=transport.http_cases
initial=http_cases.initial
nf=initial.native
OUT=transport.REPO/'cp6-proof/t3/ow04-browser-fixtures'
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
class Adapter:
    def __init__(self,target):self.target=target
    def connect(self):return psycopg.connect(self.target)
def load_fixture(key,expected_sha):
    assert str(uuid.UUID(key))==key
    raw=(OUT/(key+'.json')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected_sha,'OW04_BROWSER_FIXTURE_CHANGED'
    f=decoded(json.loads(raw))
    assert f['gold']in initial.expected()['cases'],'OW04_BROWSER_FROZEN_FINANCIAL_EXPECTED_CHANGED'
    return f
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','OW04_BROWSER_COPY_ONLY'
    assert operation in('prepare','verify','snapshot','revoke','restore'),'OW04_BROWSER_FIXED_OPERATION'
    p=json.loads(sys.stdin.read());adapter=Adapter(target)
    if operation=='prepare':
        mode=p['mode'];assert mode in('CREDIT','REFUND')
        today=date.fromisoformat(p['today'])
        with adapter.connect()as conn,conn.cursor()as cur:
            assert cur.execute("select (statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]==today
            conn.rollback()
        f=http_cases.prepared(adapter,today,paid='1000.00'if mode=='CREDIT'else'900.00',
          profile='OPEN'if mode=='CREDIT'else'REOPENED',mode=mode)
        # These are prospective NEW user inputs, never posted source rewrites.
        physical=datetime.fromisoformat(f['x']['physical']['returned']).replace(hour=10,minute=0,second=0,microsecond=0)
        wire=lambda t:t.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
        f['x']['physical']['returned']=wire(physical);f['x']['return_payload']['physical_at']=wire(physical)
        f['query']['return_payload']['physical_at']=wire(physical)
        if mode=='REFUND':
            f['query']['settlement']['refund_physical_at']=wire(physical.replace(hour=13))
        with adapter.connect()as conn,conn.cursor()as cur:
            nf.b.api.admin(cur);detail=nf.source.read(cur,f['x']['f'])['detail']
            destination=cur.execute('select location_name from erp.locations where id=%s',(f['x']['f']['destination'],)).fetchone()[0]
            # The retained Native stock fixture already reads the real products.sku.
            # product_sku is a public reader alias, not a physical column.
            sku=f['x']['f']['sku']
            conn.rollback()
        key=str(uuid.uuid4());OUT.mkdir(parents=True,exist_ok=True)
        payload=json.dumps(encoded(f),separators=(',',':')).encode()
        with(OUT/(key+'.json')).open('xb')as stream:stream.write(payload)
        out=dict(fixture=key,mode=mode,invoice=detail,query=f['query'],credit=f['master'],
          destination_name=destination,sku=sku,return_local=physical.isoformat()[:16],
          refund_local=physical.replace(hour=13).isoformat()[:16]if mode=='REFUND'else None,
          original_paid=f['gold']['paid'],credit_amount=f['gold']['current_credit_amount'],
          return_pair=[f['x']['dates'][d]for d in f['gold']['return_pair']],
          refund_pair=[f['x']['dates'][d]for d in f['gold']['refund_pair']]if mode=='REFUND'else None,
          serialized_fixture_sha256=hashlib.sha256(payload).hexdigest())
    elif operation=='snapshot':
        out=http_cases.snapshot(adapter)
    elif operation in('revoke','restore'):
        auth=uuid.UUID(p['auth_user_id'])
        with adapter.connect()as conn,conn.cursor()as cur:
            row=cur.execute("update erp.app_users set is_active=%s where auth_user_id=%s and full_name like 'Auditor browser ow04-browser-%%'returning is_active",
              (operation=='restore',auth)).fetchall()
            assert len(row)==1,'OW04_BROWSER_ONLY_ITS_CREATED_AUTH_USER'
            conn.commit()
        out=dict(status='COMMITTED',active=operation=='restore')
    else:
        f=load_fixture(p['fixture'],p['serialized_fixture_sha256']);a=p['args'];q=p['quote'];q_input=p['quote_input'];result=p['outcome']
        assert q_input==f['query'],'OW04_BROWSER_TYPED_INPUT_CHANGED'
        envelope=dict(document=a['p_payload'],expected_version=a['p_expected'])
        request=uuid.UUID(a['p_request'])
        with adapter.connect()as conn,conn.cursor()as cur:
            nf.b.api.admin(cur)
            initial._assert_quote(cur,q,q_input,f['x'],f['gold'],f['master'])
            initial._assert_outcome(result,request,envelope,q,f['gold']['mode'])
            actual=initial._assert_actual(cur,f['x'],f['gold'],f['master'],result,request,f['original_movements'])
            nf.assert_payment_unchanged(cur,f['x'])
            detail=nf.source.read(cur,f['x']['f'])['detail']
            assert detail['financial']['paid_total']=='800.00'and detail['financial']['open_balance']=='0.00'
            assert cur.execute('select count(*)from cp7_credit.return_requests where request_id=%s',(request,)).fetchone()[0]==1
            out=dict(status='PASS',strict_original_money_date_stock_HPP_oracles=True,original_payments_immutable=True,
              original_paid=f['gold']['paid'],effective_paid='800.00',receivable='0.00',
              return_journal=actual['native_return_journal'],recognition_journal=actual['recognition_journal'],
              refund_journal=actual['refund_journal'])
            conn.rollback()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
