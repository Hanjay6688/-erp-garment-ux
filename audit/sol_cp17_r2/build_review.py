"""Dispositions and impact trace. Does not execute tests or promote inherited proof."""
from build_evidence import *

invariants=read(PROOF/'prior/INVARIANT_MATRIX.json')
for row in invariants:
 row['previous_candidate']='dfab13bf62398a69a02bf6221c06d29075e5e40b'
 row['previous_seal']=PRIOR
 row['previous_disposition']=row['status']
 row['evidence_origin']='INDEPENDENT_SOURCE_REVIEW_WITH_EXPLICIT_RETAINED_PRIOR_SOL_PROOF'
 row['scope']='Hasil lama dipertahankan hanya untuk sumber yang tidak berubah; bukti runtime r2 yang terkait dirujuk di bawah. Tidak berarti seluruh kombinasi atau produksi lulus.'
 row['r2_evidence']=['SUITE_RESULTS.json','CASE_LEDGER.json','IDENTITY_SOURCE.json']
 if row['invariant']in ['INV-L01','INV-L03','INV-UI01']:
  row.update(status='PASS',current_scope='Root angka contoh di mode UAT ditutup sesuai D15-2: 17 menu tersembunyi, dashboard tanpa angka contoh, enam layar contoh disposable berlabel. Klaim kesesuaian angka positif dibatasi kasus Native browser yang dijalankan, bukan setiap layar dan data produksi.',
   current_evidence='UI mock 48×3×2; actual UAT build/real Auth hidden census + customer lifecycle + autoPO. F03 P13/P11/P12 positive sources. UAT hosted tidak diuji.',evidence_origin='INDEPENDENT_NATIVE_RERUN_AND_INDEPENDENT_UI_MOCK_RERUN')
 if row['invariant']=='INV-K01':
  row.update(status='PASS',current_scope='Koreksi pemasukan yang sah kini selesai sebagai inverse+replacement dengan fakta lama tetap; kontrol saldo akhir negatif tetap menolak. Batas pool HPP yang belum ada UI dicatat terpisah.',
   current_evidence='SOL_R2_LITERAL 7/7 + SOL_R2_CORRECTION_HTTP 4/4; CP17 cash compound and note/misc corrections; unchanged predecessor proof.',evidence_origin='INDEPENDENT_NATIVE_RERUN')
save('INVARIANT_MATRIX.json',invariants)

closures=[
 dict(id='SOL-R1-001',status='CLOSED_TESTED_SCOPE',proof='7/7 literal Native + 4/4 real Auth HTTP; spent30.01−20 corrected25.01→bank5.01; note-only→10.01; negative15.01 refused unchanged.'),
 dict(id='SOL-R1-002',status='CLOSED_ORDINARY_NEW_PO_PATH',proof='CP17 autoPO Native/race/HTTP/browser; real UAT-build autoPO phone; PO+cutting atomic and UUID replay. New numbering boundary is separate SOL-R2-001.'),
 dict(id='SOL-R1-003',status='CLOSED_UNMODIFIED_CANDIDATE_HELPER',proof='Stop-before-U records NOT_APPLICABLE_STOPPED_BEFORE_U; native owner10/10, 58/58 pinned files; no prior Sol monkeypatch.'),
 dict(id='SOL-R1-004',status='CLOSED_DEMO_QC_WIDTH',proof='DEMO phone390: document.scrollWidth390; desktop1440:1440. Original failing669 at390 retained in seal278a95ce.'),
 dict(id='SOL-R1-005',status='CLOSED_DEMO_HPP_WIDTH',proof='DEMO phone390: document.scrollWidth390; desktop1440:1440. Original failing627 at390 retained in seal278a95ce.'),
 dict(id='KNOWN-UI-MODE',status='CLOSED_PER_D15_2',proof='17 hidden UAT menus; zero UAT sample routes; actual UAT Native census plus all288 mode/refusal/width contexts. Not hosted CP7C acceptance.'),
 dict(id='KNOWN-DAILY-MASTER',status='CLOSED_TESTED_SIX_SCREENS_AND_RATES',proof='CP17 master10 Native +7race +2HTTP +13browser; actual UAT customer create/update/deactivate and usage blockers.'),
 dict(id='KNOWN-BF-WAVE',status='CLOSED_TESTED_PER_SKU_FLOW',proof='CP17 wave5Native+1race+1HTTP+2browser; Sol independent5/2/9 sizes, cancel B, repost:16pcs, net WIP356 exact.'),
 dict(id='SOL-001',status='RETAINED_CLOSED_FRESH_CASH_CONTROL',proof='Original emptybank pay1 refused; F03/current cash guards and own literal unchanged.'),
 dict(id='SOL-002',status='RETAINED_CLOSED_PRIOR_BE16_SCOPE',proof='Prior independent BE16 complete original retained; supabase tree unchanged. Current connected prefreeze regression separately recorded, not relabelled as Native BE16 rerun.'),
 dict(id='SOL-003',status='RETAINED_CLOSED_DIAGNOSTIC_SCOPE',proof='Prior diagnostic3/3 original; current58-file owner install pass. Historical first AZ reason remains unknown.'),
]
save('RETEST_DISPOSITIONS.json',dict(candidate_sha=CANDIDATE,origin='INDEPENDENT_* except explicitly retained older original',items=closures))

