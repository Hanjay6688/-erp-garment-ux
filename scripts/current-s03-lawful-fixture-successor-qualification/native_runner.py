"""Same fresh strict11→Reader3→committed ALLOCATE witness; three adapted fixtures."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runtime():
    cfg=json.loads((PARENT/'CONFIG.json').read_bytes())
    load('s03_lawful_native_component_source_gate',HERE/'source_check.py').check(require_bound=True)
    original=ROOT/'scripts/current-attendance-period-choice-native11-qualification/native_runner.py'
    helper=load('s03_lawful_counted_native_binding',HERE/'derive.py')
    value,proof=helper.native(original.read_bytes())
    reader=load('s03_lawful_actual_Reader3_factory',HERE/'reader_group.py')
    module=ModuleType('s03_lawful_same_native14_groups_and_original_used_witness')
    module.__file__=str(original)
    module.CURRENT_READER_IDS=tuple(cfg['reader_Native3_ids'])
    module.CURRENT_BUSINESS=load('s03_lawful_explicit_private_business',HERE/'business.py')
    module.run_actual_reader3=reader.run
    exec(compile(value,str(original),'exec'),module.__dict__)
    actual_exercise=module.exercise
    def exercise(conn,cur,database,url,report,state):
        report['lawful_fixture_successor_derivation']=dict(native_runner=proof,
            business=module.business.PRIVATE_DERIVATION,
            old9ac_partial8PASS_not_prerequisite=True,actual_Native_credit_before_run=0)
        return actual_exercise(conn,cur,database,url,report,state)
    module.exercise=exercise;module.PRIVATE_DERIVATION=proof
    return module
