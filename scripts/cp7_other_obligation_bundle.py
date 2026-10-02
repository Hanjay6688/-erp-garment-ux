"""Exact delegated Native obligation readers, composed into current rule v2."""
import hashlib
import cp7_rule_source_bundle as previous
ROOT=previous.ROOT
FILES=('reminders/other-obligation-source.sql',*previous.FILES)
ROLES=('cp7_obligation_read',*previous.ROLES)
READ_TABLES=('erp.opening_subledger_balances','erp.opening_balance_items','erp.opening_balance_headers',
 'erp.initial_import_financial_sources','erp.customers','erp.suppliers','erp.contractors','erp.laundry_vendors',
 'erp.bc_lot_events_v1','erp.bc_documents_v1','erp.payroll_reimbursements','erp.payroll_settlements','erp.vendor_invoices',
 'erp.laundry_receipt_lines','erp.laundry_receipts','erp.laundry_delivery_lines','erp.laundry_deliveries',
 'erp.bd_opening_laundry_uninvoiced_v1','erp.bd_laundry_invoice_lines_v1','erp.bd_laundry_invoices_v1')
GRANTS={k:set(v)for k,v in previous.GRANTS.items()}
GRANTS['cp7_obligation_read']={'auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)',
 'erp.bb_financial_workspace_v1(uuid)','erp.bb_opening_balance_context_v1(uuid)','erp.bd_vendor_payables_v1(uuid)',
 'erp.bc_carry_remaining_v1(uuid)','erp.bd_receipt_page_v1(uuid,uuid,timestamp with time zone)',
 'erp.bd_receipt_invoiced_v1(uuid)','erp.bd_opening_invoiced_v1(uuid)','erp.bd_opening_billed_v1(uuid)',
 'erp.bd_opening_released_v1(uuid)','public.erp_cp7_get_payroll_workspace_v1(text,jsonb)',
 'public.erp_cp7_get_payroll_installments_v1(jsonb)'}
TABLE_GRANTS={**previous.TABLE_GRANTS,'cp7_obligation_read':{name:'SELECT'for name in READ_TABLES}}
OTHER_FUNCTIONS=dict(other_access='s',other_money='i',other_document='i',other_opening='s',other_payroll='s',
 other_accessory='s',other_laundry='s',other_laundry_pending='s',other_obligation_source='s')
FUNCTIONS={**previous.FUNCTIONS,**OTHER_FUNCTIONS,'condition_domain':'i','condition_domain_access':'s'}
CONTRACTS={name:('cp7_obligation_read',name=='other_obligation_source')for name in OTHER_FUNCTIONS}
def extension():return previous.previous.extension()+'\n'+'\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return previous.previous.predecessor.bundle()+'\n'+extension()
def verify(cur,extension_functions=None,extension_tables=(),extension_public=()):
 previous.previous.verify(cur,{**FUNCTIONS,**(extension_functions or{})},(*previous.TABLES,*extension_tables),(*previous.PUBLIC,*extension_public),CONTRACTS)
 for name in previous.TABLES:
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and not tgisinternal",('cp7_reminder_native.'+name,)).fetchone()[0]==1
 assert cur.execute("select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname='cp7_obligation_read'").fetchone()==(False,False,False,False,False,False,True)
 assert not cur.execute("select has_schema_privilege('cp7_obligation_read','cp7_reminder_native','CREATE')or has_schema_privilege('cp7_obligation_read','erp','CREATE')or has_schema_privilege('cp7_obligation_read','public','CREATE')").fetchone()[0]
 assert not cur.execute("select exists(select 1 from pg_auth_members where member='cp7_obligation_read'::regrole)").fetchone()[0]
 reads=cur.execute("select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_obligation_read',c.oid,'SELECT')order by 1").fetchall()
 assert reads==[(name,)for name in sorted(READ_TABLES)],reads
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_obligation_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 for principal in('anon','authenticated','service_role','cp7_reminder'):
  assert not cur.execute("select pg_has_role(%s,'cp7_obligation_read','MEMBER')",(principal,)).fetchone()[0]
 assert cur.execute("select has_function_privilege('cp7_reminder','cp7_reminder_native.other_obligation_source()','EXECUTE')").fetchone()[0]
 return dict(stage='CURRENT_RULE_V2_ALL_NATIVE_OBLIGATION_DOMAINS_UNKNOWN_RETAINED_PRIVATE_LOCAL_SINK',
  source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
