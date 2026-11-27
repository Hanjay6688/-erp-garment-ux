"""Install the audited HPP and attendance hooks on the managed credit release."""

from hashlib import sha256
from pathlib import Path

from psycopg.pq import TransactionStatus

from cp7_enteng_managed_credit_corrections import temporary_roles
from cp7_enteng_managed_identity import require
import cp7_enteng_managed_payroll_identity as payroll
import cp7_ow04_restore_bundle as catalog
from cp7_hpp_close import composition as hpp
from cp7_s03_sku_composition import catalog_contract as choice
from cp7_s03_sku_composition import installer_ddl, native_delta


SCRIPTS = Path(__file__).resolve().parent
PINNED = {
    'cp7_hpp_close/hpp_close.sql': '05a2526c1666a825be1108202af142ad95559c7fb0a288af43f72c5d1c160480',
    'cp7_hpp_close/native_delta.py': '25f0769977070acfa641929d8310e4fae42ce0a69fc953472efa68699b4c05ea',
    'cp7_s03_sku_composition/choice.sql': '44499c6d6a06d1effc2be4f066168f5fa2fe9608b2ccb80d1d2d0b1dac0a8212',
    'cp7_s03_sku_composition/readers.sql': '4ab82ff58033f4357251930504e6e9e75ecce9d8f1cc5b4e10f689940ce749e2',
    'cp7_s03_sku_composition/native_delta.py': 'a49242327798a59407739c2999fcf92408aeef9d88a1ae94fccc82bd189ac9ce',
    'cp7_s03_sku_composition/catalog_contract.py': 'f312de61b3c75087a51d7df712896627c02bb5d6473803bf6d2c90ad506d7c64',
    'cp7_s03_sku_composition/NEW_CATALOG_IDENTITIES.json': 'e49e4cb9c794d6ed98b831ae318e6d3c401a110d420cf932ee7011f7c971a578',
}
CALLERS = ('anon', 'authenticated', 'service_role')


def verify_sources():
    for name, expected in PINNED.items():
        require(sha256((SCRIPTS / name).read_bytes()).hexdigest() == expected,
                'Attendance source differs from reviewed input: ' + name)


def original_definitions(snapshot, signatures):
    routines = snapshot['functions']
    require(all(sig in routines and routines[sig][1] == 'postgres' for sig in signatures),
            'Attendance predecessor routines are missing or have a different owner')
    return {sig: routines[sig][0] for sig in signatures}


def verify_access(cur):
    roles = [row[0] for row in cur.execute("""
        select rolname from pg_roles where left(rolname,4)='cp7_' or rolname=any(%s)
    """, (list(CALLERS),)).fetchall()]
    schemas = (hpp.SCHEMA, choice.SCHEMA)
    for schema in schemas:
        require(not cur.execute("""
            select exists(select from unnest(%s::text[]) r where has_schema_privilege(r,%s,'USAGE,CREATE'))
        """, (roles,schema)).fetchone()[0], 'Private attendance schema exposed: ' + schema)
    for table in choice.TABLES:
        require(cur.execute("select relowner::regrole::text,relrowsecurity from pg_class where oid=%s::regclass",
                            (table,)).fetchone() == ('postgres',True), 'Attendance table owner or RLS changed: ' + table)
        require(not cur.execute("""
            select exists(select from unnest(%s::text[]) r where
                has_table_privilege(r,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
        """, (roles,table)).fetchone()[0], 'Private attendance table exposed: ' + table)
    for sig in (*sorted(choice.declared_functions()),hpp.READER):
        require(cur.execute("select proowner::regrole::text from pg_proc where oid=%s::regprocedure",
                            (sig,)).fetchone() == ('postgres',), 'Attendance function owner changed: ' + sig)
        expected = ['authenticated'] if sig in choice.PUBLIC else []
        actual = cur.execute("select r from unnest(%s::text[]) r where has_function_privilege(r,%s,'EXECUTE') order by r",
                             (roles,sig)).fetchall()
        require([row[0] for row in actual] == expected, 'Unexpected attendance function callers: ' + sig)


def apply(cur):
    """Use the caller's release transaction after the managed credit corrections."""
    require(cur.connection.info.transaction_status == TransactionStatus.INTRANS,
            'An explicit attendance release transaction is required')
    require(cur.execute('select session_user,current_user,rolsuper from pg_roles where rolname=current_user').fetchone()
            == ('postgres','postgres',False), 'Managed postgres attendance installer required')
    verify_sources()
    with cur.connection.transaction():
        data = catalog._data(cur)
        before = catalog._catalog_rows(cur)
        require(not {hpp.SCHEMA,choice.SCHEMA}.intersection(before['schemas']), 'Attendance stage already installed')
        hpp_names = hpp.native_delta.SIGNATURES
        hpp_defs = hpp.native_delta.patched(original_definitions(before,hpp_names))
        cur.execute((hpp.ROOT/'hpp_close.sql').read_text(),prepare=False)
        for ddl in hpp_defs.values():
            cur.execute(ddl,prepare=False)
        after_hpp = catalog._catalog_rows(cur)
        hpp.admit_catalog(before,after_hpp,hpp_defs)

        originals = original_definitions(after_hpp,native_delta.SIGNATURES)
        definitions = native_delta.patched(originals)
        with temporary_roles(cur,tuple(sorted(installer_ddl.SCHEMAS.values()))), installer_ddl.existing_schema_ddl(cur):
            for name in ('choice.sql','readers.sql'):
                cur.execute((choice.HERE/name).read_text(),prepare=False)
            for ddl in native_delta.clones(originals).values():
                cur.execute(ddl,prepare=False)
            cur.execute('revoke all on all functions in schema ' + choice.SCHEMA + ' from public,anon,authenticated,service_role')
            for ddl in definitions.values():
                cur.execute(ddl,prepare=False)
        choice.transition(after_hpp,catalog._catalog_rows(cur),definitions)
        verify_access(cur)
        bound = payroll.apply(cur)
        after_data = catalog._data(cur)
        require(all(after_data.get(k) == v for k,v in data.items()), 'Attendance install changed existing records')
        return {'hpp_routines':len(hpp_defs),'attendance_routines':len(definitions),
                'new_attendance_rpc':len(choice.PUBLIC),'payroll_identity':bound,'production_go':False}
