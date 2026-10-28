"""Only the two groups that were incomplete at exact84; no new ERP code."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


base=load('retained_actual84_consistency_cases',ROOT/'scripts/current-finance-consistent-capture-diagnostic/cases.py')
adapters=load('focused_consistency_Native_inputs',HERE/'adapters.py')
patch=base.patch
EXPECTED_CATALOG=None


def installed(catalog):
    global EXPECTED_CATALOG
    EXPECTED_CATALOG=catalog


def baseline_assigned_transaction(conn,cur,database,url,report):
    return base.baseline_assigned_transaction(conn,cur,database,url,report)


def native20(conn,cur,database,url,report):
    return adapters.native20(base,conn,cur,database,url,report,installed)


def actual_cron(conn,cur,database,url,report):
    return adapters.actual_cron(base,conn,cur,database,url,report,installed)


CHILDREN=(('REPORT_BOOK_UNCHANGED_NATIVE20',native20),
    ('REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON',actual_cron))
