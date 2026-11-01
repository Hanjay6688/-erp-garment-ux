"""New workflow ownership/activation controls. No ERP or Actions dispatch."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest,yaml
from . import workflow

class WorkflowPreparationControls(unittest.TestCase):
    def test_all_setup_restore_and_artifact_steps_keep_original_order_budget_and_ownership(self):
        text,proof=workflow.derive();value=yaml.safe_load(text)
        prior,_=workflow.load('afui_control_original_FREE3_workflow',
            workflow.ROOT/'scripts/current-de-free-date-preparation/workflow.py').derive()
        original=yaml.safe_load(prior);job=value['jobs']['p21'];steps=job['steps']
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
        self.assertIn('runtime_supervisor.py',steps[69]['run']);self.assertIn('final_gate.py',steps[69]['run'])
        self.assertIn('--allow-database-stop',steps[73]['run'])
        self.assertEqual(proof['runtime_dispatches'],0)

    def test_template_does_not_authorize_active_workflow_without_actual_accepted_parent(self):
        with TemporaryDirectory(prefix='afui-workflow-activation-control-')as directory:
            active=Path(directory)/workflow.WORKFLOW;active.parent.mkdir(parents=True)
            active.write_text('not an admitted executable workflow\n')
            with patch.object(workflow,'ROOT',Path(directory)):
                # Derive reads its exact original via the real source location.
                with patch.object(workflow,'derive',return_value=((workflow.HERE/workflow.TEMPLATE).read_text(),{})):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):workflow.source_control()

if __name__=='__main__':unittest.main()
