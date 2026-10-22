"""OW-08a stage over the complete qualified OW05 product: report checks know customer credit.

Two installed report check readers get the counted delta of native_delta.py and
one private reader is added. No table, trigger, writer, grant or business row
changes, so removal before or after use restores the exact predecessor.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_contractor_correction import composition as predecessor
from cp7_report_credit import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_report_credit'
READER='cp7_report_credit.adjustment_v1(uuid)'
OWNERS={native_delta.REPORT:'postgres',native_delta.SCOPE:'postgres'}
ROLES=('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_credit_visible_read')
catalog=predecessor.predecessor.catalog
atomic=predecessor.predecessor.atomic
as_owner=predecessor.predecessor.payment.consumer.as_owner
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('report_credit.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW08A_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key==READER)):continue
            raise ValueError('OW08A_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW08A_SCHEMA_ALREADY_EXISTS')
        for sig,owner in OWNERS.items():
            if before['functions'][sig][1]!=owner:raise ValueError('OW08A_VERIFIED_EXISTING_OWNER_CHANGED: '+sig)
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((ROOT/'report_credit.sql').read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'report_credit.sql').read_text()))
        if names!={READER.split('(')[0]}or set(after['functions'])-set(before['functions'])!={READER}:
            raise ValueError('OW08A_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions,seeded_private_rows=predecessor.predecessor.base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW08A_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW08A_REPORT_READER_NOT_PATCHED: '+sig)
    owner,definer,volatile,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(READER,)).fetchone()
    if owner!='postgres'or not definer or volatile!='s'or 'search_path=""'not in config:
        raise ValueError('OW08A_READER_AUTHORITY_CHANGED')
    for role in ROLES:
        if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,READER)).fetchone()[0]:
            raise ValueError('OW08A_PRIVATE_READER_EXPOSED: '+role)
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW08A_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW08A_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        Native_changed_functions=list(native_delta.SIGNATURES),new_private_reader=READER,
        business_tables_triggers_or_writers_changed=False,OW08_complete=False,production_go=False,
        independent_acceptance=False)


def rollback_preuse(cur,state):
    """No business row belongs to this stage; the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            cur.execute('drop function '+READER)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW08A_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW08A_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
