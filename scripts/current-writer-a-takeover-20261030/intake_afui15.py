"""Closed read-only Afui15 canonical intake. No ERP modules or connections.

Source preparation and compiling bounded pure report functions grant no actual
business credit. Both accepted parent and owning run must exist before files
claiming actual success can be read.
"""
from pathlib import Path,PurePosixPath
from hashlib import sha256,file_digest
from decimal import Decimal,ROUND_HALF_UP
from types import ModuleType,SimpleNamespace
from tempfile import TemporaryDirectory
import argparse,ast,copy,gzip,json,re,stat,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,full_census
from current_graph_sources import declared_files

HEAD='e068e189b171d1e0c39003b271d1969133afd182'
TREE='d06b27222530bc6fe28bfca9d83d053673422e81'
RUN=41509468425
JOB=125497247344
PARENT_HEAD='91a7b46ed13c4ad6094114871a4a39fa6765d140'
PARENT_TREE='01c4807d932af1d534477c4c182715b1378bd39b'
PARENT_RUN=41399754004
PARENT_JOB=125128803743
PREPARED_HEAD='8d2a1c5ad218e3592d9c57e61adb37d912190b50'
PREPARED_TREE='a286b28031a5d5235a02339d12a1ce4acb85db3b'
PREPARED_BASE='10ac4e74cfcc66db7d1f2b166f3da0fc479f127b'
PREPARED_BASE_TREE='a0b0108113b9b4d43d57483f291383229a37d4ad'
NS='scripts/cp7_accessory_nonpayable/'
WORKFLOW='.github/workflows/cp7-afui-good-nonpayable.yml'
MAIN='CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'
RAW='CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json'
CASE='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2'
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
UI_CHANGED={'src/ConnectedErpSettingsPage.tsx','scripts/check-source-ownership.mjs',
    'src/ConnectedErpSettingsPage.dom.test.tsx','scripts/check-access-catalog.mjs'}
UI_ADDED={'src/GoodPolicyDatesPanel.tsx','src/nativeGoodPolicyDates.ts','src/good-policy-dates.css',
    'src/GoodPolicyDatesPanel.dom.test.tsx','src/nativeGoodPolicyDates.test.ts'}
PURE_NAMES={'ValueError','type','len','set','dict','str','list','range','sum','any','all','int','sorted',
    'enumerate','Decimal','D','PurePosixPath','sha256','artifact','compare_census','race_facts',
    'assets','supervisor','visit','rows','census','state','allocations','expected_refusal_gaps'}
PURE_METHODS={'get','items','values','startswith','isdecimal','removeprefix','issubset','quantize',
    'fullmatch','fields','exact','pin','require_pin','strict','parent_receipt','require_changes',
    'require_append','is_absolute','is_symlink','resolve','read_bytes','decompress','hexdigest','append',
    'validate','require_economics','copies','native'}
PURE_IMPORTS={'admission','access_cases','assembly','native_cases','browser_prepare','case_boundary',
    'qualification_gate','native_fixture'}

def pure_functions(raw,path,names,context):
    """Select definitions only; replace declared package imports with Root data."""
    selected=[copy.deepcopy(n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name in names]
    exact([n.name for n in selected],list(names),'AFUI15_EXACT_SELECTED_PURE_FUNCTIONS:'+path)
    removed=[]
    class Imports(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            require(node.module=='cp7_accessory_nonpayable'and node.level==0
                and all(a.name in PURE_IMPORTS and a.asname is None for a in node.names),
                'AFUI15_PURE_ONLY_DECLARED_DATA_ADAPTER_IMPORT')
            removed.append([a.name for a in node.names]);return None
    for function in selected:
        require(not function.decorator_list,'AFUI15_PURE_NO_DECORATOR')
        require(all(isinstance(n,ast.Constant)or(isinstance(n,ast.Tuple)and not n.elts)for n in function.args.defaults+[
            n for n in function.args.kw_defaults if n is not None]),'AFUI15_PURE_LITERAL_DEFAULTS_ONLY')
        Imports().visit(function)
        for node in ast.walk(function):
            require(not isinstance(node,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.ClassDef,
                ast.Lambda,ast.With,ast.AsyncWith,ast.Await,ast.Yield,ast.YieldFrom)),
                'AFUI15_PURE_NO_RUNTIME_IMPORT_OR_EXECUTION_CONTEXT')
            if isinstance(node,ast.Name):require(not node.id.startswith('__'),'AFUI15_PURE_NO_SPECIAL_NAME')
            if isinstance(node,ast.Attribute):require(not node.attr.startswith('__'),'AFUI15_PURE_NO_SPECIAL_ATTRIBUTE')
            if isinstance(node,ast.Call):
                call=node.func
                require((isinstance(call,ast.Name)and call.id in PURE_NAMES)
                    or(isinstance(call,ast.Attribute)and call.attr in PURE_METHODS),
                    'AFUI15_PURE_DECLARED_CALLS_ONLY:'+ast.unparse(call))
    module=ModuleType('ROOT_AFUI15_PURE_'+path.replace('/','_'))
    module.__dict__.update(context)
    tree=ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[]))
    exec(compile(tree,path+':Root-pure-definitions-only','exec'),module.__dict__)
    return module,dict(source=pin(raw),functions=list(names),data_imports_replaced_by_Root_values=removed,
        actual_ERP_imports=0,actual_SQL_executed=0)

