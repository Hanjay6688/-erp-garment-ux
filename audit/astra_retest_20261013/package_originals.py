"""Losslessly retain complete JSON Originals; bulky traces stay in referenced CI artifacts."""
from pathlib import Path
import hashlib, io, json, tarfile

ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
selected=set()
for folder in E.iterdir():
    if folder.is_dir() and (folder.name.endswith('-json') or folder.name in ('asf-pure','cp7retest-astra-7a0b4a90-evidence-validation','cp7retest-astra-7a0b4a90-cp7-shell-proof')):
        selected.update(folder.rglob('*.json'))
selected.update(E.rglob('*.sarif'))
selected.update(E.glob('*FIRST_FAILURE*.log'))
selected.update(E.glob('*FIRST_DIAGNOSTIC*.log'))
selected.update(E.glob('SHELL_*.log'))
selected.update(E.glob('DOWNLOAD_INDEX*.json'))
for folder in ('cp7retest-astra-7a0b4a90-own-own-delta14-raw','cp7retest-astra-7a0b4a90-cp7-shell-proof'):
    selected.update((E/folder).rglob('*.png'))
old=ROOT/'baseline/writer_supplier_first_failure.log'
if old.exists():selected.add(old)

rows=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(selected)]
manifest=dict(format='lossless tar.xz, files unmodified',files=rows,files_count=len(rows),uncompressed_bytes=sum(x['bytes'] for x in rows),excluded='Large raw screenshots/traces/duplicated source SQL remain in original CI artifacts. No field is removed from selected complete Original JSON.',production_go=False)
payload=(json.dumps(manifest,indent=2)+'\n').encode()
(ROOT/'ORIGINALS_MANIFEST.json').write_bytes(payload)
dest=ROOT/'FINAL_ORIGINALS.tar.xz'
with tarfile.open(dest,'w:xz',preset=9) as tar:
    for p in sorted(selected):
        info=tarfile.TarInfo(str(p.relative_to(ROOT)));info.size=p.stat().st_size;info.mode=0o644;info.mtime=0
        with p.open('rb') as stream:tar.addfile(info,stream)
    info=tarfile.TarInfo('ORIGINALS_MANIFEST.json');info.size=len(payload);info.mode=0o644;tar.addfile(info,io.BytesIO(payload))
with tarfile.open(dest,'r:xz') as tar:
    assert set(tar.getnames())=={x['path'] for x in rows}|{'ORIGINALS_MANIFEST.json'}
    for row in rows:
        body=tar.extractfile(row['path']).read()
        assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'],row['path']
print(json.dumps(dict(archive=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,files=len(rows),original_bytes=manifest['uncompressed_bytes'])))
