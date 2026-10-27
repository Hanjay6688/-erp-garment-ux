#!/usr/bin/env python3
"""Retry only transient artifact GET failures; never concatenate partial ZIPs."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,re,shutil,subprocess,sys,time,uuid

ARTIFACT=re.compile(r'^repos/Hanjay6688/-erp-garment-ux/actions/artifacts/([0-9]+)/zip$')
TRANSIENT=re.compile(rb'^gh:[^\r\n]*HTTP (502|503|504)\b',re.M)
DELAYS=(2,5)


def eligible(args):
    return len(args)==2 and args[0]=='api' and ARTIFACT.fullmatch(args[1]) is not None


def digest(path):
    h=sha256()
    with path.open('rb')as stream:
        for chunk in iter(lambda:stream.read(65536),b''):h.update(chunk)
    return h.hexdigest()


def download(args,real,receipts,out,err,execute=subprocess.run,pause=time.sleep):
    if not eligible(args):raise ValueError('ARTIFACT_GET_ONLY')
    receipts.mkdir(parents=True,exist_ok=True)
    request=uuid.uuid4().hex
    for index in range(len(DELAYS)+1):
        label=request+'-'+str(index+1)
        stdout=receipts/(label+'.stdout.txt');stderr=receipts/(label+'.stderr.txt')
        started=time.monotonic()
        with stdout.open('xb')as output,stderr.open('xb')as errors:
            result=execute([real,*args],stdout=output,stderr=errors,check=False)
        error=stderr.read_bytes();transient=TRANSIENT.search(error)
        retry=result.returncode!=0 and transient is not None and index<len(DELAYS)
        receipt=dict(artifact_id=int(ARTIFACT.fullmatch(args[1]).group(1)),attempt=index+1,
            exit_code=result.returncode,http_status=int(transient.group(1)) if transient else None,
            recorded_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-started,3),
            stdout_bytes=stdout.stat().st_size,stdout_sha256=digest(stdout),
            stderr_bytes=len(error),stderr_sha256=sha256(error).hexdigest(),retry=retry,
            delay_seconds=DELAYS[index] if retry else None,partial_stdout_forwarded=False,
            downstream_original_hash_and_size_checks_unchanged=True)
        (receipts/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        if result.returncode==0:
            with stdout.open('rb')as stream:shutil.copyfileobj(stream,out,length=65536)
            out.flush()
            if error:err.write(error);err.flush()
            # Successful bytes already go to the unchanged exact-Original check.
            # Retain their hash receipt, not every historical ZIP a second time.
            stdout.unlink();stderr.unlink()
            return 0
        err.write(error)
        err.write(('Artifact GET attempt '+str(index+1)+' failed; '+('bounded retry follows' if retry else 'stopped')+'.\n').encode())
        err.flush()
        if not retry:return result.returncode
        pause(DELAYS[index])
    raise AssertionError('ARTIFACT_RETRY_BOUND')


def main():
    real=os.environ['D17_REAL_GH']
    if not os.path.isabs(real) or os.path.samefile(real,__file__):raise ValueError('REAL_GH_PATH_REQUIRED')
    args=sys.argv[1:]
    if not eligible(args):os.execv(real,[real,*args])
    return download(args,real,Path(os.environ['D17_ARTIFACT_FETCH_RECEIPTS']),sys.stdout.buffer,sys.stderr.buffer)


if __name__=='__main__':sys.exit(main())