def require_pin(value):
    require(type(value)is dict and set(value)=={'bytes','sha256'}and type(value['bytes'])is int
        and value['bytes']>0 and type(value['sha256'])is str
        and re.fullmatch('[0-9a-f]{64}',value['sha256'])is not None,'AFUI15_EXACT_TYPED_POSITIVE_PIN')
    return value

def data_assignment(g,path,name):
    nodes=[n for n in ast.parse(g.read(path)).body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name)and t.id==name for t in n.targets)]
    exact(len(nodes),1,'AFUI15_ONE_STATIC_DATA_ASSIGNMENT:'+name);node=nodes[0].value
    if isinstance(node,ast.Call):
        require(isinstance(node.func,ast.Name)and node.func.id=='dict'and not node.args
            and all(k.arg is not None for k in node.keywords),'AFUI15_ONLY_STATIC_DICT_KEYWORDS')
        keys=[k.arg for k in node.keywords];exact(len(set(keys)),len(keys),'AFUI15_UNIQUE_STATIC_DICT_KEYS')
        return{k.arg:ast.literal_eval(k.value)for k in node.keywords}
    return ast.literal_eval(node)

def report_validator(g,parent):
    proofs={}
    def select(file,names,context):
        module,proof=pure_functions(g.read(NS+file),NS+file,names,context);proofs[file]=proof;return module
    access=select('access_cases.py',('require_changes','require_append'),{})
    access.ALLOWED_DATE_TABLES=literal(g,NS+'access_cases.py','ALLOWED_DATE_TABLES')
    exact(access.ALLOWED_DATE_TABLES,{NS.split('/')[1]+'.category_versions_v1',
        NS.split('/')[1]+'.date_requests_v1'},'AFUI15_ONLY_TWO_DATE_CHANGE_TABLES')
    access.HTTP_IDS=literal(g,NS+'access_cases.py','HTTP_IDS');access.RACE_IDS=literal(g,NS+'access_cases.py','RACE_IDS')
    native_ids=literal(g,NS+'native_cases.py','FIRST_IDS')+literal(g,NS+'native_inverse_cases.py','IDS')+literal(g,NS+'native_sales_cases.py','IDS')
    browser_ids=literal(g,NS+'browser_prepare.py','IDS')
    exact([len(native_ids),len(access.HTTP_IDS),len(access.RACE_IDS),len(browser_ids)],[9,2,2,2],'AFUI15_EXACT_FIFTEEN_SOURCE_IDS')
    require(len(set(native_ids+access.HTTP_IDS+access.RACE_IDS+browser_ids))==15,'AFUI15_UNIQUE_ALL_FIFTEEN_IDS')
    boundary_constants={name:data_assignment(g,NS+'case_boundary.py',name)for name in('OWNED','FG','MISSING','MISSING_ERROR','SEQUENCE_DEFINITION')}
    owned=boundary_constants['OWNED'];witnesses={n:(t,c)for n,(t,c,_)in owned.items()}
    witnesses[boundary_constants['FG']]=('erp.fg_stock_movements','book_order')
    exact(set(witnesses),{'erp.app_access_audit_id_seq','erp.audit_logs_id_seq','erp.cost_recalc_queue_id_seq',
        'erp.production_pattern_audit_id_seq','erp.fg_stock_book_order_seq'},'AFUI15_EXACT_FIVE_OBSERVED_NATIVE_ALLOCATORS')
    boundary=select('case_boundary.py',('state','allocations','expected_refusal_gaps','validate'),dict(boundary_constants,WITNESSES=witnesses))
    groups=select('qualification_gate.py',('rows','native','copies'),{})
    money=select('native_fixture.py',('require_economics',),dict(Decimal=Decimal,ROUND_HALF_UP=ROUND_HALF_UP))
    def actual_parent():
        require(parent is not None,'AFUI15_ACTUAL_PARENT_VALUES_NOT_SUPPLIED');return parent
    data=SimpleNamespace(strict=strict,pin=pin,require_pin=require_pin,parent_receipt=actual_parent)
    context=dict(sha256=sha256,PurePosixPath=PurePosixPath,gzip=gzip,re=re,admission=data,access_cases=access,
        assembly=SimpleNamespace(USED_ERROR=literal(g,NS+'settings_stage.py','USED_ERROR')),
        native_cases=SimpleNamespace(IDS=native_ids),browser_prepare=SimpleNamespace(IDS=browser_ids),
        case_boundary=boundary,qualification_gate=groups,native_fixture=money,CASE=CASE)
    gate=select('final_gate.py',('supervisor','artifact','compare_census','race_facts','assets','validate'),context)
    return gate,dict(exact_pure_sources=proofs,Native_ids=list(native_ids),HTTP_ids=list(access.HTTP_IDS),
        race_ids=list(access.RACE_IDS),browser_ids=list(browser_ids),actual_ERP_imports=0,actual_SQL_executed=0)

