import hashlib,json,sys,zipfile
from pathlib import Path
archive=Path(sys.argv[1]);out=Path(sys.argv[2]);previous=json.loads((out/'RETAINED_REVIEW.json').read_text());key=lambda v:f"{v['variant']}/{v['surface']}/{v['width']}";old={key(v):v for v in previous['retained_variants']}
assert archive.stat().st_size==4441630 and hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()=='29b5b1ec93aebe1181cf961efd1369decb9f4eb42d9ad8d7592c09c6c5ce1aec'
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
 prior=json.loads(z.read('UI_FAMILY_POLISH_CAPTURE.json'));assert prior['after_head']=='e8e27293be3c03c67b82648d0328e3b3282d9d14' and prior['exact_coverage']['actual']==326
 assert not prior['failures'] and not prior['console_errors'] and not prior['cleanup_errors'] and prior['preview_children_reaped']
 for v in prior['variants']:
  if 'retained_from' in v:assert v==old[key(v)]
  else:
   raw=z.read(v['screenshot']['name']);assert len(raw)==v['screenshot']['bytes'] and hashlib.sha256(raw).hexdigest()==v['screenshot']['sha256']
 changed={'after/stock-card/320','after/stock-filter-open/320','after/movements-vivo-expanded/320','after/movements-vivo-expanded/768'}
 retained=[v for v in prior['variants'] if key(v) not in changed];assert len(retained)==322
 for v in retained:v.setdefault('retained_from',prior['after_head'])
 result={'first_source':prior['after_head'],'first_run':41615213976,'first_artifact':13221695309,'archive_sha256':'29b5b1ec93aebe1181cf961efd1369decb9f4eb42d9ad8d7592c09c6c5ce1aec','retained_count':322,'retained_variants':retained,'navigation':prior['navigation'],'desktop_console_smoke':prior['desktop_console_smoke'],'changed_views':sorted(changed),'new_supplemental_views':2,'note':'Prior CI success remains success. Two expanded pictures are superseded for a visual finding; four new view identities/controls are retaken. Final acceptance awaits current review.'};(out/'RETAINED_DETAILS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_original_chain':True,'retained':322,'replacement':4,'new_expanded_widths':2}))
