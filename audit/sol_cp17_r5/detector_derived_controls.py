"""Finite derived-status/configuration controls with all guards left active.

Nine IDs: seven exact negative controls plus two prevention-only controls.
No protected journal/movement/HPP fact is changed during a counter phase.
"""
from decimal import Decimal
import uuid
import detector_mutable_controls as base
from detector_case import detector_rows, counts
import cp6_bc_probe as bc
import cp7_opening_payroll_cases as opening
import cp7_sales_cases as sales
import cp7_other_obligation_cases as obligations

c, procurement = base.c, base.procurement
record, schema, baseline, phase, restored = base.record, base.schema, base.baseline, base.phase, base.restored

def one_row(cur, table, column, ident):
    c.b.api.admin(cur)
    return cur.execute('select to_jsonb(x) from erp.' + table + ' x where ' + column + '=%s', (ident,)).fetchone()[0]

def state_counter(cur, o, table, column, ident, mutation, args, expected, name):
    c.b.api.admin(cur)
    original = one_row(cur, table, column, ident)
    o.update(source_table=table, source_identity=str(ident), original_row=original)
    before = baseline(cur, o)
    cur.execute('savepoint sol_derived_control')
    try:
        c.b.api.admin(cur)
        changed = cur.execute(mutation, args).fetchall()
        assert len(changed) == 1, ('SOL_DERIVED_EXACTLY_ONE_ROW', changed)
        o['changed_row'] = changed
        phase(cur, o, name, expected, before)
    finally:
        cur.execute('rollback to savepoint sol_derived_control'); c.b.api.admin(cur)
    assert one_row(cur, table, column, ident) == original
    restored(cur, o, before)
    o['full_subject_row_restored'] = True

def refusal(cur, o, name, sql, args, message, before):
    c.b.api.admin(cur)
    cur.execute('savepoint sol_derived_refusal')
    failure = None
    try:
        cur.execute(sql, args)
    except Exception as error:
        failure = dict(sqlstate=error.sqlstate, message=str(error))
    finally:
        cur.execute('rollback to savepoint sol_derived_refusal'); c.b.api.admin(cur)
    o.setdefault('refusals', []).append(dict(name=name, observed=failure, expected_sqlstate='P0001', expected_fragment=message))
    assert failure is not None and failure['sqlstate'] == 'P0001' and message in failure['message'], ('SOL_DERIVED_WRONG_REFUSAL', failure)
    phase(cur, o, name + '_ATOMIC_REFUSAL', {}, before)

