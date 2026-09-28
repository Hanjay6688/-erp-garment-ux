#!/usr/bin/env python3
"""Validate preparation artifacts only. Never connects to ERP/network or marks ERP cases PASS.
Run: python3 verification/validate_framework.py
Dependency for JSON Schema: jsonschema==4.25.1 (isolated validation environment).
"""
from pathlib import Path
from decimal import Decimal
import json,re,hashlib,collections,copy
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name,ok,detail):
 checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail))
 if not ok:raise AssertionError(name+': '+str(detail))
def read(p):return json.loads((ROOT/p).read_text())
req=read('registries/requirements.json');packs=read('registries/work_packets.json');cases=read('registries/cases.json')
rs={r['id']:r for r in req};ps={p['id']:p for p in packs};cs={c['id']:c for c in cases}
expected={'ACC':39,'ALL':22,'AUD':33,'BR':40,'CP7':35,'CROSS':6,'LAU':36,'RMD':36,'UX32':12,'WIP':12}
actual=dict(collections.Counter(r['id'].split('-')[0] for r in req))
check('source_requirement_counts',actual==expected,actual)
check('unique_ids',len(rs)==len(req) and len(ps)==len(packs) and len(cs)==len(cases),dict(requirements=len(req),packets=len(packs),case_contracts=len(cases)))
for r in req:
 check('requirement_mapping:'+r['id'],bool(r['work_packets']) and bool(r['case_ids']) and all(x in ps for x in r['work_packets']) and all(x in cs for x in r['case_ids']) and bool(r['scenario']) and bool(r['expected']) and r['source_line']>0,'source, owner, test and expected filled')
check('erp_not_run',all(c['erp_status']=='NOT_RUN' for c in cases) and not any(r['status'] in ('PASS','INDEPENDENT_ACCEPTED') for r in req),'No runtime acceptance fabricated')
check('scope_optional_guard',rs['BR-T27']['scope']=='OPTIONAL_NOT_SELECTED','No vendor scorecard gate added')
check('future_gate_preserved',rs['AUD-G10']['scope']=='CP7.5_FUTURE' and rs['AUD-G11']['scope']=='CP7C_FUTURE' and rs['AUD-G12']['scope']=='CP8_FUTURE','Checkpoint sequence retained')
check('inherited_c6_stays_cp6',all(r['scope']=='CP6_INHERITED' for r in req if r['id'].startswith(('ALL-','ACC-','LAU-'))),'ALL22/ACC39/LAU36 not silently deferred')
visiting=set();seen=set();order=[]
def visit(x):
 if x in visiting:raise AssertionError('Cycle at '+x)
 if x in seen:return
 visiting.add(x)
 for d in ps[x]['depends_on']:
  if d not in ps:raise AssertionError('Missing dependency '+d)
  visit(d)
 visiting.remove(x);seen.add(x);order.append(x)
for p in ps:visit(p)
check('acyclic_work_packets',len(order)==22,order)
check('all_packet_exit_cases',all(all(c in cs for c in p['exit_case_ids']) for p in packs),'All work packets reference real case contracts')
check('all_cases_used',set(cs).issubset({c for p in packs for c in p['exit_case_ids']}),sorted(set(cs)-{c for p in packs for c in p['exit_case_ids']}))
check('core_dependency_order',all(order.index(a)<order.index(b) for a,b in zip(['P02','P03','P04','P05','P06','P07','P08','P14','P17'],['P03','P04','P05','P06','P07','P08','P14','P17','P18'])),'A-B-C-D-E-F-G retained')

schema=read('contracts/analysis.schema.json');example=read('contracts/analysis.example.json')
Draft202012Validator.check_schema(schema)
v=Draft202012Validator(schema,format_checker=FormatChecker())
v.validate(example);check('example_schema_valid',True,'Typed synthetic O02 example conforms')
for label,mutate in [
 ('missing_quantity',lambda x:x['recommendations'][0].pop('actual_fg')),
 ('unknown_disguised_as_zero',lambda x:x['recommendations'][0].update(actual_fg=dict(state='UNKNOWN',value='0',unit='PCS',reason='missing',refs=[]))),
 ('untyped_extra',lambda x:x.update(service_role_secret='forbidden-test-canary')),
 ('bad_decimal',lambda x:x['recommendations'][0]['actual_fg'].update(value='NaN'))]:
 y=copy.deepcopy(example);mutate(y)
 check('schema_rejects:'+label,bool(list(v.iter_errors(y))),'Malformed data is rejected; this is a contract check, not ERP parser execution')

