"""Read-only canonical FREE3 intake, closed until both actual owning runs exist.

Prepared source checks and pure report grammar grant zero business credit.
No product/ERP module, connection, Auth, browser or network is imported here.
"""
from pathlib import Path
from hashlib import file_digest
from datetime import date,datetime,time,timedelta
from decimal import Decimal
from types import ModuleType,SimpleNamespace
from zoneinfo import ZoneInfo
import argparse,ast,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census
from current_graph_sources import declared_files

HEAD='ad986b9a9d432f2ffac2b961710c3852c6c2ef90'
TREE='80bc5471330b89497991ba1e67615287b01e59c1'
RUN=41388877929
JOB=125095681990
PARENT_HEAD='6e61506c10a18541c104b981bd438e78b175b5d1'
PARENT_TREE='86f07de6e0be871d39110aa797ef26da4564e8e8'
PARENT_RUN=41368001658
PARENT_JOB=125032204589
PREPARED_HEAD='fe21e26e9ca1fb8428dc0b1f86f16b03de2c9fcb'
PREPARED_TREE='aceccbf696165c85291d5d10a365ac262908f8a2'
PREPARED_BASE='fef0d838991df1ab3474382747ee3519d4c237eb'
PREPARED_BASE_TREE='772cc0a80e1857bc03e6a544a39d5b5de3beb4c3'
NS='scripts/current-de-free-date-preparation/'
PREFIXES=('scripts/current-special-free-date-boundary/','scripts/cp7_special_free_date_on_de/',
          'scripts/cp7_current_de_free_date/',NS)
WORKFLOW='.github/workflows/cp7-current-complete-de-free-date-native3.yml'
MAIN='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3.json'
RAW='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_CASES.json'
CASE='CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3'
IDS=['FREE_DATE_NATIVE_WIB_INCLUSIVE_LOOKUP_AND_NORMAL_PUBLIC_QUOTE',
     'FREE_DATE_NATIVE_FINAL_DAY_POST_STOCK_GL_AND_EXACT_REPLAY',
     'FREE_DATE_NATIVE_POSTED_HISTORY_AFTER_ELIGIBILITY_ENDS']
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
ACTIVATION_SOURCE_HEAD='fe21e26e9ca1fb8428dc0b1f86f16b03de2c9fcb'
ACTIVATION_SOURCE_TREE='aceccbf696165c85291d5d10a365ac262908f8a2'


def nested_manifest_sources(g):
    manifests=('scripts/cp7_special_free_date_on_de/SOURCE.json','scripts/cp7_current_de_free_date/SOURCE.json')
    count=0
    for path in manifests:
        value=strict(g.read(path))
        for name,expected in value['files'].items():g.verify_pin(name,expected);count+=1
    exact(count,16,'FREE3_ALL_SIXTEEN_NESTED_PRODUCT_SOURCE_PINS')
    return dict(manifests=list(manifests),source_pins=count,actual_case_credit=0)


