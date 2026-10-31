"""Closed dynamic role-label controls; evidence shapes here are offline doubles."""
from pathlib import Path
import gzip,importlib.util,json,subprocess,tempfile,unittest
HERE=Path(__file__).resolve().parent
def load(path):
 s=importlib.util.spec_from_file_location('s03_role_label_'+path.name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
new=load(HERE/'output_admission.py')


class RoleLabels(unittest.TestCase):
 def test_actual_observed_admin_label_and_only_four_known_producer_combinations(self):
  # The first unknown label in the a209 Original was AFTER_AUTHORIZED_ROLE_ADMIN.
  source=(HERE/'retained-a209/output_admission.py.txt').read_text()
  from types import ModuleType
  original=ModuleType('s03_retained_a209_output');original.__file__=str(HERE/'output_admission.py');exec(compile(source,original.__file__,'exec'),original.__dict__)
  value=dict(all22={str(i):{} for i in range(22)},all_rows={'erp.offline_fixture':[]},data_and_all_sequences={'sequence:erp.offline_fixture_seq':['1',False]})
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   def item(label):
    name='cp6-proof/t3/S03_B4_ACCESS_'+'A'*32+'_009_'+label+'_FULL_STATE.json.gz'
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(json.dumps(value).encode()));return name
   observed=item('AFTER_AUTHORIZED_ROLE_ADMIN')
   with self.assertRaisesRegex(ValueError,'UNKNOWN_SNAPSHOT_LABEL'):original.evidence(root,HERE,observed)
   for prefix in ('AFTER_AUTHORIZED_ROLE_','AFTER_ACCESS_ROLE_REPLAY_'):
    for role in ('ADMIN','OWNER'):self.assertTrue(new.evidence(root,HERE,item(prefix+role)))
   for wrong in ('AFTER_AUTHORIZED_ROLE_STAFF','AFTER_ACCESS_ROLE_REPLAY_UNKNOWN','ARBITRARY_LABEL'):
    with self.assertRaisesRegex(ValueError,'UNKNOWN_SNAPSHOT_LABEL'):new.evidence(root,HERE,item(wrong))

 def test_complete_a209_cases_recovered_with_all_four_financial_callbacks_exact(self):
  delta=load(HERE/'refresh_delta.py');current=(HERE/'cases.mjs').read_bytes();old=(HERE/'retained-a209/cases.mjs.txt').read_bytes()
  self.assertEqual(delta.previous(current),old)
  marker=b'async function desktop('
  self.assertEqual(current[current.index(marker):],old[old.index(marker):])
  with self.assertRaises(ValueError):delta.previous(current+b'\n// unexpected code')

 def test_fresh_response_driver_controls_through_the_existing_CI_Python_entry(self):
  subprocess.run(['node','--unhandled-rejections=strict','--test',str(HERE/'test_fresh_read.mjs')],
    check=True,capture_output=True,text=True)


if __name__=='__main__':unittest.main()
