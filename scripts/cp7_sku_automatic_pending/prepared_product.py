"""One deterministic automatic successor of the exact money product.

This composes definitions only. It does not install a database, activate a
workflow or supply any qualification/adoption gate.
"""
from hashlib import sha256
from pathlib import Path
import json,re
from cp7_sku_cost_components import prepared_product as parent
from . import derivation

HERE=Path(__file__).resolve().parent


def function_map(ddl):
    result={}
    for body in re.findall(r'(?ms)^create (?:or replace )?function [\s\S]*?\$\$;\n',ddl):
        name=re.search(r'(?i)function\s+([^\s(]+)',body).group(1);result[name]=body
    return result


def derive(current_catalog,parent_originals):
    base=parent.derive(current_catalog,parent_originals)
    sources=dict(base['definitions'])|function_map(base['ddl'])
    for name in('erp.be_complete_rework_target_v1','erp.be_reverse_rework_target_v1'):
        keys=[k for k in current_catalog['functions']if k.split('(')[0]==name]
        if len(keys)!=1:raise ValueError('AUTOMATIC_EXACT_NATIVE_HOOK_SIGNATURE_REQUIRED:'+name)
        sources[keys[0]]=current_catalog['functions'][keys[0]][0]
    changed=derivation.derive(sources)
    profiles={}
    for package in('cp7_sku_moving_average','cp7_sku_cost_components'):
        profiles.update(json.loads((HERE.parent/package/'CATALOG_ADDITIONS.json').read_bytes())['groups']['functions'])
    definitions=dict(base['definitions'])
    for name,body in changed['definitions'].items():
        keys=[k for k in set(profiles)|set(current_catalog['functions'])if k.split('(')[0]==name]
        if len(keys)!=1:raise ValueError('AUTOMATIC_EXACT_COMPOSED_SIGNATURE_REQUIRED:'+name)
        definitions[keys[0]]=body
    files={str(p.relative_to(HERE.parent.parent)):dict(bytes=len(p.read_bytes()),sha256=sha256(p.read_bytes()).hexdigest())
        for p in sorted(HERE.iterdir())if p.is_file()and p.suffix in('.py','.sql','.inc')}
    return dict(ddl=base['ddl']+'\n'+changed['ddl'],definitions=definitions,
        derivations=base['derivations']|{'automatic':changed['derivations']},
        source_files=base['source_files'],automatic_source_files=files,
        original_money_product_preserved=True,actual_ERP_cases=0,production_go=False,independent_acceptance=False)
