"""R3-03 / owner D16-5: "Tutup Periode" is the "Tutup Buku" tab of "Laporan & Tutup Buku", spliced into the CP17 harness.

The merged page keeps the full history of close and reopen. The facade reads it from the Native audit rows the accepted
writers erp.close_accounting_through / erp.reopen_accounting_through record for the control row; the oracle here reads the
same rows directly (erp.audit_logs, erp.app_users) and derives CLOSE/REOPEN itself. Rights stay separate: the report needs
finance.reports.view, the tab and the facade also need finance.period_close.manage (seeded ADMIN has the first, not the
second), so ADMIN reads the report but is refused the period workspace, natively and over real Auth, and in the browser
ADMIN sees no "Tutup Buku" tab while OWNER does.
"""
from datetime import datetime
import json,uuid
import cp7_period_cases as period
import cp7_master_cases as master
b,auth=period.b,period.auth

NATIVE=['CP17_R3_03_PERIOD_HISTORY_FROM_NATIVE_AUDIT','CP17_R3_03_PERIOD_TAB_RIGHTS_ADMIN_REFUSED']
RACES=[]
HTTP=['CP17_HTTP_R3_03_PERIOD_HISTORY_AND_RIGHTS']
BROWSER=['CP17_BROWSER_R3_03_PERIOD_TAB_DESKTOP','CP17_BROWSER_R3_03_PERIOD_TAB_MOBILE']

def oracle(cur):
    """The 50 latest Native audit rows of the control row, newest first, with CLOSE when the date moved later."""
    b.api.admin(cur);out=[]
    for at,old,new,by,reason in cur.execute("""select l.changed_at,(l.old_data->>'closed_through')::date,(l.new_data->>'closed_through')::date,u.full_name,l.change_reason
        from erp.audit_logs l left join erp.app_users u on u.id=l.changed_by where l.entity_type='accounting_period_control'
        order by l.changed_at desc,l.id desc limit 50""").fetchall():
        out.append(dict(at=at,action='CLOSE' if new is not None and(old is None or new>old)else 'REOPEN',
                        **{'from':None if old is None else str(old)},to=None if new is None else str(new),by=by,reason=reason))
    return out
def shown(history):return [dict(h,at=datetime.fromisoformat(h['at']))for h in history]

def cases(cur,today):
    def history():
        f,day,initial=period.ready(cur,today);start=initial['control']['closed_through'];tag=uuid.uuid4().hex[:8]
        reasons=[f'R3-03 tutup {tag}',f'R3-03 buka kembali {tag}',f'R3-03 tutup lagi {tag}']
        period.command(cur,'CLOSE',dict(period.intent(initial),reason=reasons[0]))
        period.command(cur,'REOPEN',dict(period.intent(period.read(cur,day),'REOPEN',start),reason=reasons[1]))
        period.command(cur,'CLOSE',dict(period.intent(period.read(cur,day)),reason=reasons[2]))
        before=b.boundary.snapshot(cur);w=period.read(cur,day);assert b.boundary.snapshot(cur)==before
        want=oracle(cur);assert shown(w['history'])==want,(w['history'][:3],want[:3])
        top=want[:3];assert [h['reason']for h in top]==reasons[::-1] and [h['action']for h in top]==['CLOSE','REOPEN','CLOSE'],top
        assert top[0]['to']==str(day) and top[0]['from']==start and top[1]['to']==start and top[2]['to']==str(day) and w['control']['closed_through']==str(day)
        assert len(w['history'])<=50 and all(h['by']for h in top)
        return dict(status='PASS',finding='R3-03',owner_decision='D16-5',history_equals_native_audit_rows=True,three_changes_newest_first=['CLOSE','REOPEN','CLOSE'],
                    read_is_side_effect_free=True,rows=len(want))
    def rights():
        f,day,state=period.ready(cur,today);admin=master.role_actor(cur,'ADMIN');b.api.admin(cur)
        perms=set(x for (x,)in cur.execute("""select p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id
            where r.role_code='ADMIN' and p.permission_key in('finance.reports.view','finance.period_close.manage')""").fetchall())
        assert perms=={'finance.reports.view'},perms
        before=b.boundary.snapshot(cur);d=str(day)
        auth.actor(cur,admin);report=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps({'from':d,'to':d,'as_of':d}),)).fetchone()[0];b.api.admin(cur)
        assert report.get('close_preflight') is None and report['snapshot']['basis']['balance_sheet_as_of']==d,report.get('close_preflight')
        auth.refused(cur,lambda:period.read(cur,day,admin),'CP7_PERIOD_ACCESS_DENIED')
        auth.refused(cur,lambda:period.command(cur,'CLOSE',period.intent(state),subject=admin),'CP7_PERIOD_ACCESS_DENIED')
        assert b.boundary.snapshot(cur)==before and period.read(cur,day)['control']==state['control']
        return dict(status='PASS',finding='R3-03',owner_decision='D16-5',seeded_ADMIN_has_report_view_not_close=True,ADMIN_workspace_and_close_refused=True,
                    no_effect=True,report_right_and_close_right_separate=True)
    return [(NATIVE[0],history),(NATIVE[1],rights)]

def races(tools,today):return []

def http_cases(http,today):
    def history_and_rights():
        owner=http.login('OWNER','cp17-r3-03-owner');admin=http.login('ADMIN','cp17-r3-03-admin')
        day=str(today)
        w=owner.rpc('erp_cp7_get_period_control_v1',dict(p_through=day));assert w['status']==200,w
        with http.connect()as conn,conn.cursor()as cur:want=oracle(cur)
        assert shown(w['body']['history'])==want,(w['body']['history'][:2],want[:2])
        refused=admin.rpc('erp_cp7_get_period_control_v1',dict(p_through=day))
        assert refused['status']>=400 and 'CP7_PERIOD_ACCESS_DENIED' in json.dumps(refused['body']),refused
        report=admin.rpc('erp_cp7_get_finance_report_v1',dict(p_query={'from':day,'to':day,'as_of':day,'limit':25}));assert report['status']==200 and report['body'].get('close_preflight') is None,report
        return dict(status='PASS',finding='R3-03',owner_decision='D16-5',real_auth=True,owner_history_equals_native_audit_rows=True,rows=len(want),
                    admin_period_refused=True,admin_report_read_without_close_preflight=True)
    return [(HTTP[0],history_and_rights)]

def browser_history(cur,p):
    """For the browser case: what the Tutup Buku tab must show, from the Native rows (newest first, at most 50)."""
    want=oracle(cur)
    return dict(count=len(want),first=None if not want else dict(want[0],at=want[0]['at'].isoformat()))
