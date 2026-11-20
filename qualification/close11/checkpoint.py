"""Preserve the exact public test cluster and its Vault configuration for the auditor."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .source import HERE,check,sha

MAGIC=b'CP7G11\x01'
BLOCK=1<<20
def crypto():
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    return hashes,serialization,padding,Cipher,algorithms,modes

def seal(src,out,public):
    hashes,serialization,pad,Cipher,alg,modes=crypto()
    key=os.urandom(32);nonce=os.urandom(12)
    public_key=serialization.load_pem_public_key(public.read_bytes())
    wrap=public_key.encrypt(key,pad.OAEP(pad.MGF1(hashes.SHA256()),hashes.SHA256(),label=MAGIC))
    head=MAGIC+len(wrap).to_bytes(2,'big')+wrap+nonce
    enc=Cipher(alg.AES(key),modes.GCM(nonce)).encryptor();enc.authenticate_additional_data(head)
    with out.open('xb') as dst,src.open('rb') as inp:
        dst.write(head)
        while chunk:=inp.read(BLOCK):dst.write(enc.update(chunk))
        dst.write(enc.finalize());dst.write(enc.tag)
    return {'bytes':out.stat().st_size,'sha256':digest(out),'format':'RSA-OAEP-SHA256 + AES-256-GCM'}

def unseal(src,out,private=None,*,transferred_key=None):
    hashes,serialization,pad,Cipher,alg,modes=crypto()
    with src.open('rb') as inp:
        magic=inp.read(len(MAGIC));count=inp.read(2)
        check(magic==MAGIC and int.from_bytes(count,'big')==384,'CLOSE11_ENVELOPE')
        wrap=inp.read(384);nonce=inp.read(12)
        head=magic+count+wrap+nonce
        check((private is None) != (transferred_key is None),'CLOSE11_ONE_DECRYPTION_KEY')
        key=transferred_key if transferred_key is not None else serialization.load_pem_private_key(private.read_bytes(),password=None).decrypt(wrap,pad.OAEP(pad.MGF1(hashes.SHA256()),hashes.SHA256(),label=MAGIC))
        check(len(key)==32,'CLOSE11_KEY_LENGTH')
        inp.seek(-16,2);tag=inp.read(16);inp.seek(len(head))
        dec=Cipher(alg.AES(key),modes.GCM(nonce,tag)).decryptor();dec.authenticate_additional_data(head)
        remaining=src.stat().st_size-len(head)-16
        check(remaining>=0,'CLOSE11_SHORT_CHECKPOINT')
        with tempfile.NamedTemporaryFile(dir=out.parent,delete=False) as tmp:
            partial=Path(tmp.name)
            try:
                while remaining:
                    chunk=inp.read(min(BLOCK,remaining));check(chunk,'CLOSE11_SHORT_CHECKPOINT')
                    tmp.write(dec.update(chunk));remaining-=len(chunk)
                tmp.write(dec.finalize())
            except BaseException:
                partial.unlink();raise
        try:os.link(partial,out)
        finally:partial.unlink()

def digest(path):
    with path.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()

def capture(result):
    db='supabase_db_cp5-local'
    def docker(*args):
        response=subprocess.run(['docker',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=480)
        if response.returncode:
            err=response.stderr.decode(errors='replace').lower()
            allowed=('no space left','no such file','password authentication failed','no password supplied','peer authentication failed','permission denied','manifest','could not open','could not connect','not found')
            reason=next((s for s in allowed if s in err),'exit '+str(response.returncode))
            raise ValueError('CLOSE11_BACKUP '+stage+' '+reason)
        return response.stdout.decode().strip()
    with tempfile.TemporaryDirectory(prefix='close11-backup-') as td:
        base=Path(td);vault=Path(os.environ['GITHUB_WORKSPACE'])/'close11-audit-checkpoint';vault.mkdir(exist_ok=True)
        tmp='/tmp/writer-a-close11-basebackup'
        stage='source image'
        try:
            image=docker('inspect','-f','{{.Image}}',db)
            known=json.loads(docker('image','inspect','-f','{{json .RepoDigests}}',image))
            check(known and any('@sha256:' in v for v in known),'CLOSE11_IMAGE_DIGEST')
            # pg_basebackup includes every role, databases, WAL and backup_manifest. The config volume
            # also carries the disposable cluster's Vault key. Neither is published in clear text.
            docker('exec','-u','postgres',db,'mkdir','-m','700',tmp)
            stage='physical base backup'
            docker('exec','-u','postgres',db,'pg_basebackup','-w','-h','/var/run/postgresql','-U','supabase_admin','-D',tmp+'/data','-X','stream','-c','fast','--manifest-checksums=SHA256')
            stage='verify backup manifest'
            docker('exec','-u','postgres',db,'pg_verifybackup',tmp+'/data')
            stage='copy configuration'
            docker('exec','-u','postgres',db,'cp','-a','/etc/postgresql-custom',tmp+'/config')
            result['backup_manifest_sha256']=docker('exec','-u','postgres',db,'sha256sum',tmp+'/data/backup_manifest').split()[0]
            result['postgres_image']=known[0]
            stage='services'
            runtime=json.loads(docker('exec','-u','postgres',db,'psql','-U','supabase_admin','-d','postgres','-XAt','-v','ON_ERROR_STOP=1','-c',(
                "select jsonb_build_object('postgres_version',current_setting('server_version_num'),'scheduler_database',current_setting('cron.database_name',true),"
                "'scheduler_enabled',current_setting('cron.launch_active_jobs',true),'extensions',(select jsonb_object_agg(extname,extversion) from pg_extension where extname in ('pg_cron','pg_net','supabase_vault')), "
                "'scheduler_table',to_regclass('cron.job') is not null,'vault_reader',to_regclass('vault.decrypted_secrets') is not null)")))
            check(runtime['postgres_version']=='170006','CLOSE11_POSTGRES_SOURCE')
            result['cluster_services']=runtime
            raw=base/'cluster.tar.gz'
            with raw.open('xb') as dest:
                subprocess.run(['docker','exec','-u','postgres',db,'tar','-C',tmp,'-czf','-','data','config'],stdout=dest,stderr=subprocess.PIPE,check=True,timeout=480)
            result['checkpoint']=seal(raw,vault/'global-ffda.cp7',HERE/'auditor-public.pem')
            result['checkpoint']['plaintext_sha256']=digest(raw)
            from .audit_access import envelope
            result['envelope_sha256']=sha(envelope(vault/'global-ffda.cp7'))
            saved=Path(os.environ['RUNNER_TEMP'])/'close11-private-source'
            saved.mkdir(mode=0o700,exist_ok=False)
            shutil.move(raw,saved/'cluster.tar.gz')
        finally:
            subprocess.run(['docker','exec','-u','postgres',db,'rm','-rf','--',tmp],capture_output=True,timeout=60)
