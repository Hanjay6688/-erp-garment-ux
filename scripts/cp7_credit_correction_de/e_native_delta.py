"""Counted E1 delta over a verified D1 installation; no import-time I/O/DB.

Immutable money events keep their original target UUID. New note assignment
facts route current incoming U to the replacement. Native money/HPP bodies
change only in private owning callback copies.
"""
SCHEMA='cp7_credit_note_carry_de'
COMMAND='cp7_note.command(jsonb,uuid,text)'
REVERSE='cp7_note.reverse_sale(uuid,text)'
SNAPSHOT='cp7_credit.source_native_snapshot_v1(uuid)'
PUBLIC_COMMAND='public.erp_cp7_correct_note_v1(jsonb,uuid,text)'
PUBLIC_WORKSPACE='public.erp_cp7_get_note_correction_v2(uuid)'
CORE='erp._cp7_current_credit_adjustment(uuid)'
OBJECTS='cp7_credit.current_materialized_objects(uuid,uuid,uuid)'
PROFILE='cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'
EVENTS='cp7_credit.initial_base_events_v1(uuid,uuid)'
ORDINAL='cp7_credit.initial_ordinal_input_v1(uuid,uuid)'
FUNDING='cp7_credit.consumer_incoming_funding_v1(uuid)'
INCOMING='cp7_credit_incoming.incoming_applied_v1(uuid)'
SELECTION='cp7_credit.consumer_selection_v1(jsonb)'
CAPTURE='cp7_credit.consumer_capture_sources_v1(jsonb)'
PROJECTION='cp7_credit.consumer_projection_v1(jsonb,jsonb)'
EXECUTE='cp7_credit.consumer_execute_v1(uuid)'
CLOSURE='cp7_credit.assert_consumer_closed_v1(uuid)'
INVARIANT='cp7_credit.consumer_native_invariant_v1(uuid)'
INVOICE='cp7_credit.consumer_invoice_profile_v1(uuid)'
CONSUMER='cp7_credit.consumer_event_data_v1(uuid)'
QUOTE='cp7_credit.consumer_quote_v1(jsonb)'
SOURCE_ENTER='cp7_credit.native_source_enter(text,uuid)'
CHANGED=(PUBLIC_COMMAND,PUBLIC_WORKSPACE,CORE,OBJECTS,PROFILE,EVENTS,ORDINAL,FUNDING,INCOMING,SELECTION,CAPTURE,PROJECTION,EXECUTE,CLOSURE,INVARIANT,INVOICE,CONSUMER,QUOTE,SOURCE_ENTER)
CAPTURES=(COMMAND,REVERSE,SNAPSHOT)+CHANGED
COPIES={COMMAND:SCHEMA+'.command_v1(jsonb,uuid,text)',REVERSE:SCHEMA+'.reverse_sale_v1(uuid,text)',SNAPSHOT:SCHEMA+'.raw_native_snapshot_v1(uuid)'}


def counted(body,old,new,count,label):
    if body.count(old)!=count:raise ValueError('CREDIT_E1_EXACT_PREDECESSOR_CHANGED:'+label+':'+str(body.count(old)))
    return body.replace(old,new,count)

def once(body,old,new,label):return counted(body,old,new,1,label)

def rename(body,old,new):return once(body,'FUNCTION '+old.split('(')[0]+'(','FUNCTION '+new.split('(')[0]+'(','private header '+old)

