"""Reuse the complete current-parent package with money-only fresh counts."""
from hashlib import sha256
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL='scripts/current-vendor-receivable-qualification/probe.py'
RETAINED=ROOT/'scripts/current-sku-composite-preparation/sku_current_parent_package.py'
RETAINED_PIN=dict(bytes=2837,sha256='9e216e5face39f4c6eebfe75ab9bea1474fe2c6e1ae5855b41d21372e59a974a')
REPLACEMENTS=(
    ("'ACTUAL_ACCEPTED_MANDOR17_PARENT_INSTALL'","'ACTUAL_CURRENT_MANDOR_AND_MOVING_PARENT_INSTALL'"),
    ("'CURRENT_PARENT_SKU_NATIVE6_ONLY'","'CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'"),
)


def derive(raw):
    original=RETAINED.read_bytes()
    if dict(bytes=len(original),sha256=sha256(original).hexdigest())!=RETAINED_PIN:
        raise ValueError('SKU_CURRENT_MONEY_EXACT_RETAINED_OWNING_DERIVER_REQUIRED')
    spec=importlib.util.spec_from_file_location('current_money_retained_owning_package',RETAINED)
    retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
    source,prior=retained.derive(raw)
    modified=source
    for before,after in REPLACEMENTS:
        if modified.count(before)!=1 or after in modified:
            raise ValueError('SKU_CURRENT_MONEY_EXACT_PACKAGE_LABEL_ROUTE_REQUIRED')
        modified=modified.replace(before,after,1)
    restored=modified
    for before,after in reversed(REPLACEMENTS):restored=restored.replace(after,before,1)
    if restored!=source:raise ValueError('SKU_CURRENT_MONEY_RETAINED_PACKAGE_NOT_RECOVERED')
    compile(modified,'current_parent_money_whole_package','exec')
    return modified,dict(original=prior,retained_deriver=RETAINED_PIN,
        derived_sha256=sha256(modified.encode()).hexdigest(),additional_label_routes=2,
        complete_retained_package_recovered=True,whole_backup_restore_all_five_and_authority_unchanged=True,
        prior_parent_cases_not_counted_as_fresh=True,actual_composite_cases=0,production_go=False)
