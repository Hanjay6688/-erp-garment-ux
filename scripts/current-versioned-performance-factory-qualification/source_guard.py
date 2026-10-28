"""Retain the exact actual date-corrected fixture and all factory business guards."""
from pathlib import Path
from hashlib import sha256
import ast,json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def source_binding():
    c=json.loads((HERE/'CONFIG.json').read_bytes())
    old=REPO/'scripts/current-factory-finance-qualification'
    assert sha256((HERE/'fixture.py').read_bytes()).hexdigest()==c['fixture_sha256'],'VERSIONED_FACTORY_DATE_CORRECTED_FIXTURE_CHANGED'
    assert sha256((old/'runner.py').read_bytes()).hexdigest()==c['runner_sha256'],'VERSIONED_FACTORY_RETAINED_RUNNER_CHANGED'
    assert(HERE/'runner.py').read_text()==(old/'runner.py').read_text().replace('import cp7_current_model_target_installation','import cp7_current_versioned_performance_installation'),'VERSIONED_FACTORY_BUSINESS_GUARD_CHANGED'
    expected=(old/'probe.py').read_text().replace('import cp7_current_model_target_installation','import cp7_current_versioned_performance_installation').replace('current-model-target-native-qualification/probe.py','current-versioned-performance-native-qualification/probe.py').replace('CP7_CURRENT_FACTORY_FINANCE1','CP7_CURRENT_VERSIONED_PERFORMANCE_FACTORY_FINANCE1').replace('/tmp/current_factory_finance_pre.dump','/tmp/current_versioned_performance_factory_finance_pre.dump')
    assert(HERE/'probe.py').read_text()==expected,'VERSIONED_FACTORY_PROBE_GUARD_CHANGED'
    assertions={name:sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse((HERE/name).read_text())))for name in ('runner.py','fixture.py','probe.py')}
    return dict(exact_date_corrected_fixture_head=c['old_head'],fixture_sha256=c['fixture_sha256'],retained_assertions=assertions,all_business_oracles_unchanged=True,all24_official_metrics_and_independent_signature_retained=True,original_300s_window_and60_bounded8s_transactions=True,new_factory_runtime_credit=False,production_go=False)
