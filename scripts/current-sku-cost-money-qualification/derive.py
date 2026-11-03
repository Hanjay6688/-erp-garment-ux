"""Whole package derivation; original restore, authority and five gates remain."""
from hashlib import sha256
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def derive(raw):
    path=ROOT/'scripts/current-sku-moving-average-qualification/derive.py'
    if sha256(path.read_bytes()).hexdigest()!='3662343c0acd669c6d28d7794cce54ef1c3254db53674c57ae10b701adf4de80':
        raise ValueError('SKU_MONEY_ORIGINAL_COMPLETE_DERIVER_CHANGED')
    spec=importlib.util.spec_from_file_location('sku_money_original_whole_package_deriver',path)
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    source,proof=prior.derive(raw)
    if proof['original_sha256']!='c420d894f8d5f16bddefeae73addb621507170f372a28e7d6e33d88c7eeb0be9' or proof['derived_sha256']!='1b994775a24d21e25b4788670d961344be9bee88a6e23a2db9d91173174b160e':
        raise ValueError('SKU_MONEY_ORIGINAL_WHOLE_PACKAGE_CHANGED')
    old="'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL'";new="'EXACT_QUALIFIED_MOVAVG_PARENT_INSTALL'"
    if source.count(old)!=1:raise ValueError('SKU_MONEY_PARENT_LABEL_ANCHOR_CHANGED')
    derived=source.replace(old,new,1)
    if derived.replace(new,old,1)!=source:raise ValueError('SKU_MONEY_PARENT_LABEL_NOT_REVERSIBLE')
    compile(derived,'whole-vendor-package-derived','exec')
    return derived,dict(original=proof,derived_sha256=sha256(derived.encode()).hexdigest(),
        additional_changes=1,full_module_compile=True,complete_install_preuse_used_guard_backup_restore_roles_data_sequences_advisors_retained=True)
