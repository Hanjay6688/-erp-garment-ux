"""P12 attendance source adapter; native save/preview/post/reverse formulas retained."""
import hashlib
import cp7_roster_bundle as roster
import cp7_settlement_bundle as settlement
import cp7_nota_bundle as nota
ROOT=roster.ROOT
CONTEXT="""  if exists(select 1 from cp7_attendance.command_context c where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
    and erp.has_permission('finance.attendance.view') and erp.has_permission(c.permission)
    and(not c.owner_required or erp.current_app_role() in('OWNER','ADMIN'))
  ) then return;end if;
"""
def patched_internal(d):
    assert d.count(nota.ANCHOR)==1 and 'cp7_attendance.command_context' not in d
    return d.replace(nota.ANCHOR,CONTEXT+nota.ANCHOR)
def extension():
    expected=settlement.expected_internal().replace(nota.ANCHOR,settlement.CONTEXT+nota.ANCHOR)
    guard="""do $verify$ begin
 if(select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure)<>'%s' then raise exception 'CP7_ATTENDANCE_PREDECESSOR_CHANGED';end if;
end $verify$;"""%hashlib.sha256(expected.encode()).hexdigest()
    patch="""do $patch$ declare d text;begin
 d:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(d,$anchor$%s$anchor$,$delta$%s$delta$);
end $patch$;"""%(nota.ANCHOR,CONTEXT+nota.ANCHOR)
    return '\n'.join((guard,(ROOT/'scripts/cp7-src/payroll/attendance-write.sql').read_text(),patch))
def bundle():return roster.bundle()+'\n'+extension()
RULES={**roster.RULES,'command_access':('cp7_attendance_read',True,'s'),'validate_command':('cp7_attendance_write',False,'i'),'apply_command':('postgres',True,'v'),'attendance_command':('cp7_attendance_write',False,'v')}
