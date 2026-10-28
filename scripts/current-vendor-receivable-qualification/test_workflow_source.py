"""Guard the actual no-job CI typo locally; no ERP acceptance claim."""
from pathlib import Path
import copy,unittest,yaml
from workflow_source import checked

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'.github/workflows/cp7-current-vendor-receivable-native.yml'


class Workflow(unittest.TestCase):
    def test_actual_current_step_keys(self):checked(PATH.read_text())

    def test_first_failure_typo_rejected(self):
        workflow=yaml.safe_load(PATH.read_text())
        step=next(s for s in workflow['jobs']['p21']['steps']if s.get('name','').startswith('Bind complete actual observer'))
        step['working_directory']=step.pop('working-directory')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_STEP_KEY.*working_directory'):checked(yaml.safe_dump(workflow))


if __name__=='__main__':unittest.main()
