"""OW-05b stage over the qualified fgqc stage (OW-15 chain: OW05, OW06, kasbon, fgqc): correction guidance and history.

Two installed OW05 readers get the counted delta of native_delta.py and four private
readers are added. No table, trigger, grant or business row changes, so removal before
use restores the exact predecessor. The OW05 command, its review-token rule and its
history rows are not touched. Neither OW06, the kasbon stage nor fgqc changes the two OW05 readers, so the
counted delta applies to the same text as over OW05 alone.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_fg_correction_source import composition as predecessor
from cp7_contractor_guidance import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_contractor_guidance'
READERS=('cp7_contractor_guidance.guide_v1(jsonb)','cp7_contractor_guidance.after_step_v1()',
         'cp7_contractor_guidance.after_steps_v1()','cp7_contractor_guidance.history_v1(uuid)')
DEFINERS=('cp7_contractor_guidance.guide_v1(jsonb)','cp7_contractor_guidance.history_v1(uuid)')
ROLES=('anon','authenticated','service_role','cp7_capture')
catalog=predecessor.catalog
atomic=predecessor.atomic
as_owner=predecessor.as_owner
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('guidance.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW05B_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key in READERS)):continue
            raise ValueError('OW05B_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW05B_SCHEMA_ALREADY_EXISTS')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        if set(owners.values())!={'postgres'}:raise ValueError('OW05B_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((ROOT/'guidance.sql').read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'guidance.sql').read_text()))
        if names!={r.split('(')[0]for r in READERS}or set(after['functions'])-set(before['functions'])!=set(READERS):
            raise ValueError('OW05B_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions,seeded_private_rows=predecessor.base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW05B_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW05B_NATIVE_FUNCTION_NOT_PATCHED: '+sig)
    for reader in READERS:
        owner,definer,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(reader,)).fetchone()
        if owner!='postgres'or definer!=(reader in DEFINERS)or 'search_path=""'not in(config or()):
            raise ValueError('OW05B_READER_AUTHORITY_CHANGED: '+reader)
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        for reader in READERS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,reader)).fetchone()[0]:
                raise ValueError('OW05B_PRIVATE_READER_EXPOSED: '+role+':'+reader)
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW05B_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW05B_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        changed_OW05_readers=list(native_delta.SIGNATURES),new_private_readers=list(READERS),guided_kinds=list(native_delta.KINDS),
        command_tables_triggers_or_grants_changed=False,OW05b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No row belongs to this stage; the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            for reader in READERS:cur.execute('drop function '+reader)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW05B_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW05B_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
