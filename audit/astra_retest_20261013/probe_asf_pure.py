"""Independent ASF-F01 controls. Original four oracles are executed byte-identically."""
from pathlib import Path
from datetime import date
from copy import deepcopy
import os, sys, shutil, subprocess, json, importlib.util, io, contextlib, hashlib
ROOT=Path(__file__).resolve().parent
PRODUCT,OLD,OUT=map(lambda s:Path(s).resolve(),sys.argv[1:4])
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
def record(key,ok,observations):
    rows.append(dict(id=key,status='PASS' if ok else 'COUNTEREXAMPLE',observations=observations))
    print(json.dumps(rows[-1],default=str),flush=True)
for label,product,counts,exit_code in [('OLD_NEGATIVE',OLD,{'PASS':2,'COUNTEREXAMPLE':2},1),('NEW',PRODUCT,{'PASS':4,'COUNTEREXAMPLE':0},0)]:
    dest=OUT/label;dest.mkdir(exist_ok=True)
    script=dest/'original_asf_controls.py';shutil.copyfile(ROOT/'baseline/original_asf_controls.py',script)
    proc=subprocess.run([sys.executable,str(script),str(product)],capture_output=True,text=True)
    (dest/'first_execution.log').write_text(proc.stdout+'\n'+proc.stderr)
    raw=json.loads((dest/'evidence/ASF_BUSINESS_DAY.json').read_text())
    record('ASF-R01-ORIGINAL-'+label,proc.returncode==exit_code and raw['counts']==counts,
           dict(actual_product_sha=subprocess.check_output(['git','-C',str(product),'rev-parse','HEAD'],text=True).strip(),original_script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),exit_code=proc.returncode,counts=raw['counts'],module_sha256=raw['module_sha256'],metadata_note='The byte-identical original report hardcodes the prior candidate SHA; actual binding is this receipt and module hash.'))
spec=importlib.util.spec_from_file_location('asf_current',PRODUCT/'scripts/cp6_auditor_business_day.py')
bd=importlib.util.module_from_spec(spec);spec.loader.exec_module(bd)
D0,D1=date(2026,10,12),date(2026,10,13)
def guarded(status='PASS',**kwargs):
    r=dict(status=status,**kwargs);bd.guard(r,D0,D0,D1);return r
def group(rs):return dict(cases=deepcopy(rs),complete_boundary_restored=True,database_remaining=0,cleanup_failures=[],missing=[])
def drive(first,second=None,tag='ASTRA_ASF_EXTRA',emit=False):
    attempts=[];saved=[];output=io.StringIO()
    def once():
        attempts.append(len(attempts)+1);return deepcopy(first if len(attempts)==1 else (second or first))
    with contextlib.redirect_stdout(output):res=bd.with_retry(tag,once,lambda r:r['cases'],lambda r:saved.append(deepcopy(r)))
    if emit:print(output.getvalue(),end='',flush=True)
    return dict(attempts=len(attempts),result=res,saved=saved,stdout=output.getvalue())
for status in ['FAIL','COUNTEREXAMPLE','INCOMPLETE']:
    first=group({'OTHER_DAY_PASS':guarded(),'DATE_INDEPENDENT':guarded(status,error='ASTRA_NEGATIVE_CONTROL')})
    o=drive(first,group({'SECOND':dict(status='PASS')}),emit=status=='FAIL')
    record('ASF-R02-MIXED-'+status,o['attempts']==1 and o['result']==first,o)
for key,value in [('error','ASTRA_SETUP_ERROR'),('missing',['MISSING']),('database_remaining',1),('cleanup_failures',['COPY']),('complete_boundary_restored',False)]:
    first=group({'ROLLED_PASS':guarded()});first[key]=value;o=drive(first)
    record('ASF-R03-GROUP-'+key,o['attempts']==1 and o['result']==first,o)
for key,value in [('harness_check_failed',True),('status_outside_vocabulary','WRITER_PASS')]:
    r=guarded();r[key]=value;first=group({'BAD_ROW':r});o=drive(first)
    record('ASF-R04-ROW-'+key,o['attempts']==1 and o['result']==first,o)
first=group({'PASS_WITH_UNRELATED_ERROR':guarded(error='ASTRA_REAL_ASSERTION')});o=drive(first)
record('ASF-R05-PREEXISTING-ERROR',o['attempts']==1 and o['result']==first,o)
first=group({'A':guarded()});o=drive(first,first,emit=True)
record('ASF-R06-SECOND-ROLLOVER-NO-THIRD',o['attempts']==2 and o['result']['cases']['A']['status']=='INCOMPLETE' and o['saved']==[first] and o['result']['business_day_first_attempt']==first,o)
second=group({'A':dict(status='FAIL',error='ASTRA_SECOND_FAILURE')});o=drive(first,second)
record('ASF-R07-SECOND-FAILURE-PRESERVED',o['attempts']==2 and o['result']['cases']['A']==second['cases']['A'] and o['result']['business_day_first_attempt']==first,o)
old_env=os.environ.get('GITHUB_ACTIONS')
os.environ['GITHUB_ACTIONS']='true';buf=io.StringIO()
with contextlib.redirect_stdout(buf):bd.annotate('KEPT_FIRST_RESULT','a%\r\nb',['z\nx'])
record('ASF-R08-ANNOTATION-ESCAPING',buf.getvalue()=='::warning title=AUDITOR_BUSINESS_DAY_KEPT_FIRST_RESULT::group=a%25%0D%0Ab rolled_cases=z%0Ax\n',dict(stdout=buf.getvalue()))
os.environ['GITHUB_ACTIONS']='false';buf=io.StringIO()
with contextlib.redirect_stdout(buf):bd.annotate('KEPT_FIRST_RESULT','outside',['x'])
record('ASF-R09-NO-ANNOTATION-OUTSIDE-ACTIONS',buf.getvalue()=='',dict(stdout=buf.getvalue()))
if old_env is None:os.environ.pop('GITHUB_ACTIONS',None)
else:os.environ['GITHUB_ACTIONS']=old_env
report=dict(product_sha=subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),cases=rows,evidence_origin='INDEPENDENT_TOOL_RUNTIME',oracle_origin='ASTRA_CONTRACT',fixture_origin='ASTRA_SYNTHETIC_FAILURES',production_go=False)
report['counts']={s:sum(r['status']==s for r in rows) for s in ['PASS','COUNTEREXAMPLE']}
report['status']='PASS' if report['counts']['COUNTEREXAMPLE']==0 else 'COUNTEREXAMPLE'
(OUT/'ASF_PURE_REPORT.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print(json.dumps({k:report[k] for k in ['status','counts']}));sys.exit(0 if report['status']=='PASS' else 1)
