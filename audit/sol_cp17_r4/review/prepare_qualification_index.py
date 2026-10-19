from pathlib import Path
import json,hashlib
A=Path(__file__).resolve().parents[1];out=[]
finite=json.loads((A/'FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json').read_text())
for row in finite['canonical_cases']:out.append(dict(row,review_document='FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json'))
j=json.loads((A/'JOURNEY_Q3_RESULT_REVIEW.json').read_text())
for row in j['cases']:out.append(dict(case_id=row['id'],run_id=j['run_id'],artifact_id=j['artifact_id'],group='/browser',raw_status='PASS',canonical_for_candidate=True,case_kind='REAL_AUTH_BROWSER_BUSINESS',oracle_origin='SOL_CONTRACT_LITERAL_ARITHMETIC_AND_LINEAGE',fixture_origin='WRITER_NATIVE_START_ONLY_THEN_SOL_UI_CONTINUATION',review_document='JOURNEY_Q3_RESULT_REVIEW.json'))
for aid,report,ident,run,group,kind,review in [(12160684624,'SOL_R4_B5_B6_EXCEPTIONS.json','SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP',39193738642,'browser','REAL_AUTH_BROWSER_BUSINESS','JOURNEY_INITIAL_RESULT_REVIEW.json'),(12161202911,'SOL_R4_D01_STATE_CONTROL.json','SOL_R4_D01_MATERIAL_RECOST_STATE_PLUS1',39194063047,'native','DETECTOR_CONTROL','DETECTOR_RESULT_REVIEW.json')]:
 p=A/'ci_receipts/sol_artifacts'/str(aid)/'files'/report
 if not p.exists():
  candidates=list(p.parent.glob('SOL_R4*json'));p=next(x for x in candidates if isinstance(json.loads(x.read_text()),dict) and group in json.loads(x.read_text()) and ident in json.loads(x.read_text())[group].get('cases',{}))
 d=json.loads(p.read_text());assert d[group]['cases'][ident]['status']=='PASS'
 out.append(dict(case_id=ident,run_id=run,artifact_id=aid,group='/'+group,raw_status='PASS',canonical_for_candidate=True,case_kind=kind,oracle_origin='SOL_EXPLICIT_LITERAL_AND_ACTIVE_SOURCE_CONTRACT',fixture_origin='ACCEPTED_NATIVE_SYNTHETIC_START',review_document=review))
mutable=json.loads((A/'MUTABLE_DETECTOR_RESULT_REVIEW.json').read_text())
for row in mutable['canonical_cases']:out.append(dict(row,review_document='MUTABLE_DETECTOR_RESULT_REVIEW.json'))
expected=18
if (A/'DERIVED_DETECTOR_RESULT_REVIEW.json').exists():
 derived=json.loads((A/'DERIVED_DETECTOR_RESULT_REVIEW.json').read_text())
 for row in derived['canonical_cases']:out.append(dict(row,review_document='DERIVED_DETECTOR_RESULT_REVIEW.json'))
 expected+=len(derived['canonical_cases'])
if (A/'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').exists():
 disputed=json.loads((A/'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').read_text())
 for row in disputed['canonical_cases']:out.append(dict(row,review_document='PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json'))
 expected+=len(disputed['canonical_cases'])
assert len(out)==len({r['case_id']for r in out})==expected
p=A/'ci_receipts/SOL_QUALIFIED_CASE_INDEX.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n'for r in out));print('canonical_qualified_ids',len(out),'business',sum('BUSINESS'in r['case_kind']for r in out),'pure',sum(r['case_kind']=='CLIENT_PURE_HELPER'for r in out),'detector',sum(r['case_kind']=='DETECTOR_CONTROL'for r in out))
