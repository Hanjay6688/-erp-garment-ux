"""Exact preparation input and byte checks, with no ERP import or SQL call."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def check():
    manifest=HERE/'SOURCE.json';value=json.loads(manifest.read_bytes())
    assert value['classification']=='CLOSED_FG_MANDOR_PRIVATE_BUYER_AND_ALLOCATION_PREPARATION_NOT_QUALIFICATION'
    assert value['actual_Native_cases']==0 and value['production_go']is False and value['independent_acceptance']is False
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=env)
    assert git('rev-parse',value['base_head']+'^{tree}').decode().strip()==value['base_tree']
    def entries(ref):
        result={}
        for line in git('ls-tree','-rz',ref).split(b'\0'):
            if line:
                metadata,path=line.split(b'\t',1);result[path.decode()]=metadata.decode()
        return result
    base,current=entries(value['base_head']),entries('HEAD')
    ui=json.loads((HERE/'UI_SOURCE.json').read_bytes())
    parent_ui=json.loads((HERE/'UI_PARENT_ORIGIN.json').read_bytes())
    assert parent_ui['base_head']==value['base_head']and parent_ui['base_tree']==value['base_tree']
    changed_ui=set(parent_ui['files'])
    assert changed_ui=={'src/productionRecovery.ts','src/types/database.preconnect.ts','src/ConnectedPayrollPage.tsx',
        'scripts/check-source-ownership.mjs','scripts/check-access-catalog.mjs'}
    assert all(current.get(name)==item for name,item in base.items()if name not in changed_ui),'FG_MANDOR_PREPARED_PARENT_BLOB_OR_MODE_CHANGED'
    ui_hunks=0
    for name,record in parent_ui['files'].items():
        raw=git('show',value['base_head']+':'+name)
        assert record['before']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
        text=raw.decode()
        for change in record['changes']:
            assert change['count']==1 and text.count(change['before'])==1
            text=text.replace(change['before'],change['after'],1);ui_hunks+=1
        assert text.encode()==(ROOT/name).read_bytes()
        assert record['after']==ui['files'][name]
        assert current[name].startswith('100644 blob ')
        for change in reversed(record['changes']):
            assert text.count(change['after'])==1
            text=text.replace(change['after'],change['before'],1)
        assert text.encode()==raw
    assert ui_hunks==9
    physical={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
    assert physical==set(value['files'])|{str(manifest.relative_to(ROOT))},'FG_MANDOR_CLOSED_OWN_SOURCE_REQUIRED'
    assert ui['existing_UI_paths_changed']==5 and ui['new_UI_paths']==8
    assert set(ui['files'])=={'src/MandorShopCards.tsx','src/MandorShopCards.dom.test.tsx',
        'src/mandorShopContract.ts','src/mandorShopContract.test.ts','src/mandor-shop.css','tests/fixtures/mandorShop.ts',
        'src/MandorShopPayrollPanel.tsx','src/MandorShopPayrollPanel.dom.test.tsx'}|changed_ui
    for name,expected in ui['files'].items():
        p=ROOT/name;assert p.is_file()and not p.is_symlink()
        raw=p.read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    assert set(current)-set(base)==physical|(set(ui['files'])-set(base)),'FG_MANDOR_ONLY_COMMITTED_CLOSED_OWN_SOURCE_REQUIRED'
    assert not git('diff','--name-only','HEAD','--').strip(),'FG_MANDOR_TRACKED_SOURCE_CHANGED'
    assert not git('diff','--cached','--name-only','--').strip(),'FG_MANDOR_STAGED_SOURCE_CHANGED'
    for name,expected in value['files'].items():
        p=ROOT/name;assert p.is_file()and not p.is_symlink()and not p.stat().st_mode&0o111
        raw=p.read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected,('FG_MANDOR_SOURCE_PIN_CHANGED',name)
    spec=importlib.util.spec_from_file_location('fg_mandor_storage_preparation_gate_only',HERE/'admission.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    assert gate.RUNTIME_ENTRY is None
    try:gate.accepted_parent(b'not-a-parent-receipt')
    except ValueError as error:assert str(error)=='CP7_MANDOR_SHOP_ACTUAL_FINAL_ACCEPTED_PARENT_PENDING'
    else:raise ValueError('FG_MANDOR_PREPARATION_PARENT_GATE_WAS_OPEN')
    model=json.loads((HERE/'STORAGE_MODEL_CONTROLS.json').read_bytes())
    assert model['status']=='FG_MANDOR_ISOLATED_STORAGE_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert model['actual_Native_cases']==0 and model['actual_Auth_HTTP_cases']==0 and model['actual_two_session_races']==0
    for name,expected in model['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    allocation=json.loads((HERE/'ALLOCATION_MODEL_CONTROLS.json').read_bytes())
    assert allocation['status']=='FG_MANDOR_PRIVATE_ALLOCATION_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert allocation['retained_storage_15_controls_NOT_rerun']is True
    assert allocation['actual_Native_cases']==allocation['actual_Auth_HTTP_cases']==allocation['actual_two_session_races']==allocation['actual_browser_cases']==0
    for name,expected in allocation['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'ALLOCATION_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'allocation.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==0 and syntax['actual_Native_cases']==0
    buyer=json.loads((HERE/'BUYER_MODEL_CONTROLS.json').read_bytes())
    assert buyer['status']=='FG_MANDOR_PRIVATE_BUYER_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert buyer['retained_storage_15_and_allocation_15_controls_NOT_rerun']is True
    assert buyer['actual_Native_cases']==buyer['actual_Auth_HTTP_cases']==buyer['actual_browser_cases']==buyer['actual_two_session_races']==0
    for name,expected in buyer['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'BUYER_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'buyers.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    repair=json.loads((HERE/'BUYER_UUID_INTEGER_QUOTIENT_REPAIR.json').read_bytes())
    route=repair['counted_route'];text=raw.decode()
    assert text.count(route['after'])==route['count']==1
    original=text.replace(route['after'],route['before'],1).encode()
    assert repair['first_source']=={'bytes':len(original),'sha256':sha256(original).hexdigest()}
    assert repair['changed_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert repair['first_model_is_not_PASS']is True and repair['Native_cases']==repair['ERP_installations']==0
    identity=json.loads((HERE/'SALE_IDENTITY_MODEL_CONTROLS.json').read_bytes())
    assert identity['status']=='FG_MANDOR_NATIVE_HEADER_IDENTITY_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert identity['retained_storage_15_allocation_15_buyer_20_controls_NOT_rerun']is True
    assert identity['actual_Native_cases']==identity['actual_Auth_HTTP_cases']==identity['actual_browser_cases']==identity['actual_two_session_races']==0
    assert identity['Native_financial_functions_changed']==0
    for name,expected in identity['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'SALE_IDENTITY_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'sale_identity.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    offset=json.loads((HERE/'OFFSET_MODEL_CONTROLS.json').read_bytes())
    assert offset['status']=='FG_MANDOR_PRIVATE_OFFSET_PROJECTION_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert offset['retained_67_storage_allocation_buyer_identity_controls_NOT_rerun']is True
    assert offset['previous_unpublished_19_offset_controls_NOT_reused_on_rebuilt_source']is True
    assert offset['actual_Native_cases']==offset['actual_Auth_HTTP_cases']==offset['actual_browser_cases']==offset['actual_two_session_races']==0
    assert offset['Native_payment_hooks_implemented']is False
    assert offset['authoritative_Native_paid_projection_integrated']is False
    for name,expected in offset['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'OFFSET_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'offset_projection.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    assert syntax['new_private_functions_compiled']==3 and syntax['new_private_tables_compiled']==1
    payment=json.loads((HERE/'PAYMENT_MODEL_CONTROLS.json').read_bytes())
    assert payment['status']=='FG_MANDOR_PRIVATE_PAYMENT_OWNER_RETAINED19_NEW4_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert payment['retained_model_controls']==19 and payment['fresh_model_controls']==len(payment['results'])==4
    assert payment['retained_19_not_rerun']is True and payment['original_failed_suite_remains_failure']is True
    assert payment['all23_fresh_one_attempt']is False and payment['retained_95_previous_model_controls_NOT_rerun']is True
    assert payment['actual_Native_cases']==payment['actual_Auth_HTTP_cases']==payment['actual_browser_cases']==payment['actual_two_session_races']==0
    assert payment['Native_runtime_or_public_RPC_activated']is False
    assert payment['Native_column_type_maps']==32 and payment['new_private_functions_compiled']==4 and payment['Native_adapter_definitions_compiled']==8
    for name,expected in payment['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    retained=json.loads((HERE/'PAYMENT_RETAINED19_MODEL_CONTROLS.json').read_bytes())
    assert retained['completed_controls_retained']==len(retained['results'])==19
    assert retained['full_suite_pass']is False and retained['original_failure_relabelled_PASS']is False
    assert retained['actual_Native_cases']==0
    raw=retained['original_model_source'].encode()
    assert retained['original_model_source_pin']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    for name,expected in retained['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    assert payment['retained_controls']==retained['results']
    routes=json.loads((HERE/'PAYMENT_NATIVE_ROUTES_SOURCE_CONTROLS.json').read_bytes())
    spec=importlib.util.spec_from_file_location('fg_mandor_exact_payment_route_source',HERE/'native_payment_routes.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    reference=json.loads((HERE/'NATIVE_PAYMENT_OWNER_REFERENCE.json').read_bytes())
    definitions,actual_routes=native.derive(reference['functions'])
    assert routes==actual_routes and len(definitions)==8 and routes['source_routes']==17
    assert routes['actual_Native_cases']==routes['actual_SQL_executed']==0
    history=json.loads((HERE/'PAYMENT_MODEL_REPAIR_HISTORY.json').read_bytes())
    assert history['prior95_NOT_rerun']is True and history['completed19_NOT_rerun_for_last4']is True
    assert history['last4_first_attempt_PASS']is True and history['all23_fresh_one_attempt']is False
    assert history['actual_Native_cases']==0
    guards=json.loads((HERE/'PAYMENT_GUARD_MODEL_CONTROLS.json').read_bytes())
    assert guards['status']=='FG_MANDOR_PROTECTED_NATIVE_JOURNAL_AND_INVOICE_BOUNDARY_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert len(guards['results'])==13 and all(row['result']in('PASS','REFUSED_AS_REQUIRED')for row in guards['results'])
    assert guards['new_guard_functions_compiled']==guards['new_Native_table_triggers_compiled']==6
    assert guards['Native_column_type_maps']==33 and guards['retained_95_and_payment23_controls_NOT_rerun']is True
    assert guards['Native_function_or_payment_owner_sources_changed']is False
    assert guards['actual_Native_cases']==guards['actual_Auth_HTTP_cases']==guards['actual_browser_cases']==guards['actual_two_session_races']==0
    for name,expected in guards['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    guard_origin=json.loads((HERE/'PAYMENT_GUARD_MODEL_ORIGIN.json').read_bytes())
    assert guard_origin['old19_and_last4_controls_NOT_rerun']is True
    raw=(ROOT/guard_origin['parent_path']).read_bytes()
    assert guard_origin['parent_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    prefix=raw[:guard_origin['original_prefix_bytes']].decode()
    for change in guard_origin['source_routes']:
        assert change['count']==1 and prefix.count(change['before'])==1
        prefix=prefix.replace(change['before'],change['after'],1)
    # The new test body starts after one newline; the old test block had one
    # additional blank separator. Preserve every executable prefix byte.
    assert prefix.endswith('\n\n')
    assert (HERE/'payment_guard_model.mjs').read_text().startswith(prefix[:-1])
    facade=json.loads((HERE/'FACADE_MODEL_CONTROLS.json').read_bytes())
    assert facade['status']=='FG_MANDOR_NARROW_PUBLIC_FACADE_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert len(facade['results'])==9 and all(row['result']in('PASS','REFUSED_AS_REQUIRED')for row in facade['results'])
    assert facade['public_functions_compiled']==facade['private_entrypoint_grants']==4
    assert facade['facade_role']=='cp7_mandor_shop_api'and facade['Native_master_context_column_type_maps']==3
    assert facade['retained_131_controls_NOT_rerun']is True
    assert facade['actual_native_function_or_private_owner_source_changes']==0
    assert facade['Native_runtime_or_public_facade_activated']is False
    assert facade['actual_Native_cases']==facade['actual_Auth_HTTP_cases']==facade['actual_browser_cases']==facade['actual_two_session_races']==0
    for name,expected in facade['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    facade_origin=json.loads((HERE/'FACADE_MODEL_ORIGIN.json').read_bytes())
    assert facade_origin['all_prior_131_controls_NOT_rerun']is True
    assert facade_origin['private_owners_or_actual_Native_function_bodies_changed']is False
    raw=(ROOT/facade_origin['parent_path']).read_bytes()
    assert facade_origin['parent_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    prefix=raw[:facade_origin['original_prefix_bytes']].decode()
    for change in facade_origin['source_routes']:
        assert change['count']==1 and prefix.count(change['before'])==1
        prefix=prefix.replace(change['before'],change['after'],1)
    assert (HERE/'facade_model.mjs').read_text().startswith(prefix)
    assert value['public_facade_functions']==6 and value['public_facade_entrypoint_grants']==6
    display=json.loads((HERE/'FACADE_DISPLAY_MODEL_CONTROLS.json').read_bytes())
    assert display['status']=='FG_MANDOR_EXACT_PUBLIC_DISPLAY_CENTS_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert len(display['results'])==4 and all(row['result']=='PASS'for row in display['results'])
    assert display['new_public_functions']==display['new_roles']==display['new_grants']==0
    assert display['public_read_projection_only']is True and display['prior_140_controls_NOT_rerun']is True
    assert display['actual_native_function_or_private_owner_source_changes']==0
    assert display['Native_runtime_or_public_facade_activated']is False
    for name,expected in display['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    origin=json.loads((HERE/'FACADE_DISPLAY_MODEL_ORIGIN.json').read_bytes())
    raw=(ROOT/origin['parent_path']).read_bytes()
    assert origin['parent_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    prefix=raw[:origin['original_prefix_bytes']].decode()
    for change in origin['source_routes']:
        assert change['count']==1 and prefix.count(change['before'])==1
        prefix=prefix.replace(change['before'],change['after'],1)
    assert (HERE/'facade_display_model.mjs').read_text().startswith(prefix)
    controls=json.loads((HERE/'UI_MODEL_CONTROLS.json').read_bytes())
    assert controls['status']=='FG_MANDOR_CONTROLLED_CARD_PARSERS_AND_DOM15_FIRST_PASS_NOT_BROWSER'
    assert controls['new_parser_cases']==8 and controls['new_DOM_cases']==7 and controls['total_new_cases']==15
    assert controls['first_execution_PASS']is True and controls['UI_is_not_yet_mounted_or_RPC_wired']is True
    route=json.loads((HERE/'CONTROLLED_UI_CONTROLLER_ROUTE.json').read_bytes())
    name=route['path'];assert name=='src/MandorShopCards.tsx'
    assert route['before']==controls['source_files'][name]and route['after']==ui['files'][name]
    text=(ROOT/name).read_text()
    for change in reversed(route['changes']):
        assert change['count']==1 and text.count(change['after'])==1
        text=text.replace(change['after'],change['before'],1)
    assert route['before']=={'bytes':len(text.encode()),'sha256':sha256(text.encode()).hexdigest()}
    assert all(expected==ui['files'][name]for name,expected in controls['source_files'].items()if name!=route['path'])
    controller=json.loads((HERE/'UI_CONTROLLER_MODEL_CONTROLS.json').read_bytes())
    assert controller['first_controller_cases']==controller['controller_logical_case_coverage']==10
    assert controller['first_controller_all_PASS']is True and controller['last_refresh_only_cases']==1 and controller['last_refresh_only_PASS']is True
    assert controller['other_first_controller_cases_NOT_rerun']is True and controller['prior_UI15_not_rerun']is True
    assert controller['parent_changed_mount_regression_cases']==17 and controller['parent_regression_first_PASS']is True
    assert controller['source_files']==ui['files']and controller['full_product_installed']is False
    for name,item in controller['one_bounded_parent_refresh_route'].items():
        raw=(ROOT/name).read_bytes();assert item['after']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
        change=item['change'];text=raw.decode();assert change['count']==1 and text.count(change['after'])==1
        prior=text.replace(change['after'],change['before'],1).encode()
        assert item['before']=={'bytes':len(prior),'sha256':sha256(prior).hexdigest()}
    existing=json.loads((HERE/'BROWSER_RPC_EXISTING_NATIVE3_REFERENCE.json').read_bytes())
    assert existing['head']=='6e61506c10a18541c104b981bd438e78b175b5d1'and len(existing['functions'])==3
    assert existing['actual_new_Native_cases']==existing['actual_SQL_executed']==0
    assert controls['actual_Native_cases']==controls['actual_Auth_HTTP_cases']==controls['actual_browser_cases']==controls['actual_two_session_races']==0
    sales=json.loads((HERE/'SALES_MODEL_CONTROLS.json').read_bytes())
    assert sales['status']=='FG_MANDOR_ATOMIC_SALES_RETAINED13_PLUS_FOCUSED_EDIT1_MODEL_PASS_NOT_NATIVE'
    assert len(sales['retained_controls'])==13 and len(sales['fresh_controls'])==1
    assert all(row['result']in('PASS','REFUSED_AS_REQUIRED')for row in sales['retained_controls']+sales['fresh_controls'])
    assert sales['completed13_NOT_rerun']is True and sales['prior144_NOT_rerun']is True
    assert sales['all14_fresh_one_attempt']is False
    assert sales['actual_Native_cases']==sales['actual_Auth_HTTP_cases']==sales['actual_browser_cases']==sales['actual_two_session_races']==0
    for name,expected in sales['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    original=(HERE/sales['first13_source']).read_bytes()
    assert sales['first13_source_pin']=={'bytes':len(original),'sha256':sha256(original).hexdigest()}
    origin=json.loads((HERE/'SALES_COMMAND_MODEL_ORIGIN.json').read_bytes())
    raw=(ROOT/origin['parent_path']).read_bytes();assert origin['parent_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    prefix=raw[:origin['original_prefix_bytes']].decode()
    for change in origin['source_routes']:
        assert change['count']==1 and prefix.count(change['before'])==1
        prefix=prefix.replace(change['before'],change['after'],1)
    assert original.decode().startswith(prefix)
    change=sales['model_prefix_route'];assert change['count']==1 and prefix.count(change['before'])==1
    prefix=prefix.replace(change['before'],change['after'],1)
    assert (HERE/'sales_command_model.mjs').read_text().startswith(prefix)
    reference=json.loads((HERE/'NATIVE_SALES_COMMAND_REFERENCE.json').read_bytes())
    assert reference['functions_unchanged_in_actual_after_committed_E_use']is True
    spec=importlib.util.spec_from_file_location('fg_mandor_exact_sales_route_source',HERE/'native_sales_routes.py')
    native_sales=importlib.util.module_from_spec(spec);spec.loader.exec_module(native_sales)
    definitions,proof=native_sales.derive(reference['functions'])
    assert proof==json.loads((HERE/'NATIVE_SALES_ROUTES_SOURCE_CONTROLS.json').read_bytes())
    assert set(definitions)=={'cp7_sales.form_options(jsonb)'} and proof['route']['count']==1 and proof['complete_original_recovered']is True
    assert value['private_functions']==value['schema_and_event_functions']+value['private_allocation_functions']+value['private_buyer_functions']+value['private_sale_identity_functions']+value['private_offset_functions']+value['private_payment_functions']+value['private_payment_guard_functions']+value['private_sales_command_functions']==34
    return dict(status='FG_MANDOR_EXACT_STORAGE_PREPARATION_SOURCE_ONLY',unchanged_parent_blobs_and_modes=len(base),
        own_source_pins=len(value['files']),storage_model_controls=len(model['results']),parent_gate_closed=True,
        private_allocation_model_controls=len(allocation['results']),retained_storage_controls_NOT_rerun=True,
        private_buyer_functions=6,private_buyer_model_controls=len(buyer['results']),
        private_sale_identity_functions=1,private_sale_identity_model_controls=len(identity['results']),
        private_offset_functions=3,private_offset_model_controls=len(offset['results']),
        private_payment_functions=4,retained_payment_model_controls=19,fresh_payment_model_controls=4,
        Native_payment_source_adapters=8,actual_payment_runtime_installed=False,
        private_payment_guard_functions=6,new_payment_guard_model_controls=13,Native_payment_guard_triggers=6,
        public_facade_source_functions=6,public_facade_model_controls=9,public_facade_runtime_activated=False,
        exact_display_model_controls=4,new_controlled_UI_paths=8,new_UI_parser_cases=8,new_UI_DOM_cases=7,
        UI_mounted_or_RPC_wired=True,parent_UI_paths_changed=5,reversible_parent_UI_hunks=9,
        controller_DOM_logical_cases=10,focused_changed_refresh_cases=1,parent_mount_regression_cases=17,
        retained_67_controls_NOT_rerun=True,Native_paid_projection_integration=False,
        Native_header_trigger_source_written=True,Native_header_trigger_ERP_qualification=False,
        retained_allocation_controls_NOT_rerun=True,
        private_sales_command_functions=3,retained_new_sales_controls=13,fresh_new_sales_controls=1,
        Native_sales_form_source_adapters=1,Native_total_source_adapters=9,
        runtime_entry=None,ERP_imports=0,SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
