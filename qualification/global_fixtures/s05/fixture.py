"""Ordinary S05 callbacks for the admitted disposable Global runner.

The caller owns connections, the Global verification receipt, terminals and
backup restoration. Import from a complete checkout of the pinned a625 source.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import cp7_accessory_standard_report.cases as retained
import cp7_master_cases as master

from scope_witness import RECOST_TEMP, capture, compare, temp_terminal


ROOT = Path(retained.__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / 'EXPECTED.json').read_text())
DAY = date.fromisoformat(PLAN['report_period_WIB'][0])
B, PROD, PHYSICAL, ISSUE = retained.b, retained.prod, retained.physical, retained.issues
REPORT = 'public.erp_cp7_get_accessory_standard_report_v1'
READ_FIELDS = PLAN['columns']
CUT_ROWS = '''select r.id::text,s.id::text,y.id::text,y.qty_pcs
from erp.cutting_group_rolls r join erp.cutting_roll_yields y on y.cutting_group_roll_id=r.id
join erp.cutting_group_size_slots s on s.id=y.size_slot_id
where r.cutting_group_id=%s order by s.slot_no'''
PICKUP_ROWS = '''select b.id::text,a.id::text,a.cutting_roll_yield_id::text,a.qty_pcs
from erp.cutting_distribution_batches b join erp.cutting_distribution_allocations a on a.batch_id=b.id
where b.pickup_id=%s order by a.qty_pcs desc'''


def require(condition, label, actual=None):
    if not condition:
        raise AssertionError(label, actual)


def pinned_local_cursor(cur):
    info = cur.connection.info
    require(not cur.connection.autocommit and info.host in ('127.0.0.1', 'localhost')
            and info.port == 54322 and info.dbname == 'cp6_rollback', 'S05_DISPOSABLE_CURSOR_REQUIRED')
    actual = cur.execute("select current_setting('server_version_num'), current_setting('transaction_isolation'), "
                         "current_setting('session_replication_role'), pg_my_temp_schema()").fetchone()
    require(actual == ('170006', 'read committed', 'origin', 0), 'S05_FRESH_ORDINARY_BACKEND_REQUIRED', actual)


def scoped(operation, **bindings):
    """Reuse retained Python callback code without mutating its module."""
    fn = FunctionType(operation.__code__, dict(operation.__globals__, **bindings), operation.__name__,
                      operation.__defaults__, operation.__closure__)
    fn.__kwdefaults__ = operation.__kwdefaults__
    return fn


def load_recipe(parent_catalogue):
    path = ROOT / 'scripts/current-s05-current-ac-editor-qualification/recipe.py'
    spec = importlib.util.spec_from_file_location('s05_global_fixture_dated_recipe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    editor = module.binding.EDITOR
    parent_editor = dict(parent_catalogue['functions'])[editor]
    observations, editor_observations = [], []
    recipe = module.LawfulRecipe(retained, Path(retained.__file__).read_bytes(), observations,
                               state={'after': {'functions': {editor: parent_editor}}},
                               editor_observations=editor_observations)
    return recipe, observations, editor_observations


def assert_open_dates(cur):
    actual = cur.execute("select (clock_timestamp() at time zone 'Asia/Jakarta')::date, "
                         "p.closed_through,c.cutover_date from erp.accounting_period_control p "
                         "cross join cp7_cutover.control c where p.singleton_id=1 and c.singleton_id=1").fetchone()
    earliest = DAY - timedelta(days=1)
    require(actual is not None and actual[0] > DAY and (actual[1] is None or actual[1] < earliest)
            and (actual[2] is None or actual[2] <= earliest), 'S05_FIXED_FIXTURE_DATES_MUST_BE_OPEN', actual)
    return dict(runtime_WIB_day=str(actual[0]), closed_through=str(actual[1]) if actual[1] else None,
                cutover=str(actual[2]) if actual[2] else None, first_physical_day=str(earliest))


def retained_production(cur, contractor_id, observe):
    """Adapt the retained two-size helper to a fixture Mandor and an open period."""
    def inspect_open_period(cursor, requested_through):
        require(requested_through == DAY - timedelta(days=2), 'S05_UNEXPECTED_FABRIC_RECEIPT_DAY', requested_through)
        assert_open_dates(cursor)

    def rpc(cursor, name, payload, request_id=None, expected_version=None):
        rows_sql = {'public.erp_save_cutting_group_before_sewing_v2': CUT_ROWS,
                    'public.erp_save_cutting_pickup_v1': PICKUP_ROWS}[name]
        if payload['action'] != 'POST':
            return PROD.rpc(cursor, name, payload, request_id, expected_version)
        ident = payload['id']
        B.api.admin(cursor)
        before = cursor.execute(rows_sql, (ident,)).fetchall()
        stats = capture(cursor, expected_database='cp6_rollback', mode='transaction')
        result = PROD.rpc(cursor, name, payload, request_id, expected_version)
        B.api.admin(cursor)
        after = cursor.execute(rows_sql, (ident,)).fetchall()
        measured = observe(stats, capture(cursor, expected_database='cp6_rollback', mode='transaction'))
        key = 'cutting' if rows_sql == CUT_ROWS else 'pickup'
        require(len(before) == len(after) == 2 and [row[-1] for row in before] == [60, 40]
                and [row[-1] for row in after] == [60, 40], 'S05_DRAFT_POST_PHYSICAL_QUANTITIES', (before, after))
        replaced_columns = (0, 1, 2) if key == 'cutting' else (0, 1)
        for column in replaced_columns:
            require(not ({row[column] for row in before} & {row[column] for row in after}),
                    'S05_DRAFT_CHILDREN_MUST_BE_REBUILT', (key, before, after))
        if key == 'pickup':
            require([row[2] for row in before] == [row[2] for row in after], 'S05_PICKUP_RETAINED_YIELD_IDS')
        for relation, expected in PLAN['draft_rebuild_deletes'][key].items():
            count = measured['write_attempts'].get(relation, (0, 0, 0))[2]
            require(count == expected, 'S05_DRAFT_REBUILD_DELETE_COUNT', (relation, expected, count))
        trace[key] = dict(parent_id=ident, old_rows=before, rebuilt_rows=after, counters=measured)
        return result

    trace = {}
    prior = SimpleNamespace(**(vars(PROD.prior) | {'set_open_period': inspect_open_period}))
    receipt = scoped(PROD.estimated_receipt, prior=prior)
    prod = SimpleNamespace(**(vars(PROD) | {'CONTRACTOR': contractor_id, 'estimated_receipt': receipt, 'rpc': rpc}))
    chain = SimpleNamespace(**(vars(B.chain) | {'production': prod}))
    sized = scoped(B.two_size_fixture, chain=chain)
    business = SimpleNamespace(**(vars(B) | {'two_size_fixture': sized, 'case_day': lambda today: today - timedelta(days=1)}))
    physical = scoped(PHYSICAL.fixture, b=business)
    fixture = physical(cur, DAY + timedelta(days=3), finish=False)
    require(fixture['day'] == DAY and set(trace) == {'cutting', 'pickup'}, 'S05_RETAINED_COHORT_AND_DRAFT_REBUILD_REQUIRED')
    return fixture, trace


def master_row(cur, code, name, request, *, ident=None, token=None):
    fields = master.mandor_fields(code, str(DAY) if ident is None else None, name=name)
    if ident is None:
        action = 'CREATE'
        result = master.create(cur, 'MANDOR', fields, 'Fixture Global S05 buat mandor biasa', key=request)
    else:
        action = 'UPDATE'
        result = master.act(cur, 'MANDOR', ident, action, fields, 'Fixture Global S05 ubah nama mandor', token=token, key=request)
    entity = result['entity']
    require(result['contract_version'] == 'cp7.master-outcome.v1' and result['kind'] == 'COMMITTED_OUTCOME'
            and result['master_kind'] == 'MANDOR' and result['id'] == entity['id']
            and (result['action'], result['request_id'], entity['code'], entity['name'], entity['active'],
             entity['attendance_required'], entity['notes']) == (action, str(request), code, name, True, False, None),
            'S05_MASTER_OUTCOME', result)
    policy, = entity['policies']
    require((policy['effective_from'], policy['effective_to'], policy['is_special'], policy['attendance_required']) ==
            (str(DAY), None, False, False), 'S05_MASTER_POLICY', policy)
    return result


def rename(cur, record, name, request):
    code, ident = record['entity']['code'], record['id']
    old = master.ws(cur, 'MANDOR', dict(q=code, status='ACTIVE', offset=0, limit=20, id=ident))['selected']
    require(old['entity']['name'] == record['entity']['name'] and old['history'] == 1
            and old['review_token'] == record['review_token'],
            'S05_RENAME_FRESH_MASTER_PREIMAGE', old)
    result = master_row(cur, code, name, request, ident=ident, token=old['review_token'])
    entity = result['entity']
    require(result['id'] == ident and {k: v for k, v in entity.items() if k not in ('name', 'updated_at')}
            == {k: v for k, v in old['entity'].items() if k not in ('name', 'updated_at')}
            and result['review_token'] != old['review_token'], 'S05_RENAME_PRESERVES_ID_AND_POLICY', result)
    return result


def report_workspace(cur, prefix, contractor=None, po=None, offset=0, day=DAY):
    PROD.owner(cur)
    result = cur.execute(f'select {REPORT}(%s,%s,%s,%s,%s,%s,%s)', (day, day, contractor, po, prefix, offset, 30)).fetchone()[0]
    B.api.admin(cur)
    wanted = dict(period_start=str(day), period_end=str(day), contractor_id=contractor, po_id=po, q=prefix, offset=offset, limit=30)
    require(result['business_DML'] is False and result['contract_version'] == 'cp7.accessory-standard-report.v1'
            and result['query'] == wanted, 'S05_EXACT_REPORT_REQUEST', result)
    return result


def page_result(cur, prefix, records):
    want = [dict(id=r['id'], name=r['entity']['name'], active=True) for r in records]
    require(len({r['id'] for r in want}) == len(want) and len(want) in (30, 31), 'S05_PAGE_EXPECTED_IDENTITIES')
    results = []
    for offset in ([0, 30] if len(want) == 31 else [0]):
        result = report_workspace(cur, prefix, offset=offset)
        actual = result['contractors']
        expected = dict(total=len(want), offset=offset, limit=30, next_offset=30 if offset == 0 and len(want) == 31 else None,
                        rows=want[offset:offset + 30])
        require(actual == expected and result['selected_contractor'] is None and result['po_options'] == []
                and result['report'] is None, 'S05_PAGE_ID_ORDER_TOTAL_AND_NEXT', actual)
        results.append(result)
    return results


def page_master_result(cur, prefix, record):
    if record is None:
        current = master.ws(cur, 'MANDOR', dict(q=prefix + '-31', status='ACTIVE', offset=0, limit=20, id=None))
        require(current['page']['rows'] == [] and current['selected'] is None, 'S05_ABORTED_CREATE_ABSENT_FROM_MASTER', current)
        return current
    current = master.ws(cur, 'MANDOR', dict(q=record['entity']['code'], status='ACTIVE', offset=0, limit=20, id=record['id']))
    history = 2 if record['action'] == 'UPDATE' else 1
    require(current['selected']['entity'] == record['entity'] and current['selected']['review_token'] == record['review_token']
            and current['selected']['history'] == history, 'S05_MASTER_PAGE_TERMINAL', current)
    return current


def journal(cur, source, day, expected, *, contractor=None, po=None, product=None):
    rows = cur.execute('''select j.id::text,j.source_type,j.status,j.economic_date,j.transaction_date,j.period_shifted,
      l.account_id::text,l.debit,l.credit,l.contractor_id::text,l.po_id::text,l.product_id::text
      from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_id=%s
      and j.source_type=any(%s::text[]) order by j.source_type,l.id''', (source, list(expected))).fetchall()
    keys = sorted({mapping for lines in expected.values() for mapping in lines})
    mappings = dict(cur.execute('select mapping_key,account_id::text from erp.accounting_account_mappings '
                                'where mapping_key=any(%s::text[])', (keys,)).fetchall())
    require(set(mappings) == set(keys) and len(set(mappings.values())) == len(keys), 'S05_DISTINCT_BOOK_MAPPINGS', mappings)
    for kind, lines in expected.items():
        picked = [r for r in rows if r[1] == kind]
        want = {(mappings[k], max(Decimal(0), Decimal(v)), max(Decimal(0), -Decimal(v))) for k, v in lines.items()}
        require(len({r[0] for r in picked}) == 1 and len(picked) == len(want)
                and {r[6:9] for r in picked} == want
                and all(r[2:6] == ('POSTED', day, day, False) and r[9:] == (contractor, po, product) for r in picked),
                'S05_EXACT_BOOK_LINES', (kind, picked))
    return rows


def stock(cur, fx, quantity):
    a = fx['accessory']
    held = ISSUE.bc.stock(cur, a['material'], a['main'])
    ap, grni, cached, average = ISSUE.invoice.amounts(cur, a)
    require((held, ap, grni, cached, average) == (quantity, 0, 60, quantity, 2), 'S05_STOCK_COST_AP_GRNI', (held, ap, grni, cached, average))
    return dict(quantity_PCS=held, cached_PCS=cached, average_cost=average, remaining_value=held * average, final_AP=ap, GRNI=grni)


def note_source(cur, fx, command, number, qty, hour, po):
    a = fx['accessory']
    value, billed = Decimal(qty) * 2, Decimal(qty) * Decimal('3.25')
    row, = cur.execute('''select h.id::text,h.issue_number,h.status,h.contractor_id::text,h.po_id::text,h.location_id::text,
      h.physical_at,i.id::text,i.material_id::text,i.qty,i.unit_cost_snapshot,i.unit_sale_price_snapshot,i.total_receivable,
      i.transaction_qty,i.transaction_uom_code,i.base_qty_per_transaction_uom,i.accessory_price_version_id,i.material_price_version_id,
      m.id::text,m.qty_signed,m.unit_cost_snapshot,m.physical_at,m.reversal_of_id
      from erp.contractor_material_issues h join erp.contractor_material_issue_items i on i.issue_id=h.id
      join erp.material_stock_movements m on m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and m.source_id=i.id
      and m.movement_type='CONTRACTOR_ISSUE' and m.material_id=i.material_id and m.location_id=h.location_id
      where h.id=%s''', (command['id'],)).fetchall()
    at = datetime.fromisoformat(ISSUE.bc.local_at(DAY, *hour))
    require(row[:7] == (command['id'], number, 'POSTED', fx['contractor'], po, a['main'], at)
            and row[8:18] == (a['material'], qty, 2, Decimal('3.25'), billed, qty, 'PCS', 1, None, None)
            and row[19:] == (-qty, 2, at, None), 'S05_NOTE_ITEM_MOVEMENT_LINEAGE', row)
    free, = cur.execute('select count(*) from erp.bc_free_issue_lines_v1 where issue_id=%s', (command['id'],)).fetchone()
    require(free == 0, 'S05_ORDINARY_MANUAL_NOTE_HAS_NO_FREE_LINES')
    books = journal(cur, command['id'], DAY, {
        'CONTRACTOR_ACCESSORY_STOCK_COST': {'MATERIAL_INVENTORY': -value, 'ACCESSORY_RECOVERY_COGS': value},
        'CONTRACTOR_MATERIAL_RECEIVABLE': {'CONTRACTOR_RECEIVABLE': billed, 'MATERIAL_RECOVERY': -billed},
    }, contractor=fx['contractor'], po=po)
    return dict(id=row[7], issue_id=command['id'], issue_number=number, po_id=po, physical_at=at,
                location_id=a['main'], material_id=a['material'], category_id=a['category'], movement_ids=[row[18]],
                qty=qty, inventory_cost=value, receivable=billed, journal=books, command=command)


def good_source(cur, fx, qc, bom):
    row, = cur.execute('''select h.id::text,h.status,h.physical_at,i.id::text,i.qty_good_pcs,i.qty_bs_pcs,
      i.source_laundry_receipt_line_id::text,i.source_laundry_receipt_batch_size_line_id::text,l.id::text,l.lot_number,
      l.po_id::text,l.product_id::text,l.produced_at,l.initial_qty_pcs,l.lot_origin,c.id::text,c.bom_version_id::text,
      s.id::text,s.bom_item_id::text,s.category_id::text,s.good_qty_pcs,s.qty_per_good_fg_base,s.hpp_method,
      s.total_hpp_cost,s.total_reimbursement,e.id::text,e.contractor_id::text,e.amount,e.payroll_status,m.id::text,m.qty_signed
      from erp.qc_inspections h join erp.qc_inspection_items i on i.inspection_id=h.id
      join erp.fg_lots l on l.qc_item_id=i.id join erp.po_accessory_bom_commitments c on c.po_id=l.po_id and c.product_id=l.product_id
      join erp.fg_accessory_cost_snapshots s on s.lot_id=l.id and s.bom_version_id=c.bom_version_id
      join erp.contractor_accessory_reimbursement_entitlements e on e.snapshot_id=s.id and e.lot_id=l.id
      join erp.fg_stock_movements m on m.lot_id=l.id and m.product_id=l.product_id and m.physical_at=l.produced_at
      and m.source_type='QC_ITEM' and m.source_id=i.id and m.movement_type='QC_GOOD' and m.reversal_of_id is null
      where h.id=%s''', (qc,)).fetchall()
    at = PROD.at(DAY, 14)
    require(row[:3] == (qc, 'POSTED', at) and row[4:8] == (10, 5, fx['receipt_line'], fx['receipt_size'])
            and row[10:15] == (fx['po'], fx['product'], at, 10, 'PRODUCTION') and row[16] == bom
            and row[19:25] == (fx['accessory']['category'], 10, Decimal('0.5'), 'BOM_STANDARD', 10, 10)
            and row[26:29] == (fx['contractor'], 10, 'UNALLOCATED') and row[30] == 10, 'S05_GOOD_BOM_ENTITLEMENT_LINEAGE', row)
    books = journal(cur, row[8], DAY, {'ACCESSORY_REIMBURSE_ACCRUAL': {'WIP': '10', 'CONTRACTOR_PAYABLE': '-10'}},
                    contractor=fx['contractor'], po=fx['po'], product=fx['product'])
    audit_ids = [r[0] for r in cur.execute("select id::text from erp.audit_logs where entity_type='accessory_categories' "
                                           "and entity_id=%s and action='INSERT' and new_data->>'base_uom_code'='PCS' order by id",
                                           (fx['accessory']['category'],)).fetchall()]
    require(len(audit_ids) == 1, 'S05_AUDITED_PCS_CATEGORY', audit_ids)
    return dict(qc_id=qc, qc_item_id=row[3], lot_id=row[8], lot_number=row[9], produced_at=at, unit_basis_audit_ids=audit_ids,
                commitment_id=row[15], bom_version_id=bom, snapshot_id=row[17], bom_item_id=row[18],
                entitlement_id=row[25], fg_movement_id=row[29], journal=books)


class Fixture:
    def __init__(self, *, tag, parent_catalogue, verify_global):
        if not 1 <= len(tag) <= 10 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in tag):
            raise ValueError('S05_USE_AN_ISOLATED_ASCII_ATTEMPT_TAG')
        self.tag = f'S05G-{tag}'
        self.verify_global = verify_global
        self.recipe, self.recipe_observations, self.editor_observations = load_recipe(parent_catalogue)

    def request(self, label):
        return uuid5(NAMESPACE_URL, f'urn:erp-garment:global-s05:{self.tag}:{label}')

    def begin(self, cur):
        pinned_local_cursor(cur)
        proof = self.verify_global(cur)
        require(isinstance(proof, dict) and proof.get('full25_verified') is True
                and proof.get('existing_functions_changed') == 22 and proof.get('new_private_functions') == 19,
                'S05_INSTALLED_GLOBAL_FULL25_REQUIRED', proof)
        B.api.admin(cur)

    def prepare_page(self, cur):
        prefix = self.tag + '-P'
        require(report_workspace(cur, prefix)['contractors']['total'] == 0, 'S05_FRESH_PAGINATION_PREFIX')
        records = [master_row(cur, f'{prefix}-{i:02}', f'{prefix} Mandor {i:02}', self.request(f'page-{i:02}'))
                   for i in range(1, 31)]
        return prefix, records

    def create_page_31(self, cur, prefix):
        return master_row(cur, prefix + '-31', prefix + ' Mandor 31 Awal', self.request('page-31'))

    def rename_page_31(self, cur, record):
        return rename(cur, record, self.tag + '-P Mandor 31 Baru', self.request('page-31-rename'))

    def post_note(self, cur, fx, *, linked):
        a = fx['accessory']
        qty, hour, kind = (4, (16, 0), 'PO') if linked else (7, (0, 30), 'ALL')
        number = f'{self.tag}-{kind}-NOTE'
        po = fx['po'] if linked else None
        payload = dict(id=None, expected_version=None, number=number, contractor_id=fx['contractor'], location_id=a['main'],
                       po_id=po, physical_at=ISSUE.bc.local_at(DAY, *hour), reason='Fixture Global S05 nota eceran',
                       items=[dict(material_id=a['material'], qty=str(qty), mode='MANUAL', manual_price='3.25')])
        request = self.request('note-' + kind)
        result = ISSUE.bc.note_call(cur, 'POST', payload, request)
        require((result['action'], result['status'], result['request_id']) == ('POST', 'POSTED', str(request)),
                'S05_ORDINARY_NOTE_OUTCOME', result)
        return note_source(cur, fx, result, number, qty, hour, po)

    def prepare_report(self, cur, observe):
        """The reader owns no DDL. The caller supplies transaction-scope capture comparison."""
        dates = assert_open_dates(cur)
        prefix = self.tag + '-R'
        require(report_workspace(cur, prefix)['contractors']['total'] == 0, 'S05_FRESH_REPORT_PREFIX')
        record = master_row(cur, prefix, prefix + ' Mandor Awal', self.request('report-create'))
        fx, draft_rebuild = retained_production(cur, record['id'], observe)
        contractor, po_number = cur.execute('select contractor_id::text,po_number from erp.production_orders where id=%s', (fx['po'],)).fetchone()
        require(contractor == record['id'], 'S05_NATIVE_PICKUP_ASSIGNS_THE_REPORT_MANDOR', contractor)
        fx.update(contractor=contractor, po_number=po_number, prefix=prefix, master=record, dates=dates,
                  draft_rebuild=draft_rebuild)
        fx['accessory'] = self.receipt(cur)
        fx['received_stock'] = stock(cur, fx, 30)
        bom = self.recipe(cur, fx, qty='0.5', rate='2')['bom_version_id']
        laundry = cur.execute('''select h.id::text,h.physical_at,l.id::text,s.id::text,s.qty_good_received,
          d.id::text,d.physical_at,ds.distribution_batch_id::text,ds.qty_sent_pcs
          from erp.laundry_receipts h join erp.laundry_receipt_lines l on l.receipt_id=h.id
          join erp.laundry_receipt_batch_size_lines s on s.receipt_line_id=l.id
          join erp.laundry_delivery_batch_size_lines ds on ds.id=s.delivery_batch_size_line_id
          join erp.laundry_delivery_lines dl on dl.id=ds.delivery_line_id and dl.id=l.delivery_line_id
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.id=h.delivery_id where s.id=%s''', (fx['receipt_size'],)).fetchone()
        require(laundry == (fx['receipt'], PROD.at(DAY, 13), fx['receipt_line'], fx['receipt_size'], 30,
                            fx['delivery'], PROD.at(DAY, 11), fx['batch'], 40), 'S05_LAUNDRY_RETURN_SOURCE', laundry)
        fx['laundry_source'] = laundry
        made = PHYSICAL.qc(cur, fx, 10, 5, 14)
        B.api.admin(cur)
        fx['good'] = good_source(cur, fx, made['qc_inspection_id'], bom)
        fx['unlinked'] = self.post_note(cur, fx, linked=False)
        return fx

    def receipt(self, cur):
        """Reuse the E24/P09 estimated receipt without ancillary BC fixture masters or a period update."""
        category = master.create(cur, 'ACCESSORY_CATEGORY', dict(code=self.tag + '-AC', name=self.tag + ' Kancing',
                                 base_uom='PCS', notes=None), key=self.request('category'))['id']
        material = master.create(cur, 'ACCESSORY', dict(code=self.tag + '-MAT', name=self.tag + ' Kancing Perak',
                                 category_id=category), key=self.request('material'))['id']
        supplier_fields = dict(code=self.tag + '-SUP', name=self.tag + ' Supplier', supplier_type='MATERIAL', phone=None, address=None)
        supplier = master.create(cur, 'SUPPLIER', supplier_fields, key=self.request('supplier'))['id']
        main = master.create(cur, 'LOCATION', dict(code=self.tag + '-WH', name=self.tag + ' Gudang',
                             location_type='RAW_MATERIAL_WAREHOUSE'), key=self.request('warehouse'))['id']
        day = DAY - timedelta(days=1)
        at = ISSUE.bc.local_at(day, 9)
        payload = dict(purchase_number=self.tag + '-REC', supplier_id=supplier, location_id=main, physical_at=at,
                       change_reason='E24 sumber penerimaan Global S05', lines=[dict(material_id=material, qty='30', unit_price='2',
                       price_state='ESTIMATED', price_source='MANUAL_ESTIMATE', rolls=[])])
        draft = ISSUE.procurement.command(cur, 'SAVE_DRAFT', payload, self.request('receipt-draft'))
        posted = ISSUE.procurement.post(cur, draft, self.request('receipt-post'))
        purchase = posted['purchase_id']
        row, = cur.execute('''select i.id::text,m.id::text,h.status,h.physical_at,i.qty,i.unit_price,
          i.price_state,m.qty_signed,m.unit_cost_snapshot,m.physical_at,m.reversal_of_id
          from erp.material_purchase_headers h join erp.material_purchase_items i on i.purchase_id=h.id
          join erp.material_stock_movements m on m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=i.id
          and m.material_id=i.material_id and m.location_id=h.location_id and m.movement_type='PURCHASE'
          where h.id=%s and h.location_id=%s and i.material_id=%s''', (purchase, main, material)).fetchall()
        stamp = datetime.fromisoformat(at)
        require(row[2:] == ('POSTED', stamp, 30, 2, 'ESTIMATED', 30, 2, stamp, None), 'S05_RECEIPT_SOURCE', row)
        books = journal(cur, purchase, day, {
            'MATERIAL_PURCHASE': {'MATERIAL_INVENTORY': '60', 'AP_SUPPLIER': '-60'},
            'MATERIAL_PURCHASE_GRNI_RECLASS': {'AP_SUPPLIER': '60', 'GRNI_MATERIAL': '-60'},
        })
        return dict(category=category, material=material, main=main, supplier=supplier, pcs='PCS', received=day,
                    receipt=posted, purchase=purchase, item=row[0], receipt_movement=row[1], journal=books)

    def rename_and_post(self, cur, fx):
        record = rename(cur, fx['master'], fx['prefix'] + ' Mandor Baru', self.request('report-rename'))
        return record, self.post_note(cur, fx, linked=True)


def report_result(cur, fx, record, linked=None):
    """Fresh readback with a source and money oracle independent of the report."""
    B.api.admin(cur)
    after = linked is not None
    values = PLAN['after_COMMIT' if after else 'before_or_after_ABORT']
    status = stock(cur, fx, values['stock_PCS'])
    require(status['remaining_value'] == Decimal(values['stock_value']), 'S05_PHYSICAL_AND_CACHED_INVENTORY_VALUE', status)
    updated = master.ws(cur, 'MANDOR', dict(q=fx['prefix'], status='ACTIVE', offset=0, limit=20, id=fx['contractor']))['selected']
    require(updated['entity']['name'] == record['entity']['name'] and updated['history'] == 1 + int(after)
            and updated['entity']['policies'] == record['entity']['policies'], 'S05_MASTER_TERMINAL_READBACK', updated)
    reads = {}
    for label, po, notes in [('all_PO', None, [fx['unlinked']] + ([linked] if after else [])),
                             ('selected_PO', fx['po'], [linked] if after else [])]:
        ws = report_workspace(cur, fx['prefix'], fx['contractor'], po)
        identity = dict(id=fx['contractor'], name=record['entity']['name'], active=True)
        require(ws['selected_contractor'] == identity and ws['contractors'] == dict(total=1, offset=0, limit=30,
                next_offset=None, rows=[identity]) and ws['po_options'] == [dict(id=fx['po'], number=fx['po_number'])],
                'S05_SELECTED_CONTRACTOR_AND_PO', ws)
        report = ws['report']
        require(report['status'] == 'KNOWN' and report['business_timezone'] == 'Asia/Jakarta'
                and report['po_filter'] == po and report['contractor_id'] == fx['contractor']
                and (report['period_start'], report['period_end']) == (str(DAY), str(DAY))
                and report['definitions'] == dict(actual='POSTED_ISSUE_PHYSICAL_WIB', standard='ACCEPTED_GOOD_PRODUCED_WIB',
                                                   comparison='PERIOD_COHORTS_NOT_PO_WASTE', cost='NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS')
                and report['counts'] == dict(issue_items=len(notes), lots=1, snapshots=1, unknown_lots=0,
                                              unallocated_lots=0, issues_without_po=int(po is None)),
                'S05_SELECTED_KNOWN_WIB_COHORT', report)
        row, = report['rows']
        std, = report['standard_sources']
        lot, = report['lot_sources']
        require(row['comparison_status'] == 'KNOWN' and row['unit'] == 'PCS' and not row['reasons']
                and row['category_id'] == fx['accessory']['category']
                and [Decimal(row[k]) for k in READ_FIELDS] == [Decimal(k) for k in values[label]]
                and set(row['issue_item_ids']) == {n['id'] for n in notes} and row['snapshot_ids'] == [fx['good']['snapshot_id']],
                'S05_QUANTITY_AND_FINANCIAL_ROW', row)
        require(len(report['actual_sources']) == len(notes), 'S05_NOTE_SOURCE_COUNT')
        for actual, expected in zip(report['actual_sources'], notes, strict=True):
            exact = ('id', 'issue_id', 'issue_number', 'po_id', 'location_id', 'material_id', 'category_id', 'movement_ids')
            require(all(actual[k] == expected[k] for k in exact) and actual['unit'] == 'PCS' and actual['unit_known'] is True
                    and datetime.fromisoformat(actual['physical_at']) == expected['physical_at']
                    and [Decimal(actual[k]) for k in ('qty', 'inventory_cost', 'receivable')] == [expected[k] for k in ('qty', 'inventory_cost', 'receivable')],
                    'S05_ACTUAL_REPORT_SOURCE_LINEAGE', actual)
        good = fx['good']
        require((lot['id'], lot['product_id'], lot['po_id'], lot['contractor_id'], lot['commitment_id'], lot['committed_bom']) ==
                (good['lot_id'], fx['product'], fx['po'], fx['contractor'], good['commitment_id'], good['bom_version_id'])
                and lot['recipient_basis'] == 'GUARDED_PO' and datetime.fromisoformat(lot['produced_at']) == good['produced_at']
                and lot['rework_order_id'] is None and lot['decision_id'] is None and not lot['reasons']
                and lot['explicit_zero'] is False and lot['snapshot_count'] == lot['expected_snapshot_count'] == 1
                and (std['id'], std['lot_id'], std['bom_item_id'], std['bom_version_id'], std['category_id']) ==
                (good['snapshot_id'], good['lot_id'], good['bom_item_id'], good['bom_version_id'], fx['accessory']['category'])
                and std['entitlement_ids'] == [good['entitlement_id']] and std['entitlement_known'] is True
                and std['unit_basis_audit_ids'] == good['unit_basis_audit_ids'] and std['unit_known'] is True and std['revisions'] == []
                and std['hpp_method'] == 'BOM_STANDARD' and Decimal(std['good_qty_pcs']) == 10
                and Decimal(std['qty_per_good_fg_base']) == Decimal('0.5')
                and [Decimal(std[k]) for k in ('standard_qty', 'hpp_unit_cost', 'reimbursement_unit_rate', 'hpp_cost', 'reimbursement')]
                == [5, 2, 2, 10, 10], 'S05_STANDARD_REPORT_SOURCE_LINEAGE', (lot, std))
        reads[label] = ws
    prior = report_workspace(cur, fx['prefix'], fx['contractor'], fx['po'], day=DAY - timedelta(days=1))['report']
    require(prior['status'] == 'NO_GOOD_OUTPUT' and all(prior['counts'][k] == 0 for k in prior['counts'])
            and prior['rows'] == [], 'S05_PREVIOUS_WIB_DAY_EXCLUDES_GOOD_AND_NOTE', prior)
    return dict(reads=reads, stock=status, master=updated, prior_WIB_day=prior)


def compare_attempts(before, after, relations):
    observed = compare(before, after, relations, allowed_temp=(RECOST_TEMP,))
    require(not any(observed[k] for k in ('outside_write_attempts', 'relation_identity_changes', 'unexpected_temporary_relations')),
            'S05_FIXTURE_RELATION_SCOPE', observed)
    return observed


def note_write_evidence(before, after, relations):
    observed = compare_attempts(before, after, relations)
    require(observed['write_attempts'].get('erp.bc_free_issue_lines_v1', (0, 0, 0)) == (0, 0, 0)
            and set(after.temp_relations) == {RECOST_TEMP}, 'S05_MANUAL_NOTE_AND_RECOST_TEMP_WITNESS', observed)
    return observed


def observe_temp_after_terminal(cur, staged):
    return temp_terminal(staged, capture(cur, expected_database='cp6_rollback', mode='transaction'))
