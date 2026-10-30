"""Public prepared product + authentic qualified21 prerequisite, no fresh credit."""
from pathlib import Path
from types import ModuleType
import importlib.util

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def historical():
    d=load('sku27_historical_full_private_deriver',HERE/'derive.py');text,proof=d.derive('historical_admission')
    module=ModuleType('sku27_authentic_qualified21_admission');module.__file__=str(ROOT/d.SOURCES['historical_admission'][0])
    exec(compile(text,module.__file__,'exec'),module.__dict__);return module,proof

def retained(product):
    module,_=historical();proof=module.retained(product);assert proof['fresh_cases_credited']==0;return proof

def preflight(*,require_clean=True):
    source=load('sku27_full_current_source',HERE/'closure.py').source_only(require_clean=require_clean)
    negative=load('sku27_retained_first602',HERE/'first602.py').verified()
    return dict(source=source,retained_failed602=negative)

def admitted(product,derivation):
    source=preflight();module,proof=historical();old=module.admitted(product,derivation)
    transition=load('sku27_current_actual_product',HERE/'transition.py');transition.historical_sources(product)
    return dict(status='EXACT_QUALIFIED21_AND_ACTUAL_CURRENT_F3D_NATIVE27_SOURCE_ADMITTED',current_installation=product.sources(),
      current_source_transition=transition.source_receipt(),full_source_closure=source['source'],
      first602=source['retained_failed602'],authentic_old_qualification=old,private_old_scope_derivation=proof,
      complete_engine_derivation=derivation,actual_successor_cases=0,group_recovery_supported=False,
      production_go=False,independent_acceptance=False)
