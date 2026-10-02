"""Native cutting source bridge, separate from the untrained yield model."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'scripts/cp7-src/cutting-yield/source.sql'
def extension():return FILE.read_text()
def verify(cur):
 rows=cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_cutting_yield'").fetchall()
 assert len(rows)==7,rows
 for signature,owner,definer,config in rows:
  assert owner=='cp7_capture'and not definer and 'search_path=""'in(config or[]),(signature,owner,definer,config)
  for who in ('anon','authenticated','service_role'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature)).fetchone()[0]
 for signature in ('public.erp_cp7_capture_cutting_yield_v1(jsonb,uuid)','public.erp_cp7_read_cutting_yield_v1(uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==('cp7_capture',True,'v',['search_path=""'])
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')and not has_function_privilege('anon',%s,'EXECUTE')and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()[0]
 assert cur.execute("select relrowsecurity from pg_class where oid='cp7_cutting_yield.runs'::regclass").fetchone()[0]
 assert cur.execute("select tgtype,tgenabled,tgfoid='cp7_private.immutable_run()'::regprocedure from pg_trigger where tgrelid='cp7_cutting_yield.runs'::regclass and tgname='cutting_yield_original_immutable'").fetchone()==(27,'O',True)
 for who in ('anon','authenticated','service_role'):
  assert not cur.execute("select has_schema_privilege(%s,'cp7_cutting_yield','USAGE')or has_table_privilege(%s,'cp7_cutting_yield.runs','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,who)).fetchone()[0]
 return dict(stage='NATIVE_CUTTING_SOURCE_ONLY',source_sha256=hashlib.sha256(FILE.read_bytes()).hexdigest(),trained_model=False,full_family_acceptance=False,production_go=False)
