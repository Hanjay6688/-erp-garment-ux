"""Finite independent R5 reader qualification in the disposable Native runner.

The numerical sale/return oracles are literal. For differential checks all eleven
pre-R5 canonical definitions are installed together inside a rolled-back
savepoint, so nested calls also use the old graph. No trigger or grant is changed.
"""
from datetime import timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import json
import re
import uuid
import psycopg
from psycopg import sql
import cp6_bd_probe as bd
import cp7_cp17_fix_cases as c
import cp7_nota_cases as nota
import cp7_nota_source_cases as sources
import detector_mutable_controls as protected
from detector_case import detector_rows, counts
from reader_input_fixture import build_reader_fixture, collect_reader_inputs

PRODUCT = protected.PRODUCT
READERS = {
    'erp._v268_financial_report_checks_pre_scope()': 2,
    'erp.bb_opening_credit_account_v1(uuid)': 6,
    'erp.compute_non_po_product_hpp_book_v2620f(uuid)': 4,
    'erp.compute_po_hpp_gl_book_v2620e(uuid)': 8,
    'erp.get_owner_financial_snapshot_v2(date,date,date)': 11,
    'erp.initial_prepayment_checks_v1()': 5,
    'erp.pocket_fabric_checks_v1()': 2,
    'erp.pocket_period_book_v1(uuid)': 4,
    'erp.run_v267_financial_truth_checks()': 7,
    'erp.run_v268_financial_report_checks()': 14,
    'erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)': 6,
}
WRAP = re.compile(r"\(select erp\.account_id\('([A-Z0-9_]+)'\)\)")
IDS = ['SOL_R5_READER_FULL_GRAPH_PO_SALE_RETURN',
       'SOL_R5_READER_PREPARED_MAPPING_FRESHNESS',
       'SOL_R5_VALID_REPAIR_REVERSED_AND_REALLOCATED_ZERO_ALARM']


def definitions(cur):
    bd.api.admin(cur)
    return {s: cur.execute('select pg_get_functiondef(%s::regprocedure)', (s,)).fetchone()[0] for s in READERS}


def legacy_graph(installed):
    old = {}
    for s, definition in installed.items():
        old[s], n = WRAP.subn(lambda m: "erp.account_id('%s')" % m[1], definition)
        assert n == READERS[s] and not WRAP.search(old[s]), ('SOL_R5_LITERAL_UNWRAP_COUNT', s, n)
    return old


def claims(cur):
    bd.api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true)",
                (json.dumps(dict(sub=str(bd.chain.production.base.OPERATOR_AUTH), role='authenticated')),))


def answer(cur, signature, args):
    claims(cur)
    name, tail = signature.split('(')
    types = tail[:-1].split(',') if tail != ')' else []
    assert len(args) == len(types), (signature, args)
    placeholders = ','.join('%s::' + t for t in types)
    cur.execute('savepoint sol_r5_reader_call')
    try:
        rows = cur.execute('select to_jsonb(x)::text from ' + name + '(' + placeholders + ') x', args).fetchall()
        # Row sets are compared as multisets, including duplicates; nested JSON
        # arrays and every scalar value remain intact.
        return dict(kind='ROWS', rows=sorted(r[0] for r in rows))
    except psycopg.Error as e:
        cur.execute('rollback to savepoint sol_r5_reader_call')
        return dict(kind='ERROR', sqlstate=e.sqlstate, message=str(e).split('\n')[0])
    finally:
        cur.execute('release savepoint sol_r5_reader_call'); bd.api.admin(cur)


