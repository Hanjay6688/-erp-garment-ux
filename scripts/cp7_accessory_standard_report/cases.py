"""Predeclared Native cases, NOT executed by source preflight.

All physical/value facts use retained receipt, note, cutting, sewing, laundry,
QC and rework commands. Only administrative masters/drafts are fixture rows.
No posted-row injection, missing-source repair, new financial writer, bypass,
connect/commit, CI dispatch or release assertion. Each reader interval runs on
the actual verified parent and preserves its full data/sequence census.
"""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D
import uuid
import psycopg

from . import stage
import cp7_wip_source_cases as physical
import cp7_f03_e24_issue_cases as issues
import cp6_bf_probe as master
import cp7_qc_source_cases as qc_source
import cp7_snapshot_cases as sessions

b, prod = physical.b, physical.b.chain.production
IDS = (
    'S05_NATIVE_CATEGORY_VARIANTS_PO', 'S05_NATIVE_HISTORICAL_BOM', 'S05_NATIVE_LATE_INVOICE_COST_REVISIONS',
    'S05_NATIVE_ZERO_REIMBURSEMENT', 'S05_NATIVE_EMPTY_AND_NO_OUTPUT',
    'S05_NATIVE_WIB_COHORTS', 'S05_NATIVE_NOTE_DRAFT_INVERSE',
    'S05_NATIVE_QC_INVERSE', 'S05_NATIVE_REWORK_NONE_RECORDED_RECIPIENT',
    'S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL',
)
ZONES = ('Asia/Jakarta', 'UTC', 'Asia/Tokyo', 'Pacific/Kiritimati', 'Etc/GMT+12')


def recipe(cur, f, qty='0.5', rate='2', empty=False, method='BOM_STANDARD'):
    """The actual shared-master command, preserving its complete membership."""
    b.api.admin(cur)
    at = prod.at(f['day'], 0)
    existing = cur.execute('select s.id::text,s.sku,s.revision,v.settings from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id join erp.bf_skus_v1 s on s.id=v.sku_id where m.product_root=%s and v.effective_to is null', (f['product'],)).fetchone()
    roots = [f['product']]
    settings = dict(price=None, bom=[], work_rates=[], laundry_rates=[])
    if existing:
        roots = [r[0] for r in cur.execute('select m.product_root::text from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id where v.sku_id=%s and v.effective_to is null order by m.product_root', (existing[0],))]
        settings = deepcopy(existing[3])
        at = prod.at(f['day'], 17)  # after the committed GOOD source
    settings['bom'] = [] if empty else [dict(category_id=f['accessory']['category'], qty_per_good_fg_base=qty,
        hpp_method=method, hpp_standard_rate=rate if method == 'BOM_STANDARD' else None, hpp_uom_code=f['accessory']['pcs'], reimbursement_rate=rate,
        reimbursement_uom_code=f['accessory']['pcs'])]
    group = master.group(cur, roots, at, sku=existing[1] if existing else None, gid=existing[0] if existing else None,
                         revision=existing[2] if existing else 0, settings=settings)
    result = master.save(cur, [group], at)
    b.api.admin(cur)
    return result


def issue_note(cur, f, qty='7', *, linked=True, action='POST', previous=False, material=None, at=None):
    af = f['accessory']
    payload = issues.payload(af)
    payload.update(number='S05-'+uuid.uuid4().hex[:12], contractor_id=f['contractor'], location_id=af['main'],
                   po_id=f['po'] if linked else None, physical_at=at or issues.bc.local_at(f['day']-timedelta(days=1) if previous else f['day'], 10),
                   reason='S05 actual counted issue, no installed-consumption inference')
    payload['items'][0].update(qty=qty, material_id=material or af['material'])
    result = issues.bc.note_call(cur, action, payload)
    b.api.admin(cur)
    return result


