"""SOURCE TRANSFORM ONLY: exact private Native initial-refund copy, no DB calls.

Production derivation requires installed pg_get_functiondef/prosrc AND exact
approved pg_proc metadata. A release-file footprint is explicitly static only.
The original Native poster and its ACL/definition are never replaced here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


DIRECTORY = Path(__file__).resolve().parent
LEDGER_TRANSFORM = DIRECTORY.parent / 'ledger' / '03_native_copy_transform.py'
# Loading the shared source must not write a cache outside this proposal folder.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('ow04_refund_native_predecessor', LEDGER_TRANSFORM)
if spec is None or spec.loader is None:
    raise RuntimeError('OW04_REFUND_EXACT_NATIVE_TRANSFORM_UNAVAILABLE')
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
TARGET = 'cp7_credit._post_initial_refund_bound(text,uuid,date,text,jsonb)'


def refund_body(body: str) -> str:
    changed = native.once(
        body, '  perform erp.require_internal();',
        '  perform cp7_credit.assert_initial_refund_bound_post(p_source_type,p_source_id,p_transaction_date,p_lines);\n'
        '  perform erp.require_internal();', 'refund private admission')
    changed = native.once(
        changed, '  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);',
        '  v_gl_date:=cp7_credit.initial_refund_bound_book_date(p_source_type,p_source_id,p_transaction_date,p_lines);',
        'refund source-derived book assignment')
    changed = native.once(
        changed,
        "jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)",
        "(jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)||cp7_credit.initial_refund_bound_audit())",
        'refund truthful derived-date audit')
    changed = native.once(
        changed, "'Late/backdated posting moved to open accounting period'",
        "'OW04 refund book date: lawful period and verified initial-credit source floor'", 'refund audit reason')
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
            raise ValueError('OW04_REFUND_NATIVE_STATEMENT_CHANGED: ' + anchor)
    return changed


def derive_initial_refund_post(captured, approved=None):
    approved = native.POST_APPROVED if approved is None else approved
    if approved != native.POST_APPROVED:
        raise ValueError('OW04_REFUND_UNAPPROVED_NATIVE_POSTER_BASE')
    native.assert_capture(captured, approved)
    definition = native.replace_body(captured, refund_body(captured.body))
    definition = native.once(definition, 'FUNCTION erp.post_journal(',
                             'FUNCTION cp7_credit._post_initial_refund_bound(', 'refund private header')
    receipt = native.manifest(captured, definition, TARGET)
    # A new private function has an independent ACL, never the Native service ACL.
    sql = (definition.rstrip().rstrip(';') + ';\n'
           f'alter function {TARGET} owner to postgres;\n'
           f'revoke all on function {TARGET} from public,anon,authenticated,service_role,'
           'cp7_capture,cp7_sales_read,cp7_sales_write;\n')
    receipt.update(derived_sql_sha256=native.digest(sql),
                   exact_installed_capture_required=True, original_Native_replaced=False)
    return sql, receipt


def static_check(repo: Path):
    release = repo / 'supabase/release/cp6-t3/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
    definition, body = native.extract_release_definition(release.read_text(), 'post_journal')
    changed = refund_body(body)
    controls = []
    for label, text in (
        ('duplicated_body', body + body),
        ('missing_admission', body.replace('  perform erp.require_internal();', '  -- removed admission')),
        ('changed_date_assignment', body.replace('v_gl_date:=erp.resolve_accounting_transaction_date', 'v_gl_date:=other_resolver')),
    ):
        try:
            refund_body(text)
        except ValueError:
            controls.append(dict(case=label, status='EXPECTED_REFUSAL'))
        else:
            raise AssertionError(('UNBOUND_NATIVE_TRANSFORM_ACCEPTED', label))
    # Raw release SQL MUST NOT masquerade as the approved installed capture.
    capture = native.Capture(native.POST_JOURNAL_IDENTITY, definition, body, native.POST_APPROVED.owner,
                             native.POST_APPROVED.acl, True, 'v', native.POST_APPROVED.config)
    try:
        derive_initial_refund_post(capture)
    except ValueError:
        controls.append(dict(case='raw_release_is_not_installed_capture', status='EXPECTED_REFUSAL'))
    else:
        raise AssertionError('RELEASE_FILE_MISCLASSIFIED_AS_INSTALLED_NATIVE_CAPTURE')
    return dict(scope='STATIC_RELEASE_TRANSFORM_ONLY_NOT_NATIVE', status='PASS', native_execution_proven=False,
                exact_installed_capture_obtained=False, original_Native_replaced=False,
                source=str(release), approved_installed_definition_sha256=native.POST_JOURNAL_APPROVED_SHA256,
                raw_release_definition_sha256=native.digest(definition), raw_release_body_sha256=native.digest(body),
                transformed_body_sha256=native.digest(changed), controls=controls,
                retained=['Native require_internal', 'cent/balance/source guards', 'period SHARE', 'AP admission',
                          'actual journal/line INSERTs', 'unchanged journal-line cash trigger', 'account_daily_balances'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-check', required=True, type=Path)
    parser.add_argument('--result', type=Path, default=DIRECTORY / 'STATIC_TRANSFORM_RESULT.json')
    args = parser.parse_args()
    result = static_check(args.static_check.resolve())
    args.result.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