def actual_activation_source(g,declaration):
    """Replay the exact bound own40 from immutable, closed own38."""
    import prepare_free_activation as planner
    receipt_path=NS+'DE30_PARENT_ROOT_ACTUAL_INTAKE.json';raw=g.read(receipt_path)
    receipt=planner.accepted_parent(raw)
    fields(receipt,dict(head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB),
        'FREE3_EXACT_ROOT_ACCEPTED_CURRENT_DE_PARENT')
    with GitBytes(g.root,ACTIVATION_SOURCE_HEAD,ACTIVATION_SOURCE_TREE)as old:
        original=strict(old.read(NS+'SOURCE.json'));old_paths=set(original['files'])|{NS+'SOURCE.json'}
        exact(len(old_paths),38,'FREE3_EXACT_OLD_CLOSED_OWN38')
        changed={path for path,_ in planner.NESTED_PARENT_MANIFESTS}|{NS+n for n in('admission.py','source.py','SOURCE.json','ORIGIN.json')}
        for name in old_paths-changed:
            exact(g.tree.get(name),old.tree[name],'FREE3_ALL_THIRTYTWO_OTHER_OWN_BLOBS_AND_MODES_UNCHANGED:'+name)
        before={name:old.read(name)for name in sorted(old_paths)};expected=dict(before);routes=[]
        for path,bindings in((NS+'admission.py',(
            ('PARENT_HEAD',None,PARENT_HEAD),('PARENT_RECEIPT',None,pin(raw)))),
            (NS+'source.py',(
            ('BASE',original['base_head'],PARENT_HEAD),('TREE',original['base_tree'],PARENT_TREE)))):
            for key,previous,following in bindings:
                expected[path],route=planner.literal_route(expected[path],key,previous,following)
                routes.append(dict(path=path,**route))
        nested=planner.rebind_nested_parent_manifests(expected,before)
        for name in changed-{NS+'SOURCE.json',NS+'ORIGIN.json'}:
            exact(g.read(name),expected[name],'FREE3_ONLY_EXACT_PARENT_BINDINGS_AND_FOUR_NESTED_PINS:'+name)
        origin=strict(old.read(NS+'ORIGIN.json'));guard=origin['source_preflight_origin']
        exact(len(guard['changes']),12,'FREE3_RETAIN_ALL_TWELVE_ORIGINAL_SOURCE_GUARD_ROUTES')
        for key,previous,following in(('BASE',original['base_head'],PARENT_HEAD),('TREE',original['base_tree'],PARENT_TREE)):
            matches=[item for item in guard['changes']if item['after']==key+'='+repr(previous)]
            exact(len(matches),1,'FREE3_ONLY_UPDATE_EXISTING_SOURCE_GUARD_ROUTE:'+key)
            matches[0]['after']=key+'='+repr(following)
        actual=dict(head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,receipt=pin(raw))
        origin['actual_DE30_parent_binding']=dict(actual,source_preparation_not_FREE_acceptance=True,
            unchanged_parent_blobs_and_modes=14265,own_paths=40,own_source_pins=39,literal_routes=routes,
            nested_parent_pin_routes=nested,financial_SQL_or_Native_callbacks_changed=False,
            actual_FREE_cases=0,production_go=False,independent_acceptance=False)
        exact(g.read(NS+'ORIGIN.json'),(json.dumps(origin,indent=2)+'\n').encode(),
            'FREE3_EXACT_ORIGINAL_PROVENANCE_TWELVE_ROUTES_AND_ACTUAL_BINDING_ONLY')
        exact({k:v for k,v in declaration.items()if k not in('base_head','base_tree','files','actual_parent_qualification')},
            {k:v for k,v in original.items()if k not in('base_head','base_tree','files','actual_parent_qualification')},
            'FREE3_ALL_OTHER_ORIGINAL_SOURCE_CONTRACT_FIELDS_UNCHANGED')
        exact(declaration['actual_parent_qualification'],actual,'FREE3_EXACT_ACTUAL_PARENT_QUALIFICATION')
        exact(set(declaration['files']),set(original['files'])|{receipt_path,WORKFLOW},'FREE3_ONLY_TWO_NEW_OWN_PATHS')
        exact(g.read(WORKFLOW),old.read(NS+'native3.workflow.yml.txt'),'FREE3_EXACT_ORIGINAL_REVIEWED_WORKFLOW')
    return dict(status='EXACT_OWN38_TO40_FOUR_BINDING_FILES_AND_FOUR_NESTED_PINS_ONLY',
        unchanged_old_own_blobs_and_modes=32,actual_case_credit=0)


