"""Eight new full-restore faults for the three frozen/public composition layers."""
from copy import deepcopy

def run(cur,backup,refused,bind,model_metadata,catalog,composed):
    for name,depth in [('CHANGED_FROZEN_PUBLIC_COMPOSER_SOURCE',0),('CHANGED_FROZEN_FINANCE_COMPOSER_SOURCE',1),('CHANGED_FROZEN_UNITS_COMPOSER_SOURCE',2)]:
        b=deepcopy(backup);source=b['sources']['current_installation']
        for _ in range(depth):source=source['predecessor']
        source['entrypoint_sha256']='0'*64
        refused(name,lambda value=b:bind(value,catalog.digest(value)),'FROZEN_PUBLIC_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    for name,signature in [
        ('PUBLIC_FROZEN_FINANCE_AUTHORITY_DRIFT','public.erp_cp7_request_bounded_frozen_finance_analysis_v2(jsonb,uuid)'),
        ('PUBLIC_FROZEN_OPERATIONAL_AUTHORITY_DRIFT','public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)'),
        ('PRIVATE_FROZEN_FINANCE_AUTHORITY_DRIFT','cp7_current_frozen_finance.request_finance(jsonb,uuid)'),
        ('PRIVATE_FROZEN_UNITS_AUTHORITY_DRIFT','cp7_frozen_analysis_units_v2.request(jsonb,uuid)')]:
        refused(name,lambda s=signature:model_metadata(s),'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
    def dependency():
        cur.execute('create view public.current_frozen_public_restore_dependency as select public.erp_cp7_request_bounded_frozen_finance_analysis_v2(null,null) value')
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('NEW_FROZEN_PUBLIC_FUNCTION_DEPENDENCY',dependency,'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
