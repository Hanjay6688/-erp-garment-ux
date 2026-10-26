"""Rollback-only reuse of official readiness within one date-bound report.

Original Native snapshot/preflight/close commands stay unchanged. One private
date-only sibling returns the unchanged snapshot and official preflight using
the readiness it just calculated. No caller supplies results or cache keys.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
reader=load('retained_readonly_candidate',ROOT/'scripts/current-finance-reader-diagnostic/reader.py')
snapshot_source=load('installed_readiness_source',HERE/'readiness_source.py')
SNAPSHOT='erp.get_owner_financial_snapshot_v2(date,date,date)'
PREFLIGHT='erp.accounting_close_preflight_v1(date)'
WORKSPACE='cp7_finance.workspace(jsonb)'
PRIVATE='cp7_finance.read_snapshot_readiness_diagnostic_v1(date,date,date)'
PRIVATE_NAME=PRIVATE.split('(')[0]
CLOSE_COMMANDS=('erp.close_accounting_through(date,text)','erp.reopen_accounting_through(date,text)')
OLD_SNAPSHOT=' snapshot:=erp.get_owner_financial_snapshot_v2(from_day,to_day,as_of);'
NEW_SNAPSHOT=' shared_report:='+PRIVATE_NAME+"(from_day,to_day,as_of);\n snapshot:=shared_report->'snapshot';"
OLD_PREFLIGHT=" if erp.has_permission('finance.period_close.manage') then preflight:=erp.accounting_close_preflight_v1(as_of);end if;"
NEW_PREFLIGHT=" if erp.has_permission('finance.period_close.manage') then preflight:=shared_report->'close_preflight';end if;"
READINESS='erp.period_readiness_v1(p_through,erp.period_completeness_from_v1())'

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('READINESS_REUSE_ANCHOR_CHANGED')
    return text.replace(old,new,1)

def exact(body,kind):
    expected,source=snapshot_source.expected()
    if body!=expected[kind]:raise ValueError('READINESS_REUSE_LIVE_BODY_CHANGED:'+kind+
        ':expected='+sha256(expected[kind].encode()).hexdigest()+':actual='+sha256(body.encode()).hexdigest())
    return source

def sibling_body(snapshot,preflight):
    exact(snapshot,'snapshot');exact(preflight,'preflight')
    if snapshot.count('erp.period_readiness_v1(')!=1 or snapshot.count('erp.run_v268_financial_report_checks()')!=1:
        raise ValueError('READINESS_REUSE_CURRENT_ENGINE_SHAPE_CHANGED')
    body=once(snapshot,'declare\n','declare\n  d17_snapshot jsonb;d17_preflight jsonb:=null;\n')
    body=once(body,'  return jsonb_build_object(\n','  d17_snapshot:=jsonb_build_object(\n')
    # A nested block preserves every official preflight statement, including
    # its own access/null-date checks, close-state read and allowed-date rule.
    nested=once(preflight,'return '+READINESS,'d17_preflight:=v_readiness').replace('p_through','p_as_of')
    if 'p_through'in nested or READINESS in nested:raise ValueError('READINESS_REUSE_PREFLIGHT_SHAPE_CHANGED')
    tail="\n  if erp.has_permission('finance.period_close.manage') then\n"+nested.strip()+";\n  end if;\n  return jsonb_build_object('snapshot',d17_snapshot,'close_preflight',d17_preflight);\nend\n"
    if not body.endswith('\nend\n'):raise ValueError('READINESS_REUSE_REPORT_RETURN_CHANGED')
    return body[:-len('\nend\n')]+tail

def rewrite(body):
    exact(body,'workspace')
    out=once(body,'snapshot jsonb;preflight jsonb:=null;','snapshot jsonb;preflight jsonb:=null;shared_report jsonb;')
    out=once(out,OLD_SNAPSHOT,NEW_SNAPSHOT)
    return once(out,OLD_PREFLIGHT,NEW_PREFLIGHT)

def definition(snapshot,preflight):
    return ('create function '+PRIVATE_NAME+'(p_from date,p_to date,p_as_of date)returns jsonb\n'
        "language plpgsql stable security definer set search_path=erp, public, pg_catalog, pg_temp as $readiness$"+
        sibling_body(snapshot,preflight)+'$readiness$;')

def row(cur,signature):
    return cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),p.proconfig,pg_get_functiondef(p.oid) '
        'from pg_proc p where p.oid=%s::regprocedure',(signature,)).fetchone()

def install_for_rollback(cur):
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    assert cur.execute('select to_regprocedure(%s)',(PRIVATE,)).fetchone()[0]is None
    snapshot,preflight,workspace=(row(cur,s)for s in(SNAPSHOT,PREFLIGHT,WORKSPACE))
    close_commands={signature:row(cur,signature)for signature in CLOSE_COMMANDS}
    source=exact(snapshot[0],'snapshot');exact(preflight[0],'preflight');exact(workspace[0],'workspace')
    assert snapshot[1:5]==('s',True,'postgres',['search_path=erp, public, pg_catalog, pg_temp'])
    assert preflight[1:5]==('s',True,'postgres',['search_path=""'])
    assert workspace[1:5]==('s',False,'cp7_finance_read',['search_path=""','TimeZone=UTC','jit=off'])
    body=rewrite(workspace[0]);assert workspace[5].count(workspace[0])==1
    changed=workspace[5].replace(workspace[0],body,1)
    opening=reader.install_for_rollback(cur)
    cur.execute(definition(snapshot[0],preflight[0]),prepare=False)
    cur.execute('alter function '+PRIVATE+' owner to postgres')
    cur.execute('revoke all on function '+PRIVATE+' from public,anon,authenticated,service_role,cp7_capture,cp7_finance_read')
    cur.execute('grant execute on function '+PRIVATE+' to cp7_finance_read')
    cur.execute(changed,prepare=False)
    for role in('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,PRIVATE)).fetchone()[0]
    assert cur.execute("select has_function_privilege('cp7_finance_read',%s,'EXECUTE')",(PRIVATE,)).fetchone()[0]
    assert row(cur,SNAPSHOT)==snapshot and row(cur,PREFLIGHT)==preflight
    assert {signature:row(cur,signature)for signature in CLOSE_COMMANDS}==close_commands
    assert row(cur,WORKSPACE)==(body,*workspace[1:5],changed)
    return dict(readonly_opening=opening,strategy='SAME_REPORT_OFFICIAL_READINESS',
        snapshot_original_body_sha256=sha256(snapshot[0].encode()).hexdigest(),
        exact_live_body_matches_composed_official_installers=True,installed_source_derivation=source,
        original_Native_snapshot_and_preflight_unchanged=True,original_close_commands_unchanged=True,
        original_close_command_sha256={signature:sha256(value[5].encode()).hexdigest()for signature,value in close_commands.items()},
        private_date_only_helper=True,private_helper_only_finance_reader=True,
        original_preflight_permission_and_rules_preserved=True,no_cache_or_client_supplied_check_result=True,
        report_readiness_calls_before=2,report_readiness_calls_after=1,
        workspace_before_sha256=sha256(workspace[0].encode()).hexdigest(),workspace_after_sha256=sha256(body.encode()).hexdigest(),
        authority_unchanged=True,product_adoption=False,production_go=False)