def derive(captures):
    if set(captures)!=set(CAPTURES):raise ValueError('CREDIT_E1_CAPTURE_SET_CHANGED')
    result={}
    body=rename(captures[COMMAND],COMMAND,COPIES[COMMAND])
    body=once(body,"cp7_sales.validate_draft(p_payload-'item_lineage',true)","cp7_sales.validate_draft(p_payload-'item_lineage'-'credit_carry_review',true)",'extended correction metadata stays out of Native draft validator')
    body=once(body,' insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);',' perform '+SCHEMA+'.prepare_v1(p_payload,p_request,p_expected,correction_id,a);\n insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);','original CAS/eligibility before full graph prepare')
    body=once(body,'perform cp7_note.reverse_sale(leaf,','perform '+SCHEMA+'.reverse_sale_v1(leaf,','private bound inverse')
    body=once(body,"p_payload-'sale_id'-'review_token'-'change_reason'-'item_lineage'","p_payload-'sale_id'-'review_token'-'change_reason'-'item_lineage'-'credit_carry_review'",'never send carry metadata into Native save')
    body=once(body," values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);", " values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);\n perform "+SCHEMA+'.materialize_v1(replaced);','actual revision before assignment')
    body=once(body,' update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;', ' update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;\n perform '+SCHEMA+'.finish_v1(result);','exact committed receipt and scope completion')
    result[COPIES[COMMAND]]=body
    body=rename(captures[REVERSE],REVERSE,COPIES[REVERSE])
    body=once(body,'cp7_credit.native_source_enter(',SCHEMA+'.reverse_enter_v1(','only this owning note inverse admission')
    body=once(body,'cp7_credit.native_source_complete(',SCHEMA+'.reverse_complete_v1(','own inverse terminal')
    result[COPIES[REVERSE]]=body
    body=rename(captures[SNAPSHOT],SNAPSHOT,COPIES[SNAPSHOT])
    result[COPIES[SNAPSHOT]]=once(body,'cp7_credit.source_document_snapshot_v1(p_sale)',SCHEMA+'.raw_document_v1(p_sale)','Native-only factual snapshot, full HPP body retained')
    result[PUBLIC_COMMAND]=once(captures[PUBLIC_COMMAND],'cp7_note.command(p_payload,p_request,p_expected)',SCHEMA+'.dispatch_v1(p_payload,p_request,p_expected)','existing public correction routing')
    result[PUBLIC_WORKSPACE]=once(captures[PUBLIC_WORKSPACE],'cp7_note.workspace_with_actors(p_sale)',SCHEMA+'.workspace_v1(p_sale)','existing actor-labelled workspace carries source basis')
    result[CORE]=counted(captures[CORE],"e.event_kind='APPLY'and e.target_sale_id=p_sale","e.event_kind='APPLY'and "+SCHEMA+'.effective_target_v1(e.id)=p_sale',2,'current U + participation, historical inactive fast path unchanged')
    result[CORE]=once(result[CORE],' if not exists(select 1 from cp7_credit.return_families f where f.family_root_sale_id=m.root_sale_id)', ' if not '+SCHEMA+'.is_current_v1(p_sale)and not exists(select 1 from cp7_credit.return_families f where f.family_root_sale_id=m.root_sale_id)','a missing assignment can never use the legacy zero-adjustment fast path')
    body=once(captures[OBJECTS],"if e.event_kind='APPLY'and e.target_sale_id=p_sale then", "if e.event_kind='APPLY'and "+SCHEMA+'.effective_target_v1(e.id)=p_sale then','current U assignment, actual event object stays unchanged')
    body=once(body,"or(e.cohort_id,e.event_kind,e.target_sale_id,e.cash_account_id,e.amount)is distinct from\n    (o.cohort_id,o.event_kind,o.target_sale_id,o.cash_account_id,-o.amount)","or(e.cohort_id,e.event_kind,e.cash_account_id,e.amount)is distinct from\n    (o.cohort_id,o.event_kind,o.cash_account_id,-o.amount)\n    or not "+SCHEMA+'.same_target_v1(o.target_sale_id,e.target_sale_id)','exact named restore can target proven replacement of same invoice')
    result[OBJECTS]=body
    result[PROFILE]=once(captures[PROFILE],'  perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);', '  if root=p_root and '+SCHEMA+'.has_root_v1(root)then\n   perform '+SCHEMA+'.assert_profile_v1(p_sale,p_root,p_leaf,actual);\n  else perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);end if;','only E-owned receiving root uses logical note proof')
    result[EVENTS]=once(captures[EVENTS],'begin\n', 'begin\n if '+SCHEMA+'.is_current_v1(p_sale)then\n  if p_exclude_return is not null then raise exception \'CP7_CREDIT_NOTE_CARRY_NO_RETURN_EXCLUSION\';end if;\n  return '+SCHEMA+'.current_events_v1(p_sale);end if;\n','current E Native family financial events')
    result[ORDINAL]=once(captures[ORDINAL],'begin\n', 'begin\n if '+SCHEMA+'.is_current_v1(p_sale)then\n  if p_pending_plan is not null then raise exception \'CP7_CREDIT_NOTE_CARRY_NO_PENDING_RECOGNITION\';end if;\n  return '+SCHEMA+'.ordinal_v1(p_sale);end if;\n','E receiver has no return families or recognition')
    result[FUNDING]=once(captures[FUNDING],"event_kind='APPLY'and target_sale_id=p_sale", "event_kind='APPLY'and "+SCHEMA+'.effective_target_v1(id)=p_sale','signed immutable incoming events follow exact assignment')
    result[INCOMING]=once(captures[INCOMING],"e.event_kind='APPLY'and e.target_sale_id=p_sale","e.event_kind='APPLY'and "+SCHEMA+'.effective_target_v1(e.id)=p_sale','same signed U in all credit readers')
    body=once(captures[SELECTION],"original:=old.id;amount:=-old.amount;target:=old.target_sale_id;cash:=old.cash_account_id;", 'original:=old.id;amount:=-old.amount;target:=case when old.event_kind=\'APPLY\'then '+SCHEMA+'.effective_target_v1(old.id)else old.target_sale_id end;cash:=old.cash_account_id;','UNDO still names original; resolved target is its current assignment')
    body=once(body,'   or(target_root,target_leaf)is distinct from(target,target)then','   or((target_root,target_leaf)is distinct from(target,target)and not(target_leaf=target and '+SCHEMA+'.is_current_v1(target)))then','only owned current E target relaxes flat target restriction')
    result[SELECTION]=body
    body=once(captures[CAPTURE],"jsonb_array_elements_text(p_graph->'sale_ids')",'jsonb_array_elements_text('+SCHEMA+'.active_sales_v1(p_graph))','all graph members remain locked; capture active monetary leaves')
    body=once(body,'cp7_credit.assert_current_materialized_profile(sale,sale,sale)','cp7_credit.assert_current_materialized_profile(sale,'+SCHEMA+'.root_v1(sale),sale)','actual logical root in captured profile')
    result[CAPTURE]=once(body,'cp7_credit.inspect_current_materialized_profile(sale,sale,sale)','cp7_credit.inspect_current_materialized_profile(sale,'+SCHEMA+'.root_v1(sale),sale)','actual logical root in captured inspector')
    result[PROJECTION]=once(captures[PROJECTION],"jsonb_array_elements_text(p_locked#>'{graph,sale_ids}')",'jsonb_array_elements_text('+SCHEMA+".active_sales_v1(p_locked->'graph'))",'review versions/current Native invariants cover captured active leaves')
    result[EXECUTE]=once(captures[EXECUTE],"jsonb_array_elements_text(o.source_graph->'sale_ids')",'jsonb_array_elements_text('+SCHEMA+'.active_sales_v1(o.source_graph))','same captured active terminal set')
    body=once(captures[CLOSURE],"is distinct from o.source_graph->'sale_ids'then",'is distinct from '+SCHEMA+'.active_sales_v1(o.source_graph)then','historical receipt uses its captured leaf set')
    body=once(body,"jsonb_array_elements_text(o.source_graph->'sale_ids')",'jsonb_array_elements_text('+SCHEMA+'.active_sales_v1(o.source_graph))','historical numbers never recomputed as new leaf numbers')
    result[CLOSURE]=once(body,'perform cp7_credit.consumer_invoice_profile_v1(sale::uuid);','perform '+SCHEMA+'.validate_current_v1(sale::uuid);','separate present-state validation follows the current owned assignment')
    result[INVARIANT]=counted(captures[INVARIANT],'ce.target_sale_id=p_sale',''+SCHEMA+'.effective_target_v1(ce.id)=p_sale',2,'all consumer money excluded from Native-only invariant, including carried original')
    result[INVOICE]=once(captures[INVOICE],'begin\n','begin\n if '+SCHEMA+'.is_current_v1(p_sale)then return '+SCHEMA+'.invoice_profile_v1(p_sale);end if;\n','current E invoice numeric profile; inactive headers still never return current numbers')
    result[CONSUMER]=once(captures[CONSUMER],"(e.cohort_id,e.event_kind,e.amount,e.target_sale_id,e.cash_account_id)\n    is distinct from(old.cohort_id,old.event_kind,-old.amount,old.target_sale_id,old.cash_account_id)","(e.cohort_id,e.event_kind,e.amount,e.cash_account_id)\n    is distinct from(old.cohort_id,old.event_kind,-old.amount,old.cash_account_id)\n   or not "+SCHEMA+'.same_target_v1(old.target_sale_id,e.target_sale_id)','named inverse keeps exact original amount/cohort/account and proven logical target')
    result[QUOTE]=once(captures[QUOTE],"'expected_versions',projection->'expected_versions','quote_sha256',binding);", "'expected_versions',projection->'expected_versions','quote_sha256',binding)||\n  case when "+SCHEMA+".target_assignment_v1(selection)is null then '{}'::jsonb\n  else jsonb_build_object('target_assignment',"+SCHEMA+'.target_assignment_v1(selection))end;','closed client can verify new target/root difference from explicit assignment')
    result[SOURCE_ENTER]=once(captures[SOURCE_ENTER],'begin\n','begin\n perform '+SCHEMA+'.guard_later_native_source_v1(p_action,p_source);\n','carried originals cannot escape the retained mutation refusal via their new leaf UUID')
    if set(result)!=set(CHANGED)|set(COPIES.values()):raise ValueError('CREDIT_E1_DERIVATION_SET_CHANGED')
    return result
