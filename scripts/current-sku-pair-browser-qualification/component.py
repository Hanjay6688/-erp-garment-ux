"""Hook only: the integrator owns admission, installed clone and full restore.

No command-line main, no installer mutations, no CI trigger or publication.
For a combined host, concatenate browser.mjs's cases(ui,today) directly instead.
"""
from pathlib import Path
import importlib.util,os

HERE=Path(__file__).resolve().parent

def exercise(verify,phase='sku_pair_browser2'):
    spec=importlib.util.spec_from_file_location('sku29_browser_source_guard',HERE/'source_guard.py')
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    admitted=source.admitted()
    import cp6_auditor_modes as modes
    # The unchanged host owns timeout teardown. No timed-out SKU operation is
    # allowed to keep running while a second case starts on the same copy.
    prior=os.environ.get('AUDITOR_BROWSER_CASE_TIMEOUT_MS')
    os.environ['AUDITOR_BROWSER_CASE_TIMEOUT_MS']='600000'
    try:result=modes.run_browser(HERE/'browser.mjs',verify,phase)
    finally:
        if prior is None:os.environ.pop('AUDITOR_BROWSER_CASE_TIMEOUT_MS',None)
        else:os.environ['AUDITOR_BROWSER_CASE_TIMEOUT_MS']=prior
    return dict(result,SKU29_browser_source_admission=admitted,
      outer_actual_install_backup_all22_rows_sequences_roles_Auth_advisors_and_package_required=True,
      production_go=False,independent_acceptance=False)
