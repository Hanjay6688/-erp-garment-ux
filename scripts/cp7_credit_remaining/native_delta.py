"""Counted substitutions for OW-04b slice A over the installed cp7_credit_followups definitions.

native_source_enter: (1) an admitted incoming-credit payment sets the existing scope flag, so the retained before and
after proofs (simple Native base, zero excess on every date pair) run for it; (2) the retained refusal keeps its exact
condition for every other case: a cohort on the invoice always refuses, incoming APPLY refuses unless admitted.
source_request_enter_v1: (3) an admitted PAYMENT_REVERSE request opens no source operation, like a non-participating
invoice; the Native inverse then meets the hook above. Every refusal message and detail is unchanged.
"""
ENTER='cp7_credit.native_source_enter(text,uuid)'
REQUEST='cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)'
SIGNATURES=(ENTER,REQUEST)
ADMITTED='cp7_credit_remaining.payment_admitted_v1(p_action,p_source,sale)'
FAMILIES=' select exists(select 1 from cp7_credit.return_families where family_root_sale_id=sale)into families;\n'
APPLY_ENTER=("  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then\n"
             "  raise exception 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'"
             "using detail=cp7_credit_followups.source_mutation_reasons_v1(p_action,sale);end if;\n")
APPLY_REQUEST="  and not exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then return;end if;\n"
SUBSTITUTIONS={
    ENTER:((FAMILIES,
            ' select exists(select 1 from cp7_credit.return_families where family_root_sale_id=sale)\n'
            '  or '+ADMITTED+'into families;\n'),
           (APPLY_ENTER,
            APPLY_ENTER.replace('target_sale_id=sale)then\n','target_sale_id=sale)\n   and not '+ADMITTED+'then\n',1))),
    REQUEST:((APPLY_REQUEST,
              APPLY_REQUEST.replace('target_sale_id=sale)then return;','target_sale_id=sale)\n'
                                    '  or cp7_credit_remaining.request_admitted_v1(p_action,p_payload,sale)then return;',1)),),
}
# The installed predecessor these anchors belong to (fail closed if another composition is underneath).
PREDECESSOR_MARKERS={
    ENTER:(" if cp7_credit.payment_native_enter_v1(p_action,p_source)then return;end if;\n",
           " if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=sale)\n",
           " if families then perform cp7_credit.assert_simple_native_base_v1(sale);"
           "perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(sale));end if;\n",
           " insert into cp7_credit.source_mutation_scope values(pg_backend_pid(),txid_current(),auth.uid(),p_action,p_source,sale,a,families);\n"),
    REQUEST:(" if not exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale)\n",
             " perform cp7_credit.consumer_source_undone_v1(sale);",
             " if exists(select 1 from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then\n"),
}
REFUSALS={ENTER:("'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'",),
          REQUEST:("'CP7_CREDIT_SOURCE_SIMPLE_NATIVE_FAMILY_REQUIRED'","'CP7_CREDIT_SOURCE_ADVANCE_INVERSE_UNQUALIFIED'")}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW04BA_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW04BA_NATIVE_DELTA_SET_CHANGED')
    result={}
    for sig in SIGNATURES:
        body=originals[sig]
        if 'cp7_credit_remaining' in body:raise ValueError('OW04BA_ALREADY_PATCHED: '+sig)
        for marker in PREDECESSOR_MARKERS[sig]:
            if body.count(marker)!=1:raise ValueError('OW04BA_PREDECESSOR_COMPOSITION_CHANGED: '+sig+': '+marker[:60])
        counts={message:body.count(message)for message in REFUSALS[sig]}
        for old,new in SUBSTITUTIONS[sig]:body=once(body,old,new,sig)
        # No refusal text is added, removed or duplicated.
        if {message:body.count(message)for message in REFUSALS[sig]}!=counts:raise ValueError('OW04BA_REFUSAL_TEXT_CHANGED: '+sig)
        result[sig]=body
    return result
