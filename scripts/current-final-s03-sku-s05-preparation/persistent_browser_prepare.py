"""Native fixture preparation before the read-only browser interval.

No connection or commit is owned here. The complete admitted outer caller
must supply the local installed SKU transaction and retain these observations.
"""
from decimal import Decimal
from pathlib import Path
import importlib
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLAN = (
    ('variants', 'S05_NATIVE_CATEGORY_VARIANTS_PO'),
    ('zero', 'S05_NATIVE_ZERO_REIMBURSEMENT'),
    ('empty', 'S05_NATIVE_EMPTY_AND_NO_OUTPUT'),
)


def prepare(cur, today, state):
    connection = cur.connection
    if (connection.info.host not in ('127.0.0.1', 'localhost') or connection.info.port != 54322
            or cur.execute('select current_database()').fetchone() != ('cp6_rollback',)):
        raise ValueError('S05_SKU_BROWSER_PREP_LOCAL_INSTALLED_PARENT_ONLY')
    spec = importlib.util.spec_from_file_location('s05_sku_browser_native_factory', HERE/'business_reader.py')
    bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
    retained = importlib.import_module('cp7_accessory_standard_report.cases')
    business = bridge.business(retained, state)
    from cp7_p21_current_chain_rehearsal_probe import helper
    stage = business.stage
    product = stage.parent()
    with helper.control.product_catalog(cur):
        product.verify(cur, state)
    original_fixture = business.fixture
    captured = []

    def capture(*args, **kwargs):
        value = original_fixture(*args, **kwargs)
        captured.append(value)
        return value

    business.fixture = capture
    cases = dict(business.cases(cur, today, state))
    prepared, receipts = {}, []
    # The unchanged callbacks keep their own exact money/quantity assertions.
    # These are labelled fixture preparations, not extra Native10 case credit.
    from contextlib import contextmanager
    reader_only = stage.reader_only

    @contextmanager
    def interval(cursor, parent):
        with helper.control.product_catalog(cursor):
            with reader_only(cursor, parent) as reader:
                yield reader

    stage.reader_only = interval
    try:
        for label, case_id in PLAN:
            captured.clear()
            actual = cases[case_id]()
            if actual['status'] != 'PASS' or len(captured) != 1:
                raise ValueError('S05_SKU_EXACT_BROWSER_FIXTURE_PREPARATION_REQUIRED: '+label)
            prepared[label] = captured[0]
            receipts.append(dict(label=label, original_case_id=case_id,
                                 purpose='NATIVE_FIXTURE_PREPARATION_NOT_EXTRA_CASE_CREDIT', actual=actual))
        captured.clear()
        prepared['no_good'] = business.fixture(cur, today, finish=False)
        if len(captured) != 1:
            raise ValueError('S05_SKU_ONE_NO_GOOD_FIXTURE_REQUIRED')
        if len({fixture['po'] for fixture in prepared.values()}) != len(prepared):
            raise ValueError('S05_SKU_DISTINCT_NATIVE_PO_FIXTURES_REQUIRED')
        # Read after all lawful preparation so the same final state is used by
        # the normal App. The exact Native10 numerical assertions above remain.
        fixtures, reads = {}, []
        with stage.reader_only(cur, state):
            for label, fixture in prepared.items():
                report = business.read(cur, fixture, reads)
                business.b.api.admin(cur)
                name, active = cur.execute('select contractor_name,is_active from erp.contractors where id=%s', (fixture['contractor'],)).fetchone()
                po_number = cur.execute('select po_number from erp.production_orders where id=%s', (fixture['po'],)).fetchone()[0]
                if active is not True or not report['rows']:
                    raise ValueError('S05_SKU_VISIBLE_ACTIVE_CONTRACTOR_AND_ROWS_REQUIRED')
                fixtures[label] = dict(day=str(fixture['day']), contractor_id=fixture['contractor'],
                    contractor_name=name, po_id=fixture['po'], po_number=po_number,
                    expected_report=report)
        unknown = fixtures['no_good']['expected_report']
        if (unknown['counts']['lots'] != 0 or any(row['standard_qty'] is not None or row['delta_qty'] is not None for row in unknown['rows'])):
            raise ValueError('S05_SKU_NO_GOOD_IS_UNKNOWN_NOT_ZERO')
        if any(Decimal(row['standard_hpp_cost']) != 0 or Decimal(row['standard_reimbursement']) != 0
               for row in fixtures['zero']['expected_report']['rows']):
            raise ValueError('S05_SKU_ZERO_COST_FIXTURE_REQUIRED')
        return dict(status='ACTUAL_NATIVE_BROWSER_PREREQUISITES_PREPARED', fixtures=fixtures,
            preparation_receipts=receipts, final_actual_Native_reads=reads,
            private_fixture_binding=business.sku_parent_binding,
            Native_case_credit=0, screen_creation_claim=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False)
    finally:
        stage.reader_only = reader_only
        business.fixture = original_fixture