def fixture(cur, today, *, rate='2', empty=False, finish=True, previous_issue=False, method='BOM_STANDARD'):
    f = physical.fixture(cur, today, finish=False)
    b.api.admin(cur)
    f['contractor'] = str(cur.execute('select contractor_id from erp.production_orders where id=%s', (f['po'],)).fetchone()[0])
    f['accessory'] = issues.receipt(cur, f['day'], qty='30')
    recipe(cur, f, rate=rate, empty=empty, method=method)
    f['note'] = issue_note(cur, f, previous=previous_issue)
    if finish:
        made = physical.qc(cur, f, 15, 5, 14)
        b.api.admin(cur)
        f['qc'] = made['qc_inspection_id']
        f['lot'] = str(cur.execute('select l.id from erp.fg_lots l join erp.qc_inspection_items i on i.id=l.qc_item_id where i.inspection_id=%s', (f['qc'],)).fetchone()[0])
    return f


def read(cur, f, traces, *, start=None, end=None, linked=True, subject=None, jwt_role='authenticated'):
    if subject is None and jwt_role == 'authenticated':
        prod.owner(cur)
    else:
        sessions.actor(cur, subject, jwt_role)
    args = (start or f['day'], end or f['day'], f['contractor'], f['po'] if linked else None, '', 0, 30)
    trace = dict(query=[str(a) if a is not None else None for a in args], subject=subject, jwt_role=jwt_role)
    traces.append(trace)
    try:
        value = cur.execute('select public.erp_cp7_get_accessory_standard_report_v1(%s,%s,%s,%s,%s,%s,%s)', args).fetchone()[0]
    except psycopg.Error as error:
        trace['actual_error'] = dict(sqlstate=error.sqlstate, message=str(error))
        raise
    b.api.admin(cur)
    assert value['business_DML'] is False and value['contract_version'] == 'cp7.accessory-standard-report.v1'
    trace['actual'] = value
    return value['report']


def category(r, f):
    return next(x for x in r['rows'] if x['category_id'] == f['accessory']['category'])


def result(traces, **facts):
    return dict(status='PASS', actual_raw_reads=traces, all_reader_intervals_data_sequences_catalog_and_parent_equal=True,
                production_go=False, independent_acceptance=False, full_family_acceptance=False, **facts)


def denied(cur, operation, needle='CP7_ACCESSORY_REPORT_DENIED'):
    # The inherited savepoint helper checks the actual PostgreSQL exception;
    # it never reclassifies a different error as a successful refusal.
    return sessions.refused(cur, operation, needle)


