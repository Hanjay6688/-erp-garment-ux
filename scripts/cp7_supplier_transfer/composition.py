"""Isolated OW06 owner over the complete qualified OW05 product.

Not imported by the default application/install path until the OW06 contract,
real-user screens and used-state restore have also been qualified.
"""
from hashlib import sha256
from pathlib import Path
import re
from psycopg import sql

from cp7_contractor_correction import composition as predecessor
from cp7_supplier_transfer import native_delta

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_supplier_transfer'
TABLES=('requests_v1','transfers_v1','allocations_v1','corrections_v1','context_v1')
PUBLIC=('public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)',
        'public.erp_cp7_get_supplier_transfer_v1(jsonb)')
INTERNAL={'cp7_invoice_read':{'cp7_supplier_transfer.child_detail_v1(uuid,jsonb)'},
          'cp7_transaction_source_read':{'cp7_supplier_transfer.source_payment_v1(uuid)'}}
catalog=predecessor.predecessor.catalog
atomic=predecessor.predecessor.atomic


def sources():
    return dict(predecessor=predecessor.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()
               for name in('transfer.sql','correction.sql','read.sql','native_delta.py','composition.py')})


def admit_catalog(before,after,definitions,new_functions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW06_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is not None or new is None:raise ValueError('OW06_UNDECLARED_EXISTING_DELTA: '+group+':'+key)
            if group=='functions'and key in new_functions:continue
            if group=='schemas'and key==SCHEMA:continue
            if group in('relations','columns','constraints','indexes','triggers','policies','types','type_implementation')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('OW06_UNDECLARED_NEW_OBJECT: '+group+':'+key)


def install(cur):
    with atomic(cur):
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        definitions=native_delta.patched(originals)
        with predecessor.predecessor.payment.consumer.as_owner(cur,'postgres'):
            for filename in('transfer.sql','correction.sql','read.sql'):cur.execute((ROOT/filename).read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur)
        functions=set(after['functions'])-set(before['functions'])
        names=set(re.findall(r'create function ([a-z_0-9.]+)\(',''.join((ROOT/f).read_text()for f in('transfer.sql','correction.sql','read.sql'))))
        if {s.split('(')[0]for s in functions}!=names or len(names)!=len(functions):raise ValueError('OW06_NEW_FUNCTION_SET_CHANGED')
        admit_catalog(before,after,definitions,functions)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,before=before,after=after,
            originals=originals,new_functions=sorted(functions),
            seeded_private_rows=predecessor.predecessor.base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:raise ValueError('OW06_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig in state['new_functions']:
        owner,definer,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or not definer or 'search_path=""'not in config:raise ValueError('OW06_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_capture',*INTERNAL):
            expected=(role=='authenticated'and sig in PUBLIC)or sig in INTERNAL.get(role,set())
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=expected:raise ValueError('OW06_FUNCTION_EXECUTE_CHANGED: '+role+':'+sig)
    for table in TABLES:
        name=SCHEMA+'.'+table
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(name,)).fetchone()!=('postgres',True):raise ValueError('OW06_TABLE_AUTHORITY_CHANGED')
        for role in('anon','authenticated','service_role','cp7_capture',*INTERNAL):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,name)).fetchone()[0]:raise ValueError('OW06_PRIVATE_TABLE_EXPOSED')
    return dict(status='OW06_EXACT_SOURCE_AND_ALL22_CATALOG_GROUPS_VERIFIED',
        Native_changed_functions=list(native_delta.SIGNATURES),ERP_trigger_attachments_unchanged=True,
        one_real_cash_journal_per_transfer=True,private_parent_allocation_links=True,
        default_installer_or_UI_changed=False,OW06_complete=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        verify(cur,state)
        names=sorted(state['seeded_private_rows'])
        if not names or any(name not in state['after']['relations']for name in names):raise ValueError('OW06_PRIVATE_LOCK_SET_CHANGED')
        cur.execute(sql.SQL('lock table {} in access exclusive mode nowait').format(sql.SQL(',').join(sql.Identifier(*name.split('.'))for name in names)))
        if predecessor.predecessor.base.private_rows(cur)!=state['seeded_private_rows']:
            raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
        with predecessor.predecessor.payment.consumer.as_owner(cur,'postgres'):
            for definition in state['originals'].values():cur.execute(definition,prepare=False)
            for sig in PUBLIC:cur.execute('drop function '+sig)
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('OW06_PREDECESSOR_NOT_EXACTLY_RESTORED')
        previous=predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='OW06_PREUSE_EXACT_RESTORE',predecessor_verified=previous,
            predecessor_removed=removed,used_guard_before_any_DDL=True,financial_facts_deleted=False,production_go=False)
