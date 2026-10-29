"""Counted installed-source extensions; old frozen source files stay untouched.

Private carry CREATE/VALIDATE clones preserve the Native allocation and source
checks. Twelve existing Native functions plus one existing private settlement
facade receive bounded hooks; all thirteen actual originals remain available
for exact preuse removal. Other settlement actions keep their original paths.
"""
SCHEMA='cp7_attendance_choice'
CREATE='erp.create_attendance_hpp_pool_v1(jsonb,uuid)'
VALIDATE='erp.validate_attendance_hpp_pool_v1(uuid)'
ACTIVATE='erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)'
CANCEL='erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)'
APPROVE='erp.approve_payroll(uuid)'
UNPAID='erp.cancel_unpaid_payroll(uuid,text)'
PAID='erp.reverse_paid_payroll(uuid,text)'
POLICY='erp._cp3_r4_active_pool_affects_contractor(uuid,date,date)'
SET_POLICY='erp.set_contractor_hpp_policy_v1(jsonb,uuid,uuid)'
JOURNAL='erp.reverse_journal(uuid,text)'
SEWING='erp.record_sewing_terminal_v1(jsonb,uuid)'
BLOCKERS='erp.period_blockers_v1(date,date)'
FACADE='cp7_payroll.apply_settlement(text,jsonb,text)'
NATIVE_SIGNATURES=(CREATE,VALIDATE,ACTIVATE,CANCEL,APPROVE,UNPAID,PAID,POLICY,SET_POLICY,JOURNAL,SEWING,BLOCKERS)
SIGNATURES=NATIVE_SIGNATURES+(FACADE,)
CLONES=(SCHEMA+'.native_create_carry_pool_v1(jsonb,uuid)',SCHEMA+'.native_validate_carry_pool_v1(uuid)')


def once(body,before,after,label):
    if body.count(before)!=1:raise ValueError('CP7_S03_NATIVE_ANCHOR:'+label)
    return body.replace(before,after,1)


def entry(body,code,label):
    # pg_get_functiondef keeps the original PL/pgSQL body text. Only the first
    # top-level BEGIN is used; no cached reply or row lock can precede this hook.
    marker='\nbegin\n'
    if marker not in body:raise ValueError('CP7_S03_NATIVE_BODY_BEGIN:'+label)
    index=body.index(marker)+len(marker)
    return body[:index]+code+body[index:]


