"""Compose Afui/Mandor, moving valuation and money without projecting any state.

All accepted sources remain in their own immutable worktrees. No module is
patched in place. This loader requires the actual current Mandor Root and the
exact source-only money candidate preflight. The combined financial run is new.
"""
from pathlib import Path
from types import ModuleType
import importlib.util
import inspect
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN_SKU=ROOT.parent/'qualified-sku-money'
FROZEN_PARENT=ROOT.parent/'qualified-mandor-parent'
EXPECTED_PARENT_MODULE=FROZEN_PARENT/'scripts/current-mandor-shop-native-qualification/assembly.py'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


admission=load('current_money_parent_admission',HERE/'admission.py')
money_derive=load('current_money_parent_derivation',HERE/'derive.py')


def require(value,message):
    if not value:raise ValueError(message)


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def prepared_sources():
    reference=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
    require(reference['classification']=='PREPARED_SOURCE_REFERENCE_NOT_ACTUAL_PARENT'
        and reference['actual_ERP_cases']==0 and reference['production_go']is False,
        'SKU_MONEY_COMPOSITE_SOURCE_NOT_ACCEPTANCE')
    tree=reference['candidate_tree'];require(git(ROOT,'cat-file','-t',tree).strip()==b'tree',
        'SKU_MONEY_COMPOSITE_IMMUTABLE_CANDIDATE_TREE_REQUIRED')
    files={name:git(ROOT,'show',tree+':'+name)for name in reference['files']}
    require({n:admission.pin(v)for n,v in files.items()}==reference['files'],
        'SKU_MONEY_COMPOSITE_EXACT_CANDIDATE_SOURCE_REQUIRED')
    require(reference['files']['scripts/current-sku-recovery-material-lock/runtime_source.py']['sha256']==admission.SOURCE_FENCE_SHA256,
        'SKU_MONEY_COMPOSITE_EXACT_RETAINED_SOURCE_FENCE')
    cfg=json.loads(files['scripts/current-sku-cost-money-qualification/CONFIG.json'])
    require(reference['native_case_ids']==cfg['native_case_ids']and len(set(cfg['native_case_ids']))==19,
        'SKU_MONEY_COMPOSITE_ALL_NINETEEN_SOURCE_CASES_REQUIRED')
    product=json.loads(files['scripts/cp7_sku_cost_components/SOURCE.json'])
    require(len(product['gates'])==12 and all(v is None for v in product['gates'].values()),
        'SKU_MONEY_COMPOSITE_PREPARATION_CANNOT_PROMOTE_PRODUCT')
    for name,pin in product['files'].items():
        require(admission.pin(git(ROOT,'show',tree+':'+name))==pin,'SKU_MONEY_COMPOSITE_PRODUCT_SOURCE_CHANGED:'+name)
    path=ROOT/'scripts/current-sku-composite-preparation/sku_current_parent_derive.py'
    require(admission.pin(path.read_bytes())==reference['moving_deriver'],'SKU_MONEY_COMPOSITE_RETAINED_MOVING_DERIVER_CHANGED')
    retained=load('retained_current_moving_parent_deriver',path)
    moving,oldproof=retained.derive(files['scripts/cp7_sku_moving_average/composition.py'])
    money,proof=money_derive.derive(files['scripts/cp7_sku_cost_components/composition.py'])
    return reference,moving,money,dict(moving=oldproof,money=proof)


def source_manifest():
    raw=(HERE/'SOURCE.json').read_bytes();manifest=json.loads(raw)
    require(manifest['contract']=='cp7.current-mandor-moving-money-direct-qualification-preparation.v1'
        and manifest['actual_composite_cases']==0 and manifest['production_go']is False,
        'SKU_MONEY_COMPOSITE_EXACT_PREPARATION_MANIFEST')
    closed=[getattr(admission,name)is None for name in admission.GATES]
    require(all(closed)or not any(closed),'SKU_MONEY_COMPOSITE_NO_PARTIAL_ADMISSION')
    require(manifest['all_admission_values_unset']is all(closed)
        and manifest['actual_parent_adopted']is(not any(closed)),
        'SKU_MONEY_COMPOSITE_SOURCE_AND_GATE_STATE_REQUIRED')
    for name,pin in manifest['files'].items():
        path=HERE/name
        require(path.is_file()and not path.is_symlink()and admission.pin(path.read_bytes())==pin,
            'SKU_MONEY_COMPOSITE_DECLARED_SOURCE_CHANGED:'+name)
    reference,_,_,proof=prepared_sources()
    require(manifest['derivations']==proof,'SKU_MONEY_COMPOSITE_EXACT_DERIVATIONS_REQUIRED')
    if not any(closed):
        require(admission.SKU_HEAD==reference['candidate_head']and admission.SKU_TREE==reference['candidate_tree'],
            'SKU_MONEY_COMPOSITE_CANDIDATE_MUST_MATCH_REVIEWED_SOURCE')
    return admission.pin(raw)


