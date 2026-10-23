"""Four Native controls for full raw-stock digests, not staged freshness yet."""
from datetime import timedelta
from time import monotonic
import json
import cp7_history_reference as stage
import cp7_ow13c_schedule_cases as work
from cp7_ow04_restore_bundle import _catalog_rows

CONTRACT = 'cp7.ow13c.raw-stock-reference-native.v1'
IDS = dict(native=['OW13C_REFERENCE_PRIVATE_CATALOG22', 'OW13C_REFERENCE_NATIVE_RAW_PARITY',
                   'OW13C_REFERENCE_DENSE2000_202000_UNDER8S', 'OW13C_REFERENCE_LATE_RECORDED_PHYSICAL_BACKDATE'])
REQUIRED = dict(native=4)
EXPECTED = DECLARED = 4
FUNCTIONS, SCHEDULES = work.FUNCTIONS, work.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE = {}, {}, {}, {}, {}, {}


def digest(cur, products, at):
    work.plan.b.api.admin(cur)
    cur.execute('set local role cp7_capture')
    result = cur.execute('select cp7_history_reference.stock_digest(%s::jsonb,%s)', (json.dumps(products), at)).fetchone()[0]
    work.plan.b.api.admin(cur)
    return result


def capture(cur):
    work.plan.b.api.admin(cur)
    cur.execute('set local role cp7_capture')
    result = cur.execute('select cp7_reorder_inputs.capture_baseline(5000)').fetchone()[0]
    work.plan.b.api.admin(cur)
    return result


def cases(cur, today):
    def catalog():
        v = stage.verify(cur, REFERENCE_STATE)
        assert v['private_functions'] == 1 and v['new_tables'] == v['public_rpcs'] == v['old_replacements'] == 0
        assert len(_catalog_rows(cur)) == 22
        return dict(status='PASS', one_private_no_public_no_table_no_old_replacement=True,
                    Native_typed_projection_and_both_visibility_clocks_pinned=True)

    def parity():
        work.plan.fixture(cur, today)
        c = capture(cur)
        assert c['status'] == 'COMPLETE'
        before = work.metadata(cur)
        actual = digest(cur, c['facts']['products'], c['captured_at'])
        # Independent source: the actual Native immutable raw facts, not a
        # second copy of the reader's joins/roots/clock filters.
        expected = cur.execute("with framed as(select count(*)n,coalesce(string_agg("
            "encode(extensions.digest(convert_to(x::text,'UTF8'),'sha256'),'hex'),chr(10)order by(x->>'id')::uuid),'')frames "
            "from jsonb_array_elements(%s::jsonb)x)select n::text,encode(extensions.digest(convert_to("
            "'cp7.native-stock-row-digest.v1'||chr(10)||n::text||chr(10)||frames,'UTF8'),'sha256'),'hex')from framed",
            (json.dumps(c['facts']['stock']),)).fetchone()
        assert (actual['row_count'], actual['rows_sha256']) == expected, (actual, expected)
        assert actual['raw_rows_truncated'] is False and actual['raw_native_capture_status_overridden'] is False
        assert work.metadata(cur) == before
        return dict(status='PASS', exact_actual_Native_raw_facts_digest_parity=True,
                    every_native_stock_field_preserved=True, all_ERP_platform_auth_metadata_rows_unchanged=True)

    def dense():
        work.plan.fixture(cur, today)
        size = work.dense.seed(cur)
        c = capture(cur)
        assert c['status'] == 'INCOMPLETE' and c['stock_raw_omitted'] is True
        before, times, previous = work.metadata(cur), [], None
        for _ in range(3):
            cur.execute("set local statement_timeout='8s'")
            start = monotonic()
            value = digest(cur, c['facts']['products'], c['captured_at'])
            elapsed = (monotonic()-start)*1000
            assert elapsed < 8000, ('RAW_STOCK_DIGEST_OVER8S', elapsed)
            assert int(value['row_count']) >= 202000 and value['raw_rows_truncated'] is False
            if previous is not None:
                assert value == previous
            previous = value
            times.append(round(elapsed, 3))
        assert work.metadata(cur) == before
        return dict(status='PASS', **size, actual_rows=int(previous['row_count']),
                    all_raw_stock_rows_hashed_without_prefix=True, millis=times, statement_limit='8s',wall_limit_ms=8000,
                    raw_capture_remains_INCOMPLETE=True, all_ERP_platform_auth_metadata_rows_unchanged=True,
                    staged_source_freshness_integration=False, actual_checked_SAVE2000_qualified=False)

    def late():
        work.plan.fixture(cur, today)
        work.plan.b.api.admin(cur)
        product = work.base.retained.formula.sales.fg.base.BASE_PRODUCT
        root = cur.execute('select coalesce(identity_root_id,id)::text from erp.products where id=%s', (product,)).fetchone()[0]
        current = [p for p in capture(cur)['facts']['products'] if p['root_id'] == root]
        assert len(current) == 1
        product = current[0]['id']
        old_ids = [x[0] for x in cur.execute('select m.id from erp.fg_stock_movements m join erp.products p on p.id=m.product_id '
                   'where coalesce(p.identity_root_id,p.id)=%s::uuid', (root,))]
        # Real Native writer, physical date50 minutes in the past. Neither
        # physical_at nor system_created_at is edited by this control.
        work.plan.found_fg(cur, dict(root=product), '1')
        at, recorded, n = cur.execute('select min(m.physical_at),min(m.system_created_at),count(*)from erp.fg_stock_movements m '
            'join erp.products p on p.id=m.product_id where coalesce(p.identity_root_id,p.id)=%s::uuid '
            'and not(m.id=any(%s::uuid[]))', (root, old_ids)).fetchone()
        assert n > 0 and at < recorded
        cutoff = recorded-timedelta(microseconds=1)
        assert at < cutoff
        native = capture(cur)
        assert native['status'] == 'COMPLETE'
        products = [p for p in native['facts']['products'] if p['root_id'] == root]
        assert len(products) == 1
        before = work.metadata(cur)
        old = digest(cur, products, cutoff)
        fresh = digest(cur, products, native['captured_at'])
        expected_old, expected_fresh = cur.execute("select count(*)filter(where (x->>'physical_at')::timestamptz<=%s "
            "and(x->>'system_created_at')::timestamptz<=%s),count(*)from jsonb_array_elements(%s::jsonb)x "
            "where x->>'root_id'=%s", (cutoff, cutoff, json.dumps(native['facts']['stock']), root)).fetchone()
        assert (int(old['row_count']), int(fresh['row_count'])) == (expected_old, expected_fresh)
        assert expected_fresh >= expected_old+n and fresh['rows_sha256'] != old['rows_sha256']
        assert digest(cur, products, cutoff) == old
        assert work.metadata(cur) == before
        return dict(status='PASS', actual_Native_stock_writer=True, recorded_visibility_not_only_physical_date=True,
                    historical_cutoff_from_actual_recorded_time=True, fresh_digest_changes_old_cutoff_stays_same=True,
                    no_clock_or_row_date_rewrite=True, reader_has_no_effect=True)

    return list(zip(IDS['native'], [catalog, parity, dense, late]))