def clones(originals):
    create=originals[CREATE]
    create=once(create,'FUNCTION erp.create_attendance_hpp_pool_v1(',
                'FUNCTION '+SCHEMA+'.native_create_carry_pool_v1(',CREATE+':private-name')
    create=once(create,"v_operation constant text := 'create_attendance_hpp_pool_v1';",
                "v_operation constant text := 'cp7_s03_native_create_carry_pool_v1';",CREATE+':request-operation')
    create=once(create,"array['period_start','period_end','reason'],",
                "array['period_start','period_end','reason','decision_id','output_start','output_end'],",CREATE+':required-fields')
    create=once(create,"array['period_start','period_end','reason','correction_of_pool_id'],",
                "array['period_start','period_end','reason','correction_of_pool_id','decision_id','output_start','output_end'],",CREATE+':allowed-fields')
    create=once(create,'v_preview := erp.preview_attendance_hpp_pool_v1(v_period_start, v_period_end);',
                "v_preview := cp7_attendance_choice.carry_preview_v1((p_payload->>'decision_id')::uuid,\n"
                "    erp._cp3_parse_canonical_date(p_payload->>'output_start','carry output_start'),\n"
                "    erp._cp3_parse_canonical_date(p_payload->>'output_end','carry output_end'));\n"
                "  if v_preview->'manifest'->>'period_start' is distinct from p_payload->>'period_start'\n"
                "     or v_preview->'manifest'->>'period_end' is distinct from p_payload->>'period_end' then\n"
                "    raise exception 'CP7_S03_NATIVE_SOURCE_PERIOD_MISMATCH';\n  end if;",CREATE+':explicit-two-period-preview')
    validate=originals[VALIDATE]
    validate=once(validate,'FUNCTION erp.validate_attendance_hpp_pool_v1(',
                  'FUNCTION '+SCHEMA+'.native_validate_carry_pool_v1(',VALIDATE+':private-name')
    validate=once(validate,'v_current_manifest := erp._build_attendance_hpp_manifest_v1(v_pool.period_start, v_pool.period_end);',
                  'v_current_manifest := cp7_attendance_choice.pool_manifest_v1(v_pool.id);',VALIDATE+':carry-manifest')
    validate=once(validate,'perform erp._assert_attendance_hpp_manifest_v1(v_current_manifest);',
                  'perform cp7_attendance_choice.assert_carry_manifest_v1(v_current_manifest);',VALIDATE+':carry-assertion')
    validate=once(validate,'or erp._cp3_business_date(e.physical_at) not between v_pool.period_start and v_pool.period_end',
                  "or erp._cp3_business_date(e.physical_at) not between\n"
                  "        (select a.output_start from cp7_attendance_choice.allocations_v1 a where a.pool_id=v_pool.id) and\n"
                  "        (select a.output_end from cp7_attendance_choice.allocations_v1 a where a.pool_id=v_pool.id)",VALIDATE+':separate-output-range')
    return dict(zip(CLONES,(create,validate)))


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('CP7_S03_NATIVE_FUNCTION_SET')
    if any('cp7_attendance_choice' in value for value in originals.values()):raise ValueError('CP7_S03_ALREADY_PATCHED')
    result=dict(originals)
    result[VALIDATE]=entry(result[VALIDATE],
        "  if exists(select 1 from cp7_attendance_choice.allocations_v1 a where a.pool_id=p_pool_id)then\n"
        "    return cp7_attendance_choice.native_validate_carry_pool_v1(p_pool_id);\n  end if;\n",VALIDATE)
    result[ACTIVATE]=once(result[ACTIVATE],"'ATTENDANCE_HPP_POOL', v_pool.id, v_pool.period_end,",
        "'ATTENDANCE_HPP_POOL', v_pool.id, cp7_attendance_choice.pool_date_v1(v_pool.id,v_pool.period_end),",ACTIVATE+':journal-date')
    result[CANCEL]=entry(result[CANCEL],
        '  perform cp7_attendance_choice.assert_cancel_context_v1(p_pool_id,p_reason,p_client_request_id,p_expected_version);\n',CANCEL)
    for signature,period in((CREATE,'v_period_start, v_period_end'),(APPROVE,'p.period_start,p.period_end')):
        anchor='perform erp._cp3_lock_business_period('+period+');'
        result[signature]=once(result[signature],anchor,anchor+'\n  perform cp7_attendance_choice.assert_period_unclaimed_v1('+period+');',signature+':period-claim')
    for signature in(UNPAID,PAID):
        anchor='perform erp._cp3_lock_business_period(p.period_start,p.period_end);'
        result[signature]=once(result[signature],anchor,anchor+'\n  perform cp7_attendance_choice.assert_payroll_unclaimed_v1(p.id);',signature+':payroll-claim')
    result[POLICY]=entry(result[POLICY],
        '  if cp7_attendance_choice.policy_consumed_v1(p_contractor_id,p_effective_from,p_next_effective_from)then return true;end if;\n',POLICY)
    anchor='if erp._cp3_r4_active_pool_affects_contractor(v_contractor_id,v_effective_from,v_next_from) then'
    result[SET_POLICY]=once(result[SET_POLICY],anchor,
        'perform cp7_attendance_choice.assert_policy_mutation_v1(v_contractor_id,v_effective_from,v_next_from);\n  '+anchor,SET_POLICY+':held-policy-before-write')
    anchor='  ) returning * into v_new;\n'
    result[SET_POLICY]=once(result[SET_POLICY],anchor,
        anchor+'  perform cp7_attendance_choice.assert_active_carry_bindings_v1(v_contractor_id);\n',SET_POLICY+':carry-policy-before-audit')
    anchor='return erp._idempotency_complete(v_operation, p_client_request_id, v_response);'
    result[SET_POLICY]=once(result[SET_POLICY],anchor,
        'perform cp7_attendance_choice.assert_held_bindings_v1(v_contractor_id);\n  '+anchor,SET_POLICY+':held-policy-after-write')
    result[JOURNAL]=entry(result[JOURNAL],
        '  perform cp7_attendance_choice.assert_journal_unowned_v1(p_journal_entry_id);\n',JOURNAL)
    # Recalculate updates the payroll even when its economic totals stay equal;
    # retained bump/audit triggers therefore allocate before a later refusal.
    # Match Native row->period order and repeat Native authority after the wait.
    # The original recalculate/status/source and later period checks all remain.
    anchor='  perform erp.recalculate_payroll(p_payroll_id);'
    result[APPROVE]=once(result[APPROVE],anchor,
        "  select * into p from erp.payroll_settlements where id=p_payroll_id for update;\n"
        "  if p.id is not null then\n"
        "    perform erp._cp3_lock_business_period(p.period_start,p.period_end);\n"
        "    perform erp.require_owner_admin();\n"
        "    perform cp7_attendance_choice.assert_period_unclaimed_v1(p.period_start,p.period_end);\n"
        "  end if;\n"+anchor,APPROVE+':before-audited-recalculate')
    # Public APPROVE rebuilds nonwork before calling Native APPROVE. Fence this
    # existing owning facade after its raw-contractor lock, preserving that
    # order used by CANCEL/REVERSE, and before any child/source rebuild DML.
    # PREPARE/PAY/CANCEL/REVERSE and E05 individual settlement are unchanged.
    anchor=' perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text,0));'
    result[FACADE]=once(result[FACADE],anchor,anchor+
        "\n if p_action='APPROVE' then\n"
        "  perform erp._cp3_lock_business_period(p.period_start,p.period_end);\n"
        "  if cp7_payroll.settlement_access(p_action) is distinct from a then\n"
        "   raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_CHANGED';end if;\n"
        "  perform cp7_attendance_choice.assert_period_unclaimed_v1(p.period_start,p.period_end);\n"
        " end if;",FACADE+':approve-before-audited-rebuild')
    anchor='perform erp._cp3_lock_business_date(erp._cp3_business_date(v_work.physical_at));'
    result[SEWING]=once(result[SEWING],anchor,anchor+'\n  perform cp7_attendance_choice.assert_output_unclaimed_v1(v_work.physical_at);',SEWING+':carried-output-period')
    result[BLOCKERS]=once(result[BLOCKERS],
        'return query select * from cp7_hpp_close.blockers_v1(p_through);',
        'return query select * from cp7_attendance_choice.blockers_v1(p_through);',BLOCKERS+':owner-policy-successor')
    return result
