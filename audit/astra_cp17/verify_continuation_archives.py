"""Verify preserved continuation bytes and optionally extract to their original paths."""
from pathlib import Path
import gzip,hashlib,io,json,sys,zipfile
R=Path(__file__).resolve().parents[2]
index=json.loads((R/'audit/astra_cp17/CONTINUATION_ARCHIVE_INDEX.json').read_text())
for entry in index['entries']:
    chunks=[]
    for part in entry['parts']:
        b=(R/part['path']).read_bytes();assert len(b)==part['bytes'];assert hashlib.sha256(b).hexdigest()==part['sha256'];assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==part['git_blob_sha'];chunks.append(b)
    b=b''.join(chunks);assert len(b)==entry['bytes'];assert hashlib.sha256(b).hexdigest()==entry['sha256']
    raw=gzip.decompress(b)if entry['kind']=='DECODED_JOB_LOG'else b
    assert len(raw)==entry['decoded_bytes'];assert hashlib.sha256(raw).hexdigest()==entry['decoded_sha256']
    if entry['kind']=='ORIGINAL_ARTIFACT_ZIP':
        with zipfile.ZipFile(io.BytesIO(b))as z:
            assert z.testzip()is None;assert z.namelist()==entry['members']
            if '--extract'in sys.argv:z.extractall((R/entry['source_path']).parent/'original')
    if '--extract'in sys.argv:
        p=R/entry['source_path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
print('PASS',len(index['entries']),'exact ZIP/log archives; SHA256, Git blob SHA, lengths and ZIP CRCs match')
