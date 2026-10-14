"""Preserve complete GitHub artifacts; verify the server digest and ZIP members."""
import concurrent.futures,hashlib,json,pathlib,sys,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parent/'evidence'
def collect(a):
    p=ROOT/str(a['run_id'])/str(a['id']);p.mkdir(parents=True,exist_ok=True)
    body=urllib.request.urlopen(a['download_url']).read();digest=hashlib.sha256(body).hexdigest()
    assert a['digest']=='sha256:'+digest,(a['id'],'DIGEST_MISMATCH')
    archive=p/(a['name']+'.zip');archive.write_bytes(body)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():
            path=pathlib.PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts
        z.extractall(p/'original')
    receipt={k:v for k,v in a.items() if k not in ('download_url','archive_download_url','file_uri')}
    receipt.update(sha256=digest,local_archive=str(archive),members=z.namelist())
    (p/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return dict(id=a['id'],bytes=len(body),sha256=digest)
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(collect,json.loads(sys.stdin.read())):print(json.dumps(result),flush=True)