def role_ownership_source(g):
    """Exact source review of the first actual role-transfer refusal repair."""
    marker=NS+'test_role_ownership.mjs'
    if marker not in g.tree:return None
    expected={'scripts/cp7_accessory_nonpayable/FIRST_ROLE_OWNERSHIP_FAILURE_AND_REPAIR.json': {'bytes': 1244, 'sha256': 'a98b8439aaa30d77577a6183a82857e33b71daf24ed3d057823682c18c3f9ea9'}, 'scripts/cp7_accessory_nonpayable/LOCAL_ROLE_OWNERSHIP_CONTROLS.json': {'bytes': 1569, 'sha256': '82c53001d95c4e24140c038d3ceaee2c8571f14c7dee06152125d09151f802df'}, 'scripts/cp7_accessory_nonpayable/README.md': {'bytes': 19343, 'sha256': '0e9d15167ced7c9cbf97138689aff8be76d3542458707e98c156e0e87781cf1a'}, 'scripts/cp7_accessory_nonpayable/SOURCE.json': {'bytes': 11134, 'sha256': 'c29660509ad86385cb0ae08024afc6b507425111a40da0032f435d2ebfa80cfc'}, 'scripts/cp7_accessory_nonpayable/settings.sql': {'bytes': 15839, 'sha256': '733367d1822d86bd7fea5e2fe9196417c042659232cb0fbe3e887d424dcca06f'}, 'scripts/cp7_accessory_nonpayable/settings_stage.py': {'bytes': 16129, 'sha256': '683b840f4c4fbcf951e83529fe474a8a2b0258b58270552065c0de4cafb3cab6'}, 'scripts/cp7_accessory_nonpayable/test_role_ownership.mjs': {'bytes': 6920, 'sha256': '4120db9e2467b1387f26eeaaa2e0e10bf525e8294e9ea336c0c880442d27504b'}}
    for name,value in expected.items():g.verify_pin(name,value)
    original_head='f4f16c6920d94c2b9ef22fa33c62144595a672ed'
    original_tree='c2957cd8ee7c7ac00450a5cd636e39ff0e27675c'
    with GitBytes(g.root,original_head,original_tree)as old:
        changed={name for name in expected if name in old.tree}
        exact(changed,{NS+name for name in('settings.sql','settings_stage.py','README.md','SOURCE.json')},
            'AFUI94_EXACT_FOUR_EXISTING_ROLE_REPAIR_SOURCE_PATHS')
        for name,entry in old.tree.items():
            if name not in changed:exact(g.tree.get(name),entry,'AFUI94_OTHER_F4_BLOB_AND_MODE_UNCHANGED:'+name)
        exact(set(g.tree)-set(old.tree),set(expected)-changed,'AFUI94_EXACT_THREE_NEW_REPAIR_PATHS')
        pattern=r"create function ([a-z0-9_.]+)\(([^)]*)\)\nreturns jsonb language (sql|plpgsql) (stable|volatile) security definer set search_path='' as \$\$(.*?)\$\$;"
        original=re.findall(pattern,old.read(NS+'settings.sql').decode(),re.S)
        exact(len(original),6,'AFUI94_EXACT_SIX_ORIGINAL_SETTINGS_FUNCTIONS')
        exact(re.findall(pattern,g.read(NS+'settings.sql').decode(),re.S),original,
            'AFUI94_ALL_SIX_FUNCTION_SIGNATURES_AND_BODIES_UNCHANGED')
    controls=strict(g.read(NS+'LOCAL_ROLE_OWNERSHIP_CONTROLS.json'))
    fields(controls,dict(status='ISOLATED_POSTGRES_NON_SUPERUSER_ROLE_OWNERSHIP_FOCUSED4_PASS_NOT_ERP',
        actual_ERP_Native_cases=0,old_settings_API_or_financial_cases_rerun=0,
        production_go=False,independent_acceptance=False),'AFUI94_MODEL_HAS_ZERO_ERP_CREDIT')
    exact(len(controls['checks']),4,'AFUI94_EXACT_FOCUSED_FOUR_MODEL_CONTROLS')
    require(all(row.get('status')=='PASS'for row in controls['checks']),'AFUI94_FOCUSED_MODEL_PASS')
    return dict(status='ROOT_EXACT_AFUI91_TO94_ROLE_TRANSFER_SOURCE_REPAIR_ONLY',
        original_head=original_head,original_tree=original_tree,reviewed_files=expected,
        unchanged_six_settings_bodies=True,unchanged_financial_and_business_case_sources=True,
        focused_model_runtime=controls['creator_profile'],focused_model_controls=4,actual_case_credit=0)

