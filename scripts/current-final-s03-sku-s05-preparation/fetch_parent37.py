"""Read-only exact canonical joined37 prerequisite; never opens a database."""
from pathlib import Path,PurePosixPath
from hashlib import file_digest,sha256
import importlib.util,json,os,shutil,subprocess,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REPOSITORY='Hanjay6688/-erp-garment-ux'
MAIN='CP7_CURRENT_S03_SKU_S05_NATIVE31_BROWSER6.json'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def api(path):
    raw=subprocess.check_output(['gh','api','repos/'+REPOSITORY+'/'+path])
    return load('permanent_parent_API_strict_JSON',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py').strict(raw)


def digest(path):
    with path.open('rb')as stream:return file_digest(stream,'sha256').hexdigest()


def main():
    required=load('permanent_closed_actual_parent_before_any_fetch',HERE/'persistent_financial.py')
    if required.PARENT_RECEIPT is None:
        raise ValueError('PERMANENT_S05_EXACT_TERMINAL_JOIN37_INTAKE_PENDING')
    root_path=HERE/'JOIN37_ROOT_ACTUAL_INTAKE.json'
    receipt=required.qualified_receipt(root_path.read_bytes())
    run=api('actions/runs/'+str(receipt['run_id']))
    if(run['status']!='completed'or run['conclusion']!='success'or run['run_attempt']!=1
       or run['head_sha']!=required.PARENT_HEAD):
        raise ValueError('PERMANENT_S05_TERMINAL_EXACT_JOIN37_RUN_REQUIRED')
    job=api('actions/jobs/'+str(receipt['job_id']))
    if job['run_id']!=receipt['run_id']or job['status']!='completed'or job['conclusion']!='success':
        raise ValueError('PERMANENT_S05_EXACT_SUCCESSFUL_JOIN37_JOB_REQUIRED')
    metadata=api('actions/artifacts/'+str(receipt['artifact_id']));expected=receipt['archive']
    if(metadata['expired']is not False or metadata['size_in_bytes']!=expected['bytes']
       or metadata['digest']!='sha256:'+expected['sha256']
       or metadata['workflow_run']['id']!=receipt['run_id']
       or metadata['workflow_run']['head_sha']!=required.PARENT_HEAD):
        raise ValueError('PERMANENT_S05_CANONICAL_JOIN37_API_ARTIFACT_CHANGED')
    target=Path(os.environ['RUNNER_TEMP'])/'permanent-join37-parent';target.mkdir(parents=True,exist_ok=True)
    archive=target/'QUALIFIED_JOIN37.zip'
    if not archive.exists():
        partial=archive.with_suffix('.zip.partial')
        with partial.open('xb')as stream:
            subprocess.run(['gh','api','repos/'+REPOSITORY+'/actions/artifacts/'+str(receipt['artifact_id'])+'/zip'],
                stdout=stream,check=True)
        if partial.stat().st_size!=expected['bytes']or digest(partial)!=expected['sha256']:
            raise ValueError('PERMANENT_S05_CANONICAL_JOIN37_ARCHIVE_BYTES_CHANGED')
        partial.rename(archive)
    if archive.stat().st_size!=expected['bytes']or digest(archive)!=expected['sha256']:
        raise ValueError('PERMANENT_S05_EXISTING_CANONICAL_ARCHIVE_CHANGED')
    original=target/MAIN
    with zipfile.ZipFile(archive)as z:
        names=z.namelist()
        if len(names)!=expected['members']or len(set(names))!=len(names)or z.testzip()is not None:
            raise ValueError('PERMANENT_S05_CANONICAL_JOIN37_CRC_OR_MEMBERS_CHANGED')
        for name in names:
            path=PurePosixPath(name)
            if path.is_absolute()or'..'in path.parts or str(path)!=name:
                raise ValueError('PERMANENT_S05_CANONICAL_ARCHIVE_PATH_ESCAPE')
        if not original.exists():
            with z.open(MAIN)as source,original.open('xb')as output:shutil.copyfileobj(source,output,1024*1024)
    pin=receipt['originals'][MAIN]
    if original.stat().st_size!=pin['bytes']or digest(original)!=pin['sha256']:
        raise ValueError('PERMANENT_S05_CANONICAL_JOIN37_MAIN_ORIGINAL_CHANGED')
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:
        stream.write('PERMANENT_JOIN37_ROOT_INTAKE='+str(root_path)+'\n')
        stream.write('PERMANENT_JOIN37_CANONICAL_ARCHIVE='+str(archive)+'\n')
        stream.write('PERMANENT_JOIN37_MAIN='+str(original)+'\n')
    result=dict(status='EXACT_TERMINAL_JOIN37_CANONICAL_ORIGINALS_ADMITTED',head=required.PARENT_HEAD,
        run_id=receipt['run_id'],job_id=receipt['job_id'],artifact_id=receipt['artifact_id'],
        root_intake=required.PARENT_RECEIPT,archive=expected,main_original=pin,
        entire_qualified_financial_sources=receipt['qualified_financial_sources'],fresh_Native_credit=0,
        production_go=False,independent_acceptance=False)
    out=ROOT/'cp6-proof/t3/JOIN37_PARENT_ORIGINAL_ADMISSION.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
