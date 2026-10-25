"""Only full composer and exact qualified public request helper change."""
from hashlib import sha256
import ast

RUNNER_CHANGES={
 'import cp7_current_versioned_performance_installation as product':'import cp7_current_frozen_public_installation as product',
 "ROOT/'scripts/current-bounded-finance-native-qualification/cases.py'":"ROOT/'scripts/current-frozen-public-native-qualification/public_finance_cases.py'",
}
PROBE_CHANGES={
 'import cp7_current_versioned_performance_installation as product':'import cp7_current_frozen_public_installation as product',
 "REPO/'scripts/current-versioned-performance-native-qualification/probe.py'":"REPO/'scripts/current-frozen-public-native-qualification/probe.py'",
 "LABEL='CP7_CURRENT_VERSIONED_PERFORMANCE_CRON1'":"LABEL='CP7_CURRENT_FROZEN_PUBLIC_CRON1'",
 "PRE_DUMP='/tmp/current_versioned_performance_cron_pre.dump'":"PRE_DUMP='/tmp/current_frozen_public_cron_pre.dump'",
}
def check(repo,here,runner_text=None,probe_text=None):
    old=repo/'scripts/current-versioned-performance-cron-qualification';counts={};hashes={}
    for name,changes,override in [('runner.py',RUNNER_CHANGES,runner_text),('probe.py',PROBE_CHANGES,probe_text)]:
        expected=(old/name).read_text()
        for a,b in changes.items():
            assert expected.count(a)==1,('SOURCE_ANCHOR_CHANGED',name,a)
            expected=expected.replace(a,b)
        actual=(here/name).read_text()if override is None else override
        assert actual==expected,('RETAINED_CRON_OR_RESTORE_GUARD_CHANGED',name)
        counts[name]=sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))
        hashes[name]=sha256(actual.encode()).hexdigest()
    assert counts=={'runner.py':36,'probe.py':10}
    return dict(retained_assertions=counts,source_sha256=hashes,
        unchanged60_bounded_transactions=True,unchanged300_second_window=True,
        unchanged_production_minute_schedule=True,full22_all_rows_sequences_restore_guard_retained=True,
        actual_cron_claim=False,production_go=False)
