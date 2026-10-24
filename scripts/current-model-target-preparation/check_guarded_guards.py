"""Local structural controls on a real prior full backup, never Native credit."""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,sys
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_current_model_target_installation as p
import cp7_current_model_target_recovery as recovery

path=Path(os.environ['CURRENT_FINANCE_USED_MANIFEST'])
raw=path.read_bytes();actual=json.loads(raw)
assert sha256(raw).hexdigest()=='7c6aa0e6a2a46ef1c4f47e549c8c208e5e071ed13be608130637b9ed79979593'
assert len(actual['catalog'])==22 and len(actual['data'])==686
results=[]
def refused(name,fn):
    try:fn()
    except ValueError as error:results.append(dict(id=name,status='PASS',refusal=str(error)))
    else:raise AssertionError('LOCAL_INVALID_STATE_WAS_ADMITTED: '+name)

p.admit_data(actual['data'],deepcopy(actual['data']))
results.append(dict(id='ALL_686_REAL_BACKUP_DATA_KEYS_UNCHANGED',status='PASS'))
for label,mutate in [
 ('MISSING_DATA_KEY',lambda d:d.pop(next(iter(d)))),
 ('UNKNOWN_NEW_TABLE',lambda d:d.update({'cp7_unknown.extra':[0,sha256(b'[]').hexdigest()]})),
 ('CHANGED_EXISTING_ROW_HASH',lambda d:d.__setitem__('erp.app_users',[999,'changed'])),
 ('CHANGED_EXISTING_SEQUENCE',lambda d:d.__setitem__('sequence:erp.audit_logs_id_seq',['999',True]))]:
    changed=deepcopy(actual['data']);mutate(changed);refused(label,lambda:p.admit_data(actual['data'],changed))

for name,module in p.STAGES:
    before=deepcopy(actual['catalog']);after=deepcopy(before)
    old={p.freshness.SIGNATURE}if name=='BASELINE_FRESHNESS'else set(p.target.render.originals())
    new=set()if name=='BASELINE_FRESHNESS'else set(p.target.FUNCTIONS)
    schemas=set()if name=='BASELINE_FRESHNESS'else set(p.target.SCHEMAS)
    assert old<=set(before['functions'])and not new&set(before['functions'])
    # Labelled structural delta only: real old metadata is retained, while the
    # body marker represents a declared replacement. No SQL/database execution.
    template=deepcopy(before['functions'][p.freshness.SIGNATURE])
    for key in old:
        after['functions'][key][0]='LOCAL_DECLARED_BODY_CONTROL:'+key
    for key in new:
        after['functions'][key]=deepcopy(template);after['functions'][key][0]='LOCAL_NEW_FUNCTION_CONTROL:'+key
    schema=deepcopy(next(iter(before['schemas'].values())))
    for key in schemas:after['schemas'][key]=deepcopy(schema)
    state=dict(catalog=module.own_catalog(after))
    p.admit_catalog(before,after,state,name)
    results.append(dict(id=name+'_EXACT_DECLARED_TRANSITION',status='PASS'))
    bad=deepcopy(after);bad.pop('functions');refused(name+'_MISSING_GROUP',lambda:p.admit_catalog(before,bad,state,name))
    bad=deepcopy(after);bad['functions']['public.unlisted()']=deepcopy(template)
    refused(name+'_EXTRA_PUBLIC_FUNCTION',lambda:p.admit_catalog(before,bad,state,name))
    bad=deepcopy(after);victim=next(k for k in before['functions']if k not in old|new)
    bad['functions'][victim][0]='UNDECLARED_BODY_CHANGE'
    refused(name+'_UNRELATED_FUNCTION_CHANGED',lambda:p.admit_catalog(before,bad,state,name))
    bad=deepcopy(after);key=next(iter(old));bad['functions'][key]=deepcopy(before['functions'][key])
    refused(name+'_MISSING_REPLACEMENT',lambda:p.admit_catalog(before,bad,state,name))
    bad=deepcopy(after);bad['schemas']['unlisted_schema']=deepcopy(schema)
    refused(name+'_EXTRA_SCHEMA',lambda:p.admit_catalog(before,bad,state,name))

assert recovery.installation is p and recovery.installation.predecessor is p.predecessor
assert p.target.verify_sources()and p.freshness.verify_sources()
report=dict(status='PASS',scope='LOCAL_STRUCTURAL_CONTROLS_ON_REAL_PRIOR_BACKUP_NOT_NATIVE',
    actual_backup_sha256=sha256(raw).hexdigest(),catalog_groups=22,real_data_keys=686,
    cases=results,count=len(results),new_stage_source_render_exact=True,current_target_replacements=20,current_target_private_functions=8,
    Native_runtime_credit=False,production_go=False,independent_acceptance=False)
Path(__file__).with_name('LOCAL_GUARDED_GUARDS17.json').write_text(json.dumps(report,indent=2)+'\n')
assert len(results)==17
print(json.dumps({k:v for k,v in report.items()if k!='cases'}))