def compare_graph(cur, inputs, o, label):
    installed = definitions(cur)
    old = legacy_graph(installed)
    protected_before = protected.fingerprints(cur)
    answers = {s: [answer(cur, s, a) for a in inputs.get(s, [()])] for s in READERS}
    cur.execute('savepoint sol_r5_old_reader_graph')
    try:
        for definition in old.values():
            bd.api.admin(cur); cur.execute(definition)
        observed = definitions(cur)
        assert observed == old, 'SOL_R5_FULL_OLD_GRAPH_NOT_INSTALLED'
        previous = {s: [answer(cur, s, a) for a in inputs.get(s, [()])] for s in READERS}
    finally:
        bd.api.admin(cur); cur.execute('rollback to savepoint sol_r5_old_reader_graph')
        cur.execute('release savepoint sol_r5_old_reader_graph')
    row = dict(label=label, all_eleven_legacy_definitions_installed_together=True,
               inputs={s: [list(map(str, a)) for a in inputs.get(s, [()])] for s in READERS},
               installed_answers=answers, legacy_graph_answers=previous,
               installed_sha256={s: sha256(v.encode()).hexdigest() for s, v in installed.items()},
               legacy_sha256={s: sha256(v.encode()).hexdigest() for s, v in old.items()})
    o.setdefault('graph_comparisons', []).append(row)
    assert answers == previous, ('SOL_R5_READER_GRAPH_ANSWER_CHANGED', label)
    assert definitions(cur) == installed, 'SOL_R5_READER_GRAPH_NOT_RESTORED'
    assert protected.fingerprints(cur) == protected_before, 'SOL_R5_READ_CHANGED_FACTS_OR_GUARDS'
    row.update(same_rows_or_exact_refusal=True, protected_facts_and_guards_unchanged=True, graph_restored=True)
    return answers


def produced(cur, today, label):
    f = c.finish_fixture(cur, today, label=label)
    bd.api.admin(cur)
    assert tuple(map(D, c.po_hpp(cur, f['po']))) == (D(120), D(10)), 'SOL_R5_FIXTURE_HPP_120_QTY10'
    lineage = cur.execute('select po_id::text,lot_origin from erp.fg_lots where id=%s', (f['lot'],)).fetchone()
    assert lineage == (str(f['po']), 'PRODUCTION'), lineage
    locations = cur.execute('select distinct location_id::text from erp.fg_stock_movements where lot_id=%s', (f['lot'],)).fetchall()
    assert len(locations) == 1
    return dict(f, location=locations[0][0])


def book(cur, po):
    bd.api.admin(cur)
    return tuple(map(D, cur.execute('select * from erp.compute_po_hpp_gl_book_v2620e(%s)', (po,)).fetchone()))


def make_sale(cur, f):
    customer = bd.chain.base.create_customer(cur, 'SR5-' + uuid.uuid4().hex[:10])
    bd.chain.production.owner(cur)
    at = cur.execute('select statement_timestamp()-interval \'10 minutes\'').fetchone()[0]
    made = cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',
                       (json.dumps(dict(sale_number='SR5-' + uuid.uuid4().hex[:12], customer_id=str(customer),
                                        source_location_id=f['location'], sale_date=at.isoformat(),
                                        reason='Uji Sol r5, dua barang dari PO dengan HPP dua belas',
                                        items=[dict(product_id=f['product'], qty_pcs=2, unit_price_snapshot='20', discount_amount=0)])),
                        uuid.uuid4())).fetchone()[0]
    bd.api.admin(cur)
    version = cur.execute('select row_version from erp.sales_headers where id=%s', (made['sale_id'],)).fetchone()[0]
    bd.chain.production.owner(cur)
    cur.execute('select erp.post_sale_v2(%s,%s,%s)', (made['sale_id'], uuid.uuid4(), version))
    bd.api.admin(cur)
    allocations = cur.execute('select a.lot_id::text,a.qty_pcs::text from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s', (made['sale_id'],)).fetchall()
    assert len(allocations) == 1 and allocations[0][0] == f['lot'] and D(allocations[0][1]) == 2, allocations
    return made['sale_id']


