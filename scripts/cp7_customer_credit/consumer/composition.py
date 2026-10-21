"""Isolated consumer draft composition, not the default owning installer.

The caller verifies/installs the qualified predecessor, owns its transaction and
rolls back every error. No connection, commit, provider or production operation
is performed here. Actual source/metadata pins come from the accepted a45084
used manifest; declarations do not qualify the new bounded consumer vertical.
"""
from hashlib import sha256
from copy import deepcopy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINS = json.loads((HERE / 'SOURCE_PINS.json').read_text())['functions']
PINS = {**PINS, **json.loads((HERE / 'SOURCE_HISTORY_PINS.json').read_text())['functions']}
SQL_FILES = ('01_dependency_graph.sql','02_operation_facts.sql','04_credit_book_bound.sql',
             '05_event_data.sql','06_access_and_requests.sql','07_locked_projection.sql',
             '08_owning_command.sql','09_deferred_closure.sql','10_capabilities.sql','11_source_history.sql')
ROOT_HELPER = 'cp7_credit._consumer_root_source_profile_v1(uuid,uuid,uuid,jsonb)'
PUBLIC = ('public.erp_cp7_get_customer_credit_review_v1(jsonb)',
          'public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)')
TABLES=('consumer_requests_v1','consumer_execution_context','consumer_operations_v1',
        'consumer_posting_scope_v1','consumer_completions_v1')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ValueError('OW04_CONSUMER_COMPOSITION_SOURCE_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


poster = load('ow04_consumer_actual_poster', HERE/'03_native_consumer_transform.py')
guard = load('ow04_consumer_predecessor_guard', REPO/'scripts/cp7_internal_guard_bundle.py')
triggers = load('ow04_consumer_source_triggers', HERE.parent/'integration/source_triggers/trigger_guard.py')
trigger_builder = load('ow04_consumer_fk_source', HERE.parent/'integration/source_triggers/build_source_pins.py')
owning = load('ow04_consumer_qualified_owning', HERE.parent/'integration/owning_bundle.py')
once = poster.native.once
source_history = load('ow04_consumer_source_history_transform', HERE/'source_history_transform.py')


def digest(value):
    return sha256(value.encode()).hexdigest()


def capture(cur, identity):
    row = cur.execute("""select pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),l.lanname,p.prokind::text,
     p.prosecdef,p.proleakproof,p.proisstrict,p.proretset,p.provolatile::text,p.proparallel::text,p.proconfig,
     pg_get_function_result(p.oid),p.prosrc,p.proacl::text[],
     (select jsonb_agg(jsonb_build_array(case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,
      pg_get_userbyid(a.grantor),a.privilege_type,a.is_grantable)order by a.grantee,a.grantor,a.privilege_type)
      from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))a)
     from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=%s::regprocedure""",(identity,)).fetchone()
    if row is None:
        raise ValueError('OW04_CONSUMER_PREDECESSOR_FUNCTION_ABSENT: '+identity)
    keys=('owner','language','kind','security_definer','leakproof','strict','returns_set','volatility','parallel','config','return_type')
    fingerprint=dict(zip(keys,row[1:12]))
    fingerprint.update(definition_sha256=digest(row[0]),privileges=sorted(row[14],key=str))
    return dict(identity=identity,definition=row[0],body=row[12],acl=row[13],fingerprint=fingerprint)


def assert_pin(captured):
    expected={**PINS[captured['identity']], 'privileges':sorted(PINS[captured['identity']]['privileges'],key=str)}
    if captured['fingerprint']!=expected:
        raise ValueError('OW04_CONSUMER_ACTUAL_PREDECESSOR_SOURCE_OR_METADATA_CHANGED: '+captured['identity'])
    if captured['definition'].count(captured['body'])!=1:
        raise ValueError('OW04_CONSUMER_CAPTURED_BODY_NOT_UNIQUE')


def derive(captures):
    if set(captures)!=set(PINS):
        raise ValueError('OW04_CONSUMER_CAPTURE_SET_CHANGED')
    for value in captures.values():
        assert_pin(value)
    result={}
    internal=captures['erp.require_internal()']['definition']
    original, probe=guard.unpatched(internal)
    tables=guard.contexts(original)
    if len(tables)!=10 or probe!=guard.probe(tables):
        raise ValueError('OW04_CONSUMER_QUALIFIED_ONE_CONTEXT_PROBE_CHANGED')
    branch=""" if exists(select 1 from cp7_credit.consumer_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.phase in('LOCKED','POSTING','MATERIALIZED','COMPLETE')
   then cp7_credit.consumer_internal_allowed_v1() else false end) then return;end if;
"""
    expanded=once(original,guard.FALLBACK,branch+guard.FALLBACK,'real consumer internal admission')
    if guard.contexts(expanded)!=tables+['cp7_credit.consumer_execution_context']:
        raise ValueError('OW04_CONSUMER_EXPANDED_TYPED_DISPATCH_CHANGED')
    result['erp.require_internal()']=guard.patched_internal(expanded)

    identity='cp7_credit.initial_base_events_v1(uuid,uuid)'
    definition=captures[identity]['definition']
    result[identity]=once(definition,' return answer;',
        " answer:=answer||cp7_credit.consumer_incoming_funding_v1(p_sale);\n"
        " select coalesce(jsonb_agg(v order by v->>'id'collate\"C\"),'[]')into answer from jsonb_array_elements(answer)v;\n return answer;",
        'actual signed incoming FUNDING')

    identity='cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'
    definition=captures[identity]['definition']
    definition=once(definition,
        "\n  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)",
        '\n ', 'bounded incoming source data admission')
    definition=once(definition,"if(p_actual->>'I')::numeric<>0 or(p_actual->>'U')::numeric<>0 then",
        "if(p_actual->>'I')::numeric<>0 then",'proved incoming U on an empty receiving family')
    start=definition.index(' -- Current materialized inspector already proves all actual signed part/J')
    end=definition.index(" select coalesce(jsonb_agg(jsonb_build_object('id',consumer.id::text",start)
    definition=definition[:start]+""" -- Every consumer has its actual immutable operation and exact named inverse.
 for ce in select *from cp7_credit.consumption_events where cohort_id=ch.id order by id loop
  perform cp7_credit.consumer_event_data_v1(ce.id);
 end loop;
"""+definition[end:]
    # Keep original route/correction, multi-cohort and fresh source/ordinal/I
    # proofs. This first vertical does not silently implement general families.
    helper=once(definition,'FUNCTION cp7_credit.assert_current_source_plan_profile(',
        'FUNCTION cp7_credit._consumer_root_source_profile_v1(','private nonrecursive root data validator')
    result[ROOT_HELPER]=helper
    result[identity]="""create or replace function cp7_credit.assert_current_source_plan_profile(
 p_sale uuid,p_root uuid,p_leaf uuid,p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $consumer_roots$
declare root uuid;actual jsonb;e record;
begin
 if(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from
   (p_sale::text,p_root::text,p_leaf::text)then raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 if jsonb_typeof(p_actual->'upstream_root_ids')is distinct from'array'
  or not(p_actual->'upstream_root_ids')@>jsonb_build_array(p_root)then raise exception 'CP7_CREDIT_CURRENT_SOURCE_ROOT_SET_REQUIRED';end if;
 for root in select value::uuid from jsonb_array_elements_text(p_actual->'upstream_root_ids')order by value loop
  actual:=case when root=p_root then p_actual else cp7_credit.current_materialized_objects(root,root,root)end;
  for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=root order by ce.id loop
   perform cp7_credit.consumer_event_data_v1(e.id);
  end loop;
  perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);
 end loop;
end $consumer_roots$;"""

    identity='cp7_credit.assert_financial_materialization_provenance(jsonb)'
    result[identity]=once(captures[identity]['definition'],
        '  else\n   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;',
        "  elsif exists(select 1 from cp7_credit.consumer_operations_v1 where id=f.id)then\n"
        "   perform cp7_credit.consumer_actual_manifest_v1(f.id);\n"
        '  else\n   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;',
        'consumer actual data marker provenance')

    identity='cp7_credit.enforce_initial_return_closure_v1()'
    prefix="""begin
 if tg_table_name in('consumption_events','financial_materializations','financial_materialization_objects')then
  select id into source_operation from cp7_credit.consumer_operations_v1 where id=
   (case when tg_table_name='financial_materialization_objects'then row->>'materialization_id'else row->>'id'end)::uuid;
  if source_operation is not null then perform cp7_credit.assert_consumer_closed_v1(source_operation);return null;end if;
 end if;
"""
    result[identity]=once(captures[identity]['definition'],'begin\n',prefix,'exact consumer deferred closure dispatch')

    identity='erp._cp7_current_credit_adjustment(uuid)'
    result[identity]=once(captures[identity]['definition'],
        "where e.journal_id=j.id and e.id=j.source_id and e.event_kind='REFUND'))then",
        """where e.journal_id=j.id and e.id=j.source_id and e.event_kind='REFUND'))
  or exists(select 1 from erp.journal_entries j where j.source_type in('CP7_CUSTOMER_CREDIT_APPLY','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')
   and not exists(select 1 from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
    join cp7_credit.return_families f on f.id=c.family_id where ce.journal_id=j.id and ce.id=j.source_id
     and((j.source_type='CP7_CUSTOMER_CREDIT_APPLY'and ce.event_kind='APPLY'and ce.amount>0 and ce.restores_event_id is null)
      or(j.source_type='CP7_CUSTOMER_CREDIT_EVENT_REVERSE'and ce.amount<0 and ce.restores_event_id is not null))))then""",
        'orphan admission before zero-participation fast path')
    result.update(source_history.derive(captures,once))
    return result


def sources():
    names=SQL_FILES+('03_native_consumer_transform.py','SOURCE_PINS.json','SOURCE_HISTORY_PINS.json',
                    'source_history_transform.py','composition.py')
    return {name:digest((HERE/name).read_text())for name in names}


def consumer_trigger_manifest():
    """Exactly seven SOURCE-declared new parent ERP FKs, not a live adoption."""
    manifest=deepcopy(triggers.declarations(REPO))
    phase=deepcopy(manifest['phases']['OW04_COMPOSED_NATIVE_EMPTY'])
    source='scripts/cp7_customer_credit/consumer/02_operation_facts.sql'
    added=trigger_builder.fk_extract((REPO/source).read_text(),source)
    expected={('cp7_credit.consumer_operations_v1',name,'erp.sales_headers')for name in
        ('source_sale_id','source_root_sale_id','source_current_leaf_id','target_sale_id','target_root_sale_id','target_current_leaf_id')}
    expected.add(('cp7_credit.consumer_completions_v1','journal_id','erp.journal_entries'))
    actual={(x['relation'],x['columns'][0],x['parent'])for x in added}
    if len(added)!=7 or actual!=expected or any(len(x['columns'])!=1 or x['parent_columns']!=['id']
            or x['update_action']!='a'or x['delete_action']!='a'or x['match_type']!='s'
            or x['deferrable']or x['initially_deferred']or not x['validated']for x in added):
        raise ValueError('OW04_CONSUMER_NATIVE_FK_SOURCE_SET_CHANGED')
    phase['foreign_keys']+=added
    manifest['phases']['OW04_CONSUMER_BOUNDED']=phase
    return manifest


def function_catalog(cur):
    return dict(cur.execute("select oid::text,encode(sha256(convert_to(to_jsonb(p)::text,'UTF8')),'hex')from pg_proc p").fetchall())


def table_catalog(cur):
    return cur.execute("""select c.relname,pg_get_userbyid(c.relowner),c.relacl::text[],c.relrowsecurity,c.relforcerowsecurity,
     (select jsonb_agg(jsonb_build_array(a.attname,a.atttypid,a.atttypmod,a.attnotnull,a.attacl::text[],
      pg_get_expr(d.adbin,d.adrelid))order by a.attnum)from pg_attribute a left join pg_attrdef d
      on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),
     (select jsonb_agg(jsonb_build_array(k.conname,k.contype::text,k.convalidated,k.condeferrable,k.condeferred,
      pg_get_constraintdef(k.oid,false))order by k.conname)from pg_constraint k where k.conrelid=c.oid),
     (select jsonb_agg(jsonb_build_array(t.tgname,t.tgenabled::text,pg_get_triggerdef(t.oid,false))order by t.tgname)
      from pg_trigger t where t.tgrelid=c.oid),
     (select jsonb_agg(jsonb_build_array(p.polname,p.polcmd::text,p.polroles::text,p.polpermissive,
      pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))order by p.polname)from pg_policy p where p.polrelid=c.oid)
     from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_credit'and c.relname=any(%s::text[])order by c.relname""",(list(TABLES),)).fetchall()


@contextmanager
def as_owner(cur,owner):
    if owner not in ('postgres','cp7_credit_write'):
        raise ValueError('OW04_CONSUMER_UNTRUSTED_PRIVATE_OWNER')
    previous=cur.execute('show role').fetchone()[0]
    cur.execute('set local role '+owner)
    try:
        yield
    finally:
        if cur.connection.info.transaction_status!=owning.TransactionStatus.INERROR:
            cur.execute("select set_config('role',%s,true)",(previous,))


def new_function_names():
    names=[]
    for name in SQL_FILES:
        text=trigger_builder.masked((HERE/name).read_text())
        names+=re.findall(r'\bcreate\s+(?:or\s+replace\s+)?function\s+([a-z0-9_]+\.[a-z0-9_]+)\s*\(',text,re.I)
    names+=['cp7_credit._consumer_root_source_profile_v1','cp7_credit._post_consumer_bound_v1']
    if len(set(names))!=len(names):
        raise ValueError('OW04_CONSUMER_NEW_FUNCTION_NAME_NOT_UNIQUE')
    return names


def install(cur):
    """Caller-owned SINGLE transaction; no fallback, partial install or commit."""
    for table in TABLES:
        if cur.execute('select to_regclass(%s)is not null',('cp7_credit.'+table,)).fetchone()[0]:
            raise ValueError('OW04_CONSUMER_ALREADY_INSTALLED')
    captures={sig:capture(cur,sig)for sig in PINS}
    catalog_before=function_catalog(cur)
    definitions=derive(captures)
    # The original raw census must pass before adding even one declared FK.
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    trigger_manifest=consumer_trigger_manifest()
    trigger_before=owning._source_trigger_capture(cur,triggers)
    triggers.validate_source(trigger_before,trigger_manifest,'OW04_COMPOSED_NATIVE_EMPTY')
    runtime_before=capture(cur,'cp7_credit.assert_source_native_trigger_census_v1()')
    source_manifest=sources()
    schema_before=cur.execute("select nspname,nspacl::text[]from pg_namespace where nspname in('public','cp7_credit')order by 1").fetchall()
    for schema in ('public','cp7_credit'):
        if cur.execute("select has_schema_privilege('cp7_credit_write',%s,'CREATE')",(schema,)).fetchone()[0]:
            raise ValueError('OW04_CONSUMER_OUTER_ROLE_ALREADY_HAS_SCHEMA_CREATE')
        cur.execute('grant create on schema '+schema+' to cp7_credit_write')
    for name in SQL_FILES:
        text=(HERE/name).read_text()
        if digest(text)!=source_manifest[name]:
            raise ValueError('OW04_CONSUMER_COMPOSITION_SOURCE_CHANGED')
        text,n=re.subn(r'do \$not_an_installer\$begin\s*raise exception \'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION\';\s*end \$not_an_installer\$;','',text)
        if n!=1:
            raise ValueError('OW04_CONSUMER_CLOSED_BARRIER_CHANGED: '+name)
        cur.execute(text)
    for schema in ('public','cp7_credit'):
        cur.execute('revoke create on schema '+schema+' from cp7_credit_write')
    if cur.execute("select nspname,nspacl::text[]from pg_namespace where nspname in('public','cp7_credit')order by 1").fetchall()!=schema_before:
        raise ValueError('OW04_CONSUMER_SCHEMA_PRIVILEGES_NOT_EXACTLY_RESTORED')
    post=captures['erp.post_journal(text,uuid,date,text,jsonb)']
    pin=post['fingerprint']
    captured=poster.native.Capture(post['identity'],post['definition'],post['body'],pin['owner'],tuple(post['acl']or()),
        pin['security_definer'],pin['volatility'],tuple(pin['config']or()))
    native_sql,native_proof=poster.derive_consumer_post(captured)
    cur.execute(native_sql)
    for identity,definition in definitions.items():
        cur.execute(definition)
        if identity==ROOT_HELPER:
            cur.execute('alter function '+identity+' owner to postgres')
            cur.execute('revoke all on function '+identity+' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write')
    trigger_after=owning._source_trigger_capture(cur,triggers)
    trigger_proof=triggers.expected_transition(trigger_before,trigger_after,trigger_manifest,
        'OW04_COMPOSED_NATIVE_EMPTY','OW04_CONSUMER_BOUNDED')
    expected_hash=cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',(triggers.canonical(trigger_after),)).fetchone()[0]
    cur.execute(triggers.render_runtime_guard(trigger_after,trigger_manifest,'OW04_CONSUMER_BOUNDED',expected_hash))
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    guard.verify(cur)
    if capture(cur,'erp.post_journal(text,uuid,date,text,jsonb)')!=post:
        raise ValueError('OW04_CONSUMER_ORIGINAL_NATIVE_POSTER_CHANGED')
    installed={sig:capture(cur,sig)for sig in definitions}
    for sig in set(captures)-{'erp.post_journal(text,uuid,date,text,jsonb)'}:
        before=captures[sig]['fingerprint'];after=installed[sig]['fingerprint']
        if {k:v for k,v in before.items()if k!='definition_sha256'}!={k:v for k,v in after.items()if k!='definition_sha256'}:
            raise ValueError('OW04_CONSUMER_PREDECESSOR_FUNCTION_METADATA_CHANGED: '+sig)
    catalog_after=function_catalog(cur)
    allowed=[sig for sig in PINS if sig!='erp.post_journal(text,uuid,date,text,jsonb)']+['cp7_credit.assert_source_native_trigger_census_v1()']
    allowed_oids={str(cur.execute('select %s::regprocedure::oid',(sig,)).fetchone()[0])for sig in allowed}
    if any(catalog_after.get(oid)!=value for oid,value in catalog_before.items()if oid not in allowed_oids):
        raise ValueError('OW04_CONSUMER_UNDECLARED_EXISTING_FUNCTION_CHANGED')
    new_oids=sorted(set(catalog_after)-set(catalog_before))
    previous=cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    try:
        new_rows=cur.execute("select p.oid::text,p.oid::regprocedure::text,n.nspname||'.'||p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=any(%s::oid[])",(new_oids,)).fetchall()
    finally:
        if cur.connection.info.transaction_status!=owning.TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true)",(previous,))
    if len(new_rows)!=len(new_function_names())or set(r[2]for r in new_rows)!=set(new_function_names()):
        raise ValueError('OW04_CONSUMER_UNDECLARED_NEW_FUNCTION_SET')
    new_functions={sig:capture(cur,sig)for _,sig,_ in new_rows}
    state=dict(classification='ISOLATED_UNQUALIFIED_BOUNDED_CONSUMER_DRAFT',captures=captures,
        installed=installed,sources=source_manifest,native_poster_proof=native_proof,
        source_trigger_manifest=trigger_manifest,source_trigger_before=trigger_before,source_trigger_after=trigger_after,
        source_trigger_transition=trigger_proof,runtime_before=runtime_before,
        runtime_after=capture(cur,'cp7_credit.assert_source_native_trigger_census_v1()'),
        catalog_before=catalog_before,catalog_after=catalog_after,new_functions=new_functions,schema_before=schema_before,
        table_catalog=table_catalog(cur),
        formal_CP7C_started=False,Native_cases_added=0,feature_complete=False,production_go=False)
    verify(cur,state)
    return state


