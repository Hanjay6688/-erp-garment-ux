"""Capture complete actual composite-parent catalogues; execute no business."""
from pathlib import Path
import importlib.util
import json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='D1_E_SKU_ACTUAL_PARENT_CATALOGUE_RAW_ACL_SOURCE_ONLY'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def scheduler_quiet(url):
    return load('catalogue_retained_vendor_scheduler',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def exercise(conn,cur,database,url,report,state):
    stage=load('catalogue_actual_stage',HERE/'stage.py')
    cc=load('catalogue_actual_context_reader',HERE/'context_catalog.py')
    if conn.info.host not in('127.0.0.1','localhost')or conn.info.port!=54322:
        raise ValueError('DE_SKU_CATALOGUE_LOCAL_DISPOSABLE_ONLY')
    if cur.execute('select current_database()').fetchone()!=('cp6_rollback',):raise ValueError('DE_SKU_CATALOGUE_EXACT_DATABASE_REQUIRED')
    proof=stage.verify(cur,state);*_,catalog=stage.runtime()
    before=dict(catalog=catalog._catalog_rows(cur),data_and_sequences=catalog._data(cur))
    inventory=json.loads((HERE/'CONTEXT_INVENTORY.json').read_bytes())
    expected=set(inventory['actual_common51'])|{
        'cp7_credit_correction_de.work_v1','cp7_credit_correction_de.posting_v1',
        'cp7_credit_note_carry_de.work_v1','cp7_sku_conversion.execution_v1'}
    context=cc.select(before['catalog'])
    if set(context['names'])!=expected or len(expected)!=55:raise ValueError('DE_SKU_CATALOGUE_EXACT55_CONTEXTS_REQUIRED')
    tables=sorted(expected);schemas=sorted({n.split('.',1)[0]for n in tables})
    raw_authority=dict(
        schemas=cur.execute('select nspname,pg_get_userbyid(nspowner),nspacl::text from pg_namespace where nspname=any(%s)order by nspname',(schemas,)).fetchall(),
        relations=cur.execute("select n.nspname||'.'||c.relname,pg_get_userbyid(c.relowner),c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname||'.'||c.relname=any(%s)order by 1",(tables,)).fetchall(),
        columns=cur.execute("select n.nspname||'.'||c.relname,a.attnum,a.attname,a.attacl::text from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname||'.'||c.relname=any(%s)and a.attnum>0 and not a.attisdropped order by 1,2",(tables,)).fetchall(),
        effective_role_table_privileges=cur.execute("select r.rolname,t.name,p.privilege,has_table_privilege(r.oid,t.name,p.privilege)from pg_roles r cross join unnest(%s::text[])t(name)cross join unnest(array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'])p(privilege)order by 1,2,3",(tables,)).fetchall())
    hooks=('cp7_credit_correction_de.quote_v1(jsonb)','cp7_credit_correction_de.prepare_v1(jsonb,uuid,text,jsonb)',
           'cp7_credit_correction_de.finish_v1(jsonb)','cp7_credit_note_carry_de.basis_v1(uuid)',
           'cp7_credit_note_carry_de.prepare_v1(jsonb,uuid,text,uuid,jsonb)','cp7_credit_note_carry_de.finish_v1(jsonb)',
           'cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)','cp7_credit.source_request_finish_v1(uuid)')
    hook_rows={sig:before['catalog']['functions'][sig]for sig in hooks}
    after=dict(catalog=catalog._catalog_rows(cur),data_and_sequences=catalog._data(cur))
    if before!=after:raise ValueError('DE_SKU_CATALOGUE_READ_CHANGED_ACTUAL_CATALOG_ROWS_OR_SEQUENCES')
    report.update(status='PASS',classification='ACTUAL_D1_E_SKU_INSTALL_PREUSE_CATALOGUE_ONLY',
        actual_layer_catalogues=state['installed_layer_catalogues'],actual_layer_proofs=state['actual_layer_proofs'],
        actual_composite_catalogue=before['catalog'],actual_context55=context,actual_raw_context_authority=raw_authority,
        current_eight_hook_rows=hook_rows,read_before=before,read_after=after,
        read_complete_noeffect=True,preuse_catalogue_qualified=True,verification=proof,
        actual_business_cases=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        used_guard_business_witness_executed=False,global_bridge_installed=False,S03_S05_installed=False,
        production_go=False,independent_acceptance=False)
    conn.rollback()
