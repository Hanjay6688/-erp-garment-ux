"""Counted derivation from the verified installed Native/credit functions.

Only owning callbacks change in private Native copies. Public Native writers,
old source guards, money/HPP/physical bodies and frozen SQL remain unchanged.
"""
SCHEMA='cp7_credit_correction_de'
COMMAND='cp7_sales_return_correction.command(jsonb,uuid,text)'
REVERSE='cp7_sales_return_correction.reverse_sales_return(uuid,text)'
POST='erp.post_sales_return(uuid)'
JOURNAL='cp7_credit._post_journal_bound(text,uuid,date,text,jsonb)'
BASE='cp7_credit.assert_simple_native_base_v1(uuid)'
EVENTS='cp7_credit.initial_base_events_v1(uuid,uuid)'
ORDINAL='cp7_credit.initial_ordinal_input_v1(uuid,uuid)'
PROFILE='cp7_credit._consumer_root_source_profile_v1(uuid,uuid,uuid,jsonb)'
PROVENANCE='cp7_credit.assert_financial_materialization_provenance(jsonb)'
CLOSURE='cp7_credit.enforce_initial_return_closure_v1()'
PUBLIC_COMMAND='public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)'
PUBLIC_WORKSPACE='public.erp_cp7_get_sales_return_correction_v1(jsonb)'
CAPTURES=(COMMAND,REVERSE,POST,JOURNAL,BASE,EVENTS,ORDINAL,PROFILE,PROVENANCE,CLOSURE,PUBLIC_COMMAND,PUBLIC_WORKSPACE)
CHANGED=(EVENTS,ORDINAL,PROFILE,PROVENANCE,CLOSURE,PUBLIC_COMMAND,PUBLIC_WORKSPACE)
COPIES={COMMAND:SCHEMA+'.command_v1(jsonb,uuid,text)',REVERSE:SCHEMA+'.reverse_return_v1(uuid,text)',
 POST:SCHEMA+'.post_return_v1(uuid)',JOURNAL:SCHEMA+'._post_journal_v1(text,uuid,date,text,jsonb)',BASE:SCHEMA+'.assert_native_base_v1(uuid)'}


def once(body,old,new,label):
    if body.count(old)!=1:raise ValueError('CREDIT_DE_EXACT_PREDECESSOR_CHANGED:'+label+':'+str(body.count(old)))
    return body.replace(old,new,1)


def renamed(body,signature,target):
    return once(body,'FUNCTION '+signature.split('(')[0]+'(','FUNCTION '+target.split('(')[0]+'(','private Native header '+signature)


