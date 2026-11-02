"""One reversible store-picker filter; no Native command or financial rewrite."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
SIGNATURE='cp7_sales.form_options(jsonb)'
BEFORE="select id,customer_code,customer_name from erp.customers where is_active and(q=''"
AFTER="select id,customer_code,customer_name from erp.customers where is_active and not cp7_mandor_shop.is_mandor_customer(id) and(q=''"


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive(functions):
    reference=json.loads((HERE/'NATIVE_SALES_COMMAND_REFERENCE.json').read_bytes())
    if reference['functions_unchanged_in_actual_after_committed_E_use']is not True:
        raise ValueError('CP7_MANDOR_SHOP_REVIEWED_NATIVE_SALES_REFERENCE_REQUIRED')
    actual=functions.get(SIGNATURE)
    if actual!=reference['functions'][SIGNATURE]:
        raise ValueError('CP7_MANDOR_SHOP_CURRENT_NATIVE_FORM_SOURCE_REVIEW_REQUIRED')
    raw=actual[0].encode();text=raw.decode()
    if text.count(BEFORE)!=1 or AFTER in text:raise ValueError('CP7_MANDOR_SHOP_EXACT_NATIVE_CUSTOMER_ELIGIBLE_ROUTE_REQUIRED')
    derived=text.replace(BEFORE,AFTER,1)
    if derived.count(AFTER)!=1 or derived.replace(AFTER,BEFORE,1).encode()!=raw:
        raise ValueError('CP7_MANDOR_SHOP_ENTIRE_NATIVE_FORM_SOURCE_NOT_RECOVERED')
    return {SIGNATURE:derived},dict(status='FG_MANDOR_NATIVE_STORE_PICKER_ONE_SOURCE_ROUTE_NOT_APPLIED',
        before=pin(raw),after=pin(derived.encode()),route=dict(before=BEFORE,after=AFTER,count=1),
        unchanged_owner_and_ACL=actual[1:],complete_original_recovered=True,
        same_materialized_eligible_for_rows_and_total=True,stock_form_branch_unchanged=True,
        Native_command_and_financial_function_bodies_changed=0,final_parent_review_still_required=True,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    reference=json.loads((HERE/'NATIVE_SALES_COMMAND_REFERENCE.json').read_bytes())
    _,proof=derive(reference['functions']);print(json.dumps(proof))
