"""Verify all preserved bytes; reconstruct multipart ZIPs without touching Originals.
Run from the repository root: python audit/astra_cp17/verify_archives.py
"""
import pathlib,json,hashlib,zipfile,io
R=pathlib.Path(__file__).resolve().parents[2];D=R/'audit/astra_cp17'
entries=json.loads((D/'ARCHIVE_INDEX.json').read_text())['artifacts']+json.loads((D/'ARCHIVE_PARTS_INDEX.json').read_text())
seen=set();count=0
for item in entries:
 key=item.get('path') or item['original_filename']
 if key in seen:continue
 seen.add(key)
 if item.get('parts'):
  pieces=[]
  for part in item['parts']:
   b=(R/part['path']).read_bytes();assert len(b)==part['bytes'];assert hashlib.sha256(b).hexdigest()==part['sha256'];pieces.append(b)
  b=b''.join(pieces)
 else:b=(R/item['path']).read_bytes()
 assert len(b)==item['bytes'],key
 assert hashlib.sha256(b).hexdigest()==item['sha256'],key
 if b.startswith(b'PK'):
  with zipfile.ZipFile(io.BytesIO(b))as z:assert z.testzip() is None,key
 count+=1
print(f'PASS: {count} archives/logs (including explicitly marked screenshot selection); all SHA-256/lengths and ZIP CRCs match')
