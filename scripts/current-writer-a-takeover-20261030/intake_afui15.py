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
from intake_sku27 import strict,literal,full_census,declared_files

HEAD=None
TREE=None
RUN=None
JOB=None
PARENT_HEAD=None
PARENT_TREE=None
PARENT_RUN=None
PARENT_JOB=None
PREPARED_HEAD='098dbd8769cbbf6f0502750a7c2a770959e02385'
PREPARED_TREE='b40ea64ea4cdcaaa0f28fc6d32645e783c0b0121'
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
        or PurePosixPath(n).name in('NATIVE_ORIGIN.json','UI_ORIGIN.json','UI_SOURCE.json','afui15.workflow.yml.txt'))}
    if WORKFLOW in added:required.add(WORKFLOW)
    exact(set(declaration['files']),required,'AFUI15_COMPLETE_EXECUTABLE_AND_TEMPLATE_SOURCE_PINS')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    ui=strict(g.read(NS+'UI_SOURCE.json'))
    ui_paths=UI_CHANGED|UI_ADDED|{NS+'UI_ORIGIN.json'}|{NS+v['captured_file']for v in origin['files'].values()}
    exact(set(ui['files']),ui_paths,'AFUI15_ALL_UI_AND_ORIGINAL_CAPTURE_PINS')
    for name,value in ui['files'].items():g.verify_pin(name,value)
    for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB'):
        exact(literal(g,NS+'admission.py',name),globals()[name],'AFUI15_EXACT_ACTUAL_PARENT_BINDING:'+name)
    if PARENT_HEAD is None:
        exact(literal(g,NS+'admission.py','PARENT_RECEIPT'),None,'AFUI15_PREPARED_RECEIPT_CLOSED')
        exact(len(required),56,'AFUI15_PREPARED56_SOURCE_PINS');exact(len(added),88,'AFUI15_PREPARED88_OWN_PATHS')
        require(WORKFLOW not in g.tree,'AFUI15_NO_PREMATURE_EXECUTABLE_WORKFLOW')
    else:
        require(WORKFLOW in required,'AFUI15_ACTUAL_WORKFLOW_EXPLICITLY_DECLARED')
        exact(g.read(WORKFLOW),g.read(NS+'afui15.workflow.yml.txt'),'AFUI15_ACTUAL_WORKFLOW_EQUALS_REVIEWED_TEMPLATE')
    _,pure=report_validator(g,None)
    return dict(source_pins=len(required),own_paths=len(added),unchanged_parent_paths=len(base)-4,
        source_manifest=pin(g.read(NS+'SOURCE.json')),UI_manifest=pin(g.read(NS+'UI_SOURCE.json')),
        exact_counted_UI_paths=4,new_UI_paths=5,pure_report_functions=pure,
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
        fields(parent,dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_ALL5',head=PARENT_HEAD,
            tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,actual_Native_cases=3,complete3_qualified=True,
            package_all_five=True,prior_runs_aggregated=False,retained_DE30_fresh_case_credit=0,
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
