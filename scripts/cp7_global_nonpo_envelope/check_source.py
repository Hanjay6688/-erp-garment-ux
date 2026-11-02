"""Physical preparation checks only; no DB/client import or Native operation."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def check():
    p=HERE/'SOURCE.json';manifest=json.loads(p.read_bytes())
    assert manifest['classification']=='CLOSED_GLOBAL_ENVELOPE_LOCK_AND_NATIVE_SCOPE_PREPARATION_NOT_QUALIFICATION'
    assert manifest['runtime_entry']is None and manifest['actual_Native_cases']==0
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=env)
    assert git('rev-parse',manifest['base_head']+'^{tree}').decode().strip()==manifest['base_tree']
    def entries(ref):
        result={}
        for line in git('ls-tree','-rz',ref).split(b'\0'):
            if line:
                meta,name=line.split(b'\t',1);result[name.decode()]=meta.decode()
        return result
    base,current=entries(manifest['base_head']),entries('HEAD')
    assert all(current.get(name)==meta for name,meta in base.items()),'GLOBAL_ENVELOPE_PREPARED_PARENT_CHANGED'
    physical={str(f.relative_to(ROOT))for f in HERE.rglob('*')if f.is_file()and'__pycache__'not in f.parts}
    assert physical==set(manifest['files'])|{str(p.relative_to(ROOT))},'GLOBAL_ENVELOPE_EXACT_OWN_SOURCE'
    for name,expected in manifest['files'].items():
        f=ROOT/name;assert f.is_file()and not f.is_symlink()and not f.stat().st_mode&0o111
        raw=f.read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected,name
    proof=json.loads((HERE/'SYNTAX_AND_SOURCE_CONTROLS.json').read_bytes())
    for name,expected in proof['files'].items():
        raw=(HERE/name).read_bytes();assert len(raw)==expected['bytes']and sha256(raw).hexdigest()==expected['sha256']
    assert proof['SQL_executed']==proof['Native_cases']==0 and proof['actual_installer_or_owning_hooks']==0
    assert len(set(proof['required_actual_accepted15a_relation_keys']))==42
    spec=importlib.util.spec_from_file_location('global_envelope_preparation_gate',HERE/'admission.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    assert gate.RUNTIME_ENTRY is None and gate.PARENT_HEAD is None and gate.PARENT_TREE is None and gate.PARENT_ROOT_RECEIPT is None
    try:gate.parent()
    except ValueError as error:assert str(error)=='CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'
    else:raise ValueError('GLOBAL_ENVELOPE_PARENT_GATE_WAS_OPENED')
    scope=json.loads((HERE/'WORK_SCOPE_MODEL_CONTROLS.json').read_bytes())
    assert scope['status']=='GLOBAL_NATIVE_WORK_SCOPE_BINDING_AND_OUTSIDE_MODEL_CONTROLS_PASS_NOT_ERP'
    assert len(scope['results'])==21 and all(row['result']in('PASS','REFUSED_AS_REQUIRED')for row in scope['results'])
    assert scope['actual_Native_work_column_maps']==3 and scope['actual_Native_work_columns']==73
    assert scope['actual_Native_owner_lifecycles_and_barrier_and_inspector_and_current_rights_are_models']is True
    assert scope['old_actual_lock_primitives_and_old_census_NOT_rerun']is True
    assert scope['Native_owning_hooks_written']==scope['actual_Native_cases']==scope['actual_Auth_HTTP_cases']==scope['actual_two_session_races']==scope['actual_browser_cases']==0
    assert scope['complete_installer_provided']is False and scope['parent_gate_opened']is False
    for name,expected in scope['source_files'].items():
        raw=(HERE/name).read_bytes();assert expected=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    reference=json.loads((HERE/'NATIVE_SCOPE_WORK_REFERENCE.json').read_bytes())
    assert reference['head']=='6e61506c10a18541c104b981bd438e78b175b5d1'
    assert len(reference['columns'])==3 and sum(map(len,reference['columns'].values()))==73
    sql='\n'.join((HERE/name).read_text()for name in('schema.sql','lock.sql','work_scope.sql','review.sql'))
    functions=re.findall(r'^create function ([a-z0-9_.]+)\(',sql,re.M)
    assert len(functions)==len(set(functions))==manifest['envelope_private_functions']==8
    tables=re.findall(r'^create table ([a-z0-9_.]+)\(',sql,re.M)
    assert len(tables)==len(set(tables))==manifest['private_tables']==3
    assert all(name.startswith('cp7_global_nonpo_envelope.')for name in functions+tables)
    writes=re.findall(r'^\s*(?:insert into|update|delete from)\s+([a-z0-9_.]+)',(HERE/'work_scope.sql').read_text(),re.M)
    assert set(writes)=={'cp7_global_nonpo_envelope.work_scopes_v1','cp7_global_nonpo_envelope.scope_completions_v1'}
    hooks=json.loads((HERE/'OWNING_HOOK_MODEL_CONTROLS.json').read_bytes())
    assert hooks['status']=='GLOBAL_PRIVATE_REVIEW_AND_EIGHT_OWNING_SOURCE_MODEL_CONTROLS_PASS_NOT_ERP'
    assert len(hooks['results'])==13 and all(row['result']in('PASS','REFUSED_AS_REQUIRED')for row in hooks['results'])
    assert hooks['actual_original_and_derived_owning_functions_compiled_on_model']==8
    assert hooks['exact_reversible_owning_source_routes']==18 and hooks['guard_sites']==3
    assert hooks['declared_Native_rowtype_maps']==9
    assert hooks['all_Native_business_functions_NOT_executed']is True
    assert hooks['old21_scope_models_and_old_actual_lock_and_catalog_controls_NOT_rerun']is True
    assert hooks['actual_final_parent_installer_or_runtime_armed']is False
    assert hooks['actual_Native_cases']==hooks['actual_Auth_HTTP_cases']==hooks['actual_two_session_races']==hooks['actual_browser_cases']==0
    for name,expected in hooks['source_files'].items():
        raw=(HERE/name).read_bytes();assert expected=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    origin=json.loads((HERE/'OWNING_HOOK_MODEL_ORIGIN.json').read_bytes())
    raw=(ROOT/origin['parent_path']).read_bytes()
    assert origin['parent_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    prefix=raw[:origin['original_prefix_bytes']].decode()
    for change in origin['source_routes']:
        assert change['count']==1 and prefix.count(change['before'])==1
        prefix=prefix.replace(change['before'],change['after'],1)
    assert (HERE/'owning_hooks_model.mjs').read_text().startswith(prefix)
    spec=importlib.util.spec_from_file_location('global_closed_counted_owning_source',HERE/'native_hooks.py')
    owning=importlib.util.module_from_spec(spec);spec.loader.exec_module(owning)
    definitions,routes=owning.derive(owning.originals())
    assert routes==json.loads((HERE/'NATIVE_OWNING_ROUTES_SOURCE_CONTROLS.json').read_bytes())
    assert len(definitions)==8 and routes['source_routes']==18 and routes['global_guard_sites']==3
    assert routes['Native_propagation_transfer_sync_FIFO_HPP_journal_stock_engines_changed']==0
    assert routes['public_fields_or_permissions_changed']==0 and routes['actual_SQL_executed']==0
    spec=importlib.util.spec_from_file_location('global_exact_platform_catalog_source_only',HERE/'catalog_bridge.py')
    bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    _,bridge_proof=bridge.derive()
    assert bridge_proof==json.loads((HERE/'CATALOG_BRIDGE_SOURCE_CONTROLS.json').read_bytes())
    platform=(HERE/'platform_catalog_fence.sql').read_text()
    assert re.findall(r'^create function ([a-z0-9_.]+)\(',platform,re.M)==['cp7_global_catalog_fence.lock_v1']
    assert 'grant execute on function cp7_global_catalog_fence.lock_v1()to postgres;'in platform
    assert 'create role 'not in platform and 'alter default privileges'not in platform.lower()
    assert 'grant maintain'not in platform.lower()and 'grant update'not in platform.lower()
    assert 'cascade'not in bridge.inverse_sql().lower()and 'drop owned'not in bridge.inverse_sql().lower()
    assert manifest['platform_catalog_fence_functions']==2 and manifest['platform_catalog_fence_owner']=='supabase_admin'
    assert manifest['trusted_platform_bootstrap_and_cleanup_pending']is True
    relation_platform=(HERE/'platform_relation_fence.sql').read_text()
    assert re.findall(r'^create function ([a-z0-9_.]+)\(',relation_platform,re.M)==['cp7_global_catalog_fence.lock_relations_v1']
    assert 'grant execute on function cp7_global_catalog_fence.lock_relations_v1(text)to postgres;'in relation_platform
    assert bridge_proof['fresh_catalog_metadata_after_early_XID_drain']is True
    assert bridge_proof['original_later_XID_check_retained']is True and bridge_proof['source_routes']==3
    assert 'expected_relations into targets_'in relation_platform and 'COMPLETE_CATALOG_FENCE_REQUIRED_FIRST'in relation_platform
    spec=importlib.util.spec_from_file_location('global_fixed25_catalogue_profile_source_only',HERE/'catalogue_profile.py')
    catalogue=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalogue)
    catalogue_sql,catalogue_proof=catalogue.derive()
    assert catalogue_sql.encode()==(HERE/'catalogue_fingerprint.sql').read_bytes()
    assert catalogue_proof==json.loads((HERE/'CATALOGUE_PROFILE_SOURCE_CONTROLS.json').read_bytes())
    assert catalogue_proof['original_all22_groups']==22 and catalogue_proof['total_groups']==25
    assert manifest['catalogue_fingerprint_functions']==1
    assert bridge_proof['full_current_catalogue_checked_before_post_fence_source_graph_reads']is True
    spec=importlib.util.spec_from_file_location('global_portable_authority_hash_source_only',HERE/'semantic_routes.py')
    semantic=importlib.util.module_from_spec(spec);spec.loader.exec_module(semantic)
    semantic_texts,semantic_proof=semantic.derive()
    assert semantic_proof==json.loads((HERE/'SEMANTIC_AUTHORITY_SOURCE_CONTROLS.json').read_bytes())
    assert set(semantic_texts)=={'lock','review'}and semantic_proof['source_routes']==2
    assert semantic_proof['original_full_sources_recovered']is True
    assert semantic_proof['full_current_catalogue_profile_route_retained']is True
    helper=(HERE/'semantic_authority.sql').read_text()
    assert re.findall(r'^create function ([a-z0-9_.]+)\(',helper,re.M)==['cp7_global_nonpo_envelope.semantic_authority_v1']
    assert "language plpgsql immutable security invoker set search_path=''"in helper
    assert manifest['semantic_authority_functions']==1 and manifest['counted_semantic_hash_routes']==2
    sys.path.insert(0,str(ROOT/'scripts'))
    from cp7_global_nonpo_envelope import composition
    installation=composition.sources()
    assert installation['final_parent_head']is None and installation['runtime_entry']is None
    assert installation['complete_input_profile_pin']is None
    try:composition.install(None,b'{}',b'{}')
    except ValueError as error:assert str(error)=='CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'
    else:raise ValueError('GLOBAL_INSTALL_MUST_REFUSE_BEFORE_TOUCHING_CURSOR')
    plan=json.loads((HERE/'INSTALL_PLAN.json').read_bytes())
    assert plan['Native_adapters']==8 and plan['native_adapter_routes']==18
    assert len(plan['functions'])==16 and len(plan['tables'])==3 and len(plan['triggers'])==3
    assert len(plan['columns'])==32 and plan['constraint_count']==15 and plan['foreign_key_count']==1 and plan['index_count']==4
    assert manifest['guarded_complete_installer_source_provided']is True
    spec=importlib.util.spec_from_file_location('global_exact_readonly_graph_source_only',HERE/'readonly_graph.py')
    readonly=importlib.util.module_from_spec(spec);spec.loader.exec_module(readonly)
    assert readonly.source()==json.loads((HERE/'READONLY_GRAPH_SOURCE_CONTROLS.json').read_bytes())
    saved=json.loads((HERE/'READONLY_GRAPH_SAVED_DE30_COMPATIBILITY.json').read_bytes())
    assert len(saved)==2 and all(r['comparison']['actual_reference_functions']==r['comparison']['attributes_per_function']==19 and r['comparison']['view_equal']is True for r in saved.values())
    assert manifest['readonly_graph_functions']==4 and manifest['private_functions']==manifest['envelope_private_functions']+manifest['readonly_graph_functions']+manifest['platform_catalog_fence_functions']+manifest['catalogue_fingerprint_functions']+manifest['semantic_authority_functions']==16
    return dict(status='GLOBAL_PRIVATE_ENVELOPE_SOURCE_ONLY_NOT_RUNTIME_OR_PROFILE_QUALIFICATION',
        unchanged_parent_blobs_and_modes=len(base),own_source_pins=len(manifest['files']),
        parent_gate_closed=True,runtime_entry=None,profile_seed_statements=0,
        new_private_scope_functions=4,new_private_scope_tables=2,new_scope_model_controls=21,
        new_private_review_functions=2,prepared_owning_source_adapters=8,reversible_owning_source_routes=18,
        new_review_and_owning_model_controls=13,readonly_graph_source_functions=4,
        exact_retained_readonly_graph_source_files=5,total_private_functions=16,
        portable_semantic_authority_source_functions=1,counted_semantic_hash_source_routes=2,
        fresh_catalogue_fingerprint_source_functions=1,counted_fresh_catalogue_profile_source_routes=1,
        platform_catalog_fence_source_functions=2,
        counted_platform_lock_source_routes=2,actual_platform_capability_installed=False,
        actual_owning_hooks=0,guarded_complete_installer_source_provided=True,
        actual_complete_installer_qualified=False,actual_final_parent_adopted=False,
        actual_ERP_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
