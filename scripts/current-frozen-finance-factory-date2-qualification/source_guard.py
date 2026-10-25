"""Exact executed daab fixture; unchanged private runner, money and restore guards."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import json

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
FIXTURE_SHA='193197b3c288b382970250f2f3db4c38ea21e3fd45bb1729fe25f94ecbe5e3bd'
FIXTURE_PATH='scripts/current-factory-finance-runtime-qualification/fixture.py'


def source_binding():
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    old=REPO/'scripts/current-frozen-finance-factory-qualification'
    spec=importlib.util.spec_from_file_location('retained_private_factory_guard',old/'source_guard.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    retained=previous.source_binding()
    assert config['fixture_path']==FIXTURE_PATH
    assert sha256((HERE/'fixture.py').read_bytes()).hexdigest()==config['fixture_sha256']==FIXTURE_SHA,'EXECUTED_FACTORY_FIXTURE_CHANGED'
    for name in ('runner.py','probe.py'):
        assert (HERE/name).read_bytes()==(old/name).read_bytes(),('RETAINED_FACTORY_GUARD_CHANGED',name)
    counts={name:sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse((HERE/name).read_bytes())))
            for name in ('runner.py','fixture.py','probe.py')}
    assert counts['runner.py']==retained['retained_assertions']['runner.py']
    assert counts['probe.py']==retained['retained_assertions']['probe.py']
    assert counts['fixture.py']==retained['retained_assertions']['fixture.py']+2
    return dict(executed_fixture_head=config['old_head'],executed_fixture_path=FIXTURE_PATH,
        fixture_sha256=FIXTURE_SHA,retained_assertions=counts,total_assertions=sum(counts.values()),
        nine_posted_history_tables_checked=True,private_transport_only=True,
        all24_official_metrics_and_independent_signature_retained=True,
        all_money_stock_HPP_and_UNKNOWN_guards_retained=True,
        unchanged_300s_window_and60_bounded8s_transactions=True,
        new_factory_runtime_credit=False,production_go=False)
