"""Focused actual Native caller cases. Predecessor133 remains separate proof.

No old raw-WIP/start-of-day oracle is silently changed to pass this suite.
Fixture policy values below are synthetic, never owner/Enteng defaults.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
import json
import uuid
import psycopg
import cp7_b_stock_formula_cases as formula
import cp7_ow10_supply_cases as supply
from cp7_ow04_restore_bundle import _catalog_rows
from cp7_ow10_reorder_probe import MODULES

b, auth, master = formula.b, formula.auth, formula.master
CONTRACT = 'cp7.ow10.reorder-caller-native.v1'
FUNCTIONS, SCHEDULES = supply.FUNCTIONS, supply.SCHEDULES
IDS = dict(native=[
    'OW10R_NATIVE_CATALOG_PRIVATE_22', 'OW10R_NATIVE_PROFILE_MEAN_AND_CLOCKS',
    'OW10R_NATIVE_UNKNOWN_RAW_NOT_ZERO', 'OW10R_NATIVE_MANUAL_REPLAY_CLEAR',
    'OW10R_NATIVE_CURRENT_GLOBAL_GOOD', 'OW10R_NATIVE_STALE_NO_CREDIT',
    'OW10R_NATIVE_CURRENT_ACCESS',
    'OW10R_NATIVE_THRESHOLD_CACHE_FRESH_STOCK', 'OW10R_NATIVE_LARGE_EXACT_WA',
    'OW10R_NATIVE_AFTER_USE_GUARDS', 'OW10R_NATIVE_VOLUME2000_8S_WARM3S'],
    races=['OW10R_RACE_SAME_UUID_ONE_REVISION', 'OW10R_RACE_STALE_REVISION_ONE_WINNER',
           'OW10R_RACE_REVOKED_AFTER_GLOBAL_WAIT', 'OW10R_RACE_BUSY_NEW_LOW'],
    http=['OW10R_HTTP_ACTUAL_AUTH_V2_SAVE_REPLAY', 'OW10R_HTTP_ANON_AND_REVOKED'],
    browser=['OW10R_BROWSER_DESKTOP_NATIVE_V2', 'OW10R_BROWSER_MOBILE_LOST_REPLY'])
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert REQUIRED == dict(native=11, races=4, http=2, browser=2) and EXPECTED == 19
INSTALL_STATES, REORDER_STATES = {}, {}


def configured(cur, today, subject=None, stock=4, daily='2', stock_day=None):
    # A same-day positive stock fixture must be valid even just after WIB
    # midnight. Keep its day/quantity and the Native no-future guard unchanged.
    f = formula.item(cur, today, stock, stock_day=stock_day, stock_hour=0 if stock_day == today else 8)
    subject = subject or master.role_actor(cur, 'OWNER')
    p = supply.retained.profile.payload(cur, f, daily_pcs=daily,
                                       minimum_available_days='14', buffer_days='2')
    supply.retained.profile.save(cur, p, subject=subject)
    return f, subject


def row(cur, f):
    return cur.execute('select row from cp7_reorder_caller.evaluations where root_id=%s',
                       (f['product'],)).fetchone()[0]


def refresh(cur, subject):
    return formula.as_actor(cur, subject, 'select public.erp_cp7_refresh_fg_reorder_v1()')


def workspace(cur, subject, f):
    return formula.workspace(cur, subject, q=f['sku'], filter='ALL', offset=0, limit=25)


def snapshot(cur):
    return supply.private(cur, 'with s as materialized(select cp7_reorder_inputs.source_within(5000)v)'
                          'select cp7_reorder_reader.snapshot(s.v)from s')


def current_job(cur, today):
    _, root, _, _ = supply.analysis.setup(cur, today)
    s = supply.private(cur, 'select cp7_reorder_inputs.source_within(5000)')
    key, _, _, _ = supply.staged.staged_done(cur, today, q=s['query'])
    job = supply.staged.job_row(cur, key)
    formula.compute(cur)
    return dict(product=root), job


def cases(cur, today):
    def catalog():
        b.api.admin(cur)
        before = _catalog_rows(cur)
        for name, module in MODULES:
            module.verify(cur, REORDER_STATES[name])
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            for schema in ('cp7_reorder_inputs', 'cp7_reorder_reader', 'cp7_reorder_caller'):
                assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, schema)).fetchone()[0]
        assert _catalog_rows(cur) == before
        return dict(status='PASS', actual_Native_private_catalog_and_three_preuse22=True)

    def profile_mean():
        f, subject = configured(cur, today)
        before = b.boundary.snapshot(cur)
        refresh(cur, subject)
        e = row(cur, f)
        assert e['point'] == '10' and e['projection']['target_pcs'] == '24' and float(e['daily_mean']) == 2, e
        assert e['lead_basis'] == 'PROFILE' and e['projection']['threshold_source'] == 'PLANNING_PROFILE'
        w = workspace(cur, subject, f)
        assert w['contract_version'] == 'cp7.fg-reorder.v2' and w['page']['rows'][0]['point'] == '10'
        assert e['projection']['threshold_checked_at'] and e['projection']['stock_checked_at']
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', actual_selected_mean2_point10_target24=True, no_ERP_DML=True)

    def unknown():
        f, subject = configured(cur, today)
        refresh(cur, subject)
        e = row(cur, f)
        assert e['wip_status'] == 'UNKNOWN' and e['wip_pcs'] is None and e['projection']['base_position_pcs'] is None, e
        assert e['state'] == 'AT_OR_BELOW' and e['free_pcs'] == '4'
        assert e['projection']['raw_WIP_credited'] is False
        return dict(status='PASS', missing_analysis_not_zero=True, free_stock_alert_continues=True)

    def manual():
        f, subject = configured(cur, today)
        key = str(uuid.uuid4())
        saved = formula.save_manual(cur, subject, f, 25, request=key, expected=0)
        assert saved['contract_version'] == 'cp7.fg-reorder-manual.v2'
        assert saved['evaluation']['point'] == '25' and saved['evaluation']['projection']['target_pcs'] == '24'
        assert formula.save_manual(cur, subject, f, 25, request=key, expected=0)['replay'] is True
        assert formula.refused(cur, lambda: formula.save_manual(cur, subject, f, 26, request=key, expected=0))[1] == 'CP7_FORMULA_REQUEST_REUSED'
        zero = formula.save_manual(cur, subject, f, 0)
        assert zero['evaluation']['state'] == 'NO_POINT' and zero['evaluation']['point'] == '0'
        clear = formula.save_manual(cur, subject, f, None)
        assert clear['evaluation']['point'] == '10' and clear['evaluation']['manual_point'] is None
        return dict(status='PASS', manual25_above_target24_not_added=True, replay_zero_clear=True)

    def good():
        f, job = current_job(cur, today)
        e = row(cur, f)
        assert e['wip_status'] == 'COMPLETE' and e['wip_pcs'] == '7', e
        assert e['projection']['base_position_pcs'] == '7' and e['projection']['production_base_pcs'] == '93', e
        assert e['projection']['target_pcs'] == '100' and job['state'] == 'DONE'
        return dict(status='PASS', actual_full_worker_raw8_good7_once=True, current_target100_gap93=True)

    def stale():
        f, _ = current_job(cur, today)
        assert row(cur, f)['wip_pcs'] == '7'
        formula.found(cur, f, today, 1, hour=0)
        formula.compute(cur)
        e = row(cur, f)
        assert e['free_pcs'] == '1' and e['wip_status'] == 'UNKNOWN' and e['wip_pcs'] is None, e
        return dict(status='PASS', actual_stock_change_invalidates_completed_analysis=True)

    def access():
        f, subject = configured(cur, today)
        viewer = formula.staff_with(cur, 'warehouse.fg.view')
        refresh(cur, subject)
        assert workspace(cur, viewer, f)['can_manage'] is False
        assert formula.refused(cur, lambda: formula.save_manual(cur, viewer, f, 25))[0] == '42501'
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (subject,))
        assert formula.refused(cur, lambda: workspace(cur, subject, f))[0] == '42501'
        return dict(status='PASS', actual_role_and_current_deactivation=True)

    def cache():
        f, _ = configured(cur, today)
        first, second = snapshot(cur), snapshot(cur)
        assert second['cache_hit'] is True and second['threshold_hash'] == first['threshold_hash']
        formula.found(cur, f, today, 1, hour=0)
        latest = snapshot(cur)
        assert latest['cache_hit'] is True and latest['points'] == first['points']
        target = next(x for x in latest['current_stock'] if x['root_id'] == f['product'])
        assert target['native_available_pcs'] == '5'
        assert latest['context_hash'] != first['context_hash']
        return dict(status='PASS', actual_cache_hit_and_fresh_FG=True, threshold_key_not_WIP_freshness=True)

    def large():
        f, subject = configured(cur, today, daily='2000000000000001')
        refresh(cur, subject)
        e = row(cur, f)
        assert e['point'] == '10000000000000005', e
        e['product_name'] = '🧵'*300
        alert = supply.private(cur, 'select cp7_stock_formula.alert_row(%s::jsonb,0.95)', (json.dumps(e),))
        alert['kind'] = 'FG_AT_REORDER_POINT'
        line = cur.execute("select cp7_alert_native.item_line(%s::jsonb,'SUMMARY')", (json.dumps(alert),)).fetchone()[0]
        assert len(line) == 256 and line.endswith('titik 10000000000000005 pcs')
        assert 'perkiraan tepat waktu belum diketahui' in line
        return dict(status='PASS', large_PCS_text_exact=True, unicode_label_only_shortened=True)

    def used():
        f, subject = configured(cur, today)
        refresh(cur, subject)
        before = _catalog_rows(cur)
        for name, module in reversed(MODULES[1:]):
            try:
                module.rollback_preuse(cur, REORDER_STATES[name])
            except ValueError as error:
                assert 'AFTER_USE_REQUIRES_BACKUP_RESTORE' in str(error), str(error)
            else:
                raise AssertionError('OW10R_AFTER_USE_ALLOWED: '+name)
            assert _catalog_rows(cur) == before
        return dict(status='PASS', caller_and_cache_after_use_refused_before_DDL=True)

    def volume():
        # Timing-only synthetic data. Explicit historical establishment does
        # not relabel a newly created real product as historically available.
        b.api.admin(cur)
        cur.execute('set local session_replication_role=replica')
        cur.execute("insert into erp.product_models(id,model_code,model_name,is_active)"
                    "select gen_random_uuid(),'OW10RV-M'||g,'OW10R synthetic model '||g,true from generate_series(1,200)g")
        cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,created_at,is_active,is_portal_visible)
            select x.id,'OW10RV-'||x.n,m.id,b.brand_id,'OW10RV',b.size_id,'OW10R synthetic '||x.n,x.id,
             now()-interval'131 days',now()-interval'131 days',true,true
            from(select gen_random_uuid()id,g n from generate_series(1,2000)g)x
            join(select id,row_number()over(order by model_code)rn from erp.product_models where model_code like 'OW10RV-M%%')m on m.rn=1+(x.n%%200)
            cross join(select*from erp.products where id=%s)b""", (formula.sales.fg.base.BASE_PRODUCT,))
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
            select gen_random_uuid(),p.id,null,%s,'GRADE_A','OPENING',800,10,'OW10R_VOLUME',now()-interval'130 days',now()-interval'130 days'
            from erp.products p where p.sku like 'OW10RV-%%'""", (formula.sales.fg.base.LOCATION,))
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
            select gen_random_uuid(),p.id,null,%s,'GRADE_A','SALE',-(1+(g%%6)),10,'OW10R_VOLUME',now()-((g%%120)||' days')::interval-interval'2 hours',now()-interval'1 hour'
            from erp.products p cross join generate_series(1,100)g where p.sku like 'OW10RV-%%'""", (formula.sales.fg.base.LOCATION,))
        cur.execute('set local session_replication_role=origin')
        cur.execute('analyze erp.fg_stock_movements')
        times = []
        for _ in range(3):
            cur.execute("set local statement_timeout='8s'")
            started = monotonic()
            answer = formula.compute(cur)
            times.append(round((monotonic()-started)*1000))
        n = cur.execute("select count(*)from cp7_reorder_caller.evaluations where row->>'sku'like'OW10RV-%%'"
                        "and row->>'counted_days'='30'and row->>'free_pcs'='450'").fetchone()[0]
        moves = cur.execute("select count(*)from erp.fg_stock_movements where source_type='OW10R_VOLUME'").fetchone()[0]
        assert n == 2000 and moves == 202000 and answer['items'] >= 2000
        assert max(times[1:]) <= 3000, times
        return dict(status='PASS', label='SYNTHETIC_NATIVE_TIMING_ONLY', items=n, movements=moves,
                    millis=times, warm_limit_ms=3000, statement_limit='8s', no_raw_stock_truncation=True)

    return list(zip(IDS['native'], [catalog, profile_mean, unknown, manual, good, stale,
                                   access, cache, large, used, volume]))


