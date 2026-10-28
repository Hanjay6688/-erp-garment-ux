from pathlib import Path
import importlib.util,ast,unittest,yaml
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('race_guard_successor',HERE/'race.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
source=(ROOT/'scripts/cp6_v2620ah_concurrency.py').read_text();tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run_case');original=ast.get_source_segment(source,node)+'\n'
class Derivation(unittest.TestCase):
 def test_single_guard_literal_only(self):self.assertEqual(r.derive(original).replace(r.NEW,r.OLD),original)
 def test_all_original_assertions_retained(self):self.assertEqual(sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(original))),sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(r.derive(original)))))
 def test_missing_anchor_refused(self):
  with self.assertRaises(AssertionError):r.derive(original.replace(r.OLD,"'wrong'"))
 def test_duplicate_anchor_refused(self):
  with self.assertRaises(AssertionError):r.derive(original+'\n# '+r.OLD)
 def test_already_changed_source_refused(self):
  with self.assertRaises(AssertionError):r.derive(original.replace(r.OLD,r.NEW))
class WorkflowHistory(unittest.TestCase):
 def test_materialization_precedes_source_and_database(self):
  workflow=yaml.safe_load((ROOT/'.github/workflows/cp7-current-cp6-return-race-followup.yml').read_bytes());steps=workflow['jobs']['p21']['steps']
  positions=[i for i,s in enumerate(steps)if s.get('run')=='python scripts/current-workflow-history-isolation/materialize.py']
  self.assertEqual(len(positions),1);index=positions[0];self.assertEqual(steps[index]['working-directory'],'auditor')
  self.assertLess(index,next(i for i,s in enumerate(steps)if s.get('name')=='Admit whole unchanged3194 backend before database'))
  self.assertLess(index,next(i for i,s in enumerate(steps)if s.get('name')=='Start disposable database'))
class SourceConnection(unittest.TestCase):
 def test_source_session_closed_before_copy(self):
  text=(HERE/'runner.py').read_text();self.assertLess(text.index('conn.close()'),text.index('modes.run_races('))
  self.assertIn("result.get('counts')",text)
if __name__=='__main__':unittest.main()
