"""Retain all nineteen money callbacks on the complete current parent.

Only product selection, exact frozen input paths and the owning output label
change. No financial assertion, prerequisite, used guard or census is edited.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL='scripts/current-sku-cost-money-qualification/runner.py'
PIN=dict(bytes=6118,sha256='91c92eb8dd535e98f9b16a8c6dd57d7285abe56d277b77639511a71c79e86d3a')
LABEL='CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19'
CASE='CURRENT_MANDOR_PARENT_SKU_MONEY_NATIVE19_AND_USED_INVERSE'
REPLACEMENTS=(
    ('from cp7_sku_cost_components import composition as product','product=_CURRENT_MONEY_ASSEMBLY'),
    ("HERE/'native_cases.py'","_FROZEN_SKU/'scripts/current-sku-cost-money-qualification/native_cases.py'"),
    ("HERE/'native_preflight.py'","_FROZEN_SKU/'scripts/current-sku-cost-money-qualification/native_preflight.py'"),
    ("ROOT/'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py'",
     "_FROZEN_SKU/'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py'"),
    ("LABEL='CP7_SKU_COST_MONEY_NATIVE19'","LABEL='"+LABEL+"'"),
)


def derive(raw):
    if dict(bytes=len(raw),sha256=sha256(raw).hexdigest())!=PIN:
        raise ValueError('SKU_CURRENT_MONEY_EXACT_NINETEEN_COMPONENT_REQUIRED')
    source=raw.decode()
    for before,after in REPLACEMENTS:
        if source.count(before)!=1 or after in source:
            raise ValueError('SKU_CURRENT_MONEY_EXACT_COMPONENT_ROUTE_REQUIRED')
        source=source.replace(before,after,1)
    restored=source
    for before,after in reversed(REPLACEMENTS):
        if restored.count(after)!=1:raise ValueError('SKU_CURRENT_MONEY_COMPONENT_INVERSE_ROUTE_REQUIRED')
        restored=restored.replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('SKU_CURRENT_MONEY_COMPONENT_NOT_RECOVERED')
    compile(source,'current_parent_money_component','exec')
    return source,dict(original=PIN,derived_sha256=sha256(source.encode()).hexdigest(),exact_routes=5,
        complete_original_recovered=True,all_nineteen_case_assertions_preflight_used_guard_and_census_unchanged=True,
        actual_composite_cases=0,production_go=False)


def load_prepared(bridge,product,parent_raw,money_raw,scheduler_quiet):
    bridge.admission.require_ready()  # Before any receipt, file or ERP import.
    reference,_,_,_=bridge.prepared_sources()
    bridge.admission.admitted(parent_raw,money_raw,reference['native_case_ids'])
    bridge.source_manifest()
    path=bridge.FROZEN_SKU/ORIGINAL
    if not path.is_file()or path.is_symlink():raise ValueError('SKU_CURRENT_MONEY_REGULAR_NATIVE_COMPONENT_REQUIRED')
    source,proof=derive(path.read_bytes())
    module=ModuleType('current_parent_exact_nineteen_money_component')
    module.__file__=str(HERE/'component.py')
    module._CURRENT_MONEY_ASSEMBLY=product;module._FROZEN_SKU=bridge.FROZEN_SKU
    exec(compile(source,module.__file__+'::exact_nineteen','exec'),module.__dict__)
    if module.ROOT!=ROOT or module.LABEL!=LABEL:raise ValueError('SKU_CURRENT_MONEY_OWNING_OUTPUT_NAMESPACE')
    return SimpleNamespace(CASE=CASE,LABEL=LABEL,exercise=module.exercise,scheduler_quiet=scheduler_quiet),proof
