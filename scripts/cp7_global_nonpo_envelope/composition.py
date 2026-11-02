"""Guarded complete Global stage. Actual final-parent/input admission is closed.

No connection, commit, predecessor reinstallation or business command occurs.
The trusted caller owns the transaction. Existing eight Native owners/OIDs/raw
ACLs and all other original metadata remain exact. No new role is created.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import json,re
from . import admission,catalog_bridge,catalogue_profile,native_hooks,readonly_graph,semantic_routes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.global-guarded-installation.v1'
SCHEMAS=('cp7_global_nonpo_envelope','cp7_global_nonpo_native_graph','cp7_global_catalog_fence')
CORE_ORDER=('schema.sql','work_scope.sql','graph_helpers/authority.sql','graph_helpers/scope.sql',
    'graph_helpers/capture.sql','graph_helpers/inspect.sql','semantic_authority.sql','catalogue_fingerprint.sql',
    'derived_review.sql','derived_lock.sql')
PLATFORM_ORDER=('platform_catalog_fence.sql','platform_relation_fence.sql')


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def sql_sources():
    routes,_=semantic_routes.derive()
    return {name:(routes[name.removeprefix('derived_').removesuffix('.sql')]if name.startswith('derived_')else(HERE/name).read_text())
        for name in CORE_ORDER+PLATFORM_ORDER}


def sources():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    for name,value in manifest['files'].items():
        path=ROOT/name
        require(path.is_file()and not path.is_symlink()and pin(path.read_bytes())==value,'GLOBAL_INSTALL_SOURCE_CHANGED:'+name)
    plan=json.loads((HERE/'INSTALL_PLAN.json').read_bytes())
    require(plan['contract']==CONTRACT and plan['actual_parent_adoption']is False,'GLOBAL_INSTALL_CLOSED_PREPARATION_PLAN')
    require(plan['source_sql']=={n:pin(t.encode())for n,t in sql_sources().items()},'GLOBAL_INSTALL_EXACT_DERIVED_SOURCE_PLAN')
    definitions,routes=native_hooks.derive(native_hooks.originals())
    require(plan['native_adapter_sources']=={n:pin(t.encode())for n,t in definitions.items()}
        and plan['native_adapter_routes']==routes['source_routes']==18,'GLOBAL_INSTALL_EXACT_EIGHT_NATIVE_ADAPTER_PLAN')
    return dict(contract=CONTRACT,manifest=pin((HERE/'SOURCE.json').read_bytes()),plan=pin((HERE/'INSTALL_PLAN.json').read_bytes()),
        final_parent_head=admission.PARENT_HEAD,runtime_entry=admission.RUNTIME_ENTRY,
        complete_input_profile_pin=admission.INPUT_PROFILE_PIN,production_go=False,independent_acceptance=False)


@contextmanager
def metadata_context(cur):
    previous=cur.execute("select current_setting('search_path'),current_setting('TimeZone')").fetchone()
    cur.execute("set local search_path='';set local timezone='UTC'")
    try:yield
    finally:
        from psycopg.pq import TransactionStatus
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true),set_config('TimeZone',%s,true)",previous)


@contextmanager
def atomic(cur):
    require(not cur.connection.autocommit,'GLOBAL_INSTALL_CALLER_TRANSACTION_REQUIRED')
    cur.execute('savepoint cp7_global_envelope_stage')
    try:yield
    except BaseException:
        cur.execute('rollback to savepoint cp7_global_envelope_stage');cur.execute('release savepoint cp7_global_envelope_stage');raise
    else:cur.execute('release savepoint cp7_global_envelope_stage')


@contextmanager
def as_role(cur,role):
    from psycopg import sql
    from psycopg.pq import TransactionStatus
    require(role in('postgres','supabase_admin'),'GLOBAL_INSTALL_ONLY_DECLARED_EXISTING_OWNERS')
    previous=cur.execute('select current_user').fetchone()[0]
    if previous!=role:cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
    try:yield
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            if cur.execute('select current_user').fetchone()[0]!=previous:
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))


def trusted_installer(cur):
    require(cur.execute('select rolsuper from pg_roles where rolname=session_user').fetchone()==(True,),
        'GLOBAL_TRUSTED_MAINTENANCE_SESSION_REQUIRED_FOR_PLATFORM_BOOTSTRAP')


def capture(cur):
    """Full25 sorted key/value rows; duplicate keys are retained, never erased."""
    with metadata_context(cur):
        result={}
        for name,query in sorted(catalogue_profile.queries().items()):
            result[name]=[list(row)for row in cur.execute('select k,v from('+query+')q(k,v)order by k collate "C",v::text collate "C"').fetchall()]
        return result


def all22(value):
    result={}
    for group,rows in value.items():
        if group in catalogue_profile.EXTRA:continue
        result[group]=dict(rows);require(len(result[group])==len(rows),'GLOBAL_ORIGINAL_ALL22_DUPLICATE_KEY:'+group)
    require(len(result)==22,'GLOBAL_ORIGINAL_ALL22_REQUIRED');return result


def fingerprint(cur,value):
    from psycopg.types.json import Jsonb
    preimage=cur.execute('select %s::jsonb::text',(Jsonb(value),)).fetchone()[0]
    return dict(contract='cp7.global-catalogue-fingerprint.v1',groups=25,
        sha256=sha256(preimage.encode()).hexdigest(),counts={k:len(v)for k,v in value.items()})


def native_identity(cur,signatures):
    result={}
    for sig in signatures:
        row=cur.execute("""select p.oid,p.proacl::text,pg_get_userbyid(p.proowner),n.nspname,
          pg_get_userbyid(n.nspowner),n.nspacl::text,has_schema_privilege(p.proowner,n.oid,'CREATE')
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure""",(sig,)).fetchone()
        require(row is not None and row[2]=='postgres','GLOBAL_EXACT_EXISTING_POSTGRES_OWNING_FUNCTION_REQUIRED:'+sig)
        result[sig]=list(row)
    return result


def replace_native(cur,definitions,identity):
    from psycopg import sql
    for sig,definition in definitions.items():
        old=identity[sig];require(native_identity(cur,[sig])[sig]==old,'GLOBAL_NATIVE_RAW_AUTHORITY_CHANGED:'+sig)
        # Use maintenance only for a temporary schema CREATE lease when its
        # existing owner is not postgres. No SET/INHERIT membership is added.
        if not old[6]:cur.execute(sql.SQL('grant create on schema {} to postgres').format(sql.Identifier(old[3])))
        with as_role(cur,'postgres'):cur.execute(definition,prepare=False)
        if not old[6]:cur.execute(sql.SQL('revoke create on schema {} from postgres').format(sql.Identifier(old[3])))
        require(native_identity(cur,[sig])[sig]==old,'GLOBAL_NATIVE_OID_RAW_ACL_OR_SCHEMA_LEASE_NOT_RESTORED:'+sig)


def normalize_private(cur,plan):
    from psycopg import sql
    with as_role(cur,'postgres'):
        for sig,row in plan['functions'].items():
            if row['owner']!='postgres':continue
            grantees=cur.execute("""select distinct a.grantee from pg_proc p
              cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))a
              where p.oid=%s::regprocedure and a.grantee<>p.proowner""",(sig,)).fetchall()
            for grantee, in grantees:
                role=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
                cur.execute(sql.SQL('revoke all on function {} from {}').format(sql.SQL(sig),sql.Identifier(role)if grantee else sql.SQL('PUBLIC')))
        for table in plan['tables']:
            grantees=cur.execute("""select distinct a.grantee from pg_class c
              cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner)))a
              where c.oid=%s::regclass and a.grantee<>c.relowner""",(table,)).fetchall()
            for grantee, in grantees:
                role=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
                cur.execute(sql.SQL('revoke all on table {} from {}').format(sql.SQL(table),sql.Identifier(role)if grantee else sql.SQL('PUBLIC')))
        for schema in SCHEMAS[:2]:
            grantees=cur.execute("""select distinct a.grantee from pg_namespace n
              cross join lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a
              where n.nspname=%s and a.grantee<>n.nspowner""",(schema,)).fetchall()
            for grantee, in grantees:
                role=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
                cur.execute(sql.SQL('revoke all on schema {} from {}').format(sql.Identifier(schema),sql.Identifier(role)if grantee else sql.SQL('PUBLIC')))


def transition(before,after,definitions,plan):
    old,new=all22(before),all22(after)
    for group in catalogue_profile.EXTRA:require(after[group]==before[group],'GLOBAL_EXISTING_DISPATCH_AUTHORITY_CHANGED:'+group)
    for group in old:
        for key in set(old[group])|set(new[group]):
            left,right=old[group].get(key),new[group].get(key)
            if left==right:continue
            if group=='functions'and key in definitions and left is not None and right is not None:
                require(right[0]==definitions[key]and right[1:]==left[1:],'GLOBAL_ONLY_DECLARED_NATIVE_BODY_MAY_CHANGE:'+key);continue
            require(left is None and right is not None,'GLOBAL_EXISTING_UNDECLARED_CATALOGUE_CHANGE:'+group+':'+key)
            if group=='schemas'and key in SCHEMAS:continue
            if group=='functions'and key in plan['functions']:continue
            if group=='relations'and(key in plan['tables']or right[1]=='i'and key in plan['index_relations']):continue
            if group in('columns','constraints','triggers')and key.split(':',1)[0]in plan['tables']:continue
            if group=='indexes'and key in plan['index_relations']:continue
            if group in('types','type_implementation')and key in plan['types']:continue
            raise ValueError('GLOBAL_UNDECLARED_NEW_CATALOGUE_OBJECT:'+group+':'+key)
    require(set(new['functions'])-set(old['functions'])==set(plan['functions']),'GLOBAL_EXACT_NEW_SIXTEEN_FUNCTION_SET')
    require(set(new['schemas'])-set(old['schemas'])==set(SCHEMAS),'GLOBAL_EXACT_NEW_THREE_SCHEMA_SET')
    require(set(k for k,row in new['relations'].items()if row[1]in('r','p'))-set(k for k,row in old['relations'].items()if row[1]in('r','p'))==set(plan['tables']),'GLOBAL_EXACT_NEW_THREE_TABLE_SET')
    require(set(new['columns'])-set(old['columns'])==set(plan['columns']),'GLOBAL_EXACT_NEW_DECLARED_COLUMN_SET')
    added_triggers={k:new['triggers'][k]for k in set(new['triggers'])-set(old['triggers'])}
    require({k for k,row in added_triggers.items()if row[0]is False}=={t['relation']+':'+t['name']for t in plan['triggers']},'GLOBAL_EXACT_NEW_THREE_CUSTOM_TRIGGER_SET')
    internal=[row for row in added_triggers.values()if row[0]is True]
    require(len(internal)==4*plan['foreign_key_count']and all(row[15]in plan['tables']and row[8].split('(')[0].rsplit('.',1)[-1].strip('"').startswith('RI_FKey_')for row in internal),'GLOBAL_ONLY_DECLARED_NEW_INTERNAL_FK_TRIGGERS')
    require(len(new['constraints'])-len(old['constraints'])==plan['constraint_count'],'GLOBAL_EXACT_DECLARED_CONSTRAINT_COUNT')
    require(len(new['indexes'])-len(old['indexes'])==plan['index_count'],'GLOBAL_EXACT_DECLARED_INDEX_COUNT')


def relation_metadata(cur,names):
    result=[]
    require(isinstance(names,list)and len(names)==len(set(names))and names==sorted(names),'GLOBAL_REVIEWED_DISTINCT_SORTED_RELATION_NAMES_REQUIRED')
    for name in names:
        require(isinstance(name,str)and re.fullmatch(r'[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*',name)and not name.startswith('pg_'),
            'GLOBAL_REVIEWED_APPLICATION_RELATION_NAME_REQUIRED')
        row=cur.execute("""select n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
          pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
          case when c.relacl is null then null else to_jsonb(array(select a::text from unnest(c.relacl)a order by a::text collate "C"))end
          from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname||'.'||c.relname=%s""",(name,)).fetchone()
        require(row is not None and row[2]in('r','p'),'GLOBAL_REVIEWED_PHYSICAL_RELATION_REQUIRED:'+name);result.append(list(row))
    return result


def install(cur,parent_receipt_raw,input_profile_raw):
    source=sources();parent,inputs=admission.runtime_admission(parent_receipt_raw,input_profile_raw)
    with atomic(cur),metadata_context(cur):
        trusted_installer(cur);before=capture(cur);current=all22(before)
        # Bind the noncircular SQL/adapter plan. The admission source itself
        # contains INPUT_PROFILE_PIN and cannot be part of its own preimage.
        require(inputs.get('installation_plan')==source['plan']and inputs.get('parent_catalogue_fingerprint')==fingerprint(cur,before),
            'GLOBAL_EXACT_CURRENT_PARENT_AND_REVIEWED_MODULE_REQUIRED')
        require(not any(n in current['schemas']for n in SCHEMAS),'GLOBAL_EXISTING_MODULE_REFUSE_TO_TOUCH')
        readonly_graph.compare_current(current)
        originals=native_hooks.originals();definitions,_=native_hooks.derive({n:current['functions'].get(n)for n in originals})
        for columns in json.loads((HERE/'NATIVE_SCOPE_WORK_REFERENCE.json').read_bytes())['columns'].values():
            for key,row in columns.items():require(current['columns'].get(key)==row,'GLOBAL_NATIVE_WORK_COLUMN_PROFILE_CHANGED:'+key)
        identity=native_identity(cur,definitions);plan=json.loads((HERE/'INSTALL_PLAN.json').read_bytes());texts=sql_sources()
        with as_role(cur,'postgres'):
            cur.execute('create schema cp7_global_nonpo_native_graph authorization postgres')
            for name in CORE_ORDER:cur.execute(texts[name],prepare=False)
        for name in PLATFORM_ORDER:
            with as_role(cur,'supabase_admin'):cur.execute(texts[name],prepare=False)
        normalize_private(cur,plan);replace_native(cur,definitions,identity)
        # Finish DDL before freezing metadata. A fresh permanent-XID drain
        # rejects earlier uncommitted catalog writers; no snapshot-xip shortcut.
        catalogs=cur.execute('select cp7_global_catalog_fence.lock_v1()').fetchone()[0]
        require(not cur.execute("select 1 from pg_locks where locktype='transactionid'and mode='ExclusiveLock'and granted and pid is distinct from pg_backend_pid()limit 1").fetchone(),
            'GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN')
        after=capture(cur);transition(before,after,definitions,plan)
        required=set(json.loads((HERE/'SYNTAX_AND_SOURCE_CONTROLS.json').read_bytes())['required_actual_accepted15a_relation_keys'])|set(plan['tables'])
        require(required<=set(inputs.get('relations',[])),'GLOBAL_COMPLETE_REVIEWED_RELATION_PROFILE_REQUIRED')
        relations=relation_metadata(cur,inputs['relations']);fp=fingerprint(cur,after)
        require(cur.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]==fp,'GLOBAL_INDEPENDENT_FULL25_FINGERPRINT_MISMATCH')
        authority,preimage=cur.execute("select a,a::text from(select cp7_global_nonpo_envelope.semantic_authority_v1(cp7_global_nonpo_native_graph.authority_v1())a)s").fetchone()
        require(authority.get('known_functions_exact')is True and authority.get('new_private_acl_closed')is True and authority.get('view',{}).get('exact_known_source')is True,'GLOBAL_CURRENT_COMPLETE_NATIVE_AUTHORITY_REQUIRED')
        authority_sha=sha256(preimage.encode()).hexdigest()
        wrapper=dict(contract='cp7.global-parent-and-catalogue-profile.v1',accepted_parent=parent,catalogue_fingerprint=fp,
            reviewed_input_profile_pin=pin(input_profile_raw),module_manifest=source['manifest'])
        sealed=dict(parent_head=parent['head'],parent_tree=parent['tree'],actual_parent_root_receipt=wrapper,
            expected_catalogs=catalogs,expected_relations=relations,native_authority_sha256=authority_sha)
        profile_id=digest(sealed)
        from psycopg.types.json import Jsonb
        with as_role(cur,'postgres'):
            cur.execute('insert into cp7_global_nonpo_envelope.profiles(id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)values(%s,%s,%s,%s,%s,%s,%s)',
                (profile_id,parent['head'],parent['tree'],Jsonb(wrapper),Jsonb(catalogs),Jsonb(relations),authority_sha))
            cur.execute('select cp7_global_nonpo_envelope.lock_v1(%s)',(profile_id,))
        state=dict(contract=CONTRACT,sources=source,parent=parent,inputs=inputs,before=before,after=after,
            originals={n:r[0]for n,r in originals.items()},definitions=definitions,native_identity=identity,
            plan=plan,profile_id=profile_id,sealed=sealed)
        state['sha256']=digest(state);verify(cur,state);return state


def verify(cur,state):
    require(state.get('contract')==CONTRACT and state.get('sha256')==digest({k:v for k,v in state.items()if k!='sha256'}),'GLOBAL_INSTALL_STATE_CHANGED')
    require(state['sources']==sources(),'GLOBAL_INSTALLED_SOURCE_CHANGED')
    with metadata_context(cur):
        require(capture(cur)==state['after'],'GLOBAL_COMPLETE_INSTALLED_FULL25_CATALOGUE_CHANGED')
        require(native_identity(cur,state['definitions'])==state['native_identity'],'GLOBAL_NATIVE_OID_RAW_AUTHORITY_CHANGED')
        rows=cur.execute('select to_jsonb(p)-\'sealed_at\'from cp7_global_nonpo_envelope.profiles p').fetchall()
        require(len(rows)==1 and rows[0][0]==({'id':state['profile_id']}|state['sealed']),'GLOBAL_SEALED_PROFILE_ROW_CHANGED')
        catalogue=all22(state['after'])
        for sig,expected in state['plan']['functions'].items():
            row=cur.execute("select encode(sha256(convert_to(p.prosrc,'UTF8')),'hex'),pg_get_userbyid(p.proowner),l.lanname,p.provolatile::text,p.prosecdef,p.proretset,p.proconfig from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=%s::regprocedure",(sig,)).fetchone()
            require(row is not None and list(row)==[expected[k]for k in('body_sha256','owner','language','volatility','security_definer','returns_set','config')],'GLOBAL_EXACT_NEW_FUNCTION_SOURCE_AUTHORITY_REQUIRED:'+sig)
            acl=catalogue['functions'][sig][18]
            require({tuple(x)for x in acl}=={(expected['owner'],expected['owner'],'EXECUTE',False)}|({('postgres','supabase_admin','EXECUTE',False)}if expected['owner']=='supabase_admin'else set()),'GLOBAL_EXACT_NEW_FUNCTION_ACL_REQUIRED:'+sig)
        for table in state['plan']['tables']:
            row=catalogue['relations'][table]
            require(row[0]=='postgres'and row[3]is True and all(x[0]=='postgres'and x[1]=='postgres'for x in row[12]),'GLOBAL_PRIVATE_TABLE_OWNER_RLS_OR_ACL_CHANGED:'+table)
    return dict(contract=CONTRACT,new_private_functions=16,Native_adapters=8,full25_verified=True,
        actual_business_qualification=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    from psycopg import sql
    with atomic(cur),metadata_context(cur):
        trusted_installer(cur);verify(cur,state)
        with as_role(cur,'postgres'):
            cur.execute('select cp7_global_nonpo_envelope.lock_v1(%s)',(state['profile_id'],))
        for table in state['plan']['tables']:
            if table.endswith('.profiles'):continue
            require(not cur.execute(sql.SQL('select exists(select 1 from {} limit 1)').format(sql.SQL(table))).fetchone()[0],
                'GLOBAL_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:'+table)
        replace_native(cur,state['originals'],state['native_identity'])
        # No CASCADE or DROP OWNED. Profile metadata is removed only with the
        # unused module; immutable completion/work histories are never erased.
        with as_role(cur,'postgres'):
            for trigger in state['plan']['triggers']:
                cur.execute(sql.SQL('drop trigger {} on {}').format(sql.Identifier(trigger['name']),sql.SQL(trigger['relation'])))
        with as_role(cur,'supabase_admin'):cur.execute(catalog_bridge.inverse_sql(),prepare=False)
        with as_role(cur,'postgres'):
            cur.execute('drop function '+','.join(sig for sig,row in state['plan']['functions'].items()if row['owner']=='postgres'))
            cur.execute('drop table '+','.join(state['plan']['tables']))
            cur.execute('drop schema cp7_global_nonpo_native_graph;drop schema cp7_global_nonpo_envelope',prepare=False)
        require(capture(cur)==state['before'],'GLOBAL_PREUSE_FULL25_NOT_EXACTLY_RESTORED')
        require(native_identity(cur,state['originals'])==state['native_identity'],'GLOBAL_PREUSE_NATIVE_RAW_AUTHORITY_CHANGED')
        return dict(full25_and_Native_raw_authority_restored=True,used_rows_removed=False,
            cascade_or_DROP_OWNED_used=False,production_go=False,independent_acceptance=False)
