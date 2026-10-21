"""Attest an offline full backup, then bind its strict census to a fresh DB.

Administrative Python API only: no connection, commit, public RPC, bypass flag,
provider or scheduling. The caller supplies its transaction and the trusted
backup manifest's SHA256. Keep the source transaction open through pg_dump;
SHARE locks prevent business changes while that backup is taken. A restored
database must match every captured row, sequence and portable catalog object
before the ONE source-validated runtime seal can be regenerated. Ordinary
runtime still checks the complete raw census, including local object OIDs.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re

from psycopg import sql
from psycopg.pq import TransactionStatus
import cp7_full_owning_install as product

ROOT = Path(__file__).resolve().parents[1]
GUARD = 'cp7_credit.assert_source_native_trigger_census_v1()'
VERSION = 'ow04.offline-full-backup.v1'
EXCLUDED = ['pg_catalog', 'information_schema', 'cron']
NAMESPACE = "n.nspname<>all(array['pg_catalog','information_schema','cron']) and n.nspname!~'^pg_'"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _acl(column, owner, kind):
    return "(select coalesce(jsonb_agg(jsonb_build_array(case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,pg_get_userbyid(a.grantor),a.privilege_type,a.is_grantable)order by a.grantee::regrole::text,a.grantor::regrole::text,a.privilege_type,a.is_grantable),'[]'::jsonb)from aclexplode(coalesce("+column+",acldefault('"+kind+"',"+owner+")))a)"


QUERIES = {
 'schemas': "select n.nspname,jsonb_build_array(pg_get_userbyid(n.nspowner),"+_acl('n.nspacl','n.nspowner','n')+")from pg_namespace n where "+NAMESPACE,
 'relations': "select n.nspname||'.'||c.relname,jsonb_build_array(pg_get_userbyid(c.relowner),c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,c.relispartition,c.relreplident,c.reloptions,c.relispopulated,case when c.relkind in('v','m')then pg_get_viewdef(c.oid,false)else null end,pg_get_partkeydef(c.oid),pg_get_expr(c.relpartbound,c.oid),case when c.relkind='S'then "+_acl('c.relacl','c.relowner','s')+"else "+_acl('c.relacl','c.relowner','r')+"end)from pg_class c join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'columns': "select n.nspname||'.'||c.relname||':'||a.attname,jsonb_build_array(a.attname,row_number()over(partition by c.oid order by a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,a.attstorage,a.attcompression,a.attstattarget,a.attoptions,a.attfdwoptions,a.attcollation::regcollation::text,a.attacl::text[],pg_get_expr(d.adbin,d.adrelid))from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attnum>0 and not a.attisdropped and "+NAMESPACE,
 'constraints': "select n.nspname||'.'||coalesce(c.relname,t.typname)||':'||k.conname,jsonb_build_array(k.contype,k.condeferrable,k.condeferred,k.convalidated,k.conislocal,k.coninhcount,k.connoinherit,pg_get_constraintdef(k.oid,false))from pg_constraint k join pg_namespace n on n.oid=k.connamespace left join pg_class c on c.oid=k.conrelid left join pg_type t on t.oid=k.contypid where "+NAMESPACE,
 'indexes': "select n.nspname||'.'||c.relname,jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisvalid,i.indisready,i.indislive,i.indisclustered,i.indisreplident)from pg_index i join pg_class c on c.oid=i.indexrelid join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'triggers': "select n.nspname||'.'||c.relname||':'||case when t.tgisinternal then k.conrelid::regclass::text||':'||k.conname||':'||t.tgfoid::regprocedure::text||':'||t.tgtype::text else t.tgname end,jsonb_build_array(t.tgisinternal,t.tgenabled,t.tgtype,t.tgnargs,encode(t.tgargs,'hex'),coalesce((select jsonb_agg(a.attname order by x.ord)from unnest(t.tgattr::smallint[])with ordinality x(attnum,ord)join pg_attribute a on a.attrelid=t.tgrelid and a.attnum=x.attnum),'[]'::jsonb),t.tgdeferrable,t.tginitdeferred,t.tgfoid::regprocedure::text,case when t.tgisinternal then null else pg_get_triggerdef(t.oid,false)end,t.tgoldtable,t.tgnewtable,k.conname,case when t.tgconstrrelid=0 then null else t.tgconstrrelid::regclass::text end,case when t.tgparentid=0 then null else (select p.tgname from pg_trigger p where p.oid=t.tgparentid)end,k.conrelid::regclass::text)from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace left join pg_constraint k on k.oid=t.tgconstraint where "+NAMESPACE,
 'functions': "select p.oid::regprocedure::text,jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),l.lanname,p.prokind,p.prosecdef,p.proleakproof,p.proisstrict,p.proretset,p.provolatile,p.proparallel,p.procost::text,p.prorows::text,p.proconfig,p.proargnames,p.proargmodes,pg_get_function_arguments(p.oid),pg_get_function_result(p.oid),p.prosupport::regprocedure::text,"+_acl('p.proacl','p.proowner','f')+")from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_language l on l.oid=p.prolang where p.prokind<>'a'and "+NAMESPACE,
 'aggregates': "select p.oid::regprocedure::text,to_jsonb(a)from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_aggregate a on a.aggfnoid=p.oid where "+NAMESPACE,
 'types': "select t.oid::regtype::text,jsonb_build_array(pg_get_userbyid(t.typowner),t.typtype,t.typcategory,t.typispreferred,t.typisdefined,t.typnotnull,case when t.typbasetype=0 then null else format_type(t.typbasetype,t.typtypmod)end,t.typdefault,t.typcollation::regcollation::text,"+_acl('t.typacl','t.typowner','t')+")from pg_type t join pg_namespace n on n.oid=t.typnamespace where "+NAMESPACE,
 'enums': "select t.oid::regtype::text||':'||e.enumsortorder::text,to_jsonb(e.enumlabel)from pg_enum e join pg_type t on t.oid=e.enumtypid join pg_namespace n on n.oid=t.typnamespace where "+NAMESPACE,
 'sequences': "select s.seqrelid::regclass::text,jsonb_build_array(format_type(s.seqtypid,null),s.seqstart::text,s.seqincrement::text,s.seqmax::text,s.seqmin::text,s.seqcache::text,s.seqcycle)from pg_sequence s join pg_class c on c.oid=s.seqrelid join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'policies': "select n.nspname||'.'||c.relname||':'||p.polname,jsonb_build_array(p.polcmd,p.polpermissive,(select jsonb_agg(case when r=0 then 'PUBLIC'else pg_get_userbyid(r)end order by case when r=0 then 'PUBLIC'else pg_get_userbyid(r)end)from unnest(p.polroles)r),pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'extensions': "select e.extname,jsonb_build_array(e.extversion,n.nspname,pg_get_userbyid(e.extowner),e.extrelocatable,(select jsonb_agg(r::regclass::text order by r::regclass::text)from unnest(e.extconfig)r),e.extcondition)from pg_extension e join pg_namespace n on n.oid=e.extnamespace where e.extname<>'pg_cron'",
 'roles': "select r.rolname,jsonb_build_array(r.rolsuper,r.rolinherit,r.rolcreaterole,r.rolcreatedb,r.rolcanlogin,r.rolreplication,r.rolbypassrls,r.rolconnlimit,r.rolvaliduntil::text,encode(sha256(convert_to(coalesce(r.rolconfig::text,''),'UTF8')),'hex'))from pg_roles r",
 'memberships': "select pg_get_userbyid(m.roleid)||':'||pg_get_userbyid(m.member)||':'||pg_get_userbyid(m.grantor),jsonb_build_array(m.admin_option,m.inherit_option,m.set_option)from pg_auth_members m",
 'event_triggers': "select e.evtname,jsonb_build_array(e.evtevent,pg_get_userbyid(e.evtowner),e.evtfoid::regprocedure::text,e.evtenabled,e.evttags)from pg_event_trigger e",
 'rules': "select n.nspname||'.'||c.relname||':'||r.rulename,jsonb_build_array(r.ev_type,r.ev_enabled,r.is_instead,pg_get_ruledef(r.oid,false))from pg_rewrite r join pg_class c on c.oid=r.ev_class join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'inheritance': "select i.inhrelid::regclass::text||':'||i.inhseqno::text,to_jsonb(i.inhparent::regclass::text)from pg_inherits i join pg_class c on c.oid=i.inhrelid join pg_namespace n on n.oid=c.relnamespace where "+NAMESPACE,
 'default_privileges': "select pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,"+_acl('d.defaclacl','d.defaclrole','r')+"from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace",
 'database_authority': "select 'CURRENT',jsonb_build_array(pg_get_userbyid(d.datdba),pg_encoding_to_char(d.encoding),d.datcollate,d.datctype,d.datconnlimit,d.datistemplate,d.datallowconn,"+_acl('d.datacl','d.datdba','d')+",(select jsonb_agg(jsonb_build_array(case when s.setrole=0 then 'DATABASE'else pg_get_userbyid(s.setrole)end,encode(sha256(convert_to(s.setconfig::text,'UTF8')),'hex'))order by s.setrole)from pg_db_role_setting s where s.setdatabase=d.oid))from pg_database d where d.datname=current_database()",
 'type_implementation': "select t.oid::regtype::text,jsonb_build_array(t.typlen,t.typbyval,t.typdelim,t.typalign,t.typstorage,t.typndims,t.typrelid::regclass::text,t.typelem::regtype::text,t.typarray::regtype::text,t.typsubscript::regprocedure::text,t.typinput::regprocedure::text,t.typoutput::regprocedure::text,t.typreceive::regprocedure::text,t.typsend::regprocedure::text,t.typmodin::regprocedure::text,t.typmodout::regprocedure::text,t.typanalyze::regprocedure::text)from pg_type t join pg_namespace n on n.oid=t.typnamespace where "+NAMESPACE,
 'sequence_ownership': "select c.oid::regclass::text,jsonb_build_array(d.deptype,d.refobjid::regclass::text,a.attname)from pg_class c join pg_namespace n on n.oid=c.relnamespace join pg_depend d on d.classid='pg_class'::regclass and d.objid=c.oid and d.refclassid='pg_class'::regclass and d.deptype in('a','i')left join pg_attribute a on a.attrelid=d.refobjid and a.attnum=d.refobjsubid where c.relkind='S'and "+NAMESPACE,
}


@contextmanager
def _catalog(cur):
    before=cur.execute('show search_path').fetchone()[0]
    zone=cur.execute('show timezone').fetchone()[0]
    cur.execute("select set_config('search_path','',true),set_config('TimeZone','UTC',true)")
    try:
        yield
    finally:
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true),set_config('TimeZone',%s,true)",(before,zone))


def _authority(cur):
    user,db,oid=cur.execute('select current_user,current_database(),(select oid::text from pg_database where datname=current_database())').fetchone()
    if user not in ('postgres','supabase_admin'):
        raise ValueError('OW04_RESTORE_ADMINISTRATIVE_IDENTITY_REQUIRED')
    return dict(database=db,database_oid=oid)


def _lock_tables(cur):
    names=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p')and "+NAMESPACE+" order by n.nspname collate \"C\",c.relname collate \"C\"").fetchall()
    if not names:raise ValueError('OW04_RESTORE_EMPTY_DATABASE_REFUSED')
    cur.execute(sql.SQL('lock table {} in share mode nowait').format(sql.SQL(',').join(sql.Identifier(*n)for n in names)))


def _catalog_rows(cur):
    result={}
    with _catalog(cur):
        for kind,query in QUERIES.items():
            try:rows=cur.execute(query).fetchall()
            except Exception as error:
                raise ValueError('OW04_RESTORE_CATALOG_QUERY_FAILED: '+kind+': '+str(error))from error
            if kind=='aggregates'and rows:
                raise ValueError('OW04_RESTORE_UNSUPPORTED_USER_AGGREGATE')
            values=dict(rows)
            if len(values)!=len(rows):raise ValueError('OW04_RESTORE_DUPLICATE_CATALOG_IDENTITY: '+kind)
            result[kind]=values
    if any(row[1]=='f'for row in result['relations'].values()):
        raise ValueError('OW04_RESTORE_UNSUPPORTED_FOREIGN_RELATION')
    return result


def _data(cur):
    result={}
    with _catalog(cur):
        tables=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p','m')and "+NAMESPACE+" order by 1,2").fetchall()
        for name in tables:
            row=cur.execute(sql.SQL("select count(*),encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),'[]'::jsonb)::text,'UTF8')),'hex')from {} r").format(sql.Identifier(*name))).fetchone()
            result['.'.join(name)]=list(row)
        sequences=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='S'and "+NAMESPACE+" order by 1,2").fetchall()
        for name in sequences:
            result['sequence:'+'.'.join(name)]=list(cur.execute(sql.SQL('select last_value::text,is_called from {}').format(sql.Identifier(*name))).fetchone())
    return result


def _sources():
    return dict(product=product.source_manifest(),restore_module_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def export_manifest(cur,state):
    """Keep this transaction and its SHARE locks open until the full dump ends."""
    identity=_authority(cur)
    _lock_tables(cur)
    product.verify(cur,state)
    guard=product.credit.load('ow04_backup_source_guard',product.credit.ROOT/'integration/source_triggers/trigger_guard.py')
    manifest=guard.declarations(ROOT)
    capture=product.credit._source_trigger_capture(cur,guard)
    phase=state['credit']['source_triggers']['phase']
    guard.verify_unchanged(capture,state['credit']['source_triggers']['installed'],manifest,phase)
    result=dict(contract_version=VERSION,source_identity=identity,sources=_sources(),phase=phase,
        excluded_schemas=EXCLUDED,catalog=_catalog_rows(cur),data=_data(cur))
    return result,digest(result)


def _normal(value):
    # One previously proved PostgreSQL dump/reparse spelling, preserving each
    # varchar literal in order. No general whitespace/SQL/ACL normalization.
    stored=re.compile(r"\(ARRAY\[((?:'[^']*'::character varying(?:, )?)+)\]\)::text\[\]")
    reparsed=re.compile(r"ARRAY\[((?:\('[^']*'::character varying\)::text(?:, )?)+)\]")
    def transform(v):
        if isinstance(v,str):
            token=lambda m:'ARRAY<'+json.dumps(re.findall(r"'([^']*)'",m.group(1)))+'>'
            return reparsed.sub(token,stored.sub(token,v))
        if isinstance(v,list):return [transform(x)for x in v]
        if isinstance(v,dict):return {k:transform(x)for k,x in v.items()}
        return v
    return transform(value)


def _portable(catalog):
    # pg_dump may reparse these stored SQL expressions. A function body,
    # role, owner, grant, identifier or any other metadata stays byte exact.
    result=deepcopy(catalog)
    for kind,indexes in (('constraints',(-1,)),('indexes',(0,)),
                         ('relations',(9,)),('policies',(-2,-1)),
                         ('columns',(-1,)),('rules',(-1,)),('triggers',(9,))):
        for row in result.get(kind,{}).values():
            for index in indexes:row[index]=_normal(row[index])
    return result


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    """Only an exact trusted fresh restore may obtain its new local OID seal."""
    if not isinstance(expected_sha256,str)or digest(backup)!=expected_sha256:
        raise ValueError('OW04_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    if backup.get('contract_version')!=VERSION or backup.get('sources')!=_sources()or backup.get('excluded_schemas')!=EXCLUDED:
        raise ValueError('OW04_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    identity=_authority(cur)
    if identity['database']!=expected_database or identity==backup['source_identity']:
        raise ValueError('OW04_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    _lock_tables(cur)
    actual=_catalog_rows(cur)
    portable_actual,portable_expected=_portable(actual),_portable(backup['catalog'])
    if portable_actual!=portable_expected:
        differences={kind:sorted(k for k in set(portable_actual.get(kind,{}))|set(portable_expected.get(kind,{}))if portable_actual.get(kind,{}).get(k)!=portable_expected.get(kind,{}).get(k))for kind in set(portable_actual)|set(portable_expected)}
        raise ValueError('OW04_RESTORE_CATALOG_CHANGED: '+canonical({k:v for k,v in differences.items()if v}))
    before=_data(cur)
    if before!=backup['data']:raise ValueError('OW04_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    guard=product.credit.load('ow04_restore_source_guard',product.credit.ROOT/'integration/source_triggers/trigger_guard.py')
    manifest=guard.declarations(ROOT)
    capture=product.credit._source_trigger_capture(cur,guard)
    guard.validate_source(capture,manifest,backup['phase'])
    expected=cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',(canonical(capture),)).fetchone()[0]
    rendered=guard.render_runtime_guard(capture,manifest,backup['phase'],expected)
    cur.execute(rendered,prepare=False)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    after=_catalog_rows(cur)
    changed=[(kind,key)for kind in set(actual)|set(after)for key in set(actual.get(kind,{}))|set(after.get(kind,{}))if actual.get(kind,{}).get(key)!=after.get(kind,{}).get(key)]
    if changed!=[('functions',GUARD)]:raise ValueError('OW04_RESTORE_UNDECLARED_BINDING_CATALOG_DELTA: '+canonical(changed))
    old,new=actual['functions'][GUARD],after['functions'][GUARD]
    if old[1:]!=new[1:]:raise ValueError('OW04_RESTORE_RUNTIME_SEAL_PRIVILEGE_OR_METADATA_CHANGED')
    if _data(cur)!=before:raise ValueError('OW04_RESTORE_BINDING_CHANGED_BUSINESS_DATA')
    return dict(contract_version='ow04.verified-restore-binding.v1',trusted_backup_sha256=expected_sha256,
        fresh_database_verified=True,all_rows_and_sequences_equal=True,portable_catalog_equal=True,
        changed_functions=[GUARD],local_raw_oid_census_enforced=True,
        runtime_capture_sha256_pg=expected,production_go=False)
