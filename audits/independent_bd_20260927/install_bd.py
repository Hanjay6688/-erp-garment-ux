"""Install the frozen delivered package through BD. No old test suite is run."""
from pathlib import Path
import hashlib,json,os,sys,traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp6_t3_release_package import Applier,CLONE

out=ROOT/'audit-results';out.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_text())
report={'candidate':'08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec','scope':'AC..BD; BE excluded explicitly',
        'kind':'environment construction only; no inherited test verdict','files':[],'status':'BLOCKED'}
try:
    applier=Applier(CLONE,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    for f in manifest['files']:
        if f['key']=='BE':break
        data=(ROOT/f['file']).read_bytes()
        actual=hashlib.sha256(data).hexdigest()
        assert actual==f['package_sha256'],('PACKAGE_IDENTITY_MISMATCH',f['key'])
        applier.install({'stamp':f['stamp'],'name':f['name'],'closed':f['closed_admission']},data.decode())
        report['files'].append({'key':f['key'],'sha256':actual,'status':'INSTALLED'})
        print('INSTALLED',f['key'],actual,flush=True)
    assert len(report['files'])==28 and report['files'][-1]['key']=='BD'
    report['status']='READY_FOR_INDEPENDENT_TESTS'
except Exception as e:
    report['error']=str(e);report['traceback']=traceback.format_exc()
finally:
    (out/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
if report['status']!='READY_FOR_INDEPENDENT_TESTS':
    print(json.dumps(report,indent=2));raise SystemExit(1)
