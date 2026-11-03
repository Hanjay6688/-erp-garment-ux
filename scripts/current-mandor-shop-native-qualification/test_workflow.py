"""New owning workflow ordering, actual output names and shell syntax only."""
from pathlib import Path
import ast,subprocess,unittest
import yaml
import workflow,fetch_parent


class WorkflowControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text,cls.proof=workflow.derive();cls.value=yaml.safe_load(cls.text)
        cls.job=cls.value['jobs']['p21'];cls.steps=cls.job['steps']

    def index(self,needle):
        matches=[i for i,s in enumerate(self.steps)if needle in s.get('run','')]
        self.assertEqual(len(matches),1,needle);return matches[0]

    def test_all_prerequisites_precede_database_and_only_one_runtime_is_present(self):
        db=next(i for i,s in enumerate(self.steps)if s.get('name')=='Start disposable database')
        for command in ['materialize_parent.py','fetch_parent.py','parent_artifacts.py --prepare','qualification.py --check']:
            # Several inherited canonical fetchers have the same basename; bind
            # the exact new namespace when checking the Afui15 prerequisite.
            marker=workflow.NS+command
            self.assertLess(self.index(marker),db)
        self.assertLess(self.index(workflow.NS+'parent_artifacts.py --prepare'),self.index(workflow.NS+'qualification.py --check'))
        runtime=[s for s in self.steps if "runtime_supervisor.py'"in s.get('run','')and'--allow-database-stop'not in s.get('run','')]
        self.assertEqual(len(runtime),1);self.assertIn(workflow.NS+'final_gate.py',runtime[0]['run'])
        self.assertEqual(len(self.steps),79)

    def test_failure_retention_precedes_guarded_database_stop_and_upload(self):
        retained=self.index(workflow.NS+'parent_artifacts.py --retain');stop=self.index('--allow-database-stop')
        self.assertLess(retained,stop);self.assertEqual(self.steps[retained]['if'],'always()')
        self.assertEqual(self.steps[stop]['if'],'always()')
        self.assertEqual(self.steps[-1]['if'],'always()');self.assertEqual(self.steps[-1]['with']['path'],'auditor/cp6-proof/t3')

    def test_recorded_filenames_match_actual_component_gate_and_parent_fetch(self):
        receipt=next(s['run']for s in self.steps if s.get('name','').startswith('Preserve exact original JSON'))
        component=ast.parse((workflow.HERE/'component.py').read_bytes());env={}
        for n in component.body:
            if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('LABEL','NATIVE_LABEL')for t in n.targets):
                exec(compile(ast.Module(body=[n],type_ignores=[]),'inert_component_labels','exec'),env)
        for name in(env['LABEL']+'.json',env['NATIVE_LABEL']+'.json',env['NATIVE_LABEL']+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
            self.assertIn(repr(name),receipt)
        gate=ast.parse((workflow.HERE/'final_gate.py').read_bytes())
        outputs=[n.value for n in ast.walk(gate)if isinstance(n,ast.Constant)and type(n.value)is str
            and n.value.startswith('cp6-proof/t3/')and n.value.endswith('.json')]
        self.assertEqual(len(outputs),1);self.assertIn(repr(Path(outputs[0]).name),receipt)
        parent=ast.parse(fetch_parent.derive()[0])
        outputs=[n.value for n in ast.walk(parent)if isinstance(n,ast.Constant)and type(n.value)is str
            and n.value.startswith('cp6-proof/t3/')and n.value.endswith('.json')]
        self.assertEqual(len(outputs),1);self.assertIn(repr(Path(outputs[0]).name),receipt)

    def test_new_owning_commands_parse_and_keep_single_branch_and_budget(self):
        self.assertEqual(self.job['if'],"github.ref == 'refs/heads/"+workflow.BRANCH+"'")
        self.assertEqual(self.value['on']['push']['branches'],[workflow.BRANCH])
        self.assertFalse(self.value['concurrency']['cancel-in-progress']);self.assertEqual(self.job['timeout-minutes'],360)
        self.assertEqual(self.value['permissions'],{'contents':'read','actions':'read'})
        checked=0
        for step in self.steps:
            command=step.get('run','')
            if workflow.NS in command or 'MANDOR_NATIVE_JOB_START_MONOTONIC'in command:
                subprocess.run(['bash','-n'],input=command,text=True,check=True,capture_output=True);checked+=1
        self.assertEqual(checked,9)
        self.assertFalse((workflow.ROOT/workflow.WORKFLOW).exists())


if __name__=='__main__':unittest.main()