def report_validator(g):
    """Compile only the exact four pure functions from an immutable blob."""
    selected=[node for node in ast.parse(g.read(NS+'final_gate.py')).body
              if isinstance(node,ast.FunctionDef)and node.name in('money','posted','case_boundary','validate')]
    exact([node.name for node in selected],['money','posted','case_boundary','validate'],'FREE3_EXACT_FOUR_PURE_VALIDATOR_FUNCTIONS')
    names={'ValueError','type','len','set','dict','str','list','range','sum','any',
           'int','Decimal','ZoneInfo','timedelta','money','posted','case_boundary'}
    attributes={'fields','exact','fromisoformat','combine','isoformat','utcoffset','is_finite','get','items','values',
                'startswith','isdecimal'}
    for function in selected:
        require(not function.decorator_list,'FREE3_PURE_VALIDATOR_NO_DECORATOR')
        for node in ast.walk(function):
            require(not isinstance(node,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,
                ast.With,ast.AsyncWith,ast.Await,ast.Yield,ast.YieldFrom)),
                'FREE3_PURE_VALIDATOR_NO_RUNTIME_IMPORT_OR_CONTEXT')
            if isinstance(node,ast.Attribute):
                require(not node.attr.startswith('__'),'FREE3_PURE_VALIDATOR_NO_SPECIAL_ATTRIBUTE')
            if isinstance(node,ast.Call):
                call=node.func
                require((isinstance(call,ast.Name)and call.id in names)
                    or(isinstance(call,ast.Attribute)and call.attr in attributes),
                    'FREE3_PURE_VALIDATOR_DECLARED_CALLS_ONLY:'+ast.unparse(call))
    module=ModuleType('ROOT_EXACT_PURE_FREE3_REPORT_VALIDATOR')
    module.__dict__.update(Decimal=Decimal,date=date,datetime=datetime,time=time,timedelta=timedelta,
                          ZoneInfo=ZoneInfo,CASE=CASE)
    exec(compile(ast.Module(body=selected,type_ignores=[]),NS+'final_gate.py:pure-only','exec'),module.__dict__)
    return module,dict(selected_functions=[node.name for node in selected],
        exact_source=pin(g.read(NS+'final_gate.py')),actual_ERP_imports=0,actual_SQL_executed=0)


def source_guard_derivation(g,origin):
    guard=origin['source_preflight_origin']
    fields(guard,dict(head='674a700096eab400e9b75700e4a2704f799d69b8',
        path='scripts/current-complete-de-integration-preparation/source.py',bytes=4260,
        sha256='8fcd679648b2cc0902562c39d00588594dbbf426ab8e40aabf2f4cbbde30dccb'),
        'FREE3_EXACT_ORIGINAL_SOURCE_GUARD')
    raw=g.read(guard['path'],guard['head']);exact(pin(raw),{k:guard[k]for k in('bytes','sha256')},
        'FREE3_ORIGINAL_SOURCE_GUARD_BYTES')
    text=raw.decode();exact(len(guard['changes']),12,'FREE3_SIX_ORIGINAL_AND_SIX_EXPLICIT_WORKFLOW_SOURCE_ROUTES')
    for row in guard['changes']:
        require(type(row['before'])is str and row['before']and type(row['after'])is str and row['after']
            and type(row['count'])is int and row['count']>0,'FREE3_EXACT_TYPED_SOURCE_ROUTE')
        exact(text.count(row['before']),row['count'],'FREE3_EXACT_SOURCE_GUARD_ROUTE_ANCHOR')
        text=text.replace(row['before'],row['after'],row['count'])
    exact(text.encode(),g.read(NS+'source.py'),'FREE3_ONLY_COUNTED_SOURCE_GUARD_CHANGES')
    for row in reversed(guard['changes']):
        exact(text.count(row['after']),row['count'],'FREE3_EXACT_SOURCE_ROUTE_REVERSE')
        text=text.replace(row['after'],row['before'],row['count'])
    exact(text.encode(),raw,'FREE3_ENTIRE_ORIGINAL_SOURCE_GUARD_RECOVERED')
    exact(literal(g,NS+'source.py','WORKFLOW'),WORKFLOW,'FREE3_ONLY_THE_EXACT_WORKFLOW_PATH_ADMITTED')
    return dict(original_source_guard=pin(raw),counted_source_routes=12,
        entire_original_recovered=True,actual_case_credit=0)

