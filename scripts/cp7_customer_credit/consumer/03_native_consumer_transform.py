"""Exact private Native consumer-poster derivation; no DB calls or installation.

The complete owning consumer bundle must supply all three operation-bound
callbacks before using the SQL. Original Native require_internal, financial
guards and writes remain. This module does not create a caller context, grant
a Native bypass, implement a consumer command or prove runtime execution.
"""
from pathlib import Path
import importlib.util
import sys

sys.dont_write_bytecode = True
DIRECTORY = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ow04_consumer_exact_native_base',
    DIRECTORY.parent / 'ledger/03_native_copy_transform.py')
if spec is None or spec.loader is None:
    raise RuntimeError('OW04_CONSUMER_NATIVE_TRANSFORM_UNAVAILABLE')
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
TARGET = 'cp7_credit._post_consumer_bound_v1(text,uuid,date,text,jsonb)'


def consumer_body(body):
    changed = native.once(body, '  perform erp.require_internal();',
        '  perform cp7_credit.assert_consumer_bound_post_v1(p_source_type,p_source_id,p_transaction_date,p_lines);\n'
        '  perform erp.require_internal();', 'consumer exact posting admission')
    changed = native.once(changed,
        '  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);',
        '  v_gl_date:=cp7_credit.consumer_bound_book_date_v1(p_source_type,p_source_id,p_transaction_date,p_lines);',
        'consumer exact operation-derived book assignment')
    changed = native.once(changed,
        "jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)",
        "(jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)||cp7_credit.consumer_bound_audit_v1())",
        'consumer source-bound date audit')
    changed = native.once(changed,
        "'Late/backdated posting moved to open accounting period'",
        "'Pembukuan pemakaian atau pembatalan kredit mengikuti tanggal sumber dan periode yang sah'",
        'consumer factual date audit reason')
    for anchor in (
        '  perform erp.require_internal();',
        '    v_cent_lines:=v_cent_lines||jsonb_build_array(r||jsonb_build_object(',
        '  if v_debit<>v_credit or v_debit<=0 then',
        "  if exists(select 1 from erp.journal_entries where source_type=p_source_type and source_id=p_source_id and status='POSTED') then",
        '  perform 1 from erp.accounting_period_control where singleton_id=1 for share;',
        "  v_ap_vendor_account:=erp.account_id('AP_VENDOR');",
        '  insert into erp.journal_entries(', '    insert into erp.journal_lines(',
        '  insert into erp.account_daily_balances(',
    ):
        if not body.count(anchor) or body.count(anchor) != changed.count(anchor):
            raise ValueError('OW04_CONSUMER_NATIVE_STATEMENT_CHANGED: ' + anchor)
    return changed


def derive_consumer_post(captured, approved=None):
    approved = native.POST_APPROVED if approved is None else approved
    if approved != native.POST_APPROVED:
        raise ValueError('OW04_CONSUMER_UNAPPROVED_NATIVE_POSTER')
    native.assert_capture(captured, approved)
    definition = native.replace_body(captured, consumer_body(captured.body))
    definition = native.once(definition, 'FUNCTION erp.post_journal(',
        'FUNCTION cp7_credit._post_consumer_bound_v1(', 'consumer private posting header')
    sql = definition.rstrip().rstrip(';') + ';\n'
    sql += 'alter function ' + TARGET + ' owner to postgres;\n'
    sql += ('revoke all on function ' + TARGET + ' from public,anon,authenticated,service_role,'
            'cp7_capture,cp7_sales_read,cp7_sales_write;\n')
    receipt = native.manifest(captured, definition, TARGET)
    receipt.update(derived_sql_sha256=native.digest(sql),
        exact_installed_capture_required=True, original_Native_replaced=False,
        original_Native_require_internal_retained=True,
        complete_owning_consumer_callbacks_required=True,
        financial_command_implemented=False, native_execution_proven=False)
    return sql, receipt
