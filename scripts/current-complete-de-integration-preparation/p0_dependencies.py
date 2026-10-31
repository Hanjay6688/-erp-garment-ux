"""Select exact P0 identities from the existing full readonly snapshot.

This adds no SQL. It retains complete already-captured pg_proc/pg_class rows
and their owner-role rows so a later Root intake can reject missing or changed
objects without treating identity as authority, reachability, or lock closure.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def positive_oid(value):
    if type(value) not in (int,str) or type(value)is bool:
        raise ValueError('DE_P0_POSITIVE_OID_REQUIRED')
    text=str(value)
    if not text.isascii()or not text.isdecimal()or str(int(text))!=text or not 1<=int(text)<=4294967295:
        raise ValueError('DE_P0_POSITIVE_OID_REQUIRED')
    return text


def select(base,declaration):
    if base['classification']!='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE':
        raise ValueError('DE_P0_ACTUAL_READONLY_SYSTEM_METADATA_REQUIRED')
    groups=base['groups']
    if not {'routines','relations','roles'}<=set(groups):
        raise ValueError('DE_P0_FULL_ROUTINE_RELATION_ROLE_GROUPS_REQUIRED')
    routines={}
    for row in groups['routines']['rows']:
        signature=row.get('signature')
        if signature in declaration['functions']:
            if signature in routines:raise ValueError('DE_P0_DUPLICATE_FUNCTION:'+signature)
            spec=declaration['functions'][signature]
            if(row.get('schema')!=spec['schema']or row.get('prokind')!='f'
                    or row.get('prosecdef')is not spec['security_definer']
                    or row.get('provolatile')!=spec['volatility']):
                raise ValueError('DE_P0_FUNCTION_SOURCE_CONTRACT_CHANGED:'+signature)
            positive_oid(row.get('oid'));positive_oid(row.get('proowner'))
            routines[signature]=row
    if set(routines)!=set(declaration['functions']):
        raise ValueError('DE_P0_ALL_SIX_FUNCTIONS_REQUIRED')
    relations={}
    for row in groups['relations']['rows']:
        key=row.get('schema','')+'.'+row.get('relname','')
        if key in declaration['relations']:
            if key in relations:raise ValueError('DE_P0_DUPLICATE_RELATION:'+key)
            spec=declaration['relations'][key]
            if(row.get('relkind')!=spec['kind']or row.get('relpersistence')!=spec['persistence']):
                raise ValueError('DE_P0_RELATION_SOURCE_CONTRACT_CHANGED:'+key)
            positive_oid(row.get('oid'));positive_oid(row.get('relowner'))
            relations[key]=row
    if set(relations)!=set(declaration['relations']):
        raise ValueError('DE_P0_BOTH_REGISTRY_RELATIONS_REQUIRED')
    owners={positive_oid(row['proowner'])for row in routines.values()}|{
        positive_oid(row['relowner'])for row in relations.values()}
    roles={positive_oid(row['oid']):row for row in groups['roles']['rows']
        if positive_oid(row['oid'])in owners}
    if set(roles)!=owners:raise ValueError('DE_P0_ALL_OWNER_ROLE_ROWS_REQUIRED')
    for oid,row in roles.items():
        if type(row.get('rolname'))is not str or not row['rolname']:
            raise ValueError('DE_P0_OWNER_ROLE_NAME_REQUIRED:'+oid)
    return dict(functions=routines,relations=relations,owner_roles=roles)


def capture(base):
    raw=(HERE/'P0_DEPENDENCIES.json').read_bytes();declaration=json.loads(raw)
    selected=select(base,declaration)
    return dict(classification=declaration['classification'],selected=selected,
        declaration_sha256=sha256(raw).hexdigest(),same_original_readonly_snapshot=True,
        original_27_groups_rewritten=False,unresolved=declaration['unresolved'],
        identity_is_not_authority=True,identity_is_not_reachability=True,
        identity_is_not_lock_closure=True,writer_closure=False,permission_closure=False,
        lockset_approved=False,actual_Native_case_credit=0,production_go=False,
        independent_acceptance=False)
