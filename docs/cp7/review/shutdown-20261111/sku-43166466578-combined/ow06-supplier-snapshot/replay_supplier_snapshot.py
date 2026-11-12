"""Reproduce supplier review and page drift, with a volatile Auth boundary."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic, sleep
from zipfile import ZipFile
import sys

import psycopg
from psycopg.errors import InsufficientPrivilege
from psycopg.types.json import Jsonb
from loopback_postgres import cluster
from replay_sku_owning_install import exact_catalog

FOLDER = Path(__file__).resolve().parent
SCHEMA = 'cp7_supplier_transfer'
PUBLIC = 'public.erp_cp7_get_supplier_transfer_v1(jsonb)'
WORKSPACE = f'{SCHEMA}.workspace_v1(jsonb)'
DETAIL = f'{SCHEMA}.detail_v1(uuid)'
CHILD = f'{SCHEMA}.child_detail_v1(uuid,jsonb)'
REVIEW = f'{SCHEMA}.review_v1(uuid,uuid)'
INNER = f'{SCHEMA}.workspace_snapshot_v1(jsonb,jsonb)'
SUPPLIER = '30000000-0000-4000-8000-000000000001'
TRANSFER = '10000000-0000-4000-8000-000000000001'
JOURNAL = '20000000-0000-4000-8000-000000000001'
GATE = 77241407
QUERY = dict(supplier_id=SUPPLIER, transfer_id=TRANSFER)

# This is the exact pair of SELECTs in the observed workspace body.
PAGE_OLD = """ select count(*)into tn from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier;
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.number,'status',x.status,'amount',x.amount::text,'payment_date',x.payment_date)order by x.recorded_at desc,x.id),'[]')into trows
  from(select *from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier order by recorded_at desc,id limit 25 offset toff)x;"""
PAGE_NEW = """ with matching as materialized(
  select * from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier
 ), page_rows as(
  select * from matching order by recorded_at desc,id limit 25 offset toff
 )
 select (select count(*) from matching),
  coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'number',x.number,'status',x.status,
    'amount',x.amount::text,'payment_date',x.payment_date)order by x.recorded_at desc,x.id)
   from page_rows x),'[]'::jsonb)
 into tn,trows;"""
GUARD = (" if cp7_supplier_transfer.access_now_v1(false)is distinct from auth_before then "
         "raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;")


def pin(value):
    b=value.encode() if isinstance(value,str) else value
    return dict(bytes=len(b),sha256=sha256(b).hexdigest())


def once(source, before, after):
    assert source.count(before)==1, before
    return source.replace(before,after,1)


def original(path):
    with ZipFile(path) as z:
        raw=z.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert pin(raw)==dict(bytes=16048163,sha256='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07')
    rows=dict(json.loads(raw)['functions'])
    return {n:rows[n] for n in (WORKSPACE,PUBLIC,DETAIL,CHILD,REVIEW)}


def derive(rows):
    old=rows[WORKSPACE][0]
    narrow=once(old,PAGE_OLD,PAGE_NEW)
    prefix,body,end=old.split('$function$')
    assert end=='\n'
    inner=once(narrow,'workspace_v1(p jsonb)','workspace_snapshot_v1(p jsonb, p_authority jsonb)')
    inner=once(inner,'\n SECURITY DEFINER\n','\n STABLE\n')
    inner=once(inner,' auth_before:=cp7_supplier_transfer.access_now_v1(false);',' auth_before:=p_authority;')
    inner=once(inner,GUARD+'\n','')
    wrapper=prefix+'$function$'+"""
declare auth_before jsonb; result jsonb;
begin
 auth_before:=cp7_supplier_transfer.access_now_v1(false);
 result:=cp7_supplier_transfer.workspace_snapshot_v1(p,auth_before);
"""+GUARD+"""
 return result;
