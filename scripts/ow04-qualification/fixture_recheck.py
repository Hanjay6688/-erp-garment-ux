"""Actual import/parser controls only; no database, browser or race execution."""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import psycopg

REPO=Path(os.environ.get('ERP_REPO',Path(__file__).resolve().parents[2])).resolve()
BASE='8a683ef21d2236d438c9a534f355c181a17fea2a'
results=[];connections=[]
def forbidden(*args,**kwargs):
    connections.append(True)
    raise AssertionError('FIXTURE_CONTROLS_MUST_NOT_CONNECT')
psycopg.connect=forbidden

import browser_fixture as fixture
assert fixture.http_cases is fixture.transport.initial_http
assert fixture.initial is fixture.http_cases.initial
assert callable(fixture.http_cases.prepared)and callable(fixture.http_cases.snapshot)
results.append(dict(id='ACTUAL_BROWSER_FIXTURE_IMPORT_AND_HELPERS',status='PASS'))
old=subprocess.check_output(['git','-C',str(REPO),'show',BASE+':scripts/ow04-qualification/browser_fixture.py'],text=True)
try:exec(compile(old,'before_browser_fixture.py','exec'),{'__name__':'before_browser_fixture','__file__':fixture.__file__})
except AttributeError as error:
    assert "has no attribute 'initial'"in str(error)
    results.append(dict(id='ORIGINAL_BROWSER_IMPORT_FAILURE_REPRODUCED',status='PASS',error=str(error)))
else:raise AssertionError('original import must fail')

raw_path=REPO/'scripts/cp7_customer_credit/native/cp7_ow04_native_source_fixture.py'
raw_node=next(n for n in ast.parse(raw_path.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='_raw')
namespace=dict(json=json,hashlib=hashlib)
exec(compile(ast.Module(body=[raw_node],type_ignores=[]),str(raw_path),'exec'),namespace)
exact_raw=namespace['_raw']
race_path=REPO/'scripts/ow04-qualification/cp7_ow04_source_inverse_race_cases.py'
before=subprocess.check_output(['git','-C',str(REPO),'show',BASE+':'+str(race_path.relative_to(REPO))],text=True)
def operation(source):
    return next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='_operation')
def assignment(source):
    return next(n for n in operation(source).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='current_source'for t in n.targets))
after=race_path.read_text()
guard=next(n for n in operation(after).body if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='key')
before_guard=next(n for n in operation(before).body if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='key')
assert ast.dump(guard)==ast.dump(before_guard),'HPP equality predicates must be unchanged'
keys=ast.literal_eval(guard.iter)
assert keys==('hpp_versions','opening_hpp_corrections','nonpo_hpp_events','po_hpp_events',
              'opening_hpp_states','po_hpp_states','hpp_accounts','period_snapshot')
raw='{"hpp_versions":[{"id":"fixture-hpp","hpp_per_pcs":10.000000,"total_cost":100.000000,"version_no":1,"is_current":true}],'+','.join('"'+key+'":[]'for key in keys[1:])+'}'
class Cursor:
    def __init__(self,text):self.text=text
    def execute(self,query,args):
        assert args==('fixture-sale',)
        self.value=self.text if query.endswith('::text')else json.loads(self.text)
        return self
    def fetchone(self):return(self.value,)
sealed=exact_raw(Cursor(raw),'select cp7_credit.source_native_snapshot_v1(%s)',('fixture-sale',))['document']
def check(source,text):
    scope=dict(cur=Cursor(text),f={'sale':'fixture-sale'},native=SimpleNamespace(_raw=exact_raw),
        op={'before_source':deepcopy(sealed),'actual_source':deepcopy(sealed)},
        completions=[{'final_native_source':deepcopy(sealed)}])
    exec(compile(ast.Module(body=[assignment(source),guard],type_ignores=[]),str(race_path),'exec'),scope)
    return scope['current_source']
try:check(before,raw)
except AssertionError as error:
    assert error.args[0]==('OW04_SOURCE_RACE_ADDITIONAL_NATIVE_HPP_EFFECT','hpp_versions')
    results.append(dict(id='ORIGINAL_MIXED_JSON_NUMERIC_READ_REPRODUCED',status='PASS',error=str(error)))
else:raise AssertionError('original numeric decoding must reproduce failure')
assert check(after,raw)==sealed
results.append(dict(id='SAME_EXACT_PARSER_ACCEPTS_IDENTICAL_FULL_SNAPSHOTS',status='PASS'))
mutations=[('HPP_AMOUNT_CHANGED',raw.replace('10.000000','10.000001')),
           ('EXTRA_HPP_VERSION',raw.replace('"version_no":1,"is_current":true}]','"version_no":1,"is_current":true},{"id":"extra-hpp"}]'))]
mutations +=[(key.upper()+'_CHANGED',raw.replace('"'+key+'":[]','"'+key+'":[{"changed":true}]'))for key in keys[1:]]
for ident,text in mutations:
    assert text!=raw
    try:check(after,text)
    except AssertionError as error:
        assert error.args[0][0]=='OW04_SOURCE_RACE_ADDITIONAL_NATIVE_HPP_EFFECT'
        results.append(dict(id=ident,status='PASS',changed_fact_rejected=True))
    else:raise AssertionError('changed HPP/source snapshot must still be rejected: '+ident)
large=raw.replace('100.000000','999999999999999999999999.990001')
assert exact_raw(Cursor(large),'select cp7_credit.source_native_snapshot_v1(%s)',('fixture-sale',))['document']['hpp_versions'][0]['total_cost']=='999999999999999999999999.990001'
results.append(dict(id='ACTUAL_PARSER_RETAINS_LARGE_EXACT_DECIMAL',status='PASS'))
assert connections==[]
print(json.dumps(dict(classification='ACTUAL_IMPORT_AND_READER_EXPRESSIONS_SYNTHETIC_INPUT_NOT_RUNTIME_PROOF',
    status='PASS',count=len(results),results=results,database_calls=0,Native_executed=False,
    unchanged_HPP_guard_AST=True,production_go=False)))
