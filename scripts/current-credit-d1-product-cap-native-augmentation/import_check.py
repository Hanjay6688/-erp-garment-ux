"""Import exact retained business + register adapter with connections forbidden."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for relative in('scripts','scripts/cp7_customer_credit/consumer',
                'scripts/cp7_customer_credit/reconciliation/native',
                'scripts/cp7_customer_credit/native','scripts/cp7_customer_credit/initial-settlement'):
    sys.path.insert(0,str(ROOT/relative))
arguments=sys.argv[:]
try:
    sys.argv=sys.argv[:1]
    with patch('psycopg.connect',side_effect=AssertionError('D1_CAP_NATIVE_LOCAL_IMPORT_FORBIDS_DB')):
        from cp7_credit_correction_de import cases as retained
        spec=importlib.util.spec_from_file_location('d1_cap_native_actual_factory_import',HERE/'factory.py')
        factory=importlib.util.module_from_spec(spec);spec.loader.exec_module(factory)
        before=dict(vars(retained));proxy=factory.business(retained)
        class NoSQL:
            def __getattr__(self,key):raise AssertionError('D1_CAP_NATIVE_NO_SQL_DURING_REGISTRATION:'+key)
        planned=proxy.cases(NoSQL(),None)
        assert tuple(key for key,_ in planned)==retained.IDS and len(planned)==13
        assert set(vars(retained))==set(before)and all(vars(retained)[key]is value for key,value in before.items())
        assert set(vars(proxy))==set(before)
        assert all(getattr(proxy,key)is value for key,value in before.items()if key!='cases')
        source,api=factory.guard.admit()
finally:
    sys.argv=arguments
print(json.dumps(dict(status='EXACT_RETAINED_IMPORT_AND13_REGISTRATION_PASS_NO_DB',
    case_ids=[key for key,_ in planned],only_proxy_attribute_changed='cases',imported_module_not_patched=True,
    source_files=len(source['files']),api_modules=len(api['modules']),api_bodies=len(api['functions']),
    Native_executed=False,production_go=False,independent_acceptance=False)))
