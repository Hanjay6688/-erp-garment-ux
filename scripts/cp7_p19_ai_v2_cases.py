"""P19 AI v2: the "Tanya AI" brief of a staged analysis snapshot (snapshot contract v2 §6).

Owner decision 8 Oct 2026: AI may use the snapshot as analysis, labelled with its
time and freshness and never called current; actual finance comes from the
authoritative reader (the client reads the owner finance report at question
time; the brief itself carries none). The brief is bounded (25 targets with the
largest open need, at most 20 selected targets) and read from the retained
per-target index in one ordinary request. Real Native E01 facts and staged
runs, a real concurrent session and real Auth/PostgREST calls on the closed
harness; nothing is written and no AI is called by the server.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import json
import threading
import uuid

import cp7_p19_staged_cases as staged
import cp7_p19_report_v2_cases as report

IDS = dict(
    native=['P19A_BRIEF_EQUALS_INDEX', 'P19A_FIELDS_AND_BOUNDS', 'P19A_STALE_SNAPSHOT_LABELLED', 'P19A_ACCESS_AND_NO_FINANCE'],
    races=['P19A_RACE_BRIEF_WHILE_STOCK_COMMITS'],
    http=['P19A_HTTP_FLOW', 'P19A_HTTP_REVOKED'],
    browser=['P19A_BROWSER_DESKTOP_AI', 'P19A_BROWSER_MOBILE_AI'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.ai-v2.v1'
FUNCTIONS = ('erp_cp7_get_staged_ai_brief_v1',)
SIGNATURE = 'public.erp_cp7_get_staged_ai_brief_v1(uuid,jsonb)'
auth, b, load, bridge = report.auth, report.b, report.load, report.bridge


def brief(cur, run, keys=(), subject=None):
    return report.limited(cur, 'erp_cp7_get_staged_ai_brief_v1', (run, json.dumps(list(keys))), subject)


def index_rows(cur, r):
    """The run's per-target index with each target's page, read directly (admin)."""
    b.api.admin(cur)
    cuts = cur.execute('select cuts from cp7_analysis_stage.headers where run_id=%s', (r['run'],)).fetchone()[0]
    rows = cur.execute('select ord,target_key,row from cp7_analysis_stage.plan_targets where job_id=%s order by ord', (r['job'],)).fetchall()
    page = lambda o: next(i for i, (lo, hi) in enumerate(cuts) if lo <= o <= hi)
    return [(o, k, row, page(o)) for o, k, row in rows]


def expected_row(o, k, row, p):
    """ai_row written independently: the index values as they are, the page holding the target."""
    prod = (row.get('products') or [{}])[0]
    sku = ((prod.get('commercial') or [{}])[0] or {}).get('sku') if prod.get('commercial') else None
    ids = sorted({a['id'] for a in (row.get('assumptions') or []) + (row.get('fabric_assumptions') or []) if isinstance(a, dict) and a.get('id')})
    return dict(ord=o, page_index=p, target_key=k, sku=sku if sku is not None else prod.get('sku'), product_name=prod.get('product_name'),
                production_state=((row.get('production_policy') or {}).get('policy') or {}).get('state'), available_fg_pcs=row.get('available_fg_pcs'),
                target_pcs=(row.get('target') or {}).get('target_pcs'), raw_gap_pcs=row.get('raw_gap_pcs'), base_gap_pcs=row.get('base_gap_pcs'),
                conditional_gap_pcs=row.get('conditional_gap_pcs'), directed_on_time_good_pcs=row.get('directed_on_time_good_pcs'),
                candidate_allocated_good_pcs=row.get('candidate_allocated_good_pcs'), assumption_ids=ids)


def gap(row):
    v = row.get('conditional_gap_pcs')
    try:
        return D(v) if v is not None else None
    except Exception:
        return None


def normal(rows):
    return [dict(x, assumption_ids=sorted(x['assumption_ids'])) for x in rows]


def checked(x, r):
    assert x['contract_version'] == 'cp7.native-ai-brief-staged.v1' and x['run_id'] == r['run'] and x['identity_hash'] == r['identity'], x.get('contract_version')
    assert x['finance'] == 'NOT_IN_SNAPSHOT' and x['apply_enabled'] is False and x['production_go'] is False and x['bounds'] == dict(priority=25, selected=20)
    assert x['targets_total'] == r['ps']['targets_total'] and x['totals'] == r['ps']['totals'] and x['query'] == r['query']
    return x


def cases(cur, today):
    def equals_index():
        f, _ = load.real_workload(cur, today)
        r = report.staged_run(cur, today)
        before = b.boundary.snapshot(cur)
        idx = index_rows(cur, r)
        keys = [k for _, k, _, _ in idx][:2]
        x = checked(brief(cur, r['run'], keys), r)
        open_need = sorted([t for t in idx if (gap(t[2]) or 0) > 0], key=lambda t: (-gap(t[2]), t[0]))[:25]
        assert normal(x['priority']) == normal([expected_row(*t) for t in open_need]), ('P19A_PRIORITY', x['priority'][:2])
        assert normal(x['selected']) == normal([expected_row(*t) for t in idx if t[1] in keys]), 'P19A_SELECTED'
        assert x['need_counts'] == dict(targets=len(idx), with_open_need=sum(1 for t in idx if (gap(t[2]) or 0) > 0),
                                        need_unknown=sum(1 for t in idx if gap(t[2]) is None)), x['need_counts']
        fresh = report.limited(cur, 'erp_cp7_staged_snapshot_freshness_v1', (r['run'],))
        assert {k: v for k, v in x['freshness'].items() if k != 'evaluated_at'} == {k: v for k, v in fresh.items() if k != 'evaluated_at'}, 'P19A_FRESHNESS'
        assert b.boundary.snapshot(cur) == before, 'P19A_BRIEF_WROTE'
        b.api.admin(cur)
        assert cur.execute('select count(*)from cp7_analysis_stage.report_jobs').fetchone()[0] == 0
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', priority_equals_independent_order=len(x['priority']), selected=len(x['selected']), freshness_same_as_its_RPC=True,
                    writes_nothing=True, need_counts=x['need_counts'])

    def fields_bounds():
        f, _ = load.real_workload(cur, today)
        r = report.staged_run(cur, today)
        keys = [k for _, k, _, _ in index_rows(cur, r)]
        for bad in (['x'], [keys[0], keys[0]], [1], {'a': 1}, [keys[0]] * 21):
            report.refused(cur, lambda: report.limited(cur, 'erp_cp7_get_staged_ai_brief_v1', (r['run'], json.dumps(bad))), 'CP7_AI_V2_TARGETS')
        unknown = str(uuid.uuid4()) + ':' + str(uuid.uuid4())
        report.refused(cur, lambda: brief(cur, r['run'], [unknown]), 'CP7_AI_V2_TARGET')
        report.refused(cur, lambda: brief(cur, str(uuid.uuid4())), 'CP7_AI_V2_SNAPSHOT_UNAVAILABLE', '42501')
        running = uuid.uuid4()
        staged.checked(staged.request(cur, today, running), running, 'RUNNING')
        report.refused(cur, lambda: brief(cur, staged.job_row(cur, running)['run_id']), 'CP7_AI_V2_SNAPSHOT_UNAVAILABLE', '42501')
        # A run older than the per-target index is refused with its own code.
        b.api.admin(cur)
        cur.execute('alter table cp7_analysis_stage.plan_scope disable trigger immutable_stage_plan_scope')
        cur.execute('delete from cp7_analysis_stage.plan_scope where job_id=%s', (r['job'],))
        cur.execute('alter table cp7_analysis_stage.plan_scope enable trigger immutable_stage_plan_scope')
        report.refused(cur, lambda: brief(cur, r['run']), 'CP7_AI_V2_SNAPSHOT_INDEX_MISSING')
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', targets_list_closed=True, at_most_twenty_distinct=True, unknown_target_refused=True,
                    unknown_or_unfinished_run_refused=True, run_without_index_refused=True)

    def stale_labelled():
        f, _ = load.real_workload(cur, today)
        r = report.staged_run(cur, today)
        first = checked(brief(cur, r['run']), r)
        staged.location(cur, 'changed after the AI snapshot')
        check = staged.recorded_check(cur, r['run'], 'RECORDING_TIME')
        assert check['source_state'] == 'ARCHIVED_STALE', check
        later = checked(brief(cur, r['run']), r)
        assert later['freshness']['freshness_state'] == 'STALE_VERIFIED' and later['freshness']['data_as_of'] == first['freshness']['data_as_of'], later['freshness']
        assert {k: v for k, v in later.items() if k != 'freshness'} == {k: v for k, v in first.items() if k != 'freshness'}, 'P19A_SNAPSHOT_VALUES_CHANGED'
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', served_after_change=True, freshness_stale_verified=True, snapshot_values_unchanged=True)

    def access_no_finance():
        f, _ = load.real_workload(cur, today)
        r = report.staged_run(cur, today)
        other, role = auth.custom_actor(cur)
        report.refused(cur, lambda: brief(cur, r['run'], subject=other), 'CP7_AI_V2_SNAPSHOT_UNAVAILABLE', '42501')
        mine = report.staged_run(cur, today, other)
        x = checked(brief(cur, mine['run'], subject=other), mine)
        text = json.dumps(x)
        assert not any(w in text for w in ('IDR', 'unit_hpp', 'hpp_per_pcs', 'cogs', 'journal')), 'P19A_FINANCE_IN_BRIEF'
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (role,))
        report.refused(cur, lambda: brief(cur, mine['run'], subject=other), 'CP7_ACCESS_DENIED', '42501')
        for who in ('anon', 'authenticated', 'service_role'):
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, SIGNATURE)).fetchone()[0] == (who == 'authenticated'), who
            assert not cur.execute("select has_function_privilege(%s,'cp7_analysis_stage.ai_brief(uuid,jsonb)','EXECUTE')", (who,)).fetchone()[0], who
        bridge.literal(cur, f, '175.00')
        return dict(status='PASS', foreign_run_refused=True, own_run_served=True, no_finance_or_HPP_in_brief=True, permission_loss_refused=True,
                    only_the_public_wrapper=True)

    return list(zip(IDS['native'], (equals_index, fields_bounds, stale_labelled, access_no_finance)))


def races(tools, today):
    def while_stock():
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            r = report.staged_run(cur, today)
            first = checked(brief(cur, r['run']), r)
            conn.commit()
        gate = threading.Barrier(2)

        def writer():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                report.found_fg(cur, report.first_root(r), 2)
                conn.commit()
                return True

        def reader():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                x = brief(cur, r['run'])
                conn.commit()
                return x
        with ThreadPoolExecutor(max_workers=2) as pool:
            w, x = pool.submit(writer), pool.submit(reader)
            w.result(60)
            during = checked(x.result(60), r)
        with tools.connect() as conn, conn.cursor() as cur:
            after = checked(brief(cur, r['run']), r)
            conn.commit()
            bridge.literal(cur, f, '175.00')
        same = lambda y: {k: v for k, v in y.items() if k != 'freshness'}
        assert same(during) == same(first) == same(after), 'P19A_SNAPSHOT_VALUES_MOVED_WITH_LIVE_STOCK'
        fg_rows = lambda y: next(c['rows'] for c in y['freshness']['changes_since'] if c['category'] == 'FG_STOCK')
        assert fg_rows(after) >= fg_rows(first) + 1 and fg_rows(during) in (fg_rows(first), fg_rows(after)), (fg_rows(first), fg_rows(during), fg_rows(after))
        return dict(status='PASS', snapshot_values_fixed_under_concurrent_stock=True, freshness_counts_the_commit=True,
                    fg_changes=[fg_rows(first), fg_rows(during), fg_rows(after)])

    return list(zip(IDS['races'], (while_stock,)))


def http_cases(http, today):
    state = {}

    def flow():
        owner = http.login('OWNER', 'p19a-owner')
        other = http.login('OWNER', 'p19a-other')
        with http.connect() as conn, conn.cursor() as cur:
            f, _ = load.real_workload(cur, today)
            r = report.staged_run(cur, today, owner.auth_user_id)
            keys = [k for _, k, _, _ in index_rows(cur, r)][:1]
            conn.commit()
        args = dict(p_run=r['run'], p_targets=keys)
        x = owner.rpc('erp_cp7_get_staged_ai_brief_v1', args)
        assert x['status'] == 200, x
        checked(x['body'], r)
        assert [y['target_key'] for y in x['body']['selected']] == keys
        foreign = other.rpc('erp_cp7_get_staged_ai_brief_v1', args)
        assert foreign['status'] == 403 and 'CP7_AI_V2_SNAPSHOT_UNAVAILABLE' in json.dumps(foreign['body']), foreign
        anonymous = http.anon_rpc('erp_cp7_get_staged_ai_brief_v1', args)['status']
        assert anonymous in (401, 403), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            bridge.literal(cur, f, '175.00')
        state.update(owner=owner, args=args)
        return dict(status='PASS', real_Auth_brief=True, foreign_403=True, anonymous_refused=anonymous)

    def revoked():
        assert state, 'P19A_REQUIRED_PRIOR_HTTP_CASE'
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (state['owner'].auth_user_id,))
            conn.commit()
        code = state['owner'].rpc('erp_cp7_get_staged_ai_brief_v1', state['args'])['status']
        assert code == 403, code
        return dict(status='PASS', deactivated_user_403=True)

    return list(zip(IDS['http'], (flow, revoked)))
