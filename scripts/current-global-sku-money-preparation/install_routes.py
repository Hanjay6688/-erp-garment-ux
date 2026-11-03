"""Bind exact money observation sources while original runtime stays closed."""
from pathlib import Path
from types import ModuleType,SimpleNamespace,FunctionType
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


routes=load('global_money_install_graph_routes',HERE/'routes.py')
callbacks=load('global_money_install_callback_sources',HERE/'callback_preflight.py')
from cp7_global_nonpo_envelope import composition as original
from cp7_global_nonpo_envelope import admission,build_install_plan
base=routes.base
PLAN=HERE/'INSTALL_PLAN.json'
GATES=('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_RECEIPT','PARENT_RUN','PARENT_JOB',
    'PARENT_ROOT_CONTRACT','INPUT_PROFILE_PIN','RUNTIME_ENTRY')


def exact_original():
    source=Path(original.__file__).resolve()
    base.require(source==base.GLOBAL/'composition.py','GLOBAL_MONEY_ORIGINAL_INSTALLER_PATH')
    manifest=json.loads((base.GLOBAL/'SOURCE.json').read_bytes());raw=source.read_bytes()
    base.require(base.pin(raw)==manifest['files'][str(source.relative_to(ROOT))],
        'GLOBAL_MONEY_ORIGINAL_INSTALLER_SOURCE_CHANGED')
    return raw


def sql_sources():
    exact_original();result=original.sql_sources();helpers,_=routes.derive()
    for name,text in helpers.items():result['graph_helpers/'+name+'.sql']=text
    base.require(set(result)==set(original.CORE_ORDER+original.PLATFORM_ORDER),
        'GLOBAL_MONEY_EXACT_ORIGINAL_SQL_SET')
    return result


def build_plan():
    path=base.GLOBAL/'build_install_plan.py'
    manifest=json.loads((base.GLOBAL/'SOURCE.json').read_bytes())
    base.require(base.pin(path.read_bytes())==manifest['files'][str(path.relative_to(ROOT))],
        'GLOBAL_MONEY_ORIGINAL_BUILDER_CHANGED')
    namespace=dict(build_install_plan.build.__globals__)
    namespace['composition']=SimpleNamespace(sql_sources=sql_sources,CONTRACT=original.CONTRACT)
    return FunctionType(build_install_plan.build.__code__,namespace,build_install_plan.build.__name__)()


def check_sources():
    exact_original();manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    base.require(manifest['contract']=='cp7.global-sku-money-closed-preparation.v1'
        and manifest['runtime_entry']is None and manifest['actual_ERP_cases']==0,
        'GLOBAL_MONEY_PREPARATION_ONLY')
    required={str((HERE/n).relative_to(ROOT))for n in ('install_routes.py','INSTALL_PLAN.json',
        'routes.py','money_edges.sql','SKU_SOURCE.json','callback_preflight.py',
        'CALLBACK_SOURCE_REVIEW.json','INPUT_REVIEW_CONTROLS.json')}
    base.require(required<=set(manifest['files']),'GLOBAL_MONEY_ALL_PROVIDERS_MUST_BE_PINNED')
    for name,expected in manifest['files'].items():
        path=ROOT/name
        base.require(path.is_file()and not path.is_symlink()and base.pin(path.read_bytes())==expected,
            'GLOBAL_MONEY_DECLARED_SOURCE_CHANGED:'+name)
    plan=json.loads(PLAN.read_bytes())
    base.require(plan['contract']==original.CONTRACT and plan['actual_parent_adoption']is False,
        'GLOBAL_MONEY_CLOSED_PLAN_REQUIRED')
    base.require(plan['source_sql']=={n:base.pin(t.encode())for n,t in sql_sources().items()},
        'GLOBAL_MONEY_SOURCE_PLAN_MISMATCH')
    callbacks.requirements()
    return manifest


def manifest_pin():
    value=dict(original=base.pin((base.GLOBAL/'SOURCE.json').read_bytes()),
        prior=base.pin((routes.PRIOR/'SOURCE.json').read_bytes()),
        preparation=base.pin((HERE/'SOURCE.json').read_bytes()))
    return base.pin((json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())


def derive():
    raw=exact_original();source=raw.decode();changes=[]
    def change(before,after,count,label):
        nonlocal source
        base.require(source.count(before)==count and after not in source,'GLOBAL_MONEY_EXACT_INSTALL_ROUTE:'+label)
        source=source.replace(before,after);changes.append(dict(before=before,after=after,count=count,label=label))
    before="""def sql_sources():
    routes,_=semantic_routes.derive()
    return {name:(routes[name.removeprefix('derived_').removesuffix('.sql')]if name.startswith('derived_')else(HERE/name).read_text())
        for name in CORE_ORDER+PLATFORM_ORDER}
"""
    change(before,'def sql_sources():\n    return _money_sql_sources()\n',1,'current_money_SQL_provider')
    change("(HERE/'INSTALL_PLAN.json')",'_money_plan_path()',3,'one_exact_plan_for_source_install_and_seal')
    change('    readonly_graph.compare_current(current)','    _money_compare_current(current)',1,'current_full19_authority')
    change('def sources():\n    manifest=','def sources():\n    _money_check_sources()\n    manifest=',1,'source_fence_before_cursor')
    change("manifest=pin((HERE/'SOURCE.json').read_bytes())",'manifest=_money_manifest_pin()',1,'seal_all_three_manifests')
    before='    source=sources();parent,inputs=admission.runtime_admission(parent_receipt_raw,input_profile_raw)\n'
    change(before,before+'    _money_input_relations(inputs)\n',1,'current_lower_bound_before_cursor')
    recovered=source
    for item in reversed(changes):
        base.require(recovered.count(item['after'])==item['count'],'GLOBAL_MONEY_INVERSE_INSTALL_ROUTE')
        recovered=recovered.replace(item['after'],item['before'])
    base.require(recovered.encode()==raw and sum(c['count']for c in changes)==8,
        'GLOBAL_MONEY_ORIGINAL_INSTALLER_NOT_RECOVERED')
    return source,dict(status='GLOBAL_MONEY_INSTALLER_SOURCE_PREPARED_GATE_CLOSED',original=base.pin(raw),
        derived=base.pin(source.encode()),routes=changes,counted_replacements=8,
        original_installer_recovered=True,admission_or_transaction_restore_or_ownership_code_changed=False,
        actual_ERP_cases=0,production_go=False,independent_acceptance=False)


def load_prepared():
    check_sources()
    base.require(all(getattr(admission,name)is None for name in GATES),
        'GLOBAL_MONEY_FINAL_ADOPTION_REQUIRES_SEPARATE_REVIEW')
    source,proof=derive()
    module=ModuleType('cp7_global_nonpo_envelope.prepared_money_composition')
    module.__package__='cp7_global_nonpo_envelope';module.__file__=original.__file__
    module.__dict__.update(_money_sql_sources=sql_sources,_money_plan_path=lambda:PLAN,
        _money_compare_current=routes.current_reference,_money_check_sources=check_sources,
        _money_manifest_pin=manifest_pin,_money_input_relations=callbacks.require_input_relations)
    exec(compile(source,module.__file__+'::prepared_money','exec'),module.__dict__)
    return module,proof