def cases(cur, today):
    def kasbon(o):
        o.update(oracle_origin='SOL_ONE_UNALLOCATED_COLLECTIBLE10_STATUS_SET_TO_SETTLED', fixture_origin='ACCEPTED_BC_NATIVE_NOTE_QTY1_MANUAL_PRICE10')
        f = bc.fixture(cur, today, stock_qty=10, cost='2.00', zones=False)
        _, ident = bc.note(cur, f, 1, '10.00', today)
        c.b.api.admin(cur)
        value = cur.execute('select payroll_status,erp.bc_note_item_collectible_v1(id)::text from erp.contractor_material_issue_items where id=%s', (ident,)).fetchone()
        assert value[0] == 'UNALLOCATED' and Decimal(value[1]) == 10
        o['actual_collectible_and_status'] = value
        state_counter(cur, o, 'contractor_material_issue_items', 'id', ident,
                      "update erp.contractor_material_issue_items set payroll_status='SETTLED' where id=%s returning payroll_status", (ident,),
                      {'run_integrity_checks:KASBON_STATUS_MISMATCH': 1}, 'KASBON_STATUS_ONLY')

    def supplier(o):
        o.update(oracle_origin='SOL_FINAL_AP10_PAID0_HEADER_PAID_INCONSISTENCY_TWO_EXPORTED_IDENTITIES', fixture_origin='ACCEPTED_PUBLIC_PROCUREMENT_RECEIPT_QTY1_FINAL10')
        f = procurement.fixture(cur, today, qty='1', price='10', final=True)
        posted = procurement.post(cur, procurement.command(cur, 'SAVE_DRAFT', f['payload']))
        ident = posted['purchase_id']; c.b.api.admin(cur)
        assert cur.execute('select payment_status from erp.material_purchase_headers where id=%s', (ident,)).fetchone() == ('UNPAID',)
        assert Decimal(cur.execute('select erp.material_purchase_final_ap_total(%s)', (ident,)).fetchone()[0]) == 10
        expected = {fn + ':V2620M_SUPPLIER_PAYMENT_EXACT_STATUS': 1 for fn in ('run_v267_financial_truth_checks', 'run_v268_financial_report_checks')}
        state_counter(cur, o, 'material_purchase_headers', 'id', ident,
                      "update erp.material_purchase_headers set payment_status='PAID' where id=%s returning payment_status", (ident,), expected, 'SUPPLIER_PAYMENT_STATUS_ONLY')

    def opening_status(o):
        o.update(oracle_origin='SOL_OPENING65_SETTLED0_STATUS_SET_TO_SETTLED_TWO_EXPORTED_IDENTITIES', fixture_origin='ACCEPTED_BB_POSTED_OPENING_PAYABLE_UPAH_OLD_NET65')
        f = opening.fixture(cur, today); ident = f['balances']['UPAH-OLD']; c.b.api.admin(cur)
        value = cur.execute('select original_amount::text,settled_amount::text,status from erp.opening_subledger_balances where id=%s', (ident,)).fetchone()
        assert (Decimal(value[0]), Decimal(value[1]), value[2]) == (Decimal(65), Decimal(0), 'OPEN')
        o['actual_opening'] = value
        expected = {fn + ':V2620M_OPENING_SUBLEDGER_STATE': 1 for fn in ('run_v267_financial_truth_checks', 'run_v268_financial_report_checks')}
        state_counter(cur, o, 'opening_subledger_balances', 'id', ident,
                      "update erp.opening_subledger_balances set status='SETTLED' where id=%s returning status", (ident,), expected, 'OPENING_DERIVED_STATUS_ONLY')

    def vendor(o):
        o.update(oracle_origin='SOL_POSTED_VENDOR_INVOICE17312_90_PAID0_STATUS_ONLY', fixture_origin='ACCEPTED_P16_NATIVE_LAUNDRY_RECEIPT_AND_BD_INVOICE')
        f = obligations.laundry_fixture(cur, today, invoice=True); ident = f['invoice']; c.b.api.admin(cur)
        value = cur.execute('select total_amount::text,status,(select count(*) from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status=\'POSTED\') from erp.vendor_invoices h where id=%s', (ident,)).fetchone()
        assert (Decimal(value[0]), value[1], value[2]) == (Decimal('17312.90'), 'POSTED', 0)
        o['actual_invoice'] = value
        state_counter(cur, o, 'vendor_invoices', 'id', ident,
                      "update erp.vendor_invoices set status='PAID' where id=%s returning status", (ident,),
                      {'run_v268_financial_report_checks:V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH': 1}, 'VENDOR_DERIVED_STATUS_ONLY')

    def subcent(o):
        o.update(oracle_origin='SOL_ONE_PO_HPP_TOTAL_CACHE_PLUS_ONE_MICRO_UNIT_SUBCENT_AND_EXACT_TARGET_COLLATERAL', fixture_origin='ACCEPTED_NATIVE_FINISH10_GOOD_HPP120')
        f = c.finish_fixture(cur, today, label='SOLR4-SUBCENT'); ident = f['po']; c.b.api.admin(cur)
        value = Decimal(cur.execute('select hpp_total_cost from erp.po_hpp_gl_state where po_id=%s', (ident,)).fetchone()[0])
        assert value == 120
        state_counter(cur, o, 'po_hpp_gl_state', 'po_id', ident,
                      'update erp.po_hpp_gl_state set hpp_total_cost=hpp_total_cost+0.000001 where po_id=%s returning hpp_total_cost::text', (ident,),
                      {'run_v268_financial_report_checks:V2620C_HPP_STATE_HAS_SUBCENT': 1,
                       'run_v268_financial_report_checks:V2620C_PO_HPP_TARGET_STATE_MISMATCH': 1}, 'ONE_MICRO_UNIT_SUBCENT')

    def customer(o):
        o.update(oracle_origin='SOL_ACTIVE_SALE20_PAID0_STATUS_SET_TO_PAID', fixture_origin='ACCEPTED_NATIVE_UNSOURCED_FG_AND_SALE_QTY1_PRICE20')
        f = sales.fixture(cur, today, qty=1, price='20', stock=1)
        sales.fg.post_sale(cur, f['draft']); ident = f['sale']; c.b.api.admin(cur)
        value = cur.execute('select status,erp.sale_net_total(id)::text from erp.sales_headers where id=%s', (ident,)).fetchone()
        assert value[0] == 'POSTED' and Decimal(value[1]) == 20
        # The accepted FOUND_AT_OPNAME lot has no PO/OPENING HPP lineage; status triggers remain active.
        lineage = cur.execute('select lot_origin,po_id from erp.fg_lots where id=%s', (f['lot'],)).fetchone()
        assert lineage[1] is None and lineage[0] != 'OPENING'
        o.update(actual_sale=value, source_lot_lineage=lineage)
        state_counter(cur, o, 'sales_headers', 'id', ident,
                      "update erp.sales_headers set status='PAID' where id=%s returning status", (ident,),
                      {'run_v268_financial_report_checks:V2620H_CUSTOMER_AR_STATUS_MISMATCH': 1}, 'CUSTOMER_DERIVED_STATUS_ONLY')

    def grni_invalid(o):
        o.update(oracle_origin='SOL_NEW_UNUSED_ACTIVE_POSTABLE_LIABILITY_DEBIT_ACCOUNT_VIOLATES_GRNI_CREDIT_PREDICATE', fixture_origin='NEW_UNUSED_CHART_ACCOUNT_BEFORE_POINTER_COUNTER_NO_LEDGER_OR_PREPAYMENT')
        c.b.api.admin(cur)
        tag = 'SR4G-' + uuid.uuid4().hex[:12]
        ident = str(cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) select %s,%s,'LIABILITY',report_group,'DEBIT',true,true from erp.chart_accounts where id=erp.account_id('GRNI_MATERIAL') returning id", (tag, tag)).fetchone()[0])
        assert cur.execute('select count(*) from erp.journal_lines where account_id=%s', (ident,)).fetchone()[0] == 0
        assert cur.execute('select count(*) from erp.initial_import_prepayments where coa_account_id=%s', (ident,)).fetchone()[0] == 0
        original = one_row(cur, 'accounting_account_mappings', 'mapping_key', 'GRNI_MATERIAL')
        o.update(new_account_id=ident, original_mapping=original, ordinary_configuration_UI_claim=False)
        before = baseline(cur, o)
        # Exact single-unit oracle requires the untouched baseline GRNI ledger/subledger to be empty.
        balance = cur.execute("select coalesce(sum(debit-credit),0) from erp.journal_lines where account_id=erp.account_id('GRNI_MATERIAL')").fetchone()[0]
        assert Decimal(balance) == 0
        cur.execute('savepoint sol_derived_control')
        try:
            c.b.api.admin(cur)
            o['changed_mapping'] = cur.execute("update erp.accounting_account_mappings set account_id=%s where mapping_key='GRNI_MATERIAL' returning mapping_key,account_id::text", (ident,)).fetchall()
            assert o['changed_mapping'] == [('GRNI_MATERIAL', ident)]
            phase(cur, o, 'NEW_UNUSED_LIABILITY_DEBIT_POINTER', {'run_v267_financial_truth_checks:V267_GRNI_MAPPING_INVALID': 1}, before)
        finally:
            cur.execute('rollback to savepoint sol_derived_control'); c.b.api.admin(cur)
        assert one_row(cur, 'accounting_account_mappings', 'mapping_key', 'GRNI_MATERIAL') == original
        restored(cur, o, before); o['full_subject_row_restored'] = True

    def accessory_refused(o):
        o.update(oracle_origin='SOL_EXACT_NATIVE_CATEGORY_FREEZE_AND_VARIANT_UOM_VALIDATOR_REFUSALS', fixture_origin='NEW_UNUSED_BC_ACCESSORY_CATEGORY_AND_VARIANT_NO_RECEIPT', detector_negative_control_claim=False)
        f = bc.fixture(cur, today, zones=False, purchase=False); c.b.api.admin(cur)
        alt = cur.execute('select unit_code from erp.uom_definitions where unit_code<>%s and is_active order by unit_code limit 1', (f['pcs'],)).fetchone()[0]
        original = one_row(cur, 'accessory_categories', 'id', f['category'])
        material = one_row(cur, 'materials', 'id', f['material'])
        before = baseline(cur, o)
        refusal(cur, o, 'CATEGORY_WITH_VARIANT_UOM_CHANGE', 'update erp.accessory_categories set base_uom_code=%s where id=%s', (alt, f['category']), 'Accessory category base UOM is frozen', before)
        refusal(cur, o, 'VARIANT_UOM_MISMATCH', 'update erp.materials set unit_code=%s where id=%s', (alt, f['material']), 'must match category base UOM', before)
        assert one_row(cur, 'accessory_categories', 'id', f['category']) == original and one_row(cur, 'materials', 'id', f['material']) == material
        restored(cur, o, before); o.update(full_subject_row_restored=True, disposition='GUARD_PREVENTION_ONLY_NOT_0_1_0')

    def grni_missing_refused(o):
        o.update(oracle_origin='SOL_EXACT_CORE_MAPPING_DELETE_AND_RENAME_GUARD_WITH_NO_ADMIN_BYPASS', fixture_origin='EXISTING_REQUIRED_GRNI_MAPPING_UNCHANGED', detector_negative_control_claim=False)
        c.b.api.admin(cur)
        original = one_row(cur, 'accounting_account_mappings', 'mapping_key', 'GRNI_MATERIAL')
        before = baseline(cur, o)
        refusal(cur, o, 'CORE_MAPPING_DELETE', "delete from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'", (), 'Core accounting mapping GRNI_MATERIAL tidak boleh dihapus', before)
        refusal(cur, o, 'CORE_MAPPING_RENAME', "update erp.accounting_account_mappings set mapping_key='SR4_GRNI_RENAMED' where mapping_key='GRNI_MATERIAL'", (), 'Core accounting mapping key GRNI_MATERIAL tidak boleh di-rename', before)
        assert one_row(cur, 'accounting_account_mappings', 'mapping_key', 'GRNI_MATERIAL') == original
        restored(cur, o, before); o.update(full_subject_row_restored=True, disposition='GUARD_PREVENTION_ONLY_NOT_0_1_0')

    return [record('SOL_R4_D01_KASBON_DERIVED_STATUS', kasbon),
            record('SOL_R4_D01_SUPPLIER_PAYMENT_DERIVED_STATUS', supplier),
            record('SOL_R4_D01_OPENING_DERIVED_STATUS', opening_status),
            record('SOL_R4_D01_VENDOR_PAYMENT_DERIVED_STATUS', vendor),
            record('SOL_R4_D01_HPP_SUBCENT_DERIVED_STATE', subcent),
            record('SOL_R4_D01_CUSTOMER_AR_DERIVED_STATUS', customer),
            record('SOL_R4_D01_GRNI_NEW_UNUSED_DEBIT_MAPPING', grni_invalid),
            record('SOL_R4_D01_ACCESSORY_UOM_GUARD_PREVENTION', accessory_refused),
            record('SOL_R4_D01_CORE_GRNI_GUARD_PREVENTION', grni_missing_refused)]
