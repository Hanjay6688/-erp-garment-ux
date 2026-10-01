"""Retain exact qualification reports and expose a source-bound safe receipt."""
from pathlib import Path
import sys,json,hashlib,gzip,zipfile
def main():
 archive=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
 expected_bytes=138502324;expected_sha='833cdecb6c70193aef9809b1191863f4feb4b8c317d70ef182a442ed26ac1347'
 assert archive.stat().st_size==expected_bytes and hashlib.sha256(archive.read_bytes()).hexdigest()==expected_sha,'RETAINED_NATIVE155_ARCHIVE_IDENTITY'
 names=('ALIGNED_CHAIN.json','CP7_F05_NATIVE_ATTENTION.json','T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json','T3_PACKAGE_INSTALL.json')
 originals={};members={}
 with zipfile.ZipFile(archive)as z:
  for name in names:
   found=[p for p in z.namelist()if Path(p).name==name];assert len(found)==1,('ORIGINAL_MEMBER',name,found)
   raw=z.read(found[0]);originals[name]=json.loads(raw);compressed=gzip.compress(raw,mtime=0);(dest/(name+'.gz')).write_bytes(compressed)
   members[name]=dict(member=found[0],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),gzip_sha256=hashlib.sha256(compressed).hexdigest())
 r=originals['CP7_F05_NATIVE_ATTENTION.json'];pkg=originals['T3_PACKAGE_INSTALL.json'];pkg=pkg.get('t3_package_run',pkg)
 identity=pkg['run_identity'];assert identity['tool_head']=='928332db2aafa2317271eeed22430719a57bd5b9'and str(identity['run_id'])=='36814071634','RETAINED_NATIVE155_SOURCE_IDENTITY'
 assert r['status']=='PASS'and r['expected_case_count']==155 and r['observed_case_count']==155
 assert r['source_sha256']=='6f349f70eebd4e5d367d436ee3d815fddf6f8d1af5112a73c2a0c205dfa60f4a'
 assert r['cp6_restored']and len(r['restore_components'])==3 and all(r['restore_components'].values())and r['advisor_gate']
 counts={name:r[name]['counts']for name in('native','races','http','browser')};assert counts==dict(native=dict(PASS=103),races=dict(PASS=19),http=dict(PASS=13),browser=dict(PASS=20)),counts
 for name in counts:assert r[name].get('database_remaining',0)==0
 assert pkg['primary_unchanged']and pkg['auth_users_before']==pkg['auth_users_after']==0
 receipt=dict(source_commit=identity['tool_head'],run_id=36814071634,artifact_id=11141076740,archive_bytes=expected_bytes,archive_sha256=expected_sha,status=r['status'],source_sql_sha256=r['source_sha256'],expected_case_count=155,observed_case_count=155,counts=counts,restore_components=r['restore_components'],advisor_gate=r['advisor_gate'],native_public_catalog_comparison=r.get('native_public_catalog_comparison'),original_reports=members,primary_unchanged=pkg['primary_unchanged'],auth_users_before=pkg['auth_users_before'],auth_users_after=pkg['auth_users_after'],full_family_acceptance=False,independent_acceptance=False,production_go=False)
 (dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('CP7_RETAINED_NATIVE155_928332D_RECEIPT '+json.dumps(receipt),flush=True)
if __name__=='__main__':main()
