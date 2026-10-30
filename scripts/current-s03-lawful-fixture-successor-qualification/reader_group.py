"""Unchanged Reader3 group with one explicit lawful P2 helper binding."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def parent():
    helper=load('s03_lawful_counted_reader_binding',HERE/'derive.py')
    return helper.module('s03_lawful_same_fresh_Reader3_runner',PARENT/'reader_group.py',
        [(helper.READER_BEFORE,helper.READER_AFTER)],
        CURRENT_BUSINESS=load('s03_lawful_reader_explicit_API',HERE/'business.py'))


def exact_group(group,ids):
    # Structural group gate never imports business fixtures or connects.
    return load('s03_lawful_frozen_exact_group_gate',PARENT/'reader_group.py').exact_group(group,ids)


def run(native,control,state,report,verify,original11):
    value,proof=parent()
    report['lawful_reader3_private_binding']=proof
    return value.run(native,control,state,report,verify,original11)
