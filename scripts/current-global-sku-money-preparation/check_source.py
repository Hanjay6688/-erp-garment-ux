"""Exact additive source fence. No final catalogue, admission or ERP credit."""
from hashlib import sha1
from pathlib import Path
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('global_money_source_fence_installer',HERE/'install_routes.py')
install=importlib.util.module_from_spec(spec);spec.loader.exec_module(install)
base=install.base
ROOT=install.ROOT


def check():
    manifest=install.check_sources()
    require=base.require
    require(manifest['base']==dict(public_head='4d641eef01fe28dbc302731c646be949c01eb4bf',
        tree='37185c4964430e8cbe027b1c97fa176c6717235e'),'GLOBAL_MONEY_EXACT_PREPARED_BASE')
    parent=set()
    for item in base.git('ls-tree','-rz',manifest['base']['tree']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode();parent.add(name)
        path=ROOT/name
        require(kind=='blob'and path.is_file()and not path.is_symlink(),'GLOBAL_MONEY_REGULAR_PARENT_FILE:'+name)
        raw=path.read_bytes()
        require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'GLOBAL_MONEY_UNDECLARED_PARENT_CHANGE:'+name)
    paths={p.decode()for p in base.git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if p}
    own=set(manifest['files'])|{str((HERE/'SOURCE.json').relative_to(ROOT))}
    require(paths-parent==own,'GLOBAL_MONEY_EXACT_ADDITIVE_NAMESPACE')
    require(all(p.startswith(str(HERE.relative_to(ROOT))+'/')for p in own),'GLOBAL_MONEY_OWN_NAMESPACE_ONLY')
    _,graph=install.routes.derive();_,installer=install.derive()
    require(graph['derived_helpers']==manifest['derived_helpers']and installer['derived']==manifest['prepared_installer'],
        'GLOBAL_MONEY_EXACT_DERIVED_SOURCES')
    source=json.loads((HERE/'SOURCE_CONTROLS.json').read_bytes())
    model=json.loads((HERE/'MODEL_CONTROLS.json').read_bytes())
    inputs=json.loads((HERE/'INPUT_REVIEW_CONTROLS.json').read_bytes())
    require(source['status']=='GLOBAL_MONEY_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME'
        and source['source_helpers']==graph['derived_helpers']and len(source['negative_controls'])==41
        and all(c['result']=='REFUSED_AS_REQUIRED'for c in source['negative_controls'])
        and source['column_tables']==80 and source['column_count']==813,'GLOBAL_MONEY_SOURCE_CONTROLS_REQUIRED')
    require(model['status']=='MODELED_POSTGRES17_GLOBAL_MONEY_GRAPH_CAPTURE_PASS_NOT_ERP'
        and model['source_helpers']==graph['derived_helpers']and len(model['results'])==40
        and all(c['result']=='PASS'for c in model['results'])and model['actual_ERP_cases']==0,
        'GLOBAL_MONEY_TYPED_MODEL_CONTROLS_REQUIRED')
    require(inputs['graph_source_routes']==graph['derived_helpers']
        and inputs['prepared_money_source']==install.routes.sources()[1]
        and inputs['selected_source_functions']==302 and len(inputs['physical_relation_candidates'])==232,
        'GLOBAL_MONEY_CURRENT_INPUT_REVIEW_REQUIRED')
    require(all(getattr(install.admission,n)is None for n in install.GATES),'GLOBAL_MONEY_ALL_ADMISSION_GATES_CLOSED')
    callbacks=install.callbacks.requirements()
    return dict(status='GLOBAL_MONEY_EXACT_ADDITIVE_SOURCE_FENCE_PASS_NOT_RUNTIME',unchanged_parent_files=len(parent),
        own_paths=len(own),source_negative_controls=41,typed_model_checks=40,new_full_rowsets=9,
        selected_source_functions=302,source_relation_candidates=232,
        required_relation_lower_bound=len(callbacks['required_relation_lower_bound']),
        actual_final_parent_adopted=False,complete_input_review=False,actual_ERP_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