def races(tools, today):
    def prepare():
        with tools.connect() as conn, conn.cursor() as cur:
            f, subject = configured(cur, today)
            conn.commit()
        return f, subject

    def save(f, subject, request):
        with tools.connect() as conn, conn.cursor() as cur:
            cur.execute("set local statement_timeout='8s'")
            try:
                value = formula.save_manual(cur, subject, f, 25, request=request, expected=0)
                conn.commit()
                return value
            except psycopg.Error as error:
                conn.rollback()
                return dict(code=error.sqlstate, message=error.diag.message_primary)

    def same():
        f, subject = prepare()
        key = str(uuid.uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: save(f, subject, key), range(2)))
        assert sorted(x['replay'] for x in answers) == [False, True], answers
        with tools.connect() as conn, conn.cursor() as cur:
            assert cur.execute('select count(*)from cp7_stock_formula.manual_points where root_id=%s', (f['product'],)).fetchone()[0] == 1
        return dict(status='PASS', actual_two_sessions_one_UUID_one_revision=True)

    def stale():
        f, subject = prepare()
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: save(f, subject, str(uuid.uuid4())), range(2)))
        assert sum(x.get('replay') is False for x in answers) == 1, answers
        assert sum(x.get('message') == 'CP7_FORMULA_MANUAL_STALE' for x in answers) == 1, answers
        return dict(status='PASS', actual_two_sessions_one_expected_revision_winner=True)

    def revoke():
        f, subject = prepare()
        started, pid = Event(), []

        def waiting():
            with tools.connect() as conn, conn.cursor() as cur:
                cur.execute("set local statement_timeout='8s'")
                pid.append(cur.execute('select pg_backend_pid()').fetchone()[0])
                started.set()
                try:
                    value = formula.save_manual(cur, subject, f, 25, expected=0)
                    conn.commit()
                    return value
                except psycopg.Error as error:
                    conn.rollback()
                    return dict(code=error.sqlstate, message=error.diag.message_primary)

        with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=1) as pool:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))")
            future = pool.submit(waiting)
            assert started.wait(5)
            deadline, observed = monotonic()+5, False
            while monotonic() < deadline:
                value = h.execute('select wait_event_type from pg_stat_activity where pid=%s', (pid[0],)).fetchone()
                if value and value[0] == 'Lock':
                    observed = True
                    break
                sleep(.05)
            assert observed, 'OW10R_NO_ACTUAL_LOCK_WAIT'
            with tools.connect() as conn, conn.cursor() as cur:
                cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (subject,))
                conn.commit()
            holder.rollback()
            answer = future.result(timeout=15)
        assert answer.get('code') == '42501', answer
        with tools.connect() as conn, conn.cursor() as cur:
            assert cur.execute('select count(*)from cp7_stock_formula.manual_points where root_id=%s', (f['product'],)).fetchone()[0] == 0
        return dict(status='PASS', actual_lock_wait_observed=True, revoked_before_write_no_revision=True)

    def busy():
        # Commit the initial refresh first: its transaction holds the global
        # FG lock. A second backend must never wait on that uncommitted fixture.
        with tools.connect() as conn, conn.cursor() as cur:
            f, subject = configured(cur, today, stock=11, stock_day=today)
            refresh(cur, subject)
            assert row(cur, f)['state'] == 'ABOVE'
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            formula.sales.fg.ax.reverse(cur, f['found'], 'OW10R reverse today fixture stock')
            before = row(cur, f)
            conn.commit()
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("set local statement_timeout='8s'")
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))")
            with tools.connect() as conn, conn.cursor() as cur:
                cur.execute("set local statement_timeout='8s'")
                source = formula._fg_source(cur, subject)
                low = next(x for x in source['rows'] if x['subject_key'] == f['target'])
                assert low['detail']['free_pcs'] == '0' and low['detail']['wip_pcs'] is None, low
                assert row(cur, f) == before
        return dict(status='PASS', actual_second_backend_lock_and_ensure_computed=True,
                    newly_low_item_after_actual_today_stock_inverse=True, no_evaluation_write=True)

    return list(zip(IDS['races'], [same, stale, revoke, busy]))


