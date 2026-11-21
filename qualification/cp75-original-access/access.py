"""Restrict a CP7.5 restore grant to the two pinned synthetic archives, one receiver and one Actions run."""
import argparse
import base64
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ORIGINS = {
    "clean": {
        "sha256": "996a89a48b4309b6ae4239dd8811b47f22719ed0fafdb1826d9c1cc4b1cb1019",
        "envelope_sha256": "4bfb365a0fae712e662d482fe740738c63fbaab92a367f0fd5401e052489c943",
        "source_run": 44800849536
    },
    "upgrade": {
        "sha256": "f8f698fbdbf17673f9c7cea8f916d59ffdce89bc9cac200beb93fd3df8f3062a",
        "envelope_sha256": "e895e7ed7286057f70281dd3e26649cc676cce67f23e49db0f3668c1432becc3",
        "source_run": 44671146483
    }
}
SOURCE = "Hanjay6688/-erp-garment-ux"
BRANCH = "refs/heads/writer-a/cp75-baseline-public"
PRODUCT = "48858590a361343e73a7f16f6646363dc155c04e"
MAGIC = b"CP7G11\x01"


def check(truth, message):
    if not truth:
        raise ValueError(message)


def pack(raw):
    return base64.b64encode(raw).decode("ascii")


def unpack(text):
    return base64.b64decode(text,validate=True)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def oaep(label):
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=label)


def bytes_of(value):
    return (json.dumps(value, sort_keys=True, separators=(",",":")) + "\n").encode()


def write(path, content):
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as out:
        out.write(content)


def header(path):
    with path.open("rb") as file:
        prefix=file.read(405)
        check(prefix.startswith(MAGIC) and int.from_bytes(prefix[7:9],"big")==384 and len(prefix)==405,"invalid checkpoint envelope")
        return prefix


def make_request(archives, origins, run, head, keypath):
    check(os.environ.get("GITHUB_REPOSITORY")==SOURCE and os.environ.get("GITHUB_REF")==BRANCH,"unexpected receiver")
    check(run.isdecimal() and re.fullmatch("[a-f0-9]{40}",head),"invalid run identity")
    check(set(archives)==set(origins),"both archives required")
    members={}
    for lane,pin in origins.items():
        with archives[lane].open("rb") as f:
            check(hashlib.file_digest(f,"sha256").hexdigest()==pin["sha256"],"original archive mismatch")
        data=header(archives[lane])
        check(digest(data)==pin["envelope_sha256"],"original envelope mismatch")
        members[lane]={**pin,"header":pack(data)}
    key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    write(keypath,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    return bytes_of({"protocol":"cp75-originals/v1","repo":SOURCE,"ref":BRANCH,"product":PRODUCT,
                     "run":run,"head":head,"nonce":secrets.token_hex(24),"origins":members,
                     "receiver":pack(key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo))})


def validate(request,origins,run,head):
    doc=json.loads(request)
    check(len(request)<8000 and doc["protocol"]=="cp75-originals/v1","invalid request")
    check((doc["repo"],doc["ref"],doc["product"],doc["run"],doc["head"])==(SOURCE,BRANCH,PRODUCT,run,head),"wrong receiver or run")
    check(re.fullmatch("[0-9a-f]{48}",doc["nonce"]) and set(doc["origins"])==set(origins),"wrong origin set")
    for lane,pin in origins.items():
        received=doc["origins"][lane]
        data=unpack(received["header"])
        check(len(data)==405 and data[:7]==MAGIC and int.from_bytes(data[7:9],"big")==384,"invalid envelope")
        check({k:received[k] for k in pin}==pin and digest(data)==pin["envelope_sha256"],"untrusted checkpoint envelope")
    return doc


def label(request,lane):
    return hashlib.sha256(b"cp75-originals/v1\0"+lane.encode()+b"\0"+request).digest()


def issue(request,key,origins,run,head):
    doc=validate(request,origins,run,head)
    receiver=serialization.load_der_public_key(unpack(doc["receiver"]))
    check(isinstance(receiver,rsa.RSAPublicKey) and receiver.key_size==3072 and receiver.public_numbers().e==65537,"invalid receiver key")
    granted={}
    for lane in origins:
        encrypted=unpack(doc["origins"][lane]["header"])[9:-12]
        data=key.decrypt(encrypted,oaep(MAGIC))
        check(len(data)==32,"invalid data key")
        granted[lane]=pack(receiver.encrypt(data,oaep(label(request,lane))))
    return bytes_of({"run":run,"head":head,"request_sha256":digest(request),"wrapped":granted})


def receive(request,response,receiver,origins,run,head):
    validate(request,origins,run,head)
    reply=json.loads(response)
    check((reply["run"],reply["head"],reply["request_sha256"])==(run,head,digest(request)),"grant for another run")
    check(set(reply["wrapped"])==set(origins),"incomplete grant")
    keys={lane:receiver.decrypt(unpack(reply["wrapped"][lane]),oaep(label(request,lane))) for lane in origins}
    check(all(len(v)==32 for v in keys.values()),"invalid grant")
    return keys


def main():
    p=argparse.ArgumentParser()
    modes=p.add_subparsers(dest="op",required=True)
    challenge=modes.add_parser("request")
    for arg in ["clean","upgrade","receiver","out"]:
        challenge.add_argument("--"+arg,type=Path,required=True)
    grant=modes.add_parser("grant")
    for arg in ["request","key","out"]:
        grant.add_argument("--"+arg,type=Path,required=True)
    grant.add_argument("--run",required=True)
    grant.add_argument("--head",required=True)
    grant.add_argument("--clean-only", action="store_true", help="Grant only the pinned BF archive for a BF-only request")
    a=p.parse_args()
    if a.op=="request":
        raw=make_request({"clean":a.clean,"upgrade":a.upgrade},ORIGINS,os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_SHA"],a.receiver)
    else:
        key=serialization.load_pem_private_key(a.key.read_bytes(),None)
        origins = {"clean": ORIGINS["clean"]} if a.clean_only else ORIGINS
        raw=issue(a.request.read_bytes(),key,origins,a.run,a.head)
    write(a.out,raw)


if __name__=="__main__":
    main()
