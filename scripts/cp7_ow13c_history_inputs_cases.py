"""Three Native controls for bounded inputs, not a completed staged job/SAVE."""
from time import monotonic
import json
import cp7_history_bounded as stage
import cp7_ow13c_schedule_cases as work
from cp7_ow04_restore_bundle import _catalog_rows

CONTRACT = 'cp7.ow13c.bounded-history-inputs-native.v1'
IDS = dict(native=['OW13C_BOUNDED_INPUTS_CATALOG_PARITY',
                   'OW13C_BOUNDED_INPUTS_DENSE2000_202000_UNDER8S',
                   'OW13C_BOUNDED_INPUTS_REAL_PRODUCT_OVERFLOW_REFUSED'])
REQUIRED = dict(native=3)
EXPECTED = DECLARED = 3
FUNCTIONS, SCHEDULES = work.FUNCTIONS, work.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE = {}, {}, {}, {}, {}


def call(cur, q, limit):
    work.plan.b.api.admin(cur)
    cur.execute('set local role cp7_capture')
    result = cur.execute('select cp7_history_bounded.capture(%s::jsonb,%s)', (json.dumps(q), limit)).fetchone()[0]
    # A refused SQL statement remains aborted until the caller's savepoint
    # rollback. Do not replace its original code with a reset-role error.
    work.plan.b.api.admin(cur)
    return result


def cases(cur, today):
    def parity():
        v = stage.verify(cur, BOUNDED_STATE)
        assert v['private_functions'] == 2 and v['new_tables'] == v['public_rpcs'] == v['old_replacements'] == 0
        assert len(_catalog_rows(cur)) == 22
        work.plan.fixture(cur, today)
        before = work.metadata(cur)
        q = work.plan.staged.query(today)
        cur.execute('set local role cp7_capture')
        c = cur.execute('select cp7_reorder_inputs.capture_baseline(5000)').fetchone()[0]
        assert c['status'] == 'COMPLETE'
        actual, original = cur.execute('select cp7_history_bounded.compile(%s::jsonb,%s::jsonb,null,5000),'
                                       'cp7_reorder_inputs.history(%s::jsonb,%s::jsonb)',
                                       (json.dumps(c), json.dumps(q), json.dumps(c), json.dumps(q))).fetchone()
        work.plan.b.api.admin(cur)
        assert actual['inputs'] == original and actual['raw_native_capture_status'] == 'COMPLETE'
        assert actual['input_path'] == 'COMPLETE_NATIVE_CAPTURE' and actual['coverage'] == 'COMPLETE'
        assert work.metadata(cur) == before
        return dict(status='PASS', two_private_no_public_no_table_no_old_replacement=True,
                    exact_Native_complete_input_parity=True, all_ERP_platform_auth_metadata_rows_unchanged=True)

    def dense():
        work.plan.fixture(cur, today)
        size = work.dense.seed(cur)
        before, q = work.metadata(cur), work.plan.staged.query(today)
        times, captured = [], None
        for _ in range(3):
            cur.execute("set local statement_timeout='8s'")
            start = monotonic()
            result = call(cur, q, 5000)
            elapsed = (monotonic()-start)*1000
            assert elapsed < 8000, ('BOUNDED_INPUTS_OVER8S', elapsed)
            times.append(round(elapsed, 3))
            assert result['coverage'] == 'COMPLETE' and result['raw_native_capture_status'] == 'INCOMPLETE'
            assert result['input_path'] == 'COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE'
            assert result['raw_native_status_overridden'] is False and result['stock_raw_omitted'] is True
            assert result['raw_stock_rows_read'] >= 202000
            inputs = result['inputs']
            captured = len(inputs['products'])
            assert captured == len(inputs['history']) == len(inputs['current_stock']) == len(inputs['targets'])
            synthetic = {x['root_id']+':'+x['size_id'] for x in inputs['products'] if x['sku'].startswith('OW13CSV-')}
            assert len(synthetic) == 2000
            assert synthetic <= {x['target_key'] for x in inputs['current_stock']}
            assert not inputs['apply_enabled'] and not result['production_go']
        assert work.metadata(cur) == before
        return dict(status='PASS', **size, captured_products=captured, actual_private_full_capture=True,
                    raw_capture_remains_INCOMPLETE=True, no_stock_discarded=True,
                    exact_Native_events_history_stock_target_kernels=True, millis=times,
                    statement_limit='8s', wall_limit_ms=8000, all_ERP_platform_auth_metadata_rows_unchanged=True,
                    actual_checked_SAVE2000_qualified=False, staged_job_done=False)

    def overflow():
        work.plan.fixture(cur, today)
        work.dense.seed(cur)
        before = work.metadata(cur)
        work.plan.refused(cur, lambda: call(cur, work.plan.staged.query(today), 1000),
                          'CP7_BOUNDED_HISTORY_SOURCE_SHAPE')
        assert work.metadata(cur) == before
        return dict(status='PASS', real_more_than1000_current_products_refused=True,
                    no_other_Native_bound_relaxed=True, no_input_or_job_or_quantity_fabricated=True,
                    all_ERP_platform_auth_metadata_rows_unchanged=True)

    return list(zip(IDS['native'], [parity, dense, overflow]))
