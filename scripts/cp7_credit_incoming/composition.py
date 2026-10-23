"""OW-04b slice C stage over cp7_credit_multi (slice B): followups -> A -> B -> C, one linear chain.

Step 2: seven installed slice B definitions get the counted delta of native_delta.py (C1-C7, C12), replaced as their
verified existing owner postgres; one private reader is added in one new schema (incoming.sql). No table, trigger, grant
on an existing object or business row changes, so removal before use restores the exact slice B definitions, then
slice B removes itself the same way. Cases, race and workflow are a later step.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_credit_multi import composition as predecessor
from cp7_credit_incoming import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_credit_incoming'
READERS=('cp7_credit_incoming.incoming_applied_v1(uuid)',)
ROLES=predecessor.ROLES
catalog=predecessor.catalog
atomic=predecessor.atomic
as_owner=predecessor.as_owner
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('incoming.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW04BC_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key in READERS)):continue
            raise ValueError('OW04BC_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW04BC_SCHEMA_ALREADY_EXISTS')
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        if set(owners.values())!={'postgres'}:raise ValueError('OW04BC_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        if originals!=previous['definitions']:raise ValueError('OW04BC_SLICE_B_DEFINITIONS_CHANGED')
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((ROOT/'incoming.sql').read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'incoming.sql').read_text()))
        if names!={sig.split('(')[0]for sig in READERS}or set(after['functions'])-set(before['functions'])!=set(READERS):
            raise ValueError('OW04BC_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions)
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW04BC_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    return dict(verify_objects(cur,state),status='OW04BC_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED')


def verify_objects(cur,state):
    """This stage's objects, then slice B, A and followups objects except the definitions this stage replaced."""
    if state['sources']!=sources():raise ValueError('OW04BC_INSTALLED_SOURCE_CHANGED')
    mine=set(state['definitions']);multi=state['predecessor'];remaining=multi['predecessor'];followups=remaining['predecessor']
    keep=lambda defs:{sig:text for sig,text in defs.items()if sig not in mine}
    lower=dict(multi,definitions=keep(multi['definitions']),
        predecessor=dict(remaining,predecessor=dict(followups,definitions=keep(followups['definitions']))))
    below=predecessor.verify_objects(cur,lower)
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW04BC_CREDIT_FUNCTION_NOT_PATCHED: '+sig)
    if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()[0]!='postgres':
        raise ValueError('OW04BC_SCHEMA_OWNER_CHANGED')
    for sig in READERS:
        owner,config=cur.execute('select pg_get_userbyid(proowner),proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or 'search_path=""'not in(config or()):raise ValueError('OW04BC_READER_AUTHORITY_CHANGED: '+sig)
        for role in ROLES:
            if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('OW04BC_PRIVATE_READER_EXPOSED: '+role+':'+sig)
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW04BC_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW04BC_EXACT_STAGE_OBJECTS_VERIFIED',lower_objects=below['status'],
        changed_credit_functions=list(native_delta.SIGNATURES),new_private_readers=list(READERS),
        U_from='cp7_credit_incoming.incoming_applied_v1',native_empty_direct_route_C8_unchanged=True,OW04b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No business row belongs to this stage; the slice B definitions come back exactly, then slice B removes itself."""
    with atomic(cur):
        verify(cur,state)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            for sig in reversed(READERS):cur.execute('drop function '+sig)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW04BC_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW04BC_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
