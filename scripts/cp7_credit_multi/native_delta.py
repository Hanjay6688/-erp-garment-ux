"""Counted substitutions for OW-04b slice B step 2 (docs/cp7/d17-14/ow04/OW04B_SLICE_B_INVENTORY.md B1-B8, B11).

Every substitution is an exact anchor found once in the installed (captured) definition. With no earlier family that
has a cohort, every replaced expression evaluates to exactly the retained value: prior_recognized_v1 is 0 and
assert_prior_families_reconciled_v1 is assert_zero_excess_v1. The per-cohort profile (B9) is a later step; until it
lands a second return is still refused by the retained profile at completion, so nothing new can be committed.
"""
BUILD='cp7_credit.build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)'
GUARD='cp7_credit.native_return_guard(uuid,numeric,numeric,numeric)'
ADMISSION='cp7_credit.assert_source_admission(uuid)'
COMPLETE='cp7_credit.native_return_complete(uuid,numeric,numeric)'
REASONS='cp7_credit_followups.initial_family_reasons_v1(uuid,jsonb)'
SIGNATURES=(BUILD,GUARD,ADMISSION,COMPLETE,REASONS)
PRIOR="cp7_credit_multi.prior_recognized_v1(h.id)"
SUBSTITUTIONS={
    BUILD:(
        ('B1',"\n  or exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id"
              " where f.family_root_sale_id=(p_legacy->>'sale_id')::uuid)",''),
        ('B2'," perform cp7_credit.assert_zero_excess_v1(before_events);\n",
              " perform cp7_credit_multi.assert_prior_families_reconciled_v1(h.id,before_events,p_own_return);\n"),
        ('B3',"if gross<0 or net<0 or paid<0 or paid>net or amount<0 or after_net<0 then",
              "if gross<0 or net<0 or paid<0 or paid-"+PRIOR+">net or amount<0 or after_net<0 then"),
        ('B4',"if issued<0 or issued>amount or paid-issued>after_net or paid-issued<0 then",
              "if issued<0 or issued>amount or paid-"+PRIOR+"-issued>after_net or paid-"+PRIOR+"-issued<0 then"),
        ('B5a',"'credit_applied','0.00','credit_recognized','0.00','effective_paid',cp7_credit.cent_text(paid),"
               "'receivable_remaining',cp7_credit.cent_text(net-paid));",
               "'credit_applied','0.00','credit_recognized',cp7_credit.cent_text("+PRIOR+"),'effective_paid',cp7_credit.cent_text(paid-"+PRIOR+"),"
               "'receivable_remaining',cp7_credit.cent_text(net-paid+"+PRIOR+"));"),
        ('B5b',"'credit_recognized',cp7_credit.cent_text(issued),'effective_paid',cp7_credit.cent_text(paid-issued),"
               "'receivable_remaining',cp7_credit.cent_text(after_net-paid+issued));",
               "'credit_recognized',cp7_credit.cent_text("+PRIOR+"+issued),'effective_paid',cp7_credit.cent_text(paid-"+PRIOR+"-issued),"
               "'receivable_remaining',cp7_credit.cent_text(after_net-paid+"+PRIOR+"+issued));")),
    GUARD:(
        ('B6',"  v:=p_raw_paid-(w.projected_kernel->>'net_current_k')::numeric;\n",
              "  v:=p_raw_paid-cp7_credit_multi.prior_recognized_v1(w.source_sale_id)-(w.projected_kernel->>'net_current_k')::numeric;\n"),),
    ADMISSION:(
        ('B7a'," perform cp7_credit.assert_zero_excess_v1(p.before_events);\n",
               " perform cp7_credit_multi.assert_prior_families_reconciled_v1(w.source_sale_id,p.before_events,w.return_id);\n"),
        ('B7b',"   where f.family_root_sale_id=w.source_sale_id and other.id<>p.cohort_id)then raise exception 'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID';end if;",
               "   where f.family_root_sale_id=w.source_sale_id and other.id<>p.cohort_id\n"
               "    and(w.family_ordinal is null or f.family_ordinal>=w.family_ordinal))then raise exception 'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID';end if;")),
    COMPLETE:(
        ('B8'," result:=(w.projection->>'raw_paid')::numeric-full_k;\n",
              " result:=(w.projection->>'raw_paid')::numeric-cp7_credit_multi.prior_recognized_v1(w.source_sale_id,w.family_ordinal)-full_k;\n"),),
    REASONS:(
        ('B11'," if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=p_sale)then\n"
               "  reasons:=reasons||jsonb_build_array('PRIOR_CREDIT_RETURN');end if;\n",''),),
}
# The installed predecessor these anchors belong to (fail closed if another composition is underneath).
PREDECESSOR_MARKERS={
    BUILD:("using detail=cp7_credit_followups.initial_family_reasons_v1((p_legacy->>'sale_id')::uuid,src);end if;\n",
           " before_events:=cp7_credit.initial_base_events_v1(h.id);\n"),
    GUARD:(" if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_guard_v1(",),
    ADMISSION:(" select *into strict w from cp7_credit.initial_return_work where plan_id=p_plan;\n",),
    COMPLETE:(" if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_complete_v1(",
              " perform cp7_credit.store_initial_plan_v1(w.operation_id);\n"),
    REASONS:("  reasons:=reasons||jsonb_build_array('CREDIT_APPLIED_TO_INVOICE');end if;\n",),
}
REFUSALS=("'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'","'CP7_CREDIT_CORRUPT_BEFORE_AR_OR_RETURN'","'CP7_CREDIT_INITIAL_K_OUTSIDE_RETURN_SCOPE'",
          "'CP7_CREDIT_NATIVE_RETURN_TOTALS_CHANGED'","'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED'","'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID'",
          "'CP7_CREDIT_ACTUAL_EFFECTIVE_PAID_INVALID'","'CP7_CREDIT_NATIVE_COMPLETION_TOTALS_CHANGED'")


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW04BB_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW04BB_NATIVE_DELTA_SET_CHANGED')
    result={}
    for sig in SIGNATURES:
        body=originals[sig]
        if 'cp7_credit_multi' in body:raise ValueError('OW04BB_ALREADY_PATCHED: '+sig)
        for marker in PREDECESSOR_MARKERS[sig]:
            if body.count(marker)!=1:raise ValueError('OW04BB_PREDECESSOR_COMPOSITION_CHANGED: '+sig+': '+marker[:60])
        counts={message:body.count(message)for message in REFUSALS}
        for label,old,new in SUBSTITUTIONS[sig]:body=once(body,old,new,sig+' '+label)
        if {message:body.count(message)for message in REFUSALS}!=counts:raise ValueError('OW04BB_REFUSAL_TEXT_CHANGED: '+sig)
        result[sig]=body
    return result
