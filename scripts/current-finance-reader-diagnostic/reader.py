"""Rollback-only experiment: retain opening-HPP arithmetic without its writer.

Not a product installer. The original posting resolver is never replaced.
The report-check call is redirected only in a disposable transaction and must
be restored by rollback before the complete catalog is verified again.
"""
from pathlib import Path
from hashlib import sha256

HERE=Path(__file__).resolve().parent
ORIGINAL='erp.resolve_opening_fg_unit_hpp(uuid,date)'
REPORT='erp.run_v268_financial_report_checks()'
PRIVATE='cp7_finance.read_opening_hpp_diagnostic_v1(uuid,date)'
BODY_SHA='d82bdae08187b2121b7a777e0b3973f292318b195a148762f3ba5998407bf48a'
OLD_CALL='erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date)'
NEW_CALL='cp7_finance.read_opening_hpp_diagnostic_v1(oi.id,oh.opening_date)'
REMOVALS=(
 ('where id=p_item_id for update;', 'where id=p_item_id;'),
 ('    update erp.opening_balance_items set reference_sell_price_snapshot=v_price,unit_cost_snapshot=v_hpp where id=i.id;\n',''),
 ('  update erp.opening_balance_items set reference_sell_price_snapshot=null where id=i.id;\n',''),
)

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('FINANCE_READER_DIAGNOSTIC_ANCHOR_CHANGED')
    return text.replace(old,new,1)

def readonly_body(original):
    expected=(HERE/'original-opening-hpp-body.sql').read_text()
    if sha256(expected.encode()).hexdigest()!=BODY_SHA:raise ValueError('FINANCE_READER_EXPECTED_BODY_CHANGED')
    if original!=expected:raise ValueError('FINANCE_READER_NATIVE_BODY_CHANGED')
    for old,new in REMOVALS:original=once(original,old,new)
    return original

def definition(original):
    return ("create function cp7_finance.read_opening_hpp_diagnostic_v1(p_item_id uuid,p_opening_date date) returns numeric\n"
        "language plpgsql stable security definer set search_path='' as $reader$"+
        readonly_body(original)+"$reader$;")

def report_definition(original):
    if not original.startswith('CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()\n'):
        raise ValueError('FINANCE_READER_REPORT_IDENTITY_CHANGED')
    if '\n STABLE SECURITY DEFINER\n'not in original:raise ValueError('FINANCE_READER_REPORT_AUTHORITY_CHANGED')
    return once(original,OLD_CALL,NEW_CALL)

def install_for_rollback(cur):
    """Caller owns one isolated transaction and unconditionally rolls it back."""
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    assert cur.execute('select to_regprocedure(%s)',(PRIVATE,)).fetchone()[0]is None
    row=cur.execute("select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),p.proconfig from pg_proc p where p.oid=%s::regprocedure",(ORIGINAL,)).fetchone()
    assert row[1:]==('v',True,'postgres',['search_path=erp, public']),row[1:]
    report=cur.execute('select pg_get_functiondef(%s::regprocedure)',(REPORT,)).fetchone()[0]
    replacement=report_definition(report)
    cur.execute(definition(row[0]),prepare=False)
    cur.execute('alter function '+PRIVATE+' owner to postgres')
    cur.execute('revoke all on function '+PRIVATE+' from public,anon,authenticated,service_role,cp7_capture,cp7_finance_read')
    cur.execute(replacement,prepare=False)
    for role in ('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,PRIVATE)).fetchone()[0],role
    installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(REPORT,)).fetchone()[0]
    assert installed==replacement
    assert cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(ORIGINAL,)).fetchone()[0]==row[0]
    return dict(original_resolver_unchanged=True,private_helper_not_callable_by_browser_or_worker=True,
        original_body_sha256=BODY_SHA,report_before_sha256=sha256(report.encode()).hexdigest(),
        report_after_sha256=sha256(replacement.encode()).hexdigest(),
        changed_report_call_count=1,removed_lock_count=1,removed_update_count=2,
        product_installed=False,production_go=False)