def runtime_fixture_binding_repair(g,declaration):
    """Admit one exact source repair; keep the failed C73 and all product pins."""
    old_head='c73dea71ad8e15e828ea7f4a27937c5c9da5e839'
    old_tree='b171e37eb8a76d3764e60662f93f368f98f41883'
    origin_path=NS+'RUNTIME_FIXTURE_BINDING_REPAIR.json'
    expected_pins={"scripts/current-de-free-date-preparation/native_free.py":{"bytes":17601,"sha256":"ef17c94216892f2a40681eac8372a0bd1e6fddc52e7dbd5f3868a85145734792"},"scripts/current-de-free-date-preparation/probe.py":{"bytes":3907,"sha256":"b7b3a4fbca8bfe2321b40f96265906e50b50ff2415b7ad019b0ae617837653df"},"scripts/current-de-free-date-preparation/workflow.py":{"bytes":6280,"sha256":"5bbbfc673330602d65a913bfc7c66d2465be589c8e3b92159146e85ae718c750"},"scripts/current-de-free-date-preparation/native3.workflow.yml.txt":{"bytes":33770,"sha256":"5b8360a78183ecdbafb60c51c8d6004afac9cd40a96587d229348a1818310342"},".github/workflows/cp7-current-complete-de-free-date-native3.yml":{"bytes":33770,"sha256":"5b8360a78183ecdbafb60c51c8d6004afac9cd40a96587d229348a1818310342"},"scripts/current-de-free-date-preparation/RUNTIME_FIXTURE_BINDING_REPAIR.json":{"bytes":11076,"sha256":"e4ad30a2b4a4b65d65dff32f9ebbe24103623e0f8cabd93d4ad2cbeb00db6f20"}}
    exact(len(expected_pins),6,'FREE3_EXACT_FIVE_REPAIRED_FILES_AND_ONE_ORIGIN')
    for name,value in expected_pins.items():g.verify_pin(name,value)
    origin=strict(g.read(origin_path))
    fields(origin,dict(classification='EXACT_C73_RUNTIME_FIXTURE_BINDING_AND_PREDB_PREFLIGHT_AND_CLEANUP_REPAIR_NOT_QUALIFICATION',
        head=old_head,tree=old_tree,changed_old_own_paths=6,new_own_paths=1,
        unchanged_old_own_paths=34,own_paths=41,source_pins=40,reversible_routes=12,
        financial_SQL_and_Native_case_bodies_changed=False,fixture_or_runner_original_file_changes=0,
        prior_product_source_graph_changed=False,workflow_changed_steps=[64,73],
        job_budget_seconds=21600,preDB_fixture_binding_runs_in_exact_actual_writer_CWD=True,
        actual_Native_cases=0,production_go=False,independent_acceptance=False),
        'FREE3_EXACT_FAILED_C73_RUNTIME_SOURCE_REPAIR')
    exact(set(origin['files']),set(expected_pins)-{origin_path},'FREE3_EXACT_FIVE_REPAIRED_SOURCE_PATHS')
    with GitBytes(g.root,old_head,old_tree)as old:
        retained=source(old)  # Preserve every existing own40/parent/origin/validator gate.
        original=strict(old.read(NS+'SOURCE.json'))
        old_paths=set(original['files'])|{NS+'SOURCE.json'}
        changed=set(origin['files'])|{NS+'SOURCE.json'}
        exact(len(old_paths-changed),34,'FREE3_THIRTYFOUR_UNCHANGED_OLD_OWN_FILES')
        exact(set(g.tree)-set(old.tree),{origin_path},'FREE3_ONLY_ONE_NEW_REPAIR_ORIGIN')
        for name in set(old.tree)-changed:
            exact(g.tree.get(name),old.tree[name],'FREE3_ALL_OTHER_CURRENT_SOURCE_BLOBS_AND_MODES_UNCHANGED:'+name)
        routes=0
        for name,value in origin['files'].items():
            original_raw=old.read(name);exact(pin(original_raw),value['before'],'FREE3_EXACT_FAILED_SOURCE_BYTES:'+name)
            raw=g.read(name);exact(pin(raw),value['after'],'FREE3_EXACT_REPAIRED_SOURCE_BYTES:'+name)
            exact(g.tree[name]['mode'],old.tree[name]['mode'],'FREE3_REPAIR_KEEPS_SOURCE_MODE:'+name)
            text=original_raw.decode()
            for change in value['changes']:
                fields(change,dict(count=1),'FREE3_SINGLE_EXACT_REPAIR_ROUTE')
                exact(text.count(change['before']),1,'FREE3_EXACT_REPAIR_BEFORE_ANCHOR')
                text=text.replace(change['before'],change['after'],1);routes+=1
            exact(text.encode(),raw,'FREE3_ONLY_REVIEWED_RUNTIME_REPAIR_ROUTES:'+name)
            for change in reversed(value['changes']):
                exact(text.count(change['after']),1,'FREE3_EXACT_REPAIR_REVERSE_ANCHOR')
                text=text.replace(change['after'],change['before'],1)
            exact(text.encode(),original_raw,'FREE3_ENTIRE_FAILED_ORIGINAL_RECOVERED:'+name)
        exact(routes,12,'FREE3_ONLY_TWELVE_EXACT_REPAIR_ROUTES')
        expected=dict(original)
        expected['files']=dict(original['files'],**expected_pins)
        expected['runtime_fixture_binding_repair']=dict(origin=origin_path,
            before_head=old_head,before_tree=old_tree,actual_Native_cases=0)
        exact(declaration,expected,'FREE3_ONLY_PINNED_FIXTURE_PREFLIGHT_AND_CLEANUP_MANIFEST_REPAIR')
        def business_functions(raw,excluded):
            return {node.name:ast.dump(node,include_attributes=False)for node in ast.parse(raw).body
                if isinstance(node,ast.FunctionDef)and node.name not in excluded}
        exact(business_functions(g.read(NS+'native_free.py'),{'bind','runtime_modules'}),
              business_functions(old.read(NS+'native_free.py'),{'bind'}),
              'FREE3_ALL_NATIVE_CASE_AND_FINANCIAL_FUNCTION_BODIES_UNCHANGED')
    return dict(status='EXACT_OWN40_TO41_FIXTURE_PREFLIGHT_AND_CLEANUP_REPAIR_ONLY',
        failed_head=old_head,failed_tree=old_tree,retained_failed_candidate_source=retained,
        unchanged_old_own_blobs_and_modes=34,reversible_routes=12,
        Native_case_and_financial_function_bodies_unchanged=True,actual_case_credit=0)


