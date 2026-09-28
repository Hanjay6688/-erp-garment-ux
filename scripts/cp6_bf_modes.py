"""Writer BF incremental qualification. Only listed cases are evidence; CP6 remains HOLD."""
import cp6_bf_probe as bf
import cp6_bb_probe as bb
import cp6_bd_revision_modes as bd_revision
INSTALL_BF=True

def cases(cur,today):
    return [('BF:IMPORT_AMBIGUOUS_FAILS_BEFORE_POST',lambda:bf.import_ambiguity(cur,today)),
        ('BF:IMPORT_EXACT_SIZE_SALES_CUSTODY_COGS_REPLAY',lambda:bf.import_exact(cur,today)),
        ('BF:IMPORT_INSUFFICIENT_STOCK_ATOMIC',lambda:bf.import_insufficient(cur,today)),
        ('BF:IMPORT_REWORK_SOURCE_RECIPE',lambda:bf.import_rework_source(cur,today)),
        ('BF:UNUSED_ROLLBACK_EXACT',lambda:bf.recovery_unused(cur,today)),
        ('BF:USED_ROLLBACK_REFUSED',lambda:bf.recovery_used(cur,today)),
        ('BF:TWO_SKUS_ONE_WAVE_WORK_LAUNDRY_QC',lambda:bf.production_ranges(cur,today)),
        ('BF:SHARED_MASTER_PHYSICAL_ROOTS_REPLAY_GUARD',lambda:bf.foundation(cur,today)),
        ('BF:SINGLETON_BEFORE_ECONOMICS',lambda:bf.optional_economics(cur,today)),
        ('BF:TEMPORAL_31_33_TO_31_34_ATOMIC',lambda:bf.temporal_move(cur,today)),
        ('BF:LEGACY_CONFLICT_ACKNOWLEDGED_AND_FUTURE_PRICES',lambda:bf.conflicts(cur,today))]+[("BF_REG_BD:"+k,lambda f=f:f(cur,bf.b.case_day(today))) for k,_,f in bf.b.PLAN if k.startswith(('T02:','T03:','T04:','T05:','T06:','T07:','T12:','T13:','T20:','DEC01:','T24:','D10:','REV:'))]+[("BF_REG_BB:"+k,lambda f=f:f(cur,today)) for k,_,f in bb.PLAN if 'W02' in k]


def race_master(tools,today,commit):
    from datetime import timedelta
    import copy
    with tools.connect() as conn,conn.cursor() as cur:
      rows=bf.products(cur);roots=[r[0] for r in rows];now=bf.one(cur,'select clock_timestamp()')
      g=bf.group(cur,roots,now-timedelta(minutes=4));bf.save(cur,[g],now-timedelta(minutes=4))
      a=bf.group(cur,roots,now-timedelta(minutes=1),sku=g['sku'],gid=g['id'],revision=1);a['settings']['price']='190000'
      z=copy.deepcopy(a);z['settings']['price']='200000';conn.commit()
    held,contention,outcome=tools.two_sessions(lambda cur:bf.save(cur,[a],now-timedelta(minutes=1)),lambda cur:bf.save(cur,[z],now-timedelta(minutes=1)),commit)
    with tools.connect() as conn,conn.cursor() as cur:
      revision=bf.one(cur,'select revision from erp.bf_skus_v1 where id=%s',g['id'])
      prices=[bf.one(cur,'select erp.resolve_product_price_at(%s,%s)',r,now) for r in roots];conn.rollback()
    return bd_revision.bd._verdict('BF_SHARED_SKU_TWO_EDITORS',commit,held,contention,outcome,'STALE_VERSION',dict(revision=revision,prices=list(map(str,prices))),revision==2 and prices==([190000]*3 if commit else [200000]*3))


def races(tools,today):
    return [('BF_RACE:SHARED_SKU_FIRST_COMMITS',lambda:race_master(tools,today,True)),('BF_RACE:SHARED_SKU_FIRST_ABORTS',lambda:race_master(tools,today,False))]+bd_revision.races(tools,today)


def http_cases(http,today):
    import uuid,json
    from datetime import timedelta
    def authorization():
      with http.connect() as conn,conn.cursor() as cur:
        rows=bf.products(cur);roots=[r[0] for r in rows];at=bf.one(cur,"select clock_timestamp()-interval '1 minute'")
        g=bf.group(cur,roots,at);conn.commit()
      actor=http.login('ADMIN','bf-authorized-admin')
      args=dict(p_action='SAVE_GROUPS',p_payload=dict(groups=[g],effective_from=at.isoformat(),reason='BF Auth and replay probe'),p_client_request_id=str(uuid.uuid4()))
      first=actor.rpc('erp_save_sku_action_v1',args);again=actor.rpc('erp_save_sku_action_v1',args)
      assert first['status']==200,first
      with http.connect() as conn,conn.cursor() as cur:
        role=bf.one(cur,'select role_id from erp.app_users where auth_user_id=%s',actor.auth_user_id)
        grants=bf.b.q(cur,"select role_id,permission_key,granted_by,granted_at from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.manage','finance.hpp.view')",role)
        assert grants
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.manage','finance.hpp.view')",(role,));conn.commit()
      try:
        cached=actor.rpc('erp_save_sku_action_v1',args)
        hidden=actor.rpc('erp_get_sku_workspace_v1',dict(p_filters=dict(query=g['sku'])))
        hpp=actor.rpc('erp_get_sku_hpp_v1',dict(p_filters={}))
      finally:
        with http.connect() as conn,conn.cursor() as cur:
          cur.executemany('insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at) values(%s,%s,%s,%s)',grants);conn.commit()
      restored=actor.rpc('erp_save_sku_action_v1',args)
      return bf.b.verdict(dict(first=first['status']==200,replay=again['status']==200 and again['body'].get('replayed') is True,
        revoked_replay=cached['status']>=400 and 'groups' not in cached.get('body',{}),hpp_denied=hpp['status']>=400,
        hidden=hidden['status']==200 and hidden['body']['lookups'] is None and all(g['settings'] is None for g in hidden['body']['groups']),
        restored=restored['status']==200 and restored['body'].get('replayed') is True))
    return [('BF_HTTP:PERMISSION_BEFORE_REPLAY_AND_REPORTS',authorization)]+bd_revision.http_cases(http,today)
