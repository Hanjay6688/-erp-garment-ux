"""Two new Native public-boundary cases; no Auth HTTP or browser claim."""
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import json
import uuid
import cp7_current_frozen_public_installation as product
import cp7_p21_current_chain_rehearsal_probe as chain

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('public_native_unchanged_private_helpers',HERE/'private_cases.py')
private=importlib.util.module_from_spec(spec);spec.loader.exec_module(private)
plan,bounded=private.plan,private.bounded
render=product.public.render
IDS=('CURRENT_FROZEN_PUBLIC_TWO_FACADES_FULL22_DEPENDENCY',
     'CURRENT_FROZEN_PUBLIC_OPERATIONAL_PENDING_COMPLETE_REPLAY')
STATE=CHECKER=None


@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=STATE,CHECKER;STATE,CHECKER=state,checker
    try:yield
    finally:STATE,CHECKER=old


def install(cur):
    assert STATE is not None and callable(CHECKER)
    plan.b.api.admin(cur);return CHECKER(cur)


def request(cur,q,key,actor):
    return plan.staged.limited(cur,render.OPERATIONAL.split('.')[1].split('(')[0],(json.dumps(q),key),actor)


def cases(cur,today):
    def catalog():
        proof=install(cur)
        assert proof['new_public_rpcs']==2 and proof['official_finance_source_reused']
        assert proof['all22_transition_chain_verified']and not proof['substituted_catalog_or_definitions']
        rows=STATE['public']['rows'];assert set(rows)==set(render.definitions())
        for row in rows.values():assert row[2:6]==['cp7_capture',True,'v',['search_path=""','TimeZone=UTC']]
        cur.execute('create view public.current_frozen_public_inverse_guard as select '+render.FINANCE.split('(')[0]+'(null::jsonb,null::uuid)value')
        held,data=product.catalog._catalog_rows(cur),product.catalog._data(cur)
        try:
            with chain.helper.control.product_catalog(cur):product.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)=='CURRENT_FROZEN_PUBLIC_SOURCE_OR_FULL22_CHANGED',str(error)
        else:raise AssertionError('PUBLIC_DEPENDENT_VIEW_INVERSE_ACCEPTED')
        assert product.catalog._catalog_rows(cur)==held and product.catalog._data(cur)==data
        cur.execute('drop view public.current_frozen_public_inverse_guard');CHECKER(cur)
        return dict(status='PASS',two_authenticated_definer_facades_exact=True,
            dependent_view_refused_by_full22_before_inverse=True,all_catalog_and_data_unchanged=True,
            full_preuse_inverse_verified_by_outer_runner=True,actual_Auth_HTTP_credit=False)

    def operational():
        install(cur);plan.fixture(cur,today)
        actor=private.native.policy.master.role_actor(cur,'OWNER')
        physical=plan.monetary_state(cur)
        q,key=plan.staged.query(today),str(uuid.uuid4())
        initial=request(cur,q,key,actor);plan.staged.checked(initial,key,'RUNNING')
        assert 'finance_capture'not in initial
        row=plan.staged.job_row(cur,key,actor)
        assert initial['units_done']==0 and private.coverage(cur,row['id'])=='PENDING'
        reference=row['reference'];assert reference.get('finance_sidecar_mode','DEFERRED')=='DEFERRED'
        workspace=bounded.work.get(cur,key,actor)
        assert workspace['contract_version']=='cp7.planning-schedule-staged-bounded.v2'
        assert workspace['history_input_coverage']=='PENDING'and workspace['source_state']=='UNCHANGED'
        fixture=dict(key=key,initial=initial,row=row,subject=actor);bounded.finish(cur,fixture)
        assert private.coverage(cur,row['id'])=='COMPLETE'
        assert private.prepared_cache(cur,row['id'])['inputs']==private.frozen.original_compile(cur,reference,q,{})
        assert request(cur,q,key,actor)==fixture['done']and'finance_capture'not in fixture['done']
        plan.refused(cur,lambda:request(cur,{**q,'group_mode':'RESTATED'if q['group_mode']=='AS_SOLD'else'AS_SOLD'},key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
        plan.refused(cur,lambda:bounded.request(cur,today,key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
        assert plan.staged.job_row(cur,key,actor)['reference']==reference
        assert plan.monetary_state(cur)==physical
        held,data=product.catalog._catalog_rows(cur),product.catalog._data(cur)
        try:
            with chain.helper.control.product_catalog(cur):product.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)==product.USED_ERROR
        else:raise AssertionError('PUBLIC_USED_INVERSE_ACCEPTED')
        assert product.catalog._catalog_rows(cur)==held and product.catalog._data(cur)==data
        return dict(status='PASS',actual_authenticated_Native_public_request=True,
            pending_then_complete_coverage=True,whole_compiler_inputs_exact=True,
            exact_public_UUID_replay=True,cross_method_and_changed_query_refused=True,
            deferred_has_no_finance_capture=True,reference_immutable=True,
            money_stock_HPP_unchanged=True,global_used_inverse_refused_before_DDL=True,
            step_millis=[call['ms']for call in fixture['calls']],
            page_count=fixture['pages']['page_count'],actual_Auth_HTTP_credit=False)
    return list(zip(IDS,(catalog,operational)))