def load_prepared(parent,money_module,parent_raw,money_raw):
    # No receipt/file/module/Git access is allowed before the closed gate.
    admission.require_ready()
    own=source_manifest();reference,moving_code,money_code,derivations=prepared_sources()
    receipt=admission.admitted(parent_raw,money_raw,reference['native_case_ids'])
    require(Path(inspect.getfile(type(parent))).resolve()==EXPECTED_PARENT_MODULE.resolve(),
        'SKU_MONEY_COMPOSITE_EXACT_CURRENT_MANDOR_ASSEMBLY_REQUIRED')
    require(admission.pin(EXPECTED_PARENT_MODULE.read_bytes())==admission.PARENT_MODULE_PIN,
        'SKU_MONEY_COMPOSITE_ACCEPTED_PARENT_ASSEMBLY_SOURCE_CHANGED')
    cost=FROZEN_SKU/'scripts/cp7_sku_cost_components';moving_path=FROZEN_SKU/'scripts/cp7_sku_moving_average'
    require(Path(money_module.__file__).resolve()==cost/'composition.py','SKU_MONEY_COMPOSITE_EXACT_FROZEN_MONEY_MODULE')
    moving_module=money_module.parent()
    require(Path(moving_module.__file__).resolve()==moving_path/'composition.py','SKU_MONEY_COMPOSITE_EXACT_FROZEN_MOVING_MODULE')
    for module,folder,names in ((money_module,cost,('prepared_product','catalog_additions')),
        (moving_module,moving_path,('private_delta','consumer_delta','reader_delta','credit_delta','catalog_additions','reader_access'))):
        for name in names:
            require(Path(getattr(module,name).__file__).resolve()==folder/(name+'.py'),
                'SKU_MONEY_COMPOSITE_EXACT_FROZEN_DEPENDENCY:'+name)
    def frozen_child():
        require(git(FROZEN_SKU,'rev-parse','HEAD').decode().strip()==admission.SKU_HEAD
            and git(FROZEN_SKU,'rev-parse','HEAD^{tree}').decode().strip()==admission.SKU_TREE,
            'SKU_MONEY_COMPOSITE_FROZEN_CHILD_IDENTITY_CHANGED')
        require(not git(FROZEN_SKU,'status','--porcelain','--untracked-files=no').strip(),
            'SKU_MONEY_COMPOSITE_FROZEN_CHILD_DIRTY')
    frozen_child()
    def bridge_sources():
        require(admission.admitted(parent_raw,money_raw,reference['native_case_ids'])==receipt
            and source_manifest()==own,'SKU_MONEY_COMPOSITE_RECEIPT_OR_PREPARATION_CHANGED')
        frozen_child()
        require(admission.pin(EXPECTED_PARENT_MODULE.read_bytes())==admission.PARENT_MODULE_PIN,
            'SKU_MONEY_COMPOSITE_PARENT_ASSEMBLY_CHANGED')
        require(admission.pin(admission.canonical(parent.sources()))==admission.PARENT_SOURCE_PIN,
            'SKU_MONEY_COMPOSITE_COMPLETE_CURRENT_PARENT_SOURCE_GRAPH_CHANGED')
        require(admission.pin(admission.canonical(money_module.sources()))==admission.SKU_SOURCE_PIN,
            'SKU_MONEY_COMPOSITE_COMPLETE_CANDIDATE_MONEY_SOURCE_GRAPH_CHANGED')
        return dict(receipt=receipt,preparation_source=own,derivations=derivations,parent_state_projection=False,
            actual_composite_cases=0,production_go=False)
    bridge_sources()
    moving=ModuleType('current_mandor_moving_for_money')
    moving.__file__=str(moving_path/'composition.py');moving.__package__=moving_module.__package__
    moving.__dict__.update(_CURRENT_PARENT=parent,_BRIDGE_SOURCES=bridge_sources)
    exec(compile(moving_code,moving.__file__+'::current_mandor_parent','exec'),moving.__dict__)
    money=ModuleType('current_mandor_moving_money')
    money.__file__=str(cost/'composition.py');money.__package__=money_module.__package__
    money.__dict__.update(_CURRENT_MOVING_PARENT=moving,_BRIDGE_SOURCES=bridge_sources)
    exec(compile(money_code,money.__file__+'::current_moving_parent','exec'),money.__dict__)
    return money
