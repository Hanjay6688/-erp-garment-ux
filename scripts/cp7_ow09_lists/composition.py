"""OW-09 stage over the qualified OW05 product: sort and filter apply to the whole list in eight readers (D17-16).

Eight installed readers get the counted delta of native_delta.py and are replaced as their verified existing owners:
the CP7 read roles that own the seven CP7 readers and their schemas, and postgres for the CP6 accessory note reader.
No table, trigger, grant, row or function is added, so removal before use restores the exact predecessor. Every one
of the 22 catalog groups is captured; only these eight definitions may change.

The base CP7 SQL stays frozen (E25j2): scripts/cp7-src is not edited. The Native harness creates the CP7 roles as its
superuser, so postgres may lack SET on them; handover() then grants exactly SET+INHERIT on exactly the owner roles for
this transaction and revokes it before the catalog is read again (E25j, the OW-12a pattern).
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from psycopg import sql
from psycopg.pq import TransactionStatus

from cp7_contractor_correction import composition as predecessor
from cp7_ow09_lists import native_delta

ROOT=Path(__file__).resolve().parent
OWNERS=native_delta.OWNERS
ROLES=('anon','authenticated','service_role','cp7_capture')
BROWSER=('anon','authenticated','service_role')
catalog=predecessor.predecessor.catalog
atomic=predecessor.predecessor.atomic
# The verified installer switch to postgres (the harness admin role cannot run DDL itself), as the OW05b/OW07 stages.
as_owner=predecessor.predecessor.payment.consumer.as_owner
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()for name in('native_delta.py','composition.py')})


@contextmanager
def handover(cur):
    """SET+INHERIT for postgres on the existing CP7 owner roles, for this transaction only, when it is missing."""
    granted=[]
    for role in sorted(set(OWNERS.values())-{'postgres'}):
        if cur.execute("select pg_has_role('postgres',%s,'SET')and pg_has_role('postgres',%s,'USAGE')",(role,role)).fetchone()[0]:continue
        if not cur.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0]:
            raise ValueError('OW09_INSTALLER_CANNOT_HAND_OVER: '+role)
        cur.execute(sql.SQL('grant {} to postgres with inherit true, set true').format(sql.Identifier(role)));granted.append(role)
    try:yield granted
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            for role in granted:cur.execute(sql.SQL('revoke {} from postgres').format(sql.Identifier(role)))


@contextmanager
def as_role(cur,role):
    if role not in set(OWNERS.values()):raise ValueError('OW09_UNTRUSTED_DDL_ROLE')
    previous=cur.execute('select current_user').fetchone()[0]
    if previous!='postgres':raise ValueError('OW09_UNTRUSTED_INSTALLER_ROLE')
    if role!=previous:cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
    try:yield
    finally:
        if role!=previous and cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))


@contextmanager
def function_ddl(cur,signature):
    """Replace as the function's verified existing owner; a CP7 owner also owns the schema (so no temporary grant)."""
    owner=OWNERS[signature]
    actual,schema_owner,create=cur.execute("""select pg_get_userbyid(p.proowner),pg_get_userbyid(n.nspowner),has_schema_privilege(%s,n.oid,'CREATE')
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure""",(owner,signature)).fetchone()
    if actual!=owner or not create or(owner!='postgres'and schema_owner!=owner):
        raise ValueError('OW09_VERIFIED_EXISTING_OWNER_CHANGED: '+signature)
    with as_role(cur,owner):yield


def replace(cur,definitions):
    """Install the given definitions of the eight readers (install, removal, and the cases' side-by-side original reads)."""
    if set(definitions)!=set(native_delta.SIGNATURES):raise ValueError('OW09_NATIVE_DELTA_SET_CHANGED')
    with handover(cur),as_owner(cur,'postgres'):
        for signature in native_delta.SIGNATURES:
            with function_ddl(cur,signature):cur.execute(definitions[signature],prepare=False)


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW09_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None\
               and new[0]==definitions[key]and old[1:]==new[1:]:continue
            raise ValueError('OW09_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def access(cur):
    """Who may execute each private reader and its public wrapper: must stay exactly as before."""
    roles=[r for r in ROLES if cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(r,)).fetchone()[0]]
    return {role+':'+sig:cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]
            for role in roles for sig in(*native_delta.SIGNATURES,*native_delta.PUBLIC.values())}


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        if owners!=OWNERS:raise ValueError('OW09_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        allowed=access(cur)
        exposed=[k for k,v in allowed.items()if v and k.split(':',1)[0]in BROWSER and k.split(':',1)[1]in native_delta.SIGNATURES]
        if exposed:raise ValueError('OW09_PRIVATE_READER_EXPOSED: '+repr(exposed))
        definitions=native_delta.patched(originals)
        replace(cur,definitions)
        after=catalog._catalog_rows(cur)
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions,access=allowed)
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW09_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        owner,text=cur.execute('select pg_get_userbyid(proowner),pg_get_functiondef(oid)from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if text!=definition:raise ValueError('OW09_NATIVE_FUNCTION_NOT_PATCHED: '+sig)
        if owner!=OWNERS[sig]:raise ValueError('OW09_VERIFIED_EXISTING_OWNER_CHANGED: '+sig)
    if access(cur)!=state['access']:raise ValueError('OW09_READER_ACCESS_CHANGED')
    return dict(status='OW09_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        changed_readers=list(native_delta.SIGNATURES),owners=dict(OWNERS),new_objects=[],
        tables_triggers_grants_or_writers_changed=False,base_cp7_sql_edited=False,
        OW09_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """No row belongs to this stage (readers only); the predecessor keeps its own used-state guard."""
    with atomic(cur):
        verify(cur,state)
        replace(cur,state['originals'])
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW09_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW09_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