def verify(cur,state):
    if state['sources']!=sources()or function_catalog(cur)!=state['catalog_after']:
        raise ValueError('OW04_CONSUMER_COMPOSITION_SOURCE_OR_FUNCTION_CATALOG_CHANGED')
    tables=table_catalog(cur)
    if len(tables)!=5 or tables!=state['table_catalog']:
        raise ValueError('OW04_CONSUMER_PRIVATE_TABLE_METADATA_CHANGED')
    for name,owner,acl,rls,force,*_ in tables:
        expected_owner='cp7_credit_write'if name in('consumer_requests_v1','consumer_execution_context')else'postgres'
        if owner!=expected_owner or not rls or force:
            raise ValueError('OW04_CONSUMER_PRIVATE_TABLE_OWNER_OR_RLS_CHANGED')
        for role in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                    (role,'cp7_credit.'+name)).fetchone()[0]:
                raise ValueError('OW04_CONSUMER_PRIVATE_TABLE_OUTSIDER_DML_CHANGED')
        if expected_owner=='postgres'and cur.execute("select has_table_privilege('cp7_credit_write',%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                ('cp7_credit.'+name,)).fetchone()[0]:
            raise ValueError('OW04_CONSUMER_OUTER_ROLE_CAN_ACCESS_FINANCIAL_FACTS')
    for sig,expected in {**state['installed'],**state['new_functions']}.items():
        if capture(cur,sig)!=expected:
            raise ValueError('OW04_CONSUMER_INSTALLED_FUNCTION_METADATA_CHANGED: '+sig)
    if capture(cur,'cp7_credit.assert_source_native_trigger_census_v1()')!=state['runtime_after']:
        raise ValueError('OW04_CONSUMER_NATIVE_RAW_TRIGGER_GUARD_CHANGED')
    guard.verify(cur)
    triggers.verify_unchanged(owning._source_trigger_capture(cur,triggers),state['source_trigger_after'],
        state['source_trigger_manifest'],'OW04_CONSUMER_BOUNDED')
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    for sig in state['new_functions']:
        owner=state['new_functions'][sig]['fingerprint']['owner']
        expected_owner='cp7_credit_write'if sig in ('cp7_credit.consumer_command_v1(jsonb,uuid,jsonb)',PUBLIC[1])else'postgres'
        if owner!=expected_owner:
            raise ValueError('OW04_CONSUMER_NEW_FUNCTION_OWNER_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'):
            allowed=cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]
            if allowed!=(role=='authenticated'and sig in PUBLIC):
                raise ValueError('OW04_CONSUMER_NEW_FUNCTION_OUTSIDER_EXECUTE_CHANGED: '+sig+' '+role)
    return dict(status='VERIFIED_SOURCE_AND_METADATA_NOT_NATIVE_EXECUTION',new_function_count=len(state['new_functions']),
        Native_cases_added=0,production_go=False)


