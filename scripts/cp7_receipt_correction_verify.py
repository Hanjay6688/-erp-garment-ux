"""Closed owning receipt-correction command and private metadata; unchanged Native writers."""
import hashlib
import cp7_receipt_correction_bundle as bundle

TABLES=('requests','revisions','roll_lineage','movement_lineage','journal_restatements','payment_replays','ledger_links','invoice_replays','invoice_restatements','context','name_requests','material_names')
PRIVATE=('cp7_receipt_fix.access_now()','cp7_receipt_fix.admit(text)','cp7_receipt_fix.review_token(uuid)','cp7_receipt_fix.roll_use(uuid,uuid)','cp7_receipt_fix.location_floor(uuid,uuid,timestamptz)','cp7_receipt_fix.shifted_floor(uuid,uuid,uuid,timestamptz,timestamptz,numeric)',
 'cp7_receipt_fix.blockers(uuid)','cp7_receipt_fix.restate(uuid,text)','cp7_receipt_fix.restate_all(text)','cp7_receipt_fix.journal_net(uuid[])',
 'cp7_receipt_fix.reverse_invoice(uuid,text,uuid)','cp7_receipt_fix.payment_snapshot(uuid)','cp7_receipt_fix.replay_payment(uuid,jsonb,numeric,text,text)','cp7_receipt_fix.command(jsonb,uuid,text)','cp7_receipt_fix.workspace(uuid)',
 'cp7_receipt_fix.name_access(text)','cp7_receipt_fix.identity(uuid)','cp7_receipt_fix.name_workspace(uuid)','cp7_receipt_fix.rename(jsonb,uuid,text)')

def verify(cur):
 for t in TABLES:
  assert cur.execute("select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass",('cp7_receipt_fix.'+t,)).fetchone()==('postgres',True),('RF_PRIVATE_METADATA_OWNER',t)
  for who in ('anon','authenticated','service_role','cp7_capture','cp7_procure_read','cp7_procure_write'):
   assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,'cp7_receipt_fix.'+t)).fetchone()[0],('RF_PRIVATE_TABLE',who,t)
 for f in PRIVATE:
  assert cur.execute("select pg_get_userbyid(proowner) from pg_proc where oid=%s::regprocedure",(f,)).fetchone()[0]=='postgres',('RF_PRIVATE_OWNER',f)
  for who in ('anon','authenticated','service_role','cp7_capture','cp7_procure_read'):
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,f)).fetchone()[0],('RF_PRIVATE_FUNCTION',who,f)
 owners={'public.erp_cp7_get_receipt_correction_v1(uuid)':('cp7_procure_write','v'),'public.erp_cp7_correct_receipt_v1(jsonb,uuid,text)':('cp7_procure_write','v'),
  'public.erp_cp7_get_material_ledger_v2(uuid,uuid,uuid,integer,integer)':('cp7_material_read','s'),
  'public.erp_cp7_get_material_name_v1(uuid)':('cp7_procure_write','v'),'public.erp_cp7_rename_material_v1(jsonb,uuid,text)':('cp7_procure_write','v')}
 for f,(owner,vol) in owners.items():
  assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure",(f,)).fetchone()==(owner,True,vol,['search_path=""']),('RF_PUBLIC_OWNER',f)
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE') and not has_function_privilege('anon',%s,'EXECUTE') and not has_function_privilege('service_role',%s,'EXECUTE')",(f,f,f)).fetchone()==(True,),('RF_PUBLIC_GRANT',f)
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_procure_write',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE'))").fetchone()[0],'RF_LOW_WRAPPER_NATIVE_DML'
 return dict(receipt_correction_source_sha256=bundle.sha256(),private_metadata_postgres_rls=True,private_functions_not_callable=True,public_wrappers_authenticated_only=True,native_writers_unchanged=True,production_go=False)
