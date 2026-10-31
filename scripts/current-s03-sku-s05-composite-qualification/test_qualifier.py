"""Source and orchestration controls only: no Native or browser credit."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from contextlib import nullcontext
from hashlib import sha256
from unittest.mock import patch
import ast,importlib.util,io,json,subprocess,sys,tempfile,unittest,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location('join_control_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class SourceControls(unittest.TestCase):
    def test_browser_reuses_admitted_proof_and_refuses_changed_parent_before_private_import(self):
        private=load('native_s03')
        source={'predecessor':{'actual':'qualified-parent'}}
        proof=dict(status='EXACT_CURRENT_PARENTS_AND_NATURAL_S03_ON_SKU_PRODUCT_SOURCE_ADMITTED',
            product_sources_override=False,projected_source_graph=False,
            current_installation=source,qualified_SKU_current_installation=source['predecessor'])
        sentinel=object()
        with patch.object(private,'_modules',return_value=(None,sentinel,None))as prepared,patch.object(private,'load',side_effect=AssertionError('REPEATED_ADMISSION')):
            self.assertIs(private.business_runtime(proof),sentinel)
            prepared.assert_called_once_with(proof)
            for change in [dict(status='not-admitted'),dict(product_sources_override=True),
                           dict(projected_source_graph=True),dict(qualified_SKU_current_installation={'changed':True})]:
                with self.subTest(change=change),self.assertRaisesRegex(ValueError,'FRESH_ADMITTED_SOURCE'):
                    private.business_runtime(dict(proof,**change))
            self.assertEqual(prepared.call_count,1)

    def test_diagnostics_preserve_original_exception_and_append_without_case_credit(self):
        notes=load('runtime_note')
        with tempfile.TemporaryDirectory()as directory,patch.object(notes,'OUT',Path(directory)),patch.object(sys,'stderr',io.StringIO()):
            with self.assertRaisesRegex(KeyboardInterrupt,'original'):
                with notes.phase('CONTROL'):raise KeyboardInterrupt('original')
            rows=[json.loads(line)for line in(Path(directory)/'JOIN_RUNTIME_PROGRESS.jsonl').read_text().splitlines()]
            self.assertEqual([r['event']for r in rows],['START','RAISED_KeyboardInterrupt'])
            self.assertTrue(all(r['actual_case_credit']==0 and r['diagnostics_only']is True for r in rows))
            self.assertTrue(all(r['self_peak_rss_KiB']>0 for r in rows))
            with patch.object(notes.os,'open',side_effect=OSError('local-write-failure')):
                with self.assertRaisesRegex(RuntimeError,'original'):
                    with notes.phase('CONTROL_WRITE_FAILURE'):raise RuntimeError('original')

    def test_parent_import_reselects_after_vendor_path_change_and_refuses_foreign_module(self):
        selector=load('parent_import');root=Path('/control/qualified');previous=list(sys.path)
        def imported(name):
            self.assertEqual(sys.path[0],str(root/'scripts'))
            result=SimpleNamespace(__file__=str(root/'scripts'/(name.replace('.', '/')+'.py')))
            if name.startswith('cp7_vendor'):sys.path[:]=['/control/foreign/scripts']
            return result
        try:
            with patch.object(selector,'owning_harness',return_value={}),patch.object(selector.importlib,'import_module',side_effect=imported):
                self.assertEqual(len(selector.parent_modules(root)),2)
            with patch.object(selector,'owning_harness',return_value={}),patch.object(selector.importlib,'import_module',return_value=SimpleNamespace(__file__='/control/foreign/composition.py')):
                with self.assertRaisesRegex(ValueError,'ORIGIN_CHANGED'):selector.parent_modules(root)
        finally:sys.path[:]=previous

    def test_owning_harness_refuses_foreign_cached_cp6_module(self):
        selector=load('parent_import');previous=list(sys.path)
        package=SimpleNamespace(__file__=str(ROOT/'scripts/cp6_t3_package_run.py'),AUDITOR=ROOT,OUT=ROOT/'cp6-proof/t3')
        identity=SimpleNamespace(__file__=str(ROOT/'scripts/cp6_run_identity.py'),ROOT=ROOT)
        foreign=ModuleType('cp6_run_identity');foreign.__file__='/foreign/scripts/cp6_run_identity.py'
        try:
            with patch.object(selector.importlib,'import_module',side_effect=lambda name:package if name=='cp6_t3_package_run'else foreign):
                with self.assertRaisesRegex(ValueError,'OWNING_CP6_HARNESS_ORIGIN_CHANGED'):selector.owning_harness()
        finally:sys.path[:]=previous

    def test_retained_reader_group_accepts_json_arrays_and_refuses_tuple_or_changed_ids(self):
        source_path=ROOT/'scripts/current-s03-sku-native14-binding/prepare.py'
        spec=importlib.util.spec_from_file_location('joined_actual_reader_group_contract',source_path)
        source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
        texts,proof=source.prepare();private=load('native_s03')
        reader=private.code('control_unchanged_authored_reader',texts['reader'],path=HERE/'joined_reader.py',
            JOIN_READER_ADMISSION=object(),JOIN_CORE=object(),LAWFUL=object())
        # Admission-only orchestration control. The original callbacks and SQL
        # are not invoked and no financial case is credited by this control.
        ids=proof['original11_ids']
        original11=dict(status='PASS',counts={'PASS':11},planned_case_ids=list(ids),complete_boundary_restored=True,
            cases={key:dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True)for key in ids})
        class ReachedStrictGroup(Exception):pass
        def stop(*args):raise ReachedStrictGroup('REAL_READER_GROUP_ADMISSION_REACHED')
        previous=list(sys.path);sys.path.insert(0,str(ROOT/'scripts'))
        try:
            with tempfile.TemporaryDirectory()as directory:
                native=SimpleNamespace(public_state=lambda *args:None,strict_group=stop,r1=SimpleNamespace(OUT=Path(directory)))
                for kind in ('original_tuple_failure','JSON_arrays','changed_ID'):
                    configuration=private.reader_configuration(proof)
                    configured=proof['reader3_ids']if kind=='original_tuple_failure'else configuration['reader_Native3_ids']
                    if kind=='changed_ID':configured[0]+=':CHANGED'
                    group=private.code('control_complete_retained_reader_group',texts['reader_group'],path=HERE/'joined_reader_group.py',
                        JOIN_CONFIG=dict(original_Native11_ids=list(ids),reader_Native3_ids=configured),JOIN_READER=reader)
                    with self.subTest(kind=kind):
                        if kind=='JSON_arrays':
                            with self.assertRaises(ReachedStrictGroup):group.run(native,object(),{}, {},object(),original11)
                        else:
                            with self.assertRaisesRegex(ValueError,'EXACT_AUTHORED_READER3_IDS_REQUIRED'):group.run(native,object(),{}, {},object(),original11)
        finally:sys.path[:]=previous

    def test_all_derivations_recover_exact_immutable_blobs(self):
        declaration=json.loads((HERE/'DERIVATIONS.json').read_bytes())
        for name,item in declaration['files'].items():
            with self.subTest(name=name):
                raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',item['source_commit']+':'+item['source_path']])
                self.assertEqual(len(raw),item['original_bytes']);self.assertEqual(sha256(raw).hexdigest(),item['original_sha256'])
                if item.get('derivation')=='FULL_UNCHANGED_BRIDGE_FUNCTION_AND_EXACT_IDS_EXTRACTION':
                    derived=(HERE/name).read_bytes();original_tree=ast.parse(raw);current_tree=ast.parse(derived)
                    bridge=lambda tree:next(node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name=='_bridge')
                    ids=lambda tree:ast.literal_eval(next(node.value for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id=='IDS'for target in node.targets)))
                    self.assertEqual(ast.dump(bridge(original_tree)),ast.dump(bridge(current_tree)));self.assertEqual(ids(original_tree),ids(current_tree))
                    self.assertEqual(len(derived),item['derived_bytes']);self.assertEqual(sha256(derived).hexdigest(),item['derived_sha256']);continue
                text=raw.decode()
                for change in item['changes']:
                    self.assertEqual(text.count(change['before']),change['count']);text=text.replace(change['before'],change['after'])
                derived=(HERE/name).read_bytes();self.assertEqual(text.encode(),derived)
                self.assertEqual(len(derived),item['derived_bytes']);self.assertEqual(sha256(derived).hexdigest(),item['derived_sha256'])
                for change in reversed(item['changes']):
                    self.assertEqual(text.count(change['after']),change['count']);text=text.replace(change['after'],change['before'])
                self.assertEqual(text.encode(),raw)

    def test_complete_outer_engine_and_anchor_refusal(self):
        engine=load('engine');raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text,proof=engine.derive(raw);compile(text,'joined_complete_engine_control','exec')
        self.assertTrue(proof['complete_original_recovered']);self.assertEqual(proof['counted_changes'],2)
        with self.assertRaisesRegex(ValueError,'ANCHOR'):engine.derive(raw.replace(engine.INSTALL_BEFORE.encode(),b'changed',1))

    def test_typed_duplicate_and_nonfinite_original_refusals(self):
        parents=load('parents')
        for raw in ('{"PASS":1,"PASS":2}','{"PASS":NaN}','{"PASS":1e999}'):
            with self.assertRaises(ValueError):parents.strict(raw)
        for forged in (True,37.0,'37'):
            with self.assertRaisesRegex(ValueError,'TYPE'):parents.exact(forged,37,'FRESH_CASE_COUNT')

    def test_workflow_keeps_exact_setup_and_admits_before_DB(self):
        record=json.loads((HERE/'WORKFLOW_DERIVATION.json').read_bytes())
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',record['source_commit']+':'+record['source_path']])
        self.assertEqual(sha256(raw).hexdigest(),record['source_sha256'])
        old=yaml.safe_load(raw)['jobs']['p21']['steps']
        workflow=yaml.safe_load((ROOT/'.github/workflows/cp7-s03-sku-s05-composite.yml').read_bytes())
        current=workflow['jobs']['p21']
        self.assertEqual(workflow['on']['push']['branches'],['astra-a/s03-sku-product-join-20261031'])
        self.assertEqual(current['if'],"github.ref == 'refs/heads/"+workflow['on']['push']['branches'][0]+"'")
        steps=current['steps']
        for index in record['unchanged_steps']:
            expected=dict(old[index])
            if expected.get('name')in record.get('historical_admission_steps_use_exact_physical_SKU_checkout',[]):
                expected['working-directory']='qualified-sku090b'
            for change in record.get('clone_output_path_changes',[]):
                if expected.get('name')==change['step_name']:
                    self.assertEqual(expected['run'].count(change['before']),1)
                    expected['run']=expected['run'].replace(change['before'],change['after'],1)
            self.assertIn(expected,steps)
        start=next(i for i,s in enumerate(steps)if s.get('name')=='Start disposable database')
        for marker in ('fetch_parents.py','test_rpc_transport.mjs','probe.py --check'):
            self.assertTrue(any(marker in s.get('run','')for s in steps[:start]))
        actual=next(s for s in steps if 'probe.py\' --runtime' in s.get('run',''))
        self.assertIn('final_gate.py',actual['run']);self.assertEqual(current['timeout-minutes'],210)
        self.assertEqual(current['env']['JOIN_CONFIRM'],'cp6_rollback')
        self.assertEqual(current['env']['JOIN_QUALIFIED_SKU_ROOT'],'${{ github.workspace }}/qualified-sku090b')
        runtime_index=next(i for i,s in enumerate(steps)if 'probe.py\' --runtime'in s.get('run',''))
        retained_index=next(i for i,s in enumerate(steps)if 'retain_clone.py'in s.get('run',''))
        self.assertGreater(retained_index,runtime_index)
        self.assertEqual(steps[retained_index]['if'],'always()')
        diagnostic_upload=next(i for i,s in enumerate(steps)if s.get('name')=='Preserve the pre-runtime diagnostic independently of runner survival')
        self.assertLess(diagnostic_upload,runtime_index)
        self.assertEqual(steps[diagnostic_upload]['with']['path'],'auditor/cp6-proof/t3/JOIN_PRE_RUNTIME_RESOURCE.json')

    def test_exact_historical_app_is_admitted_and_current_additions_remain_explicit(self):
        backend=load('frozen_parent')
        original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',backend.HEAD+':src/App.tsx'])
        namespace={};exec(compile((ROOT/'scripts/cp7_ab_master_navigation.py').read_bytes(),'original_navigation_admission','exec'),namespace)
        self.assertTrue(namespace['admit_master_navigation'](original,namespace['OLD_APP_SHA256'])['unchanged_other_App_bytes'])
        current=(ROOT/'src/App.tsx').read_bytes()
        with self.assertRaisesRegex(ValueError,'UNDECLARED_APP_CHANGE'):
            namespace['admit_master_navigation'](current,namespace['OLD_APP_SHA256'])
        text=original.decode()
        for before,after in [("const ConnectedAccessoryIssuePage = lazy(() => import('./ConnectedAccessoryIssuePage'))","const ConnectedAccessoryWorkspacePage = lazy(() => import('./ConnectedAccessoryWorkspacePage'))"),('<ConnectedAccessoryIssuePage/>','<ConnectedAccessoryWorkspacePage/>')]:
            self.assertEqual(text.count(before),1);text=text.replace(before,after)
        self.assertEqual(text.encode(),current)

class OrchestrationControls(unittest.TestCase):
    def invoke(self,*,failed=None,duplicate=False):
        module=load('component');source={'control':'whole-natural-source'};order=[]
        def cases(prefix,count):return {prefix+str(i):{'status':'PASS'}for i in range(count)}
        def exercise(name,count,native):
            def run(*args):
                order.append(name);report=args[4]if native or name=='S03B'else args[2]
                report.update(status='INCOMPLETE'if failed==name else'PASS',used_guard_refused_before_DDL=True)
                if native:
                    report.update(actual_Native_cases=count,native={'cases':cases(name,count if name!='S03N'else 11)})
                    if name=='S03N':report['reader_native3']={'cases':cases('S03R',3)}
                else:
                    report.update(actual_browser_cases=count,browser={'cases':cases(name,count)})
                    if duplicate and name=='S05B':report['browser']['cases']={'S03N0':{'status':'PASS'},'S05B1':{'status':'PASS'}}
            return run
        proof=dict(current_installation=source,qualified_SKU_parent={'control':1},qualified_S03_parent={'control':2})
        doubles={
            'runtime_note':SimpleNamespace(phase=lambda label:nullcontext()),
            'admission':SimpleNamespace(admitted=lambda:proof),
            'native_s03':SimpleNamespace(exercise=exercise('S03N',14,True)),
            'native_sku':SimpleNamespace(exercise=exercise('SKUN',7,True)),
            'native_s05':SimpleNamespace(component=lambda:(SimpleNamespace(exercise=exercise('S05N',10,True)),{'control':1})),
            's03_component':SimpleNamespace(exercise=exercise('S03B',4,False)),
            's05_browser':SimpleNamespace(exercise=exercise('S05B',2,False))}
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def cursor(self):return nullcontext(object())
        psycopg=ModuleType('psycopg');psycopg.connect=lambda *args:Connection()
        product=ModuleType('cp7_s03_sku_composition');product.composition=SimpleNamespace(sources=lambda:source)
        report={}
        with patch.object(module,'load',side_effect=lambda name,path:doubles[path.stem]),patch.dict(sys.modules,{'psycopg':psycopg,'cp7_s03_sku_composition':product}):
            try:module.exercise(object(),object(),'control','control://no-database',report,{'sources':source})
            except ValueError as error:return report,order,error
        return report,order,None

    def test_native14_precedes_every_other_commit_and_all37_required(self):
        report,order,error=self.invoke();self.assertIsNone(error);self.assertEqual(order,['S03N','SKUN','S05N','S03B','S05B'])
        self.assertEqual(report['business_counts'],{'PASS':37});self.assertEqual(report['retained_SKU27_fresh_case_credit'],0)
        self.assertFalse(report['global_writer_or_permission_or_lock_closure'])

    def test_first_failure_stops_following_components(self):
        for failed in ['S03N','SKUN','S05N','S03B','S05B']:
            with self.subTest(failed=failed):
                report,order,error=self.invoke(failed=failed);self.assertIsInstance(error,ValueError)
                self.assertEqual(order[-1],failed);self.assertEqual(report['status'],'INCOMPLETE')

    def test_duplicate_case_cannot_manufacture37(self):
        report,order,error=self.invoke(duplicate=True);self.assertRegex(str(error),'37_UNIQUE');self.assertEqual(report['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
