"""Counted substitutions of three installed OW04 credit functions (OW-04b part 3).

Each retained refusal keeps its exact condition, position and message text; only `using detail=` is added, built by a
private reader of followups.sql from the same sub-conditions. Callers that compare the message (for example the qualified
race oracle CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED) see the same message. Nothing is admitted that was refused.
"""
BUILD='cp7_credit.build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)'
ENTER='cp7_credit.native_source_enter(text,uuid)'
BASE='cp7_credit.assert_simple_native_base_v1(uuid)'
SIGNATURES=(BUILD,ENTER,BASE)
REFUSALS={BUILD:'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',
          ENTER:'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION',
          BASE:'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED'}
DETAILS={BUILD:"cp7_credit_followups.initial_family_reasons_v1((p_legacy->>'sale_id')::uuid,src)",
         ENTER:'cp7_credit_followups.source_mutation_reasons_v1(p_action,sale)',
         BASE:'cp7_credit_followups.correction_reasons_v1(p_sale)'}
# The installed predecessor text these anchors belong to (fail closed if another composition is underneath):
# BUILD from coordinator/02_initial_projection.sql; ENTER from native-empty/04_exact_overlays.sql plus the payment
# correction entry hook; BASE from coordinator/05_factual_profile.sql after payment_correction/transform.py.
PREDECESSOR_MARKERS={
 BUILD:("  or exists(select 1 from cp7_sales_return_correction.links where sale_id=(p_legacy->>'sale_id')::uuid)then\n",),
 ENTER:(" if cp7_credit.payment_native_enter_v1(p_action,p_source)then return;end if;\n",
        " if cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_source_enter_v1(p_action,p_source);return;end if;\n"),
 BASE:(" perform cp7_credit.payment_link_source_check_v1(p_sale);\n",),
}


def anchor(sig):
    return "  raise exception '"+REFUSALS[sig]+"';end if;\n"


def replacement(sig):
    return "  raise exception '"+REFUSALS[sig]+"'using detail="+DETAILS[sig]+";end if;\n"


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW04B_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW04B_NATIVE_DELTA_SET_CHANGED')
    result={}
    for sig in SIGNATURES:
        body=originals[sig]
        if 'cp7_credit_followups' in body:raise ValueError('OW04B_ALREADY_PATCHED: '+sig)
        for marker in PREDECESSOR_MARKERS[sig]:
            if body.count(marker)!=1:raise ValueError('OW04B_PREDECESSOR_COMPOSITION_CHANGED: '+sig)
        # The refusal message occurs exactly once, in exactly the retained raise statement.
        if body.count("'"+REFUSALS[sig]+"'")!=1:raise ValueError('OW04B_REFUSAL_NOT_UNIQUE: '+sig)
        result[sig]=once(body,anchor(sig),replacement(sig),sig)
    return result
