"""SKU-01 qualification plus existing BE/BF/BD regressions; disposable copies only."""
import copy,uuid
from datetime import timedelta
import cp6_bf_free_probe as free
import cp6_bf_range_followup as range_followup
import cp6_be_revision_modes as regression
from cp6_bd_modes import _fixture_usage,_verdict

INSTALL_BF=True
bf=free.bf

def cases(cur,today):
    return [('RANGE:REPEATED_DRAWINGS_ONE_CHOICE_PER_SIZE',lambda:range_followup.repeated_drawings(cur,today)),
        ('SKU01:ALL_FOUR_MASTER_STATUSES_AND_REPLAY',lambda:free.master_statuses(cur,today)),
        ('SKU01:INVALID_RATES_ATOMIC_REFUSAL',lambda:free.atomic_rejections(cur,today)),
        ('SKU01:FREE_WAIVED_SHIP_RECEIVE_QC_HPP',lambda:free.free_production(cur,today))]+regression.cases(cur,today)

def race_free(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        # RaceTools supplies its own disposable-only schema grant; HTTP/browser copies do not.
        f=free.master_fixture(cur);g=f['g'];bf.save(cur,[g],f['at']);at=f['now']-timedelta(minutes=2)
        a=bf.group(cur,[p for p,_ in f['rows']],at,sku=g['sku'],gid=g['id'],revision=1,settings=copy.deepcopy(g['settings']))
        z=copy.deepcopy(a);z['settings']['laundry_rates'][0].update(rate_status='WAIVED',reason='Second owner documented waiver')
        conn.commit()
    held,contention,outcome=tools.two_sessions(lambda cur:bf.save(cur,[a],at),lambda cur:bf.save(cur,[z],at),commit)
    with tools.connect() as conn,conn.cursor() as cur:
        revision,rates=cur.execute("select s.revision,v.settings->'laundry_rates' from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id and v.revision=s.revision where s.id=%s",(g['id'],)).fetchone();conn.rollback()
    return _verdict('SKU_FREE_TWO_EDITORS',commit,held,contention,outcome,'STALE_VERSION',dict(revision=revision,rates=rates),
        revision==2 and rates==(a if commit else z)['settings']['laundry_rates'])

def races(tools,today):
    return [('SKU01_RACE:FREE_FIRST_COMMITS',lambda:race_free(tools,today,True)),
        ('SKU01_RACE:FREE_FIRST_ABORTS',lambda:race_free(tools,today,False))]+regression.races(tools,today)

def http_cases(http,today):
    def master():
        with http.connect() as conn,conn.cursor() as cur:
            with _fixture_usage(cur):f=free.master_fixture(cur,True)
            conn.commit()
        owner=http.login('OWNER','sku-free-owner');warehouse=http.login('GUDANG','sku-free-warehouse')
        args=dict(p_action='SAVE_GROUPS',p_payload=dict(groups=[f['g']],effective_from=f['at'].isoformat(),reason='Real Auth SKU zero rates'),p_client_request_id=str(uuid.uuid4()))
        anon=http.anon_rpc('erp_save_sku_action_v1',args);denied=warehouse.rpc('erp_save_sku_action_v1',args)
        first=owner.rpc('erp_save_sku_action_v1',args);assert first['status']==200,first
        again=owner.rpc('erp_save_sku_action_v1',args)
        with http.connect() as conn,conn.cursor() as cur:
            at=f['now']-timedelta(minutes=2);g=f['g']
            update=bf.group(cur,[p for p,_ in f['rows']],at,sku=g['sku'],gid=g['id'],revision=1,settings=copy.deepcopy(g['settings']));conn.rollback()
        checks=dict(anon=anon['status'] in (401,403),role_refused=denied['status']>=400,
                    success=first['status']==200,replay=again['status']==200 and again['body'].get('replayed') is True)
        evidence=[]
        for label,patch,code in free.invalid_rates():
            bad=copy.deepcopy(update);bad['settings']['laundry_rates'][0].update(patch)
            result=owner.rpc('erp_save_sku_action_v1',dict(p_action='SAVE_GROUPS',p_payload=dict(groups=[bad],effective_from=at.isoformat(),reason='Real Auth invalid rate must refuse'),p_client_request_id=str(uuid.uuid4())))
            checks[label]=result['status']>=400 and code in str(result.get('body',{}));evidence.append(dict(case=label,result=result))
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        try:revoked=owner.rpc('erp_save_sku_action_v1',args)
        finally:
            with http.connect() as conn,conn.cursor() as cur:
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        checks['revoked_replay']=revoked['status']>=400 and 'groups' not in revoked.get('body',{})
        with http.connect() as conn,conn.cursor() as cur:
            revision,settings=cur.execute('select s.revision,v.settings from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id and v.revision=s.revision where s.id=%s',(g['id'],)).fetchone()
            count=free.one(cur,'select count(*) from erp.bf_sku_versions_v1 where sku_id=%s',g['id']);conn.rollback()
        checks['persisted_once_and_atomic']=revision==1 and count==1 and settings==g['settings']
        return free.b.verdict(checks,invalid=evidence,revoked=revoked,rates=settings['laundry_rates'])
    return [('SKU01_HTTP:REAL_AUTH_FREE_WAIVED_AND_REJECTIONS',master)]+regression.http_cases(http,today)
