"""Local Git, file-retention and explicit packet models; actual ERP cases zero."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType,SimpleNamespace
from unittest.mock import patch
import ast,io,json,os,subprocess,sys,unittest,zipfile
from money_execution_bindings import admission
import money_gate_support as gate_support
import execution_routes
import candidate_source
import money_current_parent_artifacts as artifacts
import money_current_parent_fetch as fetch
import money_current_parent_final_gate as final
import money_current_parent_materialize as materialize
import money_current_parent_receipts as receipts
import money_current_parent_runtime as runtime
import money_current_parent_supervisor as supervisor
import money_current_parent_workflow as workflow

HERE=Path(__file__).resolve().parent


def modeled_preflight():
    # Protocol values only: no accepted file or actual database outcome exists.
    meta=gate_support.expected()
    return dict(status='PASS',errors=[],actual_ERP_cases=0,clock_changed=False,
        posted_financial_fixtures='EXISTING_NATIVE_WRITERS_ONLY',source_graph='EXACT_QUALIFIED_PARENT_AND_ALL22_INSTALLATION',
        fixture_offsets_seconds=[-60,-59,-45,-40,-30,-20,-10],functions={s:True for s in meta['required_functions']},
        actors={name:dict(role='OWNER',database_role=['authenticated','authenticated'],
            permissions={key:True for key in meta['permissions'][name]},direct_call_capabilities={sig:True for sig in sigs})
            for name,sigs in meta['actor_functions'].items()},
        active_PCS=[['PCS']],accounts={'4100':[[True,True,'REVENUE']],'5100':[[True,True,'EXPENSE']]},
        account_mappings={key:[[True,True]]for key in meta['account_mappings']},
        canonical_location=[True,'FG_WAREHOUSE'],canonical_product_master=[True]*5,open_period=[['2026-10-20']],
        business_day='2026-11-04',observed_WIB='2026-11-04T10:00:00+07:00',
        earliest_opening_day='2026-10-31',material_receipt_day='2026-10-29')


def modeled_packet():
    ids=['EXPLICIT_MODEL_CASE_'+str(i)for i in range(19)]
    native=dict(status='PASS',planned_case_ids=ids,counts={'PASS':19},missing=[],complete_boundary_restored=True,
        production_go=False,independent_acceptance=False,final={n:'PASS'for n in ids},
        cases={n:dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
            session_leaks=dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[]))for n in ids})
    part=dict(status='PASS',actual_Native_cases=19,actual_Auth_browser=False,actual_two_session_races=0,
        qualification_scope='NATIVE_COMPONENT_ONLY',used_guard_refused_before_DDL=True,
        failure_evidence_preserved=True,acceptance_requires_complete_outer_restore_and_package=True,
        physical_FIFO_preserved=True,economic_valuation='SKU_LOCATION_GRADE_MOVING_AVERAGE_WITH_SOURCE_CENTS',
        production_go=False,independent_acceptance=False,native=deepcopy(native),native_prerequisites=modeled_preflight())
    main=dict(status='PASS',qualification_commit='explicit-model-head',required_case_ids=[final.component.CASE],
        required_case_ids_pass=True,actual_Native_cases=19,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        actual_browser_cases=0,actual_business_cases=19,real_Auth_HTTP_qualified=False,real_Auth_browser_claim=False,
        qualification_scope='CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY',baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
        used_guard_refused_before_DDL=True,full_combined_final_qualification=False,production_go=False,
        independent_acceptance=False,committed={final.component.CASE:part},
        focused_preuse_removal=dict(used_guard_before_DDL=True))
    owned=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='explicit-model-head',github_run_id='1',
        github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
        process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
        job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600)
    p=final.typed_reader()
    docs={final.MAIN:main,final.NATIVE:native,final.SUPERVISION:owned,final.PREFLIGHT:deepcopy(part['native_prerequisites']),
        'T3_PACKAGE_INSTALL.json':dict(gate=deepcopy(p.GATES),run_identity=dict(tool_head='explicit-model-head',
            github_sha='explicit-model-head',run_id='1',run_attempt='1')),
        'T3_BACKUP_RESTORE_DRILL.json':dict(status='RESTORED_IDENTICAL',checks=dict(rows=True,roles=True),data=dict(differ={}))}
    return p,docs,ids


class ExecutionPreparation(unittest.TestCase):
    def test_child_fetches_existing_native27_and_moving6_without_a_money_financial_run(self):
        parent=b'{"explicit_parent_fetch_interface_model":true}'
        with patch.object(runtime,'actual_inputs',return_value=(parent,b'candidate source model',{})),\
             patch.object(runtime,'frozen')as frozen,patch.object(fetch,'derive',return_value=('def main():pass',{})),\
             patch.object(subprocess,'run')as call:
            fetch.main()
        frozen.assert_called_once_with(runtime.FROZEN_SKU,admission.SKU_HEAD,admission.SKU_TREE)
        self.assertEqual(set(fetch.KINDS),{'MANDOR'})
        self.assertEqual(call.call_count,2)
        expected=['scripts/current-sku-moving-average-qualification/fetch_parent.py',
            'scripts/current-sku-cost-money-qualification/fetch_moving_parent.py']
        for actual,entry in zip(call.call_args_list,expected):
            self.assertEqual(actual.args,([sys.executable,'-B',str(runtime.FROZEN_SKU/entry)],))
            self.assertEqual(actual.kwargs,dict(cwd=runtime.FROZEN_SKU,check=True))

    def test_complete_candidate_source_recheck_requires_exact_full_bytes(self):
        value={'explicit_source_protocol_model':True,'actual_ERP_cases':0}
        raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
        with patch.object(runtime,'actual_inputs',return_value=(b'modeled parent',raw,{})),\
             patch.object(runtime,'frozen'),patch.object(candidate_source,'observe',return_value=(value,{})):
            self.assertEqual(candidate_source.check_frozen()[2],raw)
            with self.assertRaisesRegex(ValueError,'FIXED_FROZEN_SOURCE_CHECKOUT_REQUIRED'):
                candidate_source.check_frozen('/explicitly-wrong-model-checkout')
            value['extra_unbound_source']='changed'
            with self.assertRaisesRegex(ValueError,'COMPLETE_CANDIDATE_SOURCE_PREFLIGHT_CHANGED'):
                candidate_source.check_frozen()

    def test_candidate_collector_restores_search_path_after_import_refusal(self):
        before=list(sys.path)
        ref=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
        def git(root,*args):
            if args==('rev-parse','HEAD^{tree}'):return ref['candidate_tree']
            if args==('rev-parse','HEAD'):return 'explicit-local-head-model'
            if args==('status','--porcelain','--untracked-files=no'):return ''
            raise AssertionError(args)
        def modeled_load(name,path):
            sys.path.insert(0,'EXPLICIT_TEST_IMPORT_SIDE_EFFECT')
            raise RuntimeError('explicit source import refusal')
        with patch.object(candidate_source,'git',side_effect=git),patch.object(candidate_source,'load',side_effect=modeled_load):
            with self.assertRaisesRegex(RuntimeError,'explicit source import refusal'):
                candidate_source.observe('/source-interface-model-only')
        self.assertEqual(sys.path,before)

    def test_exact_execution_derivations_and_prerequisite_constants(self):
        proof=execution_routes.check()
        self.assertEqual(set(proof['files']),set(execution_routes.KINDS))
        self.assertTrue(all(v['complete_original_recovered']for v in proof['files'].values()))
        meta=gate_support.expected()
        self.assertEqual(len(meta['required_functions']),23)
        self.assertEqual(sum(len(v)for v in meta['actor_functions'].values()),19)

    def test_runtime_option_context_restores_arguments_after_closed_refusal(self):
        args=['money_current_parent_runtime.py','--check','unrelated-option']
        with patch.object(sys,'argv',args):
            with self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_CANDIDATE_SOURCE_AND_OWNING_ENTRY_PENDING'):
                runtime.runtime()
            self.assertIs(sys.argv,args)
            self.assertEqual(args,['money_current_parent_runtime.py','--check','unrelated-option'])

    def test_preflight_requires_complete_original_and_all_typed_capabilities(self):
        p,original,ids=modeled_packet()
        changes=[(['functions',sig],False)for sig in gate_support.expected()['required_functions']]
        for name,functions in gate_support.expected()['actor_functions'].items():
            changes.extend((['actors',name,'direct_call_capabilities',sig],False)for sig in functions)
            changes.extend((['actors',name,'permissions',key],False)for key in gate_support.expected()['permissions'][name])
            changes.extend([(['actors',name,'role'],'GUDANG'),(['actors',name,'database_role'],['postgres','postgres'])])
        changes.extend([(['errors'],['EXPLICIT_MODEL_REFUSAL']),(['clock_changed'],True),
            (['canonical_product_master'],[True]*4+[False]),(['canonical_location'],[True,'RAW_MATERIAL_WAREHOUSE']),
            (['active_PCS'],[['PCS'],['pcs']]),(['open_period'],[['2026-10-31']]),
            (['observed_WIB'],'2026-11-04T00:01:00+07:00'),(['observed_WIB'],'2026-11-04T10:00:00+00:00'),
            (['material_receipt_day'],'2026-10-28'),(['earliest_opening_day'],'2026-11-01'),
            (['synthetic_receipt_not_an_actual_qualification'],True),
            (['account_mappings','COGS'],[[1,True]])])
        for path,value in changes:
            docs=deepcopy(original);target=docs[final.PREFLIGHT]
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            docs[final.MAIN]['committed'][final.component.CASE]['native_prerequisites']=deepcopy(docs[final.PREFLIGHT])
            with self.subTest(path=path),self.assertRaises(ValueError):
                final.validate(p,docs,'explicit-model-head',ids)
        docs=deepcopy(original);docs[final.PREFLIGHT]['extra_unbound_observation']='changed'
        with self.assertRaisesRegex(ValueError,'COMPLETE_PREFLIGHT_ORIGINAL'):
            final.validate(p,docs,'explicit-model-head',ids)

    def test_all_actual_entrypoints_refuse_before_Git_files_or_network(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('premature file read')),\
            patch.object(subprocess,'check_output',side_effect=AssertionError('premature subprocess')),\
            patch.object(sys,'argv',['supervisor']):
            for call in(fetch.main,materialize.materialize,artifacts.prepare,supervisor.main,candidate_source.check_frozen,
                lambda:final.gate(Path('/not-an-original'),'not-accepted')):
                with self.subTest(entry=repr(call)),self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_CANDIDATE_SOURCE_AND_OWNING_ENTRY_PENDING'):call()

    def test_actual_mandor_canonical_fetch_retains_all_original_checks(self):
        for kind in fetch.KINDS:
            text,proof=fetch.derive(kind)
            self.assertEqual(proof['exact_routes'],21);self.assertTrue(proof['complete_original_recovered'])
            self.assertIn("run['run_attempt']!=1",text);self.assertIn("z.testzip()is not None",text)
            self.assertIn("len(set(names))!=len(names)",text)
            self.assertIn("required=_ACTUAL_ROOT_BINDING",text)
            self.assertIn(repr(fetch.KINDS[kind]['main']),text)
            self.assertIn("metadata['digest']!='sha256:'+expected['sha256']",text)

    def test_actual_parent_binding_resolves_only_its_own_modeled_archive(self):
        # Actual GETs zero: api is an explicit in-memory interface model.
        for kind,item in fetch.KINDS.items():
            with self.subTest(kind=kind),TemporaryDirectory()as directory:
                root=Path(directory);here=root/'scripts/current-sku-money-composite-preparation';here.mkdir(parents=True)
                target=root/'runner'/item['folder'];target.mkdir(parents=True)
                raw=b'{"explicit_local_model":true}\n';archive=target/item['archive']
                with zipfile.ZipFile(archive,'w')as z:z.writestr(item['main'],raw)
                ref=dict(admission.pin(archive.read_bytes()),members=1)
                receipt=dict(run_id=1,job_id=2,artifact_id=3,archive=ref,originals={item['main']:admission.pin(raw)},
                    **{item['sources']:{'explicit_model_only':True}})
                (here/item['file']).write_text(json.dumps(receipt));calls=[]
                metadata={
                    'actions/runs/1':dict(status='completed',conclusion='success',run_attempt=1,head_sha='model-'+kind),
                    'actions/jobs/2':dict(run_id=1,status='completed',conclusion='success'),
                    'actions/artifacts/3':dict(expired=False,size_in_bytes=ref['bytes'],digest='sha256:'+ref['sha256'],
                        workflow_run=dict(id=1,head_sha='model-'+kind))}
                text,_=fetch.derive(kind);module=ModuleType('explicit_fetch_model_'+kind)
                module.__file__=str(here/'derived.py');module._ACTUAL_ROOT_BINDING=SimpleNamespace(
                    PARENT_ROOT_PIN={'explicit_model':True},PARENT_HEAD='model-'+kind,parent=lambda data:json.loads(data))
                exec(compile(text,module.__file__,'exec'),module.__dict__)
                def api(path):calls.append(path);return deepcopy(metadata[path])
                module.api=api
                with patch.dict(os.environ,{'RUNNER_TEMP':str(root/'runner'),'GITHUB_ENV':str(root/'env')}),\
                    patch.object(subprocess,'run',side_effect=AssertionError('unexpected actual GET')),patch('builtins.print'):
                    module.main()
                    self.assertEqual((target/item['main']).read_bytes(),raw)
                    result=json.loads((root/'cp6-proof/t3'/item['output']).read_bytes())
                    self.assertEqual(result['head'],'model-'+kind)
                    self.assertEqual(calls,list(metadata))
                    metadata['actions/runs/1']['head_sha']='other-candidate'
                    with self.assertRaisesRegex(ValueError,'TERMINAL_EXACT'):module.main()

    def test_materialization_keeps_real_git_worktrees_and_refuses_dirty_source(self):
        with TemporaryDirectory()as directory:
            root=Path(directory)/'owner';root.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()
            git('init','-q');git('config','user.email','local-model@example.invalid');git('config','user.name','Local model')
            (root/'source').write_text('exact source\n');git('add','source');git('commit','-qm','explicit local model')
            head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
            with patch.object(materialize,'ROOT',root):
                for folder in('qualified-mandor-parent','qualified-sku-money'):
                    self.assertTrue(materialize.one(folder,head,tree)['created'])
                    self.assertFalse(materialize.one(folder,head,tree)['created'])
                source=root.parent/'qualified-mandor-parent/source';source.write_text('changed')
                with self.assertRaisesRegex(ValueError,'TRACKED_SOURCE_CHANGED'):
                    materialize.one('qualified-mandor-parent',head,tree)
                self.assertEqual(source.read_text(),'changed')
                with self.assertRaisesRegex(ValueError,'FIXED_REGULAR_WORKTREE_PATH'):
                    materialize.one('unexpected-tree',head,tree)

    def test_full_file_retention_in_three_frozen_trees_never_projects_or_overwrites(self):
        helpers=artifacts.helpers()
        with TemporaryDirectory()as directory,ExitStack()as stack:
            root=Path(directory)/'owner';own=root/'cp6-proof/t3';own.mkdir(parents=True)
            raw=b'\x00\xffcomplete binary original\n'*4096;(own/'original.bin').write_bytes(raw)
            for folder in artifacts.FOLDERS:(root.parent/folder).mkdir()
            for name,value in [('ROOT',root),('OWN',own),('MANIFEST',own/'manifest.json'),('RETAINED',own/'retained')]:
                stack.enter_context(patch.object(artifacts,name,value))
            stack.enter_context(patch.object(artifacts,'helpers',return_value=helpers))
            stack.enter_context(patch.object(runtime,'actual_inputs',return_value=('explicit-model',)*3))
            artifacts.prepare()
            for folder in artifacts.FOLDERS:
                parent=root.parent/folder/'cp6-proof/t3';self.assertEqual((parent/'original.bin').read_bytes(),raw)
                (parent/'original.bin').write_bytes(raw+b'new runtime bytes')
                (parent/'nested').mkdir();(parent/'nested/new.json').write_bytes(b'{"unprojected": [1,2,3]}')
            result=artifacts.retain();self.assertEqual(result['retained_files'],6)
            for folder in artifacts.FOLDERS:
                self.assertEqual((own/'retained'/folder/'original.bin').read_bytes(),raw+b'new runtime bytes')
            self.assertEqual((own/'original.bin').read_bytes(),raw)
            parent=root.parent/artifacts.FOLDERS[0]/'cp6-proof/t3'
            (parent/'original.bin').write_bytes(b'conflicting second result')
            with self.assertRaisesRegex(ValueError,'EXISTING_BYTES_CONFLICT'):artifacts.retain()
            self.assertEqual((own/'retained'/artifacts.FOLDERS[0]/'original.bin').read_bytes(),raw+b'new runtime bytes')

    def test_original_copy_helpers_refuse_source_destination_and_ancestor_symlinks(self):
        h=artifacts.helpers()
        with TemporaryDirectory()as directory:
            root=Path(directory);source=root/'src';destination=root/'dst';source.mkdir();destination.mkdir()
            p=source/'original';p.write_bytes(b'original');reference=h.pin(p)
            (destination/'linked').symlink_to(p)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):h.copy_exact(p,destination/'linked',source,destination,reference)
            (destination/'dir').symlink_to(source,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):h.copy_exact(p,destination/'dir/copy',source,destination,reference)

    def test_console_receipts_are_bounded_and_keep_full_original_immutable(self):
        with TemporaryDirectory()as directory:
            root=Path(directory);path=root/receipts.NAMES[0];raw=os.urandom(100000);path.write_bytes(raw)
            result=receipts.receipts(root)
            self.assertEqual(result['originals'][path.name],admission.pin(raw))
            self.assertLess(len(json.dumps(result)),16384);self.assertEqual(path.read_bytes(),raw)
            self.assertNotIn('gzip_base64',json.dumps(result));receipts.receipts(root)
            path.write_bytes(raw+b'changed')
            with self.assertRaisesRegex(ValueError,'FIRST_RECEIPT_CHANGED'):receipts.receipts(root)

    def test_supervisor_is_reversible_and_keeps_original_real_budgets(self):
        text,proof=supervisor.derive()
        self.assertTrue(proof['real_360_330_20_10_budgets_unchanged'])
        for before,after in reversed(supervisor.CHANGES):text=text.replace(after,before,1)
        self.assertEqual(admission.pin(text.encode())['sha256'],proof['original_sha256'])
        for token in('WORK_SECONDS','RECOVERY_SECONDS','process_tree_empty','--allow-database-stop'):
            self.assertIn(token,text)

    def test_workflow_preserves_67_original_steps_and_never_adds_active_file(self):
        import yaml
        text,proof=workflow.derive();old=yaml.safe_load((workflow.ROOT/workflow.ORIGINAL).read_bytes())
        new=yaml.safe_load(text);a=old['jobs']['p21']['steps'];b=new['jobs']['p21']['steps']
        self.assertEqual([i for i in range(79)if a[i]!=b[i]],list(workflow.ROUTED))
        self.assertEqual(sum(x==y for x,y in zip(a,b)),67)
        self.assertEqual(new['jobs']['p21']['timeout-minutes'],360)
        self.assertFalse((workflow.ROOT/workflow.WORKFLOW).exists())
        self.assertEqual((HERE/workflow.TEMPLATE).read_text(),text)
        self.assertNotIn('gzip_base64',b[76]['run']);self.assertEqual(b[-1]['if'],'always()')
        self.assertLess(b[67]['run'].index('candidate_source.py --check'),b[67]['run'].index('money_current_parent_runtime.py --check'))
        self.assertEqual(b[68:72],a[68:72]);self.assertEqual(new['permissions'],old['permissions'])

    def test_typed_final_packet_model_has_no_current_ERP_or_browser_credit(self):
        p,docs,ids=modeled_packet();result=final.validate(p,docs,'explicit-model-head',ids)
        self.assertTrue(result['prior_parent_cases_not_counted_as_fresh'])
        self.assertEqual(result['actual_browser_cases'],0);self.assertEqual(result['actual_Auth_HTTP_cases'],0)
        self.assertTrue(all(getattr(admission,name)is None for name in(
            'PARENT_HEAD','PARENT_TREE','PARENT_ROOT_PIN','PARENT_SOURCE_PIN','PARENT_MODULE_PIN',
            'SKU_HEAD','SKU_TREE','SKU_SOURCE_PREFLIGHT_PIN','SKU_SOURCE_PIN','RUNTIME_ENTRY')))
        with self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_CANDIDATE_SOURCE_AND_OWNING_ENTRY_PENDING'):
            final.gate(Path('/not-an-original'),'explicit-model-head')

    def test_packet_gate_refuses_false_green_recovery_identity_counts_and_orphans(self):
        p,original,ids=modeled_packet()
        mutations=[
            (final.MAIN,'synthetic_receipt_not_an_actual_qualification',True),
            (final.MAIN,'actual_Native_cases',5),(final.MAIN,'actual_Native_cases',True),
            (final.MAIN,'actual_Auth_HTTP_cases',2),(final.MAIN,'actual_browser_cases',2),
            (final.MAIN,'actual_business_cases',23),(final.MAIN,'cp6_restored',False),
            (final.MAIN,'baseline_full22_all_rows_all_sequences_equal',False),
            (final.MAIN,'restore_raw_public_equal',False),(final.MAIN,'baseline_advisors_equal',False),
            (final.MAIN,'advisor_gate',False),(final.MAIN,'used_guard_refused_before_DDL',False),
            (final.MAIN,'full_combined_final_qualification',True),(final.MAIN,'qualification_commit','old-head'),
            (final.SUPERVISION,'process_tree_empty',False),(final.SUPERVISION,'orphaned_child',True),
            (final.SUPERVISION,'work_budget_seconds',60),(final.SUPERVISION,'github_run_attempt','2'),
            (final.SUPERVISION,'github_run_id','2'),(final.SUPERVISION,'worker_exit',1)]
        for name,key,value in mutations:
            docs=deepcopy(original);docs[name][key]=value
            with self.subTest(name=name,key=key),self.assertRaises(ValueError):
                final.validate(p,docs,'explicit-model-head',ids)
        for gate in p.GATES:
            docs=deepcopy(original);docs['T3_PACKAGE_INSTALL.json']['gate'][gate]=False
            with self.subTest(gate=gate),self.assertRaises(ValueError):final.validate(p,docs,'explicit-model-head',ids)
        for checks,differ in[({'rows':1},{}),({'rows':False},{}),({},{}),({'rows':True},{'changed':'row'})]:
            docs=deepcopy(original);docs['T3_BACKUP_RESTORE_DRILL.json'].update(checks=checks,data={'differ':differ})
            with self.subTest(checks=checks,differ=differ),self.assertRaises(ValueError):
                final.validate(p,docs,'explicit-model-head',ids)

    def test_packet_gate_requires_complete_native_original_and_every_case_boundary(self):
        p,original,ids=modeled_packet()
        docs=deepcopy(original);docs[final.NATIVE]['cases'][ids[0]]['business_observation']='unrecorded change'
        with self.assertRaisesRegex(ValueError,'NOT_PROJECTED'):final.validate(p,docs,'explicit-model-head',ids)
        for key,value in [('full_boundary_restored',False),('public_schema_unchanged',False),
                          ('session_leaks',dict(advisory_locks=1,advisory_lock_keys=['leftover'],other_sessions=[]))]:
            docs=deepcopy(original);docs[final.NATIVE]['cases'][ids[0]][key]=value
            docs[final.MAIN]['committed'][final.component.CASE]['native']=deepcopy(docs[final.NATIVE])
            with self.subTest(key=key),self.assertRaises(ValueError):final.validate(p,docs,'explicit-model-head',ids)


if __name__=='__main__':unittest.main(verbosity=2)
