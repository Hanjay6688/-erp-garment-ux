"""Actual probe failure-emission controls; no database or Native exit credit."""
import ast
import json
import tempfile
import traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def main():
    source = Path(__file__).with_name('cp7_f05_analysis_probe.py').read_text()
    module = ast.parse(source)
    run = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    outer = next(node for node in run.body if isinstance(node, ast.Try))
    restoration = next(node for node in outer.finalbody if isinstance(node, ast.If) and ast.unparse(node.test) == 'installed')
    with tempfile.TemporaryDirectory(prefix='cp7-emission-control-') as temporary:
        for initial_error in (None, 'earlier actual case failure'):
            report = {'status': 'INCOMPLETE'}
            for group, count in [('native', 10), ('races', 2), ('http', 2), ('browser', 2)]:
                report[group] = {'status': 'PASS', 'counts': {'PASS': count}}
            if initial_error:
                report['error'] = initial_error
            connection = Mock()
            connection.connect.side_effect = RuntimeError('deliberate restoration lock failure')
            output = Path(temporary) / ('earlier.json' if initial_error else 'restore.json')
            environment = dict(installed=True, psycopg=connection, package=Mock(), report=report,
                               traceback=traceback, fabric_any=False, p19_load=False, p19_transport=False, p19_scale=False, p19_staged=False,
                               attention=False, p18_e01=False,
                               rule_lifecycle=False, source_navigation=False, misc_correction=False,
                               payment_correction=False, supplier_payment_correction=False,
                               return_correction=False, sales_chain=False, cutting_correction=False,
                               expected=16, out=output, json=json)
            # Execute the current real finalizer, including status calculation
            # and actual report writing, without importing a Native connection.
            finalizer = ast.fix_missing_locations(ast.Module(body=outer.finalbody, type_ignores=[]))
            exec(compile(finalizer, 'actual-probe-finalizer', 'exec'), environment)
            emitted = json.loads(output.read_text())
            assert emitted['status'] == 'INCOMPLETE' and emitted['observed_case_count'] == 16
            assert emitted['cp6_restored'] is emitted['advisor_gate'] is False
            assert 'deliberate restoration lock failure' in emitted['restore_error']
            assert sum(sum(emitted[group]['counts'].values()) for group in ('native', 'races', 'http', 'browser')) == 16
            assert emitted['error'] == initial_error if initial_error else emitted['error'].startswith('CP7_RESTORATION_INCOMPLETE:')
        declaration=json.loads(Path(__file__).resolve().parents[1].joinpath('docs/cp7/p19/P19_NATIVE_LOAD.json').read_text())
        for fault in ('NONE', 'WRONG_ID', 'MISSING_GROUP', 'RESTORATION_FAILURE', 'EARLIER_FAILURE'):
            report=dict(status='INCOMPLETE',cp6_restored=True,advisor_gate=True,
                        required_case_counts=declaration['required_case_counts'])
            for group,ids in declaration['required_case_ids'].items():
                report[group]=dict(status='PASS',counts={'PASS':len(ids)},
                                   **{'races'if group=='races'else'cases':{key:dict(status='PASS')for key in ids}})
            connection=Mock();connection.connect.side_effect=RuntimeError('deliberate restoration lock failure')
            if fault=='WRONG_ID':
                ids=report['native']['cases'];row=ids.pop(next(iter(ids)));ids['UNDECLARED_SUBSTITUTE']=row
            elif fault=='MISSING_GROUP':report.pop('http')
            elif fault=='EARLIER_FAILURE':report['error']='earlier actual case failure'
            output=Path(temporary)/('p19-'+fault+'.json')
            environment.update(installed=fault=='RESTORATION_FAILURE',p19_load=True,report=report,
                               expected=6,out=output,psycopg=connection,
                               case_provider=SimpleNamespace(IDS=declaration['required_case_ids']))
            exec(compile(finalizer,'actual-p19-finalizer','exec'),environment)
            emitted=json.loads(output.read_text())
            assert emitted['status']==('PASS'if fault=='NONE'else'INCOMPLETE')
            assert emitted['observed_case_count']==(4 if fault=='MISSING_GROUP'else 6)
            assert 'browser'not in emitted
            if fault=='RESTORATION_FAILURE':
                assert emitted['cp6_restored']is emitted['advisor_gate']is False
                assert 'deliberate restoration lock failure'in emitted['restore_error']
            if fault=='EARLIER_FAILURE':assert emitted['error']=='earlier actual case failure'
    print(json.dumps(dict(status='PASS', actual_finalizer_emission_controls=7,
                         passing_cases_do_not_override_failed_restoration=True,
                         Native_database_access=False, Native_product_case_credit=0)))


if __name__ == '__main__':
    main()
