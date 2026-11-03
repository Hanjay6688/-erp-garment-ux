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
    require(manifest['base']==dict(public_head='5f099fa6852c9088ab46daa0f1079a0f6a1f3185',
        tree='3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d'),'GLOBAL_MONEY_EXACT_PREPARED_BASE')
    parent=set()
    for item in base.git('ls-tree','-rz',manifest['base']['tree']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode();parent.add(name)
        path=ROOT/name
        require(kind=='blob'and path.is_file()and not path.is_symlink(),'GLOBAL_MONEY_REGULAR_PARENT_FILE:'+name)
        raw=path.read_bytes()
        require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'GLOBAL_MONEY_UNDECLARED_PARENT_CHANGE:'+name)
    current_parent_files=len(parent)
    retained=manifest['retained_Global_input_preparation']
    require(retained['tree']=='37185c4964430e8cbe027b1c97fa176c6717235e'
        and retained['namespace']=='scripts/current-global-sku-input-preparation/',
        'GLOBAL_MONEY_RETAINED_INPUT_IDENTITY')
    retained_files={}
    for item in base.git('ls-tree','-rz',retained['tree'],'--',retained['namespace']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode()
        require(kind=='blob'and mode=='100644'and name not in parent,'GLOBAL_MONEY_RETAINED_INPUT_REGULAR_ADDITION')
        raw=base.git('show',retained['tree']+':'+name);path=ROOT/name
        require(path.is_file()and not path.is_symlink()and path.read_bytes()==raw,
            'GLOBAL_MONEY_RETAINED_INPUT_SOURCE_CHANGED:'+name)
        retained_files[name]=dict(blob=blob,pin=base.pin(raw));parent.add(name)
    require(len(retained_files)==23 and retained_files==retained['files'],
        'GLOBAL_MONEY_COMPLETE_RETAINED_INPUT_NAMESPACE')
    identity=json.loads((HERE/'CURRENT_SOURCE_IDENTITY.json').read_bytes())
    current=json.loads((ROOT/'scripts/current-sku-money-composite-preparation/SOURCE_REFERENCE.json').read_bytes())
    require(identity['contract']=='cp7.global-current-money-identical-product-source.v1'
        and identity['source_only']is True and identity['actual_ERP_cases']==0
        and identity['runtime_admission']is False and identity['production_go']is False,
        'GLOBAL_MONEY_CURRENT_IDENTITY_IS_NOT_ACCEPTANCE')
    require(identity['historical_reviewed_source']==install.routes.sources()[1]
        and identity['current_candidate']==dict(public_head=current['candidate_head'],tree=current['candidate_tree']),
        'GLOBAL_MONEY_CURRENT_PARENT_CANDIDATE_BINDING')
    original_blobs=None
    for tree in (identity['historical_reviewed_source']['tree'],identity['current_candidate']['tree']):
        blobs={}
        for item in base.git('ls-tree','-rz',tree,'--','scripts/cp7_sku_cost_components/').split(b'\0'):
            if not item:continue
            metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split()
            require(kind=='blob'and mode=='100644','GLOBAL_MONEY_REGULAR_PRODUCT_SOURCE')
            blobs[name.decode()]=blob
        require(len(blobs)==44 and blobs==identity['exact_product_blobs'],
            'GLOBAL_MONEY_COMPLETE_CURRENT_PRODUCT_MUST_MATCH_REVIEWED_SOURCE')
        if original_blobs is not None:require(blobs==original_blobs,'GLOBAL_MONEY_HISTORICAL_SOURCE_REUSE_REQUIRES_EXACT_BYTES')
        original_blobs=blobs
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
    return dict(status='GLOBAL_MONEY_EXACT_ADDITIVE_SOURCE_FENCE_PASS_NOT_RUNTIME',unchanged_parent_files=current_parent_files,
        retained_Global_input_files=len(retained_files),current_money_product_files_identical=44,
        current_parent_candidate=manifest['base'],own_paths=len(own),source_negative_controls=41,typed_model_checks=40,new_full_rowsets=9,
        selected_source_functions=302,source_relation_candidates=232,
        required_relation_lower_bound=len(callbacks['required_relation_lower_bound']),
        actual_final_parent_adopted=False,complete_input_review=False,actual_ERP_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
