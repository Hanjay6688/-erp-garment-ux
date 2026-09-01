#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'ops/cp3/cp3_source_archive_manifest.json'
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def main():
 m=json.loads(MANIFEST.read_text())
 if m.get('format')!='CP3_SOURCE_ARCHIVE_V2':raise SystemExit('unsupported archive format')
 chunks=[]
 for spec in m['parts']:
  p=ROOT/spec['path']; d=p.read_bytes()
  if len(d)!=spec['bytes'] or sha(d)!=spec['sha256']:raise SystemExit(f'chunk mismatch: {p}')
  chunks.append(d)
 encoded=b''.join(chunks)
 if len(encoded)!=m['base64_bytes'] or sha(encoded)!=m['base64_sha256']:raise SystemExit('base64 aggregate mismatch')
 try: archive=base64.b64decode(encoded,validate=True)
 except Exception as exc:raise SystemExit(f'invalid base64 archive: {exc}')
 if len(archive)!=m['archive_bytes'] or sha(archive)!=m['archive_sha256']:raise SystemExit('archive mismatch')
 tmp=ROOT/'.cp3-source-v2.tar.gz';tmp.write_bytes(archive)
 with tarfile.open(tmp,'r:gz') as tf:
  for member in tf.getmembers():
   target=(ROOT/member.name).resolve()
   if ROOT.resolve() not in target.parents and target!=ROOT.resolve():raise SystemExit(f'unsafe path: {member.name}')
   if member.issym() or member.islnk() or member.isdev():raise SystemExit(f'unsafe member: {member.name}')
  tf.extractall(ROOT,filter='data')
 tmp.unlink()
 for rel,spec in m['materialized_files'].items():
  p=ROOT/rel;d=p.read_bytes()
  if len(d)!=spec['bytes'] or sha(d)!=spec['sha256']:raise SystemExit(f'materialized mismatch: {rel}')
 print(json.dumps({'status':'PASS','archive_sha256':m['archive_sha256'],'materialized_files':len(m['materialized_files'])},sort_keys=True))
if __name__=='__main__':main()
