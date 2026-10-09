"""Own 73->41 physical source, read-only observations for real browser commands."""
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
sys.path.insert(0,str(Path.cwd().parent/'auditor/scripts'))
import cases_business as b

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
    assert u.hostname in ('127.0.0.1','localhost') and u.path=='/cp6_auditor_browser','DISPOSABLE_ONLY'
    p=json.loads(sys.stdin.read());op=sys.argv[1]
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=b.production(cur,date.fromisoformat(p['today']));b.assess(cur,f)
            lots=cur.execute('select id::text from erp.fg_lots where po_id=%s',(f['po'],)).fetchall()
            assert len(lots)==1;f['lot']=lots[0][0]
            f['destination_name']=cur.execute('select location_name from erp.locations where id=%s',(f['destination'],)).fetchone()[0]
            f['bank_code']=cur.execute('select cash_account_code from erp.cash_accounts where id=%s',(f['bank'],)).fetchone()[0]
            f['mapping']={k:b.account(cur,k) for k in ('AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS')};out=f
        elif op=='state':
            f=p['fixture'];b.admin(cur)
            found=cur.execute('select id::text from erp.sales_headers where sale_number=%s',(f['tag'],)).fetchone()
            doc=b.returns.source.read(cur,dict(f,sale=found[0]))['detail'] if found else None
            returns=cur.execute('select id::text,status from erp.sales_returns where sale_id=%s order by id',(found[0],)).fetchall() if found else []
            payments=cur.execute('select id::text,status,amount from erp.sales_payments where sale_id=%s order by id',(found[0],)).fetchall() if found else []
            positions=cur.execute('select m.location_id::text,m.quality_grade,sum(m.qty_signed)::text from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s group by m.location_id,m.quality_grade having sum(m.qty_signed)<>0 order by m.location_id,m.quality_grade',(f['po'],)).fetchall()
            raw=cur.execute('select sum(qty_signed)::text,sum(qty_signed*unit_cost_snapshot)::text from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()
            bad=cur.execute('select j.id::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id group by j.id having sum(l.debit-l.credit)<>0').fetchall()
            out=dict(document=doc,returns=returns,payments=payments,positions=positions,available=str(b.fg_qty(cur,f)),accounts=b.gl(cur),raw=raw,unbalanced_journals=bad)
        else:raise ValueError(op)
        b.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
