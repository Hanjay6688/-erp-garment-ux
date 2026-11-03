"""Retain only unchanged accepted view identities; verify both source Originals."""
import hashlib,json,sys,zipfile
from pathlib import Path
archive=Path(sys.argv[1]);out=Path(sys.argv[2]);first=json.loads((out/'RETAINED_FIRST.json').read_text())
assert archive.stat().st_size==38227206
assert hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()=='e646b9cf6e4115e5fb4a971b5bc067099b15cd1a5b1df41b027c319b6578e762'
key=lambda v:f"{v['variant']}/{v['surface']}/{v['width']}"
first_map={key(v):v for v in first['retained_variants']}
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
 prior=json.loads(z.read('UI_FAMILY_REVIEW_CAPTURE.json'))
 assert prior['after_head']=='de7098079a1aa06dd36b393f1ee3042d459d233d'
 assert prior['status']=='CAPTURED_FOR_VISUAL_REVIEW_NOT_BACKEND_ACCEPTANCE' and prior['exact_coverage']['actual']==323
 assert not prior['failures'] and not prior['console_errors'] and not prior['cleanup_errors'] and prior['preview_children_reaped']
 for v in prior['variants']:
  if 'retained_from' in v:assert v==first_map[key(v)]
  else:
   raw=z.read(v['screenshot']['name']);assert len(raw)==v['screenshot']['bytes'] and hashlib.sha256(raw).hexdigest()==v['screenshot']['sha256']
 changed={f'after/{s}/{w}' for s in ['bs-rework','hpp'] for w in [320,390,768,1440]}|{f'after/stock-card/{w}' for w in [320,390,768]}|{f'after/{s}/320' for s in ['movements-vivo','movements-widie']}
 retained=[v for v in prior['variants'] if key(v) not in changed];assert len(changed)==13 and len(retained)==310
 for v in retained:v.setdefault('retained_from',prior['after_head'])
 result={'contract':'cp7.B.verified-polish-retention.v1','first_source':prior['after_head'],'first_run':41613755256,'first_artifact':13220396976,'archive_sha256':'e646b9cf6e4115e5fb4a971b5bc067099b15cd1a5b1df41b027c319b6578e762','retained_count':310,'retained_variants':retained,'navigation':prior['navigation'],'desktop_console_smoke':prior['desktop_console_smoke'],'original_first':{k:first[k] for k in ['first_source','first_run','first_artifact','archive_sha256']},'changed_views':sorted(changed),'new_supplemental_views':3}
 (out/'RETAINED_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_both_originals':True,'retained':310,'changed':13,'supplemental':3}))
