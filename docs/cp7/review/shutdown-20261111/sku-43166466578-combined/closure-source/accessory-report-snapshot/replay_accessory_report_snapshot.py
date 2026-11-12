"""Exercise S05's report and filter pagination against concurrent updates."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys
from zipfile import ZipFile

import psycopg
from psycopg.errors import InsufficientPrivilege, RaiseException
from loopback_postgres import cluster
from replay_sku_owning_install import exact_catalog
from replay_supplier_snapshot import GATE, once, pin, race


HERE = Path(__file__).resolve().parent
SCHEMA = 'cp7_accessory_standard_report'
ARGS = '(date,date,uuid,uuid,text,integer,integer)'
WORKSPACE = f'{SCHEMA}.workspace{ARGS}'
DATA = f'{SCHEMA}.workspace_data_v1{ARGS}'
PUBLIC = f'public.erp_cp7_get_accessory_standard_report_v1{ARGS}'
FIRST = '10000000-0000-4000-8000-000000000001'
PO = '20000000-0000-4000-8000-000000000001'
ISOLATION = " if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_ACCESSORY_REPORT_FRESH_ACCESS_REQUIRED';end if;"
CHECK = """ -- A second live permission read after the statement data read; no cached
 -- JWT metadata, no elevated browser/private grants and no stale answer.
 if cp7_accessory_standard_report.access_now()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_ACCESSORY_REPORT_ACCESS_CHANGED: hak akses berubah; muat ulang.';end if;"""


def derive(old):
    prefix, _, end = old.split('$function$')
    assert end == '\n'
    helper = once(old, f'{SCHEMA}.workspace(', f'{SCHEMA}.workspace_data_v1(')
    helper = once(helper, '\n SECURITY DEFINER\n', '\n STABLE\n')
    helper = once(helper, 'declare v_access jsonb;v_result', 'declare v_result')
    helper = once(helper, ISOLATION + '\n v_access:=cp7_accessory_standard_report.access_now();\n', '')
    helper = once(helper, CHECK + '\n', '')
    wrapper = prefix + '$function$' + """
declare v_access jsonb;v_result jsonb;
begin
""" + ISOLATION + """
 v_access:=cp7_accessory_standard_report.access_now();
 v_result:=cp7_accessory_standard_report.workspace_data_v1(p_start,p_end,p_contractor,p_po,p_query,p_offset,p_limit);
""" + CHECK + """
 return v_result;
end $function$
"""
    return helper, wrapper


def prepare(conn, rows):
    conn.execute(f"""
      create role cp7_accessory_standard_read nologin;
      create role authenticated nologin;
      create role anon nologin;
      create role service_role nologin;
      create role cp7_capture nologin;
      create schema auth;
      create schema erp;
      create schema fixture;
      create schema {SCHEMA} authorization cp7_accessory_standard_read;
      create table fixture.contractors(id uuid primary key,contractor_name text,contractor_code text,is_active bool);
      create table fixture.access(allowed bool,epoch int,used_qty int);
      insert into fixture.access values(true,1,7);
      create table erp.production_orders(id uuid,po_number text,contractor_id uuid);
      create table erp.contractor_material_issues(po_id uuid,contractor_id uuid);
      insert into erp.production_orders values('{PO}','PO-1','{FIRST}');
      create function fixture.interleave(ident uuid) returns boolean language plpgsql volatile as $$
      declare visits int;
      begin
       if ident='{FIRST}' and current_setting('fixture.reader_barrier',true)='on' then
        visits:=coalesce(nullif(current_setting('fixture.visits',true),''),'0')::int+1;
        perform set_config('fixture.visits',visits::text,false);
        if visits=current_setting('fixture.gate_after')::int then perform pg_advisory_xact_lock({GATE});end if;
       end if;
       return true;
      end $$;
      create view erp.contractors as select * from fixture.contractors where fixture.interleave(id);
      create function auth.uid()returns uuid language sql stable
       as $$select nullif(current_setting('fixture.actor',true),'')::uuid$$;
      create function auth.jwt()returns jsonb language sql stable
       as $$select jsonb_build_object('role',current_setting('fixture.jwt_role',true))$$;
      create function erp.get_my_access_v1()returns jsonb language sql volatile
       as $$select jsonb_build_object('allowed',allowed,'profile',jsonb_build_object('role_code','ADMIN'),'epoch',epoch)from fixture.access$$;
      create function erp.has_permission(text)returns bool language sql volatile
       as $$select allowed from fixture.access$$;
      create function {SCHEMA}.period_data(date,date,uuid,uuid)returns jsonb language sql stable
       as $$select jsonb_build_object('counts',jsonb_build_object('issue_items',1,'snapshots',1,'lots',1),'used_qty',used_qty)from fixture.access$$;
    """,prepare=False)
    for name in (f'{SCHEMA}.access_now()', f'{SCHEMA}.iso(timestamp with time zone)', WORKSPACE, PUBLIC):
        conn.execute(rows[name][0])
    conn.execute(f"""
      revoke all on function {WORKSPACE} from public;
      grant execute on function {WORKSPACE} to cp7_accessory_standard_read;
      alter function {PUBLIC} owner to cp7_accessory_standard_read;
      revoke all on function {PUBLIC} from public;
      grant execute on function {PUBLIC} to authenticated;
    """,prepare=False)


