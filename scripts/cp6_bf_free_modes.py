"""Compatibility entrypoint, updated for vendor-native prices (not SKU tariffs).

Historical receipts keep their original filenames/verdicts. A new run exercises
this current suite, including real FREE/WAIVED prices, shipment and HPP.
"""
import json,uuid
from datetime import timedelta
import cp6_bf_free_probe as free
import cp6_bf_range_followup as range_followup
import cp6_bf_vendor_modes as regression
from cp6_bd_modes import _fixture_usage
INSTALL_BF=True
bf=free.bf

def free_cases(cur,today):
    return [('VENDOR_FREE:ALL_FOUR_STATUSES_SKU_EMPTY_REPLAY',lambda:free.master_statuses(cur,today)),
      ('VENDOR_FREE:INVALID_VENDOR_RATES_ATOMIC',lambda:free.atomic_rejections(cur,today)),
      ('VENDOR_FREE:PHYSICAL_16PCS_LABOR_HPP_FROZEN',lambda:free.free_production(cur,today))]

def cases(cur,today):
    return free_cases(cur,today)+[('RANGE:REPEATED_DRAWINGS_ONE_CHOICE_PER_SIZE',lambda:range_followup.repeated_drawings(cur,today))]+regression.cases(cur,today)

# SKU price and vendor tariff contention use the current Native concurrency
# cases. No race payload writes laundry_rates into a SKU.
races=regression.races

def vendor_http_cases(http,today):
    def master():
        with http.connect() as conn,conn.cursor() as cur:
            with _fixture_usage(cur):f=free.master_fixture(cur,True)
            conn.commit()
        owner=http.login('OWNER','vendor-free-owner');staff=http.login('STAFF','vendor-free-staff')
        component=f['rates'][0]['ref_id'];at=f['now']-timedelta(minutes=2)
        payload=dict(component_id=component,rate_status='FREE',rate_per_pcs='0.00',effective_from=at.isoformat(),reason='Real Auth explicit vendor FREE version')
        args=dict(p_action='SAVE_COMPONENT_RATE',p_payload=payload,p_client_request_id=str(uuid.uuid4()))
        anon=http.anon_rpc('erp_save_laundry_bd_action_v1',args);denied=staff.rpc('erp_save_laundry_bd_action_v1',args)
        first=owner.rpc('erp_save_laundry_bd_action_v1',args);assert first['status']==200,first
        again=owner.rpc('erp_save_laundry_bd_action_v1',args)
        def state():
            with http.connect() as conn,conn.cursor() as cur:
                out=cur.execute('select id::text,rate_status,rate_per_pcs,effective_from,effective_to,reason from erp.bd_laundry_component_rates_v1 where component_id=%s order by id',(component,)).fetchall();conn.rollback();return out
        before=state();checks=dict(anonymous_refused=anon['status'] in (401,403),staff_refused=denied['status']>=400,success=first['status']==200,replay=again['status']==200 and again['body'].get('replayed') is True)
        for label,patch,code in free.invalid_rates():
            bad=dict(payload,**patch)
            result=owner.rpc('erp_save_laundry_bd_action_v1',dict(p_action='SAVE_COMPONENT_RATE',p_payload=bad,p_client_request_id=str(uuid.uuid4())))
            checks[label]=result['status']>=400 and code in str(result.get('body',{})) and state()==before
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        try:revoked=owner.rpc('erp_save_laundry_bd_action_v1',args)
        finally:
            with http.connect() as conn,conn.cursor() as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        checks['revoked_replay_refused']=revoked['status']>=400 and 'rate_id' not in revoked.get('body',{})
        checks['versions_unchanged']=state()==before
        return free.b.verdict(checks)
    return [('VENDOR_FREE_HTTP:CURRENT_AUTH_REPLAY_INVALID_ATOMIC',master)]

def http_cases(http,today):return vendor_http_cases(http,today)+regression.http_cases(http,today)
