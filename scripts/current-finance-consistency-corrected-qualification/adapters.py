"""Correct qualification inputs; preserve the Native operations and oracles."""
from contextlib import contextmanager
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[2]
REPORT_IDS=frozenset(('OW12A_REPORT_V2_FINANCE_THROUGH_CAPTURE',
    'OW12A_REPORT_V2_DEFERRED_UNCHANGED','OW12A_REPORT_V2_PERIOD_COMPARISON'))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


fixture=load('retained_Native_attendance_fixture',ROOT/'scripts/current-finance-readonly-integration-qualification/filing_fixture.py')


def prepared_cases(retained,cur,today,prepare):
    ids=[key for key,_ in retained]
    if len(ids)!=len(set(ids))or not REPORT_IDS.issubset(ids):
        raise ValueError('CONSISTENCY_THREE_BUSINESS_REPORT_CASES_REQUIRED')
    return [(key,(lambda operation=operation:fixture.prepared(operation,cur,today,prepare))
        if key in REPORT_IDS else operation)for key,operation in retained]


@contextmanager
def inputs(base,on_install,*,capture=False,cron=None):
    install,original_cases,original_cron=base.install,base.capture.cases,base.cron
    def installed(*args):
        install(*args)
        if on_install is not None:on_install(base.EXPECTED_CATALOG)
    base.install=installed
    if capture:
        base.capture.cases=lambda cur,today:prepared_cases(original_cases(cur,today),cur,today,
            base.chain.prepare_attendance_pools)
    if cron is not None:base.cron=cron
    try:yield
    finally:base.install,base.capture.cases,base.cron=install,original_cases,original_cron


def native20(base,conn,cur,database,url,report,on_install=None):
    with inputs(base,on_install,capture=True):
        return base.native20(conn,cur,database,url,report)


def actual_cron(base,conn,cur,database,url,report,on_install=None):
    accepted=load('exact_accepted_readonly_minute_cron',
        ROOT/'scripts/current-finance-readonly-integration-qualification/runner.py')
    with inputs(base,on_install,cron=accepted):
        return base.actual_cron(conn,cur,database,url,report)
