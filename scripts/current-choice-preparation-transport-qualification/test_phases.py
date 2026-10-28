"""The probe must use the retained logger's closed phase vocabulary before DB."""
from pathlib import Path
import ast
from contextlib import redirect_stdout
import importlib.util
import io
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('retained_phase_logger',ROOT/'scripts/current-frozen-public-native-qualification/progress.py')
logger=importlib.util.module_from_spec(spec);spec.loader.exec_module(logger)

def declared_calls(text):
    calls=[]
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
        if not isinstance(node.func.value,ast.Name) or (node.func.value.id,node.func.attr)!=('progress','mark'):continue
        assert len(node.args)==1 and isinstance(node.args[0],ast.Constant),'DYNAMIC_PHASE_NOT_DECLARED'
        assert node.args[0].value in logger.PHASES,('UNDECLARED_QUALIFICATION_PHASE',node.args[0].value)
        calls.append(node.args[0].value)
    assert calls,'NO_PHASE_CALLS'
    return calls

class PhaseContract(unittest.TestCase):
    def test_all_probe_phases_are_accepted_by_real_logger(self):
        calls=declared_calls((HERE/'probe.py').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'phases.jsonl';progress=logger.Progress(path)
            with redirect_stdout(io.StringIO()):
                for phase in calls:progress.mark(phase)
            self.assertEqual(len(path.read_text().splitlines()),len(calls))

    def test_actual_failed_predecessor_stays_rejected(self):
        old=subprocess.check_output(['git','-C',str(ROOT),'show',
            'f088123ba44b68b09c88e30df04e19b312b8871d:scripts/current-choice-preparation-transport-qualification/probe.py'],text=True)
        with self.assertRaises(AssertionError):declared_calls(old)

    def test_unknown_and_dynamic_phase_cannot_sneak_through(self):
        for text in ("progress.mark('MADE_UP')","progress.mark(name.upper()+'_STARTED')"):
            with self.subTest(text=text),self.assertRaises(AssertionError):declared_calls(text)

if __name__=='__main__':unittest.main()
