"""Thin second caller of the existing complete install/Auth/restore runner.

The money runner's original two-case behavior remains its default. This caller
changes only the browser case list, report identity and source admission.
"""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

engine=load('ow08_existing_complete_browser_engine',ROOT/'scripts/current-vendor-money-browser/probe.py')
base=engine.runner
IDS=('OW08_KASBON_JOURNAL_SOURCE_DESKTOP','OW08_KASBON_JOURNAL_SOURCE_MOBILE',
     'OW08_UNKNOWN_WASH_SCREEN_PRICE_DESKTOP','OW08_UNKNOWN_WASH_SCREEN_PRICE_MOBILE',
     'OW08_FG_INVERSE_QC_BLOCKERS_DESKTOP','OW08_FG_INVERSE_QC_BLOCKERS_MOBILE')

def admitted():
    return load('ow08_exact_source_admission',HERE/'admission.py').admitted(ROOT,HERE,engine.product)

def exercise(conn,cur,database,url,report,state):
    result=base.exercise_browser(conn,cur,database,url,report,state,script=HERE/'cases.mjs',ids=IDS,tag='ow08_source6')
    report.update(new_vendor_money_UI_claim=False,full_OW08_acceptance=False,source_navigation_and_unknown_price_screen_cases=6)
    return result

engine.runner=SimpleNamespace(CASE='OW08_SOURCE_BROWSER6',IDS=IDS,exercise=exercise,scheduler_quiet=base.scheduler_quiet,
    BROWSER_CASE_COUNT=len(IDS),NEW_VENDOR_MONEY_UI=False,
    MANUAL_STEPS_SCOPE='ACTUAL_AUTH_OW08_SOURCE6_ON_EXISTING_ISOLATED_COMMITTED_BROWSER_COPY')
engine.IDS=(engine.runner.CASE,);engine.LABEL='CP7_OW08_SOURCE_BROWSER6'
engine.PRE_DUMP='/tmp/ow08_source_browser_pre.dump'
engine.OUT=ROOT/'cp6-proof/t3'/f'{engine.LABEL}.json';engine.admitted=admitted
if __name__=='__main__':
    admitted();engine.package._writer_runtime=lambda browser_mode=False:engine.run();engine.package.run('install')
