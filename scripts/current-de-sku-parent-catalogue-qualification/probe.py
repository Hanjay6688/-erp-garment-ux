"""Admit source before imports; retain complete disposable package lifecycle."""
from pathlib import Path
from types import ModuleType
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def runtime():
    admission=load('de_sku_preimport_source',HERE/'admission.py');admission.preflight()
    sys.path.insert(0,str(ROOT/'scripts'))
    transition=load('de_sku_retained_argv_scope',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/transition.py')
    with transition.scoped_argv():
        deriver=load('de_sku_whole_engine_deriver',HERE/'derive.py');text,proof=deriver.derive()
        m=ModuleType('de_sku_whole_disposable_engine');m.__file__=str(ROOT/deriver.OLD)
        exec(compile(text,m.__file__,'exec'),m.__dict__);m.CATALOGUE_ENGINE_DERIVATION=proof
        original=m.admitted
        def admitted():
            with transition.scoped_argv():return original()
        m.admitted=admitted
    return m


def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--runtime',action='store_true');args=parser.parse_args()
    if args.check:
        ctx=load('de_sku_no_database_source_context',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with ctx.fenced_source_read()as guard:
            m=runtime();proof=m.admitted()
        print(json.dumps(dict(status='EXACT_SOURCE_ONLY_NO_DATABASE',proof=proof,guard=guard),default=str));return
    m=runtime();transition=load('de_sku_execute_argv_scope',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/transition.py')
    with transition.scoped_argv():
        m.admitted();m.package._writer_runtime=lambda browser_mode=False:m.run();m.package.run('install')


if __name__=='__main__':main()
