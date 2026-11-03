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
import po_routes
import install_routes


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
    _,po_proof=po_routes.derive()
    routes.require(po_proof['derived_helpers']==manifest['po_derived_helpers'],
        'GLOBAL_SKU_PO_EXACT_DERIVED_HELPERS')
    po_source=json.loads((HERE/'PO_SOURCE_CONTROLS.json').read_bytes())
    po_model=json.loads((HERE/'PO_MODEL_CONTROLS.json').read_bytes())
    reviewed=json.loads((HERE/'INPUT_REVIEW_CONTROLS.json').read_bytes())
    routes.require(po_source['status']=='GLOBAL_SKU_PO_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME'
        and po_source['source_helpers']==po_proof['derived_helpers']
        and len(po_source['controls'])==7 and all(x['result']=='PASS'for x in po_source['controls']),
        'GLOBAL_SKU_PO_SOURCE_PREREQUISITES_REQUIRED')
    routes.require(po_model['status']=='MODELED_POSTGRES17_GLOBAL_SKU_PO_OBSERVATIONS_PASS_NOT_NATIVE'
        and po_model['source_helpers']==po_proof['derived_helpers']and len(po_model['results'])==41
        and all(x['result']=='PASS'for x in po_model['results'])and po_model['actual_Native_cases']==0,
        'GLOBAL_SKU_PO_NEW_MODEL_EVIDENCE_REQUIRED')
    routes.require(reviewed['classification']=='PREPARED_SOURCE_REVIEW_NOT_ACTUAL_INPUT_PROFILE'
        and reviewed['graph_source_routes']==po_proof['derived_helpers']
        and reviewed['selected_source_projection_has_no_unresolved']is True
        and reviewed['complete_input_review']is False and reviewed['actual_final_parent_adopted']is False,
        'GLOBAL_SKU_PO_EXPECTATION_CANNOT_ADOPT_ACTUAL_INPUT_PROFILE')
    _,installer=install_routes.derive()
    install_controls=json.loads((HERE/'INSTALL_ROUTE_CONTROLS.json').read_bytes())
    routes.require(installer['derived']==manifest['prepared_installer']
        and install_controls['derived_installer']==installer['derived']
        and install_controls['status']=='GLOBAL_SKU_PO_INSTALLER_BINDING_CONTROLS_PASS_NOT_RUNTIME'
        and install_controls['tests_run']==7 and install_controls['exit_code']==0,
        'GLOBAL_SKU_PO_INSTALLER_SOURCE_CONTROLS_REQUIRED')
    install_routes.check_sources()
    return dict(status='GLOBAL_SKU_PREPARATION_EXACT_SOURCE_FENCE_PASS_NOT_RUNTIME',
        unchanged_prepared_parent_files=len(parent),own_paths=len(expected),
        source_prerequisite_controls=len(report['controls']),new_graph_model_checks=len(model['results']),
        new_PO_source_controls=7,new_PO_observation_model_checks=41,
        new_installer_binding_controls=7,prepared_installer_replacements=7,
        prepared_source_body_projection_count=reviewed['selected_source_functions'],
        prepared_physical_relation_candidates=len(reviewed['physical_relation_candidates']),
        current_parent_ROOT_adopted=False,owning_runtime_installed=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
