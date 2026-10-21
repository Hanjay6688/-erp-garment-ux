"""Exact source-pinned derivation of the bounded all-undone source adapter.

Preserves Native inverse/date/HPP/account/permission predicates and the existing
signed two-axis arithmetic. Does not implement incoming source restatement.
No connection, install or commit occurs on import or derivation.
"""


def derive(captures, once):
    result = {}
    for identity, root in (
        ('cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)', 'sale'),
        ('cp7_credit.source_adjustment_fresh_v1(uuid)', 'w.sale_id'),
    ):
        original = captures[identity]['definition']
        start = original.index(" select coalesce(jsonb_agg(jsonb_build_object('event_id',e.id,'cohort_id',e.cohort_id,'event_kind',e.event_kind,")
        marker = "raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO'using detail=blocked::text;end if;"
        end = original.index(marker, start) + len(marker)
        result[identity] = original[:start] + '\n perform cp7_credit.consumer_source_undone_v1(' + root + ');' + original[end:]

    identity = 'cp7_credit.source_adjustment_fresh_v1(uuid)'
    result[identity] = once(result[identity], "   or jsonb_array_length(fi->'consumptions')<>0\n", '\n ',
                            'retained historical C, still exact before-consumptions binding')
    result[identity] = once(result[identity], "c.initial_mode='CREDIT'", "c.initial_mode in('CREDIT','REFUND')",
                            'both known original disposition modes after exact named undos')

    identity = 'cp7_credit.store_source_adjustments_v1(uuid,jsonb)'
    result[identity] = once(captures[identity]['definition'],
        "  if c.initial_mode<>'CREDIT'or exists(select 1 from cp7_credit.consumption_events where cohort_id=c.id)then\n"
        "   raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO';end if;",
        "  if c.initial_mode not in('CREDIT','REFUND')then raise exception 'CP7_CREDIT_SOURCE_INITIAL_MODE_CHANGED';end if;\n"
        "  perform cp7_credit.consumer_source_undone_v1(w.sale_id);",
        'exact all-undone current facts instead of erasing historical C')

    identity = 'cp7_credit.source_historical_ordinal_input_v1(uuid,boolean)'
    result[identity] = once(captures[identity]['definition'],
        "  if exists(select 1 from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id where c.family_id=f.id)then\n"
        "   raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_CONSUMER_ADAPTER_UNIMPLEMENTED';end if;",
        '  perform cp7_credit.consumer_source_historical_v1(p_operation,f.id);',
        'historical named consumer actual facts')
    result[identity] = once(result[identity], "'retained_recognition',retained,'consumptions','[]'::jsonb)",
        "'retained_recognition',retained,'consumptions',cp7_credit.consumer_source_historical_v1(p_operation,f.id))",
        'full signed historical input to unchanged ordinal kernel')

    identity = 'cp7_credit.source_historical_objects_v1(uuid)'
    result[identity] = once(captures[identity]['definition'],
        "   or(x->>'object_kind'in('PART','PART_JOURNAL')and(x->>'object_id')::uuid=any(part_ids));",
        "   or(x->>'object_kind'in('PART','PART_JOURNAL')and(x->>'object_id')::uuid=any(part_ids))\n"
        "   or(x->>'object_kind'='CONSUMPTION'and exists(select 1 from cp7_credit.consumption_events e\n"
        "    join cp7_credit.cohorts c on c.id=e.cohort_id where e.id=(x->>'object_id')::uuid and c.id=any(cohort_ids))\n"
        "    and exists(select 1 from jsonb_array_elements(op#>'{before_financial_profile,actual_objects}')old\n"
        "     where old=x));",
        'exact historical financial-object membership and current immutable hash')
    return result
