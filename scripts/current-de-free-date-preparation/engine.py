"""Reuse the entire original package engine with declared date-only routes."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def derive(raw):
    path=ROOT/'scripts/current-complete-de-integration-preparation/engine.py'
    spec=importlib.util.spec_from_file_location('free_date_exact_complete_DE_engine_derivation',path)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    text,prior=parent.derive(raw)
    changes=(('ACTUAL_QUALIFIED_COMPLETE_PERMANENT_PARENT_INSTALL',
              'ACTUAL_QUALIFIED_COMPLETE_DE_NATIVE30_PARENT_INSTALL'),
             (parent.COUNTS_AFTER,parent.COUNTS_AFTER.replace("=30","=0")
              .replace('retained_permanent6_fresh_case_credit','retained_DE30_fresh_case_credit')
              +"\n            report['retained_Native_cases']=3"
              +"\n            report['retained_cases_are_not_fresh']=True"
              +"\n            report['candidate_case_coverage']=3"
              +"\n            report['financial_groups_rerun']=False"
              +"\n            report['source_invariant_reuse']=True"
              +"\n            report['prior_runs_aggregated']=True"))
    original=text
    for before,after in changes:
        if text.count(before)!=1 or after in text:
            raise ValueError('FREE_DATE_EXACT_WHOLE_ENGINE_ROUTE_REQUIRED')
        text=text.replace(before,after,1)
    restored=text
    for before,after in reversed(changes):
        if restored.count(after)!=1:raise ValueError('FREE_DATE_EXACT_WHOLE_ENGINE_REVERSE_REQUIRED')
        restored=restored.replace(after,before,1)
    if restored!=original:raise ValueError('FREE_DATE_ORIGINAL_DE_ENGINE_NOT_RECOVERED')
    compile(text,'free-date-derived-whole-package-engine','exec')
    return text,dict(parent_derivation=prior,parent_derived_sha256=sha256(original.encode()).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),additional_declared_routes=2,
        entire_original_engine_recovered=True,all_original_backup_restore_and_package_checks_retained=True,
        actual_Native_cases=0,actual_SQL_executed=0)
