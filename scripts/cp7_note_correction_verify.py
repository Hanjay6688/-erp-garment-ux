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
  native_security=cur.execute('select prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()
  owner,secdef,config,body=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig,prosrc from pg_proc where oid=%s::regprocedure',(private,)).fetchone()
  assert owner=='postgres' and (secdef,config)==native_security and 'perform cp7_note.require_context();'in body,('NOTE_SCOPED_HELPER',private,{'owner':owner,'private_security':(secdef,config),'native_security':native_security,'private_context_fence':'perform cp7_note.require_context();'in body})
 report_signature=bundle.note_report.SIGNATURE
 original,original_hash,overlay_hash=cur.execute('select original_definition,original_sha256,overlay_sha256 from cp7_note.report_sources where native_signature=%s',(report_signature,)).fetchone()
 assert hashlib.sha256(original.encode()).hexdigest()==original_hash,'NOTE_NATIVE_REPORT_ORIGINAL_HASH'
 overlay=bundle.note_report.patched_report(original)
 assert hashlib.sha256(overlay.encode()).hexdigest()==overlay_hash,'NOTE_NATIVE_REPORT_DECLARED_DELTA_HASH'
 assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(report_signature,)).fetchone()[0]==overlay,'NOTE_NATIVE_REPORT_EXACT_READ_DELTA'
 for table in ('requests','revisions','context','helper_sources','journal_restatements','payment_replays','report_sources','item_lineage'):
  assert cur.execute("select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass",('cp7_note.'+table,)).fetchone()==('postgres',True),('NOTE_PRIVATE_METADATA_OWNER',table)
 for signature in ('public.erp_cp7_get_sales_v1(jsonb)','cp7_fg.book_anchor(uuid,uuid,text)'):
  assert cur.execute("select has_function_privilege('postgres',%s,'EXECUTE')",(signature,)).fetchone()[0],('NOTE_INTERNAL_COMPOSITION',signature)
 for table,rights in (('cp7_sales.command_context',('INSERT','DELETE')),('cp7_fg.correction_movements',('SELECT','INSERT'))):
  for right in rights:assert cur.execute("select has_table_privilege('postgres',%s,%s)",(table,right)).fetchone()[0],('NOTE_INTERNAL_TABLE_COMPOSITION',table,right)
 for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_fg_write'):
  assert not cur.execute("select has_schema_privilege(%s,'cp7_note','USAGE')",(who,)).fetchone()[0],('NOTE_PRIVATE_SCHEMA',who)
  for signature in SIGNATURES:
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature.replace('erp.','cp7_note.',1))).fetchone()[0],('NOTE_PRIVATE_HELPER',who,signature)
  assert not cur.execute("select has_function_privilege(%s,'cp7_note.report_lifecycle(date,date,text)','EXECUTE')",(who,)).fetchone()[0],('NOTE_PRIVATE_REPORT_HELPER',who)
  for table in ('cp7_note.requests','cp7_note.revisions','cp7_note.context','cp7_note.helper_sources','cp7_note.journal_restatements','cp7_note.payment_replays','cp7_note.report_sources','cp7_note.item_lineage','cp7_fg.correction_movements'):
   assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,table)).fetchone()[0],('NOTE_PRIVATE_TABLE',who,table)
 for table in ('cp7_note.requests','cp7_note.revisions','cp7_note.context','cp7_note.helper_sources','cp7_note.journal_restatements','cp7_note.payment_replays','cp7_note.report_sources','cp7_note.item_lineage'):
  assert not cur.execute("select has_table_privilege('cp7_sales_write',%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(table,)).fetchone()[0],('NOTE_LOW_WRAPPER_NO_METADATA_DML',table)
 for signature in ('public.erp_cp7_get_note_correction_v2(uuid)', 'public.erp_cp7_get_note_correction_v1(uuid)','public.erp_cp7_correct_note_v1(jsonb,uuid,text)'):
  assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure",(signature,)).fetchone()==('cp7_sales_write',True,'v',['search_path=""']),('NOTE_PUBLIC_OWNER',signature)
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE') and not has_function_privilege('anon',%s,'EXECUTE') and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()==(True,)
 assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid='public.erp_cp7_get_fg_book_v2(jsonb)'::regprocedure").fetchone()==('cp7_fg_read',True,'s',['search_path=""'])
 for signature,owner,definer,volatility in (
  ('public.erp_cp7_get_fg_ledger_v2(jsonb)','cp7_fg_read',True,'s'),
  ('cp7_fg.corrected_ledger_rows(uuid,uuid,uuid,text)','cp7_fg_read',False,'s'),
  ('cp7_fg.corrected_ledger(jsonb)','cp7_fg_read',False,'s'),
  ('cp7_note.workspace_with_actors(uuid)','postgres',True,'v')):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==(owner,definer,volatility,['search_path=""']),('NOTE_READ_PROJECTION_OWNER',signature)
  for who in('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,signature)).fetchone()[0],('NOTE_READ_PROJECTION_PRIVATE',signature,who)
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(signature,)).fetchone()[0]==signature.startswith('public.'),('NOTE_READ_PROJECTION_PUBLIC_ONLY',signature)
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_sales_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 for signature in ('cp7_note.bind_items(uuid,uuid,uuid,jsonb,jsonb)','cp7_note.line_origin(uuid,uuid,uuid,uuid,uuid,text)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==('postgres',True,['search_path=""'])
  for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_write'):
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature)).fetchone()[0],('NOTE_PRIVATE_ITEM_LINEAGE',who,signature)
 assert cur.execute("select tgtype,tgenabled,tgfoid='cp7_note.immutable_revision()'::regprocedure from pg_trigger where tgrelid='cp7_note.item_lineage'::regclass and tgname='note_item_lineage_immutable'").fetchone()==(27,'O',True)
 return dict(owning_note_source_sha256=hashlib.sha256((bundle.ROOT/'scripts/cp7-src/sales/correction.sql').read_bytes()).hexdigest(),accepted_six_native_helpers_unchanged=True,exact_owner_report_read_delta=True,native_owner_report_original_sha256=original_hash,native_owner_report_overlay_sha256=overlay_hash,private_helpers_not_callable=True,original_financial_and_stock_rules_retained=True,production_go=False)
