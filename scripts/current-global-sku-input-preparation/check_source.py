"""Fence this separate source preparation without changing the frozen parent.

The parent's unified gate deliberately still excludes this preparation. Its
owning runtime cannot consume these helpers until explicit final integration.
"""
from pathlib import Path
from hashlib import sha1
import json,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE))
import routes


def check():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    routes.require(manifest['contract']=='cp7.global-sku-closed-source-preparation.v1'
        and manifest['runtime_entry']is None and manifest['actual_Native_cases']==0,
        'GLOBAL_SKU_SOURCE_PREPARATION_ONLY')
    base=manifest['base'];routes.require(base==dict(head='c19211eede0a2ccbf7f9abfb97214ffcb39ceba1',tree='b0ae193ff03c4d62800e178672b4a5dc9326b983'),
        'GLOBAL_SKU_EXACT_PREPARED_PARENT_REQUIRED')
    routes.require(routes.git('rev-parse',base['head']+'^{tree}').decode().strip()==base['tree'],
        'GLOBAL_SKU_PREPARED_PARENT_TREE_CHANGED')
    parent=set()
    for item in routes.git('ls-tree','-rz',base['head']).split(b'\0'):
        if not item:continue
        meta,name=item.split(b'\t',1);mode,kind,blob=meta.decode().split();name=name.decode();parent.add(name)
        f=ROOT/name;routes.require(kind=='blob'and f.is_file()and not f.is_symlink(),'GLOBAL_SKU_PARENT_REGULAR_FILE:'+name)
        raw=f.read_bytes()
        routes.require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
            'GLOBAL_SKU_UNDECLARED_PARENT_CHANGE:'+name)
    paths={p.decode()for p in routes.git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if p}
    expected=set(manifest['files'])|{str((HERE/'SOURCE.json').relative_to(ROOT))}
    routes.require(paths-parent==expected,'GLOBAL_SKU_EXACT_PREPARATION_NAMESPACE')
    for name,expected_pin in manifest['files'].items():
        f=ROOT/name;routes.require(f.is_file()and not f.is_symlink()and routes.pin(f.read_bytes())==expected_pin,
            'GLOBAL_SKU_DECLARED_SOURCE_CHANGED:'+name)
    _,proof=routes.derive()
    routes.require(proof['derived_helpers']==manifest['derived_helpers'],'GLOBAL_SKU_EXACT_DERIVED_HELPERS')
    report=json.loads((HERE/'SOURCE_CONTROLS.json').read_bytes())
    model=json.loads((HERE/'MODEL_CONTROLS.json').read_bytes())
    routes.require(report['status']=='GLOBAL_SKU_NEW_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME'
        and all(c['result']in('PASS','REFUSED_AS_REQUIRED')for c in report['controls']),
        'GLOBAL_SKU_SOURCE_CONTROLS_REQUIRED')
    routes.require(model['status']=='MODELED_POSTGRES17_GLOBAL_SKU_GRAPH_CAPTURE_PASS_NOT_NATIVE'
        and model['source_helpers']==proof['derived_helpers']and len(model['results'])==22
        and all(c['result']=='PASS'for c in model['results'])and model['actual_Native_cases']==0,
        'GLOBAL_SKU_EXACT_NEW_MODEL_EVIDENCE_REQUIRED')
    return dict(status='GLOBAL_SKU_PREPARATION_EXACT_SOURCE_FENCE_PASS_NOT_RUNTIME',
        unchanged_prepared_parent_files=len(parent),own_paths=len(expected),
        source_prerequisite_controls=len(report['controls']),new_graph_model_checks=len(model['results']),
        current_parent_ROOT_adopted=False,owning_runtime_installed=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
