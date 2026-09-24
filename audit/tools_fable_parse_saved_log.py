#!/usr/bin/env python3
"""parse_saved_log.py <saved MCP result file> <name>: extract logs_content, save to SP/logs/auditor_<name>.log, dump JSON lines to SP/out/auditor_<name>.json and print a compact per-case view."""
import json,re,sys
SP='/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad'
fn,name=sys.argv[1],sys.argv[2]
txt=open(fn).read(); d=json.loads(txt[txt.find('{'):]); log=d['logs_content']
open(f'{SP}/logs/auditor_{name}.log','w').write(log)
objs=[]
for l in log.split('\n'):
    b=re.sub(r'^\S+\s','',l)
    if b.startswith('{'):
        try: objs.append(json.loads(b))
        except Exception: pass
json.dump(objs,open(f'{SP}/out/auditor_{name}.json','w'),default=str,indent=1)
for o in objs:
    if 'case' in o:
        extra={k:v for k,v in o.items() if k in ('checks','error','expected')}
        ob=o.get('observed') or {}
        brief={k:ob.get(k) for k in ('contract_shape','invoice_date','daily_move','reading_PHYSICAL_max_E_cutday_matches','cut_accepted','cut_error','late_invoice_accepted','late_invoice_error','receipt_physical_at','cut_at','conserved_by_today','new_journals','calls','control_before','control_after','who','role') if k in ob}
        print('CASE',o['case'],'|',o.get('status'),'| fbr',o.get('full_boundary_restored'))
        print('   ',json.dumps(extra,default=str)[:900])
        if brief: print('   obs:',json.dumps(brief,default=str)[:1400])
    elif o.get('auditor_phase'):
        print('FINAL',json.dumps({k:o.get(k) for k in ('status','auditor_cases','error','primary_unchanged')},default=str)[:400])
    elif 'auditor_scenario_sha256' in o: print('SHA',o)