def runtime_domain_preflight_source(g,declaration):
    """Review exactly the prepared import/CWD/cleanup repair; zero case credit."""
    role_repair=role_ownership_source(g)
    origin_path=NS+'RUNTIME_DOMAIN_PREFLIGHT_ORIGIN.json'
    original_head='098dbd8769cbbf6f0502750a7c2a770959e02385'
    original_tree='b40ea64ea4cdcaaa0f28fc6d32645e783c0b0121'
    expected_pins={"scripts/cp7_accessory_nonpayable/RUNTIME_DOMAIN_PREFLIGHT_ORIGIN.json":{"bytes":11588,"sha256":"347d47486114dc494db714780a83309936f5b18d2e413432c9f65699e962b753"},"scripts/cp7_accessory_nonpayable/afui15.workflow.yml.txt":{"bytes":33890,"sha256":"551e9f853a6307e791991926b714aa53578f95b69ee246e7c567ff213dc75799"},"scripts/cp7_accessory_nonpayable/composition.py":{"bytes":14747,"sha256":"e33a129629787ff093bd54a715cc9069df1d307d7a7dc446535faef3f0d048b5"},"scripts/cp7_accessory_nonpayable/native_fixture.py":{"bytes":18110,"sha256":"af4352bd06ea35cf463fe989933e6cce628f24918667edc425f72f72890d8962"},"scripts/cp7_accessory_nonpayable/qualification.py":{"bytes":4615,"sha256":"55f3cafc94c1a87c03f320dbce26e56953eb5c6bc93e52b9c68d6052bd530fe9"},"scripts/cp7_accessory_nonpayable/workflow.py":{"bytes":7781,"sha256":"bd8f5b3e730ca6e68416a8e09c5a5d6802387d20ebf6294954a27a9faac6d85e"}}
    exact(len(expected_pins),6,'AFUI15_EXACT_FIVE_REPAIRED_SOURCE_FILES_AND_ORIGIN')
    for name,value in expected_pins.items():g.verify_pin(name,value)
    origin=strict(g.read(origin_path))
    fields(origin,dict(classification='AFUI_EXACT_NATIVE_DOMAIN_API_PREFLIGHT_AND_WRITER_CWD_CLEANUP_PREPARATION_NOT_QUALIFICATION',
        head=original_head,tree=original_tree,reversible_routes=12,modified_old_own_paths=6,
        new_own_paths=1,unchanged_old_own_paths=82,own_paths=89,source_pins=57,
        Native_financial_SQL_and_case_function_bodies_changed=False,
        actual_original_domain_files_changed=0,actual_parent_still_unbound=True,
        actual_Native_cases=0,production_go=False,independent_acceptance=False),
        'AFUI15_EXACT_REVIEWED_DOMAIN_PREFLIGHT_ORIGIN')
    exact(set(origin['files']),set(expected_pins)-{origin_path},'AFUI15_EXACT_FIVE_OWN_REPAIR_PATHS')
    with GitBytes(g.root,original_head,original_tree)as old:
        original=strict(old.read(NS+'SOURCE.json'));old_base=old.entries(PREPARED_BASE)
        old_own=set(old.tree)-set(old_base)
        exact(len(old_own),88,'AFUI15_EXACT_RETAINED_ORIGINAL_PREPARATION_OWN88')
        changed=set(origin['files'])|{NS+'SOURCE.json'}
        if PARENT_HEAD is not None:changed.add(NS+'admission.py')
        if role_repair is not None:changed|={NS+name for name in('settings.sql','settings_stage.py','README.md')}
        for name in old_own-changed:
            exact(g.tree.get(name),old.tree[name],'AFUI15_ALL_OTHER_ORIGINAL_OWN_BLOBS_MODES_UNCHANGED:'+name)
        routes=0
        for name,value in origin['files'].items():
            raw=old.read(name);exact(pin(raw),value['before'],'AFUI15_EXACT_ORIGINAL_PREPARED_SOURCE:'+name)
            actual=g.read(name);exact(pin(actual),value['after'],'AFUI15_EXACT_REPAIRED_PREPARED_SOURCE:'+name)
            text=raw.decode()
            for change in value['changes']:
                exact(change['count'],1,'AFUI15_SINGLE_REVIEWED_ROUTE')
                exact(text.count(change['before']),1,'AFUI15_EXACT_REPAIR_ANCHOR')
                text=text.replace(change['before'],change['after'],1);routes+=1
            exact(text.encode(),actual,'AFUI15_ONLY_EXACT_REPAIR_ROUTES:'+name)
            for change in reversed(value['changes']):
                exact(text.count(change['after']),1,'AFUI15_EXACT_REPAIR_REVERSE')
                text=text.replace(change['after'],change['before'],1)
            exact(text.encode(),raw,'AFUI15_ENTIRE_ORIGINAL_PREPARATION_RECOVERED:'+name)
        exact(routes,12,'AFUI15_ONLY_TWELVE_REPAIR_ROUTES')
        expected=dict(original);expected['files']=dict(original['files'],**expected_pins)
        expected['runtime_domain_preflight']=dict(origin=origin_path,before_head=original_head,
            before_tree=original_tree,actual_Native_cases=0)
        if PARENT_HEAD is None:
            exact(g.read(NS+'admission.py'),old.read(NS+'admission.py'),'AFUI15_PREPARED_PARENT_GATE_ENTIRELY_UNCHANGED')
        else:
            from prepare_de_activation import literal_route
            from prepare_afui_activation import focused_parent_admission
            receipt_raw=g.read(NS+'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json')
            raw=old.read(NS+'admission.py')
            raw,_=focused_parent_admission(raw)
            for key,value in(('PARENT_HEAD',PARENT_HEAD),('PARENT_TREE',PARENT_TREE),
                ('PARENT_RUN',PARENT_RUN),('PARENT_JOB',PARENT_JOB),('PARENT_RECEIPT',pin(receipt_raw))):
                raw,_=literal_route(raw,key,None,value)
            exact(g.read(NS+'admission.py'),raw,'AFUI15_ONLY_EXACT_FOCUSED_TYPED_RECEIPT_AND_FIVE_ACTUAL_PARENT_BINDINGS')
            expected['base_head']=PARENT_HEAD;expected['base_tree']=PARENT_TREE
            expected['files'][NS+'admission.py']=pin(raw)
            exact(g.read(WORKFLOW),g.read(NS+'afui15.workflow.yml.txt'),'AFUI15_EXACT_PREPARED_WORKFLOW_ACTIVATION')
            expected['files'][WORKFLOW]=pin(g.read(WORKFLOW))
        if role_repair is not None:
            for name in('settings.sql','settings_stage.py','test_role_ownership.mjs'):
                expected['files'][NS+name]=role_repair['reviewed_files'][NS+name]
        exact(declaration,expected,'AFUI15_ONLY_REVIEWED_DOMAIN_PREFLIGHT_SOURCE_AND_OPTIONAL_ACTUAL_BINDINGS')
    return dict(status='EXACT_AFUI_OWN88_TO89_DOMAIN_PREFLIGHT_SOURCE_REPAIR_ONLY',
        original_head=original_head,original_tree=original_tree,reversible_routes=12,
        unchanged_original_case_functions=True,role_ownership_repair=role_repair,actual_case_credit=0)


