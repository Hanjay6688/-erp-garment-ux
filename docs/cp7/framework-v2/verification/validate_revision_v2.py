"""Offline preparation checks; never marks ERP runtime PASS."""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal
import sys,json,re,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
from jsonschema import Draft202012Validator,FormatChecker
from semantic_contract import validate_semantics
from generate_contract_types import render
P=Path(__file__).resolve().parents[1]
def read(f):return json.loads((P/f).read_text())
checks=[]
def check(name,ok,detail=''):
    checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})
    if not ok:raise AssertionError(name+': '+str(detail))
schema=read('contracts/analysis.schema.json');e=read('contracts/analysis.example.json')
Draft202012Validator.check_schema(schema)
v=Draft202012Validator(schema,format_checker=FormatChecker())
check('example_shape',not list(v.iter_errors(e)))
check('example_semantics',not validate_semantics(e),validate_semantics(e))
typescript=(P/'contracts/backbone.ts').read_text()
apply_types=typescript[typescript.index('export type ApplyPlanActionRequest'):]
check('typescript_shape_generated_from_schema',typescript==render(schema,apply_types))
canonical=deepcopy(e);canonical.pop('run_id');canonical.pop('semantic_hash')
canonical['snapshot'].pop('snapshot_id');canonical['snapshot'].pop('generated_at')
check('example_semantic_hash',hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()==e['semantic_hash'])
def invalid(name,change,code):
    x=deepcopy(e);change(x);errors=validate_semantics(x)
    check(name,any(err.startswith(code) for err in errors),errors)
invalid('fractional_count',lambda x:x['recommendations'][0]['actual_fg'].update(value='0.5'),'COUNT_INVALID')
invalid('source_overallocation',lambda x:x['sources'][1]['allocated'].update(value='21'),'SOURCE_INPUT_CAPACITY')
invalid('incomplete_complete',lambda x:x['snapshot'].update(capture_complete=False),'COMPLETE_WITH_INCOMPLETE_CAPTURE')
invalid('negative_lost_sales',lambda x:x['timeline'][0].update(mode='LOST_SALES',balance_end={'state':'KNOWN','value':'-2','unit':'PCS','refs':[]}),'LOST_SALES_CARRIES_BACKLOG')
invalid('wrong_edge_size',lambda x:x['allocation_edges'][0].update(size_id='31'),'EDGE_SIZE_MISMATCH')
invalid('incompatible_edge',lambda x:x['allocation_edges'][0].update(match='INCOMPATIBLE'),'INELIGIBLE_MATCH')
invalid('missing_edge',lambda x:x['allocation_edges'].pop(),'EDGE_INPUT_TOTAL')
invalid('stopped_start',lambda x:x['recommendations'][0].update(production_state='STOPPED'),'INACTIVE_START_NEW')
invalid('undefined_assumption',lambda x:x['recommendations'][0]['assumption_ids'].append('MISSING'),'UNRESOLVED_ASSUMPTION')
invalid('metric_scope',lambda x:x['metrics'][0].update(scope_key='MISSING'),'UNRESOLVED_METRIC_TARGET')
x=deepcopy(e);x['timeline'][0]['demand']={'state':'UNKNOWN','reason':'AVAILABILITY_UNKNOWN','unit':'PCS','refs':[]}
check('schema_represents_unknown_timeline',not list(v.iter_errors(x)),'Shape only; propagation needs ERP proof')
x=deepcopy(e)
for field,val in [('physical_remaining','100'),('eligible_input','100'),('eligible_projected','90'),('allocated','100')]:x['sources'][1][field]['value']=val
x['allocation_edges'][1]['input_qty']['value']='100';x['allocation_edges'][1]['projected_output_qty']['value']='90'
check('yield_input100_output90',not validate_semantics(x),validate_semantics(x))
x['allocation_edges'][1]['projected_output_qty']['value']='91'
check('yield_output91_rejected','SOURCE_OUTPUT_CAPACITY' in validate_semantics(x))
req=read('registries/requirements.json');cases=read('registries/cases.json');packets=read('registries/work_packets.json')
owners=read('registries/owner_delta.json');families=read('registries/families.json');subs=read('registries/subpackets.json')
cs={c['id'] for c in cases};ps={p['id']:p for p in packets}
check('counts',len(req)==271 and len(cases)==84 and len(packets)==22 and len(owners)==10 and len(families)==7 and len(subs)==10)
check('unique_ids',len(cs)==84 and len(ps)==22)
check('legacy_mappings',all(all(c in cs for c in r['case_ids']) and all(p in ps for p in r['work_packets']) for r in req))
check('owner_mapping',all(o['case_ids'] and o['work_packets'] and all(c in cs for c in o['case_ids']) and all(p in ps for p in o['work_packets']) for o in owners))
check('subpacket_mapping',all(s['parent_packet'] in ps and all(c in cs for c in s['case_ids']) for s in subs))
flat=[p for f in families for p in f['work_packets']]
check('family_partition',len(flat)==len(set(flat))==22 and set(flat)==set(ps))
visiting=set();seen=set()
def visit(k):
    if k in visiting:raise AssertionError('cycle '+k)
    if k in seen:return
    visiting.add(k)
    for d in ps[k]['depends_on']:visit(d)
    visiting.remove(k);seen.add(k)
