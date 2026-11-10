"""Complete owning engine with exact IO and actual Native25/browser2 counts."""
from pathlib import Path
import importlib.util
from hashlib import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RETAINED = ROOT / 'scripts/current-sku-money-composite-preparation/package.py'
MANDOR_AUTHORITY = 'scripts/current-mandor-afui-preparation/report_io.py'
MANDOR_AUTHORITY_PIN = (9238, '300a4239a2e3fec6bbd6fa6fc8115a730034592aa362fee1993cff013e0c3c25')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installer_authority(frozen_parent):
    path = frozen_parent / MANDOR_AUTHORITY
    if not path.is_file() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('SKU_AUTOMATIC_EXACT_MANDOR_INSTALL_AUTHORITY_FILE_REQUIRED')
    raw = path.read_bytes()
    if (len(raw), sha256(raw).hexdigest()) != MANDOR_AUTHORITY_PIN:
        raise ValueError('SKU_AUTOMATIC_EXACT_MANDOR_INSTALL_AUTHORITY_BYTES_REQUIRED')
    return load('automatic_exact_mandor_install_authority', path).install_qualified_parent


def bind_install_authority(product, install_afui, as_admin):
    money = product.parent()
    moving = money.parent()
    mandor = moving.parent()

    def install_parent(cur):
        # Mandor's fixture admission needs maintenance identity at entry.
        afui_state = install_afui(cur)
        mandor_state = mandor.install_delta(cur, afui_state)

        def install_sku_parents(admin):
            moving_state = moving.install_delta(admin, mandor_state)
            return money.install_delta(admin, moving_state)

        return as_admin(cur, install_sku_parents)

    def scoped(operation):
        def run(cur, state):
            return as_admin(cur, lambda admin: operation(admin, state))
        return run

    return dict(_sku_install_parent=install_parent,
                _sku_install_delta=scoped(product.install_delta),
                _sku_rollback_delta_preuse=scoped(product.rollback_delta_preuse),
                _sku_verify_installed=scoped(product.verify))


def derive(raw):
    original, prior = load('automatic_retained_whole_money_engine', RETAINED).derive(raw)
    io = load('automatic_complete_package_report_IO', HERE / 'report_io.py')
    text, output = io.derive_packet(original, 'money19')
    replacements = (
        ("'ACTUAL_CURRENT_MANDOR_AND_MOVING_PARENT_INSTALL',product.parent().install,cur",
         "'ACTUAL_CURRENT_MANDOR_MOVING_AND_MONEY_PARENT_INSTALL',_sku_install_parent,cur"),
        ("'FIRST_FINANCE_DELTA',product.install_delta,cur,prior",
         "'FIRST_FINANCE_DELTA',_sku_install_delta,cur,prior"),
        ("'FINANCE_DELTA_PREUSE_INVERSE',product.rollback_delta_preuse,cur,STATE",
         "'FINANCE_DELTA_PREUSE_INVERSE',_sku_rollback_delta_preuse,cur,STATE"),
        ("'SECOND_FINANCE_DELTA',product.install_delta,cur,prior",
         "'SECOND_FINANCE_DELTA',_sku_install_delta,cur,prior"),
        ("report['complete_installed_verification']=product.verify(cur,STATE)",
         "report['complete_installed_verification']=_sku_verify_installed(cur,STATE)"),
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
                      exact_install_authority_routes=5,
                      source_sha256=sha256(text.encode()).hexdigest(),
                      actual_counts_still_read_from_completed_component=True,
                      actual_Auth_HTTP_and_race_counts_remain_zero=True,
                      browser_count_and_Auth_claim_read_from_completed_current_component=True,
                      full_install_unused_inverse_used_guard_all22_all_rows_all_sequences_and_restore_unchanged=True,
                      actual_ERP_cases=0, production_go=False)
