"""Retain the complete failed Native269 Original without promoting its gates."""
import gzip,hashlib,json,sys,zipfile
from pathlib import Path

def main():
 archive=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
 data=archive.read_bytes();digest=hashlib.sha256(data).hexdigest()
 assert len(data)==255285330 and digest=='dd8aa0bce32b5f41ac2d41367fe887d3ad717da5d075dd493dac25526cf735fe'
 with zipfile.ZipFile(archive)as z:
  originals={n:z.read(n).decode('UTF8')for n in z.namelist()if '/'not in n and n.endswith('.json')}
  r=json.loads(originals['CP7_F05_NATIVE_ATTENTION.json']);pkg=json.loads(originals['T3_PACKAGE_INSTALL.json'])
  identity=pkg['run_identity'];assert identity['tool_head']=='656e4fd5944b6061a87fd0a388d2b928563ac398'and str(identity['run_id'])=='36953696884'
  assert r['status']=='INCOMPLETE'and r['expected_case_count']==269 and r['observed_case_count']==235
  assert r['required_case_counts']==dict(native=171,races=37,http=27,browser=34)
  assert pkg['gate']['primary_unchanged']is False and pkg['gate']['writer_runtime']is False
  assert pkg['auth_users_before']==0 and pkg['auth_users_after']==32
  envelope=json.dumps(dict(contract='cp7.retained-originals.v1',source_commit=identity['tool_head'],root_json_utf8=originals),ensure_ascii=False,separators=(',',':')).encode()
  (dest/'ORIGINAL_REPORTS.json.gz').write_bytes(gzip.compress(envelope,mtime=0))
  counts={name:r[name].get('counts')for name in('native','races','http','browser')}
  failures={}
  for group in counts:
   cases=r[group].get('cases',r[group].get('races',{}))
   failures[group]={name:row['status']for name,row in cases.items()if row.get('status')!='PASS'}
  receipt=dict(status='NATIVE_WRITER_INCOMPLETE',source_commit=identity['tool_head'],source_tree='d0a70ed59c8dedbe88ab0b16a214a4da4201449a',run_id=36953696884,job_id=110671915559,
   artifact_id=11205539184,original_file_id='file_000000007c7882078e6311cc1a69606b',zip_bytes=len(data),zip_sha256=digest,
   source_bundle_sha256=r['source_sha256'],expected_case_count=r['expected_case_count'],observed_case_count=r['observed_case_count'],required_case_counts=r['required_case_counts'],counts=counts,
   browser_observed_counts={s:sum(1 for row in r['browser']['cases'].values()if row.get('status')==s)for s in('PASS','INCOMPLETE','FAIL')},browser_observed_counts_are_not_formal_acceptance=True,
   failures=failures,restore_components=r['restore_components'],cp6_restored=r['cp6_restored'],advisor_gate=r['advisor_gate'],package_gate=pkg['gate'],primary_unchanged=pkg['primary_unchanged'],
   auth_users_before=pkg['auth_users_before'],auth_users_after=pkg['auth_users_after'],browser_cleanup_failures=r['browser']['cleanup_failures'],
   original_root_reports={n:hashlib.sha256(raw.encode()).hexdigest()for n,raw in originals.items()},
   all_zip_members={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest())for n in sorted(z.namelist())if not n.endswith('/')},
   full_family_acceptance=False,independent_acceptance=False,production_go=False)
  (dest/'RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:receipt[k]for k in('status','run_id','expected_case_count','observed_case_count','counts','package_gate','auth_users_before','auth_users_after')}))
if __name__=='__main__':main()
