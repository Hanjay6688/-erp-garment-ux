"""Final finding, invariant and boundary dispositions; no business test execution."""
from build_evidence import *

def finding(id,severity,title,origin,level,location,impact,proof,fix,tests,product_bug=True):
    return dict(id=id,severity=severity,title=title,origin=origin,evidence_level=level,status='OPEN',product_bug=product_bug,
      first_seen_sha=CANDIDATE,retested_sha=CANDIDATE,locations=location,impact=impact,proof=proof,
      suggested_fix=fix,acceptance_tests=tests,production_go=False)
F=[]
F.append(finding('SOL-R1-001','S1','Koreksi pemasukan yang telah dipakai ditolak walau saldo akhir sah, termasuk koreksi catatan saja',
 'NEW_SOL_INDEPENDENT','NATIVE_QUALIFIED',
 ['scripts/cp7-src/finance/dated-guards.sql:39-57','scripts/cp7-src/sales/payment-correction.sql:177-201'],
 'Koreksi pembayaran pelanggan macet; pembaruan AR/kas yang sah tidak bisa diselesaikan. Tidak ada bukti saldo rusak: seluruh efek ditolak atomik.',
 dict(run_id=38787925433,job_id=116604642907,artifact_id=11998368969,member='SOL_CORRECTION_QUALIFIED.json',
   native_case='SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE',
   real_auth_http_cases=['SOL_HTTP_SPENT_INCOME_CORRECTION_FINAL_POSITIVE','SOL_HTTP_SPENT_INCOME_NOTE_ONLY_CORRECTION'],
   input=dict(income='30.01',spent='20.00',bank_before='10.01',replacement='25.01'),
   expected=dict(bank_after='5.01',outcome='COMMITTED_OUTCOME'),
   observed=dict(http_status=400,sqlstate='P0001',code='CP7_CASH_NEGATIVE',temporary_minimum='-20.00',bank_after='10.01'),
   controls=['Unspent 30.01→25.01 succeeds','Spent 20, replacement 15.01 genuinely negative is refused'],
   boundary_unchanged_on_failure=True,raw_status='COUNTEREXAMPLE',protocol_status='FAIL'),
 'Validasi saldo akhir keseluruhan command atomik, dengan penguncian rekening dan pemeriksaan semua tanggal tetap berlaku. Jangan melemahkan pengaman pengeluaran biasa. Pembalik dan pengganti harus dapat selesai sebelum penilaian akhir, lalu wajib gagal sebelum commit bila ada saldo kronologis negatif.',
 ['Spent/unspent; amount naik/turun/tetap; note-only; bank sama/berbeda; backdate/later-day prefix; dua sesi; UUID replay/payload berubah; inverse tanpa replacement; seluruh stok/HPP/AR/GL dan batas privat tetap pulih.'],True))
F.append(finding('SOL-R1-002','S1','PO produksi harian baru tidak punya jalur biasa dari aplikasi',
 'NEW_SOL_SOURCE_TRACE','STATIC',
 ['src/ConnectedCuttingPage.tsx:193,355','supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql:715-717',
  'src/NativePlanDraftPanel.tsx:55-74','scripts/cp7-src/plan-native/preflight.sql:71',
  'supabase/migrations/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.sql:647'],
 'Rantai B2 hanya berjalan bila PO aktif sudah tersedia. Operator tidak bisa memulai PO harian baru lewat jalur produksi biasa. Penjadwalan/analisis hanya menyimpan rencana, bukan PO Native. OPEN_PO memang ada melalui impor saldo awal dan menandainya sebagai legacy/migration; itu tidak disamarkan sebagai writer PO harian.',
 dict(source_register='SOURCE_REVIEW.json',browser_inventory='DISPOSABLE_TEST/desktop/cutting-roll and UAT_AUTH_SIMULATION/phone/cutting-roll',
   scan=['all src TS/TSX','all scripts/cp7-src SQL','supabase migrations and bootstrap function bodies'],
   only_insert_writer_found='erp.apply_migration_open_pos',native_runtime_absence_claim=False,
   fixtures_create_po_via_direct_sql='scripts/cp7_cp17_fix_cases.py:152,166,194'),
 'Sediakan alur PO harian Native dari Buat Potongan/menu produksi: identitas PO, model/ukuran/target, izin dan UUID, validasi ulang serta pembaca hilir. Jangan menjadikan impor saldo awal/legacy sebagai jalan transaksi produksi harian.',
 ['Mulai dari model/master sah tanpa PO; buat PO lewat UI→public facade→Native; lanjut potong/pickup/jahit/laundry/QC/selesai PO. Verifikasi nomor ganda, izin, versi, replay dan tidak ada jurnal/stok sebelum tahap yang memang memosting.'],False))