def function_acl_source(g,declaration):
    """Exact six-new-function ACL repair; no business or Native case credit."""
    expected={'scripts/cp7_accessory_nonpayable/ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json': {'bytes': 1521, 'sha256': 'c0409e9e66aa516ac34a05bfa62171d000b9be24fc5e95c965367b0160a881f1'}, 'scripts/cp7_accessory_nonpayable/FIRST_FUNCTION_ACL_FAILURE_AND_REPAIR.json': {'bytes': 1591, 'sha256': '03c87acb3ddd2fc754e2b059f46181fa4a9a321dcc49b005f797acb91a55212d'}, 'scripts/cp7_accessory_nonpayable/LOCAL_FUNCTION_DEFAULT_ACL_CONTROLS.json': {'bytes': 1400, 'sha256': '6b80b10add4bb3172a780f421d33b9e7ab5a866306993e94a72737bc6266c5a4'}, 'scripts/cp7_accessory_nonpayable/README.md': {'bytes': 20113, 'sha256': '5127cf0043b70eca7980f470519300920b0a4d9f24a08d4a1cf274cd13fd86c0'}, 'scripts/cp7_accessory_nonpayable/SOURCE.json': {'bytes': 11685, 'sha256': 'f7d8429fdd854a5a8fbb2172ee60c402f8a5fce5370b1250000525d27597a439'}, 'scripts/cp7_accessory_nonpayable/composition.py': {'bytes': 14792, 'sha256': '18f2eb8feea6f6ace99330a3ff480cbeb171818ca71c24a7b1cfdd0f4a2b8fac'}, 'scripts/cp7_accessory_nonpayable/function_acl_capability.py': {'bytes': 8455, 'sha256': '3c509e803b6e6a1f2e34c941010ab35dfa588a97275ccafb073b724a2565e8ba'}, 'scripts/cp7_accessory_nonpayable/runtime_supervisor.py': {'bytes': 2672, 'sha256': 'a7a6fc74fe43dd0f1e30a1b29729d3e625886b2370074044fce850c906073761'}, 'scripts/cp7_accessory_nonpayable/settings.sql': {'bytes': 16348, 'sha256': 'affee25285953f007d9bf0175ca33c891a54343310968c64be247ed61217f15e'}, 'scripts/cp7_accessory_nonpayable/test_function_acl.mjs': {'bytes': 7049, 'sha256': 'f2f9af1aa13d8f5c0088d2c688b0b04d80bddd2a2517d5aceaafc710f41d3c71'}}
    for name,value in expected.items():g.verify_pin(name,value)
    old_head='47e9cfb66e8b2b493605bbb005537457f3ddcd86'
    old_tree='b55f6b27ec3bb111b01e315cc0d77d3d606f7d5f'
    with GitBytes(g.root,old_head,old_tree)as old:
        changed={name for name in expected if name in old.tree}
        exact(changed,{NS+n for n in('settings.sql','composition.py','runtime_supervisor.py','README.md','SOURCE.json')},'AFUI99_EXACT_FIVE_CHANGED_SOURCE_PATHS')
        for name,entry in old.tree.items():
            if name not in changed:exact(g.tree.get(name),entry,'AFUI99_ALL_OTHER_47E_BLOBS_AND_MODES_UNCHANGED:'+name)
        exact(set(g.tree)-set(old.tree),set(expected)-changed,'AFUI99_EXACT_FIVE_NEW_SOURCE_PATHS')
        pattern=r"create function ([a-z0-9_.]+)\(([^)]*)\)\nreturns jsonb language (sql|plpgsql) (stable|volatile) security definer set search_path='' as \$\$(.*?)\$\$;"
        bodies=re.findall(pattern,old.read(NS+'settings.sql').decode(),re.S)
        exact(len(bodies),6,'AFUI99_EXACT_SIX_ORIGINAL_SETTINGS_BODIES')
        exact(re.findall(pattern,g.read(NS+'settings.sql').decode(),re.S),bodies,'AFUI99_ALL_SIX_SIGNATURES_VOLATILITY_AND_BODIES_UNCHANGED')
        prior=strict(old.read(NS+'SOURCE.json'))
        retained=runtime_domain_preflight_source(old,prior)
        expect=copy.deepcopy(prior)
        for name in('settings.sql','composition.py','runtime_supervisor.py','ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json','function_acl_capability.py','test_function_acl.mjs'):
            expect['files'][NS+name]=expected[NS+name]
        exact(declaration,expect,'AFUI99_ONLY_EXACT_SIX_SOURCE_PIN_UPDATES')
    controls=strict(g.read(NS+'LOCAL_FUNCTION_DEFAULT_ACL_CONTROLS.json'))
    fields(controls,dict(status='ISOLATED_POSTGRES_NON_SUPERUSER_ACTUAL_DEFAULT_ACL_FOCUSED3_PASS_NOT_ERP',actual_ERP_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False),'AFUI99_MODEL_ZERO_NATIVE_CREDIT')
    exact(len(controls['checks']),3,'AFUI99_ONLY_THREE_NEW_FOCUSED_ACL_MODELS')
    require(all(r.get('status')=='PASS'for r in controls['checks']),'AFUI99_THREE_NEW_ACL_MODEL_PASS')
    for name,value in controls['source_sha256'].items():
        exact(pin(g.read(NS+name))['sha256'],value,'AFUI99_MODEL_EXACT_SOURCE:'+name)
    ast.parse(g.read(NS+'function_acl_capability.py'))
    return retained,dict(status='ROOT_EXACT_AFUI94_TO99_NEW_FUNCTION_ACL_SOURCE_REPAIR_NOT_QUALIFICATION',original_head=old_head,original_tree=old_tree,reviewed_files=expected,unchanged_six_settings_bodies=True,focused_WASM18_6_controls=3,actual_PostgreSQL17_capability_pending=True,actual_case_credit=0)


