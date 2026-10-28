"""Negative source controls only; synthetic bytes cannot become ERP proof."""
from pathlib import Path
import importlib.util,json,unittest
from hashlib import sha256
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('vendor_followup_closed_gate',HERE/'gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Gate(unittest.TestCase):
 def test_unselected_backend_closed(self):
  with self.assertRaisesRegex(ValueError,'CLOSED_NATIVE7'):m.checked(json.loads((HERE/'CONFIG.json').read_bytes()),b'',b'',{},())
 def test_partial_actual_claim_refused(self):
  raw=json.dumps(dict(label='CP7_VENDOR_RECEIVABLE_NATIVE7',status='INCOMPLETE',qualification_commit='synthetic')).encode();pkg=b'{}'
  cfg=dict(accepted_native7=dict(head='synthetic',original=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),package=dict(bytes=len(pkg),sha256=sha256(pkg).hexdigest())))
  with self.assertRaisesRegex(ValueError,'NOT_QUALIFIED'):m.checked(cfg,raw,pkg,{},())
 def test_tampered_original_refused_before_content(self):
  cfg=dict(accepted_native7=dict(original=dict(bytes=2,sha256=sha256(b'{}').hexdigest())))
  with self.assertRaisesRegex(ValueError,'BYTES_CHANGED'):m.checked(cfg,b'[]',b'',{},())
if __name__=='__main__':unittest.main()
