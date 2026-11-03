"""Closed, exact-source Global installer binding for the prepared SKU/PO graph.

The original installer and admission module are immutable. This module creates
an isolated derived module; it never mutates imported modules or opens a gate.
"""
from pathlib import Path
from types import ModuleType,SimpleNamespace,FunctionType
import json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE))
import po_routes
from cp7_global_nonpo_envelope import composition as original
from cp7_global_nonpo_envelope import admission,build_install_plan

base=po_routes.base
PLAN=HERE/'PO_INSTALL_PLAN.json'


def exact_original():
    source=Path(original.__file__).resolve()
    base.require(source==base.GLOBAL/'composition.py','GLOBAL_PO_INSTALL_ORIGINAL_MODULE_PATH')
    manifest=json.loads((base.GLOBAL/'SOURCE.json').read_bytes())
    raw=source.read_bytes()
    base.require(base.pin(raw)==manifest['files'][str(source.relative_to(ROOT))],
        'GLOBAL_PO_INSTALL_ORIGINAL_SOURCE_CHANGED')
    return raw


def sql_sources():
    exact_original();sources=original.sql_sources();helpers,_=po_routes.derive()
    for name,text in helpers.items():sources['graph_helpers/'+name+'.sql']=text
    base.require(set(sources)==set(original.CORE_ORDER+original.PLATFORM_ORDER),
        'GLOBAL_PO_INSTALL_EXACT_ORIGINAL_SQL_SET')
    return sources


def build_plan():
    """Run the unchanged parser with an explicit source provider, offline only."""
    original_source=base.GLOBAL/'build_install_plan.py'
    manifest=json.loads((base.GLOBAL/'SOURCE.json').read_bytes())
    base.require(base.pin(original_source.read_bytes())==manifest['files'][str(original_source.relative_to(ROOT))],
        'GLOBAL_PO_INSTALL_ORIGINAL_BUILDER_CHANGED')
    namespace=dict(build_install_plan.build.__globals__)
    namespace['composition']=SimpleNamespace(sql_sources=sql_sources,CONTRACT=original.CONTRACT)
    builder=FunctionType(build_install_plan.build.__code__,namespace,build_install_plan.build.__name__)
    return builder()


def check_sources():
    exact_original()
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    base.require(manifest['contract']=='cp7.global-sku-closed-source-preparation.v1'
        and manifest['runtime_entry']is None and manifest['actual_Native_cases']==0,
        'GLOBAL_PO_INSTALL_PREPARATION_ONLY')
    required={str((HERE/n).relative_to(ROOT))for n in ('install_routes.py','PO_INSTALL_PLAN.json',
        'po_routes.py','routes.py','po_capture_ctes.sql')}
    base.require(required<=set(manifest['files']),'GLOBAL_PO_INSTALL_ALL_PROVIDER_SOURCES_MUST_BE_PINNED')
    for name,expected in manifest['files'].items():
        path=ROOT/name
        base.require(path.is_file()and not path.is_symlink()and base.pin(path.read_bytes())==expected,
            'GLOBAL_PO_INSTALL_PREPARED_SOURCE_CHANGED:'+name)
    plan=json.loads(PLAN.read_bytes())
    base.require(plan['contract']==original.CONTRACT and plan['actual_parent_adoption']is False,
        'GLOBAL_PO_INSTALL_CLOSED_PLAN_REQUIRED')
    base.require(plan['source_sql']=={n:base.pin(t.encode())for n,t in sql_sources().items()},
        'GLOBAL_PO_INSTALL_SOURCE_PLAN_MISMATCH')
    return manifest


def manifest_pin():
    # The original manifest remains part of the seal; the new preparation is
    # additive. Plan bytes stay separate from admission to avoid a hash cycle.
    value=dict(original=base.pin((base.GLOBAL/'SOURCE.json').read_bytes()),
        preparation=base.pin((HERE/'SOURCE.json').read_bytes()))
    return base.pin((json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())


def derive():
    raw=exact_original();source=raw.decode();routes=[]
    def change(before,after,count,label):
        nonlocal source
        base.require(source.count(before)==count and after not in source,'GLOBAL_PO_INSTALL_EXACT_ROUTE:'+label)
        source=source.replace(before,after);routes.append(dict(before=before,after=after,count=count,label=label))
    before="""def sql_sources():
    routes,_=semantic_routes.derive()
    return {name:(routes[name.removeprefix('derived_').removesuffix('.sql')]if name.startswith('derived_')else(HERE/name).read_text())
        for name in CORE_ORDER+PLATFORM_ORDER}
"""
    change(before,'def sql_sources():\n    return _prepared_sql_sources()\n',1,'exact_SQL_provider_only')
    change("(HERE/'INSTALL_PLAN.json')",'_prepared_plan_path()',3,'source_install_and_seal_use_same_plan')
    change('    readonly_graph.compare_current(current)','    _prepared_compare_current(current)',1,
        'complete_current_19_by_19_SKU_authority')
    change('def sources():\n    manifest=', 'def sources():\n    _prepared_check_sources()\n    manifest=',1,
        'own_source_fence_before_any_cursor_use')
    change("manifest=pin((HERE/'SOURCE.json').read_bytes())",'manifest=_prepared_manifest_pin()',1,
        'seal_original_and_prepared_source_manifests')
    recovered=source
    for route in reversed(routes):
        base.require(recovered.count(route['after'])==route['count'],'GLOBAL_PO_INSTALL_INVERSE_ROUTE')
        recovered=recovered.replace(route['after'],route['before'])
    base.require(recovered.encode()==raw and sum(r['count']for r in routes)==7,
        'GLOBAL_PO_INSTALL_ORIGINAL_NOT_RECOVERED')
    return source,dict(status='GLOBAL_SKU_PO_EXACT_INSTALLER_SOURCE_PREPARED_GATE_CLOSED',
        original=base.pin(raw),derived=base.pin(source.encode()),routes=routes,
        counted_replacements=7,route_groups=5,original_installer_recovered=True,
        admission_or_transaction_restore_or_ownership_code_changed=False,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)


def load_prepared():
    check_sources()
    base.require(all(getattr(admission,n)is None for n in ('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_RECEIPT',
        'PARENT_RUN','PARENT_JOB','PARENT_ROOT_CONTRACT','INPUT_PROFILE_PIN','RUNTIME_ENTRY')),
        'GLOBAL_PO_INSTALL_FINAL_ADOPTION_REQUIRES_SEPARATE_REVIEW')
    source,proof=derive()
    module=ModuleType('cp7_global_nonpo_envelope.prepared_SKU_PO_composition')
    module.__package__='cp7_global_nonpo_envelope';module.__file__=original.__file__
    module.__dict__.update(_prepared_sql_sources=sql_sources,_prepared_plan_path=lambda:PLAN,
        _prepared_compare_current=base.current_reference,_prepared_check_sources=check_sources,
        _prepared_manifest_pin=manifest_pin)
    exec(compile(source,module.__file__+'::prepared_SKU_PO','exec'),module.__dict__)
    return module,proof