for p in ps:visit(p)
check('packet_dag',len(seen)==22)
check('all_cases_owned',{c for p in packets for c in p['exit_case_ids']}==cs)
check('no_runtime_pass',all(c['erp_status']=='NOT_RUN' for c in cases) and all(o['runtime_status']=='NOT_RUN' for o in owners))
check('legacy_status_preserved',not any(r['status'] in ('PASS','INDEPENDENT_ACCEPTED') for r in req))
state=read('registries/current_state.json')
check('gates',state['cp6_gate']=='HOLD' and state['cp7_implementation']=='NOT_STARTED' and state['accepted_execution_base'] is None and state['production_go'] is False and state['messages_sent']==0 and state['product_mutations']==0)
check('wa_phase_explicit',all(c['runtime_phase']=='CP7C_LIVE_CP7_READINESS' for c in cases if c['id'] in [f'X{i:02}' for i in range(25,31)]))
m=read('contracts/model.oracles.json');level=Decimal(m['ses']['initial']);alpha=Decimal(m['ses']['alpha']);levels=[]
for value in m['ses']['observations']:
    level=alpha*Decimal(value)+(1-alpha)*level;levels.append(level)
check('ses_arithmetic',levels==list(map(Decimal,m['ses']['expected_levels'])) and level==Decimal(m['ses']['expected_next']))
p=m['promotion'];actual=list(map(Decimal,p['actual']))
mae=lambda xs:sum(abs(Decimal(a)-b) for a,b in zip(xs,actual))/len(actual)
bias=lambda xs:sum(Decimal(a)-b for a,b in zip(xs,actual))/len(actual)
check('promotion_arithmetic',mae(p['baseline'])==5 and mae(p['challenger'])==1 and bias(p['baseline'])==-5 and bias(p['challenger'])==-1 and not p['holdout_used_for_selection'])
check('cross_invoice_arithmetic',100+80-30-20==130 and (100-30)+(80-20)==130)
check('financial_report_arithmetic',375-225==150 and Decimal(150)/375==Decimal('.4') and 200+175==375)
check('intraday_counterexample',min(0,-5,0)==-5 and min(0,5,0)==0)
check('lost_sales_counterexample',max(0,0-5)+5==5 and max(0,5-0)==5)
for path in P.glob('*.md'):check('fences:'+path.name,len(re.findall(r'^```',path.read_text(),re.M))%2==0)
result={'framework_version':'CP7-BACKBONE-20260928-v2','scope':'OFFLINE_FRAMEWORK_SCHEMA_SEMANTIC_SAMPLES_AND_ARITHMETIC_ONLY',
        'status':'PREPARATION_VALIDATION_PASS','erp_runtime_verdict':'NOT_RUN','checks_count':len(checks),'checks':checks,
        'limitations':['Not a complete runtime semantic validator','No ERP/native/Auth/HTTP/browser tests','No scheduler/provider/delivery tested','Kernel example SES only; chosen kernels need independent vectors before P07 acceptance']}
(P/'verification/framework_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','limitations')}))
