"""D14-6 kasbon tunai: CP7 facade (scripts/cp7-src/payroll/kasbon.sql) plus the declared Native deltas it needs.

Declared Native deltas, all forward and restored exactly on uninstall:
- erp.payroll_deductions constraint payroll_cash_advance_source_check: a CASH_ADVANCE deduction may come without an
  opening balance; the deferred trigger cp7_kasbon_deduction_linked then requires its kasbon link. Original
  definition captured and put back (fails, as it must, while kasbon deductions exist).
- erp.guard_opening_cash_advance_deduction_v1(): a CASH_ADVANCE row without an opening balance passes to the kasbon
  guard (cp7_kasbon.guard_deduction) instead of being refused as an opening allocation.
- erp.check_opening_cash_advance_payroll_v1(uuid): payroll approval/payment also checks its kasbon deductions.
- erp.run_v267_financial_truth_checks(): AP_CASH_ADVANCE_SOURCE accepts a lawful kasbon deduction.
Posting, payment, reversal and payroll recalculation stay the accepted Native definitions.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_kasbon_write', 'cp7_kasbon_read')
SCHEMA = 'cp7_kasbon'
TABLES = ('advances', 'deduction_links', 'requests', 'command_context')
CONSTRAINT = 'payroll_cash_advance_source_check'
CONSTRAINT_KEY = 'erp.payroll_deductions#' + CONSTRAINT
NEW_CONSTRAINT = ("check((deduction_type='CASH_ADVANCE' and contractor_issue_item_id is null and bs_resolution_id is null)"
                  " or (deduction_type<>'CASH_ADVANCE' and opening_cash_advance_balance_id is null))")
GUARD = 'erp.guard_opening_cash_advance_deduction_v1()'
CHECK = 'erp.check_opening_cash_advance_payroll_v1(uuid)'
TRUTH = 'erp.run_v267_financial_truth_checks()'
PATCHES = {
    GUARD: ("   if new.opening_cash_advance_balance_id is null and new.deduction_type<>'CASH_ADVANCE'\n",
            "   -- D14-6 kasbon (cp7_kasbon_bundle.py): a CASH_ADVANCE row without an opening balance is a kasbon deduction,\n"
            "   -- guarded by cp7_kasbon.guard_deduction and its deferred link check.\n"
            "   if new.opening_cash_advance_balance_id is null\n"),
    CHECK: ("   raise exception 'Hitung ulang payroll: total potongan harus cocok dan tidak boleh melebihi pendapatan';end if;\n",
            "   raise exception 'Hitung ulang payroll: total potongan harus cocok dan tidak boleh melebihi pendapatan';end if;\n"
            " -- D14-6 kasbon (cp7_kasbon_bundle.py): kasbon deductions are checked as well.\n"
            " perform cp7_kasbon.check_payroll(p.id);\n"),
    TRUTH: ("  where d.deduction_type='CASH_ADVANCE' and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'\n",
            "  where d.deduction_type='CASH_ADVANCE' and not cp7_kasbon.linked_ok(d.id) and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'\n"),
}


def patched(signature, definition):
    anchor, change = PATCHES[signature]
    assert definition.count(anchor) == 1, ('KASBON_NATIVE_SOURCE_CHANGED', signature)
    return definition.replace(anchor, change, 1)


def capture(cur, originals):
    for signature in PATCHES:
        assert signature not in originals, ('KASBON_NATIVE_ALREADY_CAPTURED', signature)
        originals[signature] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        patched(signature, originals[signature])
    definition = cur.execute("select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.payroll_deductions'::regclass and conname=%s",
                             (CONSTRAINT,)).fetchone()[0]
    assert 'opening_cash_advance_balance_id IS NOT NULL' in definition, ('KASBON_NATIVE_CONSTRAINT_CHANGED', definition)
    originals[CONSTRAINT_KEY] = ('alter table erp.payroll_deductions drop constraint ' + CONSTRAINT + ', add constraint ' + CONSTRAINT + ' '
                                 + definition)


def expected_definitions(originals):
    return {signature: patched(signature, originals[signature]) for signature in PATCHES}


def extension():
    blocks = []
    for n, (signature, (anchor, change)) in enumerate(PATCHES.items()):
        blocks.append("do $kasbon" + str(n) + "$\ndeclare definition text;\nbegin\n definition:=pg_get_functiondef('" + signature + "'::regprocedure);\n"
                      " if (length(definition)-length(replace(definition,$anchor$" + anchor + "$anchor$,'')))<>length($anchor$" + anchor + "$anchor$) then\n"
                      "  raise exception 'CP7_KASBON_NATIVE_SOURCE_CHANGED: %','" + signature + "';end if;\n"
                      " execute replace(definition,$anchor$" + anchor + "$anchor$,$changed$" + change + "$changed$);\nend $kasbon" + str(n) + "$;\n")
    constraint = ("do $kasbon_constraint$\nbegin\n"
                  " if not exists(select 1 from pg_constraint where conrelid='erp.payroll_deductions'::regclass and conname='" + CONSTRAINT + "'\n"
                  "  and pg_get_constraintdef(oid) like '%opening_cash_advance_balance_id IS NOT NULL%') then\n"
                  "  raise exception 'CP7_KASBON_NATIVE_CONSTRAINT_CHANGED';end if;\n"
                  " alter table erp.payroll_deductions drop constraint " + CONSTRAINT + ", add constraint " + CONSTRAINT + " " + NEW_CONSTRAINT + ";\n"
                  "end $kasbon_constraint$;\n")
    return ((ROOT / 'scripts/cp7-src/payroll/kasbon.sql').read_text() + '\n-- D14-6 declared Native deltas (cp7_kasbon_bundle.py).\n'
            + constraint + ''.join(blocks))


def verify(cur):
    for signature, (anchor, change) in PATCHES.items():
        definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert change in definition, ('KASBON_NATIVE_NOT_PATCHED', signature)
    constraint = cur.execute("select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.payroll_deductions'::regclass and conname=%s",
                             (CONSTRAINT,)).fetchone()[0]
    assert 'opening_cash_advance_balance_id IS NOT NULL' not in constraint, ('KASBON_CONSTRAINT_NOT_RELAXED', constraint)
    triggers = set(r[0] for r in cur.execute(
        "select t.tgname from pg_trigger t join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and not t.tgisinternal",
        (SCHEMA,)).fetchall())
    assert triggers == {'cp7_kasbon_deduction_guard', 'cp7_kasbon_deduction_linked', 'cp7_kasbon_journal_guard'}, triggers
    rows = cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",
                       (SCHEMA,)).fetchall()
    for sig, name, owner, secdef in rows:
        assert owner == 'postgres' and secdef, sig
        for who in ('anon', 'authenticated', 'service_role', 'cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        for who, allowed in (('cp7_kasbon_read', 'workspace'), ('cp7_kasbon_write', 'command')):
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (name == allowed), (who, sig)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolsuper,rolbypassrls from pg_roles where rolname=%s', (who,)).fetchone() == (False, False, False)
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE'))",
                               (who,)).fetchone()[0], who
    for table in TABLES:
        relation = SCHEMA + '.' + table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (relation,)).fetchone() == ('postgres', True)
        for who in ('anon', 'authenticated', 'service_role', 'cp7_capture') + ROLES:
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')", (who, relation)).fetchone()[0], (who, relation)
    for signature, owner in (('public.erp_cp7_get_kasbon_v1(uuid)', 'cp7_kasbon_read'), ('public.erp_cp7_save_kasbon_v1(text,jsonb,uuid,text)', 'cp7_kasbon_write')):
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef from pg_proc where oid=%s::regprocedure', (signature,)).fetchone() == (owner, True)
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (signature,)).fetchone()[0]
        assert not cur.execute("select has_function_privilege('anon',%s,'EXECUTE')", (signature,)).fetchone()[0]
    return dict(kasbon_facade=True, native_deltas=sorted(PATCHES) + [CONSTRAINT_KEY], deduction_row_shape_unchanged=True)
