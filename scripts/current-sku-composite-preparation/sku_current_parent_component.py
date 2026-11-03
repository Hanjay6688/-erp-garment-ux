"""Select the unchanged accepted child cases on the complete current parent.

Only the injected assembly, frozen case path and new artifact label change.
The original component source and every test assertion remain recoverable.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import sku_current_parent_admission as admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT.parent/'qualified-sku-moving-average'
ORIGINAL='scripts/current-sku-moving-average-qualification/runner.py'
PIN=dict(bytes=4275,sha256='86223b628bd9a7ab296826624d7f54af7c965af6230ba191ff82795fc4199423')
LABEL='CP7_SKU_CURRENT_PARENT_NATIVE6'
CASE='CURRENT_MANDOR_PARENT_SKU_NATIVE6_AND_USED_INVERSE'
REPLACEMENTS=(
    ('from cp7_sku_moving_average import composition as product','product=_CURRENT_SKU_ASSEMBLY'),
    ("ROOT/'scripts/cp7_sku_moving_average/qualification_cases.py'",
     "_FROZEN_SKU/'scripts/cp7_sku_moving_average/qualification_cases.py'"),
    ("LABEL='CP7_SKU_MOVING_AVERAGE_NATIVE6'","LABEL='"+LABEL+"'"),
)


def derive(raw):
    if admission.pin(raw)!=PIN:raise ValueError('SKU_COMPOSITE_EXACT_CHILD_COMPONENT_ORIGINAL')
    text=raw.decode()
    for before,after in REPLACEMENTS:
        if text.count(before)!=1 or after in text:raise ValueError('SKU_COMPOSITE_EXACT_COMPONENT_ROUTE')
        text=text.replace(before,after,1)
    restored=text
    for before,after in reversed(REPLACEMENTS):restored=restored.replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('SKU_COMPOSITE_CHILD_COMPONENT_NOT_RECOVERED')
    compile(text,'sku_current_parent_component','exec')
    return text,dict(original=PIN,derived_sha256=sha256(text.encode()).hexdigest(),exact_routes=3,
        complete_original_recovered=True,all_case_assertions_and_used_guard_unchanged=True,
        actual_composite_cases=0,production_go=False)


def load_prepared(product,parent_raw,sku_raw,scheduler_quiet):
    admission.admitted(parent_raw,sku_raw)  # Before files or inherited ERP imports.
    from sku_current_parent_assembly import source_manifest
    source_manifest()
    path=FROZEN/ORIGINAL
    if not path.is_file()or path.is_symlink():raise ValueError('SKU_COMPOSITE_REGULAR_CHILD_COMPONENT_REQUIRED')
    text,proof=derive(path.read_bytes())
    module=ModuleType('current_parent_exact_accepted_SKU_component')
    # ROOT in the exact component now owns only its NEW output namespace.
    # The explicit case path above still selects the frozen accepted child.
    module.__file__=str(HERE/'sku_current_parent_component.py')
    module._CURRENT_SKU_ASSEMBLY=product;module._FROZEN_SKU=FROZEN
    exec(compile(text,module.__file__+':exact-derived-component','exec'),module.__dict__)
    if module.ROOT!=ROOT or module.LABEL!=LABEL:raise ValueError('SKU_COMPOSITE_OWNING_OUTPUT_NAMESPACE')
    return SimpleNamespace(CASE=CASE,LABEL=LABEL,exercise=module.exercise,scheduler_quiet=scheduler_quiet),proof
