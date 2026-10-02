"""P11 bounded sales reader on the explicit P09 development stack."""
from pathlib import Path
import hashlib
import cp7_procurement_bundle
ROOT=Path(__file__).resolve().parents[1]
GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','erp.bf_commercial_sku_at_v1(uuid,timestamptz)')
ANCHOR=' v_app_role:=erp.current_app_role();'
ADMISSION=""" if exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
   and c.action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
   then cp7_sales.command_access(c.action) is not null else false end) then return;end if;
"""
def patched_internal(definition):
 assert definition.count(ANCHOR)==1 and 'cp7_sales.command_context' not in definition
 return definition.replace(ANCHOR,ADMISSION+ANCHOR)
def admission():
 old_body=(ROOT/'scripts/cp7-src/procurement/accepted-deltas.sql').read_text().split('as $function$',1)[1].split('$function$',1)[0]
 assert old_body.count(ANCHOR)==1
 old_hash=hashlib.sha256(old_body.encode()).hexdigest()
 return """do $patch$ declare old_definition text;begin
 if(select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure)<>'"""+old_hash+"""' then raise exception 'CP7_SALES_ADMISSION_PREDECESSOR_CHANGED';end if;
 old_definition:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(old_definition,$anchor$"""+ANCHOR+"""$anchor$,$delta$"""+ADMISSION+ANCHOR+"""$delta$);
end $patch$;"""
def extension():return '\n'.join((ROOT/'scripts/cp7-src/sales'/p).read_text() for p in ('read.sql','drafts.sql','commands.sql','form.sql','payments.sql','returns.sql'))+'\n'+admission()
def bundle():return cp7_procurement_bundle.bundle()+'\n'+extension()