def make_return(cur, sale):
    ident = str(uuid.uuid4())
    bd.chain.production.owner(cur)
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) select %s,%s,id,customer_id,statement_timestamp(),erp.current_app_user_id() from erp.sales_headers where id=%s",
                (ident, 'SR5-RET-' + ident, sale))
    cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,20 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.sale_item_id in(select id from erp.sales_items where sale_id=%s)", (ident, sale))
    cur.execute('select erp.post_sales_return(%s)', (ident,)); bd.api.admin(cur)
    return ident


def lifecycle(cur, kind, source, po, expected):
    bd.api.admin(cur)
    journals = cur.execute("select id::text from erp.journal_entries where source_type=%s and source_id=%s and status='POSTED'", (kind, source)).fetchall()
    assert len(journals) == 1, journals
    amount = cur.execute('select erp.sale_lifecycle_po_hpp_amount_v2620d(%s,%s)', (journals[0][0], po)).fetchone()[0]
    assert amount is not None and D(amount) == D(expected), ('SOL_R5_LIFECYCLE_LITERAL_ORACLE', kind, amount, expected)
    return dict(kind=kind, source_id=source, journal_id=journals[0][0], po_id=po, expected=str(expected), observed=str(amount))


def expanded_inputs(cur, today, po, product, journal_pairs=()):
    out = collect_reader_inputs(cur, today)
    missing = uuid.UUID('08d87ac7-eefb-4537-a6c4-d826bf9a5bad')
    for s in READERS:
        args = s.split('(')[1][:-1]
        if args == 'uuid':
            out.setdefault(s, []).extend([(None,), (missing,)])
        elif args == 'uuid,uuid':
            out.setdefault(s, []).extend([(None, None), (missing, missing)])
        elif args == 'date,date,date':
            out[s].append((today - timedelta(days=500), today - timedelta(days=499), today - timedelta(days=499)))
    out['erp.compute_po_hpp_gl_book_v2620e(uuid)'].append((po,))
    out['erp.compute_non_po_product_hpp_book_v2620f(uuid)'].append((product,))
    out['erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)'].extend(journal_pairs)
    return out


def record(ident, operation):
    def once():
        o = dict(case_id=ident, oracle_origin='SOL_LITERAL_NUMBERS_AND_COMPLETE_OLD_VERSUS_NEW_READER_GRAPH',
                 product_candidate='17fa25075ba77f0853c3c16f504288ace03eec35',
                 runtime='ISOLATED_LOOPBACK_NATIVE_DATABASE', production_go=False,
                 trigger_or_privilege_changed=False)
        try:
            operation(o); o['status'] = 'PASS'; return o
        finally:
            p = PRODUCT / 'cp6-proof/t3' / (ident + '_OBSERVATIONS.json')
            p.write_text(json.dumps(o, indent=2, default=str) + '\n')
    return ident, once


