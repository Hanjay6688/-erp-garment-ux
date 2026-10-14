"""Recover original proof bytes; validate GitHub digest and every ZIP CRC."""
import hashlib,json,zipfile
from pathlib import Path
E=Path(__file__).parent/'evidence'
meta={str(x['id']):x for x in json.loads((E/'ARTIFACT_REGISTER.json').read_text())}
index=[]
for p in sorted(E.glob('*.zip')):
 m=meta[p.stem];sha=hashlib.sha256(p.read_bytes()).hexdigest()
 assert 'sha256:'+sha==m['digest'],('DOWNLOAD_DIGEST',p.name)
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None,('ZIP_CRC',p.name)
  entries=[]
  for name in z.namelist():
   if not name.endswith(('.json','.sarif','.jsonl')):continue
   raw=z.read(name);entries.append(dict(name=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
   if name.endswith('.jsonl'):continue
   try:d=json.loads(raw)
   except (ValueError,UnicodeError):continue
   if not isinstance(d,dict):continue
   if any(k in d for k in ('status','groups','candidate_sha','runs','errors','candidate_tree'))and not name.endswith(('package.json','package-lock.json')):
    q=E/'original-reports'/p.stem/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
 index.append(dict(artifact_id=m['id'],run_id=m['scan_run'],name=m['name'],zip_sha256=sha,members=entries))
(E/'MEMBER_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps(dict(verified_artifacts=len(index),original_reports=len(list((E/'original-reports').rglob('*'))))))
