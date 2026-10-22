"""Source-owned OW05 stage; never project old definitions into a verifier.

The current OW04 owner is verified before this extension. Every one of the 22
catalog groups is captured and subsequent checks require exact equality.
Only the Native pickup writer has a declared forward delta. Its old rejection
still applies except to this command's private, current-transaction capability.
"""
from hashlib import sha256
from pathlib import Path
from contextlib import contextmanager
import re
from psycopg.pq import TransactionStatus

import cp7_payment_source_owning_install as predecessor

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_contractor_correction'
TABLES = ('requests_v1', 'history_v1', 'context_v1')
NATIVE = 'erp.save_cutting_pickup_v1(jsonb,uuid,bigint)'
REVISION = 'cp7_cutting_correction.sewing_revision(uuid,uuid,numeric,uuid,timestamp with time zone,uuid)'
REVISION_TABLE = 'cp7_cutting_correction.rate_revisions'
REVISION_KEY = 'rate_revisions_original_snapshot_id_basis_at_key'
REVISION_INDEX = 'cp7_cutting_correction.'+REVISION_KEY
OLD_UNIQUE = 'UNIQUE (original_snapshot_id, basis_at)'
NEW_UNIQUE = 'UNIQUE NULLS NOT DISTINCT (original_snapshot_id, basis_at, mandor_generation)'
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


def patched_revision(original):
    replacements = (
        ('  where r.original_snapshot_id=p_original and r.basis_at=p_basis;',
         '  where r.original_snapshot_id=p_original and r.basis_at=p_basis\n'
         '   and r.mandor_generation is not distinct from cp7_contractor_correction.generation_v1(o.po_id);'),
        ('insert into cp7_cutting_correction.rate_revisions(snapshot_id,original_snapshot_id,po_id,basis_at,actor,request_id)',
         'insert into cp7_cutting_correction.rate_revisions(snapshot_id,original_snapshot_id,po_id,basis_at,actor,request_id,mandor_generation)'),
        ('values(v_id,p_original,o.po_id,p_basis,auth.uid(),p_request);',
         'values(v_id,p_original,o.po_id,p_basis,auth.uid(),p_request,cp7_contractor_correction.generation_v1(o.po_id));'),
    )
    for anchor, change in replacements:
        if original.count(anchor) != 1:
            raise ValueError('OW05_RATE_REVISION_PREDECESSOR_SOURCE_CHANGED')
        original = original.replace(anchor, change, 1)
    return original


@contextmanager
def revision_schema_ddl(cur):
    """Temporary installer CREATE, revoked before any installed state is exposed.

    The old schema belongs to cp7_cutting_read. Its table/function owner
    postgres has USAGE, but CREATE INDEX (including UNIQUE) also needs schema
    CREATE. No browser/service/capture role receives an additional privilege.
    An error rolls the grant back with the enclosing atomic install/uninstall.
    """
    actor, owner, acl, allowed = cur.execute("""select current_user,pg_get_userbyid(n.nspowner),n.nspacl::text,
        has_schema_privilege(current_user,n.oid,'CREATE')from pg_namespace n
        where n.nspname='cp7_cutting_correction'""").fetchone()
    if actor != 'postgres' or owner != 'cp7_cutting_read':
        raise ValueError('OW05_REVISION_SCHEMA_INSTALLER_AUTHORITY_CHANGED')
    if not allowed:
        cur.execute('set local role cp7_cutting_read')
        cur.execute('grant create on schema cp7_cutting_correction to postgres')
        cur.execute('set local role postgres')
    try:
        yield
    finally:
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            if not allowed:
                cur.execute('set local role cp7_cutting_read')
                cur.execute('revoke create on schema cp7_cutting_correction from postgres')
                cur.execute('set local role postgres')
            if cur.execute("select nspacl::text from pg_namespace where nspname='cp7_cutting_correction'").fetchone()[0] != acl:
                raise ValueError('OW05_REVISION_SCHEMA_ORIGINAL_ACL_NOT_RESTORED')


