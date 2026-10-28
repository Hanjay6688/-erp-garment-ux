from copy import deepcopy
from hashlib import sha256
from unittest import TestCase,main
import retained_d3


class ExactD3FailureAdmission(TestCase):
    def test_unbound_or_pass_relabelled_D3_cannot_unlock_qualification(self):
        for config in ({},{'allow_qualification_execution':True},
            {'allow_qualification_execution':True,'retained_d3':{'status':'PASS'}},
            {'allow_qualification_execution':False,'retained_d3':{'status':'INCOMPLETE'}}):
            with self.subTest(config=config),self.assertRaisesRegex(ValueError,'ACTUAL_D3_FIRST_FACTORY_CUTOFF_REQUIRED'):
                retained_d3.gate(config)

    def test_both_exact_original_and_package_are_required(self):
        raw=b'{}';proof=dict(bytes=2,sha256=sha256(raw).hexdigest(),package_bytes=2,package_sha256=sha256(raw).hexdigest())
        for key in proof:
            changed=deepcopy(proof);changed[key]='changed'
            with self.subTest(key=key),self.assertRaisesRegex(AssertionError,'ORIGINAL_BYTES_CHANGED'):
                retained_d3.bind(changed,raw,raw)


if __name__=='__main__':main()
