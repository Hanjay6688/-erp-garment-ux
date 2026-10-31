"""Source and orchestration controls only: no Native or browser credit."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from contextlib import nullcontext
from hashlib import sha256
from unittest.mock import patch
import ast,importlib.util,json,subprocess,sys,unittest,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location('join_control_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class SourceControls(unittest.TestCase):
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
        for index in record['unchanged_steps']:self.assertIn(old[index],steps)
        start=next(i for i,s in enumerate(steps)if s.get('name')=='Start disposable database')
        for marker in ('fetch_parents.py','test_rpc_transport.mjs','probe.py --check'):
            self.assertTrue(any(marker in s.get('run','')for s in steps[:start]))
        actual=next(s for s in steps if 'probe.py\' --runtime' in s.get('run',''))
        self.assertIn('final_gate.py',actual['run']);self.assertEqual(current['timeout-minutes'],210)
        self.assertEqual(current['env']['JOIN_CONFIRM'],'cp6_rollback')

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
