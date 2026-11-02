"""Exact, reversible eight-function Native payment adapters; no SQL execution.

Inputs must be the actually reviewed Native catalog. These source adapters
are not an installer, an accepted final parent, or Native qualification.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
CHANGED=(
 'cp7_payroll.settlement_command(text,jsonb,uuid,text)',
 'cp7_installment.apply_command(text,jsonb,uuid,text)',
 'erp.post_payroll_payment(uuid)',
 'cp7_installment.final_payment(uuid,numeric)',
 'erp.reverse_paid_payroll(uuid,text)',
 'cp7_installment.reopen_settlement(uuid,text)',
 'erp.cancel_unpaid_payroll(uuid,text)',
 'erp._cp7_current_credit_adjustment(uuid)',
)
OTHER_BEFORE="""  select coalesce(sum(amount),0) into v_other_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type not in('MATERIAL_KASBON','CASH_ADVANCE');"""
OTHER_AFTER="""  select coalesce(sum(d.amount),0) into v_other_deduction
  from erp.payroll_deductions d where d.payroll_id=p.id and d.deduction_type not in('MATERIAL_KASBON','CASH_ADVANCE')
    and not exists(select 1 from cp7_mandor_shop.deduction_links fg where fg.deduction_id=d.id);"""
PAID="  update erp.payroll_settlements set status='PAID',settled_at=statement_timestamp(),updated_at=statement_timestamp() where id=p.id;"
REVERSED="  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=statement_timestamp() where id=p.id;"
REOPENED="  update erp.payroll_settlements set status='APPROVED',settled_at=null,updated_at=statement_timestamp() where id=p.id;"


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive(functions):
    reference=json.loads((HERE/'NATIVE_PAYMENT_OWNER_REFERENCE.json').read_bytes())
    if(reference['head']!='6e61506c10a18541c104b981bd438e78b175b5d1'
       or reference['functions_unchanged_in_actual_after_committed_E_use']is not True):
        raise ValueError('CP7_MANDOR_SHOP_ACTUAL_REVIEWED_NATIVE_PAYMENT_REFERENCE_REQUIRED')
    result={};proof={}
    for signature in CHANGED:
        row=functions.get(signature)
        if row!=reference['functions'][signature]:
            raise ValueError('CP7_MANDOR_SHOP_CURRENT_NATIVE_PAYMENT_SOURCE_REVIEW_REQUIRED:'+signature)
        raw=row[0].encode();text=raw.decode();routes=[]
        def change(before,after,count=1):
            nonlocal text
            if text.count(before)!=count or after in text:
                raise ValueError('CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_ROUTE_REQUIRED:'+signature)
            text=text.replace(before,after,count);routes.append(dict(before=before,after=after,count=count))
        if signature==CHANGED[0]:
            before=" insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),auth.uid(),(p_payload->>'id')::uuid,p_action);"
            change(before,before+"\n perform cp7_mandor_shop.payment_begin('PAYROLL',p_action,p_payload,p_request,p_expected);")
            before=' d:=cp7_payroll.apply_settlement(p_action,p_payload,p_expected);'
            change(before,before+"\n perform cp7_mandor_shop.payment_finish((p_payload->>'id')::uuid);")
        elif signature==CHANGED[1]:
            before=' insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),auth.uid(),ident,native_action);'
            change(before,before+"\n perform cp7_mandor_shop.payment_begin('INSTALLMENT',p_action,p,p_request,p_expected);")
            before=' delete from cp7_payroll.settlement_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();'
            change(before,' perform cp7_mandor_shop.payment_finish(ident);\n'+before)
        elif signature in CHANGED[2:4]:
            change(OTHER_BEFORE,OTHER_AFTER)
            change(PAID,PAID+'\n  perform cp7_mandor_shop.settle_payroll(p.id);')
        elif signature in(CHANGED[4],CHANGED[6]):
            change(REVERSED,REVERSED+'\n  perform cp7_mandor_shop.reverse_payroll_offsets(p.id,p_reason);')
        elif signature==CHANGED[5]:
            change(REOPENED,REOPENED+'\n  perform cp7_mandor_shop.reverse_payroll_offsets(p.id,p_reason);')
        else:
            before='declare h erp.sales_headers;m record;i numeric;u numeric;'
            change(before,before+'fg_ numeric;')
            before=' select *into strict h from erp.sales_headers where id=p_sale;'
            change(before,before+'\n fg_:=cp7_mandor_shop.invoice_offset_paid(p_sale);')
            change('return 0::numeric;','return fg_;',2)
            change('return cp7_credit.payment_intermediate_adjustment_v1(p_sale);',
                'return cp7_credit.payment_intermediate_adjustment_v1(p_sale)+fg_;')
            change('return u-i;','return u-i+fg_;')
        original=text
        for route in reversed(routes):
            if original.count(route['after'])!=route['count']:
                raise ValueError('CP7_MANDOR_SHOP_EXACT_NATIVE_PAYMENT_REVERSE_ROUTE_REQUIRED:'+signature)
            original=original.replace(route['after'],route['before'],route['count'])
        if original.encode()!=raw:raise ValueError('CP7_MANDOR_SHOP_ENTIRE_NATIVE_PAYMENT_BODY_NOT_RECOVERED:'+signature)
        result[signature]=text
        proof[signature]=dict(before=pin(raw),after=pin(text.encode()),routes=routes,
            original_owner_and_ACL=row[1:],complete_original_recovered=True)
    return result,dict(status='FG_MANDOR_EXACT_NATIVE_PAYMENT_ADAPTER_SOURCE_ONLY_NOT_APPLIED',
        changed_functions=proof,source_routes=sum(sum(r['count']for r in v['routes'])for v in proof.values()),
        original_cash_net_and_wage_expense_statements_unchanged=True,
        original_permission_idempotency_review_and_date_guards_unchanged=True,
        FG_excluded_from_OTHER_INCOME_in_both_payment_routes=True,
        same_authoritative_invoice_paid_projection_source_written=True,
        previous_DE_credit_semantics_and_all_return_branches_retained=True,
        final_parent_catalog_review_still_required=True,actual_Native_cases=0,actual_SQL_executed=0,
        runtime_activated=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    source=json.loads((HERE/'NATIVE_PAYMENT_OWNER_REFERENCE.json').read_bytes())
    _,proof=derive(source['functions'])
    print(json.dumps(proof))