def postgres17_capability_source(g,declaration):
    """One exact model-context repair; owning SQL and case oracles retained."""
    expected={'scripts/cp7_accessory_nonpayable/FIRST_POSTGRES17_CAPABILITY_FAILURE_AND_REPAIR.json': {'bytes': 1799, 'sha256': 'f49231749c30877668612eaaed55b3eb942bc183405b3679b7f04c204e995750'}, 'scripts/cp7_accessory_nonpayable/README.md': {'bytes': 20857, 'sha256': '97b5fabd22a11b712767ed73e8b96e8b78fa443fc8ef7b3cee1a9c7411e4ee47'}, 'scripts/cp7_accessory_nonpayable/SOURCE.json': {'bytes': 11685, 'sha256': 'bdc3b456e26ed592cb5ac32f76bde67c8325292b9fd667a01f4e1f71c2109f05'}, 'scripts/cp7_accessory_nonpayable/function_acl_capability.py': {'bytes': 8532, 'sha256': '1233fb8248e43fd1806cb99fa87726ac152fd77bc24d489f9a3d3b3387d39887'}}
    for name,value in expected.items():g.verify_pin(name,value)
    old_head='14d44c8d601bb9d94b87d4c7f1834d6c2a41f947'
    old_tree='e1632822f61e0a5b5499f96104c02cec79cdd4ae'
    with GitBytes(g.root,old_head,old_tree)as old:
        changed={n for n in expected if n in old.tree}
        exact(changed,{NS+n for n in('function_acl_capability.py','SOURCE.json','README.md')},'AFUI100_EXACT_THREE_CHANGED_PATHS')
        exact(set(g.tree)-set(old.tree),{NS+'FIRST_POSTGRES17_CAPABILITY_FAILURE_AND_REPAIR.json'},'AFUI100_EXACT_ONE_NEW_REPAIR_RECORD')
        for name,entry in old.tree.items():
            if name not in changed:exact(g.tree.get(name),entry,'AFUI100_ALL_OTHER_99_BLOBS_AND_MODES_UNCHANGED:'+name)
        prior=strict(old.read(NS+'SOURCE.json'));retained,acl_repair=function_acl_source(old,prior)
        record=strict(g.read(NS+'FIRST_POSTGRES17_CAPABILITY_FAILURE_AND_REPAIR.json'))
        change=record['source_route'];exact(change['count'],1,'AFUI100_ONE_CONTEXT_ROUTE')
        raw=old.read(NS+'function_acl_capability.py');text=raw.decode()
        exact(text.count(change['before']),1,'AFUI100_EXACT_ORIGINAL_CONTEXT_ANCHOR')
        exact(text.replace(change['before'],change['after'],1).encode(),g.read(NS+'function_acl_capability.py'),'AFUI100_ONLY_EXACT_EMPTY_PATH_AND_UTC_CONTEXT_INSERTION')
        exact(change['after'],'            cur.execute("set local search_path=\'\';set local timezone=\'UTC\'")\n'+change['before'],'AFUI100_FIXED_OWNING_CONTEXT_ONLY')
        expected_declaration=copy.deepcopy(prior);expected_declaration['files'][NS+'function_acl_capability.py']=expected[NS+'function_acl_capability.py']
        exact(declaration,expected_declaration,'AFUI100_ONLY_ONE_SOURCE_PIN_CHANGED')
    return retained,acl_repair,dict(status='ROOT_EXACT_AFUI99_TO100_PG17_CAPABILITY_CONTEXT_SOURCE_REPAIR_NOT_BUSINESS',
        before_head=old_head,before_tree=old_tree,reviewed_files=expected,exact_reversible_routes=1,
        settings_SQL_six_function_bodies_and_financial_case_oracles_unchanged=True,actual_case_credit=0)


