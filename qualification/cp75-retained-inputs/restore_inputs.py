"""Open the auditor's sealed copies of three previously published synthetic workflow artifacts."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CIPHER_SHA = "e5a5eccf3df6f87bdd5e76102478ad77702bd7a88ac908ba8db62e2654071929"
MANIFEST_SHA = "2a948d714d8092672649c6f27209316737ebe8edb8ae958aeb51a52393a2f902"
HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_manifest():
    raw = (HERE / "archives.json").read_bytes()
    if digest(raw) != MANIFEST_SHA:
        raise ValueError("Unexpected archived input manifest")
    return raw, json.loads(raw)


def transport_label(request):
    return hashlib.sha256(b"astra-cp75-retained-inputs/receiver-v1\0" + request + bytes.fromhex(CIPHER_SHA)).digest()


def oaep(label):
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=label)


def open_archives(request, response, receiver, run, head, destination):
    expected = (str(run), head, digest(request))
    if (response["run"], response["head"], response["request_sha256"]) != expected:
        raise ValueError("The audit response belongs to another request")
    retained = response["retained_inputs"]
    if retained["cipher_sha256"] != CIPHER_SHA:
        raise ValueError("Unexpected sealed input payload")
    cipher = (HERE / "inputs.aesgcm").read_bytes()
    if digest(cipher) != CIPHER_SHA:
        raise ValueError("Sealed payload differs from the verified copy")
    aad, pins = read_manifest()
    key = receiver.decrypt(base64.b64decode(retained["wrapped_key"], validate=True), oaep(transport_label(request)))
    body = AESGCM(key).decrypt(cipher[:12], cipher[12:], aad)
    with ZipFile(io.BytesIO(body)) as archive:
        if sorted(archive.namelist()) != sorted(aid + ".zip" for aid in pins):
            raise ValueError("Unexpected contents in the audit payload")
        for aid, pin in pins.items():
            raw = archive.read(aid + ".zip")
            if len(raw) != pin["bytes"] or digest(raw) != pin["sha256"]:
                raise ValueError("Stored bytes differ from the original artifact " + aid)
            with (destination / (aid + ".zip")).open("xb") as target:
                target.write(raw)
    return pins


def main():
    import access
    import live

    run, head = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_SHA"]
    request = live.REQUEST.read_bytes()
    access.validate(request, {"clean": access.ORIGINS["clean"]}, run, head)
    response = json.loads(live.response())
    receiver = serialization.load_pem_private_key(live.KEY.read_bytes(), None)
    folder = Path(os.environ["RUNNER_TEMP"]) / "cp75-retained-inputs"
    folder.mkdir(mode=0o700)
    pins = open_archives(request, response, receiver, run, head, folder)
    proof = {"run": run, "head": head, "archive_bytes_verified": pins, "production_go": False}
    (live.RESULT / "retained-inputs-verified.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("Three archived originals match their pinned GitHub ZIP digests", flush=True)


if __name__ == "__main__":
    main()
