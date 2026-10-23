"""Counted substitutions for OW-04b slice C step 2 (docs/cp7/d17-14/ow04/OW04B_SLICE_C_INVENTORY.md C1-C7, C12).

Applied to the installed slice B definitions (cp7_credit_multi). Every anchor is found once. U is
cp7_credit_incoming.incoming_applied_v1, the credit applied to the invoice (incoming.sql); with U = 0 every replaced
expression evaluates to exactly slice B's value. C8 (the native-empty direct route) is deliberately not touched.
"""
from cp7_credit_multi import native_delta as b

BUILD,GUARD,ADMISSION,COMPLETE,REASONS,PROFILE,OPENING=b.BUILD,b.GUARD,b.ADMISSION,b.COMPLETE,b.REASONS,b.PROFILE,b.OPENING
SIGNATURES=(BUILD,GUARD,ADMISSION,COMPLETE,REASONS,PROFILE,OPENING)
PRIOR=b.PRIOR
U_SALE="cp7_credit_incoming.incoming_applied_v1(h.id)"
U_WORK="cp7_credit_incoming.incoming_applied_v1(w.source_sale_id)"
SUBSTITUTIONS={
    BUILD:(
        ('C1',"\n  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=(p_legacy->>'sale_id')::uuid)",''),
        ('C2a',"paid-"+PRIOR+">net","paid+"+U_SALE+"-"+PRIOR+">net"),
        ('C2b',"paid-"+PRIOR+"-issued>after_net or paid-"+PRIOR+"-issued<0 then",
               "paid+"+U_SALE+"-"+PRIOR+"-issued>after_net or paid+"+U_SALE+"-"+PRIOR+"-issued<0 then"),
        ('C2c',"'credit_applied','0.00','credit_recognized',cp7_credit.cent_text("+PRIOR+"),'effective_paid',cp7_credit.cent_text(paid-"+PRIOR+"),"
               "'receivable_remaining',cp7_credit.cent_text(net-paid+"+PRIOR+"));",
               "'credit_applied',cp7_credit.cent_text("+U_SALE+"),'credit_recognized',cp7_credit.cent_text("+PRIOR+"),"
               "'effective_paid',cp7_credit.cent_text(paid+"+U_SALE+"-"+PRIOR+"),"
               "'receivable_remaining',cp7_credit.cent_text(net-paid-"+U_SALE+"+"+PRIOR+"));"),
        ('C2d',"'effective_paid',cp7_credit.cent_text(paid-"+PRIOR+"-issued),'receivable_remaining',cp7_credit.cent_text(after_net-paid+"+PRIOR+"+issued));",
               "'effective_paid',cp7_credit.cent_text(paid+"+U_SALE+"-"+PRIOR+"-issued),"
               "'receivable_remaining',cp7_credit.cent_text(after_net-paid-"+U_SALE+"+"+PRIOR+"+issued));")),
    GUARD:(
        # C3b: an ordinary return (no settlement choice). P > net_after keeps the retained Native paid exception (P11)
        # exactly; an overfunding with U is refused by the retained recognition-review refusal (the kernel includes U);
        # otherwise the effective paid Native sees is P + U.
        ('C3b',"  if(w.projected_kernel->>'has_recognition_effect')::boolean then raise exception 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;\n"
               "  v:=p_raw_paid;\n",
               "  if(w.projected_kernel->>'has_recognition_effect')::boolean then raise exception 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;\n"
               "  v:=p_raw_paid+"+U_WORK+";\n"),
        ('C3',"  v:=p_raw_paid-cp7_credit_multi.prior_recognized_v1(w.source_sale_id)-",
              "  v:=p_raw_paid+"+U_WORK+"-cp7_credit_multi.prior_recognized_v1(w.source_sale_id)-")),
    ADMISSION:(
        ('C5',"  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=w.source_sale_id)\n",''),),
    COMPLETE:(
        ('C4'," result:=(w.projection->>'raw_paid')::numeric-cp7_credit_multi.prior_recognized_v1(w.source_sale_id,w.family_ordinal)-full_k;\n",
              " result:=(w.projection->>'raw_paid')::numeric+"+U_WORK+"-cp7_credit_multi.prior_recognized_v1(w.source_sale_id,w.family_ordinal)-full_k;\n"),),
    REASONS:(
        ('C7'," if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then\n"
              "  reasons:=reasons||jsonb_build_array('CREDIT_APPLIED_TO_INVOICE');end if;\n",''),),
    PROFILE:(
        ('C6',"or(p_actual->>'U')::numeric<>0 then\n","or(p_actual->>'U')::numeric<>cp7_credit_incoming.incoming_applied_v1(p_sale)then\n"),),
    OPENING:(
        # C12: the opening-HPP owner expects exactly the guard's value, now including U (as B12 did for earlier credit).
        ('C12',"   or n.guard_effective_paid is distinct from((w.projection->>'raw_paid')::numeric-\n",
               "   or n.guard_effective_paid is distinct from((w.projection->>'raw_paid')::numeric+"+U_WORK+"-\n"),),
}
# Slice B text this delta must find (fail closed if slice B is not exactly underneath).
PREDECESSOR_MARKERS={
    BUILD:(" perform cp7_credit_multi.assert_prior_families_reconciled_v1(h.id,before_events,p_own_return);\n",),
    GUARD:("cp7_credit_multi.prior_recognized_v1(w.source_sale_id)",),
    ADMISSION:(" perform cp7_credit_multi.assert_prior_families_reconciled_v1(w.source_sale_id,p.before_events,w.return_id);\n",),
    COMPLETE:("cp7_credit_multi.prior_recognized_v1(w.source_sale_id,w.family_ordinal)",),
    REASONS:("  reasons:=reasons||jsonb_build_array('RETURN_CORRECTED');end if;\n",),
    PROFILE:(" for ch in select c.*from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id",),
    OPENING:("then cp7_credit_multi.prior_recognized_v1(w.source_sale_id)+(w.projected_kernel->>'net_current_k')::numeric else 0 end)then\n",),
}
REFUSALS=b.REFUSALS+("'CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED'",)


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW04BC_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patch(sig,body):
    if 'cp7_credit_incoming' in body:raise ValueError('OW04BC_ALREADY_PATCHED: '+sig)
    for marker in PREDECESSOR_MARKERS[sig]:
        if body.count(marker)!=1:raise ValueError('OW04BC_PREDECESSOR_COMPOSITION_CHANGED: '+sig+': '+marker[:60])
    counts={message:body.count(message)for message in REFUSALS}
    for label,old,new in SUBSTITUTIONS[sig]:body=once(body,old,new,sig+' '+label)
    if {message:body.count(message)for message in REFUSALS}!=counts:raise ValueError('OW04BC_REFUSAL_TEXT_CHANGED: '+sig)
    return body


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW04BC_NATIVE_DELTA_SET_CHANGED')
    return {sig:patch(sig,originals[sig])for sig in SIGNATURES}
