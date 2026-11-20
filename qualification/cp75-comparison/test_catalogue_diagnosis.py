"""Check object-level diagnosis without losing duplicate catalogue identities."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/"cp75-original-live/catalogue_evidence.py"
spec=importlib.util.spec_from_file_location("catalogue_evidence",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueDiagnosis(unittest.TestCase):
    def compare_case(self, old, new, new_count):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source={"origin_run":1,"server":{"sha256":"archive","counts":{"functions":len(old)}},
                    "groups":{"functions":"before"},"objects":{"functions":old}}
            collected={"server":{"sha256":"reconstructed","counts":{"functions":new_count}},"group_hashes":{"functions":"after"}}
            for name,doc in (("old.gz",source),("new.gz",{"functions":new})):
                with gzip.open(root/name,"wt") as file:
                    json.dump(doc,file)
            (root/"measured.json").write_text(json.dumps(collected))
            module.compare(root/"old.gz",root/"new.gz",root/"measured.json",root/"difference.json")
            full=json.loads((root/"difference.json").read_text())
            self.assertEqual(full["changed_groups"],["functions"])
            return full["groups"]["functions"]

    def test_localizes_only_the_changed_function(self):
        result=self.compare_case([["a","1"],["b","2"]],{"a":"1","b":"3"},2)
        self.assertEqual(result["different"],[{"name":"b","archived":"2","reconstructed":"3"}])
        self.assertTrue(result["object_hashes_complete"])

    def test_ambiguous_names_keep_the_raw_group_difference_open(self):
        result=self.compare_case([["a","1"],["a","2"]],{"a":"2"},2)
        self.assertFalse(result["object_hashes_complete"])
        self.assertNotIn("different",result)
