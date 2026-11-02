"""Exact template-copy authority preservation for three fixed local DB names."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import ast,subprocess

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL='scripts/ow04-payment-current-qualification/copy_authority.py'
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(3895, 'cfdc3b899e335dd13a9456242ed5158b718ac5c56d9b1ebf06c4571eda2cc7a2')
BEFORE="assert name in('cp6_auditor_browser','cp6_auditor_http')"
AFTER="assert name in('cp6_auditor_browser','cp6_auditor_http','cp6_auditor_race')"

def derive(raw):
    if PIN is None or (len(raw),sha256(raw).hexdigest())!=PIN:
        raise ValueError('NONPAYABLE_EXACT_ORIGINAL_COPY_AUTHORITY_SOURCE_REQUIRED')
    original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGINAL_BASE+':'+ORIGINAL])
    if raw!=original:raise ValueError('NONPAYABLE_COPY_AUTHORITY_ORIGINAL_PUBLIC_BYTES_REQUIRED')
    text=raw.decode()
    if text.count(BEFORE)!=1 or AFTER in text:raise ValueError('NONPAYABLE_ONE_EXACT_COPY_NAME_EXTENSION_REQUIRED')
    derived=text.replace(BEFORE,AFTER,1)
    if derived.replace(AFTER,BEFORE,1).encode()!=raw:
        raise ValueError('NONPAYABLE_COPY_AUTHORITY_ORIGINAL_NOT_RECOVERED')
    ast.parse(derived)
    return derived,dict(original_bytes=len(raw),original_sha256=PIN[1],derived_sha256=sha256(derived.encode()).hexdigest(),
        exact_copy_name_extension_count=1,original_bytes_recovered=True,all_raw22_authority_checks_unchanged=True,
        product_or_schema_or_RPC_grants_added=False,actual_SQL_executed=0,actual_case_credit=0)

@contextmanager
def scope(modes,state):
    from . import admission,assembly
    admission.parent_receipt()  # Before ERP graph import or any copy operation.
    text,proof=derive((ROOT/ORIGINAL).read_bytes())
    _,_,_,_,catalog=assembly.runtime()
    adapter=ModuleType('afui_exact_original_copy_authority_with_third_fixed_copy')
    adapter.__file__=str(ROOT/ORIGINAL)
    exec(compile(text,adapter.__file__,'exec'),adapter.__dict__)
    previous=modes.copy_db
    adapter.ORIGINAL_COPY_DATABASE=previous
    adapter.STATE=dict(installed_catalog=state['after'])
    def verify(cur,actual):
        if actual is not adapter.STATE:raise ValueError('NONPAYABLE_EXACT_COPY_ADAPTER_STATE_REQUIRED')
        return assembly.verify(cur,state)
    adapter.PRODUCT=SimpleNamespace(catalog=catalog,verify=verify)
    modes.copy_db=adapter.copy_database
    try:yield dict(source=proof,actual_copy_admissions=adapter.COPY_ADMISSIONS)
    finally:modes.copy_db=previous
