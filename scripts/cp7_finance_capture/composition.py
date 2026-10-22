"""OW-12a finance capture stage over the qualified OW05 product (isolated until the OW-15 linear integration).

One private schema (two tables, the capture job and three reads owned by the finance reader) plus counted substitutions
of four staged-report functions and the server runner, each replaced as its own existing owner. No business row,
Native writer or v1 path changes, so removal before use restores the exact predecessor.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import re

from psycopg import sql
from psycopg.pq import TransactionStatus

from cp7_contractor_correction import composition as predecessor
from cp7_finance_capture import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_finance_capture'
TABLES=('captures','chunks')
FINANCE_READER='cp7_finance_read'
READS=('cp7_finance_capture.report_unit(jsonb)',
       'cp7_finance_capture.book_chunk(text,date,text,integer,pg_snapshot)',
       'cp7_finance_capture.seal_hash(jsonb,text)')
ROLES=('anon','authenticated','service_role')
OWNER='cp7_capture'
DDL_ROLES={'postgres',OWNER}
catalog=predecessor.predecessor.catalog
atomic=predecessor.predecessor.atomic
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('finance_capture.sql','native_delta.py','composition.py')})


@contextmanager
def as_role(cur,role):
    if role not in DDL_ROLES:raise ValueError('OW12A_UNTRUSTED_DDL_ROLE')
    previous=cur.execute('select current_user').fetchone()[0]
    if previous not in DDL_ROLES:raise ValueError('OW12A_UNTRUSTED_INSTALLER_ROLE')
    if role!=previous:cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
    try:yield
    finally:
        if role!=previous and cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))


@contextmanager
def function_ddl(cur,signature,captured):
    """Replace as the function's verified existing owner, which also owns its schema (so no temporary grant)."""
    namespace=signature.split('.',1)[0]
    owner=captured['functions'][signature][1]
    schema_owner=cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(namespace,)).fetchone()[0]
    if owner!=OWNER or schema_owner!=OWNER:raise ValueError('OW12A_VERIFIED_EXISTING_OWNER_CHANGED: '+signature)
    with as_role(cur,owner):yield


def admit_catalog(before,after,definitions,new_functions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW12A_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is not None or new is None:raise ValueError('OW12A_UNDECLARED_EXISTING_DELTA: '+group+':'+key)
            if group=='functions'and key in new_functions:continue
            if group=='schemas'and key==SCHEMA:continue
            if group in('relations','columns','constraints','indexes','policies','types','type_implementation')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('OW12A_UNDECLARED_NEW_OBJECT: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:raise ValueError('OW12A_SCHEMA_ALREADY_EXISTS')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        definitions=native_delta.patched(originals)
        text=(ROOT/'finance_capture.sql').read_text()
        with as_role(cur,'postgres'):
            cur.execute(text,prepare=False)
            for signature,definition in definitions.items():
                with function_ddl(cur,signature,before):cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        functions=set(after['functions'])-set(before['functions'])
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',text))
        if {s.split('(')[0]for s in functions}!=names or len(names)!=len(functions)or set(READS)-functions:
            raise ValueError('OW12A_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions,functions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions,new_functions=sorted(functions))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW12A_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW12A_FUNCTION_NOT_PATCHED: '+sig)
    for sig in state['new_functions']:
        owner,definer,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        expected=FINANCE_READER if sig in READS else OWNER
        if owner!=expected or definer!=(sig in READS)or 'search_path=""'not in(config or()):
            raise ValueError('OW12A_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in ROLES:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('OW12A_PRIVATE_FUNCTION_EXPOSED: '+role+':'+sig)
    for role in ROLES:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('OW12A_PRIVATE_SCHEMA_EXPOSED: '+role)
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT')",(role,SCHEMA+'.'+table)).fetchone()[0]:
                raise ValueError('OW12A_PRIVATE_TABLE_EXPOSED: '+role+':'+table)
    for sig in READS:
        if not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(OWNER,sig)).fetchone()[0]:raise ValueError('OW12A_CAPTURE_CANNOT_READ: '+sig)
    return dict(status='OW12A_FINANCE_CAPTURE_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        changed_functions=list(native_delta.SIGNATURES),new_functions=state['new_functions'],
        reads_owned_by=FINANCE_READER,figures_from='cp7_finance.workspace (accepted owner report, one statement)',
        business_rows_or_writers_changed=False,OW12a_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """Refused once a capture exists; otherwise the exact predecessor comes back."""
    with atomic(cur):
        verify(cur,state)
        if cur.execute('select exists(select 1 from cp7_finance_capture.captures)').fetchone()[0]:raise ValueError('OW12A_USED_STATE_PRESENT')
        with as_role(cur,'postgres'):
            for signature,original in state['originals'].items():
                with function_ddl(cur,signature,state['before']):cur.execute(original,prepare=False)
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW12A_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW12A_FINANCE_CAPTURE_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
