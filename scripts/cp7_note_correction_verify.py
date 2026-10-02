"""Closed owning command, immutable lineage and unchanged accepted Native helpers."""
import hashlib
import cp7_f03_bundle as bundle

SIGNATURES=(
 'erp.reverse_fg_movement(uuid,text)',
 'erp._cp3_r4_reverse_journal_internal(uuid,text)',
 'erp.reverse_journal(uuid,text)',
 'erp.reverse_sale(uuid,text)',
 'erp.reverse_sales_return(uuid,text)',
 'erp.reverse_sales_payment(uuid,text)',
)

def verify(cur):
 rows=dict(cur.execute('select native_signature,native_definition_sha256 from cp7_note.helper_sources').fetchall())
 assert set(rows)==set(SIGNATURES),'NOTE_NATIVE_SOURCE_SET_CHANGED'
 for signature in SIGNATURES:
  definition=cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
  assert hashlib.sha256(definition.encode()).hexdigest()==rows[signature],('NOTE_NATIVE_DEFINITION_CHANGED',signature)
  private=signature.replace('erp.','cp7_note.',1)
  owner,secdef,body=cur.execute('select pg_get_userbyid(proowner),prosecdef,prosrc from pg_proc where oid=%s::regprocedure',(private,)).fetchone()
  assert owner=='postgres' and secdef and 'perform cp7_note.require_context();'in body,('NOTE_SCOPED_HELPER',private)
 for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_fg_write'):
  assert not cur.execute("select has_schema_privilege(%s,'cp7_note','USAGE')",(who,)).fetchone()[0],('NOTE_PRIVATE_SCHEMA',who)
  for signature in SIGNATURES:
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature.replace('erp.','cp7_note.',1))).fetchone()[0],('NOTE_PRIVATE_HELPER',who,signature)
  for table in ('cp7_note.requests','cp7_note.revisions','cp7_note.context','cp7_note.helper_sources','cp7_fg.correction_movements'):
   assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,table)).fetchone()[0],('NOTE_PRIVATE_TABLE',who,table)
 for signature in ('public.erp_cp7_get_note_correction_v1(uuid)','public.erp_cp7_correct_note_v1(jsonb,uuid,text)'):
  assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure",(signature,)).fetchone()==('cp7_sales_write',True,'v',['search_path=""']),('NOTE_PUBLIC_OWNER',signature)
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE') and not has_function_privilege('anon',%s,'EXECUTE') and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()==(True,)
 assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid='public.erp_cp7_get_fg_book_v2(jsonb)'::regprocedure").fetchone()==('cp7_fg_read',True,'s',['search_path=""'])
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_sales_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 return dict(owning_note_source_sha256=hashlib.sha256((bundle.ROOT/'scripts/cp7-src/sales/correction.sql').read_bytes()).hexdigest(),accepted_six_native_helpers_unchanged=True,private_helpers_not_callable=True,original_financial_and_stock_rules_retained=True,production_go=False)
