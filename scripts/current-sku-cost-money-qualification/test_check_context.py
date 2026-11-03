"""Exercise the original refusing guard without importing its database runtime."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('money_cli_check_under_test',HERE/'check.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
original=HERE.parents[1]/'scripts/ow04-payment-used-restore-qualification/probe.py'
guard=next(node for node in ast.parse(original.read_text()).body
           if isinstance(node,ast.If)and ast.unparse(node.test)=='sys.argv[1:]')
code=compile(ast.Module(body=[guard],type_ignores=[]),str(original),'exec')

class RetainedArguments(unittest.TestCase):
    def test_actual_retained_guard_and_caller_identity(self):
        previous=sys.argv;caller=['check.py','--complete'];sys.argv=caller
        try:
            with self.assertRaisesRegex(SystemExit,'Current used-state restore accepts no arguments'):
                exec(code,dict(sys=sys))
            with check.retained_arguments():
                exec(code,dict(sys=sys))
                sys.argv.append('--retained-module-mutation')
            self.assertIs(sys.argv,caller)
            self.assertEqual(caller,['check.py','--complete'])
        finally:sys.argv=previous

    def test_exception_restores_caller_identity(self):
        previous=sys.argv;caller=['check.py','--source'];sys.argv=caller
        try:
            with self.assertRaisesRegex(RuntimeError,'source failure'):
                with check.retained_arguments():
                    exec(code,dict(sys=sys))
                    raise RuntimeError('source failure')
            self.assertIs(sys.argv,caller)
            self.assertEqual(caller,['check.py','--source'])
        finally:sys.argv=previous

if __name__=='__main__':unittest.main()
