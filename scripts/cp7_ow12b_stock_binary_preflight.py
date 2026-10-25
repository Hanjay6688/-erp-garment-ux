"""Actual closed route admission, source declarations and independent codec."""
import ast,copy,inspect,json,sys
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_stock_binary_cases as c
from cp7_ow12b_stock_binary_codec import encode,decode,expected_values,FIELDS

root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/STOCK_BINARY_NATIVE4_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(c.CONTRACT,c.IDS,c.REQUIRED,c.EXPECTED)
assert c.EXPECTED==c.DECLARED==4 and c.REQUIRED==dict(native=4)
assert d['public_rpcs']==list(c.FUNCTIONS)and d['schedules']==c.SCHEDULES
assert d['stock_binary_source_sha256']==c.sources()
c.binary_stage.verify_sources()
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,ow13c_history_reference=True,ow12b_stock_binary=True)
assert ns['run'](**args)
refused=0
for flag in set(args)-{'ow12b_stock_binary'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('STOCK_BINARY_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 value='A'if flag.endswith('_part')else True
 try:ns['run'](**{**args,flag:value})
 except AssertionError as error:assert str(error)=='STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('STOCK_BINARY_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-source-only','exec'),ns)
report=ns['source_only'](**args)
assert report['label']=='CP7_OW12B_STOCK_BINARY'and report['expected_case_count']==4
assert report['required_case_counts']==c.REQUIRED and report['required_case_ids']==c.IDS
assert report['predeclared_case_contract']==d and report['stock_binary_source_sha256']==c.sources()
# Independent codec round trips exercise NULL versus empty, UTF8, timezone
# microseconds, infinities and a 64-bit integer above Number's exact range.
row=dict(zip((name for name,_ in FIELDS),['11111111-1111-4111-8111-111111111111']*6+['三\nA','-9007199254740993.00','2026-10-25T01:02:03.123456+07:00','2026-10-25T01:02:03.123457+07:00','SALE','SYNTHETIC',None,None,'9223372036854775807']))
assert decode(encode(row))==expected_values(row)
for key,value in(('physical_at','-infinity'),('system_created_at','infinity'),('source_type',''),('source_type',None)):
 changed=dict(row);changed[key]=value;assert decode(encode(changed))==expected_values(changed)and encode(changed)!=encode(row)
for malformed in(encode(row)[:-1],encode(row)+b'X',b''):
 try:decode(malformed)
 except AssertionError:pass
 else:raise AssertionError('BINARY_MALFORMED_FRAME_ACCEPTED')
assert len(FIELDS)==len(c.binary_stage.render.LAYOUT)==15
assert {oid for _,oid in FIELDS}=={2950,17,1184,20}
print(json.dumps(dict(status='PASS',native_cases_declared=4,source_pins=len(c.sources()),actual_source_only_route=True,invalid_or_missing_route_controls=refused,independent_codec_controls=True,malformed_frames_refused=3,actual_Native=False,actual_Auth_HTTP_credit=False,caller_integrated=False,production_go=False)))
