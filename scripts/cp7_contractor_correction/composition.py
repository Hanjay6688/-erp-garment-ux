"""Source-owned OW05 stage; never project old definitions into a verifier.

The current OW04 owner is verified before this extension. Every one of the 22
catalog groups is captured and subsequent checks require exact equality.
Only the Native pickup writer has a declared forward delta. Its old rejection
still applies except to this command's private, current-transaction capability.
"""
from hashlib import sha256
from pathlib import Path
import re

import cp7_payment_source_owning_install as predecessor

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_contractor_correction'
TABLES = ('requests_v1', 'history_v1', 'context_v1')
NATIVE = 'erp.save_cutting_pickup_v1(jsonb,uuid,bigint)'
PUBLIC = ('public.erp_cp7_get_mandor_correction_v1(uuid)',
          'public.erp_cp7_correct_mandor_v1(jsonb,uuid)')
ANCHOR = '     or erp.cutting_group_has_downstream_after_pickup(v_group.id) then\n'
CHANGE = ('     or (erp.cutting_group_has_downstream_after_pickup(v_group.id)\n'
          '         and not cp7_contractor_correction.admitted_group_v1(v_group.id)) then\n')


def sources():
    return dict(composition_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        sql_sha256=sha256((ROOT/'contractor.sql').read_bytes()).hexdigest(),
        predecessor=predecessor.sources())


def patched(original):
    if original.count(ANCHOR) != 1:
        raise ValueError('OW05_NATIVE_PICKUP_SOURCE_CHANGED')
    return original.replace(ANCHOR, CHANGE, 1)


def _admit(before, after, native_definition, functions):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW05_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if group == 'functions' and key == NATIVE and new[0] == native_definition and old[1:] == new[1:]:
                continue
            if old is not None or new is None:
                raise ValueError('OW05_UNDECLARED_EXISTING_DELTA: '+group+':'+key)
            if group == 'functions' and key in functions:
                continue
            if group == 'schemas' and key == SCHEMA:
                continue
            if group in ('relations', 'columns', 'indexes') and any(
                key == SCHEMA+'.'+table+'_pkey' or key.startswith(SCHEMA+'.'+table+'_pkey:')
                for table in TABLES):
                continue
            if group in ('relations', 'columns', 'constraints', 'indexes', 'triggers',
                         'policies', 'types', 'type_implementation') and any(
                key == SCHEMA+'.'+table or key == SCHEMA+'.'+table+'[]'
                or key.startswith(SCHEMA+'.'+table+':') for table in TABLES):
                continue
            raise ValueError('OW05_UNDECLARED_NEW_OBJECT: '+group+':'+key)


def install(cur):
    with predecessor.atomic(cur):
        previous = predecessor.install(cur)
        proof = predecessor.verify(cur, previous)
        before = predecessor.catalog._catalog_rows(cur)
        original = cur.execute('select pg_get_functiondef(%s::regprocedure)', (NATIVE,)).fetchone()[0]
        expected = patched(original)
        with predecessor.payment.consumer.as_owner(cur, 'postgres'):
            cur.execute((ROOT/'contractor.sql').read_text(), prepare=False)
            cur.execute(expected, prepare=False)
        after = predecessor.catalog._catalog_rows(cur)
        functions = set(after['functions']) - set(before['functions'])
        names = set(re.findall(r'create function ([a-z_0-9.]+)\(', (ROOT/'contractor.sql').read_text()))
        if {sig.split('(')[0] for sig in functions} != names or len(functions) != len(names):
            raise ValueError('OW05_FUNCTION_SET_CHANGED')
        _admit(before, after, expected, functions)
        state = dict(sources=sources(), predecessor=previous, predecessor_proof=proof,
            before=before, after=after, original=original, new_functions=sorted(functions))
        verify(cur, state)
        return state


def verify(cur, state):
    if sources() != state['sources'] or predecessor.catalog._catalog_rows(cur) != state['after']:
        raise ValueError('OW05_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig in state['new_functions']:
        owner, secdef, config = cur.execute(
            'select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',
            (sig,)).fetchone()
        if owner != 'postgres' or not secdef or 'search_path=""' not in config:
            raise ValueError('OW05_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_capture'):
            allowed = role == 'authenticated' and sig in PUBLIC
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0] != allowed:
                raise ValueError('OW05_FUNCTION_EXECUTE_CHANGED: '+role+':'+sig)
    for name in TABLES:
        relation = SCHEMA+'.'+name
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',
                       (relation,)).fetchone() != ('postgres', True):
            raise ValueError('OW05_PRIVATE_TABLE_AUTHORITY_CHANGED')
        for role in ('anon', 'authenticated', 'service_role', 'cp7_capture'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                           (role, relation)).fetchone()[0]:
                raise ValueError('OW05_PRIVATE_TABLE_EXPOSED')
    return dict(status='OW05_EXACT_SOURCE_AND_22_CATALOG_GROUPS_VERIFIED',
        predecessor_verified_before_extension=True, Native_delta=NATIVE,
        Native_financial_writers_unchanged=True, Native_trigger_attachments_unchanged=True,
        production_go=False, formal_CP7C_started=False, independent_acceptance=False)


def rollback_preuse(cur, state):
    with predecessor.atomic(cur):
        verify(cur, state)
        for table in TABLES:
            cur.execute('lock table '+SCHEMA+'.'+table+' in access exclusive mode')
        if any(cur.execute('select count(*)from '+SCHEMA+'.'+table).fetchone()[0] for table in TABLES):
            raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
        cur.execute(state['original'], prepare=False)
        for sig in PUBLIC:
            cur.execute('drop function '+sig)
        # All 22 groups were checked above: the cascade can only remove this
        # source's three private tables and declared private functions.
        cur.execute('drop schema '+SCHEMA+' cascade')
        if predecessor.catalog._catalog_rows(cur) != state['before']:
            raise ValueError('OW05_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous = predecessor.verify(cur, state['predecessor'])
        removed = predecessor.rollback_preuse(cur, state['predecessor'])
        return dict(status='OW05_PREUSE_EXACT_RESTORE', predecessor_verified=previous,
                    predecessor_removed=removed, financial_facts_deleted=False, production_go=False)
