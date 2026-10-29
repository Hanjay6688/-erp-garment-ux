"""Load the actual dependency graph with empty imported CLI, without a DB."""
from pathlib import Path
import importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
original=sys.argv
try:
    sys.argv=sys.argv[:1]
    spec=importlib.util.spec_from_file_location('sku_group_cost_prepared_import',HERE/'cases.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
finally:sys.argv=original

assert module.NATIVE7_ADMISSION is None
try:module.cases(None,None)
except AssertionError as error:assert str(error)=='SKU_COST_REQUIRES_PRIOR_ACTUAL_NATIVE7_PASS',str(error)
else:raise AssertionError('SKU_COST_CALLBACKS_RAN_WITHOUT_NATIVE7')
print(json.dumps(dict(status='PREPARED_IMPORT_ADMITTED_AND_UNADMITTED_CALLBACKS_REFUSED',case_ids=module.IDS,no_database_opened=True,actual_runtime_execution=False)))
