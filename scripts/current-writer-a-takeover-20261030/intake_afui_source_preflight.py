"""Read the actual Afui91 preDB originals without repeating the natural import.

The source-only run stays failed: its final wrapper assumed every natural
module lived in auditor, although the accepted loader selects four byte-exact
modules from the explicitly materialized SKU backend. No Native credit follows.
"""
from pathlib import Path
import argparse,ast,json,zipfile
import intake_afui15 as child
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict

HEAD='f4f16c6920d94c2b9ef22fa33c62144595a672ed'
TREE='c2957cd8ee7c7ac00450a5cd636e39ff0e27675c'
CONTROLLER='ff55bac2411528715ef2b81bfec229794f341022'
RUN=41409274390
JOB=125158339919
ARTIFACT=13124394130
ARCHIVE={'bytes':6536,'sha256':'fa25e0c3e71ecc2295c45ffca037e55a2c89787cf0339ab6be831971b420818a'}
FROZEN='090b85d3fcb738d3e694d4329d306f199a686eb8'
WORKSPACE='/home/runner/work/-erp-garment-ux/-erp-garment-ux/'
MEMBERS={'FOUR_SOURCE_ORIGINALS.json','PHYSICAL_STATIC_SOURCE.json','ROOT_IMMUTABLE_SOURCE.json',
    'SOURCE_RESOURCE_PREFLIGHT.json','WRITER_CWD_NATURAL_DOMAIN_SOURCE_FENCE.json'}


def callbacks(g):
    def parts(node):
        if isinstance(node,ast.Name):return [node.id]
        if isinstance(node,ast.Attribute):
            base=parts(node.value)
            return base+[node.attr]if base else None
        return None
    result=[]
    for name in('native_fixture.py','native_cases.py','native_sales_cases.py','native_inverse_cases.py','access_cases.py'):
        for node in ast.walk(ast.parse(g.read(child.NS+name))):
            if not isinstance(node,ast.Call):continue
            route=parts(node.func)
            if(not route or route[0]not in('modules','bc','bd','invoice','qc','bom')or len(route)<2
                or(route[0]=='modules'and route[1]not in('bc','bd','invoice','qc','bom','product','control'))):continue
            require(not any(isinstance(v,ast.Starred)for v in node.args)
                and not any(k.arg is None for k in node.keywords),'AFUI_SOURCE_EXPLICIT_ORIGINAL_CALLBACK_ARGUMENTS')
            result.append(dict(source=name,line=node.lineno,operation='.'.join(route),
                positional=len(node.args),keywords=[k.arg for k in node.keywords]))
    return result