F.append(finding('SOL-R1-003','S3','Pengganti arsip pre-U menolak baseline helper yang sengaja berhenti sebelum U',
 'NEW_SOL_TEST_TOOL_TRACE','NATIVE_QUALIFIED_TEST_INFRA',
 ['scripts/cp6_t3_aligned_chain.py:88','scripts/cp6_pre_u_inventory.py:78-80'],
 'Alat pembentukan baseline v2.6.20 untuk uji pemasang 58 berkas berhenti sebelum kasus Native pemasangan berjalan. Bukan bukti paket Native gagal dipasang.',
 dict(original_run=38785656090,original_job=116596862914,error='PRE_U_INVENTORY_NOT_CAPTURED',
   root='unconditional finished(PENDING) despite stop=G01.STOP occurring before U',
   qualified_run=38787131786,qualified_job=116601912076,qualification='OWNER_TOOL_QUALIFICATION.json',
   result='Original 58 exact files and 10 owner cases PASS after auditor-only stop-aware adapter; original failure retained'),
 'Wajibkan capture selesai hanya bila langkah U memang termasuk jalur yang dieksekusi. Bila berhenti sebelumnya, catat NOT_APPLICABLE_BEFORE_U; setelah U tetap fail-closed pada pending/count/names mismatch. Simpan laporan baseline juga ketika assertion menolak.',
 ['Stop G01/v2.6.20 before U tanpa capture sah; stop sesudah U dengan capture sah; pending setelah U ditolak; count/names/frozen-function mismatch ditolak. Tidak mengubah X admission atau SQL pemasang.'],False))
for key,page,width,location in [('004','qc',669,['src/QcFinalPage.tsx','DEMO_SIMULATION/phone/qc']),('005','hpp',627,['src/HppPage.tsx:298-305','src/hpp.css:23','DEMO_SIMULATION/phone/hpp'])]:
    F.append(finding('SOL-R1-'+key,'S2',f'Layar demo {"QC" if page=="qc" else "HPP"} melebar keluar viewport HP 390 px',
      'NEW_SOL_BROWSER_OBSERVATION','BROWSER_CHROMIUM_HTTP_MOCK',location,
      'Konten/angka di sisi kanan membutuhkan geser halaman; ini cacat tata letak demo. Tidak ada bukti kerusakan Native atau semua layar tersambung mengalami hal sama.',
      dict(run_id=38786177957,job_id=116598629614,artifact_id=11998406630,member='DEMO_SIMULATION.json',case_id='DEMO_SIMULATION/phone/'+page,
           viewport_width=390,document_width=width,inventory_status='PASS (visit-only)',feature_observation='horizontal page overflow',
           connected_refusal_document_width=390,connected_positive_layout_claim=False),
      'Perbaiki grid/min-content dan pembungkusan kartu/angka pada halaman terkait; gunakan scroll lokal hanya jika tabel memang memerlukannya, tanpa membuat body melebar.',
      ['Viewport 390×844 dan tablet; angka/aksi kanan tetap terlihat atau berada di scroll lokal yang jelas; desktop tetap terbaca. Pisahkan uji data positif dari layar refusal kosong.'],False))
