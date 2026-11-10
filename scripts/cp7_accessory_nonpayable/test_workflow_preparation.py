"""New workflow ownership/activation controls. No ERP or Actions dispatch."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest,yaml
from . import workflow,admission

class WorkflowPreparationControls(unittest.TestCase):
    def workflow_source_fixture(self,directory):
        root=Path(directory);here=root/'scripts/cp7_accessory_nonpayable';here.mkdir(parents=True)
        data=b'qualification template bytes\n';(here/workflow.TEMPLATE).write_bytes(data)
        active=root/workflow.WORKFLOW;active.parent.mkdir(parents=True)
        manifest=dict(base_head='control-parent-head',base_tree='control-parent-tree',
            files={workflow.WORKFLOW:admission.pin(data)})
        return root,here,active,data,manifest

    def test_unarmed_source_workflow_never_reads_parent(self):
        with TemporaryDirectory()as directory:
            root,here,active,data,manifest=self.workflow_source_fixture(directory)
            with patch.object(workflow,'ROOT',root),patch.object(workflow,'HERE',here), \
                 patch.object(admission,'parent_receipt')as parent:
                self.assertIsNone(workflow.admit_source({'files':{}}));parent.assert_not_called()

    def test_missing_and_stray_workflow_refuse_before_parent(self):
        with TemporaryDirectory()as directory:
            root,here,active,data,manifest=self.workflow_source_fixture(directory)
            with patch.object(workflow,'ROOT',root),patch.object(workflow,'HERE',here), \
                 patch.object(admission,'parent_receipt')as parent:
                active.write_bytes(data)
                with self.assertRaisesRegex(ValueError,'UNDECLARED_WORKFLOW_REFUSED'):
                    workflow.admit_source({'files':{}})
                active.unlink()
                with self.assertRaisesRegex(ValueError,'DECLARED_WORKFLOW_MISSING'):
                    workflow.admit_source(manifest)
                parent.assert_not_called()

    def test_exact_source_workflow_requires_actual_matching_parent(self):
        with TemporaryDirectory()as directory:
            root,here,active,data,manifest=self.workflow_source_fixture(directory);active.write_bytes(data)
            with patch.object(workflow,'ROOT',root),patch.object(workflow,'HERE',here), \
                 patch.object(admission,'parent_receipt')as parent:
                parent.side_effect=ValueError('NONPAYABLE_ACTUAL_FREE3_ROOT_INTAKE_PENDING')
                with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                    workflow.admit_source(manifest)
                parent.side_effect=None
                for field in('head','tree'):
                    receipt={'head':manifest['base_head'],'tree':manifest['base_tree']};receipt[field]='wrong-parent'
                    parent.return_value=receipt
                    with self.assertRaisesRegex(ValueError,'EXACT_SOURCE_BASE_QUALIFICATION'):
                        workflow.admit_source(manifest)
                parent.return_value={'head':manifest['base_head'],'tree':manifest['base_tree']}
                self.assertEqual(workflow.admit_source(manifest)['actual_ERP_cases'],0)
                parent.reset_mock();bad=dict(manifest,files={workflow.WORKFLOW:dict(bytes=len(data),sha256='0'*64)})
                with self.assertRaisesRegex(ValueError,'EXACT_WORKFLOW_SOURCE_PIN_REQUIRED'):
                    workflow.admit_source(bad)
                (here/workflow.TEMPLATE).write_bytes(b'changed template')
                with self.assertRaisesRegex(ValueError,'MUST_EQUAL_REVIEWED_TEMPLATE'):
                    workflow.admit_source(manifest)
                parent.assert_not_called()

    def test_all_setup_restore_and_artifact_steps_keep_original_order_budget_and_ownership(self):
        text,proof=workflow.derive();value=yaml.safe_load(text)
        prior,_=workflow.load('afui_control_original_FREE3_workflow',
            workflow.ROOT/'scripts/current-de-free-date-preparation/workflow.py').derive()
        original=yaml.safe_load(prior);job=value['jobs']['p21'];all_steps=job['steps']
        self.assertEqual(len(all_steps),80)
        self.assertEqual(value['on']['push']['branches'],[workflow.BRANCH,workflow.PREPARATION_BRANCH])
        self.assertEqual(job['if'],"github.ref == 'refs/heads/"+workflow.BRANCH+"'")
        preparation=value['jobs']['browser_prerequisites_only']
        self.assertEqual(preparation['if'],"github.ref == 'refs/heads/"+workflow.PREPARATION_BRANCH+"'")
        self.assertEqual(preparation['timeout-minutes'],25)
        self.assertEqual(preparation['steps'][3:5],all_steps[65:67])
        self.assertIn('npm ci --include=dev',all_steps[65]['run'])
        self.assertIn('auditor writer',all_steps[65]['run'])
        self.assertIn('playwright install --with-deps chromium',all_steps[65]['run'])
        self.assertIn('browser_prerequisites.mjs',all_steps[66]['run'])
        retained78=[s for i,s in enumerate(all_steps)if i not in(65,66)]
        self.assertEqual(len(retained78),78)
        steps=[s for i,s in enumerate(retained78)if i not in workflow.ADDED]
        self.assertEqual([i for i in range(75)if steps[i]!=original['jobs']['p21']['steps'][i]],list(workflow.ROUTED))
        self.assertEqual(job['timeout-minutes'],360)
        self.assertIn('AFUI_JOB_START_MONOTONIC',steps[0]['run'])
        self.assertNotIn('FREE_DATE_JOB_START_MONOTONIC',text)
        self.assertEqual(steps[2]['run'],original['jobs']['p21']['steps'][2]['run'])
        self.assertFalse(value['concurrency']['cancel-in-progress'])
        self.assertEqual(value['permissions'],original['permissions'])
        self.assertEqual(set(value['on']),set(original['on']))
        self.assertEqual(value['on']['workflow_dispatch'],original['on']['workflow_dispatch'])
        from . import ui_derivation
        self.assertEqual(set(value['on']['push']['paths']),
            {workflow.WORKFLOW,workflow.NS+'**'}|ui_derivation.CHANGED|ui_derivation.ADDED)
        self.assertEqual(steps[69]['uses'],'./auditor/'+workflow.NS)
        self.assertEqual(steps[69]['with'],{'mode':'runtime'})
        self.assertEqual(retained78[65]['with']['ref'],workflow.UPLOADER)
        self.assertFalse(retained78[65]['with']['persist-credentials'])
        self.assertEqual(retained78[66]['with'],{'mode':'preflight'})
        self.assertEqual(retained78[67],original['jobs']['p21']['steps'][65])
        self.assertIn('final_gate.py',retained78[72]['run'])
        self.assertIn('--allow-database-stop',steps[73]['run'])
        self.assertEqual(proof['runtime_dispatches'],0)

    def test_template_does_not_authorize_active_workflow_without_actual_accepted_parent(self):
        with TemporaryDirectory(prefix='afui-workflow-activation-control-')as directory:
            active=Path(directory)/workflow.WORKFLOW;active.parent.mkdir(parents=True)
            active.write_text('not an admitted executable workflow\n')
            with patch.object(workflow,'ROOT',Path(directory)), \
                 patch.multiple(admission,PARENT_HEAD=None,PARENT_TREE=None,PARENT_RUN=None,PARENT_JOB=None,PARENT_RECEIPT=None):
                # Derive reads its exact original via the real source location.
                with patch.object(workflow,'derive',return_value=((workflow.HERE/workflow.TEMPLATE).read_text(),{})):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):workflow.source_control()

if __name__=='__main__':unittest.main()
