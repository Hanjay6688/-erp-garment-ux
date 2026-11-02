"""Exact canonical FREE3 archive fetch; closed parent precedes every GET."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CHANGES=(
    ("MAIN='CP7_CURRENT_COMPLETE_D1_E_NATIVE30.json'","MAIN='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3.json'",1),
    ("HERE/'DE30_PARENT_ROOT_ACTUAL_INTAKE.json'","HERE/'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json'",1),
    ("'free-date-de30-parent'","'afui-free3-parent'",1),
    ("'QUALIFIED_DE30.zip'","'QUALIFIED_FREE3.zip'",1),
    ("'cp6-proof/t3/DE30_PARENT_ORIGINAL_ADMISSION.json'","'cp6-proof/t3/FREE3_PARENT_ORIGINAL_ADMISSION.json'",1),
    ("receipt['qualified_complete_DE_sources']","receipt['qualified_complete_DE_FREE_date_sources']",1),
    ('entire_qualified_complete_DE_sources=','entire_qualified_complete_DE_FREE_date_sources=',1),
)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def derive():
    free=load('afui_exact_FREE3_canonical_fetch_derivation',ROOT/'scripts/current-de-free-date-preparation/fetch_parent.py')
    parent=load('afui_exact_original_canonical_fetch_labels',ROOT/'scripts/current-complete-de-integration-preparation/fetch_parent.py')
    text,prior=free.derive();original=text;labels=[]
    for value in parent.LABELS:
        before=value.replace('PERMANENT_S05_','COMPLETE_DE_').replace('PERMANENT_JOIN37_','COMPLETE_DE_PERMANENT6_').replace('JOIN37','PERMANENT6')
        before=before.replace('COMPLETE_DE_','FREE_DATE_').replace('PERMANENT6','DE30')
        after=before.replace('FREE_DATE_','NONPAYABLE_').replace('DE30','FREE3')
        labels.append((repr(before),repr(after),1))
    changes=CHANGES+tuple(labels)
    for before,after,count in changes:
        if text.count(before)!=count or after in text:raise ValueError('NONPAYABLE_EXACT_CANONICAL_PARENT_FETCH_ROUTE_REQUIRED:'+before)
        text=text.replace(before,after,count)
    restored=text
    for before,after,count in reversed(changes):
        if restored.count(after)!=count:raise ValueError('NONPAYABLE_EXACT_CANONICAL_FETCH_REVERSE_REQUIRED')
        restored=restored.replace(after,before,count)
    if restored!=original:raise ValueError('NONPAYABLE_ORIGINAL_FULL_CANONICAL_FETCHER_NOT_RECOVERED')
    compile(text,str(HERE/'derived_FREE3_fetcher.py'),'exec')
    return text,dict(parent_derivation=prior,parent_derived_sha256=sha256(original.encode()).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),additional_counted_routes=len(changes),
        original_full_fetcher_recovered=True,terminal_run_job_head_artifact_bytes_SHA_ZIP_CRC_paths_and_all5_checks_unchanged=True,
        actual_GitHub_GETs=0,actual_ERP_cases=0)

def main():
    from cp7_accessory_nonpayable import admission
    admission.parent_receipt()
    text,_=derive();module=ModuleType('afui_exact_canonical_actual_FREE3_fetcher')
    module.__file__=str(HERE/'derived_FREE3_fetcher.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__);module.main()

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'));main()