F.append(finding('KNOWN-UI-MODE','S0','Mode Enteng menampilkan angka contoh, termasuk dua layar uang tanpa label simulasi lokal',
 'KNOWN_WRITER_GAP_INDEPENDENTLY_VERIFIED','BROWSER_CHROMIUM_HTTP_MOCK_PLUS_SOURCE',
 ['src/App.tsx:637-638,761','src/FinancePages.tsx:51,120,229','src/App.tsx:dashboard connected notice'],
 '23/48 menu UAT masih data contoh. Ringkasan Keuangan menyebut Rp284,6 jt sebagai saldo buku dan Payroll memuat nota/uang contoh tanpa label simulasi lokal, walau tidak ada RPC bisnis yang berhasil. Owner bisa mengambil keputusan dari angka yang tidak berasal dari buku. Tidak mengklaim saldo database hosted benar-benar berubah.',
 dict(run_id=38786177957,uat_job_id=116598630009,artifact_id=11998077978,
   cases=['UAT_AUTH_SIMULATION/desktop/finance-overview','UAT_AUTH_SIMULATION/phone/finance-payroll'],
   mode_routes=dict(UAT_connected=23,UAT_examples=23,UAT_blocked=1,UAT_notice=1,disposable_connected=35),
   business_rpc_on_two_fake_finance_pages=0,backend_in_inventory='all business reads deliberately 403; no hosted request',
   global_context='RuntimeBadge says UAT · MODUL TERPILIH LIVE and sidebar lists selected connected production modules; this is not a per-page simulation label for finance figures.',
   source='writer SCREEN_MAP §2.1–4 disclosed this before this round; Sol verified independently; not claimed as a new discovery'),
 'Sebelum Enteng dipakai: rute layar bisnis yang disetujui ke backend tersambung dan fail-closed bila belum terpasang/403. Angka contoh wajib jelas terpisah dari angka buku; hilangkan klaim dashboard yang menunjuk angka asli ke menu yang masih contoh. Membetulkan label saja tidak menyelesaikan koneksi transaksi.',
 ['Build UAT dengan backend disposable sah: 48 route, reader/command, peran/revoke/403, kosong/tidak tersedia, refresh dan HP. Dua layar uang tidak boleh menampilkan seed sebagai saldo buku.'],False))
F.append(finding('KNOWN-DAILY-MASTER','S1','Enam kelompok data induk harian tetap simulasi dan belum menyediakan pengelolaan Native biasa',
 'KNOWN_WRITER_GAP_INDEPENDENTLY_VERIFIED','STATIC_PLUS_BROWSER_INVENTORY',
 ['src/App.tsx:755-756','src/MaterialMasterPages.tsx','src/MasterDataPages.tsx'],
 'Pelanggan, supplier/vendor umum, mandor, gudang/lokasi, kain/benchmark serta aksesori/harga tidak dapat ditambahkan atau diubah melalui menu harian tersambung. Impor awal dan master khusus yang tersedia tidak otomatis menutup kebutuhan menu harian.',
 dict(run_id=38786177957,artifact_ids=[11998247784,11998077978],menu_ids=['master-fabric','master-accessory','master-customers','master-partners','master-workforce','master-locations'],writer_disclosed='SCREEN_MAP §2.10'),
 'Sambungkan pengelolaan master harian dengan izin, identitas stabil, validasi referensi dan snapshot historis. Gunakan reader/Native writer sah; jangan mengubah identitas dokumen terposting saat master diperbarui.',
 ['Tambah pelanggan/supplier/mandor/lokasi/material biasa lewat UI; gunakan pada transaksi berikutnya; uji larangan ubah/hapus saat sudah digunakan dan sejarah SKU/range/PO tetap benar.'],False))
F.append(finding('KNOWN-BF-WAVE','S1','Selesai jahit G1 masih menolak potongan dengan tarif wave BF per SKU/ukuran',
 'KNOWN_WRITER_LIMIT_INDEPENDENTLY_SOURCE_VERIFIED','STATIC',
 ['scripts/cp7-src/cutting-correction/sewing.sql:106-107,224','src/SewingCompletionPanel.tsx'],
 'G1 baru menyambungkan jalur dasar, tetapi potongan yang memiliki bf_wave_skus_v1 diblokir WAVE_SKU_RATES. PASS G1 dasar tidak membuktikan operator dapat menuntaskan varian itu dan membentuk upah/siap laundry melalui aplikasi.',
 dict(source_register='SOURCE_REVIEW.json',condition='exists erp.bf_wave_skus_v1 for cutting_group_id',refusal='WAVE_SKU_RATES',
      new_runtime_counterexample_claim=False,writer_disclosed='HANDOFF_SOL: known G1 limitation'),
 'Sediakan jalur Native penyelesaian per SKU/ukuran dengan tarif snapshot BF dan alokasi upah per komponen; pertahankan identitas historis, PCS dan HPP. Jangan meloloskan lewat penulis dasar yang tidak mengenal rate wave.',
 ['Kasus dasar tetap lulus; wave BF dua SKU/ukuran bertarif beda, parsial, sisa, replay, koreksi, upah per mandor/komponen dan siap laundry; browser desktop/HP.'],False))
