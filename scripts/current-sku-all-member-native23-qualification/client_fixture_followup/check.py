"""Supplemental model15 closure only. Never opens a database or writes sources."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def check():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,pin in source['files'].items():
        raw=(ROOT/path).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('SKU_SUPPLEMENTAL15_EXACT_SOURCE_CHANGED:'+path)
    spec=importlib.util.spec_from_file_location('sku_private_model15_derive',HERE/'derive.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw,proof=module.derive((ROOT/module.ORIGINAL).read_bytes())
    if raw!=(ROOT/module.DERIVED).read_bytes():raise ValueError('SKU_SUPPLEMENTAL15_DERIVATION_CHANGED')
    declared=json.loads((HERE/'DERIVATION.json').read_bytes())
    for key,value in proof.items():
        if declared[key]!=value:raise ValueError('SKU_SUPPLEMENTAL15_DECLARED_DERIVATION_CHANGED:'+key)
    if sha256((HERE/'native_downstream.sql').read_bytes()).hexdigest()!='f65dc3f4888809d0566095f7d5c7a59a6103cfa83f688aef679845d6fba85045':
        raise ValueError('SKU_SUPPLEMENTAL15_NATIVE_DOWNSTREAM_BODY_CHANGED')
    original=json.loads((HERE/'evidence/ORIGINAL_RESOLVED_RUNTIME15.json').read_bytes())
    if (original['numTotalTests'],original['numPassedTests'],original['numFailedTests'],original['numPendingTests'])!=(15,14,1,0):
        raise ValueError('SKU_SUPPLEMENTAL15_FIRST_MISSING_RELATION_FAILURE_MUST_REMAIN')
    failed=[row for suite in original['testResults']for row in suite['assertionResults']if row['status']=='failed']
    # The unchanged original assertion lets Vitest truncate the actual error.
    # Preserve/check its exact observable prefix; do not manufacture a full raw error.
    if len(failed)!=1 or failed[0]['title']!=proof['same15_test_IDs'][8] or 'relation "erp.be_conversion_sources_v'not in '\n'.join(failed[0]['failureMessages']):
        raise ValueError('SKU_SUPPLEMENTAL15_FIRST_MISSING_RELATION_PREFIX_REQUIRED')
    first=json.loads((HERE/'evidence/DERIVED_FIRST15.json').read_bytes())
    if (first['numTotalTests'],first['numPassedTests'],first['numFailedTests'],first['numPendingTests'])!=(15,9,6,0):
        raise ValueError('SKU_SUPPLEMENTAL15_FIRST_OWN_MODEL_ERROR_MUST_REMAIN')
    first_failures=[row for suite in first['testResults']for row in suite['assertionResults']if row['status']=='failed']
    if len(first_failures)!=6 or any('column reference "source_id" is ambiguous'not in '\n'.join(row['failureMessages'])for row in first_failures):
        raise ValueError('SKU_SUPPLEMENTAL15_EXACT_FIRST_OWN_MODEL_AMBIGUITY_REQUIRED')
    final=json.loads((HERE/'evidence/DERIVED_FINAL15.json').read_bytes())
    if (final['numTotalTests'],final['numPassedTests'],final['numFailedTests'],final['numPendingTests'])!=(15,15,0,0):
        raise ValueError('SKU_SUPPLEMENTAL15_COMPLETE_LOCAL_MODEL_PASS_REQUIRED')
    observed=[row['title']for suite in final['testResults']for row in suite['assertionResults']]
    if observed!=proof['same15_test_IDs']:raise ValueError('SKU_SUPPLEMENTAL15_OBSERVED_IDS_CHANGED')
    if source['main72_modified']is not False or type(source['Native_executions'])is not int or source['Native_executions']!=0:
        raise ValueError('SKU_SUPPLEMENTAL15_NO_MAIN_OR_NATIVE_CREDIT_ALLOWED')
    return dict(status='PASS_SUPPLEMENTAL_LOCAL_MODEL15_SOURCE_ONLY',source_files=len(source['files']),
        main72_modified=False,supplemental_model_tests=15,original_assertion_lines=proof['original_assertion_lines'],
        Native_executions=0,actual_Auth=0,actual_browser=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check()))