def cases(cur, today):
    def full_graph(o):
        o['fixture_origin'] = 'WRITER_ACCEPTED_BB_BE_INPUT_BUILDERS_PLUS_SOL_NATIVE_PRODUCED_PO_SALE_AND_RETURN'
        o['input_fixture'] = build_reader_fixture(cur, today)
        f = produced(cur, today, 'SOL-R5-GRAPH')
        o['produced_fixture'] = f
        o['literal_book_oracles'] = []
        inputs = expanded_inputs(cur, today, f['po'], f['product'])
        o['literal_book_oracles'].append(dict(phase='FG10', expected=['120','0','0'], observed=list(map(str,book(cur,f['po'])))))
        assert book(cur, f['po']) == (D(120), D(0), D(0))
        compare_graph(cur, inputs, o, 'PRODUCED10_BEFORE_OWN_SALE')
        sale = make_sale(cur, f)
        assert book(cur, f['po']) == (D(96), D(24), D(0))
        sale_life = lifecycle(cur, 'SALE', sale, f['po'], 24)
        o['literal_book_oracles'].append(dict(phase='SALE2', expected=['96','24','0'], observed=list(map(str,book(cur,f['po'])))))
        inputs = expanded_inputs(cur, today, f['po'], f['product'], [(sale_life['journal_id'],f['po'])])
        compare_graph(cur, inputs, o, 'SOLD2_LIFECYCLE_POSITIVE24')
        ret = make_return(cur, sale)
        assert book(cur, f['po']) == (D(108), D(12), D(0))
        ret_life = lifecycle(cur, 'SALES_RETURN', ret, f['po'], -12)
        o.update(sale_lifecycle=sale_life, return_lifecycle=ret_life)
        o['literal_book_oracles'].append(dict(phase='RETURN1', expected=['108','12','0'], observed=list(map(str,book(cur,f['po'])))))
        inputs = expanded_inputs(cur, today, f['po'], f['product'], [(sale_life['journal_id'],f['po']),(ret_life['journal_id'],f['po'])])
        compare_graph(cur, inputs, o, 'RETURNED1_LIFECYCLE_NEGATIVE12')
        o['all_nine_detector_outputs_after_lawful_chain'] = detector_rows(cur)
        assert len(counts(o['all_nine_detector_outputs_after_lawful_chain'])) == 167
        o.update(positive_nonzero_po_lifecycle_exercised=True, all11_graphs_compared_at_three_stages=True,
                 finite_input_scope_only=True, whole_application_equivalence_claim=False)

    def mapping_freshness(o):
        o['fixture_origin'] = 'ACCEPTED_NATIVE_PO10_HPP120_AND_NEW_UNUSED_ASSET_MASTER'
        f = produced(cur, today, 'SOL-R5-MAPPING')
        assert book(cur, f['po']) == (D(120), D(0), D(0))
        bd.api.admin(cur)
        original = cur.execute("select account_id::text from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'").fetchone()[0]
        expected_type = cur.execute("select erp.expected_mapping_account_type('FG_INVENTORY')").fetchone()[0]
        assert expected_type == 'ASSET'
        other = cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,normal_balance,is_postable,is_active) values(%s,%s,'ASSET','DEBIT',true,true) returning id::text", ('SR5FG'+uuid.uuid4().hex[:12], 'Uji Sol r5 akun persediaan kosong')).fetchone()[0]
        protected_before = protected.fingerprints(cur)
        inputs = expanded_inputs(cur, today, f['po'], f['product'])
        cur.execute('PREPARE sol_r5_book(uuid) AS SELECT to_jsonb(x) FROM erp.compute_po_hpp_gl_book_v2620e($1) x')
        def prepared(expected):
            bd.api.admin(cur)
            row = cur.execute(sql.SQL('EXECUTE sol_r5_book({})').format(sql.Literal(uuid.UUID(str(f['po']))))).fetchone()[0]
            assert D(str(row['fg_value'])) == D(expected), ('SOL_R5_PREPARED_MAPPING_STALE', row, expected)
            return row
        try:
            o['prepared_baseline'] = prepared(120)
            compare_graph(cur, inputs, o, 'ORIGINAL_FG_MAPPING')
            cur.execute('savepoint sol_r5_mapping')
            try:
                cur.execute("update erp.accounting_account_mappings set account_id=%s where mapping_key='FG_INVENTORY'", (other,))
                assert cur.execute("select erp.account_id('FG_INVENTORY')::text").fetchone()[0] == other
                o['prepared_changed_mapping'] = prepared(0)
                compare_graph(cur, inputs, o, 'LEGAL_FG_MAPPING_CHANGED_TO_EMPTY_ASSET')
                o['mapping_change_all_nine_detector_outputs'] = detector_rows(cur)
            finally:
                bd.api.admin(cur); cur.execute('rollback to savepoint sol_r5_mapping'); cur.execute('release savepoint sol_r5_mapping')
            assert cur.execute("select erp.account_id('FG_INVENTORY')::text").fetchone()[0] == original
            o['prepared_restored_mapping'] = prepared(120)
            compare_graph(cur, inputs, o, 'ORIGINAL_MAPPING_RESTORED')
        finally:
            bd.api.admin(cur); cur.execute('DEALLOCATE sol_r5_book')
        assert protected.fingerprints(cur) == protected_before
        refusals = []
        for label, statement in [('DELETE_CORE',"delete from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'"),
                                  ('RENAME_CORE',"update erp.accounting_account_mappings set mapping_key='SOL_R5_RENAMED_FG' where mapping_key='FG_INVENTORY'")]:
            cur.execute('savepoint sol_r5_core_mapping_refusal')
            observed = None
            try:
                cur.execute(statement)
            except psycopg.Error as e:
                observed = dict(sqlstate=e.sqlstate,message=str(e).split('\n')[0])
            finally:
                cur.execute('rollback to savepoint sol_r5_core_mapping_refusal'); cur.execute('release savepoint sol_r5_core_mapping_refusal'); bd.api.admin(cur)
            refusals.append(dict(action=label,observed=observed))
            assert observed and observed['sqlstate'] == 'P0001' and 'core' in observed['message'].lower(), ('SOL_R5_CORE_MAPPING_GUARD',refusals)
        o.update(refusals=refusals, prepared_query_values_120_0_120=True,
                 native_guards_active=True, protected_facts_unchanged=True,
                 mapping_change_is_configuration_comparison_not_healthy_book_or_UI_auth_claim=True)

    def reversed_repair(o):
        o['oracle_origin'] = 'SOL_VALID_REPAIR_6000_ALARM_ZERO_POST_REVERSE_REALLOCATE'
        o['fixture_origin'] = 'ACCEPTED_AX_REPAIR_QTY2_AND1_RATE2000_AND_PUBLIC_CP7_NOTA'
        o['phases'] = []
        def zero(label):
            rows = detector_rows(cur); values = counts(rows)
            o['phases'].append(dict(label=label,rows=rows))
            assert len(values)==167 and all(v==0 for v in values.values()), ('SOL_R5_VALID_REVERSED_ALARM',label,{k:v for k,v in values.items() if v})
        zero('BEFORE')
        f = sources.repair(cur,today,qty=2)
        sources.ax.post(cur,sources.ax.repair_payload(f,1));bd.api.admin(cur)
        zero('TWO_REPAIR_WAGES')
        posted = nota.act(cur,'POST',nota.command(cur,'SAVE',nota.payload(cur,f,today)));bd.api.admin(cur)
        first = posted['payroll_id']
        assert D(cur.execute('select net_payable from erp.payroll_settlements where id=%s',(first,)).fetchone()[0])==6000
        zero('VALID_NOTA_6000')
        fixed = protected.fingerprints(cur)
        bd.chain.production.owner(cur)
        cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(first,'Uji Sol r5, pembatalan nota yang belum dibayar'));bd.api.admin(cur)
        assert cur.execute('select status from erp.payroll_settlements where id=%s',(first,)).fetchone()[0]=='REVERSED'
        zero('REVERSED_NOTA')
        replacement = nota.act(cur,'POST',nota.command(cur,'SAVE',nota.payload(cur,f,today)));bd.api.admin(cur)
        assert replacement['payroll_id']!=first and D(cur.execute('select net_payable from erp.payroll_settlements where id=%s',(replacement['payroll_id'],)).fetchone()[0])==6000
        zero('REPLACEMENT_VALID_NOTA_6000')
        assert protected.fingerprints(cur)==fixed
        o.update(original_payroll_id=first,replacement_payroll_id=replacement['payroll_id'],
                 stock_HPP_journal_unchanged=True,all167_counts_zero_at_five_stages=True,
                 no_detector_guard_function_or_trigger_edited=True)

    return [record(IDS[0], full_graph), record(IDS[1], mapping_freshness), record(IDS[2], reversed_repair)]
