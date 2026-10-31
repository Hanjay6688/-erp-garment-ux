"""Fetch exact immutable inputs; never execute a writer while admitting them."""
from pathlib import Path
import base64,importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
REPO='Hanjay6688/-erp-garment-ux'

def load():
    spec=importlib.util.spec_from_file_location('joined_fetch_exact_parents',HERE/'parents.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def api(endpoint):
    return json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/'+endpoint]))

def main():
    module=load();spec=module.specification();directory=Path(os.environ['RUNNER_TEMP'])/'joined-exact-parents'
    directory.mkdir(exist_ok=True)
    for kind in module.HEADS:
        item=spec[kind];run=api('actions/runs/'+str(item['run_id']))
        module.fields(run,dict(head_sha=item['head'],status='completed',conclusion='success',run_attempt=1),kind+'_TERMINAL_RUN')
        artifacts=api('actions/runs/'+str(item['run_id'])+'/artifacts')['artifacts']
        selected=[row for row in artifacts if row['id']==item['artifact_id']]
        if len(selected)!=1:raise ValueError('JOIN_EXACT_ARTIFACT_REQUIRED:'+kind)
        module.fields(selected[0],dict(expired=False,size_in_bytes=item['archive']['bytes'],
            digest='sha256:'+item['archive']['sha256']),kind+'_API_ARCHIVE')
        receipt=item['root_receipt'];source=api('contents/'+receipt['source_path']+'?ref='+receipt['source_commit'])
        source_raw=base64.b64decode(source['content']);local=(HERE/receipt['path']).read_bytes()
        module.pinned(source_raw,{key:receipt[key]for key in('bytes','sha256')},kind+'_PUBLIC_ROOT_RECEIPT')
        if source_raw!=local:raise ValueError('JOIN_PUBLIC_ROOT_RECEIPT_DIFFERS:'+kind)
        path=directory/(kind+'.zip')
        if path.exists():raise ValueError('JOIN_FIRST_PARENT_DOWNLOAD_MUST_NOT_BE_OVERWRITTEN:'+kind)
        with path.open('xb')as output:
            subprocess.run(['gh','api','repos/'+REPO+'/actions/artifacts/'+str(item['artifact_id'])+'/zip'],stdout=output,check=True)
        os.environ['JOIN_'+kind+'_ORIGINAL']=str(path)
    proof=module.admitted()
    with open(os.environ['GITHUB_ENV'],'a')as env:
        for kind in module.HEADS:env.write('JOIN_'+kind+'_ORIGINAL='+os.environ['JOIN_'+kind+'_ORIGINAL']+'\n')
    print(json.dumps({kind:{key:row[key]for key in('status','head','run_id','artifact_id','fresh_composite_case_credit')}for kind,row in proof.items()}))

if __name__=='__main__':main()
