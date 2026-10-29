"""Actual own CLI parsers + exact inherited argv guard; no product/DB import.

The engine body/admission are explicit import doubles. Their only operation is
executing the retained old no-argument guard and observing sys.argv. The own
check/probe parsers and probe.runtime/check code execute unchanged otherwise.
"""
from contextlib import contextmanager, redirect_stdout
from importlib.abc import Loader
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import io
import json
import os
import runpy
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


boundary=load('s05_unit_import_argv',HERE/'import_argv.py')
old_guard_path=ROOT/'scripts/ow04-payment-used-restore-qualification/probe.py'
old_guard_tree=ast.parse(old_guard_path.read_text())
old_guard=next(n for n in old_guard_tree.body if isinstance(n,ast.If)
    and 'Current used-state restore accepts no arguments' in ast.get_source_segment(old_guard_path.read_text(),n))
old_guard_code=compile(ast.Module(body=[old_guard],type_ignores=[]),str(old_guard_path),'exec')


class FakeLoader(Loader):
    def __init__(self,configure):self.configure=configure
    def create_module(self,spec):return None
    def exec_module(self,module):self.configure(module)


@contextmanager
def source_import_doubles(*,lazy_error=None):
    """No Native runtime is imported; only the exact old argv guard executes."""
    calls=[]
    def guard(phase):
        calls.append((phase,list(sys.argv)))
        exec(old_guard_code,{'sys':sys})
    guard_module=ModuleType('s05_test_exact_old_noarg_guard')
    guard_module.guard=guard
    actual_spec=importlib.util.spec_from_file_location
    def spec(name,path,*args,**kwargs):
        if name=='s05_exact_engine_derivation':
            assert Path(path)==HERE/'derive.py'
            def configure(module):
                module.derive=lambda _raw:(
                    "import s05_test_exact_old_noarg_guard as local\nlocal.guard('engine_import')\nproduct=object()\n",
                    {'LOCAL_IMPORT_DOUBLE_ONLY':True})
            return importlib.util.spec_from_loader(name,FakeLoader(configure),origin=str(path))
        if name=='s05_actual_source_admission':
            assert Path(path)==HERE/'admission.py'
            def configure(module):
                def admitted(*_args):
                    guard('lazy_admission')
                    if lazy_error is not None:raise lazy_error
                    return dict(status='LOCAL_IMPORT_ARGV_DOUBLE_ONLY',prerequisite={'fresh_S05_runtime_credit':0})
                module.admitted=admitted
            return importlib.util.spec_from_loader(name,FakeLoader(configure),origin=str(path))
        return actual_spec(name,path,*args,**kwargs)
    # Test-only dependencies. No old or product module/global is patched.
    with patch.dict(sys.modules,{'s05_test_exact_old_noarg_guard':guard_module}), \
         patch.object(importlib.util,'spec_from_file_location',side_effect=spec), \
         patch.object(sys,'path',list(sys.path)),patch.dict(os.environ,{},clear=False):
        yield calls


def cli(path,args):
    original=sys.argv
    caller=['s05-caller',*args]
    expected=list(caller)
    stream=io.StringIO()
    try:
        sys.argv=caller
        with redirect_stdout(stream):runpy.run_path(str(path),run_name='__main__')
        return json.loads(stream.getvalue())
    finally:
        # The real runpy argv[0] context and our inner context must both restore.
        assert sys.argv is caller and caller==expected,'S05_CALLER_ARGV_NOT_EXACTLY_RESTORED'
        sys.argv=original