def cases(cur, today, qualified_parent):
    """Caller supplies the actual vendor composition state, never a receipt.

    This factory performs no setup. Run each callable inside the retained
    strict runner's rollback boundary. Keep its returned actual_raw_reads.
    """
    def intervals(operation):
        with stage.reader_only(cur, qualified_parent):
            return operation()

    def variants():
        f = fixture(cur, today); traces = []
        # A second physical variant in exactly the same category, with its
        # own real receipt at another inventory cost. No stock facts seeded.
        af = f['accessory']; variant = str(uuid.uuid4())
        cur.execute("insert into erp.materials(id,material_sku,material_name,material_type,unit_code,accessory_category_id)values(%s,%s,'S05 red button','ACCESSORY',%s,%s)", (variant, 'S05-'+variant, af['pcs'], af['category']))
        payload = dict(purchase_number='S05-'+uuid.uuid4().hex[:12], supplier_id=af['supplier'], location_id=af['main'], physical_at=issues.bc.local_at(af['received'], 11),
                       change_reason='S05 independent physical red variant', lines=[dict(material_id=variant, qty='10', unit_price='4', price_state='ESTIMATED', price_source='MANUAL_ESTIMATE', rolls=[])])
        draft = issues.procurement.command(cur, 'SAVE_DRAFT', payload); issues.procurement.post(cur, draft)
        extra = issue_note(cur, f, '4', material=variant)
        unlinked = issue_note(cur, f, '1', linked=False)
        def observe():
            scoped = read(cur, f, traces); row = category(scoped, f)
            assert row['comparison_status'] == 'KNOWN' and D(row['actual_qty']) == 11 and D(row['standard_qty']) == D('7.5') and D(row['delta_qty']) == D('3.5'), row
            assert D(row['actual_inventory_cost']) == 30 and D(row['standard_hpp_cost']) == 15
            assert {s['material_id'] for s in scoped['actual_sources']} == {af['material'], variant}
            all_pos = read(cur, f, traces, linked=False)
            assert D(category(all_pos, f)['actual_qty']) == 12
            assert any(s['issue_id'] == unlinked['id'] and s['po_id'] is None for s in all_pos['actual_sources'])
            assert not any(s['issue_id'] == unlinked['id'] for s in scoped['actual_sources'])
            return scoped
        intervals(observe)
        return result(traces, two_variants_individual_native_stock_preserved=True, linked11_standard7_5_difference3_5=True,
                      all_PO12_includes_unlinked1=True, second_issue_id=extra['id'])

    def historical():
        f = fixture(cur, today); traces = []
        before = intervals(lambda: read(cur, f, traces))
        old = [(s['id'], s['bom_version_id'], s['bom_item_id'], s['standard_qty'], s['hpp_cost']) for s in before['standard_sources']]
        changed = recipe(cur, f, qty='3', rate='9')
        after = intervals(lambda: read(cur, f, traces))
        assert [(s['id'], s['bom_version_id'], s['bom_item_id'], s['standard_qty'], s['hpp_cost']) for s in after['standard_sources']] == old
        assert D(category(after, f)['standard_qty']) == D('7.5') and D(category(after, f)['standard_hpp_cost']) == 15
        return result(traces, lawful_Native_BOM_successor=changed, original_standard_and_source_identity_preserved=True)

    def zero():
        # Native refuses positive HPP with reimbursement0. This lawful zero
        # cost/rate BOM still makes positive-quantity snapshots at GOOD.
        f = fixture(cur, today, rate='0'); traces = []
        r = intervals(lambda: read(cur, f, traces)); row = category(r, f)
        assert row['comparison_status'] == 'KNOWN' and D(row['standard_qty']) == D('7.5')
        assert D(row['standard_hpp_cost']) == D(row['standard_reimbursement']) == 0
        assert r['standard_sources'] and all(s['entitlement_ids'] == [] and s['entitlement_known'] for s in r['standard_sources'])
        return result(traces, positive_quantity_snapshot_zero_rate_not_lost_to_entitlement_join=True)

    def recost():
        f = fixture(cur, today, method='CATEGORY_MOVING_AVG'); traces = []
        before = intervals(lambda: read(cur, f, traces))
        row = category(before, f)
        assert D(row['actual_inventory_cost']) == 14 and D(row['standard_hpp_cost']) == 15
        af = f['accessory']; movements = issues.material_movements(cur, af); findings = issues.bc.findings(cur)
        payload = issues.invoice.payload(af, '30', '3.50')
        payload.update(invoice_date=str(f['day']+timedelta(days=1)), received_at=issues.bc.local_at(f['day']+timedelta(days=1), 8), due_date=str(f['day']+timedelta(days=15)))
        invoice = issues.invoice.finalize(cur, af, p=payload)
        issues.bc.internal(cur, 'process_cost_recalc_queue', 100)
        assert issues.invoice.amounts(cur, af) == (105, 0, 23, D('3.5'))
        assert issues.material_movements(cur, af) == movements, 'S05_INVOICE_CREATED_PHYSICAL_FACT'
        assert abs(issues.bc.gl(cur, 'MATERIAL_INVENTORY')-issues.bc.subledger_value(cur)) <= D('.05')
        assert issues.bc.new_findings(findings, issues.bc.findings(cur)) == {}
        after = intervals(lambda: read(cur, f, traces)); row = category(after, f)
        assert D(row['actual_inventory_cost']) == D('24.5') and D(row['actual_receivable']) == D('22.75')
        assert D(row['standard_qty']) == D('7.5') and D(row['standard_hpp_cost']) == D('26.25') and D(row['standard_reimbursement']) == 15
        identity = lambda r: [(s['id'], s['bom_version_id'], s['bom_item_id'], s['standard_qty']) for s in r['standard_sources']]
        assert identity(before) == identity(after)
        assert all(s['revisions'] for s in after['standard_sources'])
        return result(traces, actual_late_invoice_id=invoice['invoice_id'], unchanged_physical_movements=True,
                      AP105_GRNI0_stock23_cost3_5=True, exact_Native_snapshot_cost_revision_IDs_preserved=True, no_new_integrity_findings=True)

    def empty_no_output():
        f = fixture(cur, today, empty=True, finish=False); traces = []
        before = intervals(lambda: read(cur, f, traces)); row = category(before, f)
        assert before['status'] == 'UNKNOWN' and row['standard_qty'] is None and row['delta_qty'] is None
        made = physical.qc(cur, f, 15, 5, 14); b.api.admin(cur)
        after = intervals(lambda: read(cur, f, traces)); row = category(after, f)
        assert row['comparison_status'] == 'KNOWN' and D(row['standard_qty']) == 0 and D(row['delta_qty']) == 7
        assert after['standard_sources'] == [] and after['lot_sources'] and all(l['explicit_zero'] for l in after['lot_sources'])
        return result(traces, missing_GOOD_not_zero=True, Native_explicit_empty_commitment_zero=True, qc_id=made['qc_inspection_id'])

    def dates():
        f = fixture(cur, today, previous_issue=True); traces = []
        issue_note(cur, f, '2', at=str(f['day'])+'T00:00:00.000000+07:00')
        issue_note(cur, f, '3', at=str(f['day'])+'T23:59:59.999999+07:00')
        reports = []
        for zone in ZONES:
            cur.execute("select set_config('TimeZone',%s,true)", (zone,))
            reports.append(intervals(lambda: read(cur, f, traces)))
        assert all(r == reports[0] for r in reports)
        now = category(reports[0], f)
        assert D(now['actual_qty']) == 5 and D(now['standard_qty']) == D('7.5') and D(now['delta_qty']) == D('-2.5')
        prior = intervals(lambda: read(cur, f, traces, start=f['day']-timedelta(days=1), end=f['day']-timedelta(days=1)))
        assert D(category(prior, f)['actual_qty']) == 7 and category(prior, f)['standard_qty'] is None
        return result(traces, zones=list(ZONES), previous_day_issue_current_day_GOOD_distinct_cohorts=True)

    def note_inverse():
        f = fixture(cur, today); traces = []
        draft = issue_note(cur, f, '2', action='SAVE_DRAFT')
        before = intervals(lambda: read(cur, f, traces))
        assert D(category(before, f)['actual_qty']) == 7 and all(s['issue_id'] != draft['id'] for s in before['actual_sources'])
        issues.bc.note_call(cur, 'REVERSE', dict(id=f['note']['id'], expected_version=f['note']['row_version'], reason='S05 actual physical note inverse'))
        b.api.admin(cur)
        after = intervals(lambda: read(cur, f, traces)); row = category(after, f)
        assert D(row['actual_qty']) == 0 and D(row['standard_qty']) == D('7.5') and after['actual_sources'] == []
        return result(traces, Native_draft_and_reversed_note_excluded=True, snapshot_standard_survives_issue_inverse=True)

    def qc_inverse():
        f = fixture(cur, today, rate='0'); traces = []
        before = intervals(lambda: read(cur, f, traces)); assert before['lot_sources']
        number = cur.execute('select inspection_number from erp.qc_inspections where id=%s', (f['qc'],)).fetchone()[0]
        qc_source.reverse(cur, dict(qc=f['qc'], number=number))
        after = intervals(lambda: read(cur, f, traces))
        assert after['lot_sources'] == [] and after['standard_sources'] == []
        assert category(after, f)['standard_qty'] is None and category(after, f)['delta_qty'] is None
        return result(traces, Native_QC_inverse_voids_production_lot_without_erasing_original_snapshot_history=True)

    def rework_none():
        # Laundry rework records its recipient from the source PO in the
        # immutable Native decision. Read that recorded choice, including NONE.
        f = fixture(cur, today, empty=True); traces = []
        bs = str(cur.execute('select id from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null', (f['group'],)).fetchone()[0])
        when = lambda hour: prod.at(f['day'], hour)
        bom = cur.execute('select erp.resolve_rework_accessory_bom_v1(%s,%s)::text', (bs, when(15))).fetchone()[0]
        payload = dict(rework_number='S05-RW-'+uuid.uuid4().hex[:10], bs_case_id=bs, destination_type='LAUNDRY', contractor_id=None, vendor_id=f['vendor'], qty_sent=5,
                       physical_sent_at=when(15).isoformat(), status='IN_PROGRESS', return_fg_location_id=physical.base.LOCATION,
                       accessory_bom_version_id=bom, accessory_bom_item_ids=[], components=[], change_reason='S05 explicit no-accessory laundry rework')
        made = b.chain.bs_action(cur, 'SAVE_REWORK', payload); rid = made['result']['rework_order_id']; b.api.admin(cur)
        completed = b.chain.bs_action(cur, 'COMPLETE_REWORK', dict(rework_order_id=rid, qty_good=3, qty_bs=2, completed_at=when(16).isoformat(),
                       return_fg_location_id=physical.base.LOCATION, change_reason='S05 Native three GOOD rework return'), b.chain.version(cur, 'rework_orders', rid)); b.api.admin(cur)
        r = intervals(lambda: read(cur, f, traces)); recovered = next(l for l in r['lot_sources'] if l['id'] == completed['result']['good_fg_lot_id'])
        authoritative = str(cur.execute('select reimbursement_contractor_id from erp.rework_accessory_decisions where rework_order_id=%s', (rid,)).fetchone()[0])
        assert recovered['decision_state'] == 'NONE' and recovered['recipient_basis'] == 'REWORK_DECISION'
        assert recovered['contractor_id'] == authoritative == f['contractor'] and recovered['explicit_zero'] and not recovered['reasons']
        assert r['status'] == 'KNOWN' and D(category(r, f)['standard_qty']) == 0
        return result(traces, actual_Native_rework_NONE_exact_recorded_recipient=True)

    def access():
        f = fixture(cur, today, empty=True); traces = []
        subject, role = sessions.custom_actor(cur, finance=True)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.contractor_accessory.view')", (role,))
        intervals(lambda: denied(cur, lambda: read(cur, f, traces, subject=subject)))  # STAFF, even with both rights
        intervals(lambda: denied(cur, lambda: read(cur, f, traces, jwt_role='service_role')))
        admin_subject, _ = sessions.custom_actor(cur, finance=True)
        admin_role = cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s', (admin_role, admin_subject))
        for permission in ('finance.contractor_accessory.view', 'finance.hpp.view'):
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing', (admin_role, permission))
        intervals(lambda: read(cur, f, traces, subject=admin_subject))
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'", (admin_role,))
        intervals(lambda: denied(cur, lambda: read(cur, f, traces, subject=admin_subject)))
        prod.owner(cur); owner_auth = str(cur.execute('select auth.uid()').fetchone()[0]); b.api.admin(cur)
        intervals(lambda: read(cur, f, traces, subject=owner_auth))
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner_auth,))
        intervals(lambda: denied(cur, lambda: read(cur, f, traces, subject=owner_auth)))
        assert len([t for t in traces if 'actual_error' in t]) == 4
        assert all(t['actual_error']['sqlstate'] == '42501' for t in traces if 'actual_error' in t)
        return result(traces, live_inactive_user_and_revoked_Admin_permission_refused=True, staff_with_rights_and_service_JWT_refused=True,
                      all_private_ACLs_and_no_new_Native_writer_grants_checked_each_interval=True)

    operations = (variants, historical, recost, zero, empty_no_output, dates, note_inverse, qc_inverse, rework_none, access)
    assert len(operations) == len(IDS)
    return list(zip(IDS, operations))
