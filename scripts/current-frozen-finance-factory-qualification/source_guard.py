"""Exact old factory fixture and assertions, on the new private request transport."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def expected_runner():
    old=(REPO/'scripts/current-versioned-performance-factory-qualification/runner.py').read_text()
    return old.replace('import cp7_current_versioned_performance_installation','import cp7_current_frozen_finance_installation').replace(
        "'scripts/current-bounded-finance-native-qualification/cases.py'",
        "'scripts/current-frozen-finance-native-qualification/finance_cases.py'").replace(
        "CASE='CURRENT_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE'",
        "CASE='CURRENT_FROZEN_PRIVATE_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE'").replace(
        'explicit_bounded_STAGED_and_legacy_DEFERRED','explicit_private_STAGED_and_operational_DEFERRED')


def expected_probe():
    return (REPO/'scripts/current-versioned-performance-factory-qualification/probe.py').read_text().replace(
        'import cp7_current_versioned_performance_installation','import cp7_current_frozen_finance_installation').replace(
        'current-versioned-performance-native-qualification/probe.py','current-frozen-finance-native-qualification/probe.py').replace(
        'CP7_CURRENT_VERSIONED_PERFORMANCE_FACTORY_FINANCE1','CP7_CURRENT_FROZEN_PRIVATE_FACTORY_FINANCE1').replace(
        '/tmp/current_versioned_performance_factory_finance_pre.dump','/tmp/current_frozen_private_factory_finance_pre.dump')


def source_binding():
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    old=REPO/'scripts/current-factory-finance-qualification/runner.py'
    assert sha256(old.read_bytes()).hexdigest()==config['runner_sha256']
    spec=importlib.util.spec_from_file_location('retained_performance_factory_source_guard',REPO/'scripts/current-versioned-performance-factory-qualification/source_guard.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    previous.source_binding()
    assert sha256((HERE/'fixture.py').read_bytes()).hexdigest()==config['fixture_sha256']=='6dceb87ae35bb87527eba3176f80b292e5ab9ef2a4a4b5a813bf6d3f3097724e'
    assert (HERE/'runner.py').read_text()==expected_runner(),'FROZEN_FACTORY_BUSINESS_GUARD_CHANGED'
    assert (HERE/'probe.py').read_text()==expected_probe(),'FROZEN_FACTORY_FULL_RESTORE_GUARD_CHANGED'
    counts={name:sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse((HERE/name).read_bytes())))
            for name in('runner.py','fixture.py','probe.py')}
    assert sum(counts.values())==63
    return dict(exact_date_corrected_fixture_head=config['old_head'],fixture_sha256=config['fixture_sha256'],
        retained_assertions=counts,total_assertions=63,private_transport_only=True,
        all24_official_metrics_and_independent_signature_retained=True,
        all_money_stock_HPP_and_UNKNOWN_guards_retained=True,
        unchanged_300s_window_and60_bounded8s_transactions=True,
        new_factory_runtime_credit=False,production_go=False)