def source(g):
    base_head=PARENT_HEAD or PREPARED_BASE;base_tree=PARENT_TREE or PREPARED_BASE_TREE
    exact(g.git('rev-parse',base_head+'^{tree}').decode().strip(),base_tree,'AFUI15_EXACT_WHOLE_PARENT_TREE')
    declaration=strict(g.read(NS+'SOURCE.json'))
    fields(declaration,dict(contract='cp7.accessory-good-nonpayable.v1',base_head=base_head,base_tree=base_tree,
        actual_Native_cases=0,production_go=False,independent_acceptance=False),'AFUI15_SOURCE_IS_NOT_QUALIFICATION')
    base=g.entries(base_head);origin=strict(g.read(NS+'UI_ORIGIN.json'))
    exact(set(origin['files']),UI_CHANGED,'AFUI15_EXACT_FOUR_EXISTING_UI_ROUTES')
    for name,entry in base.items():
        if name not in UI_CHANGED:exact(g.tree.get(name),entry,'AFUI15_UNCHANGED_PARENT_BLOB_MODE:'+name)
    for name,row in origin['files'].items():
        raw=g.read(name,base_head);exact(pin(raw),row['original'],'AFUI15_EXACT_UI_PREDECESSOR:'+name)
        exact(g.tree[name]['mode'],'100644','AFUI15_REGULAR_REVIEWED_UI_PATH')
        text=raw.decode()
        require(row['changes'],'AFUI15_NONEMPTY_REVIEWED_UI_DERIVATION')
        for change in row['changes']:
            exact(change['count'],1,'AFUI15_ONE_UI_HUNK');exact(text.count(change['before']),1,'AFUI15_EXACT_UI_HUNK_ANCHOR')
            text=text.replace(change['before'],change['after'],1)
        exact(text.encode(),g.read(name),'AFUI15_ONLY_EXACT_REVIEWED_UI_CHANGES:'+name)
        exact(pin(text.encode()),row['derived'],'AFUI15_EXACT_DERIVED_UI_PIN')
        for change in reversed(row['changes']):
            exact(text.count(change['after']),1,'AFUI15_EXACT_UI_REVERSE_ANCHOR');text=text.replace(change['after'],change['before'],1)
        exact(text.encode(),raw,'AFUI15_COMPLETE_UI_ORIGINAL_RECOVERED')
    added=set(g.tree)-set(base)
    require(UI_ADDED<=added and all(n.startswith(NS)or n in UI_ADDED or n==WORKFLOW for n in added),
        'AFUI15_ONLY_ADDITIVE_OWN_SOURCE_AND_EXACT_UI_PATHS')
    required={n for n in added if n.startswith(NS)and(PurePosixPath(n).suffix in('.py','.sql','.mjs')
        or PurePosixPath(n).name in('NATIVE_ORIGIN.json','UI_ORIGIN.json','UI_SOURCE.json','afui15.workflow.yml.txt',
            'RUNTIME_DOMAIN_PREFLIGHT_ORIGIN.json','ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json'))}
    if WORKFLOW in added:required.add(WORKFLOW)
    exact(set(declaration['files']),required,'AFUI15_COMPLETE_EXECUTABLE_AND_TEMPLATE_SOURCE_PINS')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    ui=strict(g.read(NS+'UI_SOURCE.json'))
    ui_paths=UI_CHANGED|UI_ADDED|{NS+'UI_ORIGIN.json'}|{NS+v['captured_file']for v in origin['files'].values()}
    exact(set(ui['files']),ui_paths,'AFUI15_ALL_UI_AND_ORIGINAL_CAPTURE_PINS')
    for name,value in ui['files'].items():g.verify_pin(name,value)
    for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB'):
        exact(literal(g,NS+'admission.py',name),globals()[name],'AFUI15_EXACT_ACTUAL_PARENT_BINDING:'+name)
    acl_repair=None;capability_repair=None
    if NS+'FIRST_POSTGRES17_CAPABILITY_FAILURE_AND_REPAIR.json'in g.tree:
        repaired,acl_repair,capability_repair=postgres17_capability_source(g,declaration)
    elif NS+'ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json'in g.tree:
        repaired,acl_repair=function_acl_source(g,declaration)
    else:repaired=runtime_domain_preflight_source(g,declaration)if 'runtime_domain_preflight'in declaration else None
    if PARENT_HEAD is None:
        exact(literal(g,NS+'admission.py','PARENT_RECEIPT'),None,'AFUI15_PREPARED_RECEIPT_CLOSED')
        exact(len(required),57 if repaired else 56,'AFUI15_EXACT_PREPARED_SOURCE_PIN_COUNT')
        exact(len(added),89 if repaired else 88,'AFUI15_EXACT_PREPARED_OWN_PATH_COUNT')
        require(WORKFLOW not in g.tree,'AFUI15_NO_PREMATURE_EXECUTABLE_WORKFLOW')
    else:
        require(WORKFLOW in required,'AFUI15_ACTUAL_WORKFLOW_EXPLICITLY_DECLARED')
        exact(g.read(WORKFLOW),g.read(NS+'afui15.workflow.yml.txt'),'AFUI15_ACTUAL_WORKFLOW_EQUALS_REVIEWED_TEMPLATE')
    _,pure=report_validator(g,None)
    return dict(source_pins=len(required),own_paths=len(added),unchanged_parent_paths=len(base)-4,
        source_manifest=pin(g.read(NS+'SOURCE.json')),UI_manifest=pin(g.read(NS+'UI_SOURCE.json')),
        exact_counted_UI_paths=4,new_UI_paths=5,pure_report_functions=pure,
        runtime_domain_preflight_repair=repaired,new_function_ACL_repair=acl_repair,
        PostgreSQL17_capability_context_repair=capability_repair,
        parent_qualification_pending=PARENT_HEAD is None,actual_case_credit=0)

