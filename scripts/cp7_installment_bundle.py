"""E05: cash installments on one immutable native approved payroll.

Native approval, source reservations and dated journal posting remain authoritative.
The two derived private routines preserve the accepted settlement side effects.
The original native functions, guards, enum, owners and ACLs remain unchanged.
"""
import hashlib
import cp7_settlement_bundle as settlement

ROOT = settlement.ROOT
READ_GRANTS = ('auth.uid()', 'auth.jwt()', 'erp.get_my_access_v1()', 'erp.has_permission(text)')
WRITE_GRANTS = ('auth.uid()',)
NONCASH = "'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_CASH_ADVANCE_DEDUCTION'"


def replace_once(text, old, new):
    assert text.count(old) == 1, ('E05_NATIVE_DERIVATION_ANCHOR_CHANGED', old)
    return text.replace(old, new, 1)


def derive_payment():
    original = settlement.accepted('post_payroll_payment')
    final = replace_once(original, 'erp.post_payroll_payment(p_payroll_id uuid)',
                         'cp7_installment.final_payment(p_payroll_id uuid, p_cash_amount numeric)')
    final = replace_once(final, "SET search_path TO 'erp', 'public', 'pg_temp'",
                         "SET search_path TO ''\n SET TimeZone TO 'Asia/Jakarta'")
    final = replace_once(final, '  perform erp.require_internal();',
                         '  perform cp7_installment.require_context(p_payroll_id);\n'
                         '  perform erp.require_internal();')
    # Give every cash installment its own native source identity, including the
    # final installment. Reusing PAYROLL_PAYMENT/payroll_id would prevent a
    # replacement after an earlier installment is reversed while the old final
    # installment remains posted. Approved net and all non-cash settlement
    # formulas and source lifecycles remain unchanged.
    final = replace_once(final, "erp.post_journal('PAYROLL_PAYMENT',p.id,p.payment_date",
                         "erp.post_journal('PAYROLL_INSTALLMENT',(select c.native_payment_id "
                         "from cp7_installment.command_context c where c.backend_pid=pg_backend_pid() "
                         "and c.transaction_id=txid_current() and c.actor=auth.uid()),p.payment_date")
    for old, new in [('\'debit\',p.net_payable,\'credit\',0', "'debit',p_cash_amount,'credit',0"),
                     ("'debit',0,'credit',p.net_payable", "'debit',0,'credit',p_cash_amount")]:
        final = replace_once(final, old, new)
    anchor = "  select coalesce(sum(amount),0) into v_material_deduction"
    pos = final.index(anchor)
    final = final[:pos] + "  perform cp7_installment.assert_payment_amount(p.id,p_cash_amount,true);\n" + final[pos:]
    # Run the exact native pre-settlement source checks for early installments
    # too, without executing any deduction, paid transition or repeated cost.
    check = final[:final.index(anchor)]
    check = replace_once(check, 'cp7_installment.final_payment(p_payroll_id uuid, p_cash_amount numeric)',
                         'cp7_installment.check_payment(p_payroll_id uuid, p_cash_amount numeric)')
    check = replace_once(check, 'assert_payment_amount(p.id,p_cash_amount,true)',
                         'assert_payment_amount(p.id,p_cash_amount,false)')
    check += 'end;\n$function$\n'
    return check, final


def derive_reopen():
    original = settlement.accepted('reverse_paid_payroll')
    result = replace_once(original, 'erp.reverse_paid_payroll(p_payroll_id uuid, p_reason text)',
                          'cp7_installment.reopen_settlement(p_payroll_id uuid, p_reason text)')
    result = replace_once(result, "SET search_path TO 'erp', 'public', 'pg_temp'",
                          "SET search_path TO ''\n SET TimeZone TO 'Asia/Jakarta'")
    result = replace_once(result, '  perform erp.require_owner_admin();',
                          '  perform cp7_installment.require_context(p_payroll_id);')
    pool = """  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;
"""
    # Individual cash correction leaves the approval/accrual and HPP unchanged.
    # Whole-payroll reversal separately retains this native dependency guard.
    result = replace_once(result, pool, '')
    old_types = """'PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION',
                             'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION'"""
    result = replace_once(result, old_types, NONCASH)
    result = replace_once(result, "set status='REVERSED',settled_at=null", "set status='APPROVED',settled_at=null")
    result = replace_once(result, "'REVERSE_PAID',jsonb_build_object('previous_status','PAID')",
                          "'UPDATE',jsonb_build_object('previous_status','PAID','lifecycle_action','REOPEN_INSTALLMENT_SETTLEMENT','approved_cost_unchanged',true)")
    return result


