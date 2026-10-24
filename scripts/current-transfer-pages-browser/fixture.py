"""Native setup/read oracles on the loopback browser copy; every journey write goes through the actual UI."""
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import json
from hashlib import sha256
import os
import sys
import uuid

operation=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
from cp7_supplier_transfer import cases as t
import psycopg


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def main():
    args=json.load(sys.stdin)
    url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
    assert parsed.hostname in('127.0.0.1','localhost')and parsed.path=='/cp6_auditor_browser'
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        t.b.api.admin(cur)
        if operation=='prepare':
            # ERP USAGE for the fixture actor exists only inside this transaction; the committed catalog is unchanged.
            had=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
            acl=one(cur,"select nspacl::text from pg_namespace where nspname='erp'")
            if not had:cur.execute('grant usage on schema erp to authenticated')
            today=date.fromisoformat(args['today'])
            f=t.fixture(cur,today);t.b.api.admin(cur)
            prefix='OW06PAGE-'+uuid.uuid4().hex[:10];made=[]
            receipt=t.single.invoice.receipt
            for n in range(1,32):
                source=receipt.fixture(cur,today,'100','10',True)
                source['payload']['purchase_number']=prefix+'-'+str(n)
                draft=receipt.command(cur,'SAVE_DRAFT',source['payload'])
                posted=receipt.post(cur,draft);made.append(str(posted['purchase_id']))
            t.b.api.admin(cur)
            ordered=[dict(id=str(i),number=n)for i,n in cur.execute(
                'select id,purchase_number from erp.material_purchase_headers where id=any(%s::uuid[])order by physical_at,id',(made,)).fetchall()]
            assert len(ordered)==31
            f['receipts']=[ordered[0]['id'],ordered[25]['id']]
            t.auth.actor(cur)
            page=cur.execute('select public.erp_cp7_get_supplier_transfer_v1(%s)',
                (json.dumps(dict(supplier_id=f['supplier'],purchase_q=prefix,purchase_offset=0)),)).fetchone()[0]['receipts']
            t.b.api.admin(cur)
            assert page['total']=='31'and page['next_offset']==25
            assert [r['id']for r in page['rows']]==[r['id']for r in ordered[:25]]
            physical=sha256(json.dumps(t.single.supplier.physical_state(cur),sort_keys=True,default=str).encode()).hexdigest()
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert one(cur,"select nspacl::text from pg_namespace where nspname='erp'")==acl
            code,name=cur.execute('select cash_account_code,cash_account_name from erp.cash_accounts where id=%s',(f['cash'],)).fetchone()
            at=one(cur,'select statement_timestamp()')-timedelta(minutes=5)
            out=dict(supplier=f['supplier'],receipts=f['receipts'],cash=f['cash'],bank_start=str(f['bank_start']),bank_code=code,bank_name=name,
                numbers=[one(cur,'select purchase_number from erp.material_purchase_headers where id=%s',(pid,))for pid in f['receipts']],
                at_local=at.astimezone(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%dT%H:%M'),
                all_receipts=made,receipt_order=ordered,search_prefix=prefix,physical_sha256=physical)
            conn.commit();return out
        assert operation=='observe'
        f=args['fixture']
        for key in('supplier','cash'):uuid.UUID(f[key])
        result=dict(cash_delta=str(t.single.misc.cash_balance(cur,f['cash'])-t.D(f['bank_start'])),
            paid={pid:str(one(cur,"select coalesce(sum(amount),0)from erp.supplier_payments where purchase_id=%s and status='POSTED'",(pid,)))for pid in f['receipts']},
            # The retained fixture reuses one supplier, so only transfers allocated to this journey's own receipts count.
            transfers=[[str(x)for x in r]for r in cur.execute("""select number,status,amount from cp7_supplier_transfer.transfers_v1 x
                where x.supplier_id=%s and exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=x.id and a.purchase_id=any(%s::uuid[]))
                order by recorded_at,id""",(f['supplier'],f['receipts'])).fetchall()],
            journals=[[str(x)for x in r]for r in cur.execute("""select j.status,sum(l.debit),sum(l.credit),count(*)from erp.journal_entries j
                join erp.journal_lines l on l.journal_entry_id=j.id join cp7_supplier_transfer.transfers_v1 x on x.id=j.source_id
                where j.source_type='CP7_SUPPLIER_TRANSFER'and x.supplier_id=%s
                 and exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=x.id and a.purchase_id=any(%s::uuid[]))
                group by j.id,j.status order by j.status,j.id""",(f['supplier'],f['receipts'])).fetchall()],
            unselected_posted_payments=one(cur,"select count(*)from erp.supplier_payments where purchase_id=any(%s::uuid[])and not(purchase_id=any(%s::uuid[]))and status='POSTED'",(f['all_receipts'],f['receipts'])),
            stock_HPP_sha256=sha256(json.dumps(t.single.supplier.physical_state(cur),sort_keys=True,default=str).encode()).hexdigest(),
            contexts=one(cur,'select count(*)from cp7_supplier_transfer.context_v1'))
        assert result['stock_HPP_sha256']==f['physical_sha256'],'TRANSFER_PAGING_CHANGED_STOCK_HPP'
        assert result['unselected_posted_payments']==0,'TRANSFER_PAGING_PAID_UNSELECTED_RECEIPT'
        conn.rollback();return result


if __name__=='__main__':print(json.dumps(main(),default=str))
