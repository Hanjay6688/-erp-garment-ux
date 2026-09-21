#!/usr/bin/env python3
"""AL pins all 533 live functions and the 157 unchanged AC relation objects."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
sys.path.insert(0,str(Path.cwd()/"scripts"))
import cp6_v2620ac_runtime as ac
import cp6_v2620ak_runtime as predecessor
from cp6_v2620al_build_sql import STAMP,NAME,VERSION,MIGRATION,ROLLBACK,PINS,CATALOG,PREDECESSOR_HEAD,PREDECESSOR_TREE

ROOT=Path(__file__).resolve().parents[1]
MIGRATION,ROLLBACK,PINS,CATALOG=(ROOT/p for p in (MIGRATION,ROLLBACK,PINS,CATALOG))
CAPSULE='erp.cp6_v2620al_rollback_capsule'
PINS_SHA256='ac9e8000a291ea18950e8528ef9228b3a096d801f48cc6ff876ecd041ab1b014'

def pins():
 raw=PINS.read_bytes();assert hashlib.sha256(raw).hexdigest()==PINS_SHA256,'AL_TRUSTED_PINS_CHANGED'
 p=json.loads(raw)
 assert (p['predecessor_head'],p['predecessor_tree'],p['boundary_count'],p['predecessor_table_count'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE,224,226)
 return p

def verify_source_files():
 p=pins();predecessor.verify_source_files()
 for path,expected in p['source_pins'].items():
  b=(ROOT/path).read_bytes();assert len(b)==expected['bytes'] and hashlib.sha256(b).hexdigest()==expected['sha256'],'AL_SOURCE_DRIFT:'+path
 assert len(p['functions'])==2
 return p

def verify_audit_source():
 verify_source_files()
 # Execution checkout stays pinned AI; the predecessor AK is installed and
 # fully verified before this new migration. Harness head is bound separately.
 return predecessor.verify_audit_source()


def reviewed_local_rollback():
 # The unchanged controller accepts files only inside its execution checkout.
 # Materialize the exact already-pinned AL bytes there; retain that path gate
 # and the controller's independently pinned rollback checksum.
 verify_audit_source()
 target=Path.cwd()/'cp6-proof/writer-al/reviewed'/ROLLBACK.name
 assert target.resolve().is_relative_to(Path.cwd().resolve()),'AL_LOCAL_ROLLBACK_PATH'
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
  for f in pins()['functions']:expected[f['identity']].update(sha256=f['installed_sha256'],owner=f['owner'],acl=f['acl'])
 observed=cur.execute("""select p.oid::regprocedure::text,
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.prokind='f' order by 1""").fetchall()
 assert len(observed)==533 and {r[0] for r in observed}==set(expected),'AL_COMPLETE_FUNCTION_SET_DRIFT'
 result={}
 for identity,digest,owner,acl in observed:
  e=expected[identity];assert (digest,owner,acl)==(e['sha256'],e['owner'],e['acl']),'AL_LIVE_FUNCTION_DRIFT:'+identity
  result['FUNCTION:'+identity]=dict(identity=identity,installed_sha256=digest,owner=owner,acl=acl,kind='FUNCTION')
 return result

def verify_predecessor(cur):
 verify_source_files();assert len(predecessor.verified_successor(cur))==690
 catalog(cur,False)
 assert not cur.execute("select to_regclass(%s) is not null or exists(select 1 from erp.schema_migrations where version=%s) or exists(select 1 from supabase_migrations.schema_migrations where name=%s)",(CAPSULE,VERSION,NAME)).fetchone()[0],'AL_PREDECESSOR_RESIDUE'
 return True

def verified_successor(cur,*,pre_admission=False):
 p=verify_source_files();objects=catalog(cur,True)
 assert cur.execute("select exists(select 1 from erp.schema_migrations where version=%s),to_regclass(%s) is not null",(VERSION,CAPSULE)).fetchone()==(True,True)
 platform=cur.execute("select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations where name=%s",(NAME,)).fetchall()
 assert platform==[(STAMP,p['source_pins'][str(MIGRATION.relative_to(ROOT))]['sha256'])],'AL_PLATFORM_SOURCE_DRIFT'
 ac._capsule_security(cur,CAPSULE)
 rows=cur.execute(f"""select object_regidentity,definition_sha256,encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex'),installed_definition_sha256,owner_snapshot,acl_snapshot,boundary_snapshot from {CAPSULE} order by object_regidentity""").fetchall()
 expected={f['identity']:f for f in p['functions']};assert len(rows)==2 and {r[0] for r in rows}==set(expected)
 boundary=rows[0][-1];assert boundary is not None and len(boundary)==224
 for identity,before,actual,after,owner,acl,snapshot in rows:
  e=expected[identity]
  assert (before,actual,after,owner,acl)==(e['predecessor_sha256'],e['predecessor_sha256'],e['installed_sha256'],e['owner'],e['acl']) and snapshot==boundary,'AL_CAPSULE_DRIFT:'+identity
 # Historical capsules are immutable dependencies captured in the AL boundary.
 # Their data hashes are recorded in UTC by the unchanged installation engine.
 zone=cur.execute('show timezone').fetchone()[0];cur.execute("select set_config('TimeZone','UTC',true)")
 try:
  from psycopg import sql
  names=cur.execute("select relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind='r' and relname like 'cp6%rollback_capsule' and relname<>'cp6_v2620al_rollback_capsule' order by 1").fetchall()
  for (name,) in names:
   ac._capsule_security(cur,'erp.'+name)
   digest=cur.execute(sql.SQL("""select encode(extensions.digest(convert_to(coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),'sha256'),'hex') row_hash from erp.{} t) rows""").format(sql.Identifier(name))).fetchone()[0]
   assert digest==boundary[name],'AL_INHERITED_CAPSULE_DRIFT:'+name
 finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))
 if pre_admission:return objects
 assert ac._verify_installation_state(cur)
 objects.update(ac._verify_views(cur,ac.pins()));objects.update(ac._verify_defaults(cur,ac.pins()))
 assert len(objects)==690,'AL_RUNTIME_CARDINALITY'
 return objects
