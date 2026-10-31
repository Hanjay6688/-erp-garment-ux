"""Exact canonical permanent6 intake, derived from the existing parent fetcher.

The pending parent gate precedes source derivation and every GitHub GET.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGIN='a5944f25a5e3ba1f1f537a18abe923eb753f922f'
PATH='scripts/current-final-s03-sku-s05-preparation/fetch_parent37.py'
BYTES=4756
SHA256='a595f49e9fef9860363bfef19b856efa183896af049470627108241ad45ae6dd'
CHANGES=(
    ("MAIN='CP7_CURRENT_S03_SKU_S05_NATIVE31_BROWSER6.json'","MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'",1),
    ("HERE/'persistent_financial.py'","HERE/'admission.py'",1),
    ("HERE/'JOIN37_ROOT_ACTUAL_INTAKE.json'","HERE/'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json'",1),
    ("receipt=required.qualified_receipt(root_path.read_bytes())","receipt=required.parent_receipt()",1),
    ("'permanent-join37-parent'","'complete-de-permanent6-parent'",1),
    ("'QUALIFIED_JOIN37.zip'","'QUALIFIED_PERMANENT6.zip'",1),
    ("'cp6-proof/t3/JOIN37_PARENT_ORIGINAL_ADMISSION.json'","'cp6-proof/t3/PERMANENT6_PARENT_ORIGINAL_ADMISSION.json'",1),
    ("receipt['qualified_financial_sources']","receipt['qualified_complete_sources']",1),
    ('entire_qualified_financial_sources=','entire_qualified_complete_sources=',1),
)
LABELS=(
    'PERMANENT_S05_EXACT_TERMINAL_JOIN37_INTAKE_PENDING',
    'PERMANENT_S05_TERMINAL_EXACT_JOIN37_RUN_REQUIRED',
    'PERMANENT_S05_EXACT_SUCCESSFUL_JOIN37_JOB_REQUIRED',
    'PERMANENT_S05_CANONICAL_JOIN37_API_ARTIFACT_CHANGED',
    'PERMANENT_S05_EXISTING_CANONICAL_ARCHIVE_CHANGED',
    'PERMANENT_S05_CANONICAL_JOIN37_MAIN_ORIGINAL_CHANGED',
    'PERMANENT_S05_CANONICAL_JOIN37_ARCHIVE_BYTES_CHANGED',
    'PERMANENT_S05_CANONICAL_JOIN37_CRC_OR_MEMBERS_CHANGED',
    'PERMANENT_S05_CANONICAL_ARCHIVE_PATH_ESCAPE',
    'EXACT_TERMINAL_JOIN37_CANONICAL_ORIGINALS_ADMITTED',
    'PERMANENT_JOIN37_ROOT_INTAKE=',
    'PERMANENT_JOIN37_CANONICAL_ARCHIVE=',
    'PERMANENT_JOIN37_MAIN=',
)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def derive():
    raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGIN+':'+PATH],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'))
    if len(raw)!=BYTES or sha256(raw).hexdigest()!=SHA256:
        raise ValueError('COMPLETE_DE_EXACT_CANONICAL_PARENT_FETCHER_SOURCE_REQUIRED')
    text=raw.decode()
    labels=tuple((repr(value),repr(value.replace('PERMANENT_S05_','COMPLETE_DE_')
        .replace('PERMANENT_JOIN37_','COMPLETE_DE_PERMANENT6_').replace('JOIN37','PERMANENT6')),1)
        for value in LABELS)
    changes=CHANGES+labels
    for before,after,count in changes:
        if text.count(before)!=count or after in text:
            raise ValueError('COMPLETE_DE_EXACT_PARENT_FETCH_DERIVATION_ANCHOR:'+before)
        text=text.replace(before,after,count)
    reverse=text
    for before,after,count in reversed(changes):
        if reverse.count(after)!=count:
            raise ValueError('COMPLETE_DE_EXACT_PARENT_FETCH_REVERSE_ANCHOR:'+after)
        reverse=reverse.replace(after,before,count)
    if reverse.encode()!=raw:raise ValueError('COMPLETE_DE_ORIGINAL_PARENT_FETCH_BYTES_REQUIRED')
    compile(text,str(HERE/'derived_permanent6_fetcher.py'),'exec')
    return text,dict(original_head=ORIGIN,original_path=PATH,original_bytes=BYTES,original_sha256=SHA256,
        derived_sha256=sha256(text.encode()).hexdigest(),counted_replacement_rules=len(changes),
        original_source_recovered=True,actual_GitHub_GETs=0,actual_Native_cases=0)


def main():
    load('complete_DE_actual_permanent_parent_before_fetch',HERE/'admission.py').parent_receipt()
    text,_=derive();module=ModuleType('complete_DE_canonical_permanent6_fetcher')
    module.__file__=str(HERE/'derived_permanent6_fetcher.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__);module.main()


if __name__=='__main__':main()
