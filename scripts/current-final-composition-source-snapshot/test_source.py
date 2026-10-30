"""Source tamper/refusal controls; zero ERP/DB/Auth/browser execution."""
from copy import deepcopy
from pathlib import Path
import ast
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final_source_snapshot_checker',HERE/'check.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


class SourceSnapshotControls(unittest.TestCase):
    def manifest(self):return json.loads((HERE/'SNAPSHOT.json').read_bytes())

    def test_actual_byte_exact_collection_and_all_old_base_Git_modes(self):
        r=check.check()
        self.assertEqual(r['selected_exact_original_files'],51)
        self.assertFalse(r['proposed_composition_runnable'])
        self.assertIsNone(r['runtime_entry'])

    def test_unknown_missing_duplicate_or_wrong_component_is_refused(self):
        for kind in('unknown','missing','duplicate','wrong_component'):
            value=self.manifest()
            if kind=='unknown':value['selected_files'][0]['path']='scripts/unallocated.py'
            elif kind=='missing':value['selected_files'].pop()
            elif kind=='duplicate':value['selected_files'].append(deepcopy(value['selected_files'][0]))
            else:value['selected_files'][0]['source_commit']='0'*40
            with self.subTest(kind=kind),self.assertRaises(ValueError):check.validate_manifest(value)

    def test_NULL_bindings_cannot_be_replaced_by_local_or_retained_PASS(self):
        for key,new in [('runtime_entry','fake.entry'),('global_parent_binding',{'status':'PASS'}),
                        ('accepted_component_bindings',dict.fromkeys(check.REFS,{'status':'PASS'})),
                        ('actual_execution_authorized',True),('actual_Native_Auth_HTTP_browser_races',True)]:
            value=self.manifest();value[key]=new
            with self.subTest(key=key),self.assertRaises(ValueError):check.validate_manifest(value)

    def test_path_traversal_absolute_backslash_and_alias_refuse(self):
        for path in('../outside.py','/absolute.py','scripts/../x.py','scripts\\x.py','scripts//x.py'):
            with self.subTest(path=path),self.assertRaises(ValueError):check.safe_path(path)

    def test_changed_code_cannot_keep_an_old_length_or_hash(self):
        row=dict(path='EXPLICIT_LOCAL_BYTES_DOUBLE',**check.pin(b'abc'))
        check.verify_bytes(b'abc',row)
        for raw in(b'abd',b'abcd',b''):
            with self.subTest(raw=raw),self.assertRaises(ValueError):check.verify_bytes(raw,row)

    def test_mode_and_parent_adapter_drift_are_not_admitted(self):
        value=self.manifest();value['selected_files'][0]['git_mode']='120000'
        with self.assertRaises(ValueError):check.validate_manifest(value)
        value=self.manifest();value['parent_adapters_changed']=True
        with self.assertRaises(ValueError):check.validate_manifest(value)

    def test_source_checker_itself_has_no_ERP_or_DB_import_or_network(self):
        tree=ast.parse((HERE/'check.py').read_bytes());roots=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):roots.update(x.name.split('.')[0]for x in n.names)
            elif isinstance(n,ast.ImportFrom):roots.add((n.module or'').split('.')[0])
        self.assertEqual(roots,{'pathlib','hashlib','ast','json','os','subprocess'})
        self.assertFalse({'psycopg','requests','http','socket','urllib'}&roots)


if __name__=='__main__':unittest.main(verbosity=2)
