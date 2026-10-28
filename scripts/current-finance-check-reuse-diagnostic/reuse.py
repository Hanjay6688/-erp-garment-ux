"""Rollback-only aggregation of two identical snapshot checks, no public cache."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('retained_readonly_candidate',ROOT/'scripts/current-finance-reader-diagnostic/reader.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
spec=importlib.util.spec_from_file_location('reuse_installed_snapshot_source',HERE/'snapshot_source.py')
snapshot_source=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot_source)
SNAPSHOT='erp.get_owner_financial_snapshot_v2(date,date,date)'
OLD="""  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;"""
NEW="""  select coalesce(sum(c.issue_count) filter(where c.severity='CRITICAL'),0)::bigint,
         coalesce(sum(c.issue_count) filter(where c.severity='WARNING'),0)::bigint,
         coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name)
    filter(where c.issue_count>0),'[]'::jsonb)
  into v_critical,v_warning,v_failed_checks from erp.run_v268_financial_report_checks() c;"""

def rewrite(body):
    expected,source=snapshot_source.expected()
    if body!=expected:
        raise ValueError('SNAPSHOT_REUSE_LIVE_BODY_CHANGED: expected='+source['installed_body_sha256']+
            ' actual='+sha256(body.encode()).hexdigest()+' expected_bytes='+str(len(expected.encode()))+
            ' actual_bytes='+str(len(body.encode())))
    if body.count(OLD)!=1 or body.count('erp.run_v268_financial_report_checks()')!=2:
        raise ValueError('SNAPSHOT_REUSE_CALL_SHAPE_CHANGED')
    result=body.replace(OLD,NEW,1)
    assert result.replace(NEW,OLD,1)==body
    assert result.count('erp.run_v268_financial_report_checks()')==1
    return result

def install_for_rollback(cur):
    before=cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),'
        'p.proconfig,pg_get_functiondef(p.oid) from pg_proc p where p.oid=%s::regprocedure',(SNAPSHOT,)).fetchone()
    assert before[1:5]==('s',True,'postgres',['search_path=erp, public, pg_catalog, pg_temp'])
    body=rewrite(before[0])
    definition=before[5]
    assert definition.startswith('CREATE OR REPLACE FUNCTION erp.get_owner_financial_snapshot_v2(')
    assert definition.count(before[0])==1
    changed=definition.replace(before[0],body,1)
    patch=reader.install_for_rollback(cur)
    cur.execute(changed,prepare=False)
    after=cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),'
        'p.proconfig,pg_get_functiondef(p.oid) from pg_proc p where p.oid=%s::regprocedure',(SNAPSHOT,)).fetchone()
    assert after==(body,*before[1:5],changed)
    return dict(readonly_opening=patch,snapshot_original_body_sha256=sha256(before[0].encode()).hexdigest(),
        exact_live_body_matches_composed_official_installers=True,
        native_original_body_preserved=True,installed_source_derivation=snapshot_source.expected()[1],
        snapshot_rewritten_body_sha256=sha256(body.encode()).hexdigest(),
        snapshot_checks_before=2,snapshot_checks_after=1,
        exact_body_outside_one_aggregation_unchanged=True,authority_unchanged=True,
        no_cache_or_client_supplied_check_result=True,product_adoption=False,production_go=False)
