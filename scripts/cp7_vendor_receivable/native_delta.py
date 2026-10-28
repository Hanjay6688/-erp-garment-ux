"""Counted Native changes; the old covered-payable and claim paths remain.

Only an explicit vendor_receivable_account_id opts a downward correction into
AR. No post_journal, reverse_journal, cost formula, quantity or public RPC delta.
"""
POST='erp.bd_post_invoice_v1(jsonb,uuid)'
APPLY='erp.bd_apply_vendor_credit_v1(text,uuid,text,uuid,numeric,date,text,uuid)'
APPLIED='erp.bd_claim_credit_applied_v1(text,uuid)'
OPENING='erp.bd_claim_credit_opening_lines_v1(uuid)'
PAYABLES='erp.bd_vendor_payables_v1(uuid)'
ROUTER='erp.save_laundry_bd_action_v1(text,jsonb,uuid)'
WORKSPACE='erp.get_laundry_bd_workspace_v1(jsonb)'
SIGNATURES=(POST,APPLY,APPLIED,OPENING,PAYABLES,ROUTER,WORKSPACE)
SCHEMA='cp7_vendor_receivable'

def once(value,old,new,label):
    if value.count(old)!=1:raise ValueError('OW08B_VENDOR_PREDECESSOR_CHANGED:'+label+':'+str(value.count(old)))
    return value.replace(old,new,1)

def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW08B_VENDOR_NATIVE_SET_CHANGED')
    out=dict(originals)
    out[POST]=once(out[POST],"array['invoice_id','expected_version'],array['invoice_id','expected_version'],'post invoice'",
        "array['invoice_id','expected_version'],array['invoice_id','expected_version','vendor_receivable_account_id'],'post invoice'",'post-payload')
    anchor='  if i.header_total>0 then\n'
    out[POST]=once(out[POST],anchor,
        "  if p_payload ? 'vendor_receivable_account_id' and i.header_total>=0 then raise exception 'CP7_VENDOR_RECEIVABLE_CORRECTION_REQUIRED';end if;\n"+anchor,'down-only')
    start='    select coalesce(sum(jl.credit-jl.debit),0) into v_ap from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id\n'
    out[POST]=once(out[POST],start,
        "    if p_payload ? 'vendor_receivable_account_id' then\n"
        "      v_lines:=v_lines||cp7_vendor_receivable.register_v1(i.id,erp.bd_uuid_v1(p_payload,'vendor_receivable_account_id',true));\n"
        "    else\n"+start,'ar-opt-in')
    anchor="    v_journal:=erp.post_journal('BD_LAUNDRY_CORRECTION_CREDIT',i.id,"
    out[POST]=once(out[POST],anchor,'    end if;\n'+anchor,'old-ap-end')
    anchor='  perform erp.bd_invoice_resync_v1(i.id,i.invoice_date);\n'
    out[POST]=once(out[POST],anchor,anchor+'  perform cp7_vendor_receivable.check_dates_v1(i.vendor_id);\n','post-dates')
    anchor='  select coalesce(sum(a.amount),0)::numeric(18,2) from erp.bd_claim_credit_applications_v1 a\n'
    out[APPLIED]=once(out[APPLIED],anchor,
        '  select (coalesce(sum(a.amount),0)+cp7_vendor_receivable.refunded_v1(p_kind,p_id))::numeric(18,2) from erp.bd_claim_credit_applications_v1 a\n','refund-consumption')
    anchor=("      jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',p_amount,'credit',0,'vendor_id',v_vendor),\n"
            "        jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',p_amount,'vendor_id',v_vendor)))")
    out[APPLY]=once(out[APPLY],anchor,
        '      cp7_vendor_receivable.application_lines_v1(p_kind,p_source,v_vendor,p_amount))','daily-lines')
    for label,anchor in [('daily',"    return jsonb_build_object('application_id',p_request,'target_kind',p_target_kind,'target_id',h.id,"),('opening',"  return jsonb_build_object('application_id',p_request,'target_kind',p_target_kind,'target_id',b.id,")]:
        out[APPLY]=once(out[APPLY],anchor,'  perform cp7_vendor_receivable.check_dates_v1(v_vendor);\n'+anchor,label+'-dates')
    out[OPENING]=once(out[OPENING],'  return jsonb_build_array(\n',
        '  return cp7_vendor_receivable.opening_lines_v1(p_settlement_id,jsonb_build_array(\n','opening-lines')
    anchor="    jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',s.amount,'vendor_id',b.vendor_id));"
    out[OPENING]=once(out[OPENING],anchor,anchor[:-1]+');','opening-end')
    out[PAYABLES]=once(out[PAYABLES],"  select jsonb_build_object('vendor_id',p_vendor,\n",
        "  select cp7_vendor_receivable.augment_v1(p_vendor,jsonb_build_object('vendor_id',p_vendor,\n",'payables-wrap')
    out[PAYABLES]=once(out[PAYABLES],'      from ledger l))\n','      from ledger l)))\n','payables-end')
    # Existing request envelope rechecks current authority BEFORE a cached reply.
    out[ROUTER]=once(out[ROUTER],"'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT'",
        "'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT','RECEIVE_VENDOR_REFUND','REVERSE_VENDOR_REFUND'",'actions')
    anchor="    when 'APPLY_CLAIM_CREDIT' then erp.bd_apply_claim_credit_v1(p_payload,p_client_request_id)\n"
    out[ROUTER]=once(out[ROUTER],anchor,anchor+
        "    when 'RECEIVE_VENDOR_REFUND' then cp7_vendor_receivable.refund_v1(p_payload,p_client_request_id)\n"
        "    when 'REVERSE_VENDOR_REFUND' then cp7_vendor_receivable.reverse_refund_v1(p_payload,p_client_request_id)\n",'dispatch')
    anchor="    'can_manage_master',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('master.partner.manage'),\n"
    out[WORKSPACE]=once(out[WORKSPACE],anchor,
        "    'vendor_receivable_contract','cp7.vendor-receivable.v1',\n"
        "    'vendor_receivable_accounts',case when v_money then cp7_vendor_receivable.accounts_v1()end,\n"+anchor,'workspace-contract')
    return out