def contractor(number):
    return f"""insert into fixture.contractors values
      ('10000000-0000-4000-8000-{number:012d}','C-{number:02d}','F-{number:02d}',true)"""


def page(conn, *, selected=False, offset=25):
    result = conn.execute(f"select {PUBLIC.split('(')[0]}(%s,%s,%s,%s,'',%s,25)",
        ('2026-11-01','2026-11-12',FIRST if selected else None,PO if selected else None,offset)).fetchone()[0]
    return dict(total=result['contractors']['total'], rows=[row['name'] for row in result['contractors']['rows']],
                next_offset=result['contractors']['next_offset'],
                selected=result['selected_contractor']['name'] if selected else None,
                used_qty=result['report']['used_qty'] if selected else None)


def main(bin_dir, archive):
    with ZipFile(archive) as bundle:
        raw=bundle.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert pin(raw)==dict(bytes=16048295,sha256='7e1ba214f634afd822a7ef29e7a5731690aceb8d5afd7fb0f62f22fbd3ac0e55')
    rows=dict(json.loads(raw)['functions'])
    original=rows[WORKSPACE][0]
    helper,revised=derive(original)
    patch=helper.strip()+';\n'+f'alter function {DATA} owner to postgres;\n'
    patch+=f'revoke all on function {DATA} from public,anon,authenticated,service_role,cp7_capture,cp7_accessory_standard_read;\n'
    patch+=revised.strip()+';\n'
    reports={}
    with cluster(bin_dir) as cfg, psycopg.connect(**cfg,autocommit=True) as writer, \
            psycopg.connect(**cfg,autocommit=True) as reader, ThreadPoolExecutor(max_workers=1) as pool:
        prepare(writer,rows)
        reader.execute('set session authorization authenticated')
        reader.execute("select set_config('fixture.actor',%s,false),set_config('fixture.jwt_role','authenticated',false)",(FIRST,))
        catalog=exact_catalog()
        for label in ('original','snapshot'):
            writer.execute('truncate fixture.contractors;update fixture.access set allowed=true,epoch=1,used_qty=7',prepare=False)
            for number in range(1,26):
                writer.execute(contractor(number))
            with writer.transaction(),writer.cursor() as cur:
                before=catalog._catalog_rows(cur)
                before_data=catalog._data(cur)
                if label=='snapshot':
                    with writer.transaction(force_rollback=True):
                        cur.execute(patch,prepare=False)
                        changed=catalog._catalog_rows(cur)
                        added=changed['functions'].pop(DATA)
                        assert added[1]=='postgres' and added[4] is False and added[8]=='s'
                        assert added[18]==[['postgres','postgres','EXECUTE',False]]
                        assert changed['functions'][WORKSPACE][1:]==before['functions'][WORKSPACE][1:]
                        assert changed['functions'][WORKSPACE][0]==revised
                        changed['functions'][WORKSPACE]=before['functions'][WORKSPACE]
                        assert changed==before and catalog._data(cur)==before_data
                    assert catalog._catalog_rows(cur)==before and catalog._data(cur)==before_data
                    cur.execute(patch,prepare=False)

            initial=page(reader)
            assert initial['total']==25 and initial['rows']==[]
            assert race(writer,reader,pool,contractor(26),rollback=True,reader_fn=page,gate_after=1)==initial
            during=race(writer,reader,pool,contractor(26),reader_fn=page,gate_after=1)
            assert during['total']==25 and during['rows']==(['C-26'] if label=='original' else [])
            latest=page(reader)
            assert latest['total']==26 and latest['rows']==['C-26']
            first=page(reader,offset=0)
            assert first['next_offset']==25 and len(set(first['rows']+latest['rows']))==26

            selected=lambda conn:page(conn,selected=True,offset=0)
            before_selected=selected(reader)
            assert before_selected['selected']=='C-01' and before_selected['used_qty']==7
            update=f"""with moved as (update fixture.contractors set contractor_name='C-01 new' where id='{FIRST}' returning id)
              update fixture.access set used_qty=8 where exists(select 1 from moved)"""
            changed=race(writer,reader,pool,update,reader_fn=selected,gate_after=3)
            assert changed['selected']=='C-01' and changed['used_qty']==(8 if label=='original' else 7)
            after_selected=selected(reader)
            assert after_selected['selected']=='C-01 new' and after_selected['used_qty']==8

            try:
                race(writer,reader,pool,'update fixture.access set allowed=false',reader_fn=page,gate_after=1)
            except InsufficientPrivilege as err:
                assert err.sqlstate=='42501' and 'CP7_ACCESSORY_REPORT_DENIED' in str(err)
            else:
                raise AssertionError('Stale access accepted')
            writer.execute('update fixture.access set allowed=true')
            try:
                race(writer,reader,pool,'update fixture.access set epoch=2',reader_fn=page,gate_after=1)
            except InsufficientPrivilege as err:
                assert err.sqlstate=='42501' and 'CP7_ACCESSORY_REPORT_ACCESS_CHANGED' in str(err)
            else:
                raise AssertionError('Changed permission snapshot accepted')
            try:
                with reader.transaction(force_rollback=True):
                    reader.execute('set transaction isolation level repeatable read')
                    page(reader)
            except RaiseException as error:
                assert error.diag.message_primary=='CP7_ACCESSORY_REPORT_FRESH_ACCESS_REQUIRED'
            else:
                raise AssertionError('Stale transaction isolation accepted')
            reports[label]=dict(concurrent_page=during,concurrent_report=dict(selected=changed['selected'],
                used_qty=changed['used_qty']),next_page=latest,rollback_page_equal=True,permission_revocation_refused=True,
                permission_snapshot_change_refused=True)

    output=HERE/'S05_ACCESSORY_REPORT_SNAPSHOT_PREVIEW.sql'
    output.write_text(patch)
    receipt=dict(status='S05_ACTUAL_WORKSPACE_RACES_REPRODUCED_AND_FIXED_IN_FIXTURE',
                 raw_catalogue=pin(raw),observations=reports,original=pin(original),patch=pin(patch),
                 exact_workspace_and_Auth_wrapper=True,modelled_report_and_actor=True,
                 exact_fixture_all22_and_data_rollback=True,actual_ERP_business_cases=0,
                 candidate_mutated=False,production_go=False)
    (HERE/'S05_ACCESSORY_REPORT_SNAPSHOT_RESULT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(receipt['status'],receipt['patch'])


if __name__=='__main__':
    main(sys.argv[1],sys.argv[2])
