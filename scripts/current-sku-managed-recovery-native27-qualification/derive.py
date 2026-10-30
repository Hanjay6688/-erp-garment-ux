"""Whole retained modules, reversible source/case-count adapters only."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NS='scripts/current-sku-managed-recovery-native27-qualification'
OLD_NS='scripts/current-sku-all-member-native23-qualification'
path=ROOT/OLD_NS/'derive.py';spec=importlib.util.spec_from_file_location('sku27_frozen_602_private_deriver',path)
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
SOURCES=legacy.SOURCES

EXTRA={
 'races':(
  ("def exercise(tools,today,*,same_uuid,first_commit):",
   "_schedule_spec=importlib.util.spec_from_file_location('sku27_actual_pocket_schedule',HERE.parents[1]/'"+NS+"/race_schedule.py')\nschedule=importlib.util.module_from_spec(_schedule_spec);_schedule_spec.loader.exec_module(schedule)\n_native_spec=importlib.util.spec_from_file_location('sku27_race_full_census',HERE.parents[1]/'"+NS+"/cost_cases.py')\n_native=importlib.util.module_from_spec(_native_spec);_native_spec.loader.exec_module(_native)\n\ndef exercise(tools,today,*,same_uuid,first_commit):"),
  ("held,contention,outcome=tools.two_sessions(lambda cur:f.action(cur,'POST',payload,first),lambda cur:f.action(cur,'POST',payload,second),first_commit)",
   "held,contention,outcome=schedule.run(tools,lambda cur:f.action(cur,'POST',payload,first),lambda cur:f.action(cur,'POST',payload,second),first_commit,same_uuid=same_uuid,native_fixture=_native.n)"),
  ("assert contention.get('kind')=='BLOCKED'and contention.get('holder_blocks_worker')is True,contention",
   "schedule.require_contention(contention,same_uuid)"),
 ),
 'probe':(
  ("deriver = load('sku_full_counted_vendor_derivation', HERE / 'derive.py')","deriver = load('sku_full_counted_vendor_derivation', ROOT / '"+NS+"/engine_delta.py')"),
  ("engine.LABEL = 'CP7_SKU_ALL_MEMBER_NATIVE23'","engine.LABEL = 'CP7_SKU_MANAGED_RECOVERY_NATIVE27'"),
 ),
 'runner':(
  ("CASE = 'SKU_BASE_NATIVE7_COST_NATIVE3_RACES3_NATIVE_WAITS6_AUTH_BROWSER4'","CASE = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'"),
  ("label = 'CP7_SKU_GROUP_COST_NATIVE3'","label = 'CP7_SKU_GROUP_COST_NATIVE5'"),
  ("actual = helper.control.native.strict_group(label, cost.cases, verify)","""extra = load('sku27_two_capacity_cases', ROOT / '"""+NS+"""/recovery_cases.py')
            prefix = load('sku27_cost_sequence_prefix', ROOT / '"""+NS+"""/sequence_prefix.py')
            def selected(cursor, today):
                old = cost.cases(cursor, today)
                assert tuple(key for key, _ in old) == tuple(cost.IDS)
                return prefix.wrap(old + extra.cases(cursor, today, native_fixture=cost.n),
                    SimpleNamespace(capture_current=lambda: cost.n.capture(cursor)))
            actual = helper.control.native.strict_group(label, selected, verify)"""),
  ('gate.exact_native(actual, cost.IDS, 3)',"gate.exact_native(actual, tuple(cost.IDS) + tuple(extra.IDS), 5)"),
  ('actual_cost_Native_cases=3','actual_cost_Native_cases=5'),
  ("fresh_cost_native3","fresh_cost_native5"),
  ("fresh_callbacks9","fresh_callbacks11"),
  ("cost_ids = load('sku_combined_cost_plan', HERE / 'plan.py').COST_IDS","cost_ids = load('sku_combined_cost_plan', HERE / 'plan.py').COST_IDS + load('sku27_positive_ids', ROOT / '"+NS+"/recovery_cases.py').IDS"),
  ("gate.exact_native(cost.get('native', {}), cost_ids, 3)","gate.exact_native(cost.get('native', {}), cost_ids, 5)"),
  ("assert snapshot(url, state, product) == before, 'SKU_COMBINED_COST_NATIVE_SAVEPOINT_CHANGED_SOURCE_ROWS_OR_CATALOG'","""prefix = load('sku27_complete_positive_sequence_boundary', ROOT / '"""+NS+"""/sequence_prefix.py')
    after_cost = snapshot(url, state, product)
    report['cost_strict_rollback_and_sequence_prefix'] = prefix.strict_rollback(before, after_cost)
    chain = prefix.sequences(before['data'])
    for key in cost_ids:
        receipt = cost['native']['cases'][key]['complete_case_sequence_prefix']
        assert receipt['before'] == chain, ('SKU27_UNATTRIBUTED_SEQUENCE_BEFORE_CASE', key)
        chain = receipt['after']
    assert chain == prefix.sequences(after_cost['data']), 'SKU27_UNATTRIBUTED_SEQUENCE_AFTER_COST_GROUP'
    before = after_cost"""),
  ("ROOT / 'scripts/current-sku-combined-fixture-followup/concurrency.py'","ROOT / '"+NS+"/concurrency.py'"),
  ("second['concurrency']['counts'] == {'PASS': 9}","second['concurrency']['counts'] == {'PASS': 11}"),
  ("set(plans.RACE_IDS + plans.WAIT_IDS)","set(plans.RACE_IDS + plans.WAIT_IDS + load('sku27_session_ids', ROOT / '"+NS+"/recovery_sessions.py').IDS)"),
  ("len(second['copy_catalog_admissions']) == 9","len(second['copy_catalog_admissions']) == 11"),
  ("len(cases) == 23","len(cases) == 27"),
  ("business_counts={'PASS': 23}, actual_Native_cases=10","business_counts={'PASS': 27}, actual_Native_cases=12"),
  ("base_Native_cases=7, cost_Native_cases=3, actual_two_session_races=3,","base_Native_cases=7, cost_Native_cases=5, actual_two_session_races=3,"),
  ("actual_Native_session_permission_waits=6","actual_Native_session_permission_waits=7, actual_Native_nonblocking_busy_cases=1"),
  ("ROOT / 'scripts/current-sku-combined-fixture-followup/cases.mjs'","ROOT / '"+NS+"/cases.mjs'"),
 ),
 'concurrency':(
  ("controls = load('sku_concurrency_controls', HERE / 'controls.py')","controls = load('sku_concurrency_controls', ROOT / '"+NS+"/session_controls.py')"),
  ("return dict(status='PREPARED', case_id=CASE, race_ids=list(races), permission_wait_ids=list(permissions),","extra = load('sku27_extra_session_plan', ROOT / '"+NS+"/recovery_sessions.py')\n    return dict(status='PREPARED', case_id=CASE, race_ids=list(races), permission_wait_ids=list(permissions) + [extra.IDS[0]], nonblocking_busy_ids=[extra.IDS[1]], busy_subattempts=['FG','MATERIAL_NONE'],"),
  ("expected = tuple(business.IDS) + tuple(permissions.IDS)","extra = load('sku27_real_recovery_sessions', ROOT / '"+NS+"/recovery_sessions.py')\n    cost = load('sku27_existing_derived_cost_fixture', ROOT / '"+NS+"/cost_cases.py')\n    expected = tuple(business.IDS) + tuple(permissions.IDS) + tuple(extra.IDS)"),
  ("assert list(expected) == report['prepared_plan']['race_ids'] + report['prepared_plan']['permission_wait_ids']",
   "assert list(expected) == report['prepared_plan']['race_ids'] + report['prepared_plan']['permission_wait_ids'] + report['prepared_plan']['nonblocking_busy_ids']"),
  ("list(permissions.cases(tools, today))","list(permissions.cases(tools, today)) + list(extra.cases(tools, today, native_fixture=cost.n))"),
  ("len(copy_adapter.COPY_ADMISSIONS) == 9","len(copy_adapter.COPY_ADMISSIONS) == 11"),
  ("full_installed_copy_restores=9","full_installed_copy_restores=11"),
 ),
 'browser':(
  ("mkdirSync,readFileSync,writeFileSync","mkdirSync,readFileSync,writeFileSync,lstatSync"),
  ("../auditor/scripts/current-sku-combined-fixture-followup/browser_fixture.py","../auditor/"+NS+"/browser_fixture.py"),
  ("const pins=JSON.parse(readFileSync(resolve(ROOT,'scripts/current-sku-pair-browser-qualification/SOURCE.json'),'utf8'))",
   "const pins=JSON.parse(pinnedSource('scripts/current-sku-pair-browser-qualification/SOURCE.json').toString('utf8'))"),
  ("function admitted(){","""function pinnedSource(path){
 assert.equal(typeof path,'string');assert(!path.startsWith('/')&&!path.split('/').includes('..'))
 let part=ROOT;for(const segment of path.split('/')){part=resolve(part,segment);assert(!lstatSync(part).isSymbolicLink(),'SKU27_SOURCE_SYMLINK:'+path)}
 assert(lstatSync(part).isFile(),'SKU27_SOURCE_NOT_FILE:'+path);return readFileSync(part)
}
function admitted(){"""),
  ("for(const[path,expected]of Object.entries(pins.files))assert.equal(createHash('sha256').update(readFileSync(resolve(ROOT,path))).digest('hex'),expected,'SKU29_BROWSER_SOURCE_CHANGED:'+path)","""const current=JSON.parse(pinnedSource('"""+NS+"""/BROWSER_SOURCE.json').toString('utf8'))
 assert.deepEqual(Object.keys(current).sort(),['current_files','historical_files','product_head','product_tree','retained21_original_sha256','retained21_package_sha256'].sort())
 assert.deepEqual(current.historical_files,pins.files)
 for(const[path,expected]of Object.entries(pins.files))assert.equal(createHash('sha256').update(pinnedSource(path)).digest('hex'),current.current_files[path]??expected,'SKU29_BROWSER_SOURCE_CHANGED:'+path)
 for(const[path,expected]of Object.entries(current.current_files))assert.equal(createHash('sha256').update(pinnedSource(path)).digest('hex'),expected,'SKU27_CURRENT_BROWSER_RUNTIME_SOURCE_CHANGED:'+path)
 const actual=JSON.parse(execFileSync('python',[resolve(ROOT,'"""+NS+"""/browser_source.py')],{cwd:ROOT,encoding:'utf8',maxBuffer:32*1024*1024,timeout:120000}).trim())
 assert.equal(actual.projected_sources,false);assert.equal(actual.database_calls,0)
 assert.equal(actual.product_public_head,current.product_head);assert.equal(actual.product_tree,current.product_tree)
 assert.deepEqual(actual.actual_current_installation.files,current.current_files)
 assert.equal(actual.authentic_retained_Original.original_sha256,current.retained21_original_sha256)
 assert.equal(actual.authentic_retained_Original.package_sha256,current.retained21_package_sha256)
 assert.equal(actual.authentic_retained_Original.fresh_cases_credited,0)"""),
  ("return{backend_candidate:pins.backend_candidate,case_ids:pins.case_ids,source_sha256:createHash('sha256').update(JSON.stringify(pins)).digest('hex')}","return{backend_candidate:actual.product_public_head,case_ids:pins.case_ids,source_sha256:actual.actual_current_sources_sha256,retained_Original:actual.authentic_retained_Original}"),
 ),
 'cases':(("from './browser.mjs'","from './browser.mjs'"),),
}
# 'fresh_cost_native3' occurs once in runner. No global name replacement is
# permitted except the old qualifier namespace, whose count is source-bound.
EXTRA['cases']=()

def derive(key,raw=None):
    base,prior=legacy.derive(key,raw)
    count=base.count(OLD_NS)
    text=base.replace(OLD_NS,NS)
    for before,after in EXTRA.get(key,()):
        if text.count(before)!=1 or after in text:raise ValueError('SKU27_EXACT_SOURCE_ADAPTER_REQUIRED:'+key+':'+before)
        text=text.replace(before,after,1)
    reverse=text
    for before,after in reversed(EXTRA.get(key,())):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse.replace(NS,OLD_NS)==base,'SKU27_PRIVATE_DERIVATION_NOT_REVERSIBLE'
    if SOURCES[key][0].endswith('.py'):compile(text,SOURCES[key][0],'exec')
    return text,dict(retained602=prior,retained602_derived_sha256=sha256(base.encode()).hexdigest(),
      derived_sha256=sha256(text.encode()).hexdigest(),namespace_occurrences=count,
      extra_counted_changes=len(EXTRA.get(key,())),byte_exact_reversible=True,
      original23_financial_callback_bodies_unchanged=key!='races',
      original_financial_postcondition_assertions_unchanged=True,
      explicit_race_schedule_transition=key=='races')

def inventory():return{key:derive(key)[1]for key in SOURCES}

def execute(key,namespace):
    text,proof=derive(key);namespace['__file__']=str(ROOT/SOURCES[key][0])
    exec(compile(text,namespace['__file__'],'exec'),namespace);namespace['SKU27_DERIVATION']=proof
