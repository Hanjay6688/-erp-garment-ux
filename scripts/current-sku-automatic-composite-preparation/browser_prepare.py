"""Derive both full real-App journeys with current source and value checks."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('current_browser_journey_source_contract', HERE / 'browser_preflight.py')
preflight = importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
ORIGINAL = ROOT / 'scripts/current-sku-managed-recovery-native27-qualification/browser.mjs'

ADMITTED = """function admitted(){
 const raw=execFileSync('python',[resolve(ROOT,'scripts/current-sku-automatic-composite-preparation/browser_source.py')],
  {cwd:ROOT,encoding:'utf8',maxBuffer:128*1024*1024,timeout:180000})
 const actual=JSON.parse(raw)
 assert.equal(actual.status,'COMPLETE_CURRENT_PRODUCT_SOURCE_ADMITTED_NOT_BROWSER_OR_FINANCIAL_ACCEPTANCE')
 assert.equal(actual.qualification_commit,process.env.GITHUB_SHA)
 assert.equal(execFileSync('git',['-C',ROOT,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),actual.qualification_commit)
 assert.equal(actual.source_projected,false);assert.equal(actual.database_calls,0)
 assert.equal(actual.real_case_success_not_implied,true)
 assert.equal(actual.actual_ERP_cases,0);assert.equal(actual.actual_Auth_HTTP_cases,0);assert.equal(actual.actual_browser_cases,0)
 assert.deepEqual(actual.source_database_network_guard.attempts,[])
 assert.deepEqual(actual.source_database_network_guard.network_nonGit_attempts,[])
 assert.equal(typeof actual.complete_current_source_admission,'object')
 assert(actual.complete_current_source_admission!==null)
 assert.equal(actual.current_browser_fixture_binding.complete_original_recovered,true)
 return{backend_candidate:actual.qualification_commit,case_ids:IDS,
  source_sha256:createHash('sha256').update(raw).digest('hex'),entire_current_source_admission:actual}
}
"""


def derive(raw=None):
    if raw is None:raw = ORIGINAL.read_bytes()
    require = preflight.assembly.require
    require(preflight.assembly.admission.pin(raw) == preflight.PINS['browser'], 'CURRENT_SKU_EXACT_COMPLETE_REAL_APP_JOURNEYS_REQUIRED')
    original = raw.decode()
    first = original.index('function admitted(){')
    last = original.index('\nasync function success', first)
    source_gate = original[first:last]
    routes = (
        ("{IDS,equalCensus,pairOnly,previewOracle,postedOracle,observeConsole,requireConsoleEvidence,readable} from '../current-sku-pair-browser-qualification/evidence.mjs'",
         "{IDS,equalCensus,pairOnly,previewOracle,postedOracle,observeConsole,requireConsoleEvidence,readable,inverseOracle} from './browser_evidence.mjs'"),
        ('../auditor/scripts/current-sku-managed-recovery-native27-qualification/browser_fixture.py',
         '../auditor/scripts/current-sku-automatic-composite-preparation/browser_fixture.py'),
        (source_gate, ADMITTED.rstrip()),
        ("'nilai sumber Rp 60,06'", "'nilai sumber Rp 68,07'"),
        ("one_complete_group_two_Native_parts_value:'60.06'",
         "one_complete_group_two_Native_parts_physical_value:'60.06',moving_average_value:'68.07'"),
        ("const final=state('WHOLE_GROUP_REVERSED')", "const final=state('WHOLE_GROUP_REVERSED');inverseOracle(final,f)"),
    )
    text = original
    for before, after in routes:
        require(text.count(before) == 1 and after not in text, 'CURRENT_SKU_ONE_REAL_BROWSER_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    recovered = text
    for before, after in reversed(routes):
        require(recovered.count(after) == 1, 'CURRENT_SKU_ONE_REAL_BROWSER_INVERSE_ROUTE_REQUIRED')
        recovered = recovered.replace(after, before, 1)
    require(recovered.encode() == raw, 'CURRENT_SKU_COMPLETE_REAL_APP_JOURNEYS_NOT_RECOVERED')
    return text, dict(retained=preflight.PINS['browser'], derived=preflight.assembly.admission.pin(text.encode()),
                      exact_reversible_routes=len(routes), complete_original_recovered=True,
                      real_Auth_normal_App_PostgREST_reconcile_inverse_census_and_console_checks_preserved=True,
                      native_physical_60_06_and_economic_average_68_07_both_required=True,
                      runtime_copy_and_final_packet_integration_still_pending=True,
                      actual_Auth_HTTP_cases=0, actual_browser_cases=0, actual_ERP_cases=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--check', action='store_true', required=True);parser.parse_args()
    text, proof = derive()
    if (HERE / 'browser.mjs').read_bytes() != text.encode():raise ValueError('CURRENT_SKU_EXACT_REVIEWABLE_REAL_BROWSER_MODULE_REQUIRED')
    print(json.dumps(proof, sort_keys=True))
