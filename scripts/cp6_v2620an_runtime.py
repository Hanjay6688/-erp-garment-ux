#!/usr/bin/env python3
"""AN verifies every inherited AM function, both new readers and unchanged relations."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
sys.path.insert(0,str(Path.cwd()/"scripts"))
import cp6_v2620ac_runtime as ac
import cp6_v2620am_runtime as predecessor
from cp6_v2620an_build_sql import STAMP,NAME,VERSION,MIGRATION,ROLLBACK,PINS,CATALOG,PREDECESSOR_HEAD,PREDECESSOR_TREE

ROOT=Path(__file__).resolve().parents[1]
MIGRATION,ROLLBACK,PINS,CATALOG=(ROOT/p for p in (MIGRATION,ROLLBACK,PINS,CATALOG))
from cp6_v2620an_definitions import PRIVATE_ID,PUBLIC_ID
CAPSULE='erp.cp6_v2620an_rollback_capsule'
PINS_SHA256='e4878aeaeac4f7da43f530a13f09df8ed82d34d5f1fe93bc61195f250179e10b'

def pins():
 raw=PINS.read_bytes();assert hashlib.sha256(raw).hexdigest()==PINS_SHA256,'AN_TRUSTED_PINS_CHANGED'
 p=json.loads(raw)
 assert (p['predecessor_head'],p['predecessor_tree'],p['boundary_count'],p['predecessor_table_count'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE,226,228)
 return p

def verify_source_files():
 p=pins();predecessor.verify_source_files()
 for path,expected in p['source_pins'].items():
  b=(ROOT/path).read_bytes();assert len(b)==expected['bytes'] and hashlib.sha256(b).hexdigest()==expected['sha256'],'AN_SOURCE_DRIFT:'+path
 assert len(p['functions'])==1 and len(p['new_functions'])==2
 return p

def verify_audit_source():
 verify_source_files()
 # Execution checkout stays pinned AI; the predecessor AM is installed and
 # fully verified before this new migration. Harness head is bound separately.
 return predecessor.verify_audit_source()


def reviewed_local_rollback():
 # The unchanged controller accepts files only inside its execution checkout.
 # Materialize the exact already-pinned AN bytes there; retain that path gate
 # and the controller's independently pinned rollback checksum.
 verify_audit_source()
 target=Path.cwd()/'cp6-proof/writer-an/reviewed'/ROLLBACK.name
 assert target.resolve().is_relative_to(Path.cwd().resolve()),'AN_LOCAL_ROLLBACK_PATH'
 target.parent.mkdir(parents=True,exist_ok=True)
 raw=ROLLBACK.read_bytes()
 expected=pins()['source_pins'][str(ROLLBACK.relative_to(ROOT))]['sha256']
 assert hashlib.sha256(raw).hexdigest()==expected
 target.write_bytes(raw)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
 return target

def catalog(cur,successor):
 expected={f['identity']:dict(f) for f in json.loads(CATALOG.read_text())['functions']};assert len(expected)==533
 if successor:
  for f in pins()['new_functions']:expected[f['identity']]=dict(sha256=f['installed_sha256'],owner=f['owner'],acl=f['acl'])
 observed=cur.execute("""select case when n.nspname='public' then format('public.%%I(%%s)',p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) else p.oid::regprocedure::text end,
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where (n.nspname='erp' or p.oid=to_regprocedure(%s)) and p.prokind='f' order by 1""",(PUBLIC_ID,)).fetchall()
 assert len(observed)==(535 if successor else 533) and {r[0] for r in observed}==set(expected),'AN_COMPLETE_FUNCTION_SET_DRIFT'
 result={}
 for identity,digest,owner,acl in observed:
  e=expected[identity];assert (digest,owner,acl)==(e['sha256'],e['owner'],e['acl']),'AN_LIVE_FUNCTION_DRIFT:'+identity
  result['FUNCTION:'+identity]=dict(identity=identity,installed_sha256=digest,owner=owner,acl=acl,kind='FUNCTION')
 return result

def verify_predecessor(cur):
 verify_source_files();assert len(predecessor.verified_successor(cur))==690
 catalog(cur,False)
 assert cur.execute('select to_regprocedure(%s),to_regprocedure(%s)',(PRIVATE_ID,PUBLIC_ID)).fetchone()==(None,None)
 assert not cur.execute("select to_regclass(%s) is not null or exists(select 1 from erp.schema_migrations where version=%s) or exists(select 1 from supabase_migrations.schema_migrations where name=%s)",(CAPSULE,VERSION,NAME)).fetchone()[0],'AN_PREDECESSOR_RESIDUE'
 return True

def verified_successor(cur,*,pre_admission=False):
 p=verify_source_files();objects=catalog(cur,True)
 assert cur.execute("select exists(select 1 from erp.schema_migrations where version=%s),to_regclass(%s) is not null",(VERSION,CAPSULE)).fetchone()==(True,True)
 platform=cur.execute("select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations where name=%s",(NAME,)).fetchall()
 assert platform==[(STAMP,p['source_pins'][str(MIGRATION.relative_to(ROOT))]['sha256'])],'AN_PLATFORM_SOURCE_DRIFT'
 ac._capsule_security(cur,CAPSULE)
 rows=cur.execute(f"""select object_regidentity,definition_sha256,encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex'),installed_definition_sha256,owner_snapshot,acl_snapshot,boundary_snapshot from {CAPSULE} order by object_regidentity""").fetchall()
 expected={f['identity']:f for f in p['functions']};assert len(rows)==1 and {r[0] for r in rows}==set(expected)
 boundary=rows[0][-1];assert boundary is not None and len(boundary)==226
 for identity,before,actual,after,owner,acl,snapshot in rows:
  e=expected[identity]
  assert (before,actual,after,owner,acl)==(e['predecessor_sha256'],e['predecessor_sha256'],e['installed_sha256'],e['owner'],e['acl']) and snapshot==boundary,'AN_CAPSULE_DRIFT:'+identity
 # Historical capsules are immutable dependencies captured in the AN boundary.
 # Their data hashes are recorded in UTC by the unchanged installation engine.
 zone=cur.execute('show timezone').fetchone()[0];cur.execute("select set_config('TimeZone','UTC',true)")
 try:
  from psycopg import sql
  names=cur.execute("select relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind='r' and relname like 'cp6%rollback_capsule' and relname<>'cp6_v2620an_rollback_capsule' order by 1").fetchall()
  for (name,) in names:
   ac._capsule_security(cur,'erp.'+name)
   digest=cur.execute(sql.SQL("""select encode(extensions.digest(convert_to(coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),'sha256'),'hex') row_hash from erp.{} t) rows""").format(sql.Identifier(name))).fetchone()[0]
   assert digest==boundary[name],'AN_INHERITED_CAPSULE_DRIFT:'+name
 finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))
 assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname='erp_get_cutting_workspace_v2'").fetchone()[0]==1
 if pre_admission:return objects
 assert ac._verify_installation_state(cur)
 objects.update(ac._verify_views(cur,ac.pins()));objects.update(ac._verify_defaults(cur,ac.pins()))
 assert len(objects)==692,'AN_RUNTIME_CARDINALITY'
 return objects