impacts=[
 ('R2-01','Kas dua dasar tanggal dan koreksi majemuk',
  ['finance/dated-guards.sql','finance/misc-correction.sql','sales/correction.sql','sales/payment-correction.sql'],
  'Bayar supplier/mandor/laundry, kasbon, miscellaneous, koreksi nota dan pembayaran → inverse/replacement → kas harian ekonomi+buku → GL/laporan. Lingkup majemuk privat menunda penilaian sampai hasil akhir; kunci rekening dan penolakan minus tetap.',
  'CP17 dated cash/misc/note + own7Native/4HTTP + F03P09–P13/cash. Dashboard sampel ditangani terpisah.'),
 ('R2-02','Aktivasi layar dan kejujuran angka',[],
  'screenActivation→sidebar/direct-page guard→OwnerDashboard/FinancePages. UAT:29connected,17hidden,1boundary,1notice. Disposable:41connected,6sample,1notice. Demo:48sample. Hidden route harus berhenti sebelum layar angka contoh.',
  '288 mock contexts; actual UAT realAuth census+positive customer+autoPO. No positive Native claim from403 mock.'),
 ('R2-03','Master harian dan tarif upah',['master/master.sql','master/rates.sql'],
  'Pelanggan→draft/AR; supplier/vendor→penerimaan/AP/laundry; lokasi/bahan/aksesori→stok/BOM/upah; mandor/kebijakan/tarif→pickup→snapshot per tanggal→upah/Nota/payroll→HPP. Riwayat privat immutable, token tinjau dan hak owner/admin; kode yang sudah dipakai tetap.',
  'CP17 Native10/race7/HTTP2/browser13; actual UAT customer lifecycle; source role41 manifests and Native grant/owner checks.'),
 ('R2-04','PO otomatis dan kunci pemulihan',['cutting-correction/auto-po.sql'],
  'POST BuatPotongan→PO header baru→accepted Native cutting writer→material issue/stok/GL/WIP→pickup. Draft privat belum membuat PO. Request(actor,UUID) sama memulihkan satu jawaban. UI memakai envelope bersama untuk mode PO baru/lama.',
  'AutoPO all4layers; own999control1000counterexample; final existingPO fix additionally qualified by F04consumer. SOL-R2-001 remains open.'),
 ('R2-05','Selesai dan buka ulang PO',['cutting-correction/finish.sql','cutting-correction/po-reopen.sql'],
  'Jahit/FG/beban PO→G2 Native eligibility/HPP→finish residual close→period guards→reopen inverse. Blocker FG sudah terpakai/periode dan status HPP berasal snapshot Native; tidak membuka periode otomatis.',
  'CP17 G1/G2 ten-piece conservation, unsewn/unsent6, finish/reopen/refinish, permission/race/browser desktop+phone.'),
 ('R2-06','Seri SKU penjualan lintas merek',[],
  'SalesDraftPanel: brand+SKU identity→sizes request→disable save whileloading→reset review→lusin split→Native sale draft/recovery→FG reservation/invoice/AR/cash. Brand yang sama wajib pada setiap ukuran.',
  'Current DOM+1794 unit; CP17 dozen browser desktop/phone+F03P11 Native/readback. The financial UAT routes remain hidden perD15-2.'),
 ('R2-07','Dua rantai aplikasi tambahan',[],
  'ImporWIP→FG→ganti merek→tutup buku tengah rantai→jual→bayar→kas→reopen; mastercomponent/rate→openingBS→recipe→classify components→rework→Nota→payroll→kas. Setup bank/period/seed isolation dibedakan dari klik bisnis.',
  'Both CP17 realAuth browser journeys independently PASS. No attendance HPPpool lifecycle UI: known open, no owner waiver.'),
 ('R2-08','Bootstrap dan bukti lama',[],
  'Expired AC artifact→capture exact208 preU table set→frozenX guard; stop beforeU→not applicable. G01/T2/oldentrypoints receive candidate helper. Historical allowlist/scope gates remain strict.',
  'Unmodified candidate beforeU + full58 non-superuser install; final writer116metadata paginated, 22 non-success retained. Not all old workflow acceptance green.'),
 ('R2-09','Lebar QC/HPP dan server sensus',[],
  'CSS result/size-summary→phone intrinsic width; file server reads build into Map then serves exact paths. Request paths do not reach filesystem. Mock census measures document root, not merely clipped container.',
  '48demo desktop/phone including QC390/HPP390; all288 mode contexts. Independent CodeQL JS/TS+Actions and zero-result gate separately recorded.'),
 ('R2-10','Jahit per SKU wave',['cutting-correction/sewing.sql'],
  'Cutting size yields→wave SKU binding→dated SKU/base rate preview→Native component snapshots→perSKU completion+terminalevent+wage→laundry availability/Nota/payroll/HPP. Reverse oneSKU preserves others, maxQty dimension perSKU.',
  'CP17 wave all4layers; independent sizes5/2/9, first wage188, cancel155, repost323, netWIP356 and16pieces.'),
 ('D15-5','Tanggal mulai pakai resmi',['cutover/cutover.sql'],
  'Official owner date/control FORUPDATE vs posting FORSHARE→journal economic date / material+FG movement physicalWIB→atomic refusal beforefloor; opening/migration and inverse officialpaths exempt; importbatchfloor and earliestop constrain setting.',
  'CP17 boundary/opening-lateinvoice/settlement/replay/race/HTTP/browser. No date invented and no hosted setting made.'),
]
save('IMPACT_MATRIX.json',dict(candidate_sha=CANDIDATE,scope='Whole r2 delta, CP1–7 retained source identities + all new roots',
 rows=[dict(id=i,title=t,sql_files=['scripts/cp7-src/'+x for x in f],impact=c,evidence=e,status='TERDAMPAK_DAN_DITELUSURI')for i,t,f,c,e in impacts],
 unchanged_scopes=[dict(path='supabase/',status='TIDAK_BERUBAH_BYTE_TREE',reason='git diff dfab..2e9d -- supabase empty; old CP1–6 release bodies unchanged; callers/CP7 guards are still retested.'),
 dict(path='P19/K2–K6/AI/WA engine source',status='RETAINED_PRIOR_QUALIFIED_SCOPE',reason='No changed engine SQL in r2 delta; F03 analysis/report and full unit gates rerun. Large-scale Native/realWA/hosted acceptance not newly claimed.')]))

