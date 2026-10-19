"""Finite current facade limits: exact text, numeric18,2 and real list/UI helpers."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
import cp7_procurement_cases as procurement
import cp6_bd_probe as bd
import cp7_snapshot_cases as auth


def record(ident, fn):
    observed = dict(case_id=ident, oracle_origin='SOL_LITERAL_TYPE_AND_SCALE_BOUNDARY', source='CURRENT_PINNED_FACADE')
    def once():
        try:
            fn(observed)
            observed['status'] = 'PASS'
            return observed
        finally:
            out = PRODUCT / 'cp6-proof/t3' / (ident + '_OBSERVATIONS.json')
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(observed, indent=2, default=str) + '\n')
    return ident, once


def cases(cur, today):
    def procurement_prices(o):
        o.update(fixture_origin='ACCEPTED_PUBLIC_PROCUREMENT_FIXTURE_WITH_SOL_NEW_BOUNDARY_AMOUNTS', oracle_origin='SOL_MAX12_INTEGER6_DECIMAL_AND_HALF_UP_DOCUMENT_CENTS')
        o['values'] = []
        for value in ('999999999999.999998', '999999999999.999999', '1000000000000.000000'):
            f = procurement.fixture(cur, today, qty='1', price=value, final=True)
            before = procurement.b.boundary.snapshot(cur)
            if value == '1000000000000.000000':
                detail = auth.refused(cur, lambda: procurement.command(cur, 'SAVE_DRAFT', f['payload']), 'CP7_PROCUREMENT_EXACT_DECIMAL')
                assert procurement.b.boundary.snapshot(cur) == before
                o['values'].append(dict(input=value, outcome='REFUSED_AT_13_INTEGER_DIGITS', detail=detail, no_effect=True))
            else:
                draft = procurement.command(cur, 'SAVE_DRAFT', f['payload'])
                posted = procurement.post(cur, draft)
                data = procurement.workspace(cur, dict(purchase_id=posted['purchase_id']))
                item = data['detail']['items'][0]
                assert item['finance']['unit_price'] == value and Decimal(item['qty']) == 1
                # Unit price is six-decimal; document AP is round-to-cent.
                expected = Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ap, grni = cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (posted['purchase_id'], posted['purchase_id'])).fetchone()
                assert Decimal(ap) == expected and Decimal(grni) == 0
                assert procurement.qty(cur, f) == (1, 1)
                o['values'].append(dict(input=value, saved_unit_price=item['finance']['unit_price'], posted_ap=str(ap), expected_ap=str(expected), posted=posted, response=data))
    def procurement_scale(o):
        o.update(fixture_origin='ACCEPTED_PUBLIC_PROCUREMENT_FIXTURE_WITH_SOL_NEW_SCALE_INPUTS', oracle_origin='SOL_SIX_DECIMAL_TEXT_BOUNDARY_NO_ROUNDING_OR_STOCK')
        o['values'] = []
        for value in ('0.00001', '0.000001', '0.0000001'):
            f = procurement.fixture(cur, today, qty='1', price=value, final=True)
            before = procurement.b.boundary.snapshot(cur)
            if value == '0.0000001':
                detail = auth.refused(cur, lambda: procurement.command(cur, 'SAVE_DRAFT', f['payload']), 'CP7_PROCUREMENT_EXACT_DECIMAL')
                assert procurement.b.boundary.snapshot(cur) == before
                o['values'].append(dict(input=value, outcome='REFUSED_SEVENTH_DECIMAL', detail=detail, no_effect=True))
            else:
                draft = procurement.command(cur, 'SAVE_DRAFT', f['payload'])
                data = procurement.workspace(cur, dict(purchase_id=draft['purchase_id']))
                observed = data['detail']['items'][0]['finance']['unit_price']
                assert Decimal(observed) == Decimal(value) and procurement.qty(cur, f) == (0, 0)
                o['values'].append(dict(input=value, observed=observed, draft=draft, stock_unchanged=True))
    def procurement_cent32(o):
        o.update(fixture_origin='ACCEPTED_PUBLIC_PROCUREMENT_FIXTURE_WITH_SOL_32BIT_CENT_AROUND_INPUTS', oracle_origin='SOL_LITERAL2147483647_2147483648_2147483649_CENTS_EXACT')
        o['values'] = []
        for value in ('21474836.47', '21474836.48', '21474836.49'):
            f = procurement.fixture(cur, today, qty='1', price=value, final=True)
            draft = procurement.command(cur, 'SAVE_DRAFT', f['payload']); posted = procurement.post(cur, draft)
            data = procurement.workspace(cur, dict(purchase_id=posted['purchase_id']))
            ap, grni = cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (posted['purchase_id'], posted['purchase_id'])).fetchone()
            assert Decimal(data['detail']['items'][0]['finance']['unit_price']) == Decimal(value)
            assert Decimal(ap) == Decimal(value) and Decimal(grni) == 0 and procurement.qty(cur, f) == (1, 1)
            o['values'].append(dict(input=value, cents=str(Decimal(value)*100), posted_ap=str(ap), posted=posted, response=data))
    def laundry_native18(o):
        o.update(fixture_origin='ACCEPTED_NATIVE_LAUNDRY_RECEIPT10_THEN_SOL_PUBLIC_DRAFT_AMOUNTS', oracle_origin='SOL_NUMERIC18_2_EXACT_MAXIMUM_AND_TWO_LINE_ZERO_DISCOUNT')
        fx = bd.fixture(cur, today - timedelta(days=3), 'SOLR4-NUM18')
        bd.process_rate(cur, fx, '2.00')
        delivery = bd.plain_delivery(cur, fx, 10, 11)
        receipt = bd.receive(cur, delivery, fx, 10, 13)['receipt_id']
        bd.api.admin(cur); line = bd.receipt_line(cur, receipt)
        columns = cur.execute("select column_name,data_type,numeric_precision,numeric_scale from information_schema.columns where table_schema='erp' and table_name='bd_laundry_invoices_v1' and column_name in('header_total','discount_amount') order by column_name").fetchall()
        assert {row[0]:list(row[1:]) for row in columns} == {'header_total':['numeric',18,2], 'discount_amount':['numeric',18,2]}
        o.update(columns=columns, values=[])
        for value in ('9999999999999999.98', '9999999999999999.99', '10000000000000000.00'):
            before = bd.boundary.snapshot(cur)
            if value == '10000000000000000.00':
                detail = auth.refused(cur, lambda: bd.invoice(cur, fx, [dict(line=line, qty=1, amount=value)], value, post=False, discount_amount='0.00'), 'BD_AMOUNT_INVALID')
                assert bd.boundary.snapshot(cur) == before
                o['values'].append(dict(input=value, outcome='REFUSED_AT_17_INTEGER_DIGITS', detail=detail, no_effect=True))
            else:
                draft, _ = bd.invoice(cur, fx, [dict(line=line, qty=1, amount=value)], value, post=False, discount_amount='0.00')
                header = cur.execute('select status,header_total::text,discount_amount::text from erp.bd_laundry_invoices_v1 where id=%s', (draft['invoice_id'],)).fetchone()
                lines = cur.execute('select qty,amount::text from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s', (draft['invoice_id'],)).fetchall()
                assert header == ('DRAFT', value, '0.00') and lines == [(1, value)]
                assert cur.execute('select count(*) from erp.vendor_invoices where id=%s', (draft['invoice_id'],)).fetchone()[0] == 0
                o['values'].append(dict(input=value, header=header, lines=lines, core_payable_not_created=True))
        # Same real receipt, multiple billing lines and a literal zero discount;
        # save/read only. Posted billing/cash is already covered in Q2, not faked.
        draft, _ = bd.invoice(cur, fx, [dict(line=line, qty=1, amount='10737418.24'), dict(line=line, qty=1, amount='10737418.25')], '21474836.49', post=False, discount_amount='0.00')
        values = cur.execute('select i.header_total::text,i.discount_amount::text,sum(l.amount)::text,count(*) from erp.bd_laundry_invoices_v1 i join erp.bd_laundry_invoice_lines_v1 l on l.invoice_id=i.id where i.id=%s group by i.id', (draft['invoice_id'],)).fetchone()
        assert values == ('21474836.49','0.00','21474836.49',2)
        assert Decimal(bd.ap(cur, fx['vendor'])) == 0
        o['two_line_zero_discount'] = values
        o['scope'] = 'Public BD draft/header numeric18,2 and exact line sums; no claim of maximum-size invoice POST/cash/recost or physical-device form acceptance.'
    def client_helpers(o):
        o.update(fixture_origin='ACTUAL_CANDIDATE_SOURCE_PURE_HELPERS_NO_BUSINESS_FIXTURE', oracle_origin='SOL_LITERAL_ACTUAL_HELPER_INPUT_RANGES')
        result = subprocess.run(['node', str(ROOT / 'numeric_boundary_client.mjs'), str(PRODUCT)], cwd=PRODUCT, text=True, capture_output=True)
        o['stderr'] = result.stderr
        assert result.returncode == 0, result.stderr
        observed = json.loads(result.stdout)
        assert observed['status'] == 'PASS' and observed['pinned_source_not_modified'] is True
        assert len(observed['controls']) == 27, 'SOL_NUMERIC_EXACT_CLIENT_CONTROL_COUNT'
        o['actual_client_helpers'] = observed
        o['scope'] = 'Actual TypeScript helpers transpiled in-memory; private pool parser functions are explicitly exported only in derivative text. No browser/device or complete form lifecycle credit.'
    return [record('SOL_R4_SKN26_PROCUREMENT_12_6_BOUNDARY', procurement_prices), record('SOL_R4_SKN26_PROCUREMENT_SIX_DECIMAL_SCALE', procurement_scale), record('SOL_R4_SKN26_PROCUREMENT_32BIT_CENT_AROUND', procurement_cent32), record('SOL_R4_SKN26_LAUNDRY_NUMERIC18_2_AND_TWO_LINES', laundry_native18), record('SOL_R4_SKN26_ACTUAL_CLIENT_BOUNDARY_HELPERS', client_helpers)]
