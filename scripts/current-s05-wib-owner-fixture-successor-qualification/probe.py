"""Exact complete S05/vendor engine; only two scoped private fixture dependencies."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'scripts/current-s05-current-ac-editor-qualification'


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def runtime():
    load('s05_wib_owner_before_product_full_source',HERE/'admission.py').offline()
    raw=(OLD/'probe.py').read_bytes()
    text,derivation=load('s05_wib_owner_counted_probe_bridge',HERE/'derive.py').probe(raw)
    m=ModuleType('s05_wib_owner_private_current_AC_complete_probe');m.__file__=str(OLD/'probe.py')
    m.__S05_WIB_OWNER_HERE__=HERE
    exec(compile(text,str(OLD/'probe.py'),'exec'),m.__dict__)
    engine=m.runtime()
    engine.PRE_DUMP='/tmp/s05_wib_owner_native10_pre.dump'
    previous=engine.admitted
    def admitted():
        proof=previous()
        if engine.product.sources()!=proof['current_installation']:
            raise ValueError('S05_WIB_OWNER_NATURAL_ACTUAL_PARENT_SOURCE_GRAPH_REQUIRED')
        return dict(proof,wib_owner_fixture_source=load('s05_wib_owner_full_runtime_source',HERE/'admission.py').offline(),
            current_AC_complete_probe_derivation=derivation,
            failed52eed_is_success_prerequisite=False,partial8_plus2_aggregation=False)
    engine.admitted=admitted
    return engine


def check():
    boundary=load('s05_wib_owner_exact_import_argv',ROOT/'scripts/current-s05-native10-qualification/import_argv.py')
    with boundary.source_import_arguments():return runtime().admitted()


def execute():
    if os.environ.get('S05_NATIVE_CONFIRM')!='cp6_rollback':
        raise ValueError('S05_EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED')
    engine=runtime();engine.admitted()
    engine.package._writer_runtime=lambda browser_mode=False:engine.run()
    engine.package.run('install')


if __name__=='__main__':
    if sys.argv[1:]==['--check']:print(json.dumps(check(),indent=2,default=str))
    elif not sys.argv[1:]:execute()
    else:raise SystemExit('Use --check for source-only admission; only root executes disposable Native qualification.')
