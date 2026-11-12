"""Exercise the same count/page race in three existing supplier payment readers."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import psycopg
from psycopg.errors import InsufficientPrivilege
from psycopg.types.json import Jsonb
from loopback_postgres import cluster
from replay_supplier_snapshot import GATE,SUPPLIER,once,pin,race,schema
from replay_sku_owning_install import exact_catalog

P = Path(__file__).resolve().parent
INVOICE = 'cp7_invoice.payment_workspace(uuid,text,integer,uuid)'
CREATE = 'cp7_supplier_payment_create.workspace(jsonb)'
CORRECTION = 'cp7_supplier_payment_correction.workspace(jsonb)'
PURCHASE = '50000000-0000-4000-8000-000000000001'
FIRST_PAYMENT = '60000000-0000-4000-8000-000000000001'
FIRST_CASH = '70000000-0000-4000-8000-000000000001'
CHART = '80000000-0000-4000-8000-000000000001'
CASH_FILTER = """from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0)"""
CASH_AGG = "jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind)order by c.cash_account_code,c.id)"
PAY_FILTER = "from erp.supplier_payments where purchase_id=h.id and(q='' or strpos(lower(payment_number),lower(q))>0)"
PAY_AGG = "jsonb_agg(cp7_invoice.payment_detail(p.id,ap)order by p.payment_date,p.created_at,p.id)"


def derive(name,source):
    if name==INVOICE:
        before=f""" select count(*) into total {PAY_FILTER};
 select coalesce({PAY_AGG},'[]')into rows
  from(select * {PAY_FILTER}
   order by payment_date,created_at,id limit 25 offset p_offset)p;"""
        after=f""" with matching as materialized(select * {PAY_FILTER}),
 page_rows as(select * from matching order by payment_date,created_at,id limit 25 offset p_offset)
 select (select count(*) from matching),coalesce((select {PAY_AGG} from page_rows p),'[]'::jsonb)
 into total,rows;"""
    else:
        indented=CASH_FILTER.replace('\n  where','\n   where')
        before=f""" select count(*)into total {CASH_FILTER};
 select coalesce({CASH_AGG},'[]')into rows
  from(select c.*{indented}
   order by c.cash_account_code,c.id limit 25 offset off)c;"""
        after=f""" with matching as materialized(select c.* {CASH_FILTER}),
 page_rows as(select * from matching order by cash_account_code,id limit 25 offset off)
 select (select count(*) from matching),coalesce((select {CASH_AGG} from page_rows c),'[]'::jsonb)
 into total,rows;"""
    revised=once(source,before,after)
    assert once(revised,after,before)==source
    return revised


def prepare(conn):
    schema(conn)
    conn.execute(f"""
      create schema cp7_invoice;
      create schema cp7_supplier_payment_create;
      create schema cp7_supplier_payment_correction;
      create table cp7_supplier_payment_correction.links(original_id uuid,replacement_id uuid,purchase_id uuid);
      create table erp.initial_import_prepayment_payments(payment_id uuid);
      alter table erp.supplier_payments add column created_at timestamptz;
      alter table erp.cash_accounts add column account_kind text;
      alter table erp.supplier_payments set schema fixture;
      alter table erp.cash_accounts set schema fixture;
      create function fixture.page_barrier(ident uuid) returns boolean language plpgsql volatile as $$
      begin
        if current_setting('fixture.reader_barrier',true)='on' and ident=current_setting('fixture.page_target',true)::uuid then
          perform pg_advisory_xact_lock({GATE});
        end if;
        return true;
      end $$;
      create view erp.supplier_payments as select * from fixture.supplier_payments where fixture.page_barrier(id);
      create view erp.cash_accounts as select * from fixture.cash_accounts where fixture.page_barrier(id);
      create function cp7_invoice.payment_access() returns jsonb language sql stable as
       $$select jsonb_build_object('reverse_payment',allowed) from fixture.permission$$;
      create function cp7_invoice.payment_ap(uuid) returns jsonb language sql stable as
       $$select jsonb_build_object('purchase_id',$1)$$;
      create function cp7_invoice.payment_detail(uuid,jsonb) returns jsonb language sql stable as
       $$select jsonb_build_object('id',id,'number',payment_number) from erp.supplier_payments where id=$1$$;
      create function cp7_supplier_payment_correction.link_value(cp7_supplier_payment_correction.links)
       returns jsonb language sql stable as $$select to_jsonb($1)$$;
      create function cp7_supplier_payment_create.review(uuid) returns jsonb language sql stable as
       $$select jsonb_build_object('purchase_id',$1)$$;
      insert into erp.chart_accounts values('{CHART}',true,true);
      insert into erp.material_purchase_headers values('{PURCHASE}','{SUPPLIER}','POSTED','P-1','2026-11-07T01:00:00Z');
    """,prepare=False)


def payment_insert(i):
    return f"""insert into fixture.supplier_payments values
      ('60000000-0000-4000-8000-{i:012d}','{PURCHASE}','PAY-{i:02d}','POSTED',
       '2026-11-07T01:00:00Z'::timestamptz+{i}*interval '1 second',1.23,'{FIRST_CASH}',
       '2026-11-07T01:00:00Z')"""


def cash_insert(i):
    return f"""insert into fixture.cash_accounts values
      ('70000000-0000-4000-8000-{i:012d}','BANK-{i:02d}','Bank fixture','{CHART}',true,'BANK')"""


def result_page(name,conn,offset=25):
    if name==INVOICE:
        raw=conn.execute('select cp7_invoice.payment_workspace(%s,%s,%s,%s)',(PURCHASE,'',offset,None)).fetchone()[0]['page']
        key='number'
    else:
        args=dict(purchase_id=PURCHASE,bank_offset=offset)
        if name==CORRECTION:
            args['payment_id']=FIRST_PAYMENT
        raw=conn.execute(f"select {name.partition('(')[0]}(%s)",(Jsonb(args),)).fetchone()[0]['cash_accounts']
        key='code'
    return dict(total=raw['total'],rows=[v[key] for v in raw['rows']],offset=raw['offset'],next_offset=raw['next_offset'])


def main(pg_bin, archive):
    with ZipFile(archive) as z:
        raw=z.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert pin(raw)['sha256']=='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'
    functions=dict(json.loads(raw)['functions'])
    before={k:functions[k][0] for k in (INVOICE,CREATE,CORRECTION)}
    after={k:derive(k,v) for k,v in before.items()}
    patch='\n'.join(s.strip()+';' for s in after.values())+'\n'
    catalogue=exact_catalog()
    proof={}
    with cluster(pg_bin) as info, psycopg.connect(**info,autocommit=True) as w, psycopg.connect(**info,autocommit=True) as r, ThreadPoolExecutor(max_workers=1) as pool:
        prepare(w)
        for n in (INVOICE,CREATE,CORRECTION):
            w.execute(before[n])
        for n in (INVOICE,CREATE,CORRECTION):
            reader=lambda conn:result_page(n,conn)
            expected='PAY-26' if n==INVOICE else 'BANK-26'
            target=FIRST_PAYMENT if n==INVOICE else FIRST_CASH
            r.execute("select set_config('fixture.page_target',%s,false)",(target,))
            mode={}
            for label,definition in (('original',before[n]),('one_statement',after[n])):
                w.execute("truncate fixture.supplier_payments,fixture.cash_accounts; update fixture.permission set allowed=true",prepare=False)
                for i in range(1,26):
                    w.execute(payment_insert(i))
                    w.execute(cash_insert(i))
                w.execute(definition)
                change=payment_insert(26) if n==INVOICE else cash_insert(26)
                init=reader(r)
                assert init==dict(total='25',rows=[],offset=25,next_offset=None)
                assert race(w,r,pool,change,rollback=True,reader_fn=reader,gate_after=1)==init
                during=race(w,r,pool,change,reader_fn=reader,gate_after=1)
                new=reader(r)
                assert during==dict(total='25',rows=[expected] if label=='original' else [],offset=25,next_offset=None)
                assert new==dict(total='26',rows=[expected],offset=25,next_offset=None)
                first=result_page(n,r,0)
                assert first['next_offset']==25 and len(set(first['rows']+new['rows']))==26
                try:
                    race(w,r,pool,'update fixture.permission set allowed=false',reader_fn=reader,gate_after=1)
                except InsufficientPrivilege as err:
                    assert err.sqlstate=='42501' and 'CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED' in str(err)
                else:
                    raise AssertionError('Auth change accepted: '+n)
                mode[label]=dict(first=init,during=during,next=new,rollback_kept_page=True,auth_change_refused=True)
            proof[n]=mode
            w.execute(before[n])

        with w.transaction(),w.cursor() as c:
            old=catalogue._catalog_rows(c)
            data=catalogue._data(c)
            with w.transaction(force_rollback=True):
                c.execute(patch,prepare=False)
                new=catalogue._catalog_rows(c)
                for name,body in after.items():
                    assert old['functions'][name][1:]==new['functions'][name][1:]
                    assert new['functions'][name][0]==body
                    new['functions'][name]=old['functions'][name]
                assert new==old and catalogue._data(c)==data
            assert catalogue._catalog_rows(c)==old and catalogue._data(c)==data
    (P/'OW06_PAYMENT_COUNT_PAGE_PREVIEW.sql').write_text(patch)
    result=dict(status='THREE_EXACT_SUPPLIER_PAYMENT_COUNT_PAGE_RACES_FIXED_IN_FIXTURE',proof=proof,
                catalogue_sha256=pin(raw)['sha256'],source_before={k:pin(s) for k,s in before.items()},
                source_after={k:pin(s) for k,s in after.items()},patch=pin(patch),
                exact_catalogue_and_data_rollback=True,unchanged_attributes_under_fixture_owners=True,
                fixture_AP_and_authorization=True,actual_ERP_cases=0,production_go=False,runtime_admission=False)
    (P/'OW06_PAYMENT_COUNT_PAGE_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],len(proof),result['patch'])


if __name__=='__main__':
    main(sys.argv[1],sys.argv[2])

