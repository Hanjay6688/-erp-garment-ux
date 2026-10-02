"""Retain exact Native F03 reports; never sum overlapping group oracles."""
import gzip,hashlib,json,sys,zipfile
from pathlib import Path

def main():
 manifest=json.loads(Path(sys.argv[1]).read_text());root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True)
 receipts=[]
 for f in manifest:
  path=Path(f['path']);data=path.read_bytes();assert len(data)==f['size']and 'sha256:'+hashlib.sha256(data).hexdigest()==f['digest']
  bucket=f['name'].removeprefix('cp7-f03-full-');out=root/bucket;out.mkdir(exist_ok=True)
  with zipfile.ZipFile(path)as z:
   originals={n:z.read(n).decode('UTF8')for n in z.namelist()if '/'not in n and n.endswith('.json')}
   native_name=next(n for n in originals if n.startswith('CP7_F03_FULL_'));r=json.loads(originals[native_name]);package=json.loads(originals['T3_PACKAGE_INSTALL.json']);backup=json.loads(originals['T3_BACKUP_RESTORE_DRILL.json'])
   assert r['source_commit']=='656e4fd5944b6061a87fd0a388d2b928563ac398'and r['source_tree']=='d0a70ed59c8dedbe88ab0b16a214a4da4201449a'
   assert r['status']=='PASS'and r['observed_case_count']==r['expected_case_count']and r['observed_smoke_count']==r['expected_smoke_count']and r['groups_complete']
   assert r['cp6_restored']and r['advisor_gate']and all(r['restore_components'].values())
   assert package['primary_unchanged']and package['gate']['writer_runtime']and package['auth_users_after']==package['auth_users_before']==0
   assert backup['status']=='RESTORED_SAME_MEANING'
   groups={}
   for name,g in r['groups'].items():
    groups[name]={k:g[k]for k in ('status','counts','complete_boundary_restored','cleanup_failures','auth_counts','host_status')if k in g}
    if 'cleanup_failures'in g:assert g['cleanup_failures']is False
    if 'auth_counts'in g:assert g['auth_counts']['restored']
   raw=json.dumps(dict(contract='cp7.retained-originals.v1',source_commit=r['source_commit'],root_json_utf8=originals),ensure_ascii=False,separators=(',',':')).encode()
   (out/'ORIGINAL_REPORTS.json.gz').write_bytes(gzip.compress(raw,mtime=0))
   receipt=dict(status='NATIVE_WRITER_PASS',source_commit=r['source_commit'],source_tree=r['source_tree'],run_id=36953696925,
    artifact_id=f['artifactId'],artifact_name=f['name'],original_file_id=f['fileId'],zip_bytes=len(data),zip_sha256=hashlib.sha256(data).hexdigest(),
    bucket=bucket,expected_case_count=r['expected_case_count'],observed_case_count=r['observed_case_count'],expected_smoke_count=r['expected_smoke_count'],observed_smoke_count=r['observed_smoke_count'],
    source_bundle_sha256=r['source_sha256'],manifest_sha256=r['manifest_sha256'],provider_sha256=r['provider_sha256'],retained_probe_sha256=r['retained_probe_sha256'],
    groups=groups,restore_components=r['restore_components'],cp6_restored=r['cp6_restored'],advisor_gate=r['advisor_gate'],package_gate=package['gate'],primary_unchanged=package['primary_unchanged'],
    auth_users_before=package['auth_users_before'],auth_users_after=package['auth_users_after'],backup_restore_status=backup['status'],backup_checks=backup['checks'],
    original_root_reports={n:hashlib.sha256(text.encode()).hexdigest()for n,text in originals.items()},
    all_zip_members={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest())for n in sorted(z.namelist())if not n.endswith('/')},
    unique_oracle_total_claim=False,full_family_acceptance=False,independent_acceptance=False,production_go=False)
   (out/'RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');receipts.append(receipt)
 summary=dict(status='ALL_EIGHT_NATIVE_F03_BUCKETS_WRITER_PASS',source_commit=receipts[0]['source_commit'],source_tree=receipts[0]['source_tree'],run_id=36953696925,
  buckets={r['bucket']:{k:r[k]for k in ('expected_case_count','observed_case_count','expected_smoke_count','observed_smoke_count','artifact_id','zip_sha256','primary_unchanged','cp6_restored','advisor_gate')}for r in receipts},
  unique_oracle_total_claim=False,independent_acceptance=False,full_family_acceptance=False,production_go=False)
 (root/'RECEIPT.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary))
if __name__=='__main__':main()
