"""CP1–CP7 audit fixes on dated balances: cash never negative on the economic or the book date (D14-3, D15-1;
compound corrections judged on their end state, Sol SOL-R1-001) and laundry
claim settlement never before its source or the vendor's dated payable (FIN02).
cp7_guard.findings() lists rows already in the books that these rules (and the payroll
payment-date guard) would refuse today, for the installer/auditor; nobody else may run it.

Installed last in the F03 composition. The accepted native writers keep their
exact definitions; the guards are triggers on the native rows every writer touches.
Uninstall drops role cp7_guard, whose schema cascade removes both triggers.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROLE='cp7_guard'
RULES={'min_debit_balance_from':('postgres',True,'s'),'min_debit_balance_by_book_from':('postgres',True,'s'),
       'min_vendor_ap_from':('postgres',True,'s'),'check_cash':('postgres',True,'s'),
       'begin_compound':('postgres',True,'v'),'end_compound':('postgres',True,'v'),'compound_closed':('postgres',True,'v'),
       'guard_cash_line':('postgres',True,'v'),'guard_laundry_claim_date':('postgres',True,'v'),
       'laundry_claim_floor':('postgres',True,'s'),'findings':('postgres',True,'s')}
TRIGGERS={('cp7_guard_cash_not_negative','journal_lines'),('cp7_guard_laundry_claim_date','laundry_claims'),
          ('cp7_guard_compound_closed','compound_scope')}
# Compound scope (D15-1, Sol SOL-R1-001): private tables, no grants beyond the owner.
TABLES=('compound_scope','compound_touch')

def extension():return (ROOT/'scripts/cp7-src/finance/dated-guards.sql').read_text()

def verify(cur):
    got=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_guard'").fetchall()
    assert {r[0] for r in got}==set(RULES),('CP7_GUARD_FUNCTIONS',got)
    for name,owner,secdef,vol,config in got:assert (owner,secdef,vol)==RULES[name] and config==['search_path=""'],(name,owner,secdef,vol,config)
    triggers=set(cur.execute("select t.tgname,c.relname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_guard' and t.tgenabled='O'").fetchall())
    assert triggers==TRIGGERS,('CP7_GUARD_TRIGGERS',triggers)
    for who in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_schema_privilege(%s,'cp7_guard','USAGE')",(who,)).fetchone()[0],('CP7_GUARD_SCHEMA',who)
        for name in RULES:
            sig=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_guard' and p.proname=%s",(name,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0],('CP7_GUARD_EXECUTE',who,name)
    for table in TABLES:
        owner=cur.execute("select pg_get_userbyid(c.relowner) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_guard' and c.relname=%s",(table,)).fetchone()
        assert owner==('postgres',),('CP7_GUARD_TABLE_OWNER',table,owner)
        for who in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT') or has_table_privilege(%s,%s,'INSERT') or has_table_privilege(%s,%s,'DELETE')",
                                   (who,'cp7_guard.'+table)*3).fetchone()[0],('CP7_GUARD_TABLE',who,table)
    deferred=cur.execute("select t.tgdeferrable,t.tginitdeferred from pg_trigger t where t.tgname='cp7_guard_compound_closed'").fetchone()
    assert deferred==(True,True),('CP7_GUARD_COMPOUND_BACKSTOP',deferred)
    return dict(cp7_guard_functions=sorted(RULES),cp7_guard_triggers=sorted(TRIGGERS),cp7_guard_tables=list(TABLES))
