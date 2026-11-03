"""Five exact Native guard insertions over complete actual function rows.

The payroll body already has its original reversible payment adapter. Four
other Native bodies gain one guard each. No Native permissions, payload,
idempotency, money, stock, dates, or response statements are removed.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
REFERENCE='COMMAND_GUARD_NATIVE_REFERENCE.json'
PAYROLL='cp7_payroll.settlement_command(text,jsonb,uuid,text)'
ROUTES={
 PAYROLL:(" if old.response is not null then return old.response;end if;",
  " perform cp7_mandor_shop.payroll_current_access('PAYROLL',p_action,(p_payload->>'id')::uuid);",'BEFORE'),
 'cp7_installment.command(text,jsonb,uuid,text)':(" if old.response is not null then return old.response;end if;",
  " perform cp7_mandor_shop.payroll_current_access('INSTALLMENT',p_action,(p->>'payroll_id')::uuid);",'BEFORE'),
 'cp7_sales.command(text,jsonb,uuid,text)':(" if old.response is not null then return old.response;end if;",
  " perform cp7_mandor_shop.sale_change_preflight(p_action,(p_payload->>'sale_id')::uuid);",'AFTER'),
 'cp7_note.command(jsonb,uuid,text)':(" if old.response is not null then return old.response;end if;",
  " perform cp7_mandor_shop.sale_change_preflight('CORRECT',(p_payload->>'sale_id')::uuid);",'AFTER'),
 'cp7_credit_note_carry_de.command_v1(jsonb,uuid,text)':(" if old.response is not null then return old.response;end if;",
  " perform cp7_mandor_shop.sale_change_preflight('CORRECT',(p_payload->>'sale_id')::uuid);",'AFTER'),
}


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive(functions,payment_definitions):
    from . import native_payment_routes
    reference=json.loads((HERE/REFERENCE).read_bytes())
    if(reference['source_raw25']!=dict(bytes=14755737,sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')
       or set(reference['functions'])!=set(ROUTES)):
        raise ValueError('MANDOR_GUARD_COMPLETE_ACTUAL_NATIVE_REFERENCE_REQUIRED')
    original_payment,_=native_payment_routes.derive(functions)
    if payment_definitions!=original_payment:raise ValueError('MANDOR_GUARD_EXACT_PRIOR_PAYMENT_DERIVATION')
    result={};proof={}
    for signature,(anchor,line,position)in ROUTES.items():
        row=functions.get(signature)
        if row!=reference['functions'][signature]:raise ValueError('MANDOR_GUARD_CURRENT_NATIVE_SOURCE_REVIEW_REQUIRED:'+signature)
        prior=payment_definitions[signature]if signature==PAYROLL else row[0]
        insertion=line+'\n'+anchor if position=='BEFORE'else anchor+'\n'+line
        if prior.count(anchor)!=1 or line in prior:raise ValueError('MANDOR_GUARD_ONE_EXACT_INSERTION:'+signature)
        after=prior.replace(anchor,insertion,1)
        if after.count(insertion)!=1 or after.replace(insertion,anchor,1)!=prior:
            raise ValueError('MANDOR_GUARD_COMPLETE_PRIOR_BODY_NOT_RECOVERED:'+signature)
        result[signature]=after
        proof[signature]=dict(before=pin(prior.encode()),after=pin(after.encode()),anchor=anchor,insertion=line,
            position=position,complete_prior_body_recovered=True,original_owner_and_ACL=row[1:])
    return result,dict(status='MANDOR_PREWRITE_AND_CACHED_REPLAY_GUARDS_SOURCE_ONLY',routes=proof,
        new_Native_function_identities=4,existing_payment_adapter_extended=1,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)