for src in example['sources']:
 check('sample_capacity:'+src['source_key'],Decimal(src['allocated']['value'])<=Decimal(src['eligible_projected']['value'])<=Decimal(src['physical_remaining']['value']),'Allocated <= eligible <= physical')
check('sample_no_fake_feasible',example['financial_readiness']=='BLOCKED' and example['quality']['capacity']=='UNKNOWN' and 'FEASIBILITY_NOT_PROVEN' in example['recommendations'][0]['reason_codes'],'Complete run is not final financial/feasible status')
known={x['code'] for x in read('contracts/reasons.json')}
check('reason_references',all(c in known for r in example['recommendations'] for c in r['reason_codes']) and all(a['primary_reason'] in known for a in example['actions']),'Reasons use the shared catalog')

def timeline(arrival):
 bal=18;out=[]
 for d in range(1,11):
  bal+=(12 if d==arrival else 0)+(10 if d==6 else 0)+(8 if d==7 else 0)-4;out.append(bal)
 return out
check('O01_netting',48-18-12==18 and 48-18-12-10==8,'Base18 conditional8')
check('O02_timeline',timeline(3)==[14,10,18,14,10,16,20,16,12,8] and [int(x['balance_end']) for x in example['timeline']]==timeline(3),'Target48, terminal buffer8 not double consumed')
check('O03_early_gap',timeline(8)==[14,10,6,2,-2,4,8,16,12,8],'Day5 shortage2 retained')
check('O04_shared_source',42+18==60 and 30-18==12,'Two needs share one60 source')
check('O06_draft_once',100-24-20==56,'No second reserve subtraction')
check('O07_size_gap',max(0,20-5)==15 and 25+5==10+20,'Total sufficient but L still short15')
check('O09_remaining_material',100-60==40 and 100-60-20==20,'Issued quantity alone cannot prove these operands')
check('O13_metric_math',(Decimal(1200)-1000)/1000==Decimal('.2') and Decimal('.24')-Decimal('.27')==Decimal('-.03'),'20 percent growth and minus3pp')
check('O14_cash_transfer',1000-1000+300-200==100,'Internal transfer net0')
check('O15_lineage',20+10+10+40==80 and 80+15+5==100,'Physical total100')
check('O16_capacity',30+6==36 and 30-6==24 and 40-36==4,'Feasible36 unresolved24 unused4')
check('O18_cost_conservation',sum(map(Decimal,['5.62','3.38','2.25']))==Decimal('11.25') and sum(map(Decimal,['7.50','4.50','3.00']))==Decimal('15.00'),'Inherited rounding vector conserved; not a new engine test')

def sem(x):
 y=copy.deepcopy(x);y.pop('run_id',None);y.pop('semantic_hash',None);y['snapshot'].pop('snapshot_id',None);y['snapshot'].pop('generated_at',None)
 return hashlib.sha256(json.dumps(y,sort_keys=True,separators=(',',':')).encode()).hexdigest()
check('sample_semantic_hash',sem(example)==example['semantic_hash'],'Hash matches declared example canonicalization')
other=copy.deepcopy(example);other['run_id']='fixture-run2';other['snapshot']['generated_at']='2026-10-02T00:01:00+07:00'
check('sample_hash_ignores_generation_meta',sem(other)==sem(example),'Business chronology remains included')
other['snapshot']['effective_as_of']='2026-10-01T23:59:59+07:00'
check('sample_hash_keeps_business_time',sem(other)!=sem(example),'Effective chronology affects semantic identity')

state=read('registries/current_state.json')
check('no_implementation_or_go',state['cp7_implementation']=='NOT_STARTED' and state['cp6_gate']=='HOLD' and not state['production_go'] and state['product_mutations']==0 and state['hosted_mutations']==0,'Preparation preserves gates')
for path in ROOT.rglob('*.md'):
 content=path.read_text()
 check('balanced_code_fences:'+path.name,len(re.findall(r'^```',content,re.M))%2==0,'Fences paired')
 # Only check actual Markdown local links, not inline source paths or file-tree proposals.
 for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',content):
  if link.startswith(('http:','https:','#','sandbox:')):continue
  check('local_link:'+path.name+':'+link,(path.parent/link.split('#')[0]).exists(),'Linked file exists')
report=dict(status='PREPARATION_VALIDATION_PASS',scope='DOCUMENTS_REGISTRIES_SCHEMA_SYNTHETIC_ARITHMETIC_ONLY',erp_runtime_verdict='NOT_RUN',
 requirement_groups=len(req),case_contracts=len(cases),work_packets=len(packs),check_count=len(checks),checks=checks)
(ROOT/'verification/framework_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in report if k!='checks'},ensure_ascii=False))
