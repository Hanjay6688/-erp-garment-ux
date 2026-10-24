"""Synthetic Native invoice histories, restricted to the disposable browser DB."""
from datetime import date
from hashlib import sha256
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_sales_payment_cases as payments
import cp7_sales_return_cases as returns
from cp7_ow09_lists.cases import ordered
from cp7_ab_bounded_chain import composition as product


def prepare(cur,today):
    payment=payments.fixture(cur,today,qty=4,price='20')
    returned=returns.fixture(cur,today)
    for kind,business,f in [('payment',payments,payment),('return',returns,returned)]:
        for n in range(1,32):
            if kind=='payment':
                payload,version=business.payment_payload(cur,f,'1')
                payload['payment_number']=f['tag']+'-PAY-'+str(n)
                result=business.cmd.command(cur,'PAYMENT',payload,version)
            else:
                payload,version=business.payload(cur,f,qty='1',refund='1')
                payload['return_number']=f['tag']+'-RET-'+str(n)
                result=business.cmd.command(cur,'RETURN',payload,version)
            # Keep a real posted row and thirty immutable reversed originals.
            # The history filter itself must still span more than one page.
            if n!=31:business.inverse(cur,f,result[kind+'_id'])
        payments.b.api.admin(cur)
    result={}
    for kind,f,table,number,day in [('payment',payment,'sales_payments','payment_number','payment_date'),
            ('return',returned,'sales_returns','return_number','physical_at')]:
        rows=[dict(id=str(i),label=n,status=s,date=d)for i,n,s,d in cur.execute(
            f'select id,{number},status,{day} from erp.{table} where sale_id=%s',(f['sale'],)).fetchall()]
        assert len(rows)==31 and sum(r['status']=='REVERSED'for r in rows)==30
        by_id={r['id']:r for r in rows};oracles={}
        for order in ('SOURCE','LABEL_ASC','LABEL_DESC'):
            for status in ('ALL','POSTED','REVERSED'):
                keep=[r for r in rows if status=='ALL'or r['status']==status]
                ids=ordered(keep,order,[('date',True),('id',False)])
                oracles[order+':'+status]=[dict(id=i,number=by_id[i]['label'])for i in ids]
        result[kind]=dict(sale=f['sale'],tag=f['tag'],oracles=oracles)
    return result


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    operation=sys.argv[1];payload=json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        if operation=='prepare':
            had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if not had:cur.execute('grant usage on schema erp to authenticated')
            result=prepare(cur,date.fromisoformat(payload['today']))
            payments.b.api.admin(cur)
            cur.execute('set constraints all immediate')
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
            conn.commit()
        elif operation=='state':
            # Full current-chain business tables/sequences; Auth lifecycle is
            # checked separately by the browser host before/after all cases.
            result=dict(sha256=product.catalog.digest(product.catalog._data(cur)))
            conn.rollback()
        else:raise ValueError('UNKNOWN_OPERATION')
        print(json.dumps(result,default=str))


if __name__=='__main__':main()
