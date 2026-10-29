"""Additive S03 stage over the exact qualified vendor composition.

Installation derives from the actual installed Native definitions, never the
source-derived local ABI fixture. After any use, only full backup restore may
remove the stage. No default installer or shared source is changed here.
"""
from pathlib import Path
from hashlib import sha256
from cp7_vendor_receivable import composition as predecessor
from cp7_laundry_unknown_wash.composition import as_owner
from . import native_delta
from .installer_ddl import existing_schema_ddl
from .catalog_contract import SCHEMA,TABLES,PUBLIC,declared_functions,transition

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CONTRACT='cp7.attendance-period-choice.v1'
USED_ERROR='CP7_S03_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
CAPTURED={}

def parent():return predecessor
def runtime():return predecessor.runtime()
def sources():
    return dict(contract=CONTRACT,predecessor=predecessor.sources(),files={str((HERE/name).relative_to(ROOT)):sha256((HERE/name).read_bytes()).hexdigest()
        for name in('choice.sql','readers.sql','native_delta.py','catalog_contract.py','NEW_CATALOG_IDENTITIES.json','composition.py','installer_ddl.py')},new_public_RPC=len(PUBLIC),qualification_only=True,production_go=False,independent_acceptance=False)

def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],proof=proof,
        preuse=prior['preuse_data_and_sequences'],preinstall=prior['preinstall_data_and_sequences']))

def verify(cur,state):
    _,_,_,_,catalog=runtime();catalog._authority(cur)
    prior=state['predecessor']
    if(state['sources']!=sources()or prior['sources']!=predecessor.sources()
       or state['before']!=prior['after']or state['parent_binding']!=binding(catalog,prior,state['parent_proof'])):raise ValueError('CP7_S03_PARENT_OR_SOURCE_CHANGED')
    originals={sig:state['before']['functions'][sig][0]for sig in native_delta.SIGNATURES}
    if(state['originals']!=originals or state['definitions']!=native_delta.patched(originals)
       or state['clones']!=native_delta.clones(originals)):raise ValueError('CP7_S03_ACTUAL_CAPTURE_OR_DERIVATION_CHANGED')
    if catalog._catalog_rows(cur)!=state['after']:raise ValueError('CP7_S03_ACTUAL_ALL22_CHANGED')
    transition(state['before'],state['after'],state['definitions'])
    roles=[r[0]for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    for role in roles:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE,CREATE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('CP7_S03_SCHEMA_EXPOSED:'+role)
    for table in TABLES:
        owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()
        if owner!='postgres'or not rls:raise ValueError('CP7_S03_PRIVATE_RLS_REQUIRED:'+table)
        for role in roles:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:raise ValueError('CP7_S03_TABLE_EXPOSED:'+role+':'+table)
    for signature in declared_functions():
        owner=cur.execute('select pg_get_userbyid(proowner)from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()[0]
        if owner!='postgres':raise ValueError('CP7_S03_FUNCTION_OWNER:'+signature)
        for role in roles:
            allowed=signature in PUBLIC and role=='authenticated'
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]!=allowed:raise ValueError('CP7_S03_FUNCTION_EXPOSED:'+role+':'+signature)
    return dict(status='CP7_S03_EXACT_SOURCE_ACTUAL_ALL22',actual_parent_verified_before_delta=True,projected_catalog=False,
        Native_changed_functions=list(native_delta.NATIVE_SIGNATURES),existing_private_facade_changed=native_delta.FACADE,
        existing_private_readers_changed=list(native_delta.READER_SIGNATURES),
        actual_captured_originals=15,Native_source_manifest_builder_unchanged=True,
        Native_HPP_and_journal_primitives_unchanged=True,source_and_output_periods_separate=True,
        payroll_recognition_at_APPROVED_unchanged=True,PAID_and_E05_reopen_remain_settlement=True,
        local_qualification_is_not_Native_Auth_or_browser_PASS=True,production_go=False,independent_acceptance=False)

def install_delta(cur,prior):
    _,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof=predecessor.verify(cur,prior);before=catalog._catalog_rows(cur);data=catalog._data(cur)
        if SCHEMA in before['schemas']:raise ValueError('CP7_S03_ALREADY_INSTALLED')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        if any(before['functions'][sig][1]!='postgres'for sig in originals):raise ValueError('CP7_S03_NATIVE_OWNER_CHANGED')
        CAPTURED.clear();CAPTURED.update(originals)
        patched=native_delta.patched(originals);clones=native_delta.clones(originals)
        with as_owner(cur,'postgres'),existing_schema_ddl(cur)as ddl_authority:
            cur.execute((HERE/'choice.sql').read_text(),prepare=False)
            cur.execute((HERE/'readers.sql').read_text(),prepare=False)
            for definition in clones.values():cur.execute(definition,prepare=False)
            cur.execute('revoke all on all functions in schema '+SCHEMA+' from public,anon,authenticated,service_role',prepare=False)
            for definition in patched.values():cur.execute(definition,prepare=False)
        state=dict(sources=sources(),predecessor=prior,parent_proof=proof,parent_binding=binding(catalog,prior,proof),
            private_schema_ddl_inventory=ddl_authority['before'],
            before=before,before_data=data,originals=originals,definitions=patched,clones=clones,after=catalog._catalog_rows(cur),
            preuse_data_and_sequences=catalog._data(cur),preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])
        transition(before,state['after'],patched);verify(cur,state);return state

def install(cur):
    _,_,_,base,_=runtime()
    with base.atomic(cur):return install_delta(cur,predecessor.install(cur))

def rollback_delta_preuse(cur,state):
    _,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        with as_owner(cur,'postgres'),existing_schema_ddl(cur):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            for signature in PUBLIC:cur.execute('drop function '+signature)
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['before_data']:raise ValueError('CP7_S03_PREUSE_RESTORE_MISMATCH')
        return dict(status='CP7_S03_EXACT_PREUSE_DELTA_RESTORE',parent_verified=predecessor.verify(cur,state['predecessor']),used_guard_before_DDL=True)

def rollback_preuse(cur,state):
    _,_,_,base,_=runtime()
    with base.atomic(cur):return dict(delta=rollback_delta_preuse(cur,state),parent=predecessor.rollback_preuse(cur,state['predecessor']))
