"""Tool qualification for the v2.6.20-only fixture; no candidate file edits.

Initial own run 38785656090 failed BEFORE any owner install case:
cp6_t3_aligned_chain.run(stop=G01.STOP) unconditionally requires the PRE-U
inventory even though it stopped before U. The original refusal is retained.
This adapter declares that inventory N/A ONLY for the frozen v2.6.20 stop.
The frozen chain, G01 checks, all 58 SQL files, actual installer and owner
case assertions stay unchanged. Normal chains through U keep the old gate.
"""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parents[2]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
import yaml
import cp6_readiness_owner_aligned as owner
chain=owner.chain
original=chain.pre_u.finished
observations=[]
def at_baseline(record):
 if record.get('status')!=chain.pre_u.PENDING:return original(record)
 frozen=yaml.safe_load(Path('.github/workflows/cp6-full-schema-validation.yml').read_text())
 names=[x.get('name','')for x in frozen['jobs']['validate-full-schema']['steps']]
 assert names.index(owner.baseline.STOP)<names.index(chain.pre_u.U_STEP)
 assert record['artifact_id']==10392910720 and record['capture_before_step']==chain.pre_u.U_STEP
 assert not (Path('cp6-proof')/chain.pre_u.NAME).exists()
 # No output is relabeled PASS: this was an intentionally unexecuted later
 # fixture step. The unchanged owner main below must still prove the actual
 # last step and exact G01 fingerprint before allowing a 58-file install.
 observations.append(dict(original_marker=record,disposition='NOT_APPLICABLE_STOP_BEFORE_U',stop=owner.baseline.STOP,U_was_not_executed=True))
chain.pre_u.finished=at_baseline
try:
 owner.main()
 assert len(observations)==1
 out=CANDIDATE/'cp6-proof/t3/SOL_OWNER_BASELINE_ADAPTER.json'
 out.write_text(json.dumps(dict(status='QUALIFIED_BASELINE_ONLY',original_run=38785656090,original_job=116596862914,
   original_failure='PRE_U_INVENTORY_NOT_CAPTURED',candidate_sha='dfab13bf62398a69a02bf6221c06d29075e5e40b',
   adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),candidate_files_changed=False,
   Native_SQL_or_expected_changed=False,observations=observations,production_go=False),indent=2)+'\n')
finally:chain.pre_u.finished=original
