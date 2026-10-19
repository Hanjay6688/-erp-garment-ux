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
        o.update(fixture_origin='ACCEPTED_PUBLIC_PROCUREMENT_FIXTURE_WITH_SOL_NEW_BOUNDARY_AMOUNTS', oracle_origin='SOL_RAW_AP_SIX_DECIMAL_AND_DISTINCT_POSTED_GL_CENTS')
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
                # Source contract has distinct dimensions: raw final-AP helper
                # preserves qty*unit-cost; actual posted AP journal is cent-rounded.
                expected = Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ap, grni = cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (posted['purchase_id'], posted['purchase_id'])).fetchone()
                gl = cur.execute("select j.id::text,j.source_type,j.source_id::text,j.status,l.debit::text,l.credit::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='MATERIAL_PURCHASE' and j.source_id=%s and l.account_id=erp.account_id('AP_SUPPLIER') order by j.id,l.id", (posted['purchase_id'],)).fetchall()
                # Record every observed dimension BEFORE asserting it.
                o['values'].append(dict(input=value, saved_unit_price=item['finance']['unit_price'], raw_ap=str(ap), expected_raw_ap=value, raw_grni=str(grni), actual_ap_journal=gl, expected_journal_ap=str(expected), posted=posted, response=data))
                assert Decimal(ap) == Decimal(value) and Decimal(grni) == 0, 'SOL_RAW_FINAL_AP_DIMENSION'
                assert len(gl) == 1 and gl[0][1:4] == ('MATERIAL_PURCHASE', posted['purchase_id'], 'POSTED'), ('SOL_OWN_RECEIPT_AP_JOURNAL', gl)
                assert Decimal(gl[0][4]) == 0 and Decimal(gl[0][5]) == expected, ('SOL_POSTED_GL_AP_CENT_DIMENSION', gl, expected)
                assert procurement.qty(cur, f) == (1, 1)

    def client_helpers(o):
        o.update(fixture_origin='ACTUAL_CANDIDATE_SOURCE_PURE_HELPERS_NO_BUSINESS_FIXTURE', oracle_origin='SOL_LITERAL_ACTUAL_HELPER_INPUT_RANGES')
        result = subprocess.run(['node', str(ROOT / 'numeric_boundary_client_q2.mjs'), str(PRODUCT)], cwd=PRODUCT, text=True, capture_output=True)
        o['stderr'] = result.stderr
        o['stdout'] = result.stdout
        assert result.returncode == 0, result.stderr
        observed = json.loads(result.stdout)
        assert observed['status'] == 'PASS' and observed['pinned_source_not_modified'] is True
        assert len(observed['controls']) == 27, 'SOL_NUMERIC_EXACT_CLIENT_CONTROL_COUNT'
        o['actual_client_helpers'] = observed
        o['scope'] = 'Actual TypeScript helpers transpiled in-memory; private pool parser functions are explicitly exported only in derivative text. No browser/device or complete form lifecycle credit.'

    return [record('SOL_R4_SKN26_PROCUREMENT_12_6_BOUNDARY', procurement_prices), record('SOL_R4_SKN26_ACTUAL_CLIENT_BOUNDARY_HELPERS', client_helpers)]
