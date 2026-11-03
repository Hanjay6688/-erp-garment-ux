"""Exact canonical Afui15 prerequisite; closed admission precedes every GET.

Derive the retained archive fetcher by reversible label/binding routes only.
Run, job, attempt, head, archive hash/size, CRC, member paths and main Original
checks retain the original implementation. This module never opens a DB.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CHANGES=(
    ("MAIN='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3.json'","MAIN='CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'"),
    ("HERE/'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json'","HERE/'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'"),
    ('receipt=required.parent_receipt()','receipt=required.parent(root_path.read_bytes())'),
    ('if required.PARENT_RECEIPT is None:','if required.PARENT_ROOT_PIN is None:'),
    ('root_intake=required.PARENT_RECEIPT,','root_intake=required.PARENT_ROOT_PIN,'),
    ("'afui-free3-parent'","'mandor-afui15-parent'"),
    ("'QUALIFIED_FREE3.zip'","'QUALIFIED_AFUI15.zip'"),
    ("'cp6-proof/t3/FREE3_PARENT_ORIGINAL_ADMISSION.json'","'cp6-proof/t3/AFUI15_PARENT_ORIGINAL_ADMISSION.json'"),
    ("receipt['qualified_complete_DE_FREE_date_sources']","receipt['qualified_Afui_good_nonpayable_sources']"),
    ('entire_qualified_complete_DE_FREE_date_sources=','entire_qualified_Afui_good_nonpayable_sources='),
)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def derive():
    old=load('mandor_exact_inherited_Afui_canonical_fetcher',ROOT/'scripts/cp7_accessory_nonpayable/fetch_parent.py')
    text,prior=old.derive();original=text
    labels=load('mandor_exact_original_canonical_fetch_labels',ROOT/'scripts/current-complete-de-integration-preparation/fetch_parent.py').LABELS
    routes=list(CHANGES)
    for value in labels:
        before=value.replace('PERMANENT_S05_','COMPLETE_DE_').replace('PERMANENT_JOIN37_','COMPLETE_DE_PERMANENT6_').replace('JOIN37','PERMANENT6')
        before=before.replace('COMPLETE_DE_','FREE_DATE_').replace('PERMANENT6','DE30')
        before=before.replace('FREE_DATE_','NONPAYABLE_').replace('DE30','FREE3')
        routes.append((repr(before),repr(before.replace('NONPAYABLE_','MANDOR_PARENT_').replace('FREE3','AFUI15'))))
    for before,after in routes:
        if text.count(before)!=1 or after in text:raise ValueError('MANDOR_PARENT_FETCH_EXACT_ROUTE:'+before)
        text=text.replace(before,after,1)
    recovered=text
    for before,after in reversed(routes):
        if recovered.count(after)!=1:raise ValueError('MANDOR_PARENT_FETCH_EXACT_INVERSE_ROUTE:'+after)
        recovered=recovered.replace(after,before,1)
    if recovered!=original:raise ValueError('MANDOR_PARENT_COMPLETE_ORIGINAL_FETCHER_NOT_RECOVERED')
    compile(text,str(HERE/'derived_AFUI15_fetcher.py'),'exec')
    return text,dict(status='MANDOR_AFUI15_CANONICAL_FETCH_SOURCE_PREPARED_NOT_EXECUTED',
        parent_derivation=prior,original_sha256=sha256(original.encode()).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
        exact_routes=len(routes),original_full_fetcher_recovered=True,
        unchanged_terminal_run_job_attempt_head_archive_size_SHA_CRC_member_path_and_Original_checks=True,
        actual_GitHub_GETs=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def main():
    import qualification
    qualification.actual_parent()  # No source derivation or GET before acceptance.
    text,_=derive();module=ModuleType('mandor_exact_actual_AFUI15_fetcher')
    module.__file__=str(HERE/'derived_AFUI15_fetcher.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__);module.main()


if __name__=='__main__':main()
