"""Generate reviewable Sol findings, coverage and writer tasks from own evidence."""
import csv,hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;E=R/'evidence';SHA='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
def save(name,x): (R/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def report(name):
 matches=list((E/'original-reports').rglob(name));assert matches,name
 return json.loads(matches[0].read_text()),str(matches[0].relative_to(E/'original-reports'))
cash,cash_path=report('SOL_CASH_POLICY.json');assert cash['counts']=={'PASS':1,'COUNTEREXAMPLE':1}and cash['complete_boundary_restored']
found,found_path=report('SOL_FULLSTACK_FOUNDATIONS.json');assert found['status']=='PASS'
k4,k4_path=report('SOL_K4_5000.json');assert k4['counts']=={'PASS':1}
cleanup,cleanup_path=report('SOL_C0_CLEANUP_QUALIFICATION.json');assert cleanup['status']=='PASS'and cleanup['complete_business_boundary_restored']and cleanup['complete_public_catalog_restored']
c0=cleanup['run']['reused_C0_original'];assert c0['counts']=={'PASS':25}and c0['complete_boundary_restored']
ar,ar_path=report('SOL_SCOPE_AR_MISSING_RACES.json');assert ar['status']=='PASS_CONTRACT_DISPOSITIONS'
F=[
 dict(id='SOL-001',severity='S1',priority='P1',classification='CONFIRMED_BUSINESS_COUNTEREXAMPLE',status='OPEN',
 title='Pembayaran supplier dapat membuat saldo bank negatif tanpa kebijakan overdraft yang teridentifikasi',
 root_cause='Command memeriksa AP, izin, tanggal, token, dan akun aktif, lalu menyerahkan posting kepada Native. Kapasitas kas/bank bukan bagian tinjauan atau penjagaan yang terlihat pada jalur ini.',
 invariant='INV-U05',scope=['CP6 Native cash authority','CP7 supplier payment','cash/bank reports'],
 code=['scripts/cp7-src/invoices/payment-create.sql','erp.post_supplier_payment(uuid)','erp.cash_accounts','erp.journal_lines'],
 repro=['Bank baru aktif, tanpa opening/funding, saldo GL 0; receipt FINAL menimbulkan AP 1000.','Sebagai OWNER, kirim command publik pembayaran supplier 1.00 dengan review token sah.','Respons POSTED, AP 999, saldo bank -1.00. Kontrol funded 34.50 → pembayaran 1.00 → 33.50 lulus.'],
 expected='Tolak atomik jika dana tidak cukup, kecuali ada kebijakan saldo negatif yang sah dan batasnya dipenuhi.',actual='POSTED: 0 → -1.00; tidak ada kolom overdraft pada bank fixture dan izin kebijakan tersebut tidak ditemukan dalam inventaris acuan.',
 evidence=dict(run=38575876533,job=115892704370,artifact=11902025964,report=cash_path,case='SOL_CASH_EMPTY_BANK_WITHOUT_OVERDRAFT_POLICY',control='SOL_CASH_FUNDED_PUBLIC_PAYMENT'),
 impact='Saldo bank dapat tercatat di bawah nol walau jurnal seimbang dan AP tidak kelebihan bayar. Bukti ini tidak berarti uang nyata hilang; seluruh fixture sintetis.',
 fix='Gunakan penjagaan kas bersama pada otoritas Native, dengan lock per akun dan aturan per tanggal. Jika owner mengizinkan overdraft, simpan kebijakan, batas dan periode berlaku secara eksplisit. Jangan mengarang default atau hanya menambah pemeriksaan UI.',
 acceptance=['Dana cukup, tepat habis, dana kurang dan kebijakan pending.','Dua invoice berbeda membayar dari bank yang sama bersamaan: gabungan tidak melampaui kapasitas.','Backdate, reversal dan koreksi mempertahankan aturan histori serta sumber pendanaan.','Terapkan kontrol yang sama pada vendor/laundry, payroll, pengeluaran lain, uang muka dan refund; bukti bug saat ini khusus supplier.','UUID replay sekali; semua penolakan memulihkan payment/journal/request/stock/HPP.']),
 dict(id='SOL-002',severity='S2',priority='P2',classification='CONFIRMED_EVIDENCE_PACKAGING_DEFECT',status='OPEN',
 title='Artefak BE hanya menyimpan empat dari enam belas hasil yang telah dijalankan',
 root_cause='BE memakai global r1.OUT. Kasus kelima lazy-import cp6_av_probe; import itu mengganti r1.OUT ke folder av. Hasil selanjutnya dan terminal report ditulis di av, sementara workflow mengunggah be.',
 invariant='Pro Max §16.1–16.2/16.6',scope=['BE probe','shared auditor runner','evidence upload'],
 code=['scripts/cp6_be_probe.py:252','scripts/cp6_be_probe.py:rework_new_sku','scripts/cp6_av_probe.py:32','scripts/cp6_au_r1_probe.py:save'],
 repro=['Jalankan unchanged BE after pada kandidat ini.','Artefak 11892298930 berisi BE_CASES_AFTER status INCOMPLETE dengan empat kasus; terminal RESULT_AFTER tidak ada.','Log job auditor sendiri memuat 16 PASS, terminal REVIEW_COMPLETE, primary unchanged dan clone remaining 0.'],
 expected='Seluruh 16 ID dan hasil terminal berada dalam artefak yang diunggah.',actual='Produk BE lulus 16 kasus menurut log lengkap; paket bukti parsial 4/16.',
 evidence=dict(run=38560141862,job=115838893507,artifact=11892298930,recovered='evidence/BE_LOG_RECOVERY.json',new_case_credit=0),
 impact='Auditor berikutnya dapat menerima bukti parsial atau tidak dapat memeriksa kelulusan dari artefak.',
 fix='Jadikan tujuan output eksplisit dan tetap per run/group; hindari mutasi global pada import. Unggahan wajib memeriksa set ID, jumlah, status terminal dan cleanup. Pertahankan artefak lama yang parsial.',
 acceptance=['Lazy import pada kasus kelima tidak memindahkan output.','Artefak final 16/16, exact ID set dan seluruh expected/actual serta boundary.','Hilangkan/ubah satu hasil: gate artefak harus gagal.']),
 dict(id='SOL-003',severity='S2',priority='P2',classification='CONFIRMED_INSTALLER_DIAGNOSTIC_LOSS',status='OPEN',
 title='Pemasang membuang diagnostik PostgreSQL saat pemasangan berhenti di AZ',
 root_cause='except di owner installer menyimpan error_type/sqlstate serta proyeksi MAINTENANCE_RUNTIME_FAILED, tanpa message_primary/context/detail dari kegagalan SQL.',
 invariant='Pro Max §9/16.6',scope=['non-superuser owner installation','partial install diagnosis'],
 code=['scripts/cp6_readiness_owner_install.py:run except','core._public_failure_code'],
 repro=['Jalankan FULL_FROM_V2620 dengan owner/work postgres NOSUPERUSER pada clone disposable.','A..AY (51/58) terpasang; AZ berhenti dengan P0001.','Artefak hanya menyatakan MAINTENANCE_RUNTIME_FAILED; nama penjagaan PostgreSQL yang menolak tidak tersimpan.'],
 expected='Diagnostik terikat file/hash tersedia secara privat bagi operator/auditor, dengan pesan UI tetap terbatas.',actual='Penyebab pertama tidak dapat ditentukan. Qualification berinstrumen berikutnya memasang 58/58, tetapi tidak mereproduksi atau menjelaskan kegagalan pertama.',
 evidence=dict(first_run=38564307650,first_job=115852968691,first_artifact=11895105110,diagnostic_run=38566750411,diagnostic_job=115861262360,diagnostic_artifact=11896562171),
 impact='Pemasangan parsial tidak mempunyai informasi cukup untuk membedakan drift, admission/session, atau kondisi lain. Admission tetap tertutup dengan aman.',
 fix='Simpan message_primary, context/detail yang aman, constraint/object, file key/hash dan katalog/session diagnostic dalam bukti privat. Telusuri kegagalan pertama tanpa menurunkan penjagaan pemasangan.',
 acceptance=['Kesalahan terkontrol meninggalkan nama/kode penjagaan dan identitas file dalam receipt privat.','Tampilan umum tidak membocorkan kredensial/data sensitif.','51 file yang berhasil dan admission state tetap tercatat; tidak direlabel sebagai 58/58.'])]
save('FINDINGS.json',dict(candidate_sha=SHA,findings=F,confirmed_business_roots=1,confirmed_evidence_roots=2,production_go=False))
tasks=[dict(id=f['id'],priority=f['priority'],owner='WRITER_UTAMA',status='OPEN',task=f['fix'],acceptance=f['acceptance'],evidence=f['evidence'])for f in F]
tasks+=[dict(id='OPEN-AZ-FIRST',priority='P1_BEFORE_INSTALL_ACCEPTANCE',owner='WRITER_UTAMA',status='INVESTIGATION_REQUIRED',task='Jelaskan kegagalan AZ pertama. Green berikutnya tidak menjelaskan root cause; A2/D13-10 berbeda kasus.'),dict(id='KNOWN-SKU-RANGE-DOZENS',priority='P2_REQUIREMENT_COMPLETENESS',owner='WRITER_UTAMA',status='KNOWN_OPEN_NOT_NEW_FINDING',task='Buktikan helper range di form connected: satu lusin dibagi ke anggota ukuran SKU dan pengetikan per ukuran menampilkan total lusin + PCS. A6 per-line dan simulasi 4/4/4 tidak membuktikan fitur range-wide ini.'),dict(id='COVERAGE-CLOSURE',priority='BEFORE_FULL_ACCEPTANCE',owner='WRITER_UTAMA',status='INCOMPLETE',task='Tutup bukti sensitivitas detektor yang belum dipancing, pemulihan original CP2 pada tahap yang diizinkan, dan permukaan API alternatif seperti GraphQL jika dipakai/exposed. Catat batas hardware/hosted yang ditunda owner.')]
save('WRITER_TASKS.json',tasks)
guide=Path('/workspace/scratch/5969cedfb83c/AUDIT_PANDUAN_PRO_MAX.md').read_text()
items=re.findall(r'^- \*\*(INV-[A-Z]+[0-9]+)\*\* (.*)$',guide,re.M);assert len(items)==82
basis={
 'U':'F03 P11/P13/cash, P18, literal Sol money cases and T2 financial regression',
 'S':'F03 P09/P10, BB/BE/BF, F01/F02 fullstack conservation, Native transfer/correction',
 'H':'AY/AZ/BA/BD/BE, E01/E13 and late-invoice/correction Native controls',
 'P':'F03 cash/credits/refunds/P11–P13, BB/BC/BD and P18 payables',
 'T':'T2 dated controls plus separate C0 D01, Native WIB and closed-period cases',
 'L':'P13 exact-large/read-only/archive, F05 report/obligation v2, literal Sol report delta',
 'R':'PL Native model/schedule/netting/supply, F04/F05/P19, PR44 kernel-only qualification',
 'K':'receipt/note/payment/return/cutting correction, Native lineage and append-only controls',
 'C':'Native exact-ID/boundary groups, races, UUID changed intent and real Auth/HTTP/browser recovery',
 'A':'exact catalogue/RLS/grant/body checks, current Auth/revocation cases, security gates and bound SARIF',
 'UI':'real Chromium desktop/mobile emulation, prefreeze 31, connected F03 cases and DOM/shell gates',
 'POL':'D11/D13 and Native pending/invalid policy controls; original date statuses kept',
 'M':'synthetic BB/import regression and T3 install/restore/rollback; original CP2 archive integrity',
 'N':'F05 attention, P19 reminder episodes/ACK/snooze and test transport only',
 'D':'own 29-function full-output observation; two explicit 0→1→0 targets and qualified D07 controls'}
incomplete={'INV-D01':'Tidak semua detektor mempunyai poison control exact +1. FG_CACHE_MISMATCH dan UNBALANCED_POSTED_JOURNALS lulus 0→1→0; D07 single-value controls +1, removal controls +2 tidak dihitung sebagai exact +1.',
 'INV-D04':'Tidak mengklaim semua 29 detektor tercatat sebelum/sesudah setiap skenario; witness penuh tersedia untuk dua poison controls.',
 'INV-M01':'Cutover data nyata di luar tahap ini; hanya synthetic exact-line import diuji.',
 'INV-M03':'Zero checks synthetic terbukti; data nyata belum shadow/cutover.',
 'INV-M04':'Baseline reconstructed/aligned dari snapshot hosted historis; bukan clone hosted nyata baru. First AZ failure tetap OPEN.',
 'INV-M05':'Tujuh refusal guards awal lulus dan qualification owner 58/58 lulus, tetapi first positive install berhenti 51/58 tanpa cause.',
 'INV-UI04':'Chromium desktop/mobile emulation terbukti; perangkat fisik/Safari bukan bukti ini.',
 'INV-L07':'Redaction, selected unauthorized IDs/revocation/AI projections terbukti untuk permukaan public yang diuji; alternative API/GraphQL belum diuji.',
 'INV-T04':'Arsip immutable/cutoff controls tertentu terbukti; tidak mengklaim seluruh laporan memiliki arbitrary as-known historical replay.',
 'INV-POL03':'Satu-rule controls pada keluarga teruji; bank-negative policy gap SOL-001 masih OPEN.'}
matrix=[]
for ident,text in items:
 family=re.match(r'INV-([A-Z]+)',ident).group(1)
 status='FAIL'if ident=='INV-U05'else'INCOMPLETE'if ident in incomplete else'PASS'
 note=F[0]['actual']if status=='FAIL'else incomplete.get(ident,'PASS terbatas pada jalur/provider/kasus tercatat, bukan bukti semua kombinasi atau produksi.')
 if ident=='INV-H06':note='D11 LAU-DEC04 ALLOW_PENDING mengalahkan contoh lama panduan: penjualan boleh dengan HPP nonfinal, penutupan diblokir dan recost tetap diuji.'
 matrix.append(dict(invariant=ident,requirement=text,status=status,basis=basis[family],qualification=note))
save('INVARIANT_MATRIX.json',matrix)
with (R/'INVARIANT_MATRIX.csv').open('w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(matrix[0]));w.writeheader();w.writerows(matrix)
S=[
 ('01','PASS','NOTE_YEAR_364, RF_YEAR_HISTORY_364, supplier-payment YEAR_364; sintetis 364 hari, bukan aktivitas nyata setahun.'),
 ('02','PASS','F03 transfer/late invoice, P18 E13, AY/AZ/BE; saldo bahan/FG/COGS dan inverse.'),
 ('03','PASS','Closed/reopen controls, C0 D01 dan correction economic/recognition dates.'),
 ('04','PASS','Partial/paid/refund/advance/supplier-credit paths; overpay to approved credit, no disappearing amount.'),
 ('05','PASS','P11 returns, paid refund, note/return correction and capacity races.'),
 ('06','PASS','Literal Sol identical 3@17.25 lines; second line corrected to 2 with distinct lineage.'),
 ('07','INCOMPLETE','Exact cents, partial rounding and amount beyond JS-safe integer tested. Not every extreme and 1/3 path exhaustively tested.'),
 ('08','PASS','Native malformed/null/unknown/zero/negative and absent-source controls; free/waived exceptions distinguished.'),
 ('09','PASS','WIB boundaries/timezones and microsecond timestamp paths; no new wall-clock-midnight endurance claim.'),
 ('10','PASS','Original AR/AT/AU and F03 races; UUID exact replay/changed payload/later refusal.'),
 ('11','PASS','Real Auth/browser lost reply, revoke during wait/unit and inactive actors.'),
 ('12','PASS','Draft/post/inverse/repeated correction; no direct posted edit acceptance.'),
 ('13','PASS','Native chronological prefix refusals and revised receipt/note/cutting timelines.'),
 ('14','PASS','Multi-scope native providers and dimensional vendor/contractor/customer P18 checks; tested fixtures only.'),
 ('15','PASS','Receipt/note identity, stock-source and material name/SKU correction cases.'),
 ('16','N/A_OWNER_DEFERRED','Real cutover outside current owner stage; synthetic import not substituted for real data.'),
 ('17','PASS','F04/F05/P19 unknown price/yield/date/supply fences and qualified model controls.'),
 ('18','PASS','Repeat public financial reads, immutable archives, race coherence and no business DML.'),
 ('19','INCOMPLETE','Two own exact 0→1→0 controls, full 29 outputs; remaining sensitivity not all poisoned.'),
 ('20','PASS','Temporal membership, regrouping/no physical effects and archive identities in scoped Native families.'),
 ('21','N/A_OWNER_DEFERRED','Hosted real clone/installation expressly outside this Native round; constructed owner install is separate.'),
 ('22','INCOMPLETE','E01/P18 chain through payables/cash and late price + F03 consumers verified. Real cutover/full chain and range-wide connected dozens incomplete; cash invariant FAIL.'),
 ('23','PASS_WITH_ORIGINAL_DISPOSITIONS','326 + AS34 + AR174 + AT16/AU15 with races on final stack. Raw 12 HOLD, AS/AO reds and AR zero-price retained; C0 25 and BC replacement separate.'),
 ('24','INCOMPLETE','Matcher/allocator forging and actual Native plans tested. No blanket proof every matcher→allocator→command variant follows the same route.'),
 ('25','PASS','BC Special FREE and vendor FREE_WAIVED, ordinary zero/pending/normal controls; not just zero refusal.'),
 ('26','INCOMPLETE','Native exact-large, real source paging/caps and 5,000-target pages tested. Not every writer numeric/page boundary traced; no global 32-bit N/A.'),
 ('27','INCOMPLETE','Transaction inventory and many real correction/reversal flows covered; known connected range-dozens requirement remains open. No universal correction completeness claim.'),
 ('28','PASS','AT/AU temporal identity and Native BF/range snapshots/reversed docs in tested paths.'),
 ('29','INCOMPLETE','RPC/browser/report/AI projected permissions covered in selected flows; GraphQL/alternative API and physical devices not covered; WA test transport only.')]
save('SCENARIO_MATRIX.json',[dict(id='SKN-'+i,status=s,basis=b)for i,s,b in S])
save('AUDIT_STATUS.json',dict(candidate_sha=SHA,audit_round_work_finished=True,audit_complete=False,production_go=False,decision='HOLD',confirmed_business_findings=1,evidence_findings=2,open_first_install_failure=True,owner_deferred_exclusions=True))
summary='''# Audit independen Sol CP1–CP7 — handoff writer

**Putusan: HOLD pada `0b7049d9`.** Audit putaran ini selesai; kandidat belum memenuhi penerimaan penuh. `audit_complete=false`, `production_go=false`. Satu akar masalah bisnis dan dua cacat bukti terkonfirmasi; kegagalan pertama pemasangan AZ tetap belum terjelaskan.

| ID | Prioritas | Temuan dan dampak | Pekerjaan writer |
|---|---|---|---|
| SOL-001 | P1 / S1 | Bank saldo 0 membayar supplier 1.00 dan menjadi −1.00. Kontrol funded 34.50 → 33.50 lulus. | Penjagaan kas bersama per akun/tanggal, concurrency, dan kebijakan overdraft eksplisit bila diizinkan. Tutup seluruh keluarga pengeluaran, bukan hanya form supplier. |
| SOL-002 | P2 / S2 | Artefak BE hanya 4/16; log Native sendiri memuat 16/16 PASS. Import AV memindahkan global output path. | Output sink tetap per run; unggahan harus exact ID set, terminal result dan cleanup. |
| SOL-003 | P2 / S2 | Pemasang kehilangan diagnostik PostgreSQL saat AZ gagal; hanya P0001/MAINTENANCE_RUNTIME_FAILED tersisa. | Simpan diagnosis privat yang aman, file/hash dan state; telusuri first AZ failure. |
| OPEN-AZ-FIRST | Sebelum penerimaan install | First run berhenti 51/58. Qualification berinstrumen 58/58 tidak menjelaskan first failure. | Root cause tetap OPEN. Admission first failure tertutup; data produksi tidak dipakai. |

Rincian expected/actual, root cause, bukti dan acceptance berada di `FINDINGS.json`; daftar tugas siap olah di `WRITER_TASKS.json`. Jangan menyebut SOL-002 sebagai bug hitung BE: keenam belas kasusnya terbukti berjalan melalui log asli.

**Bukti kuat yang selesai:** delapan bucket F03 447/447; prefreeze UI 31/31; F01/F02 fullstack 86/86; AT 16+4 balapan dan AU 15+6 balapan; AR 146 original + 28 balapan dengan satu original zero-price tetap INCOMPLETE dan replacement BC lulus; C0 25/25 dengan cleanup qualification terpisah dan 0 kredit pengulangan; lima kasus kontrak Sol 5/5; PR44 235/235 + dua mutant tertangkap. K4 real pg_cron menyelesaikan 5.000 target dalam 127 unit dan 26 halaman, tanpa manual tick/page step, lalu dibuka dengan UUID/run yang sama.

**Regresi 326 bukan 326 PASS:** 275 PASS, 39 CONTROL_PASS, 12 DATE_POLICY_REVIEW_REQUIRED. AS34 raw = 25 PASS, 8 COUNTEREXAMPLE, 1 INCOMPLETE; AO12 raw = 8 PASS, 4 INCOMPLETE. Pembanding C0/owner D01 berjalan terpisah; status original tidak ditimpa.

**Kebutuhan lama yang tetap terbuka:** auto-bagi satu lusin ke range ukuran dalam form connected. Kandidat masih menyebut bagi rata 4/4/4 hanya simulasi; `SalesDraftPanel` menyimpan quantity per baris dan helper lusin mengubah satu baris. A6 browser per-line lengkap sesuai D13, tetapi itu bukan bukti fitur range-wide. Ini known gap writer, tidak dihitung temuan baru.

**Batas pemeriksaan:** CP2 original utuh (149 ZIP members, 148 hashes, 142 tables, 104 configuration rows, Auth 0), tetapi original functional restore belum dijalankan. Poison control belum lengkap untuk semua detektor. API alternatif/GraphQL belum diuji, sedangkan harness HTTP saat ini mengekspos public saja. Hardware fisik/Safari, data cutover nyata, hosted clone/shadow dan backup offsite mengikuti tahap/izin owner berikutnya. Matrix lengkap: `INVARIANT_MATRIX.csv` dan `SCENARIO_MATRIX.json`.

**Urutan revisi:** tutup SOL-001 dan tetapkan kebijakan bila saldo negatif memang dibutuhkan; benahi kedua cacat bukti; diagnosis AZ; tutup known requirement/coverage gap yang berlaku; bekukan kandidat baru dan jalankan affected gate dengan oracle yang tetap. Migrasi historis jangan diubah in-place. Paket ini tidak mengubah produk/writer branch/main/hosted/deployment. A2 supplier lama tetap known OPEN sesuai D13-10 dan tidak menjadi temuan baru Sol.
'''
(R/'WRITER_HANDOFF.md').write_text(summary)
full='''# Laporan Pro Max — Sol CP1–CP7

## Identitas dan putusan

Kandidat produk `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Cabang auditor `audit/sol-cp1-7-0b7049d9-20261014`; sumber/runtime/harness/oracle/fixture terikat oleh `ROUND_MANIFEST.json`, supplemental manifests, `RUN_REGISTER_FINAL.json`, identitas per job dan hash arsip/member. Panduan SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`. Tidak membaca laporan auditor lain pada putaran ini; paparan personal-context terdahulu dicatat di `EXPOSURE_LOG.md` dan tidak digunakan sebagai bukti mandiri CP2.

Ubuntu24.04, SupabaseCLI2.116.0, PostgreSQL image17.6.1.165, Python3.12/psycopg3.2.10 dan Node22; PR44 memiliki Native PG16 kernel scope terpisah. DB sementara CI saja, synthetic input eksplisit; real Auth/PostgREST/Chromium pada keluarga yang menyatakannya. Bootstrap historis disebut sebagai input rekonstruksi, bukan uji baru original CP2/hosted. Workflow SHA dan product SHA berbeda dan dibind terpisah. Putusan HOLD; pekerjaan audit putaran selesai, `audit_complete=false`, `production_go=false`.

## Vonis per checkpoint

| CP | Vonis | Bukti dan batas |
|---|---|---|
| CP1 | LULUS cakupan sumber/baseline rekonstruksi | Tree/guide/ledger/body/config identity dan build/security/source ownership. Bukan fresh hosted preflight. |
| CP2 | INCOMPLETE pemulihan; arsip LULUS | Original encrypted archive dibaca/dekripsi privat, 149/148/142/104 terverifikasi, Auth0. Tidak ada original functional restore runtime. |
| CP3/3.5 | LULUS regresi yang tercatat, dengan disposisi | 326 exact identities pada final CP7; frozen historical outputs tidak direlabel. C0 D01 terpisah. |
| CP4/4.5 | LULUS Auth/identity/WIP pada permukaan teruji | F01/F02 86, current role/revoke/real HTTP, exact ACL/catalogue. Alternative API/GraphQL belum tertutup. |
| CP5 | LULUS core Native yang tercatat | BS/rework/rewash/claim, WIP, temporal identity dan correction families; bukan semua kombinasi/perangkat. |
| CP6 | GAGAL/HOLD | SOL-001 money policy/capacity, SOL-002 evidence; positive install pertama AZ OPEN dan SOL-003 diagnostik. |
| CP7 | GAGAL/HOLD penerimaan penuh | Public supplier payment counterexample; Native range-dozens known gap. F03/F04/F05/P19/K2–K6 banyak PASS dengan batas per bukti. |

## Temuan per akar masalah

'''
for f in F:
 full+='### '+f['id']+' — '+f['title']+'\n\n'
 full+='**'+f['severity']+' / '+f['priority']+'; '+f['classification']+'; OPEN.** '+f['root_cause']+'\n\n'
 full+='Expected: '+f['expected']+' Actual: '+f['actual']+'\n\n'
 full+='Repro: '+' → '.join(f['repro'])+'\n\n'
 full+='Dampak: '+f['impact']+'\n\nPerbaikan: '+f['fix']+'\n\n'
 full+='Code: '+', '.join('`'+x+'`'for x in f['code'])+'. Bukti: `FINDINGS.json` dan original report pointer/hash dalam ledger.\n\n'
 full+='Acceptance:\n\n'+''.join('- '+t+'\n'for t in f['acceptance'])+'\n'
full+='''## Matriks dan inventaris

`INVARIANT_MATRIX.json/.csv`: semua 82 invarian, PASS/FAIL/INCOMPLETE, dasar dan batas. `SCENARIO_MATRIX.json`: seluruh SKN-01..29. `SOURCE_INVENTORY.json`: 456 src files, 310 RPC/from/schema occurrences serta SQL declarations statis; historical/superseded declarations bukan katalog efektif. `evidence/CASE_LEDGER.json` mempertahankan setiap outcome dan pointer original; alias identik dibind per SHA tanpa mengangkat total unique-oracle dari eksekusi ulang atau stand-in kernel.

Modul yang ditelusuri: opening/import/advance/settlement → procurement/invoice/return/transfer/count → cutting/work/WIP/BS/rework/rewash → accessory/laundry/conversion/pocket/recost → sales/draft/reserve/payment/return/refund → payroll → finance/report/obligation/reminder → identity/model/matching/netting/supply/plan/AI → staged retention/cleanup/K4/K6 dan release/rollback. Source requirement berasal dari dua master yang hash-nya dicocokkan dengan acuan dan framework v2, bukan status writer semata. Link jalur: komponen src → public RPC → private facade/Native writer → stock/HPP/AP/AR/cash/journal → readers; catalogue/ACL/body checks dan scoped Native/HTTP/browser evidence menentukan penerimaan, inventory regex tidak menutup runtime.

## Merah yang bukan bug produk

| Bukti awal | Klasifikasi / tindak lanjut |
|---|---|
| CodeQL scan run38560025889 failed source/workflow SHA gate | Scan empat bahasa sukses, qualification38564516689 membind SARIF asli tanpa rescan/oracle weakening; 0 result dengan positive rule/execution controls. |
| CodeQL binding38563769739 401 | Download redirect membawa Authorization lintas origin; alat diperbaiki, original merah disimpan. |
| Sol contract38562774720 4 PASS/1 INCOMPLETE | Exact Decimal formatting −30.00 vs −30 comparator; angka/oracle sama, qualification38564813436 5/5. |
| PR44 proof38564650375 ENOENT | Report output path alat tidak konsisten; qualification38565259193 235/235 dan dua mutant. |
| CP6 release readiness/source guard dan empat legacy browser | Scope era CP6 saja menolak konten/route CP7; original tetap merah. Full-stack prefreeze31 adalah replacement source-specific sesuai D13. |
| Full-stack AR stopped before races / C0 metadata blocked | CP6 BA verifier mengharapkan original owner report, sementara CP7 mempunyai declared overlay. Dua metadata callback dikualifikasi ke exact final CP7; 28 missing AR races dan 25 C0 berjalan, case bodies/amounts unchanged. |
| C0 package38578838814 cleanup failure | 25 C0 cases PASS dan group boundary restored. Satu backend active/null-user menghentikan audit copy restoration; tipe/penyebab backend pertama tidak tersimpan, tidak disahkan sebagai infra race. Qualification38584549739 memakai original25 tanpa rerun + satu timing cleanup control: bounded natural close, no termination, full boundary/catalogue restored. |
| Cleanup38583969555 cancelled | Audit packaging callback namespace diperbaiki dan qualified workflow menggantikannya; cancellation bukan PASS dan tidak diberi kredit kasus. |
| Raw AS/AO/calendar/AR zero-price outcomes | Owner D01/ERP-DEC02 superseding rule, original statuses tetap utuh; replacement proof terpisah. |

## Asal bukti

Eksekusi native independen dengan provider/fixture lama: F03 447, prefreeze31, F01/F02 86, regression and original races, correction/consumer families. Oracle baru literal Sol: lima contract cases dan paired cash capacity control. PR44: independent historical Sol oracle235, PG16 kernel only. Detector poisoning: controlled privileged injection, explicitly not proof of append-only prevention. Archive CP2: original user recovery material, no runtime restore credit. Source/static, shell/DOM, Native kernel, real Auth/HTTP/browser, measurement-scale, reused bootstrap dan owner-deferred work diberi scope masing-masing; jangan menjumlahkannya menjadi kelulusan end-to-end.

## Belum terbukti dan pengecualian owner

- Original CP2 functional restore, actual data cutover/full period, fresh hosted clone/shadow/cutover: tidak dijalankan; tidak diganti dengan synthetic green. Backup/offsite/restore kit CP7C ditunda D13-9a dan tidak dibuka oleh audit ini.
- Exact +1 poison control belum mencakup semua detektor. Dua target Sol mempunyai full before/during/after 29-function outputs. D07 control deletion yang naik +2 tidak dihitung sebagai exact +1.
- GraphQL/alternative API belum diperiksa. HTTP harness mengatur PGRST_DB_SCHEMAS=public. Observasi direct legacy SQL pada role authenticated bukan otomatis bukti bypass browser; juga bukan bukti seluruh alternative surface aman. Official references: https://supabase.com/docs/guides/graphql/security dan https://supabase.com/docs/guides/graphql/functions (14 Okt2026).
- Range-wide auto-distribution dozens pada connected sales belum terbukti/tersedia menurut source dan known writer handoff; per-line A6 browser helper lulus.
- Physical HP/iPad/Safari, real WA recipient/live delivery dan factory SLA/capacity bukan bukti ini. K7 3s tidak tercapai; temporary background acceptance owner dipertahankan. Source inventory tidak berarti setiap 456 file dibaca manual baris demi baris.
- A2 supplier old final-group failures tetap OPEN diterima D13-10; tidak duplikasi sebagai temuan baru. First AZ failure bukan otomatis A2. Semua konfigurasi pending yang sah tetap pending, tidak diisi angka buatan.

## Keputusan owner / rekomendasi

1. Bila bank boleh negatif, writer perlu keputusan eksplisit account/limit/effective policy. Rekomendasi: default aman menolak tanpa kebijakan sah; jangan menafsirkan kewenangan membayar sebagai izin overdraft tanpa batas.
2. Acceptance pemasangan: rekomendasi HOLD sampai first AZ cause/diagnostic dan recovery path dapat diperiksa. Later58/58 tetap evidence positif tersendiri.
3. Kebutuhan range-dozens: user sebelumnya meminta auto-bagi range; rekomendasi implementasi dan real connected browser proof sebelum mengatakan fitur lengkap. D13 retirement per-line tidak membatalkan kebutuhan range.
4. Urutan CP7.5/CP7C/CP8 dan keputusan D11/D13 yang sudah ada tidak ditanya ulang. Perbaikan temuan menjadi kandidat baru untuk audit ulang terpengaruh.

## Ringkasan owner

Kandidat belum boleh ditutup. Bank kosong masih dapat membayar supplier dan menjadi negatif; kontrol bank yang didanai bekerja. Artefak BE tidak lengkap walaupun 16 kasusnya lulus dalam log. Pemasangan pertama berhenti di AZ setelah51 file, sedangkan percobaan berinstrumen berikutnya memasang58; penyebab pertama belum terjelaskan. Core F03, F01/F02, temporal/races dan banyak consumer lulus pada sumber yang dibekukan. K4 menyelesaikan5.000 target lewat penjadwal asli tanpa halaman menghitung. Original CP2 utuh, tetapi pemulihannya belum diuji di runtime. Writer menerima tugas, acceptance dan pointer bukti per akar masalah; produksi tetap belum diizinkan.

## Fokus risiko berikutnya

Kapasitas kas bersama antardokumen dan backdate; penjagaan izin lewat seluruh API yang dipakai; range identity/quantity/HPP melalui correction/recost; detector sensitivity; installation/rollback diagnostics serta source-bound evidence. Tidak ada produk/main/hosted/deployment yang diubah audit ini.
'''
(R/'AUDIT_REPORT.md').write_text(full)
print('Generated 3 findings, writer tasks, 82 invariants, 29 scenarios and two handoff reports')
