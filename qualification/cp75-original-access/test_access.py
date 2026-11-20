"""Check round-trip and refusal boundaries with independent synthetic keys."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
import access as a
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class PairGrant(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder=Path(self.tmp.name)
        self.owner=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        self.keys={name:os.urandom(32) for name in ("clean","upgrade")}
        self.pins={}
        archives={}
        for idx,(name,key) in enumerate(self.keys.items()):
            prefix=a.MAGIC+(384).to_bytes(2,"big")+self.owner.public_key().encrypt(key,a.oaep(a.MAGIC))+os.urandom(12)
            raw=prefix+os.urandom(60)
            path=folder/name
            path.write_bytes(raw)
            self.pins[name]={"sha256":a.digest(raw),"envelope_sha256":a.digest(prefix),"source_run":100+idx}
            archives[name]=path
        keyfile=folder/"receiver.pem"
        self.run="104"
        self.head="a"*40
        self.req=a.make_request(archives,self.pins,self.run,self.head,keyfile)
        self.receiver=serialization.load_pem_private_key(keyfile.read_bytes(),None)
        self.reply=a.issue(self.req,self.owner,self.pins,self.run,self.head)

    def test_roundtrip(self):
        self.assertEqual(a.receive(self.req,self.reply,self.receiver,self.pins,self.run,self.head),self.keys)

    def test_other_head(self):
        with self.assertRaises(ValueError):
            a.issue(self.req,self.owner,self.pins,self.run,"b"*40)

    def test_other_archive(self):
        changed=json.loads(self.req)
        changed["origins"]["clean"]=changed["origins"]["upgrade"]
        with self.assertRaises(ValueError):
            a.issue(a.bytes_of(changed),self.owner,self.pins,self.run,self.head)

    def test_swap_grants(self):
        swapped=json.loads(self.reply)
        w=swapped["wrapped"]
        w["clean"],w["upgrade"]=w["upgrade"],w["clean"]
        with self.assertRaises(ValueError):
            a.receive(self.req,a.bytes_of(swapped),self.receiver,self.pins,self.run,self.head)

    def test_replay(self):
        altered=json.loads(self.req)
        altered["nonce"]="a"*48
        with self.assertRaises(ValueError):
            a.receive(a.bytes_of(altered),self.reply,self.receiver,self.pins,self.run,self.head)


if __name__=="__main__":
    unittest.main()
