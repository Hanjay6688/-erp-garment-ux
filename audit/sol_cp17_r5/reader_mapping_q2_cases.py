"""Q2 audit-tool correction: supply required chart account report_group; oracles unchanged."""
from reader_graph_cases import (produced, book, bd, uuid, protected, expanded_inputs, sql, D, compare_graph, psycopg, record)

def mapping_freshness(cur, today, o):
    o['fixture_origin'] = 'ACCEPTED_NATIVE_PO10_HPP120_AND_NEW_UNUSED_ASSET_MASTER'
    f = produced(cur, today, 'SOL-R5-MAPPING')
    assert book(cur, f['po']) == (D(120), D(0), D(0))
    bd.api.admin(cur)
    original = cur.execute("select account_id::text from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'").fetchone()[0]
    expected_type = cur.execute("select erp.expected_mapping_account_type('FG_INVENTORY')").fetchone()[0]
    assert expected_type == 'ASSET'
    other = cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) select %s,%s,account_type,report_group,normal_balance,true,true from erp.chart_accounts where id=%s returning id::text", ('SR5FG'+uuid.uuid4().hex[:12], 'Uji Sol r5 akun persediaan kosong', original)).fetchone()[0]
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

def cases(cur,today):
    return [record('SOL_R5_READER_PREPARED_MAPPING_FRESHNESS_Q2',lambda o:mapping_freshness(cur,today,o))]
