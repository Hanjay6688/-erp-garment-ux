"""Exact prepared caller source admission; no database or runtime credit."""
from hashlib import sha256
from pathlib import Path
import json,subprocess
import cp7_frozen_finance_bridge as stage
from cp7_production_stage import _body
from cp7_frozen_analysis_v2.render import block
from cp7_bounded_analysis_stage import source

root=Path(__file__).resolve().parents[1]
manifest=stage.MANIFEST
official=subprocess.check_output(['git','-C',str(root),'show',manifest['official_A_head']+':scripts/cp7_finance_capture/finance_capture.sql'])
assert sha256(official).hexdigest()==manifest['official_A_finance_SQL_sha256']
qualified=subprocess.check_output(['git','-C',str(root),'show','efa800cd:scripts/cp7_finance_capture/finance_capture.sql'])
assert official==qualified,'FROZEN_FINANCE_OFFICIAL_API_NOT_SAME_QUALIFIED_SOURCE'
for signature,expected in manifest['official_dependencies'].items():
 assert sha256(_body(block(official.decode(),signature.split('(')[0])).encode()).hexdigest()==expected['body_sha256']
originals={stage.patches.REQUEST:stage.units.render.request_candidate(),stage.patches.STATUS:source.block('analysis-stages.sql','cp7_analysis_stage.status')}
assert{sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals.items()}==manifest['before_body_sha256']
patched=stage.patches.patched(originals)
assert set(patched)==set(originals)
for signature in originals:assert patched[signature]!=originals[signature]
assert patched[stage.patches.REQUEST].count('cp7_finance_capture.start(')==1
assert "c:=c||jsonb_build_object('finance_sidecar_mode','STAGED')"in patched[stage.patches.REQUEST]
assert 'update cp7_analysis_stage.jobs'not in patched[stage.patches.REQUEST]
assert 'finance_apply'not in patched[stage.patches.REQUEST]
for marker in ('CP7:ANALYSIS-REQUEST:','cp7_frozen_analysis_units_v2.source(q,true)','insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);'):
 assert originals[stage.patches.REQUEST].count(marker)==patched[stage.patches.REQUEST].count(marker)==1
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',contract=manifest['contract'],official_A_finance_SQL_exact_qualified_bytes=True,official_private_API_bodies=3,exact_predecessor_bodies=2,existing_source_snapshot_and_request_lock_preserved=True,existing_consumer_SQL_reused=True,financial_formula_added=False,actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)))
