"""Complete retained package engine, admitted before every runtime import."""
from pathlib import Path
from types import ModuleType
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def runtime():
    load('sku27_preimport_source',HERE/'admission.py').preflight()
    transition=load('sku27_empty_retained_argv',HERE/'transition.py')
    with transition.scoped_argv():
        sys.path.insert(0,str(ROOT/'scripts'))
        import cp7_vendor_receivable.composition as current_vendor
        sys.path.insert(0,str(ROOT/'scripts'))
        from cp7_sku_pair_conversion import composition as current_product
        assert Path(current_vendor.__file__).resolve().is_relative_to(ROOT)
        assert Path(current_product.__file__).resolve().is_relative_to(ROOT)
        d=load('sku27_complete_private_probe',HERE/'derive.py');module=ModuleType('sku27_complete_runtime');module.__file__=str(HERE/'probe.py')
        d.execute('probe',module.__dict__)
        original=module.admitted
        def admitted():
            with transition.scoped_argv():return original()
        module.admitted=module.engine.admitted=admitted
    return module

def main(argv=None):
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--runtime',action='store_true');mode.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    if args.check:
        context=load('sku27_probe_source_DB_guard',HERE/'source_context.py')
        with context.fenced_source_read()as guard:proof=runtime().admitted()
        print(json.dumps(dict(status='SOURCE_ONLY_ACTUAL_ORIGINALS_NO_NATIVE',proof=proof,source_DB_guard=guard,actual_successor_cases=0),sort_keys=True,default=str));return
    attempts=load('sku27_single_attempt_policy',HERE/'attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window()),sort_keys=True))
    module=runtime();transition=load('sku27_execute_argv',HERE/'transition.py')
    with transition.scoped_argv():
        module.admitted();module.engine.package._writer_runtime=lambda browser_mode=False:module.engine.run()
        import cp6_auditor_business_day as business_day
        with attempts.single_attempt(business_day):
            module.engine.package.run('install')

if __name__=='__main__':main()
