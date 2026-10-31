"""Canonical actual DE30 prerequisite, retaining every original archive check."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CHANGES=(
    ("MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'",
     "MAIN='CP7_CURRENT_COMPLETE_D1_E_NATIVE30.json'",1),
    ("HERE/'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json'","HERE/'DE30_PARENT_ROOT_ACTUAL_INTAKE.json'",1),
    ("'complete-de-permanent6-parent'","'free-date-de30-parent'",1),
    ("'QUALIFIED_PERMANENT6.zip'","'QUALIFIED_DE30.zip'",1),
    ("'cp6-proof/t3/PERMANENT6_PARENT_ORIGINAL_ADMISSION.json'",
     "'cp6-proof/t3/DE30_PARENT_ORIGINAL_ADMISSION.json'",1),
    ("receipt['qualified_complete_sources']","receipt['qualified_complete_DE_sources']",1),
    ('entire_qualified_complete_sources=','entire_qualified_complete_DE_sources=',1),
)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def derive():
    parent=load('free_date_exact_DE_canonical_fetch_derivation',
        ROOT/'scripts/current-complete-de-integration-preparation/fetch_parent.py')
    text,proof=parent.derive();original=text
    labels=[]
    for value in parent.LABELS:
        before=value.replace('PERMANENT_S05_','COMPLETE_DE_').replace(
            'PERMANENT_JOIN37_','COMPLETE_DE_PERMANENT6_').replace('JOIN37','PERMANENT6')
        after=before.replace('COMPLETE_DE_','FREE_DATE_').replace('PERMANENT6','DE30')
        labels.append((repr(before),repr(after),1))
    changes=CHANGES+tuple(labels)
    for before,after,count in changes:
        if text.count(before)!=count or after in text:
            raise ValueError('FREE_DATE_EXACT_CANONICAL_FETCH_ROUTE_REQUIRED:'+before)
        text=text.replace(before,after,count)
    restored=text
    for before,after,count in reversed(changes):
        if restored.count(after)!=count:raise ValueError('FREE_DATE_EXACT_CANONICAL_FETCH_REVERSE_REQUIRED')
        restored=restored.replace(after,before,count)
    if restored!=original:raise ValueError('FREE_DATE_ORIGINAL_DE_CANONICAL_FETCHER_NOT_RECOVERED')
    compile(text,str(HERE/'derived_DE30_fetcher.py'),'exec')
    return text,dict(parent_derivation=proof,parent_derived_sha256=sha256(original.encode()).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),additional_counted_routes=len(changes),
        complete_original_fetcher_recovered=True,actual_GitHub_GETs=0,actual_Native_cases=0)


def main():
    load('free_date_actual_DE_parent_before_any_GET',HERE/'admission.py').parent_receipt()
    text,_=derive();module=ModuleType('free_date_canonical_actual_DE30_fetcher')
    module.__file__=str(HERE/'derived_DE30_fetcher.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__);module.main()


if __name__=='__main__':main()
