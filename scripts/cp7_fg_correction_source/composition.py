"""OW-08b stage (D17-13 2.21) over the kasbon stage: FG corrections reachable and explained from QC.

The transaction-source reader (already extended by OW06 and the kasbon stage) follows an FG inverse to every
finished-goods family it already opens. erp.reverse_qc and the QC workspace keep every refusal condition and first
sentence and name the blocking documents and their menus. The three functions get the counted delta of
native_delta.py, each replaced as its exact existing owner; one private schema with two readers (postgres only) is
added. No table, trigger, grant, writer or business row changes, so removal before use restores the exact predecessor.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_kasbon_source import composition as predecessor
from cp7_fg_correction_source import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_fg_correction_source'
READERS=('cp7_fg_correction_source.qc_blockers_v1(uuid)','cp7_fg_correction_source.qc_blocker_text_v1(uuid)')
ROLES=('anon','authenticated','service_role','cp7_capture','cp7_transaction_source_read')
OWNERS={native_delta.SOURCE:'cp7_transaction_source_read',native_delta.REVERSE:'postgres',native_delta.WORKSPACE:'postgres'}
catalog=predecessor.catalog
atomic=predecessor.atomic
function_ddl=predecessor.predecessor.function_ddl  # OW06: replace the reader as its own owner
as_owner=predecessor.predecessor.predecessor.predecessor.payment.consumer.as_owner
base=predecessor.predecessor.predecessor.predecessor.base  # chain interface (OW-15): catalog, atomic, as_owner, base, function_ddl
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('fg_correction.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW08B_FG_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None and((group=='schemas'and key==SCHEMA)or(group=='functions'and key in READERS)):continue
            raise ValueError('OW08B_FG_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def replace(cur,signature,definition,captured):
    """Inside as_owner(postgres): the reader through OW06's verified owner switch, erp functions as postgres itself."""
    if signature==native_delta.SOURCE:
        with function_ddl(cur,signature,captured):cur.execute(definition,prepare=False)
    else:
        cur.execute(definition,prepare=False)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW08B_FG_SCHEMA_ALREADY_EXISTS')
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        if owners!=OWNERS or before['schemas']['erp'][0]!='postgres':raise ValueError('OW08B_FG_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        native_delta.require_downstream(before['functions'][native_delta.DOWNSTREAM][0])
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((ROOT/'fg_correction.sql').read_text(),prepare=False)
            for signature,definition in definitions.items():replace(cur,signature,definition,before)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/'fg_correction.sql').read_text()))
        if names!={r.split('(')[0]for r in READERS}or set(after['functions'])-set(before['functions'])!=set(READERS):
            raise ValueError('OW08B_FG_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions)
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW08B_FG_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW08B_FG_FUNCTION_NOT_PATCHED: '+sig)
    for reader in READERS:
        owner,definer,volatile,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(reader,)).fetchone()
        if owner!='postgres'or not definer or volatile!='s'or 'search_path=""'not in(config or()):
            raise ValueError('OW08B_FG_READER_AUTHORITY_CHANGED: '+reader)
        for role in ROLES:
            if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,reader)).fetchone()[0]:
                raise ValueError('OW08B_FG_PRIVATE_READER_EXPOSED: '+role+':'+reader)
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW08B_FG_PRIVATE_SCHEMA_EXPOSED: '+role)
    return dict(status='OW08B_FG_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        changed_functions=list(native_delta.SIGNATURES),new_private_readers=list(READERS),
        fg_inverse_families_opened=native_delta.FAMILIES,fg_families_still_unsupported=list(native_delta.UNSUPPORTED),
        refusal_conditions_changed=False,business_tables_triggers_grants_or_writers_changed=False,
        OW08b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No row belongs to this stage; the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        with as_owner(cur,'postgres'):
            for signature,original in state['originals'].items():replace(cur,signature,original,state['before'])
            for reader in reversed(READERS):cur.execute('drop function '+reader)
            cur.execute('drop schema '+SCHEMA)
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW08B_FG_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW08B_FG_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
