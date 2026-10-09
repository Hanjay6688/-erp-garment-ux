"""Audit orchestration only; candidate and inherited probes remain byte-identical."""
import copy,pathlib,yaml
root=pathlib.Path(__file__).resolve().parents[2]
base=yaml.safe_load((root/'.github/workflows/claude-p19-transport.yml').read_text())
# PyYAML YAML1.1 treats 'on' as bool unless quoted. Normalize deliberately.
base.pop(True,None)
base['name']='Astra P20 pinned independent regression rerun'
base['on']={'push':{'branches':['audit/astra-p20-2e605bb7-20261009'],'paths':['.github/workflows/astra-p20-regression.yml','audit/astra_p20/REGRESSION_START']},'workflow_dispatch':{}}
base['concurrency']={'group':'astra-p20-regression-${{ github.run_id }}','cancel-in-progress':False}
j=base['jobs']['phase'];j['strategy']['max-parallel']=6
entries=[]
for file in ['claude-p19-transport','claude-p08-physical','claude-pl-native','claude-p18-fabric-rule','claude-p21-rehearsal']:
 d=yaml.safe_load((root/'.github/workflows'/f'{file}.yml').read_text())
 for item in d['jobs']['phase']['strategy']['matrix']['include']:
  item=dict(item);item['suite']=item.get('suite') or item['artifact'];item['args']='';item.pop('name',None);item.pop('artifact',None)
  entries.append(item)
for flag in ['--roster','--payroll-review','--attendance-write']:
 entries.append({'suite':'payroll'+flag,'probe':'cp7_p12_nota_probe.py','args':flag,'timeout':180})
for stem in ['p13_finance','p18_full_cycle','note_correction','supplier_payment_correction','supplier_payment_create','receipt_correction']:
 entries.append({'suite':stem,'probe':'cp7_'+stem+'_probe.py','args':'','timeout':180})
j['strategy']['matrix']={'include':entries}
steps=j['steps']
for s in steps:
 if s.get('with',{}).get('path')=='auditor':s['with']['ref']='2e605bb7d9b6b7903919b8df2be1443f1740140b'
 if s.get('name')=='Qualify the declared Native suite':
  s['name']='Independently rerun unchanged writer cases on pinned product'
  s['run']='python "../auditor/scripts/${{ matrix.probe }}" ${{ matrix.args }}'
 if 'upload-artifact@' in s.get('uses',''):
  s['with']['name']='astra-p20-${{ matrix.suite }}'+('-json' if 'complete-json' in s['with']['name'] else '-raw')
steps.insert(2,{'uses':'actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683','with':{'path':'control','fetch-depth':1,'persist-credentials':False}})
check={'name':'Prove pinned product and record evidence origins','working-directory':'auditor','shell':'bash','run':'''set -euo pipefail
test "$(git rev-parse HEAD)" = 2e605bb7d9b6b7903919b8df2be1443f1740140b
test "$(git rev-parse HEAD^{tree})" = 51935efb12c035496848e2a85590aa18a3ed3d76
git diff --exit-code HEAD --
mkdir -p cp6-proof/t3
cp ../control/audit/astra_p20/SOURCE_RECEIPT.json cp6-proof/t3/ASTRA_SOURCE_RECEIPT.json
python - <<'PYIN'
import json,os,subprocess,pathlib
p=pathlib.Path('cp6-proof/t3/ASTRA_EXECUTION_ORIGIN.json')
p.write_text(json.dumps(dict(evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='WRITER_UNCHANGED',fixture_origin='WRITER_UNCHANGED',product_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),audit_workflow_sha=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],production_go=False),indent=2)+'\\n')
PYIN'''}
idx=next(i for i,s in enumerate(steps) if s.get('name')=='Install pinned disposable runtime');steps.insert(idx,check)
idx=next(i for i,s in enumerate(steps) if s.get('name')=='Remove disposable database')
steps.insert(idx,{'name':'Assert candidate stayed byte-identical','if':'always()','working-directory':'auditor','run':'git diff --exit-code HEAD --'})
# Preserve code layout for review; no interpolation of user-supplied commands.
p=root/'.github/workflows/astra-p20-regression.yml';p.write_text(yaml.safe_dump(base,sort_keys=False,width=110))
assert len(entries)==33,len(entries)
print({'jobs':len(entries),'max_parallel':j['strategy']['max-parallel'],'product_ref':'2e605bb7','workflow':str(p)})
