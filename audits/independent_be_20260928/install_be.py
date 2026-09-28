"""Install the frozen delivered package through BE. No old test suite is run."""
from pathlib import Path
import hashlib,json,os,sys,traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp6_t3_release_package import Applier,CLONE

out=ROOT/'audit-results';out.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_text())
report={'candidate':'6739a2f37939b4c76a5d064790d0aaba0049a7e8','scope':'Exact AC..BD package plus revised BE development installer; not release package qualification',
        'kind':'environment construction only; no inherited test verdict','files':[],'status':'BLOCKED'}
try:
    applier=Applier(CLONE,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    for f in manifest['files']:
        if f['key']=='BE':
            from audit_state import snapshot
            import psycopg
            (out/'independent-before-be.json').write_text(json.dumps(snapshot(),indent=2,default=str)+'\n')
            path=ROOT/'supabase/dev/cp6_be_t1_family.sql';data=path.read_bytes()
            with psycopg.connect(CLONE,autocommit=True) as c:c.execute(data.decode(),prepare=False)
            report['files'].append({'key':'BE','file':str(path.relative_to(ROOT)),'kind':'DEV_T1_NOT_RELEASE_PACKAGE','sha256':hashlib.sha256(data).hexdigest(),'status':'INSTALLED'})
            print('INSTALLED exact revised BE dev T1',flush=True)
            continue
        data=(ROOT/f['file']).read_bytes()
        actual=hashlib.sha256(data).hexdigest()
        assert actual==f['package_sha256'],('PACKAGE_IDENTITY_MISMATCH',f['key'])
        if f['key']=='BE':
            from audit_state import snapshot
            (out/'independent-before-be.json').write_text(json.dumps(snapshot(),indent=2,default=str)+'\n')
        applier.install({'stamp':f['stamp'],'name':f['name'],'closed':f['closed_admission']},data.decode())
        report['files'].append({'key':f['key'],'sha256':actual,'status':'INSTALLED'})
        print('INSTALLED',f['key'],actual,flush=True)
    assert len(report['files'])==29 and report['files'][-1]['key']=='BE'
    report['status']='READY_FOR_INDEPENDENT_TESTS'
except Exception as e:
    report['error']=str(e);report['traceback']=traceback.format_exc()
finally:
    (out/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
if report['status']!='READY_FOR_INDEPENDENT_TESTS':
    print(json.dumps(report,indent=2));raise SystemExit(1)
