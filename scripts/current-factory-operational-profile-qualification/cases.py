from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
previous=load('current_profile_unchanged_installed_guard',ROOT/'scripts/current-finance-factory-progress-followup-qualification/cases.py')
profile=load('current_profile_measurements',HERE/'measurements.py')
product=previous.product
installed_operations=previous.installed_operations
def operational(conn,cur,database,url,report):
    previous.verify_existing(conn,cur,report)
    return profile.exercise(conn,cur,database,url,report)
CHILDREN=(('CURRENT_FACTORY_UNIT0_AND_COMPILER_DIAGNOSTIC',operational),)
