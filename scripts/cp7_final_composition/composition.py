"""Prepared natural final sources, with no executable composite admission.

Importing this module uses the standard library only. Explicit read-only
source inspectors may load the actual natural parent graph. Business entry
methods and runtime() refuse before any ERP import or cursor access.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.final-composition-parent-adapters-prepared.v1'
CLOSED='CP7_FINAL_COMPOSITION_CLOSED_EXACT_COMPONENT_AND_GLOBAL_PROOFS_UNBOUND'
DOMAINS=('D1','E','SKU','S03','S05')


def validate_bindings(value):
    if(value['contract']!=CONTRACT or value['phase']!='SOURCE_PARENT_ADAPTERS_ONLY'
       or value['runtime_entry']is not None or value['global_parent_binding']is not None
       or value['accepted_component_bindings']!=dict.fromkeys(DOMAINS)
       or value['actual_execution_authorized']is not False
       or value['production_go']is not False
       or type(value['actual_Native_Auth_HTTP_browser_races'])is not int
       or value['actual_Native_Auth_HTTP_browser_races']!=0):
        raise ValueError('CP7_FINAL_COMPOSITION_EXACT_NULL_PREPARATION_BINDINGS_REQUIRED')
    return value


def bindings():return validate_bindings(json.loads((HERE/'BINDINGS.json').read_bytes()))


def parent():
    from cp7_accessory_standard_report import stage
    return stage


def sources():
    """Source inspection only; return the real unprojected S05 parent graph."""
    bindings()
    return dict(contract=CONTRACT,predecessor=parent().sources(),
        files={str((HERE/name).relative_to(ROOT)):sha256((HERE/name).read_bytes()).hexdigest()
               for name in('__init__.py','composition.py','BINDINGS.json')},
        runtime_entry=None,accepted_component_bindings=dict.fromkeys(DOMAINS),global_parent_binding=None,
        installed_or_catalog_verified=False,production_go=False,independent_acceptance=False)


def source_runtime():
    """Explicit source-only forwarding, never an installation capability."""
    bindings()
    value=parent().parent().runtime()
    if not isinstance(value,tuple)or len(value)!=5 or not all(isinstance(x,ModuleType)for x in value):
        raise ValueError('CP7_FINAL_COMPOSITION_REAL_FIVE_MODULE_RUNTIME_REQUIRED')
    return value


def _refuse():
    bindings()
    # Phase 2 deliberately has no path that can promote edited metadata into
    # permission to execute; a separately reviewed runtime successor is needed.
    raise ValueError(CLOSED)


def runtime():
    _refuse()
    return source_runtime()


def install(cur):_refuse()
def install_delta(cur,prior):_refuse()
def verify(cur,state):_refuse()
def rollback_delta_preuse(cur,state):_refuse()
def rollback_preuse(cur,state):_refuse()
