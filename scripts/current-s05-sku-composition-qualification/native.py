"""Prepare the qualified S05 Native10 component for the current SKU parent.

This module does not connect, install, commit, dispatch or claim acceptance.
An outer caller must admit the complete actual SKU27 Original and own the
disposable package/backup/restore boundary before invoking the component.
The normal-App component and outer caller are prepared; actual admission is pending.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = 'scripts/current-s05-native10-qualification/component.py'
FACTORY = 'scripts/current-s05-wib-owner-fixture-successor-qualification/factory.py'
CHANGES = (
    ("from cp7_vendor_receivable import composition as product",
     "from cp7_sku_pair_conversion import composition as product", 2),
    ("business = importlib.import_module('cp7_accessory_standard_report.cases')",
     "business = __S05_SKU_BUSINESS_FACTORY__(importlib.import_module('cp7_accessory_standard_report.cases'), state)", 1),
    ("CASE = 'S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE'",
     "CASE = 'S05_ON_SKU_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE'", 1),
    ("LABEL = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES'",
     "LABEL = 'CP7_S05_ON_SKU_NATIVE10_CASES'", 1),
    ("'S05_EXACT_INSTALLED_VENDOR_PARENT_REQUIRED'",
     "'S05_EXACT_INSTALLED_SKU_PARENT_REQUIRED'", 1),
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_component(raw):
    """Keep the complete reader intervals, strict group and inverse witness."""
    text = raw.decode()
    for before, after, count in CHANGES:
        if text.count(before) != count or after in text:
            raise ValueError('S05_SKU_EXACT_COMPONENT_ANCHOR_REQUIRED: '+before)
        text = text.replace(before, after)
    reverse = text
    for before, after, count in reversed(CHANGES):
        if reverse.count(after) != count:
            raise ValueError('S05_SKU_UNIQUE_COMPONENT_REVERSE_REQUIRED')
        reverse = reverse.replace(after, before)
    if reverse.encode() != raw:
        raise ValueError('S05_SKU_COMPONENT_REVERSE_BYTES_REQUIRED')
    return text, dict(original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),
        counted_change_groups=len(CHANGES), changed_occurrences=sum(c for _, _, c in CHANGES),
        original_bytes_recovered=True, original_Native10_callbacks_changed=0,
        all_strict_group_reader_ACL_data_sequences_inverse_checks_retained=True)


def bind_private_business(retained, state, factory, reader):
    """Change only the newly compiled private case module's stage dependency."""
    original_stage = retained.stage
    private = factory.business(retained, state)
    if private is retained or private.__dict__ is retained.__dict__:
        raise ValueError('S05_SKU_PRIVATE_CASE_MODULE_REQUIRED')
    if private.stage is not original_stage or retained.stage is not original_stage:
        raise ValueError('S05_SKU_ORIGINAL_STAGE_IDENTITY_REQUIRED')
    if private.IDS != retained.IDS or len(private.IDS) != 10:
        raise ValueError('S05_SKU_EXACT_NATIVE10_IDS_REQUIRED')
    for name in ('physical', 'issues', 'master', 'qc_source', 'sessions', 'b', 'prod'):
        if getattr(private, name) is not getattr(retained, name):
            raise ValueError('S05_SKU_RETAINED_NATIVE_DEPENDENCY_REQUIRED: '+name)
    private.stage = reader
    private.sku_parent_binding = dict(
        original_imported_case_module_unchanged=retained.stage is original_stage,
        private_reader_namespace='cp7_s05_sku_composition',
        original_Native10_callback_bytes_unchanged=True,
        qualified_WIB_and_active_owner_fixture_adapters_retained=True,
        actual_new_Native_credit=0)
    return private


def business(retained, state):
    load('s05_sku_source_before_private_binding', HERE/'source.py').preflight()
    from cp7_s05_sku_composition import stage
    factory = load('s05_sku_exact_519d_fixture_factory', ROOT/FACTORY)
    return bind_private_business(retained, state, factory, stage)


def component():
    """Prepare code only; the outer qualified caller remains mandatory."""
    proof = load('s05_sku_source_before_component', HERE/'source.py').preflight()
    raw = (ROOT/ORIGINAL).read_bytes()
    text, derivation = derive_component(raw)
    module = ModuleType('s05_sku_private_complete_Native10_component')
    module.__file__ = str(ROOT/ORIGINAL)
    module.__S05_SKU_BUSINESS_FACTORY__ = business
    exec(compile(text, module.__file__, 'exec'), module.__dict__)
    return module, dict(source=proof, component_derivation=derivation,
        actual_current_SKU27_original_admitted=False,
        actual_current_combined_Native_or_browser_credit=0)
