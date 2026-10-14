"""Preserve exact downloaded ZIPs and decoded logs; no source result is rewritten."""
from pathlib import Path
import gzip, hashlib, json, zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit/astra_cp17'
DEST=OUT/'preserved-continuation'
DEST.mkdir(exist_ok=True)
entries=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def add(path,kind,origin,run=None,artifact=None,job=None):
    data=path.read_bytes()
    raw=data
    name=f'{run}-{artifact}.zip' if artifact else f'{run}-{job}.log.gz'
    if kind=='DECODED_JOB_LOG':data=gzip.compress(data,mtime=0)
    item=dict(kind=kind,evidence_origin=origin,run_id=run,artifact_id=artifact,job_id=job,
        source_path=str(path.relative_to(ROOT)),filename=name,bytes=len(data),sha256=sha(data),
        decoded_bytes=len(raw),decoded_sha256=sha(raw),parts=[])
    if kind=='ORIGINAL_ARTIFACT_ZIP':
        with zipfile.ZipFile(path)as z:
            assert z.testzip() is None
            item['members']=z.namelist()
    for i,start in enumerate(range(0,len(data),600000)):
        b=data[start:start+600000]
        target=DEST/(name+(f'.part{i+1:03d}' if len(data)>600000 else ''))
        if not target.exists() or target.read_bytes()!=b:target.write_bytes(b)
        item['parts'].append(dict(path=str(target.relative_to(ROOT)),bytes=len(b),sha256=sha(b),
            git_blob_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()))
    entries.append(item)

for path in sorted((OUT/'continuation').glob('*/*/original.zip')):
    if not path.parent.name.isdigit()or not path.parent.parent.name.isdigit():continue
    add(path,'ORIGINAL_ARTIFACT_ZIP','ASTRA_EXECUTION',int(path.parent.parent.name),int(path.parent.name))
for path in sorted((OUT/'continuation/fable-exposure').glob('*/*/original.zip')):
    add(path,'ORIGINAL_ARTIFACT_ZIP','FABLE_EXECUTION_ASTRA_CROSSCHECK_ONLY',int(path.parent.parent.name),int(path.parent.name))
for path in sorted((OUT/'continuation/logs').glob('*.log')):
    run,job=map(int,path.stem.split('-'));add(path,'DECODED_JOB_LOG','ASTRA_EXECUTION',run=run,job=job)
result=dict(candidate='0b7049d9203bac52b47a4c89f3e0d75646067a8f',entries=entries,
    original_zip_count=sum(e['kind']=='ORIGINAL_ARTIFACT_ZIP'for e in entries),decoded_log_count=sum(e['kind']=='DECODED_JOB_LOG'for e in entries),
    policy='Exact Original ZIP bytes and GitHub decoded job logs (UTF-8 with one final newline). No signed URLs or credentials. Raw bundles not selected are not claimed permanently preserved. Fable files are cross-check evidence, never Astra executions.')
(OUT/'CONTINUATION_ARCHIVE_INDEX.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(archives=result['original_zip_count'],logs=result['decoded_log_count'],parts=sum(len(e['parts'])for e in entries),bytes=sum(e['bytes']for e in entries))))
