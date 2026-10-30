"""Same declared producer/output controls in the NEW workflow context only."""
from pathlib import Path
from types import ModuleType
from unittest import TestCase,main
from unittest.mock import patch
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


# The original fifteen tests execute unchanged against the new exact contract.
# This one metadata binding affects only this isolated local test module.
path=PARENT/'test_generated_later.py';raw=path.read_text()
before='HERE=Path(__file__).resolve().parent';after='HERE=CURRENT_HERE'
assert raw.count(before)==1
module=ModuleType('s03_lawful_private_unchanged_later_output_tests')
module.__file__=str(path);module.CURRENT_HERE=HERE
# Its actual validator remains the frozen original, not a local reimplementation.
value=raw.replace(before,after,1).replace("HERE/'generated_later.py'","PARENT_VALIDATOR",1)
module.PARENT_VALIDATOR=PARENT/'generated_later.py'
exec(compile(value,str(path),'exec'),module.__dict__)
CurrentLater=module.Later


class ActualProducer(TestCase):
    def test_actual_identity_producer_newWF_currentHEAD_and_repeat_package_admission_after_clone(self):
        fixture=CurrentLater('test_all_exact_output_classes_admit_in_progress_package_without_claiming_final_pass')
        fixture.setUp()
        try:
            producer=load('s03_lawful_actual_unmodified_run_identity',ROOT/'scripts/cp6_run_identity.py')
            flow=load('s03_lawful_actual_new_workflow_name',HERE/'workflow.py')
            head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
            with patch.dict(os.environ,dict(GITHUB_WORKFLOW=flow.NAME,GITHUB_SHA=head,GITHUB_RUN_ID='40967080539',
                GITHUB_RUN_ATTEMPT='1',GITHUB_JOB='p21',GITHUB_EVENT_NAME='workflow_dispatch')):
                identity=producer.identity('T3_PREP',mode='install')
            for key,value in fixture.contract['package_run_identity_static'].items():self.assertEqual(identity[key],value)
            fixture.alter('T3_PACKAGE_INSTALL.json',lambda d:d.update(run_identity=identity))
            with patch.object(module.g,'_head',lambda root:head):
                first=module.g.admit(fixture.root,fixture.here,fixture.names)
                second=module.g.admit(fixture.root,fixture.here,fixture.names)
            self.assertEqual(first,second);self.assertEqual(first[1]['classes']['clone'],5)
            self.assertEqual(first[1]['classes']['package'],2);self.assertEqual(first[1]['actual_Native_credit'],0)
            self.assertEqual(identity['workflow'],flow.NAME)
        finally:fixture.doCleanups()


if __name__=='__main__':main(verbosity=2)
