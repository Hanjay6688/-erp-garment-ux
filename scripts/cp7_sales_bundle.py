"""P11 bounded sales reader on the explicit P09 development stack."""
from pathlib import Path
import hashlib
import re
import cp7_procurement_bundle
ROOT=Path(__file__).resolve().parents[1]
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.bf_commercial_sku_at_v1(uuid,timestamptz)')
ANCHOR=' v_app_role:=erp.current_app_role();'
EARLY_ANCHOR=" if v_jwt_role='service_role' then return;end if;"
ADMISSION=""" if exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
   then cp7_sales.command_allowed(c.action) else false end) then return;end if;
"""
def early_admission(definition):
 assert definition.count(ANCHOR)==1 and definition.count(EARLY_ANCHOR)==1 and 'cp7_sales.command_context' not in definition
 # Only take the early branch when every preceding private context for this
 # backend/transaction is absent. Any row (even another actor or invalid
 # action) preserves the entire original dispatch and fine-refusal precedence.
 tables=re.findall(r'\bfrom\s+([a-z0-9_]+\.[a-z0-9_]*context)\s+c\b',definition.split(ANCHOR,1)[0])
 required=['erp.cutting_bridge_execution_context','erp.bs_resolution_execution_context','erp.cp6_laundry_qc_execution_context','cp7_procurement.execution_context','cp7_material.execution_context','cp7_supplier_return.execution_context']
 optional=['cp7_payroll.execution_context','cp7_payroll.settlement_context','cp7_attendance.command_context']
 assert tables==required or tables==required+optional,('CP7_SALES_PRECEDING_CONTEXT_DISPATCH_CHANGED',tables)
 empty='not exists('+ ' union all '.join('select 1 from '+t+' before_sales where before_sales.backend_pid=pg_backend_pid() and before_sales.transaction_id=txid_current()' for t in tables)+')'
 early=ADMISSION.replace("   then cp7_sales.command_allowed(c.action)","   and "+empty+"\n   then cp7_sales.command_allowed(c.action)")
 assert early!=ADMISSION
 return early
def patched_internal(definition):
 early=early_admission(definition)
 return definition.replace(EARLY_ANCHOR,EARLY_ANCHOR+'\n'+early,1).replace(ANCHOR,ADMISSION+ANCHOR,1)
def admission():
 old_body=(ROOT/'scripts/cp7-src/procurement/accepted-deltas.sql').read_text().split('as $function$',1)[1].split('$function$',1)[0]
 assert old_body.count(ANCHOR)==1
 old_hash=hashlib.sha256(old_body.encode()).hexdigest()
 return """do $patch$ declare old_definition text;begin
 if(select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure)<>'"""+old_hash+"""' then raise exception 'CP7_SALES_ADMISSION_PREDECESSOR_CHANGED';end if;
 old_definition:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(replace(old_definition,$early_anchor$"""+EARLY_ANCHOR+"""$early_anchor$,$early_delta$"""+EARLY_ANCHOR+'\n'+early_admission(old_body)+"""$early_delta$),$anchor$"""+ANCHOR+"""$anchor$,$delta$"""+ADMISSION+ANCHOR+"""$delta$);
end $patch$;"""
def extension():return '\n'.join((ROOT/'scripts/cp7-src/sales'/p).read_text() for p in ('read.sql','drafts.sql','commands.sql','form.sql','payments.sql','returns.sql','payment-correction.sql'))+'\n'+admission()
def bundle():return cp7_procurement_bundle.bundle()+'\n'+extension()
