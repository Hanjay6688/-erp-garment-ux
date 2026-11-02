"""Fetch the exact failed-run canonical once, before any disposable database."""
from pathlib import Path,PurePosixPath
from hashlib import file_digest
import importlib.util,json,os,shutil,subprocess,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REPOSITORY='Hanjay6688/-erp-garment-ux'


def main():
    spec=importlib.util.spec_from_file_location('fetch_exact_ROOT_retained_FREE3',HERE/'retained3.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    receipt=m.receipt();p=m.typed()
    def api(path):return p.strict(subprocess.check_output(['gh','api','repos/'+REPOSITORY+'/'+path]))
    run=api('actions/runs/'+str(m.RUN));p.fields(run,dict(id=m.RUN,status='completed',conclusion='failure',
        run_attempt=1,head_sha=m.ORIGIN_HEAD),'FREE3_ORIGINAL_RUN_STAYS_FAILURE')
    job=api('actions/jobs/'+str(m.JOB));p.fields(job,dict(id=m.JOB,run_id=m.RUN,status='completed',
        conclusion='failure'),'FREE3_ORIGINAL_FAILED_OWNING_JOB')
    artifact=api('actions/artifacts/'+str(m.ARTIFACT));expected=m.ARCHIVE
    p.fields(artifact,dict(id=m.ARTIFACT,expired=False,size_in_bytes=expected['bytes'],
        digest='sha256:'+expected['sha256']),'FREE3_EXACT_COMPLETE_CANONICAL_ARTIFACT_API')
    p.fields(artifact['workflow_run'],dict(id=m.RUN,head_sha=m.ORIGIN_HEAD),'FREE3_EXACT_ARCHIVE_ORIGIN')
    directory=Path(os.environ['RUNNER_TEMP'])/'free3-retained-ad986';directory.mkdir(parents=True,exist_ok=True)
    archive=directory/'ORIGINAL_FAILED_CANONICAL.zip'
    if not archive.exists():
        partial=archive.with_suffix('.zip.partial')
        with partial.open('xb')as stream:
            subprocess.run(['gh','api','repos/'+REPOSITORY+'/actions/artifacts/'+str(m.ARTIFACT)+'/zip'],stdout=stream,check=True)
        with partial.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
        p.exact(dict(bytes=partial.stat().st_size,sha256=digest),{k:expected[k]for k in('bytes','sha256')},
            'FREE3_EXACT_DOWNLOADED_COMPLETE_CANONICAL');partial.rename(archive)
    with archive.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
    p.exact(dict(bytes=archive.stat().st_size,sha256=digest),{k:expected[k]for k in('bytes','sha256')},
        'FREE3_EXACT_EXISTING_COMPLETE_CANONICAL')
    out=ROOT/'cp6-proof/t3';out.mkdir(parents=True,exist_ok=True);destination=out/m.RAW
    with zipfile.ZipFile(archive)as z:
        names=z.namelist();p.exact(len(names),expected['members'],'FREE3_ALL_ORIGINAL_CANONICAL_MEMBERS')
        p.exact(len(set(names)),len(names),'FREE3_NO_DUPLICATE_CANONICAL_MEMBERS')
        for name in names:
            path=PurePosixPath(name)
            if path.is_absolute()or'..'in path.parts or str(path)!=name:raise ValueError('FREE3_CANONICAL_UNSAFE_PATH')
        if z.testzip()is not None:raise ValueError('FREE3_FULL_ORIGINAL_CANONICAL_CRC_FAILURE')
        with z.open(m.RAW)as stream:digest=file_digest(stream,'sha256').hexdigest()
        p.exact(dict(bytes=z.getinfo(m.RAW).file_size,sha256=digest),receipt['originals'][m.RAW],
            'FREE3_EXACT_ROOT_VALIDATED_STRICT_NATIVE3_BYTES')
        if not destination.exists():
            with z.open(m.RAW)as source,destination.open('xb')as stream:shutil.copyfileobj(source,stream)
        with destination.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
        p.exact(dict(bytes=destination.stat().st_size,sha256=digest),receipt['originals'][m.RAW],
            'FREE3_UNMODIFIED_RETAINED_NATIVE3_ORIGINAL_INSTALLED')
    value=dict(status='EXACT_FAILED_CANONICAL_FREE3_ORIGINALS_ADMITTED_NOT_RERUN',root_receipt=m.ROOT_PIN,
        original_head=m.ORIGIN_HEAD,original_run_id=m.RUN,original_job_id=m.JOB,artifact_id=m.ARTIFACT,archive=expected,
        original_native=receipt['originals'][m.RAW],retained_Native_cases=3,actual_new_Native_cases=0,
        financial_groups_rerun=False,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        production_go=False,independent_acceptance=False)
    target=out/'FREE3_RETAINED_ORIGINAL_ADMISSION.json'
    encoded=(json.dumps(value,indent=2)+'\n').encode()
    if target.exists():p.exact(target.read_bytes(),encoded,'FREE3_EXISTING_CANONICAL_ADMISSION_IMMUTABLE')
    else:target.write_bytes(encoded)
    print(json.dumps(value));return value


if __name__=='__main__':main()