boundaries=read(PROOF/'prior/OPEN_BOUNDARIES.json')
boundaries['candidate_sha']=CANDIDATE
for row in boundaries['items']:
 row['origin']='INDEPENDENT_SOURCE_REVIEW_WITH_EXPLICIT_PRIOR_SOL_PROOF'
 if row['id']=='BOUNDARY-CUTOVER-FLOOR':row.update(status='CLOSED_PER_D15_5_TESTED_SCOPE',decision=['D15-5'],proof='Current official-cutover Native/race/realAuthHTTP/browser cases PASS. No open owner question.')
 if row['id']=='BOUNDARY-BROWSER-CHAIN':row.update(proof='Two new full application chains pass (WIP/brand/sale/cash/close; BS/rework/Nota/payroll/cash); current autoPO and master→pickup→sewing pass. No single all13+all7-side-chain continuous app run; attendance pool lifecycle missing. Per-link matrix is bounded, not blanket all-flow PASS.')
 if row['id']=='BOUNDARY-DEVICE':row['proof']='Chromium1440/390 emulation plus actual UAT build via disposable Native transport. Physical iPad/phones and every positive-loaded page not tested.'
 if row['id']=='BOUNDARY-EXECUTE82':row['proof']='Current Native inventory160 executable/82 writers; public+graphql_public exposure gate and real HTTP refusal pass. SQL EXECUTE revoke remains explicitly deferred D14-9.'
boundaries['items'].append(dict(id='BOUNDARY-POOL-UI',status='OPEN_MISSING_FUNCTIONAL_ROUTE',scope='Attendance HPPpool lifecycle screen',decision=[],proof='Writer disclosed and source scan confirmed absence. D15-2 is a hiding decision, not a waiver. See known item in FINDINGS.json.'))
save('OPEN_BOUNDARIES.json',boundaries)