def _admit(before, after, definitions, functions):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW05_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if group == 'functions' and key in definitions and new[0] == definitions[key] and old[1:] == new[1:]:
                continue
            if group == 'constraints' and key == REVISION_TABLE+':'+REVISION_KEY \
                    and old[:-1] == new[:-1] and old[-1] == OLD_UNIQUE and new[-1] == NEW_UNIQUE:
                continue
            if group == 'indexes' and key == REVISION_INDEX and old[1:] == new[1:] \
                    and new[0] == old[0].replace('(original_snapshot_id, basis_at)',
                        '(original_snapshot_id, basis_at, mandor_generation) NULLS NOT DISTINCT'):
                continue
            if group == 'columns' and key in (REVISION_TABLE+':mandor_generation',REVISION_INDEX+':mandor_generation') and old is None:
                parent=key.split(':')[0]
                template=list(before['columns'][parent+(':actor'if parent==REVISION_TABLE else':original_snapshot_id')])
                template[0]='mandor_generation'
                template[1]=1+sum(k.startswith(parent+':')for k in before['columns'])
                template[3]=False
                if new == template:
                    continue
            if old is not None or new is None:
                raise ValueError('OW05_UNDECLARED_EXISTING_DELTA: '+group+':'+key)
            if group == 'functions' and key in functions:
                continue
            if group == 'schemas' and key == SCHEMA:
                continue
            if group in ('relations', 'columns', 'indexes', 'sequences', 'sequence_ownership') and(
                    key in (SCHEMA+'.history_v1_generation_no_key',SCHEMA+'.history_v1_generation_no_seq')
                    or key.startswith(SCHEMA+'.history_v1_generation_no_key:')
                    or key.startswith(SCHEMA+'.history_v1_generation_no_seq:')):
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
        # Preserve the exact definitions from the already verified full capture.
        originals = {sig:before['functions'][sig][0] for sig in (NATIVE,REVISION)}
        definitions = {NATIVE:patched(originals[NATIVE]),REVISION:patched_revision(originals[REVISION])}
        if before['constraints'][REVISION_TABLE+':'+REVISION_KEY][-1] != OLD_UNIQUE:
            raise ValueError('OW05_RATE_REVISION_UNIQUENESS_SOURCE_CHANGED')
        with predecessor.payment.consumer.as_owner(cur, 'postgres'):
            cur.execute((ROOT/'contractor.sql').read_text(), prepare=False)
            with revision_schema_ddl(cur):
                cur.execute('alter table '+REVISION_TABLE+' add column mandor_generation uuid')
                cur.execute('alter table '+REVISION_TABLE+' drop constraint '+REVISION_KEY)
                cur.execute('alter table '+REVISION_TABLE+' add constraint '+REVISION_KEY+' '+NEW_UNIQUE)
                for definition in definitions.values():
                    cur.execute(definition, prepare=False)
        after = predecessor.catalog._catalog_rows(cur)
        functions = set(after['functions']) - set(before['functions'])
        names = set(re.findall(r'create function ([a-z_0-9.]+)\(', (ROOT/'contractor.sql').read_text()))
        if {sig.split('(')[0] for sig in functions} != names or len(functions) != len(names):
            raise ValueError('OW05_FUNCTION_SET_CHANGED')
        _admit(before, after, definitions, functions)
        state = dict(sources=sources(), predecessor=previous, predecessor_proof=proof,
            before=before, after=after, originals=originals, new_functions=sorted(functions),
            seeded_private_rows=predecessor.base.private_rows(cur))
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
        rate_revision_assignment_generation=REVISION,
        Native_financial_writers_unchanged=True, Native_trigger_attachments_unchanged=True,
        production_go=False, formal_CP7C_started=False, independent_acceptance=False)


def rollback_preuse(cur, state):
    with predecessor.atomic(cur):
        verify(cur, state)
        for table in TABLES:
            cur.execute('lock table '+SCHEMA+'.'+table+' in access exclusive mode')
        if predecessor.base.private_rows(cur) != state['seeded_private_rows']:
            raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
        with predecessor.payment.consumer.as_owner(cur,'postgres'), revision_schema_ddl(cur):
            for original in state['originals'].values():
                cur.execute(original, prepare=False)
            cur.execute('alter table '+REVISION_TABLE+' drop constraint '+REVISION_KEY)
            cur.execute('alter table '+REVISION_TABLE+' add constraint '+REVISION_KEY+' '+OLD_UNIQUE)
            cur.execute('alter table '+REVISION_TABLE+' drop column mandor_generation')
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
