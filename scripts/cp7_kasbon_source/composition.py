"""OW-08b kasbon stage over the qualified OW06 product: a kasbon journal opens its kasbon from the ledger.

The transaction-source reader (already extended by OW06) gets the counted delta of native_delta.py, replaced as its
exact existing owner; one private document reader is added for that owner only. No table, trigger, writer or business
row changes, so removal before use restores the exact predecessor.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_supplier_transfer import composition as predecessor
from cp7_kasbon_source import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_kasbon_source'
READER='cp7_kasbon_source.document_v1(uuid)'
READER_ROLE='cp7_transaction_source_read'
ROLES=('anon','authenticated','service_role','cp7_capture')
catalog=predecessor.catalog
atomic=predecessor.atomic
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('kasbon_source.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW08B_KASBON_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key==READER)):continue
            raise ValueError('OW08B_KASBON_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW08B_KASBON_SCHEMA_ALREADY_EXISTS')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with predecessor.predecessor.predecessor.payment.consumer.as_owner(cur,'postgres'):
            cur.execute((ROOT/'kasbon_source.sql').read_text(),prepare=False)
            for signature,definition in definitions.items():
                with predecessor.function_ddl(cur,signature,before):cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'kasbon_source.sql').read_text()))
        if names!={READER.split('(')[0]}or set(after['functions'])-set(before['functions'])!={READER}:
            raise ValueError('OW08B_KASBON_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions)
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW08B_KASBON_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW08B_KASBON_READER_NOT_PATCHED: '+sig)
    owner,definer,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(READER,)).fetchone()
    if owner!='postgres'or not definer or 'search_path=""'not in(config or()):raise ValueError('OW08B_KASBON_READER_AUTHORITY_CHANGED')
    if not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(READER_ROLE,READER)).fetchone()[0]:
        raise ValueError('OW08B_KASBON_SOURCE_ROLE_CANNOT_READ')
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,READER)).fetchone()[0]:
            raise ValueError('OW08B_KASBON_PRIVATE_READER_EXPOSED: '+role)
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW08B_KASBON_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW08B_KASBON_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        changed_reader=list(native_delta.SIGNATURES),new_private_reader=READER,reader_granted_only_to=READER_ROLE,
        kasbon_tables_writers_or_journals_changed=False,OW08b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No row belongs to this stage; the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        with predecessor.predecessor.predecessor.payment.consumer.as_owner(cur,'postgres'):
            for signature,original in state['originals'].items():
                with predecessor.function_ddl(cur,signature,state['before']):cur.execute(original,prepare=False)
            cur.execute('drop function '+READER)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW08B_KASBON_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW08B_KASBON_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
