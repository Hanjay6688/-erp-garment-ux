"""OW-04b stage over the qualified wash stage (which contains the OW04 credit product).

OW-15 chain: OW05, OW06, kasbon, fgqc, OW05b, OW08a, OW12a, OW-09, OW07, wash, then this stage (order change of
23 Oct). No stage below declares or changes any cp7_credit function this stage or slices A, B and C replace (each
one's 22-group catalog admission refuses any undeclared function change).

Three installed OW04 credit functions get the counted delta of native_delta.py (a DETAIL on three retained refusals),
replaced as their verified existing owner postgres; four private readers are added in one new schema. No table,
trigger, grant on an existing object or business row changes, so removal before use restores the exact predecessor.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_laundry_unknown_wash import composition as predecessor
from cp7_credit_followups import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_credit_followups'
READERS=('cp7_credit_followups.detail_v1(text,text,jsonb,jsonb)',
         'cp7_credit_followups.initial_family_reasons_v1(uuid,jsonb)',
         'cp7_credit_followups.correction_reasons_v1(uuid)',
         'cp7_credit_followups.source_mutation_reasons_v1(text,uuid)')
ROLES=('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write','cp7_credit_visible_read')
catalog=predecessor.catalog
atomic=predecessor.atomic
as_owner=predecessor.as_owner
base=predecessor.predecessor.base  # wash exports no base; its predecessor OW07 does (chain interface, OW-15)
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('followups.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW04B_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key in READERS)):continue
            raise ValueError('OW04B_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW04B_SCHEMA_ALREADY_EXISTS')
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        if set(owners.values())!={'postgres'}:raise ValueError('OW04B_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((ROOT/'followups.sql').read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'followups.sql').read_text()))
        if names!={sig.split('(')[0]for sig in READERS}or set(after['functions'])-set(before['functions'])!=set(READERS):
            raise ValueError('OW04B_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions,seeded_private_rows=base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW04B_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    return dict(verify_objects(cur,state),status='OW04B_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED')


def verify_objects(cur,state):
    """The stage's own objects: exact patched definitions, private readers and their authority."""
    if state['sources']!=sources():raise ValueError('OW04B_INSTALLED_SOURCE_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW04B_CREDIT_FUNCTION_NOT_PATCHED: '+sig)
    if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()[0]!='postgres':
        raise ValueError('OW04B_SCHEMA_OWNER_CHANGED')
    for sig in READERS:
        owner,config=cur.execute('select pg_get_userbyid(proowner),proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or 'search_path=""'not in(config or()):raise ValueError('OW04B_READER_AUTHORITY_CHANGED: '+sig)
        for role in ROLES:
            if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('OW04B_PRIVATE_READER_EXPOSED: '+role+':'+sig)
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW04B_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW04B_EXACT_STAGE_OBJECTS_VERIFIED',
        changed_credit_functions=list(native_delta.SIGNATURES),new_private_readers=list(READERS),
        refusal_conditions_or_messages_changed=False,business_tables_triggers_or_writers_changed=False,
        OW04b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No business row belongs to this stage; the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            for sig in reversed(READERS):cur.execute('drop function '+sig)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW04B_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW04B_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
