"""Closed derivations from the freshly verified complete consumer predecessor.

No connection, installation, commit or ambient authority on import. Every
anchor is unique. Original Native eligibility, dates, cash and posting remain.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_FILES = ('01_facts.sql', '02_actual_proof.sql', '03_owning_callbacks.sql', '04_completion.sql',
             '05_consumer_continuation.sql', '06_replacement_admission.sql')
CHANGED = (
 'cp7_payment_correction.apply(jsonb,uuid,text)',
 'erp.post_sales_payment(uuid)', 'erp._cp7_current_credit_adjustment(uuid)',
 'cp7_credit.current_effective_paid(uuid)', 'cp7_credit.initial_base_events_v1(uuid,uuid)',
 'cp7_credit.native_source_enter(text,uuid)', 'cp7_credit.native_source_complete(text,uuid)',
 'cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)', 'cp7_credit.source_request_finish_v1(uuid)',
 'cp7_credit.source_operation_native_reconcile_v1(text,uuid)',
 'cp7_credit.assert_source_operation_work_v1(uuid)',
 'cp7_credit.source_adjustment_fresh_v1(uuid)', 'cp7_credit.store_source_adjustments_v1(uuid,jsonb)',
 'cp7_credit.consumer_source_historical_v1(uuid,uuid)',
 'cp7_credit.source_snapshot_base_events_v1(jsonb)', 'cp7_credit.assert_simple_native_base_v1(uuid)',
 'cp7_credit.assert_source_actual_v1(uuid)', 'cp7_credit.assert_source_materialization_v1(uuid)',
 'cp7_credit.source_completion_manifest_v1(uuid)', 'cp7_credit.assert_source_operation_closed_v1(uuid)',
 'cp7_credit.consumer_execute_v1(uuid)', 'cp7_credit.assert_reconciled_source_profile_v1(uuid,jsonb)',
 'cp7_credit.validate_source_adjustment_component_v1(uuid)',
)


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('OW04_PAYMENT_SOURCE_UNIQUE_PREDECESSOR_ANCHOR_CHANGED: '+old)
    return text.replace(old, new, 1)


def preflight_definition():
    text = (HERE.parent/'consumer/12_payment_restatement_preflight.sql').read_text()
    text = re.sub(r'do \$not_an_installer\$begin[\s\S]*?end \$not_an_installer\$;', '', text)
    text = text.replace('consumer_payment_restatement_preflight_v1', 'payment_source_preflight_v1')
    text = once(text, 'returns void', 'returns jsonb')
    text = once(text, 'if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;',
        'if not cp7_credit.has_ow04_participation_v1(sale)then return null::jsonb;end if;')
    text = once(text, ' perform cp7_credit.consumer_source_undone_v1(sale);',
        " if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then\n"
        "  raise exception 'CP7_CREDIT_SOURCE_INCOMING_HISTORY_ADAPTER_REQUIRED';end if;")
    text = once(text, 'or amount<=0 or amount>=original.amount or amount*100<>trunc(amount*100)',
        'or amount<=0 or amount=original.amount or amount*100<>trunc(amount*100)')
    text = once(text,
        '  or exists(select 1 from cp7_payment_correction.links where original_id=original.id or replacement_id=original.id)\n'
        '  or exists(select 1 from cp7_credit.source_operation_materializations_v1 where sale_id=sale)\n', '')
    text = once(text, ' before_input:=cp7_credit.initial_ordinal_input_v1(sale);',
        " perform cp7_credit.payment_link_source_check_v1(sale);\n"
        " perform cp7_credit.assert_current_materialized_profile(sale,sale,sale);\n"
        " -- Existing return credit can be reconciled, but cannot fund receipts\n"
        " -- beyond the actual original invoice gross amount.\n"
        " if amount+coalesce((select sum(x.amount)from erp.sales_payments x where x.sale_id=sale\n"
        "  and x.status='POSTED'and x.id<>original.id),0)>\n"
        "  coalesce((select sum(i.line_total)from erp.sales_items i where i.sale_id=sale),0)then\n"
        "  raise exception 'CP7_CREDIT_PAYMENT_GROSS_RECEIPT_LIMIT';end if;\n"
        ' before_input:=cp7_credit.source_reconciliation_input_v1(sale);')
    # The original unsafe case keeps its entire actual-pending/cut/detail
    # contract. Only the successful terminal refusal becomes a typed result.
    anchor = " raise exception 'CP7_CREDIT_RESTATEMENT_FULL_CORRECTION_ADAPTER_REQUIRED';\nend $$;"
    text = once(text, anchor,
        " if not coalesce((result->>'arithmetic_supported')::boolean,false)\n"
        "  or exists(select 1 from jsonb_array_elements(result->'families')f\n"
        "   where coalesce((f->>'needs_cohort_configuration')::boolean,false)\n"
        "    or exists(select 1 from jsonb_array_elements(f->'reconciliation_components')x where(x->>'amount')::numeric=0))then\n"
        "  raise exception 'CP7_CREDIT_PAYMENT_PROJECTED_ADAPTER_CLASS_UNSUPPORTED';end if;\n"
        " return jsonb_build_object('authority',authority,'graph',graph,'sources',sources,'period',period,\n"
        "  'before_input',before_input,'before_result',before_result,'proposed',proposed,'result',result);\nend $$;")
    return text


def ambient_definition(inventory):
    queries = []
    for name, _, _, backend, transaction, oid, _ in inventory.SPECS:
        if name in ('cp7_sales.command_context', 'cp7_payment_correction.context',
                    'cp7_guard.compound_scope', 'cp7_guard.compound_touch'):
            continue
        if name == inventory.PLAN_TABLE:
            queries.append('select 1 where '+inventory.PLAN_READER)
        else:
            predicate = inventory._predicate(dict(name=name, backend=backend,
                transaction_column=transaction, transaction_type_oid=oid))
            queries.append('select 1 from '+name+' c where '+predicate)
    for name in ('consumer_execution_context', 'consumer_posting_scope_v1', 'initial_return_work',
                 'return_command_scope', 'return_native_scope', 'source_mutation_scope'):
        queries.append('select 1 from cp7_credit.'+name+' c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()')
    queries.append("select 1 from cp7_guard.compound_scope c where c.txid=txid_current()and(c.label<>'SALES_PAYMENT_CORRECTION'or c.depth<>1)")
    body = 'begin if exists('+ ' union all '.join(queries) + ")then raise exception 'CP7_CREDIT_PAYMENT_AMBIENT_CONTEXT_REFUSED';end if;end"
    return "create function cp7_credit.payment_source_ambient_guard_v1(p_sale uuid)returns void language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $payment_ambient$"+body+'$payment_ambient$;'


def derive(captures):
    if set(captures) != set(CHANGED):
        raise ValueError('OW04_PAYMENT_SOURCE_CAPTURE_SET_CHANGED')
    result = {sig: row['definition'] for sig, row in captures.items()}
    sig = 'cp7_payment_correction.apply(jsonb,uuid,text)'
    result[sig] = once(result[sig], 'perform cp7_credit.consumer_payment_restatement_preflight_v1(p,p_request,p_expected);',
        'perform cp7_credit.payment_source_enter_v1(p,p_request,p_expected);')
    result[sig] = once(result[sig], " insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'PAYMENT');",
        " perform cp7_credit.payment_replacement_prepare_v1(p_request,neutral,effective);\n"
        " insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'PAYMENT');")
    result[sig] = once(result[sig], " return posted||jsonb_build_object('original_payment_id',original.id,",
        " perform cp7_credit.payment_source_finish_v1(p_request,posted,link);\n return posted||jsonb_build_object('original_payment_id',original.id,")

    sig = 'erp.post_sales_payment(uuid)'
    result[sig] = once(result[sig], 'if v_paid+v_amount>v_total then',
        'if v_paid+v_amount>v_total and not cp7_credit.payment_replacement_admitted_v1(p_payment_id,v_total,v_paid,v_amount)then')
    anchor = "  update erp.sales_payments set status='POSTED' where id=p_payment_id;"
    result[sig] = once(result[sig], anchor, anchor+'\n  perform cp7_credit.payment_posted_reconcile_v1(p_payment_id);')
    sig = 'erp._cp7_current_credit_adjustment(uuid)'
    anchor = ' perform cp7_credit.assert_current_materialized_profile(p_sale,m.root_sale_id,m.current_leaf_id);'
    result[sig] = once(result[sig], anchor,
        " if cp7_credit.payment_is_intermediate_v1(p_sale)then return cp7_credit.payment_intermediate_adjustment_v1(p_sale);end if;\n"+anchor)
    sig = 'cp7_credit.current_effective_paid(uuid)'
    result[sig] = once(result[sig], 'if paid+adjustment<0 then',
        'if paid+adjustment<0 and not cp7_credit.payment_is_intermediate_v1(p_sale)then')

    for sig, call in (
        ('cp7_credit.native_source_enter(text,uuid)', 'payment_native_enter_v1'),
        ('cp7_credit.native_source_complete(text,uuid)', 'payment_native_complete_v1'),
        ('cp7_credit.source_operation_native_reconcile_v1(text,uuid)', 'payment_inverse_effect_v1')):
        result[sig] = once(result[sig], 'begin\n', 'begin\n if cp7_credit.'+call+'(p_action,p_source)then return;end if;\n')
    sig = 'cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)'
    result[sig] = once(result[sig], 'begin\n', """begin
 if exists(select 1 from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  select w.operation_id into strict op from cp7_credit.source_operation_work_v1 w join cp7_credit.payment_source_context_v1 pc on pc.operation_id=w.operation_id
   where w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()and w.actor=auth.uid()
    and w.action='PAYMENT_CORRECT'and p_action='PAYMENT_REVERSE'and pc.phase='PREPARED'
    and w.request_id=p_request and w.expected_version=p_expected and p_payload=w.payload-'replacement';
  perform cp7_credit.payment_source_assert_pending_v1(op);return;
 end if;
""")
    sig = 'cp7_credit.source_request_finish_v1(uuid)'
    result[sig] = once(result[sig], 'begin\n', """begin
 if exists(select 1 from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  select w0.*into strict w from cp7_credit.source_operation_work_v1 w0 join cp7_credit.payment_source_context_v1 pc on pc.operation_id=w0.operation_id
   where w0.backend_pid=pg_backend_pid()and w0.transaction_id=txid_current()and w0.actor=auth.uid()
    and w0.request_id=p_request and w0.action='PAYMENT_CORRECT'and pc.phase='INVERSE_COMPLETE';
  perform cp7_credit.payment_source_assert_pending_v1(w.operation_id);return;
 end if;
""")
    sig = 'cp7_credit.assert_source_operation_work_v1(uuid)'
    anchor = ' perform cp7_credit.assert_only_own_sales_source_context_v1(w.sale_id,w.action);'
    result[sig] = once(result[sig], anchor,
        " if w.action='PAYMENT_CORRECT'then perform cp7_credit.payment_source_assert_pending_v1(w.operation_id);return;end if;\n"+anchor)
    for sig in ('cp7_credit.source_adjustment_fresh_v1(uuid)', 'cp7_credit.store_source_adjustments_v1(uuid,jsonb)'):
        result[sig] = once(result[sig], 'perform cp7_credit.consumer_source_undone_v1(w.sale_id);',
            "if w.action='PAYMENT_CORRECT'then perform cp7_credit.payment_source_consumers_v1(w.operation_id);\n"
            '  else perform cp7_credit.consumer_source_undone_v1(w.sale_id);end if;')
        result[sig] = once(result[sig], "where(a->>'amount')::numeric>=0)",
            "where(a->>'amount')::numeric=0 or((a->>'amount')::numeric>0 and w.action<>'PAYMENT_CORRECT'))")
    sig = 'cp7_credit.validate_source_adjustment_component_v1(uuid)'
    result[sig] = once(result[sig], 'or p.net_amount>=0 or p.expected_component_count<=0',
        "or(p.net_amount>=0 and p.owning_action<>'PAYMENT_CORRECT')or p.expected_component_count<=0")
    result[sig] = once(result[sig], 'or cc.amount>=0))then',
        "or cc.amount=0 or(cc.amount>0 and p.owning_action<>'PAYMENT_CORRECT')))then")
    sig = 'cp7_credit.consumer_source_historical_v1(uuid,uuid)'
    result[sig] = once(result[sig], 'or(e.amount>0 and not exists(',
        "or(e.amount>0 and op->>'action'<>'PAYMENT_CORRECT'and not exists(")

    sig = 'cp7_credit.initial_base_events_v1(uuid,uuid)'
    anchor = " ),walk(id,origin,kind)as("
    result[sig] = once(result[sig], anchor,
        "  union all select j.id,j.id,'FUNDING'from erp.journal_entries j join erp.sales_payments p on p.id=j.source_id\n"
        "   where j.source_type in('PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')and p.sale_id=p_sale and j.reversal_of_id is null\n"+anchor)
    sig = 'cp7_credit.source_snapshot_base_events_v1(jsonb)'
    result[sig] = once(result[sig], "journal,source_type}'='SALES_PAYMENT'then'FUNDING'else'NET'end",
        "journal,source_type}'in('SALES_PAYMENT','PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')then'FUNDING'else'NET'end")
    anchor = "or(j#>>'{immutable_payload,journal,source_type}'='SALES_PAYMENT'and exists("
    result[sig] = once(result[sig], anchor,
        "or(j#>>'{immutable_payload,journal,source_type}'in('SALES_PAYMENT','PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')and exists(")
    sig = 'cp7_credit.assert_simple_native_base_v1(uuid)'
    anchor = "\n  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in(l.original_id,l.replacement_id)where p0.sale_id=p_sale)"
    result[sig] = once(result[sig], anchor, '')
    anchor = "  raise exception 'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED';end if;"
    result[sig] = once(result[sig], anchor, anchor+'\n perform cp7_credit.payment_link_source_check_v1(p_sale);')

    sig = 'cp7_credit.assert_source_actual_v1(uuid)'
    result[sig] = once(result[sig], 'cp7_credit.source_inverse_proof_v1(w.before_source,actual,w.action,w.source_id)',
        'cp7_credit.source_owned_actual_proof_v1(w.operation_id,w.before_source,actual,w.action,w.source_id)')
    sig = 'cp7_credit.assert_source_materialization_v1(uuid)'
    result[sig] = once(result[sig], 'or p.net_amount>=0 or sp.full_family_result',
        "or(p.net_amount>=0 and m.action<>'PAYMENT_CORRECT')or sp.full_family_result")
    result[sig] = once(result[sig], "where(x->>'amount')::numeric>=0)",
        "where(x->>'amount')::numeric=0 or((x->>'amount')::numeric>0 and m.action<>'PAYMENT_CORRECT'))")
    result[sig] = once(result[sig], 'cp7_credit.source_inverse_proof_v1(m.before_source,m.actual_source,m.action,m.source_id)',
        'cp7_credit.source_owned_actual_proof_v1(m.operation_id,m.before_source,m.actual_source,m.action,m.source_id)')
    sig = 'cp7_credit.source_completion_manifest_v1(uuid)'
    anchor = " select jsonb_build_object('contract_version','ow04.source-operation-completion.v1'"
    result[sig] = once(result[sig], anchor,
        " select case when m.action='PAYMENT_CORRECT'then cp7_credit.payment_source_completion_manifest_v1(m.operation_id)else jsonb_build_object('contract_version','ow04.source-operation-completion.v1'")
    anchor = "(m.actual_source_proof->>'inverse_journal_id')::uuid))\n from"
    result[sig] = once(result[sig], anchor, "(m.actual_source_proof->>'inverse_journal_id')::uuid))end\n from")
    sig = 'cp7_credit.assert_source_operation_closed_v1(uuid)'
    anchor = ' select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;'
    result[sig] = once(result[sig], anchor,
        " if m.action='PAYMENT_CORRECT'then perform cp7_credit.assert_payment_source_closed_v1(m.operation_id);return;end if;\n"+anchor)
    sig = 'cp7_credit.consumer_execute_v1(uuid)'
    anchor = "  update erp.sales_headers set status=case when effective=net then'PAID'when effective>0 then'PARTIAL_PAID'else'POSTED'end where id=header.id;"
    result[sig] = once(result[sig], anchor,
        anchor+'\n  perform cp7_credit.payment_consumer_header_capture_v1(o.id,header.id,to_jsonb(header));')
    sig = 'cp7_credit.assert_reconciled_source_profile_v1(uuid,jsonb)'
    result[sig] = once(result[sig],
        'cp7_credit.source_semantic_snapshot_v1(m.before_source)\n   is distinct from cp7_credit.source_semantic_snapshot_v1(last_source)',
        'not cp7_credit.payment_consumer_source_continues_v1(p_sale,\n   cp7_credit.source_semantic_snapshot_v1(last_source),cp7_credit.source_semantic_snapshot_v1(m.before_source))')
    result[sig] = once(result[sig],
        'cp7_credit.source_document_snapshot_v1(p_sale)\n  is distinct from cp7_credit.source_semantic_snapshot_v1(last_source)',
        'not cp7_credit.payment_consumer_source_continues_v1(p_sale,\n  cp7_credit.source_semantic_snapshot_v1(last_source),cp7_credit.source_document_snapshot_v1(p_sale))')
    return result