for f in F:
    f.pop('product_bug',None)
    f['category']='EVIDENCE_TOOL_DEFECT' if f['id']=='SOL-R1-003' else 'UI_PRESENTATION_DEFECT' if f['severity'] in ['S0','S2'] else 'FUNCTIONAL_GAP' if f['evidence_level']=='STATIC' else 'BUSINESS_COMMAND_DEFECT_OR_GAP'
save('FINDINGS.json',dict(candidate_sha=CANDIDATE,candidate_tree=TREE,new_findings=[f['id'] for f in F if f['id'].startswith('SOL-R1-')],
  known_roots_verified_not_new=[f['id'] for f in F if f['id'].startswith('KNOWN-')],findings=F,
  counts_new=dict(collections.Counter(f['severity'] for f in F if f['id'].startswith('SOL-R1-'))),
  counts_known=dict(collections.Counter(f['severity'] for f in F if f['id'].startswith('KNOWN-'))),
  no_new_confirmed_undetected_native_data_corruption=True,feature_complete=False,audit_complete=False,audit_round_work_finished=True,production_go=False))

old=read(E/'ANALYSIS_INPUTS.json')['old_inputs']
I=[]
for oldrow in old['INVARIANT_MATRIX.json']:
    r=dict(oldrow);r['prior_candidate']='0b7049d9203bac52b47a4c89f3e0d75646067a8f';r['prior_seal']='10bfe3972bd310dbd8600cd18638a02f47d007f0'
    r['prior_status']=oldrow['status'];r['retained_evidence_origin']='SOL_LOCKED_PRIOR_ROUND_NOT_FRESH_RUNTIME'
    r['current_scope']='Prior qualified scope retained where unchanged; relevant current witnesses below. PASS never means every possible flow/device.'
    id=r['invariant'];fam=id.split('-')[1][0]
    r['current_evidence']='Current evidence is per SUITE_RESULTS / CASE_LEDGER; prior exact qualified proof remains separately dated. No blanket fresh-runtime claim.'
    if id=='INV-U05':r.update(status='PASS',current_evidence='Own empty/funded/backdate/later-prefix/used-funding reverse; CP17 cash/race/payroll/vendor cases.',current_scope='D14-3 no-negative safety on tested paths. Legitimate income correction completion FAIL is SOL-R1-001; no overdraft exception remains.')
    if id=='INV-K01':r.update(status='FAIL',current_evidence='SOL-R1-001 Native + real Auth HTTP',current_scope='Posted history remains unchanged on failed commands. Availability of legitimate atomic correction fails; not a claim immutable facts were edited.')
    if id in ['INV-L01','INV-L03','INV-UI01']:r.update(status='FAIL',current_evidence='KNOWN-UI-MODE: source + UAT inventory, fake figures with zero business RPC.',current_scope='Backend report fixtures pass, but UAT screen claims do not consistently come from Native sources. Seed numbers are not unknown-safe output.')
    if id=='INV-UI04':r.update(status='INCOMPLETE',current_evidence='D14-5/G1/G2 real Chromium desktop/phone; 288 mocked route visits; QC/HPP demo overflow findings.',current_scope='Physical iPad/phone and positive loaded state of every connected page not proven; no equality claim for all devices.')
    if id=='INV-M05':r.update(status='PASS',current_evidence='38787131786 OWNER_CONTROLLER_QUALIFICATION 10/10; exact 58 files NOSUPERUSER owner.',current_scope='Disposable faithful v2.6.20 baseline, all declared early refusals, unchanged SQL. No hosted execution or fresh hosted read.')
    if id in ['INV-M01','INV-M03','INV-M04']:r.update(status='INCOMPLETE',current_evidence='Owner CP7C deferral and no hosted mutations; fresh synthetic opening/restore does not replace real cutover/CP2 original restore.')
    if id in ['INV-D01','INV-D04','INV-L07','INV-T04','INV-POL03','INV-M01','INV-M03','INV-M04']:r['status']='INCOMPLETE'
    if id=='INV-C06':r.update(current_evidence='All current strict Native case boundaries, race/HTTP copy disposal, Auth restored; CP6 comparison restored; original tool failures separately retained.')
    if id=='INV-A05':r.update(current_evidence='Current exact declaration/catalogue checks and CP17 FABLE012 exposure gate/HTTP refusal.',current_scope='82 direct erp EXECUTEs deferred by D14-9; no API-reachability or full-revocation PASS beyond tested exposure gate.')
    I.append(r)
