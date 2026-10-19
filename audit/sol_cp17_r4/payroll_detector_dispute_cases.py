"""Observe legitimate Nota source resolution; never edits a detector or fact.

The healthy-book contract is zero. A validated false alarm is COUNTEREXAMPLE,
not PASS. A separate opening-only fixture isolates the unexecuted status control.
"""
from decimal import Decimal
from pathlib import Path
import json
import detector_derived_controls as prior
import detector_mutable_controls as base
from detector_case import detector_rows, counts
import cp6_bb_probe as bb
import cp7_nota_cases as nota
import cp7_nota_source_cases as sources

PRODUCT = base.PRODUCT
TARGET = 'run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor'

def record(ident, fn):
    def once():
        o = dict(case_id=ident)
        try:
            fn(o)
            o.setdefault('status', 'PASS')
            return o
        finally:
            p = PRODUCT / 'cp6-proof/t3' / (ident + '_OBSERVATIONS.json')
            p.write_text(json.dumps(o, indent=2, default=str) + '\n')
    return ident, once

def zero_rows(cur):
    rows = detector_rows(cur); values = counts(rows)
    assert len(rows) == len(values) == 167 and all(v == 0 for v in values.values()), 'SOL_DISPUTE_HEALTHY_BASELINE_NOT_ZERO'
    return rows, values

