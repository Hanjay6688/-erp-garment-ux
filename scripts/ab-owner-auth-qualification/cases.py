"""Eight retained real GoTrue/PostgREST journeys on the current A/B installer."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

mandor=load('current_mandor_auth4','scripts/ow05-auth4-qualification/cases.py')
supplier=load('current_supplier_auth4','scripts/ow06-auth-qualification/cases.py')
IDS=(*mandor.IDS,*supplier.IDS)
assert len(IDS)==len(set(IDS))==8

def http_cases(http,today):
    result=[*mandor.http_cases(http,today),*supplier.http_cases(http,today)]
    assert tuple(key for key,_ in result)==IDS
    return result
