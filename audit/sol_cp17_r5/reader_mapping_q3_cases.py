"""Qualified sequencing: prepared lifetime excludes differential-graph rollback.

psycopg3.2.10 clears prepared state on ROLLBACK when its auto-prepare cache is
populated. Q2 mixed that helper rollback into the manual statement's lifetime.
All numerical/business oracles remain120/0/120 and full old/new graph equality.
"""
import json
import uuid
from decimal import Decimal as D
from psycopg import sql
import psycopg
import reader_graph_cases as g
from detector_case import detector_rows

ID='SOL_R5_READER_PREPARED_MAPPING_FRESHNESS_Q3'


def cases(cur,today):
    def qualified(o):
        bd=g.bd;bd.api.admin(cur)
        f=g.produced(cur,today,'SOL-R5-MAPPING-Q3')
        assert g.book(cur,f['po'])==(D(120),D(0),D(0))
        original=cur.execute("select account_id::text from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'").fetchone()[0]
        assert cur.execute("select erp.expected_mapping_account_type('FG_INVENTORY')").fetchone()[0]=='ASSET'
        other=cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) select %s,%s,account_type,report_group,normal_balance,true,true from erp.chart_accounts where id=%s returning id::text",('SR5FG'+uuid.uuid4().hex[:12],'Uji Sol r5 akun persediaan kosong',original)).fetchone()[0]
        protected_before=g.protected.fingerprints(cur)
        o.update(fixture_origin='ACCEPTED_NATIVE_PO10_HPP120_AND_UNUSED_VALID_ASSET_MASTER',
                 oracle_origin='UNCHANGED_SOL_120_0_120_PREPARED_QUERY_AND_ALL11_GRAPH_EQUALITY',
                 prepared_samples=[],prepared_lifetime_has_no_graph_swap_or_rollback=True,
                 trigger_or_privilege_changed=False)
        name='sol_r5_mapping_fresh'
        cur.execute('savepoint sol_r5_prepared_scope')
        try:
            cur.execute('PREPARE '+name+'(uuid) AS SELECT to_jsonb(x) FROM erp.compute_po_hpp_gl_book_v2620e($1) x')
            for label,account,expected in [('ORIGINAL',original,120),('NEW_EMPTY_ASSET',other,0),('RESTORED',original,120)]:
                bd.api.admin(cur)
                cur.execute("update erp.accounting_account_mappings set account_id=%s where mapping_key='FG_INVENTORY'",(account,))
                assert cur.execute("select erp.account_id('FG_INVENTORY')::text").fetchone()[0]==account
                prepared=cur.execute('select name,statement,parameter_types::text from pg_prepared_statements where name=%s',(name,)).fetchall()
                assert len(prepared)==1,'SOL_R5_MANUAL_PREPARED_STATEMENT_MISSING'
                row=cur.execute(sql.SQL('EXECUTE '+name+'({})').format(sql.Literal(uuid.UUID(str(f['po']))))).fetchone()[0]
                o['prepared_samples'].append(dict(label=label,mapping_account=account,expected_fg=str(expected),observed=row,actual_prepared_statement=prepared))
                assert tuple(D(str(row[k])) for k in ('fg_value','cogs_value','other_out_value'))==(D(expected),D(0),D(0)),('SOL_R5_PREPARED_MAPPING_FRESHNESS',label,row)
            cur.execute('DEALLOCATE '+name)
        finally:
            # Recover transaction first; session helpers cannot run in an aborted
            # transaction and must not mask the original error.
            cur.execute('rollback to savepoint sol_r5_prepared_scope');cur.execute('release savepoint sol_r5_prepared_scope');bd.api.admin(cur)
            if cur.execute('select exists(select 1 from pg_prepared_statements where name=%s)',(name,)).fetchone()[0]:cur.execute('DEALLOCATE '+name)
        assert not cur.execute('select exists(select 1 from pg_prepared_statements where name=%s)',(name,)).fetchone()[0]
        assert cur.execute("select erp.account_id('FG_INVENTORY')::text").fetchone()[0]==original
        assert g.protected.fingerprints(cur)==protected_before
        args=g.expanded_inputs(cur,today,f['po'],f['product'])
        g.compare_graph(cur,args,o,'ORIGINAL_MAPPING_AFTER_PREPARED_DEALLOCATED')
        cur.execute('savepoint sol_r5_q3_graph_mapping')
        try:
            cur.execute("update erp.accounting_account_mappings set account_id=%s where mapping_key='FG_INVENTORY'",(other,))
            g.compare_graph(cur,args,o,'LEGAL_EMPTY_ASSET_MAPPING_NO_MANUAL_PREPARE_ACTIVE')
            o['all_nine_detector_outputs_during_configuration_change']=detector_rows(cur)
        finally:
            cur.execute('rollback to savepoint sol_r5_q3_graph_mapping');cur.execute('release savepoint sol_r5_q3_graph_mapping');bd.api.admin(cur)
        g.compare_graph(cur,args,o,'ORIGINAL_MAPPING_RESTORED')
        o['refusals']=[]
        for label,statement,fragment in [
            ('DELETE_CORE',"delete from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'",'Core accounting mapping FG_INVENTORY tidak boleh dihapus'),
            ('RENAME_CORE',"update erp.accounting_account_mappings set mapping_key='SOL_R5_RENAMED_FG' where mapping_key='FG_INVENTORY'",'Core accounting mapping key FG_INVENTORY tidak boleh di-rename')]:
            cur.execute('savepoint sol_r5_q3_refusal');observed=None
            try:cur.execute(statement)
            except psycopg.Error as e:observed=dict(sqlstate=e.sqlstate,message=str(e).split('\n')[0])
            finally:cur.execute('rollback to savepoint sol_r5_q3_refusal');cur.execute('release savepoint sol_r5_q3_refusal');bd.api.admin(cur)
            o['refusals'].append(dict(action=label,observed=observed))
            assert observed and observed['sqlstate']=='P0001' and fragment in observed['message'],('SOL_R5_EXACT_CORE_MAPPING_REFUSAL',label,observed)
        assert g.protected.fingerprints(cur)==protected_before
        o.update(prepared_120_0_120=True,all11_graph_equal_in_three_configurations=True,
                 no_new_stock_HPP_journal=True,manual_prepared_statement_removed=True,
                 mapping_original_restored=True,native_guards_active=True,
                 configuration_comparison_not_a_healthy_book_or_UI_auth_claim=True)
    return [g.record(ID,qualified)]