def uninstall_preuse(cur,state):
    """Only after all measured cases rolled back. Used financial facts refuse."""
    verify(cur,state)
    tables=('consumer_completions_v1','consumer_posting_scope_v1','consumer_execution_context',
            'consumer_operations_v1','consumer_requests_v1')
    for name in tables:
        if cur.execute('select exists(select 1 from cp7_credit.'+name+')').fetchone()[0]:
            raise ValueError('OW04_CONSUMER_USED_INSTALLATION_REQUIRES_FINANCIAL_RECOVERY')
    for sig,value in state['captures'].items():
        if sig!='erp.post_journal(text,uuid,date,text,jsonb)':
            cur.execute(value['definition'])
    cur.execute(state['runtime_before']['definition'])
    for name in tables:
        owner='cp7_credit_write'if name in('consumer_requests_v1','consumer_execution_context')else'postgres'
        with as_owner(cur,owner):
            cur.execute('drop trigger consumer_closed on cp7_credit.'+name)
    for sig in sorted(state['new_functions'],key=lambda s:(not s.startswith('public.'),s)):
        with as_owner(cur,state['new_functions'][sig]['fingerprint']['owner']):
            cur.execute('drop function '+sig)
    for name in tables:
        owner='cp7_credit_write'if name in('consumer_requests_v1','consumer_execution_context')else'postgres'
        with as_owner(cur,owner):
            cur.execute('drop table cp7_credit.'+name)
    triggers.expected_transition(state['source_trigger_after'],owning._source_trigger_capture(cur,triggers),
        state['source_trigger_manifest'],'OW04_CONSUMER_BOUNDED','OW04_COMPOSED_NATIVE_EMPTY')
    triggers.verify_unchanged(owning._source_trigger_capture(cur,triggers),state['source_trigger_before'],
        state['source_trigger_manifest'],'OW04_COMPOSED_NATIVE_EMPTY')
    if function_catalog(cur)!=state['catalog_before']:
        raise ValueError('OW04_CONSUMER_PREUSE_FUNCTION_CATALOG_NOT_EXACTLY_RESTORED')
    if cur.execute("select nspname,nspacl::text[]from pg_namespace where nspname in('public','cp7_credit')order by 1").fetchall()!=state['schema_before']:
        raise ValueError('OW04_CONSUMER_PREUSE_SCHEMA_ACL_NOT_EXACTLY_RESTORED')
    for sig,value in state['captures'].items():
        if capture(cur,sig)!=value:
            raise ValueError('OW04_CONSUMER_PREUSE_SOURCE_NOT_EXACTLY_RESTORED: '+sig)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    return dict(status='EXACT_PREUSE_RESTORE',financial_facts_deleted=False,production_go=False)