def derive(captures):
    if set(captures)!=set(CAPTURES):raise ValueError('CREDIT_DE_CAPTURE_SET_CHANGED')
    result={}
    body=renamed(captures[COMMAND],COMMAND,COPIES[COMMAND])
    body=once(body,'perform cp7_sales_return_correction.validate(p);',"perform cp7_sales_return_correction.validate(p-'credit_review_token');",'validate extended payload, retain exact request')
    body=once(body," perform set_config('app.change_reason',btrim(p->>'change_reason'),true);", " perform cp7_credit_correction_de.prepare_v1(p,p_request,p_expected,a);\n perform set_config('app.change_reason',btrim(p->>'change_reason'),true);",'after original locks CAS and eligibility, before effects')
    body=once(body,'perform cp7_sales_return_correction.reverse_sales_return(r.id,','perform cp7_credit_correction_de.reverse_return_v1(r.id,','private reverse')
    body=once(body,'perform erp.post_sales_return(replacement);','perform cp7_credit_correction_de.post_return_v1(replacement);','private replacement')
    body=once(body," values(correction_id,r.id,replacement,h.id,auth.uid(),p_request,btrim(p->>'change_reason'))returning *into link;", " values(correction_id,r.id,replacement,h.id,auth.uid(),p_request,btrim(p->>'change_reason'))returning *into link;\n perform cp7_credit_correction_de.materialize_v1(replacement);",'actual link before member registration and actual plans')
    body=once(body,' update cp7_sales_return_correction.requests set response=result where actor=auth.uid()and request_id=p_request;', ' update cp7_sales_return_correction.requests set response=result where actor=auth.uid()and request_id=p_request;\n perform cp7_credit_correction_de.finish_v1(result);','exact receipt closure')
    result[COPIES[COMMAND]]=body
    body=renamed(captures[REVERSE],REVERSE,COPIES[REVERSE])
    for old,new in (('cp7_credit.native_source_enter(',SCHEMA+'.reverse_enter_v1('),('cp7_credit.source_operation_native_reconcile_v1(',SCHEMA+'.reverse_reconciled_v1('),('cp7_credit.native_source_complete(',SCHEMA+'.reverse_complete_v1('),('cp7_credit.current_effective_paid(s.id)',SCHEMA+'.temporary_paid_v1(s.id,false)')):
        body=once(body,old,new,'reverse callback '+old)
    result[COPIES[REVERSE]]=body
    body=renamed(captures[POST],POST,COPIES[POST])
    for name in ('native_return_enter','native_return_guard','post_return_journal','native_return_complete','native_return_leave'):
        body=once(body,'cp7_credit.'+name+'(',SCHEMA+'.'+name+'_v1(','replacement callback '+name)
    body=once(body,'cp7_credit.flush_opening_return_hpp_v1(h.id)',SCHEMA+'.assert_nonopening_v1(h.id)','nonopening proved preflight, no deferred opening work')
    result[COPIES[POST]]=body
    body=renamed(captures[JOURNAL],JOURNAL,COPIES[JOURNAL])
    for name in ('assert_bound_post','bound_book_date','bound_audit_context'):
        body=once(body,'cp7_credit.'+name+'(',SCHEMA+'.'+name+'_v1(','Native bound poster '+name)
    result[COPIES[JOURNAL]]=body
    body=renamed(captures[BASE],BASE,COPIES[BASE])
    body=once(body,'  or exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)',' ','D-owned corrections only, other source guards retained')
    body=once(body,' select *into strict h from erp.sales_headers where id=p_sale;', ' perform cp7_credit_correction_de.assert_owned_links_v1(p_sale);\n select *into strict h from erp.sales_headers where id=p_sale;','closed factual lineage admission')
    result[COPIES[BASE]]=body
    body=once(captures[EVENTS],' return answer;', ' answer:=answer||cp7_credit_correction_de.extra_events_v1(p_sale,p_exclude_return);\n select coalesce(jsonb_agg(v order by v->>\'id\'collate"C"),\'[]\')into answer from jsonb_array_elements(answer)v;\n return answer;','actual restatement financial events')
    result[EVENTS]=body
    old="    where m.family_id=f.id and j.reversal_of_id is null\n"
    new=old+"   union select j.id from cp7_credit.return_family_members m join cp7_sales_return_correction.journal_restatements s on s.original_return_id=m.return_id\n    join erp.journal_entries j on j.id in(s.neutral_journal_id,s.effective_journal_id)where m.family_id=f.id\n"
    result[ORDINAL]=once(captures[ORDINAL],old,new,'all exact restatement legs stay in their original family')
    result[PROFILE]=once(captures[PROFILE],'begin\n', 'begin\n if cp7_credit_correction_de.has_source_v1(p_sale)then\n  perform cp7_credit_correction_de.assert_profile_v1(p_sale,p_root,p_leaf,p_actual);return;end if;\n','narrow current Dprofile dispatch')
    result[PROVENANCE]=once(captures[PROVENANCE],"  else\n   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;", "  elsif cp7_credit_correction_de.marker_owned_v1(f.id)then\n   perform cp7_credit_correction_de.assert_marker_v1(f.id);\n  else\n   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;",'new immutable marker provenance')
    result[CLOSURE]=once(captures[CLOSURE],'begin\n', 'begin\n if cp7_credit_correction_de.close_fact_v1(tg_table_name,row)then return null;end if;\n','exact new fact closure ownership')
    result[PUBLIC_COMMAND]=once(captures[PUBLIC_COMMAND],'cp7_sales_return_correction.command(p_payload,p_request,p_expected)', 'cp7_credit_correction_de.dispatch_v1(p_payload,p_request,p_expected)','existing correction RPC preserves authorization and replay')
    result[PUBLIC_WORKSPACE]=once(captures[PUBLIC_WORKSPACE],'cp7_sales_return_correction.workspace(p_query)', 'cp7_credit_correction_de.workspace_v1(p_query)','existing correction workspace reviewed credit quote')
    if set(result)!=set(CHANGED)|set(COPIES.values()):raise ValueError('CREDIT_DE_DERIVED_SET_CHANGED')
    return result
