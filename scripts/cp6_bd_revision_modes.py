"""BD revision: real Auth revocation and BD+BE races. Writer evidence only."""
import uuid
from datetime import timedelta
import cp6_bd_probe as b
import cp6_bd_modes as bd
import cp6_be_modes as be


def cases(cur,today):
    # New oracle cases on the combined BD+BE source, in addition to the BD-only T1.
    return [(k,lambda f=f:f(cur,b.case_day(today))) for k,_,f in b.PLAN if k.startswith('REV:')]


def races(tools,today):return bd.races(tools,today)+be.races(tools,today)


def http_cases(http,today):
    def revoked():
        with http.connect() as conn,conn.cursor() as cur:
            with bd._fixture_usage(cur):
                fx=b.fixture(cur,today-timedelta(days=1),'REV-HTTP');b.process_rate(cur,fx,'1731.29')
                line=b.receipt_line(cur,b.receive(cur,b.plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
            conn.commit()
        actor=http.login('ADMIN','bd-revoked-admin')
        args=dict(p_action='SAVE_INVOICE_DRAFT',p_client_request_id=str(uuid.uuid4()),p_payload=dict(vendor_id=fx['vendor'],
            invoice_number='REV-HTTP-'+uuid.uuid4().hex[:10],invoice_date=str(fx['day']),header_total='1731.29',
            lines=[dict(line_kind='BILL',receipt_line_id=line,category='GOOD',qty=1,amount='1731.29')]))
        first=actor.rpc('erp_save_laundry_bd_action_v1',args);again=actor.rpc('erp_save_laundry_bd_action_v1',args)
        assert first['status']==200,first
        with http.connect() as conn,conn.cursor() as cur:
            role=b.one(cur,'select role_id from erp.app_users where auth_user_id=%s',actor.auth_user_id)
            grants=b.q(cur,"select role_id,permission_key,granted_by,granted_at from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.manage','finance.hpp.view')",role)
            assert any(x[1]=='finance.hpp.manage' for x in grants)
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.manage','finance.hpp.view')",(role,));conn.commit()
        try:
            cached=actor.rpc('erp_save_laundry_bd_action_v1',args)
            fresh=actor.rpc('erp_save_laundry_bd_action_v1',dict(args,p_client_request_id=str(uuid.uuid4())))
            hidden=actor.rpc('erp_get_laundry_bd_workspace_v1',dict(p_filters=dict(vendor_id=fx['vendor'])))
        finally:
            with http.connect() as conn,conn.cursor() as cur:
                cur.executemany('insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at) values(%s,%s,%s,%s)',grants);conn.commit()
        restored=actor.rpc('erp_save_laundry_bd_action_v1',args)
        with http.connect() as conn,conn.cursor() as cur:
            count=b.one(cur,'select count(*) from erp.bd_laundry_invoices_v1 where vendor_id=%s',fx['vendor']);conn.rollback()
        return b.verdict(dict(authorized=again['status']==200 and again['body'].get('replayed') is True,
            current_permission_cached=cached['status']>=400 and 'header_total' not in cached['body'],
            current_permission_fresh=fresh['status']>=400,hidden=hidden['status']==200 and hidden['body']['invoices'] is None,
            restored=restored['status']==200 and restored['body'].get('replayed') is True,one_effect=count==1),
            http=dict(cached=cached,fresh=fresh),invoice_count=count)
    return bd.http_cases(http,today)+be.http_cases(http,today)+[('BD_REV_HTTP:REVOKED_PERMISSION_REPLAY_NO_MONEY',revoked)]
