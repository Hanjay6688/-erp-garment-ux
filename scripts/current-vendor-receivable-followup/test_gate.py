"""Negative source controls only; synthetic bytes cannot become ERP proof."""
from pathlib import Path
import importlib.util,json,unittest
from hashlib import sha256
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('vendor_followup_closed_gate',HERE/'gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Gate(unittest.TestCase):
 def test_unselected_backend_closed(self):
  with self.assertRaisesRegex(ValueError,'CLOSED_NATIVE7'):m.checked(dict(accepted_native7=None),b'',b'',{},())
 def test_partial_actual_claim_refused(self):
  raw=json.dumps(dict(label='CP7_VENDOR_RECEIVABLE_NATIVE7',status='INCOMPLETE',qualification_commit='synthetic')).encode();pkg=b'{}'
  cfg=dict(accepted_native7=dict(head='synthetic',original=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),package=dict(bytes=len(pkg),sha256=sha256(pkg).hexdigest())))
  with self.assertRaisesRegex(ValueError,'NOT_QUALIFIED'):m.checked(cfg,raw,pkg,{},())
 def test_tampered_original_refused_before_content(self):
  cfg=dict(accepted_native7=dict(original=dict(bytes=2,sha256=sha256(b'{}').hexdigest())))
  with self.assertRaisesRegex(ValueError,'BYTES_CHANGED'):m.checked(cfg,b'[]',b'',{},())

 def complete_synthetic(self,change=lambda a,p:None,current=None):
  ids=tuple('UNIT_ONLY_CASE_'+str(i)for i in range(7));source=dict(unit_only=True)
  a=dict(label='CP7_VENDOR_RECEIVABLE_NATIVE7',status='PASS',qualification_commit='UNIT_ONLY_HEAD',
   cp6_restored=True,advisor_gate=True,baseline_full22_all_rows_all_sequences_equal=True,
   baseline_advisors_equal=True,used_guard_refused_before_DDL=True,required_case_ids_pass=True,
   expected_case_count=1,observed_case_count=1,focused_preuse_removal=dict(used_guard_before_DDL=True),
   source_declaration=dict(current_installation=source),committed=dict(VENDOR_RECEIVABLE_NATIVE7_AND_USED_INVERSE=dict(status='PASS',
    native=dict(counts={'PASS':7},cases={key:dict(status='PASS')for key in ids}))))
  p=dict(gate={key:True for key in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')},
   run_identity=dict(tool_head='UNIT_ONLY_HEAD'),writer_runtime=dict(status='PASS'),auth_users_before=0,auth_users_after=0)
  change(a,p);raw=json.dumps(a).encode();pkg=json.dumps(p).encode()
  cfg=dict(accepted_native7=dict(head='UNIT_ONLY_HEAD',original=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),package=dict(bytes=len(pkg),sha256=sha256(pkg).hexdigest())))
  return lambda:m.checked(cfg,raw,pkg,source if current is None else current,ids)

 def test_complete_synthetic_gate_contract_only(self):
  self.assertEqual(self.complete_synthetic()()['fresh_followup_cases'],0)
 def test_failed_full_boundary_refused(self):
  with self.assertRaisesRegex(ValueError,'BOUNDARY_FAILED'):
   self.complete_synthetic(lambda a,p:a.update(baseline_full22_all_rows_all_sequences_equal=False))()
 def test_missing_unused_inverse_refused(self):
  with self.assertRaisesRegex(ValueError,'PREUSE_INVERSE_REQUIRED'):
   self.complete_synthetic(lambda a,p:a.update(focused_preuse_removal={}))()
 def test_other_provider_refused(self):
  with self.assertRaisesRegex(ValueError,'OTHER_BACKEND_REFUSED'):self.complete_synthetic(current=dict(other=True))()
 def test_writer_gate_false_refused(self):
  with self.assertRaisesRegex(ValueError,'PACKAGE_NOT_QUALIFIED'):
   self.complete_synthetic(lambda a,p:p['gate'].update(writer_runtime=False))()
 def test_auth_cleanup_failure_refused(self):
  with self.assertRaisesRegex(ValueError,'AUTH_RESTORE_FAILED'):
   self.complete_synthetic(lambda a,p:p.update(auth_users_after=1))()
if __name__=='__main__':unittest.main()
