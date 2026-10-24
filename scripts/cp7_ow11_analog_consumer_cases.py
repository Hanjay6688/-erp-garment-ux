"""Opt-in Native consumer proofs; no frontend, model or full-chain acceptance."""
from datetime import timedelta
from decimal import Decimal
from time import monotonic
import json
import uuid
import cp7_ow11_analog_choice_cases as choice
import cp7_product_analog_consumer_stage as stage
from cp7_ow04_restore_bundle import _catalog_rows

reader,bounded,volume,plan=choice.reader,choice.bounded,choice.volume,choice.plan
CONTRACT='cp7.ow11.analog-consumer-native.v1'
IDS=dict(native=['OW11_ANALOG_CONSUMER_CATALOG22_PREUSE_DEPENDENCY',
 'OW11_ANALOG_CONSUMER_CONFIRM_FRESH_TARGET_CLEAR_REPLAY',
 'OW11_ANALOG_CONSUMER_POSTED_SALE_EXACT_SHARED_KERNEL',
 'OW11_ANALOG_CONSUMER_PROFILE_CHANGE_AND_MANUAL_PRIORITY',
 'OW11_ANALOG_CONSUMER_ATOMIC_FAULT_AND_OTHER_SOURCE',
 'OW11_ANALOG_CONSUMER_DENSE2000_202000_FRESH_TARGET'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=choice.FUNCTIONS
SCHEDULES=choice.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
BASIS='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'


def install(cur):
    choice.PARENT_CHECKER=PARENT_CHECKER
    before,rs,cs=choice.install(cur)
    def predecessor(c):
        choice.stage.verify(c,cs)
        snap=_catalog_rows(c)
        c.execute('savepoint consumer_choice_parent')
        try:
            choice.stage.rollback_preuse(c,cs)
            from cp7_ow11_analog_browser_probe import verify_composed
            verify_composed(c,PARENT_CHECKER,rs)
        finally:
            c.execute('rollback to savepoint consumer_choice_parent')
            c.execute('release savepoint consumer_choice_parent')
        assert _catalog_rows(c)==snap
    state=stage.install_delta(cur,predecessor)
    return before,rs,cs,state


def profile(cur,root,**changes):
    row=volume.baseline.get(cur,[root])['rows'][0]
    config=dict(volume.SYNTHETIC['profile'],mean_mode='OWN_AVAILABLE_HISTORY',daily_pcs=None,
                minimum_available_days='1',lead_days='3',review_days='0',buffer_days='0')
    config.update(changes)
    return volume.baseline.save(cur,dict(root_id=root,product_version_id=row['product_version_id'],
        expected_revision=row['revision'],config=config,reason='Explicit SYNTHETIC consumer test; not factory policy'))


def fresh(cur,today,f,q=None):
    key=str(uuid.uuid4());initial=bounded.request(cur,today,key,f.get('subject'),q=q)
    row=plan.staged.job_row(cur,key,f.get('subject'))
    new=dict(f,key=key,initial=initial,row=row)
    bounded.finish(cur,new)
    return new


def prepare(cur,today,dense=False):
    x=plan.fixture(cur,today);imported=volume.import_batch(cur,today,11,volume.Phases())
    historical=reader.historical.seed(cur,imported);target=imported[0]['target']
    source=next(p['target']for p in historical if p['target'].split(':')[1]==target.split(':')[1])
    profile(cur,imported[0]['root'])
    size=bounded.work.dense.seed(cur)if dense else None
    f=fresh(cur,today,dict(x=x,target=target,source=source,imported=imported,size=size,subject=None))
    return f


def payload(f,revision='0'):
    return dict(contract_version='cp7.product-analog-choice-command.v1',source_request=f['key'],
        source_hash=f['pages']['reference']['source_hash'],access_epoch=f['pages']['access_epoch'],
        target_key=f['target'],source_key=f['source'],scale_factor='1',
        reason='Explicit SYNTHETIC Native consumer comparison',reviewed=True,expected_revision=revision,action='CONFIRM')


def row(f):
    return next(x for x in f['row']['reference']['bounded_history_inputs']['inputs']['targets']if x['target_key']==f['target'])


def staged_row(cur,f):
    plan.b.api.admin(cur)
    result=cur.execute("select payload from cp7_analysis_stage.target_rows where job_id=%s and kind='BASE'and target_key=%s",(f['row']['id'],f['target'])).fetchone()
    assert result is not None,'CONSUMER_STAGED_BASE_ROW_MISSING'
    return result[0]


def cases(cur,today):
    def catalog():
        before,rs,cs,state=install(cur);v=stage.verify(cur,state)
        assert (v['private_functions'],v['existing_replacements'],v['new_public_rpcs'],v['new_tables'])==(7,18,0,0)
        snap=_catalog_rows(cur)
        cur.execute('create view public.ow11_consumer_inverse_guard as select cp7_product_analog_consumer.engine_hash()value')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,state)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('CONSUMER_DEPENDENT_VIEW_DROPPED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_consumer_inverse_guard');assert _catalog_rows(cur)==snap
        stage.rollback_preuse(cur,state);choice.stage.verify(cur,cs)
        choice.stage.rollback_preuse(cur,cs);reader.remove(cur,before,rs)
        return dict(status='PASS',private7_replacements18_public0_tables0=True,
          exact_catalog22_inverse=True,dependent_view_failure_restores_all_partial_DDL=True,
          exact_owner_ACL_GUC_unchanged=True,source_sha256=stage.verify_sources())

    def lifecycle():
        _,_,_,state=install(cur);f=prepare(cur,today);physical=plan.monetary_state(cur)
        assert row(f)['demand_estimate']['status']=='UNKNOWN'
        key=str(uuid.uuid4());p=payload(f);receipt,ms=choice.save(cur,p,key)
        assert receipt['revision']=='1'
        plan.refused(cur,lambda:choice.save(cur,payload(f,'1')),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
        assert choice.save(cur,p,key)[0]==receipt
        new=fresh(cur,today,f);r=row(new);s=staged_row(cur,new)
        assert r['demand_estimate']['basis']==BASIS and r['target']['target_pcs']=='0'
        assert s['demand_estimate']['basis']==BASIS and s['target']['target_pcs']=='0'
        assert r['analog_resolution']['choice_id']==receipt['choice_id']
        assert new['pages']['reference']['source_hash']!=f['pages']['reference']['source_hash']
        clear=dict(p,action='CLEAR',expected_revision='1',source_request=None,source_hash=None,
                   source_key=None,scale_factor=None,reason='Explicit withdrawal of consumer test')
        choice.save(cur,clear);cleared=fresh(cur,today,new)
        assert row(cleared)['analog_resolution']['reason']=='ANALOG_CHOICE_CLEARED'
        assert row(cleared)['demand_estimate']['status']=='UNKNOWN'and row(cleared)['target']['target_pcs']is None
        assert choice.save(cur,p,key)[0]==receipt
        snap=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,state)
        except ValueError as e:assert str(e)=='ANALOG_CONSUMER_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('CONSUMER_USED_INVERSE_ALLOWED')
        assert _catalog_rows(cur)==snap and plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_choice_changes_fresh_bounded_and_staged_target=True,
          old_reference_stales_but_exact_receipt_replays=True,clear_returns_UNKNOWN_not_zero=True,
          no_physical_stock_money_HPP_change=True,after_use_inverse_refused=True,confirm_millis=ms)

    def posted_sale():
        install(cur);f=prepare(cur,today)
        import cp7_sales_cases as sales
        import cp7_procurement_cases as receipt
        day=today-timedelta(days=1);product=f['source'].split(':')[0]
        sales.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=sales.fg.base.LOCATION,
          qty_pcs=10,physical_at=receipt.aa.at(day,8).isoformat(),reason='Consumer actual Native sale fixture',
          owner_unit_value='10',owner_value_reason='Explicit test value'))
        plan.b.api.admin(cur);tag='OW11C-'+uuid.uuid4().hex[:12]
        customer=str(sales.fg.base.create_customer(cur,tag))
        draft=plan.b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=customer,
          source_location_id=sales.fg.base.LOCATION,sale_date=receipt.aa.at(day,10).isoformat(),
          reason='Actual Native demand fixture',items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
        sales.fg.post_sale(cur,draft)
        q=dict(from_date=str(today-timedelta(days=3)),through_date=str(day),group_mode='AS_SOLD')
        f=fresh(cur,today,f,q);choice.save(cur,payload(f));new=fresh(cur,today,f,q)
        physical=plan.monetary_state(cur);r=row(new);s=staged_row(cur,new)
        assert r['analog_resolution']['analog']['available_total_pcs']=='1'
        assert r['analog_resolution']['available_days']=='3'
        assert r['target']['target_pcs']==s['target']['target_pcs']=='1'
        plan.b.api.admin(cur)
        direct=cur.execute('select cp7_baseline_native.build(%s::jsonb,%s::jsonb)',(json.dumps(new['row']['reference']),json.dumps(q))).fetchone()[0]
        d=next(x for x in direct['rows']if x['target_key']==f['target'])
        assert d['target']['target_pcs']=='1'and d['demand_estimate']['basis']==BASIS
        # ROP uses its own closed policy window, recomputed from current Native
        # history. Observed own PCS/days must remain 0, never scaled analog data.
        compiled=cur.execute('select cp7_reorder_inputs.compile(cp7_reorder_inputs.source_within(5000))').fetchone()[0]
        point=next(x for x in compiled['points']['rows']if x['target_key']==f['target'])
        assert point['demand_basis']==BASIS and point['point_pcs']=='1'
        assert point['available_total_pcs']=='0'and point['available_days']=='0'
        assert Decimal(point['daily_mean'])>0
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_public_posted_sale_quantity='1',exact_1_over_3_times_3_target='1',
          direct_staged_bounded_same_target=True,reorder_same_target_kernel=True,
          own_sales_PCS_and_days_unchanged=True,recomputed_current_ROP_window=True,
          synthetic_historical_opening_explicit=True,all_public_factory_history_credit=False)

    def profile_change():
        install(cur);f=prepare(cur,today);choice.save(cur,payload(f))
        profile(cur,f['imported'][0]['root'],minimum_available_days='2')
        new=fresh(cur,today,f)
        assert row(new)['analog_resolution']['reason']=='ANALOG_PROFILE_CHANGED'
        assert row(new)['demand_estimate']['status']=='UNKNOWN'
        profile(cur,f['imported'][0]['root'],mean_mode='SELECTED_MANUAL',daily_pcs='2')
        manual=fresh(cur,today,new);r=row(manual)
        assert r['demand_estimate']['basis']=='SELECTED_MANUAL_ASSUMPTION'and r['target']['target_pcs']=='6'
        assert 'analog_resolution'not in r
        return dict(status='PASS',actual_profile_revision_change_invalidates_choice=True,
          UNKNOWN_not_zero=True,explicit_manual_priority_preserved=True,manual_target_pcs='6')

    def atomic():
        install(cur);f=prepare(cur,today);plan.b.api.admin(cur)
        cur.execute("create function pg_temp.ow11_consumer_fault()returns trigger language plpgsql as $$begin raise exception 'OW11_CONSUMER_LAST_TABLE_FAULT';end;$$")
        cur.execute('create trigger ow11_consumer_fault before insert on cp7_product_analog_choice.commands for each row execute function pg_temp.ow11_consumer_fault()')
        snap=choice.metadata(cur);physical=plan.monetary_state(cur)
        plan.refused(cur,lambda:choice.save(cur,payload(f)),'OW11_CONSUMER_LAST_TABLE_FAULT')
        assert choice.metadata(cur)==snap and plan.monetary_state(cur)==physical
        plan.b.api.admin(cur);cur.execute('drop trigger ow11_consumer_fault on cp7_product_analog_choice.commands')
        plan.found_fg(cur,f['x'],'1')
        plan.refused(cur,lambda:choice.save(cur,payload(f)),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
        assert choice.metadata(cur)==snap
        return dict(status='PASS',own_delta_does_not_skip_atomic_last_table_fault=True,
          actual_other_Native_stock_change_refused=True,no_orphan_choice_or_command=True)

    def dense():
        install(cur);f=prepare(cur,today,dense=True);c=f['row']['reference']
        assert c['status']=='INCOMPLETE'and int(c['bounded_stock_reference']['row_count'])>=202000
        physical=plan.monetary_state(cur);key=str(uuid.uuid4());p=payload(f)
        receipt,ms=choice.save(cur,p,key);new=fresh(cur,today,f)
        assert row(new)['demand_estimate']['basis']==BASIS and staged_row(cur,new)['target']['target_pcs']=='0'
        assert choice.save(cur,p,key)[0]==receipt
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',**f['size'],actual_products=len(c['facts']['products']),
          full_stock_digest_rows=int(c['bounded_stock_reference']['row_count']),
          fresh_DONE_after_choice=True,raw_native_INCOMPLETE_not_promoted=True,confirm_millis=ms,
          slowest_step_millis=max(x['ms']for x in new['calls']),full_source_checks=2,
          exact_old_UUID_replay=True,statement_limit='8s',wall_limit_ms=8000,factory_SLA=False)

    return list(zip(IDS['native'],[catalog,lifecycle,posted_sale,profile_change,atomic,dense]))