class ArgumentBoundaryControls(unittest.TestCase):
    def test_original_check_reproduces_exact_retained_terminal_for_both_flags(self):
        old=ModuleType('s05_retained_before_argv_boundary')
        old.__file__=str(HERE/'probe.py')
        exec(compile((HERE/'cli_import/retained/probe.py').read_bytes(),old.__file__,'exec'),old.__dict__)
        def runtime():
            exec(old_guard_code,{'sys':sys})
            self.fail('OLD_GUARD_DID_NOT_REFUSE')
        old.runtime=runtime
        for flag in ('--runtime','--check'):
            caller=['original-s05',flag]
            with patch.object(sys,'argv',caller):
                with self.assertRaisesRegex(SystemExit,'Current used-state restore accepts no arguments'):old.check()
                self.assertIs(sys.argv,caller);self.assertEqual(caller,['original-s05',flag])

    def test_context_preserves_program_and_exact_caller_object_contents(self):
        caller=['outer-program','--runtime','original']
        with patch.object(sys,'argv',caller):
            with boundary.source_import_arguments():
                self.assertIsNot(sys.argv,caller);self.assertEqual(sys.argv,['outer-program'])
                caller.append('foreign-mutation')
                sys.argv=['import-reassigned-list']
            self.assertIs(sys.argv,caller);self.assertEqual(caller,['outer-program','--runtime','original'])

    def test_nested_success_and_every_base_exception_restore(self):
        caller=['outer','--check']
        with patch.object(sys,'argv',caller):
            with boundary.source_import_arguments():
                inner=sys.argv
                with boundary.source_import_arguments():self.assertEqual(sys.argv,['outer'])
                self.assertIs(sys.argv,inner)
            self.assertIs(sys.argv,caller)
        for error in (RuntimeError('runtime'),SystemExit('system-exit'),KeyboardInterrupt('interrupt')):
            with patch.object(sys,'argv',caller):
                with self.assertRaises(type(error)):
                    with boundary.source_import_arguments():raise error
                self.assertIs(sys.argv,caller);self.assertEqual(caller,['outer','--check'])

    def test_actual_check_runtime_parser_sanitizes_engine_and_lazy_admission(self):
        with source_import_doubles()as calls:
            value=cli(HERE/'check.py',['--runtime'])
        self.assertEqual(value['status'],'PASS_SOURCE_ONLY')
        self.assertTrue(value['runtime_import_source_check']);self.assertEqual(value['Native_executions'],0)
        self.assertEqual([p for p,_ in calls],['engine_import','lazy_admission'])
        self.assertTrue(all(argv==[str(HERE/'check.py')]for _,argv in calls),calls)

    def test_actual_probe_check_parser_sanitizes_engine_and_lazy_admission(self):
        with source_import_doubles()as calls:
            value=cli(HERE/'probe.py',['--check'])
        self.assertEqual(value['status'],'LOCAL_IMPORT_ARGV_DOUBLE_ONLY')
        self.assertEqual([p for p,_ in calls],['engine_import','lazy_admission'])
        self.assertTrue(all(argv==[str(HERE/'probe.py')]for _,argv in calls),calls)

    def test_actual_parsers_do_not_mask_unknown_flags(self):
        for name,args in (('check.py',['--check']),('check.py',['--runtime','unknown']),
                          ('probe.py',['--runtime']),('probe.py',['--check','unknown'])):
            with source_import_doubles()as calls:
                with self.assertRaises(SystemExit):cli(HERE/name,args)
            self.assertEqual(calls,[])

    def test_actual_both_parsers_restore_on_lazy_import_system_exit(self):
        for name,args in (('check.py',['--runtime']),('probe.py',['--check'])):
            with source_import_doubles(lazy_error=SystemExit('LOCAL_LAZY_IMPORT_FAILURE'))as calls:
                with self.assertRaisesRegex(SystemExit,'LOCAL_LAZY_IMPORT_FAILURE'):cli(HERE/name,args)
            self.assertEqual([p for p,_ in calls],['engine_import','lazy_admission'])

    def test_execute_confirmation_and_original_engine_functions_stay_byte_ast_equal(self):
        old=ast.parse((HERE/'cli_import/retained/probe.py').read_bytes())
        new=ast.parse((HERE/'probe.py').read_bytes())
        for name in ('runtime','execute','load'):
            before=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name)
            after=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name==name)
            self.assertEqual(ast.dump(before),ast.dump(after),name)
        self.assertEqual(ast.dump(old.body[-1]),ast.dump(new.body[-1]),'outer parser')


if __name__=='__main__':unittest.main()
