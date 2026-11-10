"""Keep the exact money19 callbacks and add six actual upstream callbacks."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('current_automatic_suite_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load('native_cases')
invoices = load('native_invoice_cases')
prerequisites = load('native_preflight')


def bind(business, preflight, product, prefix):
    retained_ids = tuple(business.IDS)
    if len(retained_ids) != 19 or len(set(retained_ids)) != 19:
        raise ValueError('SKU_AUTOMATIC_EXACT_RETAINED_NINETEEN_CASES_REQUIRED')
    ids = retained_ids + native.IDS + invoices.IDS
    if len(ids) != 25 or len(set(ids)) != 25:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_TWENTY_FIVE_CASE_PLAN_REQUIRED')

    def cases(cur, today):
        retained = business.cases(cur, today)
        if tuple(key for key, _ in retained) != retained_ids:
            raise ValueError('SKU_AUTOMATIC_RETAINED_MONEY_CASE_ORDER_CHANGED')
        return retained + native.cases(cur, today, product, business, prefix) + invoices.cases(cur, today, product, business, native)

    def check(cur, today, _business):
        return prerequisites.check(cur, today, business, preflight, product, native, invoices)

    # The retained runner uses these original functions for its separate
    # committed-use witness. Neither the original module nor globals change.
    combined = SimpleNamespace(IDS=ids, cases=cases, n=business.n, f=business.f,
                               canonical=business.canonical, legacy_post=business.legacy_post)
    return combined, SimpleNamespace(check=check)
