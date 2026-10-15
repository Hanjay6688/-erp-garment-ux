"""Download ONLY explicitly identified own artifacts, retaining original bytes.
URLs are ephemeral input, never persisted. ZIP digest and CRC precede extraction.
No tests run here; repeating a transfer grants no Native execution credit.
"""
from pathlib import Path
import hashlib,json,sys,urllib.request,zipfile
def collect(items,directory):
 root=Path(directory);root.mkdir(parents=True,exist_ok=True);out=[]
 for item in items:
  ident=int(item['id']);target=root/(str(ident)+'.zip');temp=target.with_suffix('.part')
  if not target.exists():
   with urllib.request.urlopen(item['download_url'],timeout=90) as response,temp.open('wb') as f:
    while chunk:=response.read(1024*1024):f.write(chunk)
   temp.replace(target)
  digest=hashlib.sha256(target.read_bytes()).hexdigest()
  assert item['digest'].removeprefix('sha256:')==digest,('ARTIFACT_HASH_MISMATCH',ident)
  assert target.stat().st_size==item['size_in_bytes'],('ARTIFACT_SIZE_MISMATCH',ident)
  members=[]
  with zipfile.ZipFile(target) as z:
   assert z.testzip() is None,('ARTIFACT_CRC',ident)
   for entry in z.infolist():
    p=Path(entry.filename);assert not p.is_absolute()and'..'not in p.parts
    if entry.is_dir()or p.suffix.lower()not in('.json','.txt','.log','.sarif'):continue
    data=z.read(entry);dest=root/str(ident)/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    members.append(dict(path=entry.filename,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
  receipt=dict(artifact_id=ident,run_id=item['run_id'],workflow_sha=item['head_sha'],digest=digest,bytes=target.stat().st_size,members=members,Native_execution_credit=0)
  (root/(str(ident)+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');out.append(receipt)
 return out
if __name__=='__main__':
 x=json.load(sys.stdin)
 print(json.dumps([dict(artifact_id=r['artifact_id'],run_id=r['run_id'],bytes=r['bytes'],reports=len(r['members']))for r in collect(x['artifacts'],x['directory'])]))