end $function$
"""
    assert 'STABLE' not in prefix and "SET \"TimeZone\" TO 'UTC'" in prefix
    leaf={}
    for name in (DETAIL,CHILD,REVIEW):
        leaf[name]=once(rows[name][0],'\n SECURITY DEFINER\n','\n STABLE SECURITY DEFINER\n')
    return narrow,inner,wrapper,leaf


def schema(conn):
    conn.execute("""
      create schema erp; create schema fixture; create schema cp7_supplier_transfer;
      create role anon; create role authenticated; create role service_role; create role cp7_invoice_read;
      create table fixture.permission(allowed boolean not null);
      insert into fixture.permission values(true);
      create table fixture.transfers(id uuid primary key,supplier_id uuid,number text,
       payment_date timestamptz,amount numeric(20,2),cash_account_id uuid,journal_id uuid,status text,note text,recorded_at timestamptz);
      create table erp.suppliers(id uuid primary key,supplier_name text);
      create table erp.material_purchase_headers(id uuid primary key,supplier_id uuid,status text,purchase_number text,physical_at timestamptz);
      create table erp.supplier_payments(id uuid primary key,purchase_id uuid,payment_number text,status text,
       payment_date timestamptz,amount numeric(20,2),cash_account_id uuid);
      create table erp.chart_accounts(id uuid primary key,is_active boolean,is_postable boolean);
      create table erp.cash_accounts(id uuid primary key,cash_account_code text,cash_account_name text,coa_account_id uuid,is_active boolean);
      create table erp.journal_entries(id uuid primary key,journal_number text,status text,economic_date date,
       transaction_date date,posting_at timestamptz,period_shifted boolean,reversal_of_id uuid);
      create table erp.journal_lines(id uuid primary key,journal_entry_id uuid);
      create table cp7_supplier_transfer.allocations_v1(payment_id uuid,purchase_id uuid,amount numeric(20,2),transfer_id uuid);
      create table cp7_supplier_transfer.corrections_v1(original_id uuid,replacement_id uuid);
      create function cp7_supplier_transfer.access_now_v1(boolean) returns jsonb language sql volatile
       as $$select jsonb_build_object('reverse_payment',allowed) from fixture.permission$$;
      create function cp7_supplier_transfer.assert_transfer_v1(uuid) returns void language plpgsql stable
       as $$begin return;end$$;
      create function public.erp_get_supplier_credit_v1(p jsonb) returns jsonb language sql stable as
       $$select jsonb_build_object('purchases',coalesce(jsonb_agg(jsonb_build_object('id',h.id,'remaining','1000.00')),'[]'::jsonb))
       from erp.material_purchase_headers h where h.supplier_id=(p->>'supplier_id')::uuid$$;
    """,prepare=False)
    conn.execute(f"""
      create function fixture.interleave(ident uuid) returns boolean language plpgsql volatile as $$
      declare visits integer;
      begin
        if ident='{TRANSFER}'::uuid and current_setting('fixture.reader_barrier', true)='on' then
          visits:=coalesce(nullif(current_setting('fixture.visits', true),''),'0')::integer+1;
          perform set_config('fixture.visits',visits::text,false);
          if visits=current_setting('fixture.gate_after')::integer then perform pg_advisory_xact_lock({GATE});end if;
        end if;
        return true;
      end $$;
      create view cp7_supplier_transfer.transfers_v1 as select * from fixture.transfers where fixture.interleave(id);
    """,prepare=False)
    conn.execute("insert into erp.suppliers values(%s,'Supplier fixture')", (SUPPLIER,))
    conn.execute("insert into erp.journal_entries values(%s,'J-1','POSTED','2026-11-07','2026-11-07','2026-11-07T01:00:00Z',false,null)",(JOURNAL,))
    conn.execute("insert into fixture.transfers values(%s,%s,'T-1','2026-11-07T01:00:00Z',1.23,null,%s,'POSTED','fixture','2026-11-07T01:00:00Z')",
                 (TRANSFER,SUPPLIER,JOURNAL))


def read(conn):
    val=conn.execute(f'select {PUBLIC.partition("(")[0]}(%s)',(Jsonb(QUERY),)).fetchone()[0]
    return dict(token=val['review_token'], selected=val['selected']['status'],
                page=[r['status'] for r in val['transfers']['rows']],can_write=val['can_write'])


def race(writer,reader,pool,action,rollback=False,reader_fn=read,gate_after=2):
    pid=reader.execute('select pg_backend_pid()').fetchone()[0]
    holder=writer.execute('select pg_backend_pid()').fetchone()[0]
    reader.execute("select set_config('fixture.visits','0',false),set_config('fixture.reader_barrier','on',false),"
                   "set_config('fixture.gate_after',%s,false)",(str(gate_after),))
    writer.execute('select pg_advisory_lock(%s)',(GATE,))
    future=pool.submit(reader_fn,reader)
    try:
        deadline=monotonic()+5
        while writer.execute('select pg_blocking_pids(%s)',(pid,)).fetchone()[0]!=[holder]:
            assert monotonic()<deadline and not future.done(),'Reader did not reach the expected transfer read'
            sleep(.01)
        with writer.transaction(force_rollback=rollback):
            writer.execute(action)
        assert not future.done()
    finally:
        assert writer.execute('select pg_advisory_unlock(%s)',(GATE,)).fetchone()==(True,)
    try:
        return future.result(timeout=5)
    finally:
        reader.execute('reset fixture.reader_barrier')



def pages(conn, offset=25):
    query=dict(supplier_id=SUPPLIER,purchase_offset=offset,transfer_offset=offset)
    data=conn.execute(f'select {PUBLIC.partition("(")[0]}(%s)',(Jsonb(query),)).fetchone()[0]
    def compact(value):
        return dict(total=value['total'], rows=[x['number'] for x in value['rows']],
                    offset=value['offset'], next_offset=value['next_offset'])
    return {k:compact(data[k]) for k in ('receipts','transfers')}


def insert_transfer(conn,i):
    conn.execute("""insert into fixture.transfers values(%s,%s,%s,
      '2026-11-07T01:00:00Z',1.23,null,%s,'POSTED','fixture',
      '2026-11-07T01:00:00Z'::timestamptz+%s*interval '1 second')""",
      (f'10000000-0000-4000-8000-{i:012d}',SUPPLIER,f'T-{i:02d}',JOURNAL,26-i))


def pagination(writer,reader,pool,old,candidate):
    for i in range(1,27):
        writer.execute("""insert into erp.material_purchase_headers values
          (%s,%s,'POSTED',%s,'2026-11-07T01:00:00Z'::timestamptz+%s*interval '1 second')""",
          (f'50000000-0000-4000-8000-{i:012d}',SUPPLIER,f'AP-{i:02d}',i))
    observed={}
    for name,definition in (('original',old),('snapshot',candidate)):
        writer.execute('truncate fixture.transfers')
        for i in range(1,26):
            insert_transfer(writer,i)
        writer.execute(definition)
        before=pages(reader)
        assert before['transfers']==dict(total='25',rows=[],offset=25,next_offset=None)
        assert before['receipts']==dict(total='26',rows=['AP-26'],offset=25,next_offset=None)
        insert="""insert into fixture.transfers values
          ('10000000-0000-4000-8000-000000000026','30000000-0000-4000-8000-000000000001',
           'T-26','2026-11-07T01:00:00Z',1.23,null,'20000000-0000-4000-8000-000000000001',
           'POSTED','fixture','2026-11-07T01:00:00Z')"""
        rolled_back=race(writer,reader,pool,insert,rollback=True,reader_fn=pages,gate_after=1)
        assert rolled_back==before
        during=race(writer,reader,pool,insert,reader_fn=pages,gate_after=1)
        after=pages(reader)
        first=pages(reader,0)
        assert after['transfers']==dict(total='26',rows=['T-26'],offset=25,next_offset=None)
        assert first['transfers']['next_offset']==25 and after['receipts']==before['receipts']
        assert len(set(first['transfers']['rows']+after['transfers']['rows']))==26
        expected=['T-26'] if name=='original' else []
        assert during['transfers']==dict(total='25',rows=expected,offset=25,next_offset=None)
        observed[name]=dict(before=before,during=during,next=after,rollback_matches=True,unique_26=True)
    return observed


def main(pg_bin,archive):
    rows=original(archive)
    narrow,inner,wrapper,leaf=derive(rows)
    proposal=[*leaf.values(),inner,f'revoke all on function {INNER} from public,anon,authenticated,service_role,cp7_invoice_read',wrapper]
    sql='\n'.join(x.strip()+';' for x in proposal)+'\n'
    catalogue=exact_catalog()
    results={}
    with cluster(pg_bin) as info, psycopg.connect(**info,autocommit=True) as w, psycopg.connect(**info,autocommit=True) as r, ThreadPoolExecutor(max_workers=1) as pool:
        assert w.execute('show server_version').fetchone()==('17.6',)
        schema(w)
        for name,row in rows.items():
            w.execute(row[0])
            w.execute(f'revoke all on function {name} from public,anon,authenticated,service_role,cp7_invoice_read')
            for role,grantor,permission,grantable in row[18]:
                assert (grantor,permission,grantable)==('postgres','EXECUTE',False)
                assert role in ('postgres','authenticated','cp7_invoice_read')
                if role!='postgres':
                    w.execute(f'grant execute on function {name} to {role}')
        for name,ddl in leaf.items():
            w.execute(ddl)
        r.execute('set role authenticated')
        reverse=f"update fixture.transfers set status='REVERSED' where id='{TRANSFER}'"
        for label,definition in (('page_only',narrow),('same_snapshot',wrapper)):
            w.execute("update fixture.transfers set status='POSTED'")
            if label=='same_snapshot':
                w.execute(inner)
                w.execute(f'revoke all on function {INNER} from public,anon,authenticated,service_role,cp7_invoice_read')
            w.execute(definition)
            old=read(r)
            assert old['selected']=='POSTED'
            aborted=race(w,r,pool,reverse,rollback=True)
            assert aborted==old
            during=race(w,r,pool,reverse)
            new=read(r)
            assert new['selected']=='REVERSED' and new['token']!=old['token']
            if label=='page_only':
                assert during['selected']==new['selected'] and during['token']==old['token'],(old,during,new)
            else:
                assert during==old,(old,during,new)
            results[label]=dict(before=old,during=during,next=new,rolled_back_writer_equals_before=True)

        w.execute("update fixture.permission set allowed=true")
        try:
            race(w,r,pool,'update fixture.permission set allowed=false')
        except InsufficientPrivilege as err:
            assert err.sqlstate=='42501' and 'CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED' in str(err)
        else:
            raise AssertionError('Concurrent Auth downgrade was not refused')
        w.execute("update fixture.permission set allowed=true")
        page_results=pagination(w,r,pool,rows[WORKSPACE][0],wrapper)
        assert w.execute('select provolatile from pg_proc where oid=to_regprocedure(%s)',(WORKSPACE,)).fetchone()==('v',)
        assert w.execute('select provolatile,prosecdef from pg_proc where oid=to_regprocedure(%s)',(INNER,)).fetchone()==('s',False)
        for role in ('anon','authenticated','service_role','cp7_invoice_read'):
            assert w.execute('select has_function_privilege(%s,%s,%s)',(role,INNER,'EXECUTE')).fetchone()==(False,)
        w.execute(rows[WORKSPACE][0])
        w.execute('drop function '+INNER)
        for name in leaf:
            w.execute(rows[name][0])
        for name,row in rows.items():
            assert w.execute('select pg_get_functiondef(to_regprocedure(%s))',(name,)).fetchone()==(row[0],)

        with w.transaction():
            before=catalogue._catalog_rows(w)
            old_data=catalogue._data(w)
            assert {name:before['functions'][name] for name in rows}==rows
            with w.transaction(force_rollback=True):
                w.execute(sql,prepare=False)
                after=catalogue._catalog_rows(w)
                assert set(after['functions'])-set(before['functions'])=={INNER}
                assert after['functions'][INNER][4] is False
                assert after['functions'][INNER][8]=='s'
                assert after['functions'][INNER][18]==[['postgres','postgres','EXECUTE',False]]
                for name,row in before['functions'].items():
                    revised=after['functions'][name]
                    if name in leaf:
                        assert revised[0]==leaf[name] and revised[8]=='s'
                        assert revised[1:8]==row[1:8] and revised[9:]==row[9:]
                    elif name==WORKSPACE:
                        assert revised[0]==wrapper and revised[1:]==row[1:]
                    else:
                        assert revised==row
                assert all(before[g]==after[g] for g in before if g!='functions')
                assert catalogue._data(w)==old_data
            assert catalogue._catalog_rows(w)==before and catalogue._data(w)==old_data
    (FOLDER/'OW06_SUPPLIER_SNAPSHOT_PREVIEW.sql').write_text(sql)
    result=dict(status='OW06_SUPPLIER_WORKSPACE_REVIEW_AND_DETAIL_SNAPSHOT_FIXTURE_PASS',
        postgres='17.6',same_original_archive=True,observed=results,pagination=page_results,concurrent_auth_change_refused='42501',
        workspace_volatile=True,snapshot_helper_stable_and_private=True,original_definitions_restored=True,
        full_patch_executed=True,prior_full19_and_acl_match=True,exact_all22_and_data_rollback=True,
        original_definitions={k:pin(v[0]) for k,v in rows.items()},
        patch=pin(sql),fixtures_for_ap_authorization_and_guard=True,actual_ERP_cases=0,
        independent_acceptance=False,runtime_admission=False,production_go=False)
    (FOLDER/'OW06_SUPPLIER_SNAPSHOT_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'], result['concurrent_auth_change_refused'],result['patch'])


if __name__=='__main__':
    main(sys.argv[1],sys.argv[2])

