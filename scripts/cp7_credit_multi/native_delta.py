"""Counted substitutions for OW-04b slice B steps 2-3 (docs/cp7/d17-14/ow04/OW04B_SLICE_B_INVENTORY.md B1-B9, B11, B12).

Every substitution is an exact anchor found once in the installed (captured) definition. With no earlier family that
has a cohort, every replaced expression evaluates to exactly the retained value: prior_recognized_v1 is 0 and
assert_prior_families_reconciled_v1 is assert_zero_excess_v1, and the per-cohort profile loop (B9) runs its one cohort
through the retained proofs with the retained values.
"""
BUILD='cp7_credit.build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)'
GUARD='cp7_credit.native_return_guard(uuid,numeric,numeric,numeric)'
ADMISSION='cp7_credit.assert_source_admission(uuid)'
COMPLETE='cp7_credit.native_return_complete(uuid,numeric,numeric)'
REASONS='cp7_credit_followups.initial_family_reasons_v1(uuid,jsonb)'
PROFILE='cp7_credit._consumer_root_source_profile_v1(uuid,uuid,uuid,jsonb)'
OPENING='cp7_credit.opening_return_hpp_owner_v1(uuid)'
SIGNATURES=(BUILD,GUARD,ADMISSION,COMPLETE,REASONS,PROFILE,OPENING)
PRIOR="cp7_credit_multi.prior_recognized_v1(h.id)"
ORDINAL="(select f.family_ordinal from cp7_credit.return_families f where f.id=ch.family_id)"
RECOGNIZED=("(select coalesce(sum(rp.net_amount),0)from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id"
            " join cp7_credit.recognition_plans rp on rp.id=c.initial_plan_id where f.family_root_sale_id=p_sale)")
