"""Admit the actual failed-run canonical bytes before reusing financial4."""
from pathlib import Path,PurePosixPath
from hashlib import file_digest
import importlib.util,json,os,subprocess,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REPOSITORY='Hanjay6688/-erp-garment-ux'


def main():
    spec=importlib.util.spec_from_file_location('fetch_exact_actual_retained_permanent4',HERE/'retained4.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    receipt=m.receipt();p=m.typed()
    def api(path):return p.strict(subprocess.check_output(['gh','api','repos/'+REPOSITORY+'/'+path]))
    run=api('actions/runs/'+str(m.RUN))
    p.fields(run,dict(id=m.RUN,status='completed',conclusion='failure',run_attempt=1,head_sha=m.ORIGIN_HEAD),
        'EXACT_RETAINED_FAILED_RUN_NOT_REPLACED_BY_SUCCESS')
    job=api('actions/jobs/'+str(m.JOB))
    p.fields(job,dict(id=m.JOB,run_id=m.RUN,status='completed',conclusion='failure'),
        'EXACT_RETAINED_ORIGINAL_FAILED_OWNING_JOB')
    artifact=api('actions/artifacts/'+str(m.ARTIFACT));expected=m.ARCHIVE
    p.fields(artifact,dict(id=m.ARTIFACT,expired=False,size_in_bytes=expected['bytes'],
        digest='sha256:'+expected['sha256']),'EXACT_RETAINED_ORIGINAL_FULL_CANONICAL_ARTIFACT_API')
    p.fields(artifact['workflow_run'],dict(id=m.RUN,head_sha=m.ORIGIN_HEAD),'EXACT_RETAINED_ARCHIVE_ORIGIN')
    directory=Path(os.environ['RUNNER_TEMP'])/'permanent-retained23e';directory.mkdir(parents=True,exist_ok=True)
    archive=directory/'ORIGINAL_FAILED_CANONICAL.zip'
    if not archive.exists():
        partial=archive.with_suffix('.zip.partial')
        with partial.open('xb')as stream:
            subprocess.run(['gh','api','repos/'+REPOSITORY+'/actions/artifacts/'+str(m.ARTIFACT)+'/zip'],stdout=stream,check=True)
        with partial.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
        p.exact(dict(bytes=partial.stat().st_size,sha256=digest),{k:expected[k]for k in('bytes','sha256')},
            'EXACT_DOWNLOADED_FULL_RETAINED_CANONICAL')
        partial.rename(archive)
    with archive.open('rb')as stream:digest=file_digest(stream,'sha256').hexdigest()
    p.exact(dict(bytes=archive.stat().st_size,sha256=digest),{k:expected[k]for k in('bytes','sha256')},
        'EXACT_EXISTING_FULL_RETAINED_CANONICAL')
    with zipfile.ZipFile(archive)as z:
        names=z.namelist();p.exact(len(names),expected['members'],'ALL_RETAINED_CANONICAL_ORIGINAL_MEMBERS')
        p.exact(len(set(names)),len(names),'NO_RETAINED_CANONICAL_DUPLICATES')
        for name in names:
            path=PurePosixPath(name)
            if path.is_absolute()or'..'in path.parts or str(path)!=name:raise ValueError('RETAINED_ARCHIVE_UNSAFE_PATH')
        if z.testzip()is not None:raise ValueError('RETAINED_FULL_ORIGINAL_CRC_FAILURE')
        name='CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4.json'
        with z.open(name)as stream:original_digest=file_digest(stream,'sha256').hexdigest()
        p.exact(dict(bytes=z.getinfo(name).file_size,sha256=original_digest),receipt['originals'][name],
            'EXACT_ROOT_VALIDATED_ORIGINAL_STRICT_FINANCIAL4_BYTES')
    value=dict(status='EXACT_FAILED_CANONICAL_FINANCIAL4_ORIGINALS_ADMITTED_NOT_RERUN',
        root_receipt=m.ROOT_PIN,original_head=m.ORIGIN_HEAD,original_run_id=m.RUN,original_job_id=m.JOB,
        artifact_id=m.ARTIFACT,archive=expected,original_native=receipt['originals'][name],
        retained_Native_cases=4,actual_new_Native_cases=0,financial_groups_rerun=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        production_go=False,independent_acceptance=False)
    out=ROOT/'cp6-proof/t3/PERMANENT_RETAINED4_ORIGINAL_ADMISSION.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n')
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:stream.write('PERMANENT_RETAINED4_CANONICAL_ARCHIVE='+str(archive)+'\n')
    print(json.dumps(value));return value


if __name__=='__main__':main()
