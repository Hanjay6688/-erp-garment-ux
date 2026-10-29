"""Exact prepared source binding, with no database or execution side effects."""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BACKEND='21c69cf25defcee854beb08e998062d7e883d968'
TREE='a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e'

def admitted(root=ROOT):
    file=root/'scripts/current-sku-group-cost-qualification/SOURCE.json';pins=json.loads(file.read_bytes())
    assert pins['backend_candidate']==dict(commit=BACKEND,tree=TREE),'SKU_COST_BACKEND_PIN_CHANGED'
    assert len(pins['case_ids'])==len(set(pins['case_ids']))==3,'SKU_COST_THREE_CASES_REQUIRED'
    required=('scripts/current-sku-pair-conversion-qualification/fixture.py','scripts/cp6_bc_probe.py','scripts/cp6_bd_probe.py',
      'scripts/cp7_sku_pair_conversion/conversion.sql','scripts/cp7_ow04_restore_bundle.py',
      'scripts/current-sku-group-cost-qualification/cases.py','scripts/current-sku-group-cost-qualification/oracle.py')
    assert all(path in pins['files']for path in required),'SKU_COST_SOURCE_PIN_MISSING'
    assert pins['Native7_PASS_required_before_callbacks']is True and pins['first_case_scope']=='NATIVE_SAFETY_REFUSAL_ONLY','SKU_COST_COVERAGE_BOUNDARY_CHANGED'
    for path,expected in pins['files'].items():
        assert sha256((root/path).read_bytes()).hexdigest()==expected,('SKU_COST_SOURCE_CHANGED',path)
    return dict(status='SKU_COST_PREPARED_EXACT_SOURCE_NOT_RUNTIME_PASS',backend_candidate=pins['backend_candidate'],case_ids=pins['case_ids'],
      source_files=len(pins['files']),source_manifest_sha256=sha256(file.read_bytes()).hexdigest(),
      actual_Native_execution=False,actual_Auth_browser=False,whole_group_recovery_capability=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':print(json.dumps(admitted(),indent=2))
