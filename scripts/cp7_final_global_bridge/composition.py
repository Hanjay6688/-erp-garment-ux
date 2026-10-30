"""Natural SKU source parent with an unimplemented, permanently closed bridge.

The source/runtime readers inspect actual canonical modules. No install,
verification, inverse or catalog claim is supplied by this placeholder.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.final-global-bridge-closed-source.v1'
CLOSED='CP7_FINAL_GLOBAL_BRIDGE_CLOSED_NO_OWNING_RUNTIME_OR_CATALOG'


def closed_metadata():
    value=json.loads((HERE/'CLOSED.json').read_bytes())
    if(value['contract']!=CONTRACT or value['runtime_entry']is not None
       or value['accepted_parent_binding']is not None or value['Native19_runtime_profile_binding']is not None
       or value['writer_or_phantom_lock_closed']is not False
       or type(value['global_hooks_installed'])is not int or value['global_hooks_installed']!=0
       or value['actual_execution_authorized']is not False):
        raise ValueError('CP7_FINAL_GLOBAL_BRIDGE_EXACT_CLOSED_METADATA_REQUIRED')
    return value


def parent():
    from cp7_sku_pair_conversion import composition
    return composition


def sources():
    closed_metadata()
    return dict(contract=CONTRACT,predecessor=parent().sources(),
        files={str((HERE/name).relative_to(ROOT)):sha256((HERE/name).read_bytes()).hexdigest()
               for name in('__init__.py','composition.py','CLOSED.json')},
        runtime_entry=None,accepted_parent_binding=None,catalog_verified=False,
        global_hooks_installed=0,qualification_only=True,production_go=False,independent_acceptance=False)


def runtime():
    """Read-only natural five-module runtime forwarding; it opens no database."""
    closed_metadata()
    value=parent().runtime()
    if not isinstance(value,tuple)or len(value)!=5 or not all(isinstance(x,ModuleType)for x in value):
        raise ValueError('CP7_FINAL_GLOBAL_BRIDGE_REAL_FIVE_MODULE_RUNTIME_REQUIRED')
    return value


def _refuse():
    closed_metadata()
    raise ValueError(CLOSED)


def install(cur):_refuse()
def install_delta(cur,prior):_refuse()
def verify(cur,state):_refuse()
def rollback_delta_preuse(cur,state):_refuse()
def rollback_preuse(cur,state):_refuse()
