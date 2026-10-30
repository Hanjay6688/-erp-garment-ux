"""Directed source and closed-entry controls, never Native/Auth/DB evidence."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class PreparedParentControls(unittest.TestCase):
    def test_runtime_observer_does_not_evaluate_foreign_tuple_subclasses(self):
        m=load('read_only_runtime_observer',HERE/'inspect_sources.py')
        class Foreign(tuple):
            def __len__(self):raise AssertionError('FOREIGN_RETURN_WAS_EVALUATED')
        frame=SimpleNamespace(f_code=SimpleNamespace(co_filename='/outside/python/platform.py',co_name='uname'))
        observed=[];m.observe_runtime_return(frame,Foreign(),set(),observed)
        self.assertEqual(observed,[])

    def test_full_source_scope_and_four_exact_reversible_derivations(self):
        r=load('guard',HERE/'guard.py').check()
        self.assertEqual((r['derived_original_files'],r['counted_substitutions']),(4,9))
        self.assertIsNone(r['runtime_entry']);self.assertFalse(r['installed_or_catalog_verified'])

    def test_every_business_entry_refuses_before_ERP_import_or_cursor_access(self):
        script='''
from pathlib import Path
import importlib.abc,importlib.util,sys
class DenyERP(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cp7_','psycopg')):raise AssertionError('ERP_IMPORT_BEFORE_CLOSED_GATE:'+fullname)
sys.meta_path.insert(0,DenyERP())
class Cursor:
 def __getattribute__(self,name):raise AssertionError('CURSOR_ACCESSED:'+name)
for folder in ('cp7_final_composition','cp7_final_global_bridge'):
 path=Path('scripts')/folder/'composition.py'
 s=importlib.util.spec_from_file_location(folder+'_direct_closed_test',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 names=('install','install_delta','verify','rollback_delta_preuse','rollback_preuse')+(('runtime',)if folder=='cp7_final_composition'else())
 for name in names:
  try:
   if name=='runtime':getattr(m,name)()
   elif name=='install':getattr(m,name)(Cursor())
   else:getattr(m,name)(Cursor(),{'status':'FAKE_PASS'})
  except ValueError as e:assert 'CLOSED'in str(e),(name,e)
  else:raise AssertionError('CLOSED_ENTRY_ACCEPTED:'+name)
print('ALL_11_ENTRIES_CLOSED_BEFORE_ERP_CURSOR')
'''
        r=subprocess.run([sys.executable,'-B','-c',script],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        self.assertEqual(r.returncode,0,r.stdout.decode());self.assertIn(b'ALL_11_ENTRIES_CLOSED',r.stdout)

    def test_fake_PASS_or_typed_count_cannot_open_the_final_facade(self):
        m=load('final_gate',ROOT/'scripts/cp7_final_composition/composition.py');value=json.loads((m.HERE/'BINDINGS.json').read_bytes())
        for key,v in [('runtime_entry','fake'),('global_parent_binding',{'status':'PASS'}),
                     ('accepted_component_bindings',dict.fromkeys(m.DOMAINS,{'status':'PASS'})),
                     ('actual_execution_authorized',True),('actual_Native_Auth_HTTP_browser_races',False)]:
            changed=deepcopy(value);changed[key]=v
            with self.subTest(key=key),self.assertRaises(ValueError):m.validate_bindings(changed)

    def test_changed_or_duplicate_counted_anchor_refuses(self):
        g=load('counter',HERE/'guard.py');step=[dict(before='unique',after='derived',count=1)]
        self.assertEqual(g.apply_changes(b'unique',step),b'derived')
        self.assertEqual(g.apply_changes(b'derived',step,True),b'unique')
        for raw in(b'changed',b'unique unique'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):g.apply_changes(raw,step)

    def test_source_byte_change_and_unknown_path_refuse(self):
        g=load('bytes',HERE/'guard.py')
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);(root/'leaf').write_bytes(b'old');entry=g.pin(b'old')
            self.assertEqual(g.read_exact(root,'leaf',entry),b'old');(root/'leaf').write_bytes(b'new')
            with self.assertRaises(ValueError):g.read_exact(root,'leaf',entry)
            for name in('../escape','/escape','a\\b','a//b'):
                with self.subTest(name=name),self.assertRaises(ValueError):g.read_exact(root,name,entry)

    def test_leaf_and_ancestor_symlinks_refuse_even_for_matching_bytes(self):
        g=load('links',HERE/'guard.py')
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);target=root/'actual';target.mkdir();(target/'leaf').write_bytes(b'exact');entry=g.pin(b'exact')
            (root/'leaf').symlink_to(target/'leaf');(root/'ancestor').symlink_to(target,target_is_directory=True)
            for name in('leaf','ancestor/leaf'):
                with self.subTest(name=name),self.assertRaises(ValueError):g.read_exact(root,name,entry)

    def test_source_parent_order_and_S05_status_are_intentional(self):
        sku=(ROOT/'scripts/cp7_sku_pair_conversion/composition.py').read_text()
        attendance=(ROOT/'scripts/cp7_attendance_period_choice/composition.py').read_text()
        report=(ROOT/'scripts/cp7_accessory_standard_report/stage.py').read_text()
        self.assertIn('from cp7_credit_correction_de import e_composition as vendor_parent',sku)
        self.assertIn('from cp7_final_global_bridge import composition as predecessor',attendance)
        self.assertIn('from cp7_attendance_period_choice import composition',report)
        self.assertIn("'CP7_S03_EXACT_SOURCE_ACTUAL_ALL22'",report)
        self.assertNotIn("'VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22'",report)


if __name__=='__main__':unittest.main(verbosity=2)
