"""Static inventory; reachability or textual mention does not establish semantic PASS."""
import pathlib,re,json,hashlib,collections
ROOT=pathlib.Path('.');OUT=ROOT/'audit/astra_cp17'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=[];rpc=[]
for p in sorted((ROOT/'src').rglob('*')):
 if p.suffix not in ('.ts','.tsx','.css') or '.test.' in p.name or p.name.endswith('.d.ts'):continue
 text=p.read_text();calls=re.findall(r'\.rpc\s*\(\s*[\'"]([^\'"]+)[\'"]',text)
 source.append(dict(path=str(p),sha256=sha(p),rpc_calls=sorted(set(calls)),audit_status='STATIC_OWNERSHIP_CHECKED; see packet evidence; no blanket line-by-line claim'))
 for name in sorted(set(calls)):rpc.append(dict(caller=str(p),rpc='public.'+name,role='COMMAND_CANDIDATE' if re.search('save|post|apply|prepare|publish|finish|claim|reverse|reopen|create|deactivate|set_',name)else'READER_OR_MIXED_CANDIDATE',classification='NAME_HEURISTIC_ONLY; runtime contracts decide mutability'))
packets=json.loads((ROOT/'docs/cp7/framework-v2/registries/work_packets.json').read_text())
requirements=json.loads((ROOT/'docs/cp7/framework-v2/registries/requirements.json').read_text())
links={
'P00':['CP1_G01','CP1_LEDGER_BYTE_CHECK','P00_FULL_catalogue'], 'P01':['own-money','own-plan','own-stage','legacy326/AS34/AR174/AT16/AU15'],
'P02':['own-stage','p19-report-v2','p19-ai-v2'], 'P03':['p18-fullcycle','cutting-model','pl-schedule','fabric-physical'], 'P04':['p18-fullcycle','pl-supply','pl-schedule'],
'P05':['pl5-history-yield','pl-model','own-plan'],'P06':['pl-supply','pl-model','own-plan'],'P07':['pl-model','own-plan'],'P08':['p19-plan-v2','own-plan'],
'P09':['f03-p09','supplier-credit','supplier-payment-correction','receipt-correction','SKN22'],'P10':['f03-p10','p18-fullcycle','fabric-physical','SKN22'],
'P11':['customer-refund','cash-installments','sales-return-correction','payment-correction','P11_XC2_carried','SKN22'],
'P12':['f03-p12','note-correction','PAY01-06','HPP01','SKN22'],'P13':['f03-p13','misc-correction','p19-report-v2','PAY06','SKN22'],
'P14':['pl-supply','pl-model','pl-schedule','netting','p19-plan-v2'],'P15':['p19-report-v2','own-stage','SKN22'],'P16':['p19-reminder-v2','rule-lifecycle','SKN22'],
'P17':['p19-ai-v2','own-stage'],'P18':['p18-fullcycle','SKN22','legacy_baseline_full_composition'],'P19':['p19-plan-v2','p19-report-v2','p19-reminder-v2','p19-ai-v2','k2-retention','k4-runner','k6-proof-runner'],
'P20':['current_Astra_report','Fable_exposure_register'],'P21':['p21-full-rehearsal','K3_XC2_carried']}
for p in packets:
 p['astra_evidence_groups']=links[p['id']]
 p['astra_disposition']='BLOCKED_FIN01' if p['id'] in ('P12','P13') else ('PARTIAL_PEER_REPORT_UNAVAILABLE' if p['id']=='P20' else ('REHEARSAL_ONLY_RELEASE_NOT_AUTHORIZED' if p['id']=='P21' else 'EVIDENCE_REVIEWED_WITH_REPORT_LIMITS'))
for req in requirements:
 req['astra_packet_evidence']={p:links.get(p,[])for p in req['work_packets']}
 req['astra_requirement_verdict']='NOT_INDIVIDUALLY_CERTIFIED; packet evidence does not prove every acceptance clause'
# Inventory public SQL declarations and relations from candidate files. These are textual,
# deliberately not claimed to be the installed catalogue (P00/run artifacts are authoritative).
declarations={};relations={}
for top in ['scripts/cp7-src','supabase/migrations']:
 for p in sorted((ROOT/top).rglob('*.sql')):
  text=p.read_text()
  for name in re.findall(r'(?i)create\s+(?:or\s+replace\s+)?function\s+(public\.[a-z_0-9]+)',text):declarations.setdefault(name,[]).append(str(p))
  for name in re.findall(r'(?i)\b(?:create\s+table\s+(?:if\s+not\s+exists\s+)?|from\s+|join\s+|update\s+|into\s+)((?:erp|cp7_[a-z_0-9]+)\.[a-z_0-9]+)',text):relations.setdefault(name,[]).append(str(p))
result=dict(candidate='0b7049d9203bac52b47a4c89f3e0d75646067a8f',requirements_count=len(requirements),packet_count=len(packets),runtime_source_file_count=len(source),caller_rpc_pairs=len(rpc),unique_frontend_rpc_names=len(set(x['rpc']for x in rpc)),feature_complete=False,audit_complete=False,production_go=False,meaning='False means no complete acceptance certification, not that all implementations are absent. Scope includes CP1-CP7; CP2 restore unverified and FIN01 blocks.',requirements=requirements,work_packets=packets,runtime_sources=source,frontend_rpc_ownership=rpc,public_sql_declaration_inventory=declarations,sql_relation_mentions=relations,inventory_limits=['Name-based role classification and SQL regex are discovery aids, not authoritative runtime dependency closure.','P00 installed catalogues and case Originals retain authoritative definitions, owners, ACLs, table membership and row hashes.','No claim all 271 requirement clauses or every function body individually certified.','Current hosted state, historical CP2 restore, live messaging, and Drive excluded or unavailable as stated in report.'])
(OUT/'FEATURE_INVENTORY.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if not isinstance(v,(list,dict))}))
