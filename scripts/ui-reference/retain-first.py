"""Verify first Original without reclassifying its failed result."""
import hashlib,json,sys,zipfile
from pathlib import Path
archive=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
assert archive.stat().st_size==51250492
assert hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()=='8a6b2fd7c6c504b0d9686834f57e84dcac6c9c11a02c99d176d9a01f6436e3e0'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
    first=json.loads(z.read('UI_FAMILY_CAPTURE.json'))
    assert first['after_head']=='402594251803b23a7d244de0d9cc03c98ac81759' and first['status']=='INCOMPLETE'
    assert first['preview_children_reaped'] and not first['cleanup_errors']
    assert len(first['variants'])==263
    for v in first['variants']:
        raw=z.read(v['screenshot']['name'])
        assert len(raw)==v['screenshot']['bytes'] and hashlib.sha256(raw).hexdigest()==v['screenshot']['sha256']
    route_ids={s['id'] for s in json.loads(Path('scripts/ui-reference/FAMILIES.json').read_text())['surfaces']}
    dialog_ids={'mandor-'+s for s in ['ready','long','empty','loading','error','stale','approved','pending']}
    invalid_desktop={'bs-rework','admin-settings','stock-adjustment','brand-conversion'}
    retained=[v for v in first['variants'] if v['variant']=='before' or (v['variant']=='after' and ((v['width']==1440 and v['surface'] in route_ids-invalid_desktop) or v['surface'] in dialog_ids))]
    assert len(retained)==114
    for v in retained:v['retained_from']='402594251803b23a7d244de0d9cc03c98ac81759'
    result={'contract':'cp7.B.verified-retained-original.v1','first_source':first['after_head'],'first_status':first['status'],'first_run':41608730540,'first_job':125824983279,'first_artifact':13218512902,'archive_bytes':archive.stat().st_size,'archive_sha256':'8a6b2fd7c6c504b0d9686834f57e84dcac6c9c11a02c99d176d9a01f6436e3e0','verified_first_views':263,'retained_count':114,'retained_variants':retained,'note':'Retained pictures refer to the exact first Original. Eight nested loading captures are not accepted as loaded inventory pages. First failure remains unchanged.'}
    (out/'RETAINED_FIRST.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_original':True,'retained':len(retained),'first_status':first['status']}))