def source(g):
    base_head=PARENT_HEAD or PREPARED_BASE;base_tree=PARENT_TREE or PREPARED_BASE_TREE
    repaired=None
    declaration=strict(g.read(NS+'SOURCE.json'))
    fields(declaration,dict(classification='CLOSED_DATE_ON_COMPLETE_DE_PREPARATION_NOT_QUALIFICATION',
        base_head=base_head,base_tree=base_tree,actual_Native_cases=0,production_go=False,
        independent_acceptance=False),'FREE3_SOURCE_PREPARATION_NOT_ACTUAL_CASE_CREDIT')
    exact(g.git('rev-parse',base_head+'^{tree}').decode().strip(),base_tree,'FREE3_EXACT_PARENT_TREE')
    base=g.entries(base_head)
    for name,value in base.items():exact(g.tree.get(name),value,'FREE3_PARENT_BLOB_AND_MODE:'+name)
    allowed=set(declaration['files'])|{NS+'SOURCE.json'}
    require(all(name.startswith(PREFIXES)or name==WORKFLOW for name in allowed),'FREE3_ONLY_OWN_NAMESPACES')
    exact(set(g.tree)-set(base),allowed,'FREE3_EXACT_CLOSED_ADDITIVE_SOURCE')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    if PARENT_HEAD is None:
        exact(len(base),14181,'FREE3_PREPARED_BASE14181');exact(len(allowed),38,'FREE3_PREPARED_OWN38')
        exact(literal(g,NS+'admission.py','PARENT_HEAD'),None,'FREE3_PREPARED_PARENT_GATE_CLOSED')
        exact(literal(g,NS+'admission.py','PARENT_RECEIPT'),None,'FREE3_PREPARED_RECEIPT_GATE_CLOSED')
        require(WORKFLOW not in g.tree,'FREE3_PREPARED_WORKFLOW_NOT_ACTIVATED')
    else:
        exact(len(base),14265,'FREE3_ACTUAL_ACCEPTED_CURRENT_DE_PARENT14265')
        if 'runtime_fixture_binding_repair' in declaration:
            exact(len(allowed),41,'FREE3_EXACT_REPAIRED_OWN41')
            repaired=runtime_fixture_binding_repair(g,declaration)
        else:
            exact(len(allowed),40,'FREE3_EXACT_ACTIVATED_OWN40')
            actual_activation_source(g,declaration)
        exact(literal(g,NS+'admission.py','PARENT_HEAD'),PARENT_HEAD,'FREE3_ACTUAL_ACCEPTED_PARENT_HEAD')
        require(WORKFLOW in allowed,'FREE3_ACTUAL_WORKFLOW_MUST_BE_EXPLICITLY_DECLARED')
        exact(g.read(WORKFLOW),g.read(NS+'native3.workflow.yml.txt'),'FREE3_ACTUAL_WORKFLOW_EQUALS_REVIEWED_TEMPLATE')
    exact(list(literal(g,NS+'native_free.py','IDS')),IDS,'FREE3_THREE_EXACT_UNIQUE_SOURCE_CASE_IDS')
    exact(literal(g,NS+'final_gate.py','CASE'),CASE,'FREE3_FINAL_GATE_CASE_ID')
    native=strict(g.read(NS+'FREE_NATIVE3_SOURCE.json'))
    fields(native,dict(classification='PREPARED_THREE_NATIVE_FREE_DATE_CASES_NOT_ACTUAL_EXECUTION',
        head='13db04e03a060e3a1faaac9f7125d9a2e5578adb',case_ids=IDS,fixture_or_runner_changes=0,
        posted_free_lines_per_post=1,paid_companion_lines=0,mandatory_PO_or_FG_matching=False,
        product_clock_changed=False,actual_Native_cases=0,actual_SQL_executed=0,
        GOOD_eligibility_policy_decided=False,production_go=False,independent_acceptance=False),
        'FREE3_NATIVE_SOURCE_NO_ECONOMIC_POLICY_OR_ACTUAL_CREDIT')
    exact(set(native['unchanged_sources']),{'scripts/cp6_bc_probe.py','scripts/cp6_auditor_runner.py',
        'scripts/cp6_v2620c_live_rollback_race.py'},'FREE3_THREE_UNCHANGED_FIXTURE_RUNNER_SOURCES')
    for name,value in native['unchanged_sources'].items():
        raw=g.verify_pin(name,value);exact(raw,g.read(name,native['head']),'FREE3_ORIGINAL_NATIVE_FIXTURE_BYTES:'+name)
    origin=strict(g.read(NS+'ORIGIN.json'))
    fields(origin,dict(head='c43dabf4378fb8096cd86b37adc9b24c359efa63',
        tree='c373fb2f1cb56db996880e4e18702588f5fc5261',
        SQL_predicate_or_original_lifecycle_function_changes=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False),'FREE3_EXACT_C43_DATE_STAGE_ORIGIN')
    exact(len(origin['files']),9,'FREE3_NINE_ORIGINAL_C43_DATE_FILES')
    changes=0
    for name,value in origin['files'].items():
        raw=g.read(value['source_path'],origin['head']);exact(pin(raw),
            {key:value[key]for key in('bytes','sha256')},'FREE3_EXACT_ORIGINAL_C43_BYTES:'+name)
        text=raw.decode()
        for change in value['changes']:
            exact(text.count(change['before']),change['count'],'FREE3_DECLARED_DATE_STAGE_ROUTE_ANCHOR')
            text=text.replace(change['before'],change['after'],change['count']);changes+=change['count']
        exact(text.encode(),g.read(name),'FREE3_ONLY_DECLARED_C43_PARENT_AND_CONTRACT_ROUTES:'+name)
    exact(changes,2,'FREE3_ONLY_TWO_DATE_STAGE_PARENT_AND_CONTRACT_ROUTES')
    guard_source=source_guard_derivation(g,origin)
    nested_source=nested_manifest_sources(g)
    _,validator=report_validator(g)
    return dict(source_pins=len(declaration['files']),own_paths=len(allowed),unchanged_base=len(base),
        Native_case_ids=IDS,original_C43_date_files=9,explicit_date_stage_routes=2,
        unchanged_Native_fixture_runner_sources=3,pure_report_validator=validator,
        exact_reversible_source_guard_derivation=guard_source,
        nested_product_source_closure=nested_source,runtime_fixture_binding_repair=repaired,
        source_manifest=pin(g.read(NS+'SOURCE.json')),actual_case_credit=0,
        parent_qualification_pending=PARENT_HEAD is None)