def http_cases(http, today):
    def flow():
        owner = http.login('OWNER', 'ow10r-v2-owner')
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = configured(cur, today, subject=owner.auth_user_id)
            conn.commit()
        assert owner.rpc('erp_cp7_refresh_fg_reorder_v1')['status'] == 200
        read = owner.rpc('erp_cp7_get_fg_reorder_v1', dict(p_query=dict(q=f['sku'], filter='ALL', offset=0, limit=25)))
        assert read['status'] == 200 and read['body']['contract_version'] == 'cp7.fg-reorder.v2', read
        args = dict(p_payload=dict(root_id=f['product'], expected_revision=0, reorder_point_pcs=25, reason='OW10R real Auth fixture'), p_request=str(uuid.uuid4()))
        saved, replay = owner.rpc('erp_cp7_save_fg_reorder_manual_v1', args), owner.rpc('erp_cp7_save_fg_reorder_manual_v1', args)
        assert saved['status'] == replay['status'] == 200 and replay['body']['replay'] is True, (saved, replay)
        assert saved['body']['evaluation']['point'] == '25'
        return dict(status='PASS', actual_Auth_PostgREST_v2_read_write_replay=True)

    def denied():
        admin = http.login('ADMIN', 'ow10r-current-admin')
        args = dict(p_query=dict(q='', filter='ALL', offset=0, limit=25))
        assert admin.rpc('erp_cp7_get_fg_reorder_v1', args)['status'] == 200
        assert http.anon_rpc('erp_cp7_get_fg_reorder_v1', args)['status'] in (401, 403)
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (admin.auth_user_id,))
            conn.commit()
        assert admin.rpc('erp_cp7_get_fg_reorder_v1', args)['status'] == 403
        return dict(status='PASS', real_token_current_access_rechecked=True, anonymous_denied=True)

    return list(zip(IDS['http'], [flow, denied]))
