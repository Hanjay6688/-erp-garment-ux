"""Verify this addendum's evidence and earlier report locks, without database access."""
from pathlib import Path
import gzip,hashlib,io,json,zipfile
HERE=Path(__file__).resolve().parent
AUDIT=HERE.parent
REPO=AUDIT.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def verify():
    prior=json.loads((AUDIT/'CONTINUATION_REPORT_LOCK.json').read_text())
    for name,meta in prior['files'].items():
        data=(AUDIT/name).read_bytes();assert len(data)==meta['bytes'] and sha(data)==meta['sha256'],name
    for row in json.loads((HERE/'FABLE_SOURCE_MANIFEST.json').read_text())['files']:
        data=(REPO/row['copy']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'],row['copy']
    count=0
    for name in ['FABLE_RUNTIME_ARCHIVES.json','ASTRA_RUNTIME_ARCHIVES.json']:
        manifest=HERE/name
        if not manifest.exists():raise AssertionError('Missing completed evidence index: '+name)
        for row in json.loads(manifest.read_text()):
            parts=[]
            for part in row['parts']:
                b=(HERE/part['path']).read_bytes();assert len(b)==part['bytes'] and sha(b)==part['sha256'];parts.append(b)
            data=b''.join(parts);assert sha(data)==row['stored_sha256']
            raw=gzip.decompress(data)if row['compression']=='gzip'else data
            assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
            if row['file'].endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(raw))as z:assert z.testzip()is None
            count+=1
    cross=json.loads((HERE/'C6_75_ALL22_CROSSWALK.json').read_text());ev=json.loads((AUDIT/'CASE_EVIDENCE_INDEX.json').read_text());assert len(cross['rows'])==97
    for row in cross['rows']:
        assert row['references'] and not row['acceptance_claim']
        for ref in row['references']:
            entry=dict(ref);key=entry.pop('evidence_id');assert entry==ev[key]
    lock=HERE/'ADDENDUM_LOCK.json'
    if lock.exists():
        for name,meta in json.loads(lock.read_text())['files'].items():
            b=(HERE/name).read_bytes();assert len(b)==meta['bytes']and sha(b)==meta['sha256'],name
    print(json.dumps(dict(previous_locked_files=len(prior['files']),source_files=len(json.loads((HERE/'FABLE_SOURCE_MANIFEST.json').read_text())['files']),archives_and_logs=count,requirements=97,verification='PASS')))
if __name__=='__main__':verify()
