"""Five additional full-restore faults for the two exact late function bodies."""
from copy import deepcopy


def run(cur,backup,refused,bind,model_metadata,catalog,composed):
    for name,path in [('CHANGED_QUALIFIED_KERNEL_SOURCE','qualified-kernel.sql'),
                      ('CHANGED_QUALIFIED_PROVENANCE_SOURCE','qualified-provenance-hooks.sql')]:
        altered=deepcopy(backup)
        altered['sources']['current_installation']['predecessor']['predecessor']['predecessor']['performance']['files'][path]='0'*64
        refused(name,lambda b=altered:bind(b,catalog.digest(b)),'FROZEN_PUBLIC_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    for name,signature in [('PERFORMANCE_RESOLVE_AUTHORITY_METADATA_DRIFT','cp7_product_analog_consumer.resolve(jsonb,text,jsonb)'),
                           ('PERFORMANCE_BASELINE_AUTHORITY_METADATA_DRIFT','cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)')]:
        assert signature in composed.predecessor.predecessor.predecessor.performance.FUNCTIONS
        refused(name,lambda s=signature:model_metadata(s),'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
    def dependency():
        cur.execute('create view public.current_performance_restore_dependency as select cp7_product_analog_consumer.resolve(null,null,null) value')
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('NEW_PERFORMANCE_FUNCTION_DEPENDENCY',dependency,'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
