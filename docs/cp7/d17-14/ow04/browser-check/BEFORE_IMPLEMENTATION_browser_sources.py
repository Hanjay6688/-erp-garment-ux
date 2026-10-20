"""Exact escrow UI composition for an isolated CI checkout, never deployment."""
from contextlib import contextmanager
from pathlib import Path
import gzip,hashlib,io,json,re,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[2]
ESCROW=ROOT/'docs/cp7/d17-14/ow04/ui-parent-escrow'
PATCHES=('ui-parent-prerequisites.patch','ui-parent-integration.patch')
CHANGED={'src/SalesReturnPanel.tsx','src/ConnectedSalesPage.tsx','src/productionRecovery.ts',
 'src/types/database.preconnect.ts','src/ConnectedSalesSettlement.dom.test.tsx',
 'src/SalesReturnSettlementSection.tsx','src/SalesReturnSettlementSection.dom.test.tsx',
 'src/salesReturnSettlementContract.ts','src/salesReturnSettlementContract.test.ts'}
def sha(data):return hashlib.sha256(data).hexdigest()
def inspect_sources():
    archive=json.loads((ESCROW/'ARCHIVE.json').read_bytes())
    manifest=json.loads((ESCROW/'ESCROW_MANIFEST.json').read_bytes())
    compressed=(ESCROW/'UI_PARENT_ESCROW.tar.gz').read_bytes()
    assert sha(compressed)==archive['gzip_sha256'],'OW04_BROWSER_ESCROW_GZIP_CHANGED'
    raw=gzip.decompress(compressed)
    assert sha(raw)==archive['tar_sha256'],'OW04_BROWSER_ESCROW_TAR_CHANGED'
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:')as tf:
        members=tf.getmembers()
        assert len(members)==archive['member_count']==53
        assert all(m.isfile()and Path(m.name).name==m.name for m in members),'OW04_BROWSER_UNSAFE_ESCROW_MEMBER'
        data={m.name:tf.extractfile(m).read()for m in members}
    assert set(data)==set(manifest['files'])
    for name,value in data.items():
        assert len(value)==manifest['files'][name]['bytes']and sha(value)==manifest['files'][name]['sha256'],name
    bases=json.loads(data['BASE_MANIFEST.json'])['read_only_source_snapshot']
    before={}
    for name,expected in bases.items():
        if not name.startswith('src/'):continue
        value=(ROOT/name).read_bytes()
        assert sha(value)==expected['sha256'],('OW04_BROWSER_BASE_SOURCE_CHANGED',name)
        before[name]=sha(value)
    changed=set()
    for name in PATCHES:
        changed.update(re.findall(r'^\+\+\+ b/(.+)$',data[name].decode(),re.M))
    assert changed==CHANGED,('OW04_BROWSER_PATCH_PATH_CHANGED',sorted(changed))
    return dict(archive_sha256=sha(compressed),members_verified=53,
      patch_sha256={n:sha(data[n])for n in PATCHES},base_source_sha256=before),data
@contextmanager
def applied_sources(report):
    source,data=inspect_sources()
    # Refuse a live/dirty checkout, including already-present prerequisites.
    status=subprocess.check_output(['git','status','--porcelain','--','src'],cwd=ROOT,text=True)
    assert status=='','OW04_BROWSER_REQUIRES_CLEAN_DISPOSABLE_FRONTEND_CHECKOUT'
    backups={p:(ROOT/p).read_bytes()if(ROOT/p).exists()else None for p in CHANGED}
    report.update(source)
    try:
        for name in PATCHES:
            for check in (True,False):
                command=['git','apply']+(['--check']if check else[])+['-']
                subprocess.run(command,input=data[name],cwd=ROOT,check=True,capture_output=True)
        report['applied_UI_sha256']={p:sha((ROOT/p).read_bytes())for p in sorted(CHANGED)}
        report['composition']='EXACT_ESCROW_UI_WITH_ATOMIC_QUALIFIED_BACKEND_ON_DISPOSABLE_COPY_ONLY'
        yield
    finally:
        for name,original in backups.items():
            target=ROOT/name
            if original is None:target.unlink(missing_ok=True)
            else:target.write_bytes(original)
        assert all(((ROOT/n).read_bytes()if(ROOT/n).exists()else None)==b for n,b in backups.items())
        assert subprocess.check_output(['git','status','--porcelain','--','src'],cwd=ROOT,text=True)==''
        report['frontend_source_restored']=True
