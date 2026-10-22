"""OW-08b failed-wash stage over the qualified OW07 product: a failed wash may wait for its laundry vendor price (LAU-DEC04).

Nine installed Native functions get the counted delta of native_delta.py, replaced as their verified existing owner
(postgres, as OW07 requires for its own three). One private schema is added: the price register prices_v1 (RLS on, nothing
granted), its immutability trigger and five SECURITY DEFINER readers/writer owned by postgres that no API role can call.
Every one of the 22 catalog groups is captured; only these declared changes are admitted. Removal before use restores the
exact OW07 predecessor; once an attempt was recorded with an unknown price, removal needs a backup restore.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_hpp_close import composition as predecessor
from cp7_laundry_unknown_wash import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA=native_delta.SCHEMA
SQL='unknown_wash.sql'
TABLE=SCHEMA+'.prices_v1'
TRIGGER='prices_v1_guard'
GUARD=SCHEMA+'.guard_v1()'
FUNCTIONS=(GUARD,SCHEMA+'.unknown_v1()',SCHEMA+'.po_pending_v1(uuid)',SCHEMA+'.blockers_v1(date)',
           SCHEMA+'.workspace_v1(uuid,boolean)',SCHEMA+'.set_price_v1(jsonb,uuid)')
STABLE=(SCHEMA+'.unknown_v1()',SCHEMA+'.po_pending_v1(uuid)',SCHEMA+'.blockers_v1(date)',SCHEMA+'.workspace_v1(uuid,boolean)')
OWNER='postgres'
ROLES=('anon','authenticated','service_role','cp7_capture','cp7_fg_read','cp7_transaction_source_read','cp7_hpp_pool_read',
       'cp7_hpp_pool_write','cp7_invoice_read','cp7_invoice_write','cp7_procure_write')
catalog=predecessor.catalog
atomic=predecessor.atomic
as_owner=predecessor.as_owner
CAPTURED={}


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in(SQL,'native_delta.py','composition.py')})


def admit_catalog(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW08B_WASH_COMPLETE_CATALOG_GROUPS_CHANGED')
    private=('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None\
               and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None:
                if group=='schemas'and key==SCHEMA:continue
                if group=='functions'and key in FUNCTIONS:continue
                if group in private and key.startswith(SCHEMA+'.'):continue
            raise ValueError('OW08B_WASH_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
            raise ValueError('OW08B_WASH_SCHEMA_ALREADY_EXISTS')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        owners={sig:before['functions'][sig][1]for sig in native_delta.SIGNATURES}
        CAPTURED.clear();CAPTURED.update(originals)  # diagnostic copy if an anchor no longer matches
        if set(owners.values())!={OWNER}:raise ValueError('OW08B_WASH_VERIFIED_EXISTING_OWNER_CHANGED: '+repr(owners))
        definitions=native_delta.patched(originals)
        with as_owner(cur,OWNER):
            cur.execute((ROOT/SQL).read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',(ROOT/SQL).read_text()))
        if names!={f.split('(')[0]for f in FUNCTIONS}or set(after['functions'])-set(before['functions'])!=set(FUNCTIONS):
            raise ValueError('OW08B_WASH_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,definitions=definitions)
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW08B_WASH_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig,definition in state['definitions'].items():
        if cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]!=definition:
            raise ValueError('OW08B_WASH_NATIVE_FUNCTION_NOT_PATCHED: '+sig)
    for sig in FUNCTIONS:
        owner,definer,volatile,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!=OWNER or definer!=(sig!=GUARD)or volatile!=('s'if sig in STABLE else'v')or 'search_path=""'not in(config or()):
            raise ValueError('OW08B_WASH_PRIVATE_FUNCTION_AUTHORITY_CHANGED: '+sig)
    owner,rls,trigger=cur.execute("""select pg_get_userbyid(c.relowner),c.relrowsecurity,(select t.tgenabled from pg_trigger t where t.tgrelid=c.oid and t.tgname=%s)
        from pg_class c where c.oid=%s::regclass""",(TRIGGER,TABLE)).fetchone()
    if owner!=OWNER or not rls or trigger!='O':raise ValueError('OW08B_WASH_PRICE_REGISTER_AUTHORITY_CHANGED')
    for role in ROLES:
        if not cur.execute('select exists(select 1 from pg_roles where rolname=%s)',(role,)).fetchone()[0]:continue
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW08B_WASH_PRIVATE_SCHEMA_EXPOSED: '+role)
        if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,TABLE)).fetchone()[0]:
            raise ValueError('OW08B_WASH_PRICE_REGISTER_EXPOSED: '+role)
        for sig in FUNCTIONS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('OW08B_WASH_PRIVATE_FUNCTION_EXPOSED: '+role+':'+sig)
    return dict(status='OW08B_WASH_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        Native_changed_functions=list(native_delta.SIGNATURES),new_private_functions=list(FUNCTIONS),price_register=TABLE,
        new_close_codes=list(native_delta.CODES),new_bd_action=native_delta.ACTION,
        Native_tables_triggers_or_grants_changed=False,OW08b_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """Exact OW07 predecessor while no attempt was recorded with an unknown price; after use a backup restore is required."""
    with atomic(cur):
        verify(cur,state)
        cur.execute('lock table '+TABLE+' in access exclusive mode')
        used=cur.execute('select count(*)from '+TABLE).fetchone()[0]
        pending=cur.execute("""select count(*)from erp.laundry_failed_wash_attempts a join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
            where rl.actual_rate_snapshot is null or rl.actual_cost_status='PENDING'""").fetchone()[0]
        if used or pending:raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
        with as_owner(cur,OWNER):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            # All 22 groups are compared below: the cascade can only remove this stage's own schema objects.
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW08B_WASH_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW08B_WASH_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,financial_facts_deleted=False,production_go=False)
