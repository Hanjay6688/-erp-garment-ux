"""Retain exact prior cron operations while declaring every new hook."""
from pathlib import Path
from hashlib import sha256
import ast,json


def check(repo,here,overrides=None):
    overrides=overrides or {}
    origin=json.loads((here/'ORIGIN.json').read_bytes());counts={}
    for name,rule in origin['transforms'].items():
        raw=(repo/rule['path']).read_bytes()
        assert sha256(raw).hexdigest()==rule['sha256'],('PRIOR_CRON_SOURCE_CHANGED',name)
        expected=raw.decode()
        for old,new in rule['replacements']:
            assert expected.count(old)==1,('CRON_TRANSFORM_ANCHOR_CHANGED',name,old)
            expected=expected.replace(old,new,1)
        actual=overrides.get(name,(here/name).read_text())
        assert actual==expected,('UNDECLARED_CRON_OPERATION_OR_ORACLE_CHANGE',name)
        counts[name]=sum(isinstance(x,ast.Assert)for x in ast.walk(ast.parse(actual)))
    assert counts==origin['assertion_counts']
    for path,digest in origin['exact_helpers'].items():
        assert sha256((here/path).read_bytes()).hexdigest()==digest,path
    fixture=ast.parse((here/'choice_fixture.py').read_text())
    for node in ast.walk(fixture):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='call':
            if isinstance(node.func.value,ast.Name)and node.func.value.id=='B':
                assert len(node.args)>1 and isinstance(node.args[1],ast.Constant)
                assert node.args[1].value in ('request','get'),'MANUAL_CHOICE_STEP_FORBIDDEN'
    return dict(retained_assertions=counts,unchanged300_second_window=True,
        unchanged60_bounded_transactions=True,unchanged_production_minute_schedule=True,
        no_manual_preparation_steps=True,full22_data_sequence_CP6_advisor_guards_retained=True,
        actual_cron_claim=False,production_go=False)