chains=read(PROOF/'prior/CHAIN_MATRIX.json');chains['candidate_sha']=CANDIDATE
for row in chains['rows']:
 row['previous_seal']=PRIOR
 row['previous_verdict']=row['verdict']
 row['evidence_origin']='INDEPENDENT_NATIVE_RERUN_PLUS_EXPLICIT_RETAINED_SOURCE_SCOPE'
 row['uat_boundary']='UAT29connected/17hidden/1boundary/1notice per D15-2; current Native browser mostly disposable; actual UAT3 via explicit isolated transport; no hosted CP7 installation.'
 if row['id']=='B2':row.update(connection_status='TERSAMBUNG DAN TERUJI',verdict='PASS_TESTED_ORDINARY_PATH_WITH_OPEN_BOUNDARY',
  independent_proof='CP17 autoPO Native/race/HTTP/browser and actual UAT Native phone; additional999/1000 test.',boundary='Daily PO route now exists. Number1000 bug SOL-R2-001 remains open.',finding_refs=['SOL-R2-001'])
 if row['id']=='B3':row.update(connection_status='TERSAMBUNG DAN TERUJI',verdict='PASS_TESTED_PATH',independent_proof='CP17 master screen chain creates Mandor+rates→BagiPotongan POST→sewing wage; autoPO Native continuation; SG01 reverse.',boundary='Fresh positive pickup path demonstrated; no single all13-stage scenario claim.')
 if row['id']=='B9':row.update(connection_status='TERSAMBUNG DAN TERUJI',verdict='PASS_TESTED_BRAND_CONVERSION_PATH',independent_proof='CP17 R2_07 screen chain importWIP→FGbrandA→convertB→sale→cash; F03P10 adjustments Native/browser.',boundary='Brand conversion chain demonstrated. Not every ledger filter/physical device combination.')
 if row['id']=='S3':row.update(connection_status='TERSAMBUNG DAN TERUJI SEBAGIAN',verdict='INCOMPLETE_POOL_UI',independent_proof='CP17 R2_07 BS→rework→Nota→payroll→pay, kasbon screen; F03P12/cash.',boundary='Rework→Nota→pay now demonstrated. Attendance HPPpool create/activate/cancel UI is missing; UATpayroll/attendance hidden perD15-2.')
 if row['id']=='S5':row.update(connection_status='TERSAMBUNG DAN TERUJI',verdict='PASS_TESTED_REWORK_NOTA_PAYROLL_PATH',independent_proof='CP17 R2_07 source-only screen chain with BS component classification, BOM recipe, Mandor rework, Nota and payment.',boundary='Same-product rewash Native retains free rule; not every partial return/QC/permutation in one app chain.')
 if row['id']=='S7':row.update(connection_status='TERSAMBUNG DAN TERUJI',verdict='PASS_TESTED_OPENING_WIP_CONTINUATION',independent_proof='CP17 R2_07 browser import→WIPoutput→FG→convert→close→sale→customerpayment→cash; openingBS→rework side chain.',boundary='Synthetic opening data only; original CP2 functional restore and realcutover shadow remain deferred.')
 if row['id']=='B7':row['boundary']='Demo QC width is fixed. Current legacy QC/API and size-range controls are recorded separately. A complete fresh QC→FG POST browser journey is not claimed; mock routing does not close it.'
 if row['id']=='B5':row.update(independent_proof='Current prefreeze31: LAU_T36 mixed sources, FREE/WAIVED physical, correction/partial ranges, claim recover/reverse; CP17 SG03/FIN02 Native.',boundary='Fresh positive legacy UI components pass on final CP7 stack. A single sewing→send→receive→QC full user journey is not claimed.',verdict='PASS_TESTED_COMPONENTS_NOT_SINGLE_END_TO_END')
 if row['id']=='B6':row.update(independent_proof='Current prefreeze31 D12 daily/opening claim payment screens + F03 vendor/AP/cash; CP17 emptybank vendor refusal.',boundary='Payment-screen and Native AP/cash cases pass; not every vendor document lineage in one browser journey.',verdict='PASS_TESTED_COMPONENTS_NOT_SINGLE_END_TO_END')
save('CHAIN_MATRIX.json',chains)

scenarios=read(PROOF/'prior/SCENARIO_MATRIX.json')
for row in scenarios:
 row['previous_seal']=PRIOR;row['candidate_sha']=CANDIDATE
 row['evidence_origin']='EXPLICIT_RETAINED_PRIOR_SOL_SCOPE_WITH_RELEVANT_R2_REGRESSION'
 row['r2_evidence']='SUITE_RESULTS.json / CASE_LEDGER.json; inherited scenario PASS is not a fresh all-family execution.'
save('SCENARIO_MATRIX.json',scenarios)
print(json.dumps(dict(invariants=dict(Counter(x['status']for x in invariants)),chains=len(chains['rows']),scenarios=len(scenarios),closures=len(closures))))