def cases(cur, today):
    def correct_repair(o):
        o.update(oracle_origin='PROMAX_INV_D02_HEALTHY_BOOK_ZERO_WITH_ACTUAL_FG_REPAIR_CONTRACTOR_RESOLUTION',
                 fixture_origin='ACCEPTED_AX_NATIVE_REPAIR_QTY2_AND1_THEN_PUBLIC_CP7_NOTA_SAVE_POST',
                 contract_expected_delta={}, expected_normal_alarm_count=0,
                 no_direct_fact_edit=True, detector_or_guard_edit=False)
        base.c.b.api.admin(cur)
        o['before'], before = zero_rows(cur)
        protected_initial = base.fingerprints(cur)
        cur.execute('savepoint sol_valid_nota_observation')
        try:
            f = sources.repair(cur, today, qty=2)
            second = sources.ax.post(cur, sources.ax.repair_payload(f, 1))
            base.c.b.api.admin(cur)
            o.update(contractor_id=str(f['contractor']), receipt_ids=[f['receipt'], second['receipt_id']])
            o['after_native_repair_sources'], repair_counts = zero_rows(cur)
            assert set(repair_counts) == set(before)
            protected_before_note = base.fingerprints(cur)
            payload = nota.payload(cur, f, today)
            o['nota_payload'] = payload
            draft = nota.command(cur, 'SAVE', payload)
            o['draft_result'] = draft
            o['after_draft'], draft_counts = zero_rows(cur)
            assert set(draft_counts) == set(before) and base.fingerprints(cur) == protected_before_note
            posted = nota.act(cur, 'POST', draft)
            base.c.b.api.admin(cur)
            o['posted_result'] = posted
            header = cur.execute('select id::text,contractor_id::text,status,labor_total::text,net_payable::text from erp.payroll_settlements where id=%s', (posted['payroll_id'],)).fetchone()
            assert header[1] == str(f['contractor']) and header[2] == 'CALCULATED' and Decimal(header[3]) == Decimal(header[4]) == 6000
            o['payroll_header'] = header
            # Resolve the source that the active checker currently omits.
            rows = cur.execute("""select p.id::text,p.source_type,p.source_id::text,p.qty_payable::text,
              p.rate_snapshot::text,p.amount::text,ps.contractor_id::text,w.contractor_id::text,
              p.work_component_id::text,w.work_component_id::text,w.qty_pcs::text,w.rate_per_pcs::text,
              w.amount::text,w.status,r.status,w.receipt_id::text
              from erp.payroll_work_items p join erp.payroll_settlements ps on ps.id=p.payroll_id
              left join erp.fg_unsourced_repair_wages_v1 w on p.source_type='FG_REPAIR' and w.id=p.source_id
              left join erp.fg_unsourced_receipts_v1 r on r.id=w.receipt_id
              where p.payroll_id=%s order by w.qty_pcs,p.id""", (posted['payroll_id'],)).fetchall()
            o['resolved_actual_FG_REPAIR_rows'] = rows
            assert len(rows) == 2 and [Decimal(r[3]) for r in rows] == [1, 2]
            for row in rows:
                assert row[1] == 'FG_REPAIR' and row[6] == row[7] == header[1]
                assert row[8] == row[9] and Decimal(row[3]) == Decimal(row[10])
                assert Decimal(row[4]) == Decimal(row[11]) == 2000
                assert Decimal(row[5]) == Decimal(row[12]) == Decimal(row[3]) * 2000
                assert row[13] == row[14] == 'POSTED' and row[15] in o['receipt_ids']
            assert sum(Decimal(r[5]) for r in rows) == 6000
            o['after_valid_post'] = detector_rows(cur); observed = counts(o['after_valid_post'])
            assert len(observed) == 167 and set(observed) == set(before)
            delta = {k: observed[k] - before[k] for k in before if observed[k] != before[k]}
            o['observed_delta'] = delta
            assert base.fingerprints(cur) == protected_before_note, 'SOL_DISPUTE_NOTA_CHANGED_PROTECTED_FACTS'
            o.update(resolved_contractor_component_qty_rate_amount_all_correct=True,
                     Nota_draft_post_added_no_stock_HPP_journal=True)
            if delta == {}:
                o.update(status='PASS', false_alarm_reproduced=False, contract_satisfied=True)
            elif delta == {TARGET: 2}:
                o.update(status='COUNTEREXAMPLE', false_alarm_reproduced=True, contract_satisfied=False,
                         impact='Two valid FG_REPAIR payroll lines reported as wrong contractor CRITICAL; no payroll amount error or application period-close blocking inferred.')
            else:
                raise AssertionError(('SOL_DISPUTE_UNEXPECTED_ALARM_SET', delta))
        finally:
            cur.execute('rollback to savepoint sol_valid_nota_observation'); base.c.b.api.admin(cur)
        o['after_rollback'], after = zero_rows(cur)
        assert after == before and base.fingerprints(cur) == protected_initial
        o['full_subject_and_protected_restore'] = True

    def opening_only(o):
        o.update(oracle_origin='SOL_OPENING65_SETTLED0_STATUS_TO_SETTLED_TWO_EXPORTED_IDENTITIES_UNCHANGED',
                 fixture_origin='ACCEPTED_BB_FINANCIAL_FIXTURE_ONE_90_LESS25_DOCUMENT_NO_NOTA_OR_PAYROLL_REVIEW')
        f = bb.financial_fixture(cur, today,
                documents=[('CONTRACTOR_PAYABLE', 'UPAH-OLD', '90.00', '25.00')], bank='100.00')
        ident = f['balances']['UPAH-OLD']; base.c.b.api.admin(cur)
        value = cur.execute('select original_amount::text,settled_amount::text,status from erp.opening_subledger_balances where id=%s', (ident,)).fetchone()
        assert (Decimal(value[0]), Decimal(value[1]), value[2]) == (Decimal(65), Decimal(0), 'OPEN')
        o.update(actual_opening=value, source_batch=f['batch'], fixture_scope='Opening-only accepted import, no unrelated Nota/payroll allocation.')
        prior.state_counter(cur, o, 'opening_subledger_balances', 'id', ident,
                  "update erp.opening_subledger_balances set status='SETTLED' where id=%s returning status", (ident,),
                  {fn + ':V2620M_OPENING_SUBLEDGER_STATE': 1 for fn in ('run_v267_financial_truth_checks', 'run_v268_financial_report_checks')},
                  'OPENING_DERIVED_STATUS_ONLY')

    return [record('SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM', correct_repair),
            record('SOL_R4_D01_OPENING_DERIVED_STATUS', opening_only)]