assert len(I)==82 and len({r['invariant'] for r in I})==82
save('INVARIANT_MATRIX.json',I)
with (OUT/'INVARIANT_MATRIX.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(I[0]),extrasaction='ignore');w.writeheader();w.writerows(I)
S=[]
for oldrow in old['SCENARIO_MATRIX.json']:
    r=dict(oldrow,prior_candidate='0b7049d9203bac52b47a4c89f3e0d75646067a8f',evidence_origin='SOL_LOCKED_PRIOR_ROUND_WITH_BOUNDED_CURRENT_RETEST')
    if r['id']=='SKN-22':r.update(status='FAIL',basis='D14-5/12 actual browser gap closed; current correction cash path FAIL (SOL-R1-001), PO daily path absent, full combined application chain remains INCOMPLETE.')
    if r['id']=='SKN-27':r.update(status='FAIL',basis='A legitimate spent-income amount/note correction is blocked. Range-dozens closed on disposable desktop/phone; broad edit/delete coverage remains bounded by CHAIN_MATRIX.')
    if r['id']=='SKN-13':r['basis']+=' Current own dated cash-prefix/refusal and used-funding inverse controls PASS.'
    if r['id']=='SKN-09':r['basis']+=' All new financial controls stayed on planned WIB 2026-10-16; original token timezone error retained as AUDITOR_TOOL.'
    S.append(r)
save('SCENARIO_MATRIX.json',S)

boundaries=[
 dict(id='BOUNDARY-CP2',status='OWNER_DEFERRED_NOT_RUNTIME_PASS',scope='Original CP2 functional restore; credentials/key and real backup work at CP7C',decision=['D13-9a','D13-8b'],proof='Prior archive verified; current T3 disposable restore is a different claim.'),
 dict(id='BOUNDARY-HOSTED',status='NOT_EXECUTED_BY_DESIGN',scope='Enteng/legacy/production SQL, installation, current cutover facts and cp7_guard.findings on hosted',decision=['D13-7a','D13-8f','D14-7'],proof='No hosted queries or mutations by Sol; no request for permission/password reopened.'),
 dict(id='BOUNDARY-AZ-FIRST',status='ROOT_CAUSE_UNKNOWN',scope='First historical AZ install failure',decision=['D14-8'],proof='New exact 58-file install PASS + diagnostic repair do not identify the old absent PostgreSQL diagnostic.'),
 dict(id='BOUNDARY-A2',status='ROOT_CAUSES_OPEN',scope='Two old A2 failures (D13-10)',decision=['D13-10','D14-8'],proof='Comparator now stable and sensitive to definition/member/owner/ACL in original run stdout; historical root failures remain unproved.'),
 dict(id='BOUNDARY-EXECUTE82',status='ACCEPTED_DEFERRAL_CP7C',scope='Revoke 82 erp writers before erp exposure via Data API',decision=['D14-9'],proof='Current exposure gate and actual HTTP refusal PASS; direct SQL EXECUTE not revoked.'),
 dict(id='BOUNDARY-BROWSER-CHAIN',status='INCOMPLETE',scope='No all-13-stage browser run plus all seven side chains; missing positive app paths listed per link',decision=['D14-13'],proof='20/20 reviewed dispositions, not 20/20 full application PASS.'),
 dict(id='BOUNDARY-DEVICE',status='INCOMPLETE',scope='Physical phones/iPad and loaded positive state of every connected page',decision=[],proof='Chromium viewports only; 288 mocked visits do not substitute real Native screen flows.'),
 dict(id='BOUNDARY-DETECTORS',status='INCOMPLETE',scope='All detector 0→+1→0 controls and every-case detector set',decision=[],proof='Prior subset positive controls retained, no blanket sensitivity acceptance.'),
 dict(id='BOUNDARY-P19',status='RETAINED_PRIOR_SCOPE',scope='Large staged analysis/K2–K6/model/AI/WA families',decision=[],proof='Prior independent scoped evidence + unchanged source; not rerun or promoted to live WA/hosted proof this round.'),
 dict(id='BOUNDARY-SG',status='ACCEPTED_BY_OWNER_RULE',scope='SG01 higher-tier reversal blocked; SG02 inverse effective when saved; SG03 same-product paid rewash has no bill',decision=['D14-10','D06'],proof='Do not reopen owner-set policy; current CP17 Native checks retain declared behavior.')]
boundaries.extend([
 dict(id='BOUNDARY-CUTOVER-FLOOR',status='EXISTING_OWNER_ITEM',scope='FABLE-011 cutover date floor',decision=[],proof='Existing writer register item, not a new question from Sol; no invented date or hosted acceptance.'),
 dict(id='BOUNDARY-POLICY',status='PENDING_VALUES_NOT_TEST_PASS',scope='K8 exposes 8/13 CP6 policies and relevant CP7 reminder/capacity thresholds; required values chosen in application at use',decision=['D11'],proof='Pending guards and existing owner stage retained; auditor does not invent business values.'),
 dict(id='BOUNDARY-LEGACY-OTHER',status='RETAINED_SCOPE_LIMITS',scope='FABLE-007 regression-only, R-DOC03/CP2 key work at CP7C, historical original A2/AZ gaps',decision=['D13-9a'],proof='Items disclosed in writer CHAIN_MAP §4; not independently converted to PASS or recounted as new Sol discoveries.')
])
save('OPEN_BOUNDARIES.json',dict(candidate_sha=CANDIDATE,owner_questions_reopened=[],items=boundaries))
save('AUDITOR_TOOL_EVENTS.json',dict(events=[
 dict(run=38785656146,case='SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE',classification='AUDITOR_TOOL',raw='INCOMPLETE',cause='Generic token read in Asia/Jakarta vs UTC correction writer; original preserved, dedicated workspace qualification unchanged expected.'),
 dict(run=38785656090,classification='WRITER_TEST_TOOL',case_count=0,cause='Pre-U pending asserted despite stop before U',finding='SOL-R1-003',qualified_run=38787131786),
 dict(run=38790146246,classification='AUDITOR_TOOL',case_count=0,cause='Installer imported relative metadata from wrong CWD',qualified_run=38790510239,all_expected_unchanged=True),
 dict(run=38787925433,classification='AUDITOR_MEASUREMENT_METADATA',field='original_posted_facts_immutable=false in spent HTTP cases',cause='Caller fixture Asia/Jakarta vs fresh UTC JSON timestamps',disposition='Do not infer fact mutation; UTC full business/private boundary unchanged on every failed command. Original false fields retained.'),
 dict(run=38786177957,classification='AUDITOR_MEASUREMENT_METADATA',field='Inventory raw evidence_origin is INDEPENDENT_NATIVE_RERUN; viewport overwritten by numeric innerWidth',cause='Overbroad origin label and object spread order in inventory probe',disposition='Normalized ledger labels all 288 BROWSER_HTTP_MOCK, zero Native transaction acceptance. Viewport labels recovered from declared case IDs; raw observations unchanged.'),
 dict(classification='LOCAL_INFRA_TOOL_LIMIT',cause='Local Playwright browser download truncated; no local browser acceptance claimed',replacement='Own CI real Chromium proofs and separate mock inventories succeeded'),
 dict(classification='NO_PRODUCT_ORACLE_EFFECT',cause='First local shell push auto-review rejected unverified destination; owner repo identity/permission verified and outgoing history reduced; GitHub app wrote only own audit branch',main_writer_or_hosted_changed=False)
],rerun_policy='No identical product case rerun for green. Three documented tool qualifications, old outcomes retained; no expected weakening.'))
print(json.dumps(dict(new=collections.Counter(f['severity'] for f in F if f['id'].startswith('SOL-R1-')),known=collections.Counter(f['severity'] for f in F if f['id'].startswith('KNOWN-')),invariants=collections.Counter(r['status'] for r in I))))