def supervision(value):
    require(HEAD is not None and RUN is not None,'FREE3_SUPERVISION_ACTUAL_IDENTITY_PENDING')
    fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=HEAD,
        github_run_id=str(RUN),github_run_attempt='1',worker_exit=0,signals=[],
        deadline_reached=False,external_signal=None,orphaned_child=False,
        process_group_empty=True,process_tree_empty=True,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600,
        actual_case_credit=0,production_go=False),'FREE3_ACTUAL_CURRENT_WORKER_COMPLETE_AND_REAPED')
    return dict(status='EXACT_FREE3_SUPERVISION_REQUIRED_NOT_BUSINESS_ACCEPTANCE',
        run_id=RUN,worker_completed_before_database_stop=True,actual_case_credit=0)


def intake(root,path,metadata):
    require(all(value is not None for value in(HEAD,TREE,RUN,JOB,PARENT_HEAD,PARENT_TREE,PARENT_RUN,PARENT_JOB)),
        'FREE3_ACTUAL_PARENT_AND_OWNING_RUN_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='success',expired=False),'FREE3_EXACT_TERMINAL_CANONICAL_API_METADATA')
    require(type(metadata['artifact_id'])is int and metadata['artifact_id']>0,'FREE3_ACTUAL_ARTIFACT_ID')
    expected=metadata['archive']
    require(type(expected['bytes'])is int and expected['bytes']>0,'FREE3_CANONICAL_ARCHIVE_POSITIVE_BYTES')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,
        'FREE3_CANONICAL_ARCHIVE_SHA256')
    path=Path(path);exact(path.stat().st_size,expected['bytes'],'FREE3_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'FREE3_CANONICAL_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'FREE3_NO_DUPLICATE_ARCHIVE_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FREE3_COMPLETE_CANONICAL_ARCHIVE_CRC')
        admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);raw=original(RAW)
        package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        supervised=supervision(original('FREE_DATE_RUNTIME_SUPERVISION.json'))
        pure,proof=report_validator(g)
        gate=pure.validate(SimpleNamespace(fields=fields,exact=exact,GATES=GATES),
            main,raw,package,backup,IDS,HEAD)
        fields(gate,dict(status='CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_AND_ALL5_PASS',head=HEAD,
            actual_fresh_cases=3,retained_DE30_fresh_case_credit=0,production_go=False,
            independent_acceptance=False),'FREE3_EXACT_PURE_CANONICAL_REPORT_GATE')
        group(raw,IDS)
        boundaries={}
        for key,row in raw['cases'].items():
            boundary=row['actual_full22_case_boundary']
            boundaries[key]=dict(
                before=full_census(boundary['before']['actual_all22'],boundary['before']['full_data_and_sequences']),
                after=full_census(boundary['after']['actual_all22'],boundary['after']['full_data_and_sequences']),
                audit_sequence_consumption=pure.case_boundary(boundary))
        used=main['committed'][CASE]['separate_committed_Native_use']
        exact(used['before'],used['after'],'FREE3_COMMITTED_USED_REFUSAL_RAW_NO_EFFECT')
        used_boundary=full_census(used['before']['actual_all22'],used['before']['full_data_and_sequences'])
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'FREE3_EXACT_CURRENT_OWNING_PACKAGE_RUN')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'FREE3_EXACT_ROLE_RESTORE')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'FREE3_OUTER_DATABASE_RESTORE')
        parent_raw=g.read(NS+'DE30_PARENT_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        fields(parent,dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_D1_E_NATIVE30_ALL5',head=PARENT_HEAD,
            tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,actual_Native_cases=30,actual_D1_cases=13,
            actual_E_cases=17,actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            package_all_five=True,prior_runs_aggregated=False,retained_permanent6_fresh_case_credit=0,
            D_complete=False,E_complete=False,global_writer_or_permission_or_lock_closure=False,
            production_go=False,independent_acceptance=False),'FREE3_ACTUAL_CANONICAL_ACCEPTED_DE30_PARENT')
        exact(pin(parent_raw),literal(g,NS+'admission.py','PARENT_RECEIPT'),'FREE3_PARENT_RECEIPT_PHYSICAL_SOURCE_PIN')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        exact(graph['date']['parent'],graph['parent'],'FREE3_NATURAL_DATE_AND_COMPLETE_DE_PARENT_GRAPH')
        parent_pin=pin(json.dumps(graph['parent'],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        exact(parent_pin,parent['qualified_complete_DE_sources'],'FREE3_ENTIRE_ACTUAL_DE30_PARENT_SOURCE_GRAPH')
        exact(main['source_declaration']['qualified_parent_sources'],parent_pin,'FREE3_ADMITTED_WHOLE_PARENT_SOURCE_PIN')
        return dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),
            originals=pins,source_admission=admitted,pure_report_validator=proof,actual_product_source_maps=maps,
            runtime_supervision=supervised,
            qualified_complete_DE_FREE_date_sources=pin(json.dumps(graph,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
            qualified_DE30=dict(head=PARENT_HEAD,tree=PARENT_TREE,run_id=PARENT_RUN,job_id=PARENT_JOB,
                root_intake=pin(parent_raw)),actual_Native_cases=3,actual_business_cases=3,
            actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            complete3_qualified=True,package_all_five=True,prior_runs_aggregated=False,
            retained_DE30_fresh_case_credit=0,actual_full22_case_boundaries=boundaries,
            actual_used_refusal_raw_boundary=used_boundary,GOOD_eligibility_policy_decided=False,
            Afui_GOOD_nonpayable_path_complete=False,D_complete=False,E_complete=False,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(dict(status='EXACT_FREE3_SOURCE_AND_THREE_IDS_ONLY',source=value,actual_Native_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'FREE3_CANONICAL_ARCHIVE_API_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],actual_Native_cases=3)))
