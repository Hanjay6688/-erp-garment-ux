"""Build reviewable ledgers from original auditor-run artifacts, never execute product tests."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PROOF=ROOT.parent/'sol-r2-proof'
CANDIDATE='2e9d6a468c110684c278d585418eb404250d1150'
TREE='5e50d224f8e74fa3bca83b599fb606739435b598'
PRIOR='278a95cea5655c23f6bc94d1eb97959cdaaca5d6'

def read(path):return json.loads(Path(path).read_text())
def save(name,value):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(group):return group.get('cases',group.get('races',{}))

F03={
 'p09':(38933274002,117082325857,12060247667),
 'p10':(38933274002,117082325912,12060500752),
 'p11':(38933274002,117082325428,12060276925),
 'p12':(38933274002,117082325742,12060312347),
 'p13':(38933274002,117082326252,12060440957),
 'cash_installments':(38933274002,117082325871,12060008782),
 'supplier_credit':(38933274002,117082325750,12060138445),
 'customer_refund':(38933274002,117082325960,12060421019),
}
SUITES=[];LEDGER=[]
def group(label,result,run,job,artifact,member,layer,smoke=False,origin='INDEPENDENT_NATIVE_RERUN'):
 case_rows=rows(result);counts=dict(Counter(x['status']for x in case_rows.values()))
 if result.get('counts') is not None:assert counts==result['counts'],(label,counts,result['counts'])
 for key,row in case_rows.items():
  LEDGER.append(dict(suite=label,id=key,status=row['status'],protocol_status='FAIL'if row['status']=='COUNTEREXAMPLE'else row['status'],
   layer=layer,smoke=smoke,evidence_origin=origin,run_id=run,job_id=job,artifact_id=artifact,member=member,
   full_boundary_restored=row.get('full_boundary_restored'),public_schema_unchanged=row.get('public_schema_unchanged'),
   session_leaks=row.get('session_leaks'),business_day=row.get('business_day')))
 return dict(label=label,status=result.get('status'),counts=counts,case_executions=len(case_rows),layer=layer,smoke=smoke,
  evidence_origin=origin,run_id=run,job_id=job,artifact_id=artifact,member=member,
  original_sha256=sha(PROOF/str(artifact)/member))

for bucket,(run,job,artifact)in F03.items():
 member='CP7_F03_FULL_'+bucket.upper()+'.json';report=read(PROOF/str(artifact)/member)
 assert report['source_commit']==CANDIDATE and report['source_tree']==TREE
 assert report['status']=='PASS'and report['cp6_restored']and report['advisor_gate']
 groups=[]
 for spec in report['predeclared_groups']:
  key=spec['key'];result=report['groups'][key]
  row=group('F03/'+bucket+'/'+key,result,run,job,artifact,member,spec['kind'],spec['smoke'])
  assert row['case_executions']==spec['expected_executions']and set(row['counts'])=={'PASS'}
  groups.append(row)
 SUITES.append(dict(label='F03/'+bucket,status=report['status'],case_executions=report['observed_case_count'],smokes=report['observed_smoke_count'],
  groups=groups,cp6_restored=True,advisor_gate=True,bundle_sha256=report['source_sha256'],private_roles=report['private_role_count']))
assert sum(x['case_executions']for x in SUITES)==447
assert sum(x['smokes']for x in SUITES)==3

run,job,artifact=38933273755,117082323906,12060741008
member='CP7_CP17_FIXES.json';report=read(PROOF/str(artifact)/member)
assert report['status']=='PASS'and report['observed_case_count']==145
groups=[group('CP17/'+k,report[k],run,job,artifact,member,k)for k in ['native','races','http','browser']]
assert {x['layer']:x['counts']for x in groups}=={k:{'PASS':n}for k,n in {'native':80,'races':18,'http':14,'browser':33}.items()}
SUITES.append(dict(label='CP17',status='PASS',case_executions=145,groups=groups,cp6_restored=report['cp6_restored'],advisor_gate=report['advisor_gate'],bundle_sha256=report['source_sha256']))
for member,layer in [('SOL_R2_LITERAL.json','native'),('SOL_R2_CORRECTION_HTTP.json','http')]:
 d=read(PROOF/str(artifact)/member);SUITES.append(group(member[:-5],d,run,job,artifact,member,layer))
for member,run,job,artifact,layer in [
 ('SOL_R2_NEW_RESULT.json',38934111700,117085146759,12059209949,'native'),
 ('SOL_R2_UAT_RESULT.json',38934752606,117087318107,12061690189,'browser_actual_UAT_build_via_disposable_transport'),
 ('OWNER_CONTROLLER_QUALIFICATION.json',38933273784,117082324619,12059484527,'owner_install')]:
 d=read(PROOF/str(artifact)/member)
 if member.startswith('OWNER_'):d['cases']={k:dict(status=v)for k,v in d['cases'].items()}
 SUITES.append(group(member[:-5],d,run,job,artifact,member,layer))

for mode,run,job,artifact in [
 ('DEMO_SIMULATION',38934111778,117085148136,12061690230),
 ('DISPOSABLE_TEST',38934111778,117085147512,12060306726),
 ('UAT_AUTH_SIMULATION',38937763036,117097460133,12061078788)]:
 matches=list((PROOF/str(artifact)).rglob(mode+'.json'))
 if not matches:continue
 member=str(matches[0].relative_to(PROOF/str(artifact)));d=read(matches[0])
 assert d['status']=='PASS'and d['counts']=={'PASS':96}
 SUITES.append(group('UI_MOCK/'+mode,d,run,job,artifact,member,'browser_mock',origin='INDEPENDENT_UI_MOCK_RERUN'))

optional=PROOF/'LATE_ARTIFACT_BINDINGS.json'
if optional.exists():
 for binding in read(optional):
  artifact=binding['artifact_id'];member=binding['member'];p=PROOF/str(artifact)/member
  if not p.exists():continue
  d=read(p)
  if 'groups'in d:
   gs=[group(binding['label']+'/'+k,g,binding['run_id'],binding['job_id'],artifact,member,
     'browser'if 'browser'in k else k)for k,g in d['groups'].items()]
  else:
   gs=[group(binding['label']+'/'+k,d[k],binding['run_id'],binding['job_id'],artifact,member,k)for k in ['native','races','http','browser']]
  SUITES.append(dict(label=binding['label'],status=d['status'],case_executions=d['observed_case_count'],groups=gs,
   cp6_restored=d['cp6_restored'],advisor_gate=d['advisor_gate'],bundle_sha256=d['source_sha256']))
  for name,observation in d.get('runtime_diagnostics',{}).items():
   SUITES.append(group('DIAGNOSTIC/'+name,observation['result'],binding['run_id'],binding['job_id'],artifact,member,
    'historical_runtime_diagnostic',origin='INDEPENDENT_NATIVE_RERUN_ZERO_ACCEPTANCE_CREDIT'))

save('SUITE_RESULTS.json',dict(protocol_evidence_origin='INDEPENDENT_NATIVE_RERUN',runtime_subject_qualification='browser_mock proves only real Chromium CI UI rendering with mocked Auth/business403; no Native business success claim',candidate_sha=CANDIDATE,candidate_tree=TREE,unique_oracle_total_claim=False,
 counts_are_execution_contexts=True,production_go=False,source_suites=SUITES))
save('CASE_LEDGER.json',dict(protocol_evidence_origin='INDEPENDENT_NATIVE_RERUN',runtime_subject_qualification='See layer and per-case scope; browser_mock is UI-only',candidate_sha=CANDIDATE,unique_oracle_total_claim=False,counts=dict(Counter(x['status']for x in LEDGER)),
 by_layer={layer:dict(Counter(x['status']for x in LEDGER if x['layer']==layer))for layer in sorted({x['layer']for x in LEDGER})},cases=LEDGER))

new=read(PROOF/'12059209949/SOL_R2_NEW_RESULT.json')['cases']
finding=dict(id='SOL-R2-001',severity='S2',status='OPEN',title='Nomor PO otomatis ke-1.000 pada tanggal yang sama tidak selesai dibuat',
 novelty='NEW_SOL_INDEPENDENT',evidence_level='NATIVE_QUALIFIED',evidence_origin='INDEPENDENT_NATIVE_RERUN',
 candidate_sha=CANDIDATE,locations=['scripts/cp7-src/cutting-correction/auto-po.sql:211-217'],
 requirements_violated=['D15-6','Owner performance: save <=2 seconds'],protected_invariants_observed=['INV-C04','INV-C06'],raw_status='COUNTEREXAMPLE',protocol_status='FAIL',
 proof=dict(run_id=38934111700,job_id=117085146759,artifact_id=12059209949,member='SOL_R2_NEW_RESULT.json',
  control=new['SOL_R2_AUTO_PO_NUMBER_999_CONTROL'],counterexample=new['SOL_R2_AUTO_PO_NUMBER_1000_BOUNDED']),
 impact='Buat Potongan tidak dapat menambah PO setelah nomor harian 001–999 terpakai. Command memegang kunci nomor tanggal itu selama menunggu; permintaan tanggal sama dapat ikut tertahan (dampak kunci dari tinjauan sumber). Uji tidak meninggalkan PO, stok atau jurnal setengah jadi.',
 cause="lpad(v_n::text,3,'0') memotong teks 1000 menjadi 100; pencarian kembali menguji nomor 100–999 yang sudah ada. Kontrol 999 selesai 0,040 detik; batas 1000 mencapai timeout 3,003 detik tepat pada WHILE itu.",
 suggested_fix='Jadikan tiga digit sebagai lebar minimum, bukan panjang maksimum. Pertahankan penguncian per tanggal, keunikan dan UUID idempoten. Alternatif batas kapasitas harus menolak secara jelas dan cepat; jangan menaikkan timeout sebagai penyelesaian.',
 acceptance_tests=['998→999→1000→1001 dan 9999→10000 menghasilkan nomor unik yang tidak terpotong.',
  'Dua sesi pada batas 999/1000 serta UUID sama menghasilkan tepat satu PO dan satu efek stok per permintaan sah.',
  'Kegagalan setelah PO dibuat tetap membatalkan PO, stok, jurnal dan nomor; simpan draf tidak membuat PO.',
  'Tanggal potong WIB menentukan nomor; batas tanggal berganti tidak saling mengunci.'],production_go=False)
save('FINDINGS.json',dict(candidate_sha=CANDIDATE,product_fixes_made=False,new_findings=[finding],
 known_open_items=[dict(id='KNOWN-R2-POOL-UI',severity='S1',status='OPEN_MISSING_UI_LIFECYCLE',novelty='WRITER_DISCLOSED_NOT_NEW_SOL',
  scope='Pool HPP absensi: preview/buat/aktifkan/batalkan lewat aplikasi belum tersedia.',
  evidence_origin='INDEPENDENT_SOURCE_REVIEW',proof='Tidak ada pemanggil create/activate/cancel_attendance_hpp_pool di src atau scripts/cp7-src; Native erp writers ada, dan CP17_HPP01 membuktikan aturan cancel→policy→replacement di SQL. D15-2 menyembunyikan absensi, bukan menerima penghilangan siklus pool.',
  impact='Pengguna yang perlu membatalkan pool aktif untuk memperbaiki sumber/upah/kebijakan diarahkan membatalkan pool, tetapi langkah itu belum mempunyai jalur layar.',
  suggested_fix='Sediakan layar siklus pool yang memakai writer Native, review/version, izin saat ini, riwayat dan penghalang periode; uji create→activate→blocked correction→cancel→correct→replacement dari layar.'),
 dict(id='KNOWN-RECEIPT-FIRST100',severity='S3',status='OPEN_WRITER_DISCLOSED',novelty='NOT_NEW_SOL',
  scope='scripts/cp7_ci_receipt.py hanya membaca halaman pertama daftar run dan job.',evidence_origin='INDEPENDENT_SOURCE_REVIEW',
  proof='Baris 28/31 memakai per_page=100 tanpa page; receipt r2 dihasilkan writer dengan salinan yang sudah dipaginasi. Verifikasi auditor memakai kedua halaman, bukan skrip itu.',
  suggested_fix='Paginasi seluruh run/job dan anotasi sebelum menyatakan receipt lengkap; uji 101+ baris dan workflow dengan >100 job.')]))
print(json.dumps(dict(suites=len(SUITES),case_contexts=len(LEDGER),by_layer=read(OUT/'CASE_LEDGER.json')['by_layer'],new_findings=1)))
