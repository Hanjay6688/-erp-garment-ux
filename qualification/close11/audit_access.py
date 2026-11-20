"""Deliver only this synthetic checkpoint's decryption key to a dedicated auditor job.

The one-time public challenge and grant may travel via normal GitHub artifacts.
The private recovery key stays with the auditor. No input is interpreted as code.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import secrets
from .checkpoint import MAGIC,crypto
from .source import PRODUCT,TREE,check,sha

def b64(value):return base64.b64encode(value).decode('ascii')
def raw(value):return base64.b64decode(value,validate=True)

def envelope(path):
    with path.open('rb') as stream:
        prefix=stream.read(len(MAGIC)+2);size=int.from_bytes(prefix[-2:],'big')
        check(prefix[:-2]==MAGIC and size==384,'CLOSE11_ARCHIVE_HEADER')
        return prefix+stream.read(size+12)

def challenge(receipt,archive,out,private):
    hashes,ser,pad,*_=crypto()
    from cryptography.hazmat.primitives.asymmetric import rsa
    row=json.loads(receipt.read_bytes());check(row['status']=='COMMITTED' and (row['product'],row['tree'])==(PRODUCT,TREE),'CLOSE11_ORIGIN')
    job=os.environ['GITHUB_RUN_ID'];head=os.environ['GITHUB_SHA']
    check(os.environ['GITHUB_REPOSITORY']=='Hanjay6688/-erp-garment-ux' and os.environ['GITHUB_REF']=='refs/heads/writer-a/cp7-close12-g14-public' and job.isdecimal() and re.fullmatch(r'[\da-f]{40}',head),'CLOSE11_AUDITOR_JOB')
    key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    with private.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(key.private_bytes(ser.Encoding.PEM,ser.PrivateFormat.PKCS8,ser.NoEncryption()))
    public=key.public_key().public_bytes(ser.Encoding.DER,ser.PublicFormat.SubjectPublicKeyInfo)
    doc=dict(source_run=row['run'],product=PRODUCT,tree=TREE,checkpoint_sha256=row['checkpoint']['sha256'],catalogue_sha256=row['full25_sha256'],audit_run=job,audit_head=head,nonce=secrets.token_hex(24),public=b64(public),header=b64(envelope(archive)))
    out.write_text(json.dumps(doc,sort_keys=True)+'\n')

def grant(proof_path,request,local_key,out,audit_run,audit_head,source_archive):
    hashes,ser,pad,*_=crypto()
    proof=json.loads(proof_path.read_bytes());doc=json.loads(request.read_bytes())
    check(proof['status']=='COMMITTED' and doc['source_run']==proof['run'] and doc['product']==proof['product']==PRODUCT and doc['tree']==proof['tree']==TREE,'CLOSE11_SOURCE_RECEIPT')
    check(doc['checkpoint_sha256']==proof['checkpoint']['sha256'] and doc['catalogue_sha256']==proof['full25_sha256'],'CLOSE11_CHECKPOINT_PIN')
    check(doc['audit_run']==audit_run and doc['audit_head']==audit_head and re.fullmatch(r'[0-9a-f]{48}',doc['nonce']),'CLOSE11_ISSUED_FOR_ANOTHER_JOB')
    header=raw(doc['header'])
    # Confirm the envelope against trusted data before unwrapping a single fixed archive key.
    if proof.get('envelope_sha256'):
        check(sha(header)==proof['envelope_sha256'],'CLOSE11_ENVELOPE_PIN')
    else:
        from .checkpoint import digest
        check(source_archive and digest(source_archive)==doc['checkpoint_sha256'] and envelope(source_archive)==header,'CLOSE11_TRUSTED_SOURCE_ARCHIVE_REQUIRED')
    oaep=lambda label:pad.OAEP(pad.MGF1(hashes.SHA256()),hashes.SHA256(),label=label)
    sk=ser.load_pem_private_key(local_key.read_bytes(),password=None);pub=ser.load_der_public_key(raw(doc['public']))
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    check(isinstance(pub,RSAPublicKey) and pub.key_size==3072,'CLOSE11_AUDITOR_PUBLIC_KEY')
    key=sk.decrypt(header[len(MAGIC)+2:-12],oaep(MAGIC))
    tie=sha(request.read_bytes());reply=dict(challenge_sha256=tie,audit_run=audit_run,envelope=b64(pub.encrypt(key,oaep(bytes.fromhex(tie)))))
    out.write_text(json.dumps(reply,sort_keys=True)+'\n')

def receive(doc_path,reply_path,private):
    hashes,ser,pad,*_=crypto()
    doc=json.loads(doc_path.read_bytes());reply=json.loads(reply_path.read_bytes());tie=sha(doc_path.read_bytes())
    check(reply['challenge_sha256']==tie and reply['audit_run']==doc['audit_run']==os.environ['GITHUB_RUN_ID'] and doc['audit_head']==os.environ['GITHUB_SHA'],'CLOSE11_AUDIT_GRANT')
    sk=ser.load_pem_private_key(private.read_bytes(),password=None)
    return sk.decrypt(raw(reply['envelope']),pad.OAEP(pad.MGF1(hashes.SHA256()),hashes.SHA256(),label=bytes.fromhex(tie)))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='op',required=True)
    c=sub.add_parser('challenge')
    for name in ('installed','archive','request','private'):c.add_argument('--'+name,type=Path,required=True)
    g=sub.add_parser('grant')
    for name in ('installed','request','key','reply'):g.add_argument('--'+name,type=Path,required=True)
    g.add_argument('--source-archive',type=Path)
    for name in ('audit-run','audit-head'):g.add_argument('--'+name,required=True)
    a=p.parse_args()
    if a.op=='challenge':challenge(a.installed,a.archive,a.request,a.private)
    else:grant(a.installed,a.request,a.key,a.reply,a.audit_run,a.audit_head,a.source_archive)
if __name__=='__main__':main()
