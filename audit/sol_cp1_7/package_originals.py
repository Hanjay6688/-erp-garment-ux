"""Durable report-only archive: exact JSON/SARIF bytes, no dumps or screenshots."""
import hashlib,io,json,lzma,re,tarfile
from pathlib import Path
R=Path(__file__).parent;E=R/'evidence';members={};aliases={}
for p in sorted((E/'original-reports').rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 assert not re.search(rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}',raw),('JWT_CREDENTIAL_REVIEW_REQUIRED',str(p))
 members.setdefault(sha,raw);aliases[str(p.relative_to(E/'original-reports'))]=sha
out=Path('/workspace/scratch/5969cedfb83c/deliverables');out.mkdir(exist_ok=True)
archive=out/'SOL_CP1_7_NATIVE_ORIGINALS.tar.xz'
temporary=out/'SOL_CP1_7_NATIVE_ORIGINALS.tar.xz.building'
with lzma.open(temporary,'wb',preset=3)as xz,tarfile.open(fileobj=xz,mode='w|')as tar:
 def put(name,raw):
  info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(raw))
 for sha,raw in sorted(members.items()):put('by-sha256/'+sha+'.json',raw)
 put('ALIASES.json',json.dumps(aliases,sort_keys=True,indent=2).encode())
 for name in ['ARTIFACT_REGISTER.json','MEMBER_INDEX.json','REPORT_IDENTITIES.json','GROUP_LEDGER.json','CASE_LEDGER.json','BE_LOG_RECOVERY.json']:
  put('metadata/'+name,(E/name).read_bytes())
 put('metadata/SOURCE_INVENTORY.json',(R/'SOURCE_INVENTORY.json').read_bytes())
 put('README.txt',b'Original JSON/SARIF bytes are named by SHA256. ALIASES.json maps original artifact/member path to its exact hash. Metadata retains run/artifact identities and raw outcomes. No unique-oracle total is claimed. Extract into a new directory and verify every by-sha256 filename. This archive contains only this auditor synthetic test reports; no original CP2 dump/key, screenshots, SQL database dumps, or ephemeral signed URLs.\n')
temporary.replace(archive)
receipt=dict(file_name=archive.name,local_path=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),compressed_bytes=archive.stat().st_size,original_report_files=len(aliases),unique_byte_reports=len(members),original_bytes=sum(map(len,members.values())),original_bytes_unchanged=True,aliases_preserved=True,no_CP2_dump_or_key=True,no_screenshots=True,no_unique_oracle_total_claim=True,production_go=False)
(R/'PROOF_ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