def intake(root,archive,metadata):
    fields(metadata,dict(head=CONTROLLER,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='failure',artifact_id=ARTIFACT,expired=False,archive=ARCHIVE),
        'AFUI_SOURCE_EXACT_ORIGINAL_FAILED_OWNER_AND_CANONICAL')
    exact(metadata['failed_steps'],['Validate zero database activity and retained exact owning API proof'],
        'AFUI_SOURCE_ONLY_LAST_WRAPPER_FAILED')
    require(all(s['conclusion']=='success'for s in metadata['required_actual_source_steps']),
        'AFUI_SOURCE_ACTUAL_PREREQUISITE_STEPS_ALL_SUCCEEDED')
    expected_steps=['Verify exact focused Root sources and require source worktree capacity',
        'Materialize every exact inherited source without database','Verify exactly four historical source Originals',
        'Admit exact actual FREE45 canonical parent before any database',
        'Check complete immutable Afui static source without database',
        'Bind actual complete natural runtime and domain APIs from real writer CWD']
    exact([s['name']for s in metadata['required_actual_source_steps']],expected_steps,
        'AFUI_SOURCE_ALL_SIX_ACTUAL_PREREQUISITES')
    exact(pin(archive.read_bytes()),ARCHIVE,'AFUI_SOURCE_EXACT_CANONICAL_BYTES')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(archive)as z:
        names=z.namelist();exact(set(names),MEMBERS,'AFUI_SOURCE_ALL_FIVE_ACTUAL_ORIGINALS')
        exact(len(names),len(MEMBERS),'AFUI_SOURCE_NO_DUPLICATES')
        for name in names:safe_path(name)
        exact(z.testzip(),None,'AFUI_SOURCE_COMPLETE_CRC')
        values={n:strict(z.read(n))for n in names};originals={n:pin(z.read(n))for n in names}
        recorded=values['ROOT_IMMUTABLE_SOURCE.json'];source=child.source(g)
        exact(recorded['identity'],dict(head=HEAD,tree=TREE),'AFUI_SOURCE_ACTUAL_EXACT_CANDIDATE')
        exact(recorded['source'],json.loads(json.dumps(source)),'AFUI_SOURCE_COMPLETE_ROOT_SOURCE_REDERIVED')
        physical=values['PHYSICAL_STATIC_SOURCE.json'];natural=values['WRITER_CWD_NATURAL_DOMAIN_SOURCE_FENCE.json']
        fields(physical,dict(status='NONPAYABLE_STATIC_WHOLE_QUALIFIER_PREPARED_NOT_EXECUTED',
            actual_SQL_executed=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,
            actual_two_session_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False),
            'AFUI_SOURCE_ACTUAL_STATIC_COMMAND_ZERO_BUSINESS_CREDIT')
        fields(physical['source'],dict(own_paths=91,own_source_pins=58,unchanged_parent_paths=14306,
            accepted_parent_bound=True,actual_SQL_executed=0,actual_Native_cases=0,
            base_head=child.PARENT_HEAD,base_tree=child.PARENT_TREE),'AFUI_SOURCE_ACTUAL_PARENT_AND_OWN91')
        fields(natural,dict(status='ACTUAL_FREE3_PARENT_AND_COMPLETE_NONPAYABLE_SOURCE_GRAPH_ADMITTED',
            entire_natural_product_source_graph_evaluated=True,actual_Native_cases=0,production_go=False),
            'AFUI_SOURCE_REAL_COMPLETE_NATURAL_GRAPH_EVALUATED')
        fields(natural['source_DB_guard'],dict(attempts=[],network_nonGit_attempts=[],
            public_source_sha256='1439d70810383db377c48e043df7fb6d487a1b2f1a995e8993a2c08590f9f797',
            self_controls=[dict(api='psycopg.connect',result='DENIED_BEFORE_LIBPQ'),
                dict(api='psycopg.Connection.connect',result='DENIED_BEFORE_LIBPQ'),
                dict(api='psycopg.AsyncConnection.connect',result='DENIED_BEFORE_LIBPQ'),
                dict(original_connect_descriptors_restored=True)]),'AFUI_SOURCE_ORIGINAL_THREE_ENTRYPOINT_FENCE')
        binding=natural['actual_domain_and_caller_binding']
        fields(binding,dict(status='EXACT_AFUI_NATURAL_DOMAIN_AND_CALLER_APIS_BOUND_BEFORE_SQL',
            actual_working_directory=WORKSPACE+'writer',constructor_signature_bound=True,
            constructor_chain_global_unchanged=True,strict_runner_API_bound=True,
            canonical_module_cache_replaced=False,original_domain_sources_changed=False,
            actual_SQL_executed=0,actual_Native_cases=0,actual_original_output=WORKSPACE+'auditor/cp6-proof/aw'),
            'AFUI_SOURCE_UNCHANGED_ACTUAL_DOMAIN_AND_STRICT_RUNNER_BINDINGS')
        frozen={'cp6_bc_probe.py','cp6_bd_probe.py','cp6_auditor_runner.py','cp7_invoice_cases.py'}
        modules=frozen|{'cp7_qc_source_cases.py','cp7_accessory_standard_report/cases.py'}
        exact(set(binding['actual_modules']),modules,'AFUI_SOURCE_EXACT_SIX_NATURAL_MODULES')
        for name,record in binding['actual_modules'].items():
            raw=g.read('scripts/'+name);location='qualified-sku090b'if name in frozen else'auditor'
            if name in frozen:exact(raw,g.read('scripts/'+name,FROZEN),'AFUI_SOURCE_EXACT_DECLARED_FROZEN_COPY:'+name)
            exact(record,dict(path=WORKSPACE+location+'/scripts/'+name,**pin(raw)),
                'AFUI_SOURCE_BYTE_EXACT_RECORDED_NATURAL_MODULE:'+name)
        exact(binding['actual_call_bindings'],callbacks(g),'AFUI_SOURCE_ALL_ACTUAL_CALLBACKS_MATCH_ENTIRE_ORIGINAL_CALL_SOURCES')
        capacity=values['SOURCE_RESOURCE_PREFLIGHT.json']
        exact(capacity['source_worktrees'],14,'AFUI_SOURCE_ALL_FOURTEEN_PHYSICAL_PREREQUISITES')
        require(capacity['available_free_bytes']>=capacity['minimum_free_bytes']
            and capacity['available_free_inodes']>=capacity['minimum_free_inodes'],'AFUI_SOURCE_ACTUAL_CAPACITY_CHECK')
        originals4=values['FOUR_SOURCE_ORIGINALS.json']
        exact([v['artifact_id']for v in originals4['originals']],
            [12769642828,12758446701,12763033758,12766592167],'AFUI_SOURCE_ACTUAL_FOUR_ORIGINAL_ARCHIVES')
        exact(originals4['actual_Native_cases'],0,'AFUI_SOURCE_ARCHIVE_READS_ARE_NOT_NATIVE')
        return dict(status='ROOT_VERIFIED_AFUI91_SOURCE_ONLY_RETAINED_ACTUAL_FENCED_DOMAIN_BINDINGS',
            head=HEAD,tree=TREE,source_only_run_id=RUN,source_only_job_id=JOB,controller_head=CONTROLLER,
            artifact_id=ARTIFACT,archive=dict(ARCHIVE,members=5),originals=originals,source=source,
            actual_parent_root_receipt=pin(g.read(child.NS+'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json')),
            complete_natural_graph_and_real_domain_APIs_passed=True,actual_call_bindings=len(binding['actual_call_bindings']),
            actual_writer_CWD_verified=True,actual_three_entrypoint_DB_and_network_fence_verified=True,
            declared_frozen_modules_byte_identical_and_expected_paths_verified=True,
            retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
            original_failure='Final source wrapper wrongly required all natural modules to load from auditor; four exact original copies load from the declared qualified SKU backend',
            additional_wrapper_missing_field_corrected='Actual parent identity belongs to the original static source receipt, not the intentionally compact natural check output',
            source_modules_or_native_fixtures_changed=False,source_only_CI_rerun=False,
            actual_ERP_cases=0,actual_SQL_executed=0,actual_DB_connection_attempts=0,
            actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,actual_two_session_cases=0,
            full15_qualification=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=intake(a.source,a.archive,strict(a.metadata.read_bytes()))
    a.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in('status','head','tree','actual_call_bindings','actual_ERP_cases','failed_run_relabelled_PASS','source_only_CI_rerun')}))