CAPACITY=" if not(capacity->>'source_prefixes_nonnegative')::boolean then raise exception 'CP7_CREDIT_CURRENT_JOINT_CAPACITY_NEGATIVE';end if;\n"
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
    # B9: the single-cohort profile becomes a loop over every cohort in family order. Each cohort keeps every retained
    # per-cohort proof, with its before-events and preserved source taken as at its own settlement (family prefix);
    # with one cohort they are the retained values. Invoice level, after the loop: the actual I and the whole excess F
    # equal the total recognized credit.
    PROFILE:(
        ('B9a'," elsif n<>1 then raise exception 'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED';end if;\n"
               " select c.*into strict ch from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_sale;\n",
               " end if;\n"
               " for ch in select c.*from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id"
               " where f.family_root_sale_id=p_sale order by f.family_ordinal,c.id loop\n"),
        ('B9b',"  or cp7_credit.initial_preserved_source_v1(p_sale,ch.source_return_id)is distinct from m.source_snapshot->'preserved_source'\n"
               "  or cp7_credit.initial_base_events_v1(p_sale,ch.source_return_id)is distinct from p.before_events then\n",
               "  or cp7_credit_multi.family_preserved_source_v1(p_sale,"+ORDINAL+")is distinct from m.source_snapshot->'preserved_source'\n"
               "  or cp7_credit_multi.family_before_events_v1(p_sale,"+ORDINAL+")is distinct from p.before_events then\n"),
        ('B9c'," perform cp7_credit.assert_zero_excess_v1(p.before_events);\n",
               " perform cp7_credit_multi.assert_prior_families_reconciled_v1(p_sale,p.before_events,ch.source_return_id);\n"),
        ('B9d'," if actual_i is distinct from fresh->'components'or(p_actual->>'I')::numeric<>p.net_amount or(p_actual->>'U')::numeric<>0 then\n",
               " if actual_i is distinct from fresh->'components'or(n=1 and(p_actual->>'I')::numeric<>p.net_amount)or(p_actual->>'U')::numeric<>0 then\n"),
        ('B9e',CAPACITY,
               CAPACITY+" end loop;\n"
               " if n>1 and((p_actual->>'I')::numeric<>"+RECOGNIZED+"\n"
               "  or(ow04_pure_kernel.recognition_plan_v1('[]',events)->>'net_current_k')::numeric<>"+RECOGNIZED+")then\n"
               "  raise exception 'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED';end if;\n")),
    # B12 (first CI run 39889035001, b005aafe): the opening-HPP return owner re-derives the guard's effective paid as
    # raw_paid - K. B6 made the guard subtract the earlier families' credit too, so the owner must expect the same
    # value; the guard runs before this return's family is registered, so every registered family is earlier.
    OPENING:(
        ('B12',"   or n.guard_effective_paid is distinct from((w.projection->>'raw_paid')::numeric-\n"
               "    case when w.origin='REVIEWED_SETTLEMENT'then(w.projected_kernel->>'net_current_k')::numeric else 0 end)then\n",
               "   or n.guard_effective_paid is distinct from((w.projection->>'raw_paid')::numeric-\n"
               "    case when w.origin='REVIEWED_SETTLEMENT'then cp7_credit_multi.prior_recognized_v1(w.source_sale_id)"
               "+(w.projected_kernel->>'net_current_k')::numeric else 0 end)then\n"),),
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
    PROFILE:(" -- Every consumer has its actual immutable operation and exact named inverse.\n",
             "if(p_actual->>'I')::numeric<>0 then",
             " select *into strict m from cp7_credit.initial_return_materializations where cohort_id=ch.id and plan_id=p.id;\n"),
    OPENING:(" if to_regclass('cp7_credit.native_empty_work')is not null then\n",
             "  select *into strict n from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();\n"),
}
REFUSALS=("'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'","'CP7_CREDIT_CORRUPT_BEFORE_AR_OR_RETURN'","'CP7_CREDIT_INITIAL_K_OUTSIDE_RETURN_SCOPE'",
          "'CP7_CREDIT_NATIVE_RETURN_TOTALS_CHANGED'","'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED'","'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID'",
          "'CP7_CREDIT_ACTUAL_EFFECTIVE_PAID_INVALID'","'CP7_CREDIT_NATIVE_COMPLETION_TOTALS_CHANGED'",
          "'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED'","'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED'",
          "'CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED'","'CP7_CREDIT_CURRENT_SOURCE_TARGET_CHANGED'",
          "'CP7_CREDIT_CURRENT_JOINT_CAPACITY_NEGATIVE'","'CP7_CREDIT_EMPTY_FAMILY_HAS_FINANCIAL_EFFECT'",
          "'CP7_CREDIT_CURRENT_ORDINAL_RECONCILIATION_REQUIRED'","'CP7_CREDIT_CURRENT_SOURCE_ROUTE_UNIMPLEMENTED'",
          "'CP7_CREDIT_OPENING_HPP_GUARDED_OWNER_REQUIRED'","'CP7_CREDIT_OPENING_HPP_NATIVE_EMPTY_GUARDED_OWNER_REQUIRED'")
# The only declared refusal-text changes: B9 removes the one-cohort refusal and adds the invoice-level check.
REFUSAL_DELTA={PROFILE:{"'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED'":-1,"'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED'":1}}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW04BB_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patch(sig,body):
    if 'cp7_credit_multi' in body:raise ValueError('OW04BB_ALREADY_PATCHED: '+sig)
    for marker in PREDECESSOR_MARKERS[sig]:
        if body.count(marker)!=1:raise ValueError('OW04BB_PREDECESSOR_COMPOSITION_CHANGED: '+sig+': '+marker[:60])
    counts={message:body.count(message)for message in REFUSALS}
    for label,old,new in SUBSTITUTIONS[sig]:body=once(body,old,new,sig+' '+label)
    expected={message:count+REFUSAL_DELTA.get(sig,{}).get(message,0)for message,count in counts.items()}
    if {message:body.count(message)for message in REFUSALS}!=expected:raise ValueError('OW04BB_REFUSAL_TEXT_CHANGED: '+sig)
    return body


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW04BB_NATIVE_DELTA_SET_CHANGED')
    return {sig:patch(sig,originals[sig])for sig in SIGNATURES}
