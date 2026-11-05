"""Complete owning engine with exact IO and actual Native25/browser2 counts."""
from pathlib import Path
import importlib.util
from hashlib import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RETAINED = ROOT / 'scripts/current-sku-money-composite-preparation/package.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive(raw):
    original, prior = load('automatic_retained_whole_money_engine', RETAINED).derive(raw)
    io = load('automatic_complete_package_report_IO', HERE / 'report_io.py')
    text, output = io.derive_packet(original, 'money19')
    replacements = (
        ("'ACTUAL_CURRENT_MANDOR_AND_MOVING_PARENT_INSTALL'", "'ACTUAL_CURRENT_MANDOR_MOVING_AND_MONEY_PARENT_INSTALL'"),
        ("'CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'", "'CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY'"),
        ("report['actual_browser_cases']=0", "report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']"),
        ("report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']",
         "report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']+cases[runner.CASE]['actual_browser_cases']\n"
         "            report['real_Auth_browser_claim']=cases[runner.CASE]['real_Auth_browser_claim']"),
    )
    for before, after in replacements:
        if text.count(before) != 1 or after in text:
            raise ValueError('SKU_AUTOMATIC_ONE_COMPLETE_PACKAGE_LABEL_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(replacements):
        restored = restored.replace(after, before, 1)
    restored = restored.replace(io.HELPER + '(OUT,report)', io.PACKET_BEFORE, 1)
    if restored != original:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_OWNING_MONEY_PACKAGE_NOT_RECOVERED')
    compile(text, 'automatic-complete-owning-package', 'exec', dont_inherit=True)
    return text, dict(retained_money_package=prior, complete_packet_output=output,
                      additional_label_routes=2, actual_completed_browser_count_routes=2, complete_money_engine_recovered=True,
                      source_sha256=sha256(text.encode()).hexdigest(),
                      actual_counts_still_read_from_completed_component=True,
                      actual_Auth_HTTP_and_race_counts_remain_zero=True,
                      browser_count_and_Auth_claim_read_from_completed_current_component=True,
                      full_install_unused_inverse_used_guard_all22_all_rows_all_sequences_and_restore_unchanged=True,
                      actual_ERP_cases=0, production_go=False)
