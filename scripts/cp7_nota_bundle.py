"""Nota composer extension over the source-qualified P12 stack; candidate only."""
import hashlib
import cp7_payroll_bundle
ROOT=cp7_payroll_bundle.ROOT
FILES=('notes.sql','note-read.sql','note-ownership.sql')
ANCHOR=' v_app_role:=erp.current_app_role();'
ADMISSION=""" if exists(select 1 from cp7_payroll.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
  and c.action='POST_NOTE' and c.permission_key='production.fg_handoff.post'
  and erp.has_permission('production.fg_handoff.view') and erp.has_permission(c.permission_key)) then return;end if;
"""
def patched_internal(definition):
    assert definition.count(ANCHOR)==1 and 'cp7_payroll.execution_context' not in definition
    return definition.replace(ANCHOR,ADMISSION+ANCHOR)
def admission():
    old_body=(ROOT/'scripts/cp7-src/procurement/accepted-deltas.sql').read_text().split('as $function$',1)[1].split('$function$',1)[0]
    assert old_body.count(ANCHOR)==1
    old_hash=hashlib.sha256(old_body.encode()).hexdigest()
    return """do $patch$ declare old_definition text; begin
 if (select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure) <> '"""+old_hash+"""' then raise exception 'CP7_NOTA_ADMISSION_PREDECESSOR_CHANGED';end if;
 old_definition:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(old_definition,$anchor$"""+ANCHOR+"""$anchor$,$delta$"""+ADMISSION+ANCHOR+"""$delta$);
end $patch$;"""
def extension():
    return '\n'.join((ROOT/'scripts/cp7-src/payroll'/f).read_text() for f in FILES)+'\n'+admission()
def bundle():
    return cp7_payroll_bundle.bundle()+'\n'+extension()
