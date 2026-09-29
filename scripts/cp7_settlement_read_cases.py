"""Finance review proof; native actions are controls, not connected settlement writes."""
from decimal import Decimal
import json,uuid
import cp7_nota_cases as nota
source,auth,b=nota.source,nota.auth,nota.b

def read(cur,section='PAYROLLS',subject=None,**q):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_payroll_workspace_v1(%s,%s)',(section,json.dumps(q))).fetchone()[0];b.api.admin(cur);return r

def fixture(cur,today):
    f=source.repair(cur,today);source.ax.post(cur,source.ax.repair_payload(f,1));n=nota.command(cur,'SAVE',nota.payload(cur,f,today));n=nota.act(cur,'POST',n);return dict(f,note=n['note_id'],payroll=n['payroll_id'])

def cases(cur,today):
    def exact():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);w=read(cur,id=f['payroll']);d=w['page']['rows'][0]
        assert d['status']=='CALCULATED' and d['totals_match_items'] and d['labor_total']==d['net_payable']=='6000.00' and d['counts']==dict(work='2',attendance='0',reimbursements='0',deductions='0',notes='1'),d
        a=read(cur,'WORK',id=f['payroll'],limit=1);z=read(cur,'WORK',id=f['payroll'],limit=1,offset=1)
        assert a['document']==z['document']==d and a['page']['total']==z['page']['total']=='2' and a['page']['next_offset']==1 and z['page']['next_offset'] is None
        rows=a['page']['rows']+z['page']['rows'];assert sum(Decimal(x['amount']) for x in rows)==6000 and sum(int(x['qty']) for x in rows)==3
        notes=read(cur,'NOTES',id=f['payroll']);assert notes['page']['rows'][0]['id']==f['note'] and notes['page']['rows'][0]['amount']=='6000.00'
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',source_note_and_two_native_work_items=True,full_header_totals_not_page_subtotal=True,read_has_no_mutations=True,labor='6000',qty=3)
    def dates_and_token():
        f=fixture(cur,today);zone=cur.execute('show timezone').fetchone()[0];docs=[]
        for tz in ('Asia/Jakarta','UTC','America/Los_Angeles'):
            cur.execute("select set_config('TimeZone',%s,true)",(tz,));docs.append(read(cur,id=f['payroll'])['page']['rows'][0])
        cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert docs[0]==docs[1]==docs[2]
        before=docs[0]
        # Administrative external-child-edit control: header is deliberately not
        # recalculated, so review must reveal stale totals and a changed token.
        cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,amount,notes) values(%s,'OTHER',1,'Administrative child-token control')",(f['payroll'],))
        after=read(cur,id=f['payroll'])['page']['rows'][0]
        assert after['row_version']==before['row_version'] and after['review_token']!=before['review_token'] and not after['totals_match_items']
        assert after['deduction_total']=='0.00' and read(cur,'DEDUCTIONS',id=f['payroll'])['page']['rows'][0]['amount']=='1.00'
        return dict(status='PASS',canonical_header_and_token_three_timezones=True,administrative_child_edit_control=True,stale_native_header_total_not_silently_recalculated=True,child_change_invalidates_review_without_header_version_change=True)
    def access():
        f=fixture(cur,today);ops,role=source.procurement.custom(cur,('production.fg_handoff.view','production.fg_handoff.post'))
        auth.refused(cur,lambda:read(cur,id=f['payroll'],subject=ops),'CP7_PAYROLL_ACCESS_DENIED')
        finance,r=source.procurement.custom(cur,('finance.payroll.view',));w=read(cur,id=f['payroll'],subject=finance)
        assert w['capabilities']==dict(approve=False,pay=False) and w['page']['rows'][0]['net_payable']=='6000.00'
        assert read(cur,'NOTES',id=f['payroll'],subject=finance)['page']['rows'][0]['id']==f['note']
        cur.execute("delete from erp.app_role_permissions where role_id=%s",(r,));auth.refused(cur,lambda:read(cur,id=f['payroll'],subject=finance),'CP7_PAYROLL_ACCESS_DENIED')
        auth.refused(cur,lambda:read(cur,'WORK',id=f['payroll'],q='partial'),'CP7_PAYROLL_QUERY')
        auth.refused(cur,lambda:read(cur,'WORK',id=str(uuid.uuid4())),'CP7_PAYROLL_MISSING')
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_payroll_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        return dict(status='PASS',finance_read_without_production_permission=True,ops_denied_money_workspace=True,current_revocation=True,closed_queries_and_missing_parent=True,no_erp_business_dml=True)
    def reversed_history():
        f=fixture(cur,today);d=read(cur,id=f['payroll'])['page']['rows'][0];before=nota.facts(cur)
        b.chain.production.owner(cur);cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(f['payroll'],'P12 native lifecycle read control'));b.api.admin(cur)
        after=read(cur,id=f['payroll'])['page']['rows'][0];n=read(cur,'NOTES',id=f['payroll'])['page']['rows'][0]
        assert after['status']=='REVERSED' and after['review_token']!=d['review_token'] and after['labor_total']=='6000.00' and n['status']=='POSTED' and n['payroll_status']=='REVERSED'
        assert read(cur,'PAYROLLS',id=f['payroll'],status='CALCULATED')['page']['total']=='0'
        assert nota.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['total']=='2' and nota.facts(cur)==before
        return dict(status='PASS',native_cancel_control_not_connected_settlement_writer=True,source_released_history_retained=True,old_total_not_current_payable_claim=True,status_filter_current=True)
    return [('P12_PAYROLL_READ_'+k,fn) for k,fn in [('EXACT_PAGES',exact),('TOKEN_TIMEZONE',dates_and_token),('ACCESS',access),('REVERSED_HISTORY',reversed_history)]]

def http_cases(http,today):
    def finance():
        user=http.login('ADMIN','p12-payroll-review')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.payroll.view')",(role,));before=nota.facts(cur);conn.commit()
        args=dict(p_section='PAYROLLS',p_query=dict(id=f['payroll']));r=user.rpc('erp_cp7_get_payroll_workspace_v1',args)
        assert r['status']==200 and r['body']['page']['rows'][0]['net_payable']=='6000.00',r
        assert r['body']['capabilities']==dict(approve=False,pay=False)
        assert http.anon_rpc('erp_cp7_get_payroll_workspace_v1',args)['status'] in (401,403)
        with http.connect() as conn,conn.cursor() as cur:
            assert nota.facts(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert user.rpc('erp_cp7_get_payroll_workspace_v1',args)['status']==403
        return dict(status='PASS',real_auth_postgrest_finance_read=True,native_value='6000.00',finance_view_not_approve_or_pay=True,no_read_business_effect=True,current_deactivation=True)
    return [('P12_PAYROLL_READ_HTTP',finance)]
