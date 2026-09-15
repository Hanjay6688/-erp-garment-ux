#!/usr/bin/env python3
"""Verify and reuse completed Native5 AD schedules after a comparator-only repair."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,stat,subprocess,zipfile
import cp6_v2620ad_runtime as runtime

SOURCE_HEAD='24ad7483ee594a7172e55c642f396208e5231f56'
SOURCE_TREE='a7cce3d39f3bc3619f38936f3fb026115f4e501c'
SOURCE_RUN=34967943841
ARTIFACT=10396157668
ZIP_BYTES=49339599
ZIP_SHA='9f98c8cd767c67017679dc8bd1e26afa30f09ea34c8d719617c8c84824f6c705'
MANIFEST_SHA='6676986e12aff119ec415900382c3bd5c9f954e2037d772e078b01dc4d8e1273'
PREFIX='AD_MAINTENANCE_ROLLBACK/'
ALLOWED_REPAIR={
  '.github/workflows/cp6-ac-independent-audit.yml',
  '.github/workflows/cp6-full-schema-validation.yml',
  'docs/cp6-ad-competition-handoff.md',
  'scripts/cp6_v2620ad_rollback_guards.py',
  'scripts/cp6_v2620ad_reuse_matrix.py',
  'scripts/cp6_v2620ad_proof.py',
}

def sha(data):return hashlib.sha256(data).hexdigest()

def validate_manifest(data):
    if sha(data)!=MANIFEST_SHA:raise AssertionError('AD_REUSE_MANIFEST_PIN_MISMATCH')
    m=json.loads(data)
    assert m['status']=='PASS' and m['head']==SOURCE_HEAD and m['source_object_count']==274
    assert m['expected_case_count']==m['completed_case_count']==len(m['cases'])==20
    expected={(op,mode) for op in ('SALE','RETURN','CONVERSION','REPORT','FK_SYNC')
        for mode in ('WRITER_FIRST','ADMISSION_FIRST','WRITER_ABORT','DRAIN_TIMEOUT')}
    assert {(c['operation'],c['mode']) for c in m['cases']}==expected
    for c in m['cases']:
        assert c['status']=='PASS' and c['target']=='AD' and c['remaining_clone_databases']==0
        assert c['migration_sha256']==sha(runtime.MIGRATION.read_bytes())
        assert c['rollback_sha256']==sha(runtime.ROLLBACK.read_bytes())
    return m

def run():
    head,tree=runtime.verify_audit_source()
    subprocess.run(['git','merge-base','--is-ancestor',SOURCE_HEAD,'HEAD'],check=True)
    assert subprocess.check_output(['git','rev-parse',SOURCE_HEAD+'^{tree}'],text=True).strip()==SOURCE_TREE
    changes=set(subprocess.check_output(['git','diff','--name-only',SOURCE_HEAD,'HEAD'],text=True).splitlines())
    if not changes or not changes.issubset(ALLOWED_REPAIR):raise AssertionError('AD_REUSE_UNQUALIFIED_SOURCE_DELTA:'+repr(sorted(changes)))
    # All other repository paths, including SQL, runtime, family oracle, matrix,
    # executor, fixtures and every imported helper, are therefore byte-identical.
    meta=json.loads(subprocess.check_output(['gh','api',f'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{ARTIFACT}'],text=True))
    assert meta['id']==ARTIFACT and meta['size_in_bytes']==ZIP_BYTES and meta['digest']=='sha256:'+ZIP_SHA
    assert meta['workflow_run']['id']==SOURCE_RUN and meta['workflow_run']['head_sha']==SOURCE_HEAD and not meta['expired']
    archive=Path(os.environ['RUNNER_TEMP'])/'ad-native5-completed-matrix.zip'
    with archive.open('wb') as f:
        subprocess.run(['gh','api',f'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{ARTIFACT}/zip'],stdout=f,check=True)
    assert archive.stat().st_size==ZIP_BYTES and sha(archive.read_bytes())==ZIP_SHA
    root=Path('cp6-proof');target=root/PREFIX
    if target.exists():raise AssertionError('AD_REUSE_DESTINATION_NOT_EMPTY')
    files={}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        manifest=validate_manifest(z.read(PREFIX+'manifest.json'))
        for info in z.infolist():
            if not info.filename.startswith(PREFIX) or info.is_dir():continue
            relative=PurePosixPath(info.filename)
            assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in info.filename
            mode=info.external_attr>>16
            assert not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0,stat.S_IFREG))
            data=z.read(info);destination=root/relative
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            files[info.filename]={'bytes':len(data),'sha256':sha(data)}
    assert len(files)==241 and sum(p['bytes'] for p in files.values())==339586090
    result={'status':'REUSED_VERIFIED_NATIVE5','source_run':SOURCE_RUN,'source_head':SOURCE_HEAD,'source_tree':SOURCE_TREE,
      'consumer_head':head,'consumer_tree':tree,'artifact_id':ARTIFACT,'artifact_bytes':ZIP_BYTES,'artifact_sha256':ZIP_SHA,
      'manifest_sha256':MANIFEST_SHA,'source_run_conclusion':'failure','completed_matrix_status':'PASS',
      'source_run_failure':'Final whole-boundary comparator after all 20 schedules completed; retained as failed.',
      'cases':manifest['completed_case_count'],'reexecuted':False,'allowed_comparator_harness_delta':sorted(changes),
      'all_other_repository_paths_identical':True,'payload_files':files,'production_go':False}
    (root/'AD_MATRIX_REUSE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='payload_files'}));return result

if __name__=='__main__':run()
