"""Guarded complete FG/Mandor stage; its final accepted-parent gate stays closed.

No connection, commit, predecessor reinstall or business command is performed.
The caller supplies the trusted installation cursor and owns its transaction.
Native bodies are replaced only as their verified existing owners. Temporary
CREATE belongs to those owners, never to a browser or ordinary product caller.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import ast,json,re
from . import admission,facade_install,native_dispatch,native_payment_routes,native_sales_routes,command_guard_routes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA='cp7_mandor_shop'
ROLE='cp7_mandor_shop_api'
CONTRACT='cp7.mandor-shop-guarded-installation.v1'
ORDER=('schema.sql','events.sql','buyers.sql','sale_identity.sql','allocation.sql',
       'offset_projection.sql','payment_owner.sql','payment_guards.sql','command_guards.sql')
ORIGINAL_QUERIES=dict(bytes=19828,sha256='a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00')


def require(v,message):
    if not v:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def sources():
    m=json.loads((HERE/'SOURCE.json').read_bytes())
    for name,value in m['files'].items():
        path=ROOT/name
        require(path.is_file()and not path.is_symlink()and pin(path.read_bytes())==value,'MANDOR_INSTALL_SOURCE_CHANGED:'+name)
    p=json.loads((HERE/'INSTALL_PLAN.json').read_bytes())
    require(p['contract']==CONTRACT and p['actual_parent_adoption']is False,'MANDOR_INSTALL_CLOSED_PREPARATION_PLAN')
    return dict(contract=CONTRACT,manifest=pin((HERE/'SOURCE.json').read_bytes()),plan=pin((HERE/'INSTALL_PLAN.json').read_bytes()),
        actual_final_parent_admission=admission.PARENT_HEAD,runtime_entry=admission.RUNTIME_ENTRY,
        production_go=False,independent_acceptance=False)


def queries():
    p=ROOT/'scripts/cp7_ow04_restore_bundle.py';raw=p.read_bytes()
    require(pin(raw)==ORIGINAL_QUERIES,'MANDOR_INSTALL_ORIGINAL_ALL22_QUERY_SOURCE')
    nodes=[]
    for n in ast.parse(raw).body:
        if isinstance(n,ast.FunctionDef)and n.name=='_acl':nodes.append(n)
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('NAMESPACE','QUERIES')for t in n.targets):nodes.append(n)
    env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':inert-catalog-query-strings','exec'),env)
    require(len(env['QUERIES'])==22,'MANDOR_INSTALL_ALL22_REQUIRED');return env['QUERIES']


@contextmanager
def metadata_context(cur):
    previous=cur.execute("select current_setting('search_path'),current_setting('TimeZone')").fetchone()
    cur.execute("set local search_path='';set local timezone='UTC'")
    try:yield
    finally:
        from psycopg.pq import TransactionStatus
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true),set_config('TimeZone',%s,true)",previous)


def capture(cur):
    with metadata_context(cur):
        value={}
        for name,query in queries().items():
            rows=cur.execute(query).fetchall();value[name]=dict(rows)
            require(len(value[name])==len(rows),'MANDOR_INSTALL_NO_DUPLICATE_CATALOG_KEY:'+name)
        return value


@contextmanager
def atomic(cur):
    require(not cur.connection.autocommit,'MANDOR_INSTALL_CALLER_TRANSACTION_REQUIRED')
    cur.execute('savepoint cp7_mandor_shop_stage')
    try:yield
    except BaseException:
        cur.execute('rollback to savepoint cp7_mandor_shop_stage');cur.execute('release savepoint cp7_mandor_shop_stage');raise
    else:cur.execute('release savepoint cp7_mandor_shop_stage')


def trusted_installer(cur):
    # Native owner roles in the actual accepted catalogue have no postgres SET
    # membership. Reuse the existing trusted maintenance installation plane;
    # do not solve this by granting broad role memberships to product users.
    row=cur.execute("select current_user,session_user,(select rolsuper from pg_roles where rolname=session_user)").fetchone()
    require(row[2]is True,'MANDOR_TRUSTED_MAINTENANCE_SESSION_REQUIRED_FOR_EXISTING_OWNERS')
    return row[0]


@contextmanager
def as_role(cur,role,allowed):
    from psycopg import sql
    from psycopg.pq import TransactionStatus
    require(role in allowed,'MANDOR_INSTALL_UNDECLARED_DDL_ROLE:'+role)
    previous=cur.execute('select current_user').fetchone()[0]
    if role!=previous:cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
    try:yield
    finally:
        if role!=previous and cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))


def native_identity(cur,signatures):
    with metadata_context(cur):
        result={}
        for sig in signatures:
            row=cur.execute("""select p.oid,p.proacl::text,pg_get_userbyid(p.proowner),n.nspname,
              pg_get_userbyid(n.nspowner),n.nspacl::text,has_schema_privilege(p.proowner,n.oid,'CREATE')
              from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure""",(sig,)).fetchone()
            require(row is not None,'MANDOR_NATIVE_ORIGINAL_MISSING:'+sig);result[sig]=list(row)
        return result


def replace_native(cur,definitions,identity):
    from psycopg import sql
    for sig,definition in definitions.items():
        old=identity[sig];owner,namespace,schema_owner,raw_schema,can_create=old[2:]
        current=native_identity(cur,[sig])[sig]
        require(current==old,'MANDOR_NATIVE_OWNER_OID_RAW_ACL_OR_SCHEMA_CHANGED:'+sig)
        allowed={owner,schema_owner,'postgres'}
        if not can_create:
            with as_role(cur,schema_owner,allowed):
                cur.execute(sql.SQL('grant create on schema {} to {}').format(sql.Identifier(namespace),sql.Identifier(owner)))
        with as_role(cur,owner,allowed):cur.execute(definition,prepare=False)
        if not can_create:
            with as_role(cur,schema_owner,allowed):
                cur.execute(sql.SQL('revoke create on schema {} from {}').format(sql.Identifier(namespace),sql.Identifier(owner)))
        require(native_identity(cur,[sig])[sig]==old,'MANDOR_NATIVE_OID_RAW_ACL_OR_SCHEMA_LEASE_NOT_RESTORED:'+sig)


def normalize_private(cur,plan):
    from psycopg import sql
    with as_role(cur,'postgres',{'postgres'}),metadata_context(cur):
        for sig in plan['private_functions']:
            row=cur.execute("select pg_get_userbyid(proowner)from pg_proc where oid=%s::regprocedure",(sig,)).fetchone()
            require(row==('postgres',),'MANDOR_ONLY_NEW_PRIVATE_OWNER_NORMALIZATION:'+sig)
            grantees=cur.execute("""select distinct a.grantee from pg_proc p
              cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))a
              where p.oid=%s::regprocedure and a.grantee<>p.proowner""",(sig,)).fetchall()
            for grantee, in grantees:
                name=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
                grantee_sql=sql.SQL('PUBLIC')if not grantee else sql.Identifier(name)
                cur.execute(sql.SQL('revoke all on function {} from {}').format(sql.SQL(sig),grantee_sql))
            for role in plan['private_execute_grants'].get(sig,[]):
                cur.execute(sql.SQL('grant execute on function {} to {}').format(sql.SQL(sig),sql.Identifier(role)))
        for table in plan['tables']:
            grantees=cur.execute("""select distinct a.grantee from pg_class c
              cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner)))a
              where c.oid=%s::regclass and a.grantee<>c.relowner""",(table,)).fetchall()
            schema,name=table.split('.',1)
            for grantee, in grantees:
                role=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
                cur.execute(sql.SQL('revoke all on table {} from {}').format(sql.Identifier(schema,name),
                    sql.Identifier(role)if grantee else sql.SQL('PUBLIC')))
        # Only the newly created private schema is normalized. Existing schema
        # grants and default privileges are never rewritten.
        grantees=cur.execute("""select distinct a.grantee from pg_namespace n
          cross join lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a
          where n.nspname=%s and a.grantee<>n.nspowner""",(SCHEMA,)).fetchall()
        for grantee, in grantees:
            name=cur.execute('select pg_get_userbyid(%s)',(grantee,)).fetchone()[0]if grantee else None
            cur.execute(sql.SQL('revoke all on schema {} from {}').format(sql.Identifier(SCHEMA),sql.Identifier(name)if grantee else sql.SQL('PUBLIC')))
        for role in(ROLE,'cp7_sales_read','cp7_payroll_write','cp7_sales_write','cp7_installment_write'):
            cur.execute(sql.SQL('grant usage on schema {} to {}').format(sql.Identifier(SCHEMA),sql.Identifier(role)))


def public_schema_transition(cur,before_items,owner):
    require(before_items is not None,'MANDOR_REVIEWED_EXPLICIT_PUBLIC_SCHEMA_ACL_REQUIRED')
    raw,items=cur.execute("select nspacl::text,nspacl::text[] from pg_namespace where nspname='public'").fetchone()
    require(items==before_items+[ROLE+'=U/'+owner],
        'MANDOR_PUBLIC_RAW_ACL_ONLY_NEW_API_USAGE_MAY_BE_APPENDED')
    return raw


def transition(before,after,definitions,plan):
    require(len(before)==22 and set(before)==set(after),'MANDOR_COMPLETE_ALL22_TRANSITION_REQUIRED')
    fk={(row[9],key.split(':',1)[1])for key,row in after['constraints'].items()
        if key not in before['constraints']and key.startswith(SCHEMA+'.')and row[0]=='f'}
    custom_parent={(t['relation'],t['name'])for t in plan['triggers']if not t['relation'].startswith(SCHEMA+'.')}
    constraint_parent={t['relation']+':'+t['name']:
        ['t',t['deferrable'],t['initially_deferred'],True,True,0,True,None,None,t['relation'],
         'TRIGGER'+(' DEFERRABLE'if t['deferrable']else' NOT DEFERRABLE')+
         (' INITIALLY DEFERRED'if t['initially_deferred']else' INITIALLY IMMEDIATE')]
        for t in plan['triggers']if t['constraint']and not t['relation'].startswith(SCHEMA+'.')}
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None:
                require(new[0]==definitions[key]and new[1:]==old[1:],'MANDOR_ONLY_NATIVE_BODY_MAY_CHANGE:'+key);continue
            if group=='schemas'and key=='public'and old is not None and new is not None:
                expected={tuple(x)for x in old[1]}|{(ROLE,old[0],'USAGE',False)}
                require(new[0]==old[0]and{tuple(x)for x in new[1]}==expected,
                    'MANDOR_PUBLIC_SCHEMA_ONLY_DECLARED_NEW_API_USAGE_ALLOWED');continue
            require(old is None and new is not None,'MANDOR_EXISTING_UNDECLARED_CATALOG_CHANGE:'+group+':'+key)
            if group=='schemas'and key==SCHEMA:continue
            if group=='roles'and key==ROLE:continue
            if group=='constraints'and key in constraint_parent:
                require(new==constraint_parent[key],'MANDOR_EXACT_DECLARED_PARENT_CONSTRAINT_TRIGGER_REQUIRED:'+key);continue
            # PostgreSQL's creator ADMIN membership is not an inherited or SET
            # capability. The facade's temporary postgres-issued SET grant has
            # already been removed; no such grant is admitted here.
            if group=='memberships'and key==ROLE+':postgres:supabase_admin'and new==[True,False,False]:continue
            if group=='functions'and key in plan['private_functions']+plan['public_functions']:continue
            if group=='triggers':
                firing=key.split(':',1)[0]
                if new[0]is True and(new[15],new[12])in fk:continue
                if(firing,key.split(':',1)[1])in custom_parent:continue
                if firing.startswith(SCHEMA+'.')and(firing,key.split(':',1)[1])in{(t['relation'],t['name'])for t in plan['triggers']}:continue
            if group in('relations','columns','constraints','indexes','types','type_implementation','policies')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('MANDOR_UNDECLARED_NEW_CATALOG_OBJECT:'+group+':'+key)
    require(set(after['functions'])-set(before['functions'])==set(plan['private_functions']+plan['public_functions']),
        'MANDOR_EXACT_NEW42_FUNCTION_SET_REQUIRED')


def install(cur,parent_receipt_raw):
    source=sources();parent=admission.runtime_admission(parent_receipt_raw)
    with atomic(cur),metadata_context(cur):
        trusted_installer(cur);before=capture(cur);plan=json.loads((HERE/'INSTALL_PLAN.json').read_bytes())
        require(SCHEMA not in before['schemas']and ROLE not in before['roles'],'MANDOR_EXISTING_MODULE_REFUSE_TO_TOUCH')
        # All thirteen source adapters demand the complete actual19
        # parent rows they were reviewed against, not only a text anchor.
        payment,_=native_payment_routes.derive(before['functions']);sales,_=native_sales_routes.derive(before['functions'])
        guards,guard_proof=command_guard_routes.derive(before['functions'],payment)
        definitions=payment|sales|guards;facades,dispatch_proof=native_dispatch.derive(before['functions'])
        reference=json.loads((HERE/'NATIVE_SCHEMA_REFERENCE.json').read_bytes())
        for columns in reference['columns'].values():
            for key,row in columns.items():
                require(before['columns'].get(key)==row,'MANDOR_CURRENT_NATIVE_COLUMN_PROFILE_CHANGED:'+key)
        identity=native_identity(cur,definitions)
        public_acl=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
        public_items=cur.execute("select nspacl::text[] from pg_namespace where nspname='public'").fetchone()[0]
        require(public_items is not None,'MANDOR_REVIEWED_EXPLICIT_PUBLIC_SCHEMA_ACL_REQUIRED')
        with as_role(cur,'postgres',{'postgres'}):
            for name in ORDER:cur.execute((HERE/name).read_text(),prepare=False)
            cur.execute(facades,prepare=False)
        normalize_private(cur,plan);replace_native(cur,definitions,identity)
        installed_public_acl=public_schema_transition(cur,public_items,before['schemas']['public'][0])
        after=capture(cur);transition(before,after,definitions,plan)
        state=dict(contract=CONTRACT,sources=source,parent=parent,before=before,after=after,
            originals={sig:before['functions'][sig][0]for sig in definitions},definitions=definitions,
            native_identity=identity,raw_public_schema_acl_before=public_acl,raw_public_schema_acl=installed_public_acl,
            dispatch_proof=dispatch_proof,command_guard_proof=guard_proof,plan=plan)
        state['sha256']=digest(state);verify(cur,state);return state


def verify(cur,state):
    require(state.get('contract')==CONTRACT and state.get('sha256')==digest({k:v for k,v in state.items()if k!='sha256'}),
        'MANDOR_INSTALL_STATE_CHANGED')
    require(state['sources']==sources(),'MANDOR_INSTALLED_SOURCE_CHANGED')
    require(capture(cur)==state['after'],'MANDOR_COMPLETE_INSTALLED_CATALOGUE_CHANGED')
    require(native_identity(cur,state['definitions'])==state['native_identity'],'MANDOR_NATIVE_OID_RAW_AUTHORITY_CHANGED')
    require(cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]==state['raw_public_schema_acl'],
        'MANDOR_PUBLIC_SCHEMA_RAW_ACL_CHANGED')
    for sig in state['plan']['private_functions']:
        row=state['after']['functions'][sig]
        require(row[1]=='postgres','MANDOR_PRIVATE_OWNER_CHANGED:'+sig)
        expected={('postgres','postgres','EXECUTE',False)}|{(r,'postgres','EXECUTE',False)for r in state['plan']['private_execute_grants'].get(sig,[])}
        require({tuple(x)for x in row[18]}==expected,'MANDOR_PRIVATE_EXACT_EXECUTE_CHANGED:'+sig)
    for sig in state['plan']['public_functions']:
        row=state['after']['functions'][sig]
        require(row[1]==ROLE and row[4]is True,'MANDOR_PUBLIC_FACADE_OWNER_OR_DEFINER_CHANGED:'+sig)
        require({tuple(x)for x in row[18]}=={(ROLE,ROLE,'EXECUTE',False),('authenticated',ROLE,'EXECUTE',False)},
            'MANDOR_PUBLIC_FACADE_EXACT_EXECUTE_CHANGED:'+sig)
    for table in state['plan']['tables']:
        row=state['after']['relations'][table]
        require(row[0]=='postgres'and row[3]is True,'MANDOR_PRIVATE_TABLE_OWNER_OR_RLS_CHANGED:'+table)
        require(all(x[0]=='postgres'and x[1]=='postgres'for x in row[12]),'MANDOR_PRIVATE_TABLE_NONOWNER_GRANT:'+table)
    role=state['after']['roles'][ROLE]
    require(not any(role[i]for i in(0,1,2,3,4,5,6)),'MANDOR_API_ROLE_PRIVILEGES_CHANGED')
    for key,row in state['after']['memberships'].items():
        if key.split(':')[0]==ROLE:require(not row[1]and not row[2],'MANDOR_TEMPORARY_ROLE_SET_OR_INHERIT_NOT_REMOVED')
    return dict(contract=CONTRACT,new_private_functions=36,new_public_facades=6,Native_adapters=13,
        all22_verified=True,Native_OID_and_raw_ACL_preserved=True,actual_business_qualification=False,
        production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    from psycopg import sql
    with atomic(cur),metadata_context(cur):
        trusted_installer(cur);verify(cur,state)
        for table in state['plan']['tables']:
            schema,name=table.split('.',1)
            require(not cur.execute(sql.SQL('select exists(select 1 from {} limit 1)').format(sql.Identifier(schema,name))).fetchone()[0],
                'MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:'+table)
        replace_native(cur,state['originals'],state['native_identity'])
        with as_role(cur,'postgres',{'postgres'}):
            for trigger in state['plan']['triggers']:
                schema,table=trigger['relation'].split('.',1)
                cur.execute(sql.SQL('drop trigger {} on {}').format(sql.Identifier(trigger['name']),sql.Identifier(schema,table)))
            cur.execute(facade_install.inverse_sql(),prepare=False)
            remaining=[s for s in state['plan']['private_functions']if s not in facade_install.PRIVATE]
            cur.execute(sql.SQL('drop function '+','.join(remaining)))
            cur.execute(sql.SQL('drop table '+','.join(state['plan']['tables'])))
            cur.execute(sql.SQL('drop schema {}').format(sql.Identifier(SCHEMA)))
        require(capture(cur)==state['before'],'MANDOR_PREUSE_ALL22_NOT_EXACTLY_RESTORED')
        require(native_identity(cur,state['originals'])==state['native_identity'],'MANDOR_PREUSE_NATIVE_OID_RAW_ACL_CHANGED')
        require(cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]==state['raw_public_schema_acl_before'],
            'MANDOR_PREUSE_RAW_PUBLIC_SCHEMA_ACL_NOT_RESTORED')
        return dict(all22_and_Native_raw_authority_restored=True,used_rows_removed=False,
            cascade_or_DROP_OWNED_used=False,production_go=False,independent_acceptance=False)
