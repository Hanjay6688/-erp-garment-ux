"""One fresh factory closure; six groups remain attributed to actual 11c."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
parent=load('factory_live_parent_cases',ROOT/'scripts/current-factory-initial-stage/cases.py')
product=parent.product
factory=load('factory_live_actual_case',HERE/'factory.py')
installed_operations=parent.installed_operations
def factory_cron(conn,cur,database,url,report):
    parent.verify_existing(conn,cur,report)
    factory.exercise(conn,cur,database,url,report)
    expected,actual=cur.execute('select report_book_signature,book_signature from cp7_finance_capture.captures where id=%s',
        (report['finance_capture_id'],)).fetchone()
    assert expected is not None and expected==actual
    conn.rollback()
    report['report_and_collected_book_signatures_equal']=True
CHILDREN=(('COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON',factory_cron),)
