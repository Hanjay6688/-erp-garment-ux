"""Closed until Root accepts both actual full candidates and the owning entry."""
from hashlib import sha256
import json

PARENT_HEAD = None
PARENT_TREE = None
PARENT_ROOT_PIN = None
PARENT_SOURCE_PIN = None
PARENT_MODULE_PIN = None
SKU_HEAD = None
SKU_TREE = None
SKU_ROOT_PIN = None
SKU_SOURCE_PIN = None
RUNTIME_ENTRY = None


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def require_ready():
    constants = (PARENT_HEAD, PARENT_TREE, PARENT_ROOT_PIN, PARENT_SOURCE_PIN, PARENT_MODULE_PIN,
                 SKU_HEAD, SKU_TREE, SKU_ROOT_PIN, SKU_SOURCE_PIN, RUNTIME_ENTRY)
    if any(value is None for value in constants):
        raise ValueError("SKU_COMPOSITE_ACTUAL_MANDOR17_SKU6_ROOT_AND_OWNING_ENTRY_PENDING")


def admitted(parent_raw, sku_raw):
    require_ready()
    if pin(parent_raw) != PARENT_ROOT_PIN or pin(sku_raw) != SKU_ROOT_PIN:
        raise ValueError("SKU_COMPOSITE_EXACT_ROOT_ORIGINALS_REQUIRED")
    parent, sku = json.loads(parent_raw), json.loads(sku_raw)
    expected_parent = dict(status="ROOT_VERIFIED_CURRENT_MANDOR17_ALL5", head=PARENT_HEAD, tree=PARENT_TREE,
        actual_Native_cases=9, actual_Native_session_cases=4, actual_Auth_HTTP_cases=2,
        actual_browser_cases=2, actual_business_cases=17, complete17_qualified=True,
        package_all_five=True, prior_runs_aggregated=False, assembly_source=PARENT_MODULE_PIN, production_go=False,
        independent_acceptance=False)
    expected_sku = dict(status="ROOT_VERIFIED_CURRENT_SKU_MOVAVG_NATIVE6_ALL5", head=SKU_HEAD, tree=SKU_TREE,
        actual_Native_cases=6, complete6_qualified=True, package_all_five=True,
        prior_runs_aggregated=False, production_go=False, independent_acceptance=False)
    for value, expected in ((parent, expected_parent), (sku, expected_sku)):
        for key, item in expected.items():
            if type(value.get(key)) is not type(item) or value[key] != item:
                raise ValueError("SKU_COMPOSITE_ACTUAL_COMPLETE_PARENT_OR_CHILD_REQUIRED:" + key)
        if value.get("synthetic_receipt_not_an_actual_qualification") is True:
            raise ValueError("SKU_COMPOSITE_SYNTHETIC_RECEIPT_REFUSED")
    return dict(parent_root=pin(parent_raw), sku_root=pin(sku_raw), runtime_entry=RUNTIME_ENTRY,
                actual_composite_cases=0, production_go=False, independent_acceptance=False)
