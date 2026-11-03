"""Exact expected PG17 DDL rows; no name-prefix or self-observed admission."""
from pathlib import Path
from hashlib import sha256
import json,re

HERE=Path(__file__).resolve().parent
COUNTS=dict(columns=117,constraints=66,functions=32,indexes=18,relations=27,triggers=109,type_implementation=18,types=18)
GROUPS=('schemas','relations','columns','constraints','indexes','triggers','functions','aggregates','types','enums',
 'sequences','policies','extensions','roles','memberships','event_triggers','rules','inheritance','default_privileges',
 'database_authority','type_implementation','sequence_ownership')


def pin(value):
    if isinstance(value,str):value=value.encode()
    return dict(bytes=len(value),sha256=sha256(value).hexdigest())


def expected(product):
    profile=json.loads((HERE/'CATALOG_ADDITIONS.json').read_bytes())
    if(profile['contract']!='cp7.sku-cost-money-catalogue-additions.v1'
       or profile['classification']!='EXPECTED_POSTGRES17_DDL_ONLY_NOT_ERP_QUALIFICATION'
       or profile['financial_functions_executed']!=0 or profile['actual_ERP_cases']!=0
       or not profile['engine'].startswith('PostgreSQL 17.')or profile['production_go']is not False
       or profile['independent_acceptance']is not False or profile['explicit_unused_inverse_all22_exact']is not True):
        raise ValueError('SKU_MONEY_DDL_PROFILE_CONTRACT_CHANGED')
    if set(profile['groups'])!=set(GROUPS)or{g:len(v)for g,v in profile['groups'].items()if v}!=COUNTS:
        raise ValueError('SKU_MONEY_ALL22_PROFILE_INCOMPLETE')
    if profile['catalog_source_sha256']!=sha256((HERE.parent/'cp7_ow04_restore_bundle.py').read_bytes()).hexdigest():
        raise ValueError('SKU_MONEY_CATALOG_QUERIES_CHANGED')
    if profile['source_files']!=product['source_files']or profile['derived_ddl']!=pin(product['ddl']):
        raise ValueError('SKU_MONEY_DDL_SOURCE_CHANGED')
    if profile['derived_replacements']!={sig:pin(source)for sig,source in product['definitions'].items()}:
        raise ValueError('SKU_MONEY_REPLACEMENT_SOURCE_CHANGED')
    if set(profile['replacement_before'])!=set(product['definitions'])or set(profile['replacement_functions'])!=set(product['definitions']):
        raise ValueError('SKU_MONEY_REPLACEMENT_SET_CHANGED')
    for sig,row in profile['replacement_functions'].items():
        if row[1:]!=profile['replacement_before'][sig][1:]:raise ValueError('SKU_MONEY_EXISTING_AUTHORITY_CHANGED:'+sig)
    tables=tuple(re.findall(r'^create table ([\w.]+)\(',product['ddl'],re.M))
    if len(tables)!=9 or set(tables)!={k for k,v in profile['groups']['relations'].items()if v[1]=='r'}:
        raise ValueError('SKU_MONEY_TABLE_SET_CHANGED')
    return profile,tables


def transition(before,after,profile):
    additions=profile['groups'];replacements=profile['replacement_functions']
    if set(before)!=set(GROUPS)or set(after)!=set(GROUPS):raise ValueError('SKU_MONEY_ALL22_REQUIRED')
    for group in GROUPS:
        if set(after[group])-set(before[group])!=set(additions[group]):raise ValueError('SKU_MONEY_CATALOG_ADDITION_SET_CHANGED:'+group)
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if group=='functions'and key in replacements:
                if old!=profile['replacement_before'][key]or new!=replacements[key]:
                    raise ValueError('SKU_MONEY_EXACT_FUNCTION_TRANSITION_CHANGED:'+key)
            elif old is None and key in additions[group]:
                if new!=additions[group][key]:raise ValueError('SKU_MONEY_EXACT_CATALOG_ADDITION_CHANGED:'+group+':'+key)
            elif old!=new:raise ValueError('SKU_MONEY_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
