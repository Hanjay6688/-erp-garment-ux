"""Offline context-catalog comparison; no database or command admission.

The complete supplied all22 catalogue is inspected without schema exclusions.
Transaction columns identify candidates, including immutable transaction facts.
This file never decides that a row grants authority and never deletes history.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re

KINDS=('r','p','f')
PERSISTENCE=('p','u')
TABLE_GROUPS=('columns','constraints','policies','triggers')
ALL22=('schemas','relations','columns','constraints','indexes','triggers','functions','aggregates',
       'types','enums','sequences','policies','extensions','roles','memberships','event_triggers',
       'rules','inheritance','default_privileges','database_authority','type_implementation','sequence_ownership')
CONTRACT='cp7.final-context.portable-catalog-source.v1'
CLOSED='FINAL_CONTEXT_RUNTIME_CLOSED_ACTUAL_COMPOSITE_RAW_ACL_AND_PHASE_PROOFS_REQUIRED'


def require(ok,message):
    if not ok:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return sha256(canonical(value).encode()).hexdigest()


def discover(catalog):
    require(type(catalog)is dict and set(catalog)==set(ALL22),'FINAL_CONTEXT_COMPLETE_ALL22_REQUIRED')
    require(all(type(catalog.get(k))is dict for k in ALL22),
            'FINAL_CONTEXT_TYPED_CATALOG_GROUPS_REQUIRED')
    found=set()
    for key,row in catalog['columns'].items():
        require(type(key)is str and ':'in key and type(row)is list and len(row)==14,
                'FINAL_CONTEXT_EXACT_COLUMN_ROW_ABI_REQUIRED')
        table,column=key.rsplit(':',1)
        require(row[0]==column and table in catalog['relations'],'FINAL_CONTEXT_COLUMN_IDENTITY_CHANGED')
        relation=catalog['relations'][table]
        require(type(relation)is list and len(relation)==13,'FINAL_CONTEXT_EXACT_RELATION_ROW_ABI_REQUIRED')
        # Wrong type, unlogged and foreign candidates remain visible and refuse
        # against a pinned profile. No cp7_* or other schema prefix is trusted.
        if column in ('transaction_id','txid') and relation[1]in KINDS and relation[2]in PERSISTENCE:
            found.add(table)
    return tuple(sorted(found))


def select(catalog):
    names=discover(catalog);name_set=set(names)
    schemas={name.split('.',1)[0]for name in names}
    owners={catalog['relations'][name][0]for name in names}
    require(schemas<=set(catalog['schemas'])and owners<=set(catalog['roles']),
            'FINAL_CONTEXT_SCHEMA_OR_OWNER_METADATA_MISSING')
    selected={group:{key:deepcopy(row)for key,row in catalog[group].items()
                    if key.split(':',1)[0]in name_set}for group in TABLE_GROUPS}
    selected['relations']={name:deepcopy(catalog['relations'][name])for name in names}
    selected['schemas']={name:deepcopy(catalog['schemas'][name])for name in sorted(schemas)}
    # Retain the whole role/membership graph: indirect inherited grants cannot
    # disappear merely because an edge does not name the immediate table owner.
    selected['roles']=deepcopy(catalog['roles'])
    selected['memberships']=deepcopy(catalog['memberships'])
    # Index membership is tied to qualified table names in pg_get_indexdef,
    # with both default and quoted schema/table rendering admitted literally.
    indexes={}
    for key,row in catalog['indexes'].items():
        require(type(row)is list and len(row)==6 and type(row[0])is str,'FINAL_CONTEXT_INDEX_ROW_ABI_REQUIRED')
        ident=r'(?:"(?:[^"]|"")+"|[A-Za-z_][A-Za-z_0-9$]*)'
        target=re.search(r'\bON\s+(?:ONLY\s+)?('+ident+r')\.('+ident+r')\s+USING\b',row[0])
        require(target is not None,'FINAL_CONTEXT_INDEX_RELATION_NOT_QUALIFIED')
        unquote=lambda s:s[1:-1].replace('""','"')if s.startswith('"')else s
        name=unquote(target[1])+'.'+unquote(target[2])
        if name in name_set:indexes[key]=deepcopy(row)
    selected['indexes']=indexes
    # Defaults and role edges are retained rather than inferred from table ACL.
    selected['default_privileges']={key:deepcopy(row)for key,row in catalog['default_privileges'].items()
        if len(key.split(':'))==3 and(key.split(':')[1]in schemas or key.split(':')[0]in owners)}
    return dict(contract=CONTRACT,names=list(names),catalog=selected,
        scope='EXACT_PORTABLE_CATALOG_SOURCE_ONLY',schema_exclusions=[],
        raw_schema_and_relation_ACLs_observed=False,reader_visibility_observed=False,
        active_row_authority_decided=False,all_transaction_tables_are_ephemeral=False,
        runtime_entry=None,actual_Native_credit=0,production_go=False)


def validate(catalog,expected):
    require(expected.get('contract')==CONTRACT and expected.get('runtime_entry')is None
            and expected.get('actual_Native_credit')==0 and expected.get('schema_exclusions')==[],
            'FINAL_CONTEXT_CLOSED_SOURCE_PROFILE_REQUIRED')
    require(list(discover(catalog))==expected['names'],'FINAL_CONTEXT_EXACT_MEMBERSHIP_CHANGED')
    current=select(catalog)
    require(canonical(current)==canonical(expected),'FINAL_CONTEXT_EXACT_PORTABLE_METADATA_CHANGED')
    return dict(status='EXACT_NARROW_CONTEXT_CATALOG_SOURCE_ONLY',contexts=len(current['names']),
        metadata_sha256=digest(current),schema_exclusions=[],raw_ACL_authority_bound=False,
        actual_final_composite=False,active_row_authority_decided=False,runtime_entry=None,
        actual_Native_credit=0,production_go=False,independent_acceptance=False)


def require_runtime(*args,**kwargs):raise ValueError(CLOSED)