def extension():
    before = {name: settlement.accepted(name) for name in
              ('post_payroll_payment', 'reverse_paid_payroll', 'cancel_unpaid_payroll')}
    guards = []
    signatures = {'post_payroll_payment': 'uuid', 'reverse_paid_payroll': 'uuid,text',
                  'cancel_unpaid_payroll': 'uuid,text'}
    for name, definition in before.items():
        digest = hashlib.sha256(definition.encode()).hexdigest()
        guards.append("if encode(extensions.digest(pg_get_functiondef('erp.%s(%s)'::regprocedure),'sha256'),'hex')<>'%s' then raise exception 'CP7_INSTALLMENT_NATIVE_PREDECESSOR_CHANGED';end if;" %
                      (name, signatures[name], digest))
    check, final = derive_payment()
    derived = '\n'.join((check+';', final+';', derive_reopen()+';'))
    sql = (ROOT/'scripts/cp7-src/payroll/installments.sql').read_text()
    assert sql.count('-- E05_DERIVED_NATIVE_ROUTINES') == 1
    return ('do $verify$ begin\n'+'\n'.join(guards)+'\nend $verify$;\n'+
            sql.replace('-- E05_DERIVED_NATIVE_ROUTINES', derived))


def verify(cur):
    expected = {
        'access_now': ('cp7_installment_read', True, 's', ['search_path=""']),
        'cash': ('cp7_installment_read', True, 's', ['search_path=""', 'TimeZone=UTC']),
        'meaning': ('cp7_installment_read', True, 's', ['search_path=""', 'TimeZone=UTC']),
        'require_context': ('cp7_installment_read', True, 's', ['search_path=""']),
        'guard_header': ('cp7_installment_read', True, 'v', ['search_path=""']),
        'guard_journal': ('cp7_installment_read', True, 'v', ['search_path=""']),
        'guard_child': ('cp7_installment_read', True, 'v', ['search_path=""']),
        'guard_line': ('cp7_installment_read', True, 'v', ['search_path=""']),
        'assert_payment_amount': ('cp7_installment_read', True, 's', ['search_path=""']),
        'check_payment': ('postgres', True, 'v', ['search_path=""', 'TimeZone=Asia/Jakarta']),
        'final_payment': ('postgres', True, 'v', ['search_path=""', 'TimeZone=Asia/Jakarta']),
        'reopen_settlement': ('postgres', True, 'v', ['search_path=""', 'TimeZone=Asia/Jakarta']),
        'source': ('cp7_installment_read', True, 's', ['search_path=""', 'TimeZone=UTC']),
        'workspace': ('cp7_installment_read', False, 's', ['search_path=""', 'TimeZone=UTC']),
        'validate': ('cp7_installment_read', False, 'i', ['search_path=""']),
        'apply_command': ('postgres', True, 'v', ['search_path=""', 'TimeZone=Asia/Jakarta']),
        'command': ('cp7_installment_write', False, 'v', ['search_path=""']),
    }
    rows = cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_installment'").fetchall()
    assert {r[0] for r in rows} == set(expected)
    for name, *metadata in rows:
        assert tuple(metadata) == expected[name], (name, metadata)
    for sig, owner, vol in [('public.erp_cp7_get_payroll_installments_v1(jsonb)', 'cp7_installment_read', 's'),
                            ('public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)', 'cp7_installment_write', 'v')]:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure', (sig,)).fetchone() == (owner, True, vol, ['search_path=""'])
    for role in ('cp7_installment_read', 'cp7_installment_write'):
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))", (role,)).fetchone()[0]
        for sig in ('erp.post_journal(text,uuid,date,text,jsonb)', 'erp.reverse_journal(uuid,text)', 'erp.post_payroll_payment(uuid)', 'erp.cancel_unpaid_payroll(uuid,text)', 'erp.reverse_paid_payroll(uuid,text)'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0], (role, sig)
    for who in ('anon', 'authenticated', 'service_role', 'cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_installment','USAGE')or has_function_privilege(%s,'cp7_installment.apply_command(text,jsonb,uuid,text)','EXECUTE')", (who, who)).fetchone()[0]
    assert cur.execute('select count(*)from cp7_installment.command_context').fetchone()[0] == 0
    for name in ('post_payroll_payment', 'reverse_paid_payroll', 'cancel_unpaid_payroll'):
        signature = name+'('+('uuid' if name=='post_payroll_payment' else 'uuid,text')+')'
        assert cur.execute('select pg_get_functiondef(%s::regprocedure)', ('erp.'+signature,)).fetchone()[0] == settlement.accepted(name)
    triggers = cur.execute("select t.tgname,c.relname,t.tgenabled from pg_trigger t join pg_class c on c.oid=t.tgrelid where t.tgname like 'cp7_installment_managed_%'").fetchall()
    assert set(triggers) == {(name, table, 'O') for name, table in [
        ('cp7_installment_managed_header', 'payroll_settlements'), ('cp7_installment_managed_journal', 'journal_entries'),
        ('cp7_installment_managed_line', 'journal_lines'), ('cp7_installment_managed_work', 'payroll_work_items'),
        ('cp7_installment_managed_attendance', 'payroll_attendance_items'), ('cp7_installment_managed_reimbursements', 'payroll_reimbursements'),
        ('cp7_installment_managed_deductions', 'payroll_deductions')]}
    return dict(immutable_approved_native_source=True,original_native_functions_unchanged=True,
                no_app_DML_native_writer_or_private_context=True,private_functions_owned=True)