def intake(root,path,metadata):
    require(all(v is not None for v in(HEAD,TREE,RUN,JOB,PARENT_HEAD,PARENT_TREE,PARENT_RUN,PARENT_JOB)),
        'AFUI15_ACTUAL_PARENT_AND_OWNING_RUN_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,conclusion='success',expired=False),
        'AFUI15_EXACT_ACTUAL_TERMINAL_API_METADATA')
    require(type(metadata['artifact_id'])is int and metadata['artifact_id']>0,'AFUI15_ACTUAL_CANONICAL_ARTIFACT_ID')
    expected=require_pin(metadata['archive']);path=Path(path)
    exact(path.stat().st_size,expected['bytes'],'AFUI15_COMPLETE_CANONICAL_ARCHIVE_BYTES')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'AFUI15_CANONICAL_ARCHIVE_SHA')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'AFUI15_NO_DUPLICATE_CANONICAL_MEMBERS')
        for name in names:
            safe_path(name);require('\\'not in name and'\x00'not in name,'AFUI15_SAFE_CANONICAL_MEMBER')
            require(stat.S_IFMT(z.getinfo(name).external_attr>>16)in(0,stat.S_IFREG,stat.S_IFDIR),'AFUI15_NO_SYMLINK_OR_SPECIAL_ARCHIVE_MEMBER')
        require(z.testzip()is None,'AFUI15_COMPLETE_CANONICAL_ARCHIVE_CRC');admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);native=original(RAW);package=original('T3_PACKAGE_INSTALL.json')
        backup=original('T3_BACKUP_RESTORE_DRILL.json');owned=original('AFUI_RUNTIME_SUPERVISION.json')
        parent_raw=g.read(NS+'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        fields(parent,dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_RETAINED3_COMMITTED_ALL5',head=PARENT_HEAD,
            tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,actual_Native_cases=0,complete3_qualified=True,
            retained_Native_cases=3,retained_cases_are_not_fresh=True,candidate_case_coverage=3,
            source_invariant_reuse=True,financial_groups_rerun=False,actual_new_committed_witness=True,
            retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
            package_all_five=True,prior_runs_aggregated=True,retained_DE30_fresh_case_credit=0,
            production_go=False,independent_acceptance=False),'AFUI15_ACTUAL_ACCEPTED_FREE3_ROOT_PARENT')
        exact(pin(parent_raw),literal(g,NS+'admission.py','PARENT_RECEIPT'),'AFUI15_EXACT_PARENT_ROOT_RECEIPT_BYTES')
        graph=main['source_declaration']['complete_sources'];maps=declared_files(g,graph)
        financial=graph['parent'];exact(financial['source'],strict(g.read(NS+'SOURCE.json')),'AFUI15_ENTIRE_OWN_SOURCE_MANIFEST')
        exact(graph['settings_ui']['source'],strict(g.read(NS+'UI_SOURCE.json')),'AFUI15_ENTIRE_OWN_UI_MANIFEST')
        qualified_parent=pin(json.dumps(financial['parent'],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        exact(qualified_parent,parent['qualified_complete_DE_FREE_date_sources'],'AFUI15_ENTIRE_ACTUAL_FREE3_SOURCE_GRAPH')
        exact(financial['qualified_parent_sources'],qualified_parent,'AFUI15_ADMITTED_WHOLE_FREE3_SOURCE_PIN')
        validator,pure=report_validator(g,parent)
        # Copy only complete current originals to a private temporary directory.
        # Parent archives are checked in place and never extracted as substitutes.
        with TemporaryDirectory(prefix='root-afui15-current-originals-')as directory:
            directory=Path(directory)
            for name in names:
                if len(PurePosixPath(name).parts)==1 and name.startswith(('AFUI_','CP7_AFUI_GOOD_NONPAYABLE_FULL15')):
                    raw=z.read(name);(directory/name).write_bytes(raw);pins[name]=pin(raw)
            gate=validator.validate(SimpleNamespace(fields=fields,exact=exact,GATES=GATES),
                main,native,package,backup,owned,HEAD,source_graph=graph,directory=directory)
        exact(original('AFUI_FINAL_GATE.json'),gate,'AFUI15_ROOT_RECOMPUTES_ACTUAL_CURRENT_FINAL_GATE')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'AFUI15_EXACT_ACTUAL_OWNING_PACKAGE_RUN')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'AFUI15_COMPLETE_ROLE_RESTORE')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'AFUI15_COMPLETE_DATABASE_RESTORE')
        boundaries={}
        for name,row in native['cases'].items():
            boundary=row['actual_full22_case_boundary']
            boundaries[name]=full_census(boundary['before']['actual_all22'],boundary['before']['full_data_and_sequences'])
        used=main['committed'][CASE]['separate_committed_Native_use']['before']
        used_census=full_census(used['actual_all22'],used['full_data_and_sequences'])
        return dict(status='ROOT_VERIFIED_CURRENT_AFUI_GOOD_NONPAYABLE_FULL15_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),
            originals=pins,source_admission=admitted,pure_report_validation=pure,actual_product_source_maps=maps,
            qualified_Afui_good_nonpayable_sources=pin(json.dumps(graph,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
            qualified_FREE3=dict(head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,root_intake=pin(parent_raw)),
            actual_Native_cases=9,actual_Auth_HTTP_cases=2,actual_two_session_races=2,actual_browser_cases=2,
            actual_business_cases=15,complete15_qualified=True,package_all_five=True,prior_runs_aggregated=False,
            retained_FREE3_fresh_case_credit=0,actual_full22_case_censuses=boundaries,actual_used_refusal_census=used_census,
            GOOD_eligibility_policy_decided=True,Afui_GOOD_nonpayable_path_complete=True,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(dict(status='ROOT_AFUI15_EXACT_SOURCE_AND_BOUNDED_PURE_GATE_PREPARED',source=value,actual_ERP_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'AFUI15_CANONICAL_ARCHIVE_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],actual_fresh_cases=15)))
