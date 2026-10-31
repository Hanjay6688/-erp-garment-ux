"""One unchanged access callback with a real additional Owner fixture.

The whole original S05 component retains reader intervals, original strict
group restore and separate committed Native use. No Native10/37 claim.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACCESS='S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL'
LABEL='CP7_S05_ON_SKU_OWNER_ACCESS_NATIVE1_CASES'
CASE='CURRENT_S05_OWNER_ACCESS_NATIVE1_WITH_EXTRA_OWNER'
CHANGES=(
 ("CASE = 'S05_ON_SKU_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE'","CASE = '"+CASE+"'"),
 ("LABEL = 'CP7_S05_ON_SKU_NATIVE10_CASES'","LABEL = '"+LABEL+"'"),
 ("qualification_scope='READ_ONLY_S05_NATIVE10_WITH_RETAINED_PARENT'","qualification_scope='OWNER_ACCESS_NATIVE1_WITH_ADDITIONAL_REAL_OWNER'"),
 ("                    active['id'] = name\n                    return operation()",
  "                    active['id'] = name\n                    __JOIN_FORCE_EXTRA_OWNER__(cursor,business,report)\n                    return operation()"),
 ("return [(name, wrapped(name, operation)) for name, operation in selected]",
  "return [(name, wrapped(name, operation)) for name, operation in selected if name == '"+ACCESS+"']"),
 ('exact_group(actual, business.IDS)',"exact_group(actual, ('"+ACCESS+"',))"),
 ('actual_Native_cases=len(business.IDS)','actual_Native_cases=1'),
)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def prepared_sources():
    bridge=load('owner_focus_unchanged_S05_source_bridge',HERE/'native_s05.py')
    raw=(ROOT/bridge.ORIGINAL).read_bytes();source,parent=bridge.derive_component(raw)
    text=source
    for before,after in CHANGES:
        if text.count(before)!=1 or after in text:raise ValueError('OWNER_FOCUS_EXACT_SOURCE_ANCHOR_REQUIRED:'+before)
        text=text.replace(before,after,1)
    reverse=text
    for before,after in reversed(CHANGES):reverse=reverse.replace(after,before,1)
    if reverse!=source:raise ValueError('OWNER_FOCUS_WHOLE_NATIVE10_COMPONENT_NOT_RECOVERED')
    compile(text,str(ROOT/bridge.ORIGINAL),'exec')
    return text,dict(parent=parent,focused_changes=len(CHANGES),whole_original_component_recovered=True,
        derived_sha256=sha256(text.encode()).hexdigest(),original_business_callback_changes=0,
        planned_Native_cases=1,actual_Native_cases=0,full37_qualified=False)


def component():
    bridge=load('owner_focus_real_S05_binding',HERE/'native_s05.py')
    load('owner_focus_closed_current_source',HERE/'source.py').preflight()
    text,proof=prepared_sources();module=ModuleType('owner_focus_private_complete_S05_component')
    module.__file__=str(ROOT/bridge.ORIGINAL)
    module.__dict__.update(__S05_SKU_BUSINESS_FACTORY__=bridge.business,
        __JOIN_FORCE_EXTRA_OWNER__=load('owner_focus_actual_additional_owner',HERE/'owner_fixture.py').force_additional_owner)
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    module.scheduler_quiet=lambda url:load('owner_focus_original_scheduler_quiet',
        ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)
    return module,proof
