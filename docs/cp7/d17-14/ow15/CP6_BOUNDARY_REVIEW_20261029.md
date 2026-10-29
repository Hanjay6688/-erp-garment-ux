# CP6: pencocokan12 batas pada sumber ab506

VENI. VIDI. VICI. ERP. Reliable data adalah dewa.
Keuangan termasuk laporan, stok, dan HPP adalah raja.

Pemeriksaan internal A, bukan keputusan auditor. Basis:
`ab50668b848a49e5544aed7f1b8ce981395175d8`, tree
`402eb28c545f64a1880cc4ba34fc9006ef7cdb11`.
Penilaian awal dikunci sebelum membaca kesimpulan pemeriksa lain. Tidak ada
DB, hosted, CI, pemasangan, atau perubahan workflow dijalankan oleh review ini.
Native SKU7 baru dan koreksi kredit D/E belum masuk basis ini.

**Hasil yang dapat dipakai:** kalimat “belum punya runner” pada beberapa baris
lama sudah usang. AF independent17, AG residual21, AH independent12, seluruh
135 perilaku focused/detector, dan36 perilaku race mempunyai pengamatan berhasil
yang terpetakan pada sumber masing-masing. Crossflow mempunyai137 dari142
perilaku terpetakan; lima absensi masih belum berhasil. Ini **bukan** PASS135,
PASS36 atau PASS142 pada satu kandidat terbaru. Tiga Original tetap INCOMPLETE;
ada penerus yang menguji kontrak sah yang lebih baru. Admission, pemeliharaan,
rollback pendahulu asli dan jalur HTTP/browser tetap dinilai terpisah.

## Bukti yang dibaca kembali

Sembilan ZIP di bawah diunduh baca-saja memakai artifact ID di receipt repo.
Ukuran dan SHA256 ZIP dicocokkan dengan receipt, lalu ukuran/hash **raw JSON**,
commit, ID, jumlah dan status kasus dibaca langsung dari entry. Tidak ada
Original diubah. Semua entry berikut berada di akar ZIP; duplikat bernama
`strict-groups/...` tidak menggantikan Original akar.

| Kode | Artifact; run; sumber | Entry Original; byte; SHA256 raw | Hasil aktual baseline / komposisi |
|---|---|---|---|
| A135 |12552283657;40074044695;`27ff04fa`|`CP7_CURRENT_CP6_AI_NATIVE135.json`;39435160;`9f8c00ded0bee193c7ee7d344d4f8f09112e1058ae1e58f735f9b5bfbe8e9fdf`|132P/3I;128P/7I; suite INCOMPLETE|
| R36 |12554330089;40076046451;`368ce870`|`CP7_CURRENT_CP6_RACE36.json`;2817657;`a9a7360a6894660497d851a7043df96a7a59f3f2f3f1ef8ab99d7eaecba67269`|23P/13I;22P/14I; suite INCOMPLETE|
| X142 |12553294724;40076046443;`368ce870`|`CP7_CURRENT_CP6_CROSSFLOW_NATIVE142.json`;41597357;`f992c82877d71e988f3a44f543295a0ac2d6817bf7940d425fa1013320fff329`|124P/18I;112P/30I; suite INCOMPLETE|
| W13 |12560807894;40095050809;`997ffe2a`|`CP7_CURRENT_WORK_PAYROLL_RACE13.json`;2776028;`0cddf07dba48b03520cf6001ab804114ae3caa6ce1011cb2acfcaf889cd58407`|12P/1I pada keduanya; suite INCOMPLETE|
| W1 |12560979882;40096433972;`d7338a92`|`CP7_CURRENT_WORK_PAYROLL_CHILD9_RACE1.json`;1906319;`2427f2846b7b943af114caf9f8b481fceff5fdd0eaeeb1b7410c5a92a4e417a1`|1P/1P; PASS|
| C6 |12589761696;40165877589;`e0a4721f`|`CP7_CURRENT_SELECTED_RETURN_CONTRACT6.json`;3801560;`fc55eeed027073451686e7c180ada527b6be20c3dcd6efcf68c26315b0094ea6`|6P/6P; PASS|
| O10 |12556896192;40083710530;`e99c1ca7`|`CP7_CURRENT_OPENING_REPLAY_READY_NATIVE10.json`;4834322;`adc8f801c858ec71395ce5851fe50f37f8d03443f0ce3030bdd3a49c14b3e25e`|10P/10P; PASS|
| L3 |12557079772;40087715870;`31b77abb`|`CP7_CURRENT_CASH_LINKED_NATIVE3.json`;2762910;`a116882c8f061db1956fd8c342eea4d8f9c24a468f8bfb4d688cd7ffc9b48c3d`|3P/3P; PASS|
| F12 |12555735321;40080319691;`f127234b`|`CP7_CURRENT_CP6_FUNDED_NATIVE12.json`;4341254;`190232afd1c59ba418e3dc5e3d73f522f497f55323467451eba70269c55d6402`|12P/12P; PASS|

P=PASS, I=INCOMPLETE. A135/R36/X142/W13 tetap mempunyai writer_runtime=false
pada paket asal; kasus yang berhasil di dalamnya tidak mengubah status paket.
W1/C6/O10/L3/F12 mempunyai lima gate paket PASS pada sumbernya. Pemulihan CP6
dan advisor yang berhasil tidak dipakai sebagai bukti fungsi bisnis.

Bukti tambahan yang dibaca: raw repo
`return-reverse3194-3a366ed6-pass/CP7_CURRENT_RETURN_REVERSE_RACES2.json.gz`,
Original883509byte/SHA256
`392bfd10e6ddb21d07319da73405000d21a769287e4774af8e14cf3609e12153`;
serta raw legacy31 yang diambil dari artifact12547777967, run40061341301,
head5681edbd: `CP7_CURRENT_LEGACY_UI_BROWSER31.json`,648018byte/SHA256
`cbfd3ac9c94d3e810099b23fc3913b47379a44501c3522b33b29398637524918`, PASS31.

## Dua belas baris: yang sudah cocok dan sisanya

Identitas/status asal adalah r2 di
`audit-candidate/cp1-7-r3-20261017/R3_08_CP6_WORKFLOW_SUCCESSORS.json`.
Tanda “guard” berarti berhenti sebelum bootstrap/kasus; bukan kegagalan
transaksi yang berhasil direproduksi. Tidak satu pun run merah diubah statusnya.

| Workflow / sumber asli; hasil asal | Penerus yang sudah ada dan jenis bukti | Exact remaining gap dan dampak delta current |
|---|---|---|
|`cp6-ac-independent-audit.yml` — AD pada AC1bdca376; NOT_RUN, hanya trigger cabang historis|**Transaksi:** X142 memuat55 jalur DAY asli melalui AE;40P langsung,10 penerus O10,5 absensi I. Sepuluh bentuk FABRIC tanpa roll tetap menjadi kontrol penolakan AE. **Install/inverse rilis:** T3 memasang AD yang guard-nya dipin ulang; bukan file pendahulu asli.|**Belum:**5 absensi; enam AD detector controls yang mengembalikan writer lama; predecessor55/admission dan20 maintenance AD serta rollback pada file AC→AD asli belum dicocokkan ke raw hasil asal. `cp6_v2620ad_reuse_matrix.py` mengikat20 schedule Native5/run34967943841/artifact10396157668, source24ad7483 dan manifest6676986e…; ini alamat bukti yang spesifik, bukan20 tes baru yang otomatis wajib. CP7 tidak mengubah file SQL asal; efek pelaporan/guard selanjutnya harus dinilai pada penerusnya.|
|`cp6-ad-roll-opening-check.yml` — AF pada AEce8e8ea5; run38894846530 FAIL, artifact AE10418502157 HTTP410|**Transaksi/detector:** AF30+11 sudah dijalankan sebagai `AH_AG_WRITER_AF_*`/`AH_AG_AF_*` dalam A135,41P. **Dua sesi:** AF4 dalam R36 semuanya P. Crossflow134 diwarisi X142/F12/O10/L3.|**Belum:**7 admission pada AE, pembanding bug dua sesi AE asli,20 AF maintenance dan8 rollback refusals file AF asli. Ini bukti tahap pemasangan lama; restoration final bukan penggantinya. Kebutuhan transaksi AF tidak perlu dijalankan ulang30+11+4 hanya karena label tabel lama.|
|`cp6-af-independent-review.yml` — AFf4669986; run38894849298 FAIL, no-merge guard|**Transaksi17 cocok:**12 `SALE_*` lewat wrapper AG `ORIGINAL_*` serta5 `AF_OPENING_*` lewat AF `ORIGINAL_*`, semuanya ada dan P di A135. `sale_case` dan `opening_change` tetap sumber asli; wrapper penerus mengharuskan perbaikannya, bukan melestarikan BUG_PROVEN.|Tidak ditemukan gap kasus bisnis tambahan pada17 perilaku ini. Pemetaan dan pengikatan sumber akhir menunggu penilaian auditor; menjalankan fungsi berlabel independent lewat alat writer tidak menjadi audit independen.|
|`cp6-ag-residual-review.yml` — AG119f8f13; run38894851987 FAIL, no-merge guard|**Transaksi21 cocok:**17 kontrol retained masuk A135 (15P/2I); dua I `RETURN_SPLIT`/`RETURN_REBIND_CUSTOMER` terwakili C6. Empat reproducer bug lama diganti kontrol AH yang sudah ada: allocation limit, draft-source, ordinary six-grade/destination, source-rebind. Yang terakhir terwakili C6.|Tidak perlu membuat21 kasus baru. Auditor menilai kesetaraan empat pengganti dan kontrak guard C6. Original AG yang membuktikan bug dan A135 yang I tetap utuh.|
|`cp6-ag-sale-reservation.yml` — AG pada AFf4669986; run38894854683 FAIL, no-merge guard|**Focused/report:**AG51+23 tersarang dalam A135, seluruh74P. **Dua sesi8:**AF4+AG4 dalam R36,8P; AF4 diwarisi, jangan dihitung dua kali. **Crossflow:**X142 dan penerus sesuai ID.|**Belum:**admission AG,20 maintenance AG, validasi raw artifact counterexample AF dan lifecycle original8 refusals/restore pada pendahulunya. Jangan mengulang8 race yang sudah berhasil. Current return changes punya C6/return3194, bukan alasan menganggap seluruh AG baru gagal.|
|`cp6-ah-independent-review.yml` — AH965ceac4; run38894857288 FAIL, no-merge guard|**Transaksi12 cocok:**11P dari blok AH independent A135; `SOURCE_REBIND` I dipetakan C6 `RETURN_REBOUND_SOURCE_ATOMIC_REFUSAL`. Dua-allocation fixtures asli tetap dipakai; bukan fixtures salah yang memakai satu allocation dua kali.|Tidak ditemukan gap bisnis12 tambahan. Penerimaan pemetaan current guard milik auditor; pekerjaan Native/OWNER ini tidak membuktikan HTTP/browser maupun audit independen.|
|`cp6-ah-return-allocation.yml` — AH pada AG119f8f13; run38894860217 FAIL, no-merge guard|**Focused/report:**seluruh blok AH di A135; reference WORK/VENDOR dan guard retur dipetakan C6, semua detector36 P di A135. **Dua sesi8:**6P retained AH + return commit/abort penerus; return3194 memeriksa keduanya pada backend3194. **Referensi:**C6 memeriksa OWNER insertion tanpa memperluas SELECT/EXECUTE dan kewajiban payroll.|**Belum:**admission AH,20 maintenance AH dan capture/restore pendahulu/original reference-negative proof yang terikat AG. Teks “no runner focused/report/race” tidak lagi benar. D/E belum berada di basis dan tidak dikreditkan di sini.|
|`cp6-ai-independent-review.yml` — AI-R2 25fa4736; run38894862576 FAIL, no-merge guard|**Dua sesi12 cocok:**dua peer race P di R36;10 lainnya P di W13 melalui populate/approve payroll Native yang eksplisit. Original lock/commit/abort/rate/uang dan final READY dipertahankan; tambahan prerequisite dicatat lewat transformasi tepat.|**Belum:**capture AH dan pembandingan restore independen pada boundary asal. Bukti restore komposisi baru berbeda lingkup. Tidak ada alasan mererun12 race hanya untuk memperoleh nama suite hijau.|
|`cp6-ai-work-source.yml` — AI pada AH965ceac4; run38894865676 FAIL, no-merge guard|**Focused/report135:**128P retained +7 ID yang dipetakan enam kontrol C6. **Dua sesi16:**AH8 di atas +AI8; tiga AI yang I terwakili dua W13 +W1 untuk `HEADER_CHILD_ABORT`. W1 mempertahankan9×1.25=11.25 dan lock nyata. **Crossflow:**137/142 perilaku terpetakan.|**Belum:**AI admission8,20 maintenance AI dan original AH counterexample qualification/capture jika dibutuhkan untuk menutup arsip tahap asal; lima absensi. A135 dan W13 tetap I. Tidak ada status PASS135/16 satu run yang diciptakan dari penjumlahan.|
|`cp6-ap-flow.yml` — AO/AP proposal pada AN; run38894871775 FAIL, changed-file guard|**Sebagian transaksi/browser terkait:**E24 issue pada06ba28b0/run36658126203 membuktikan nota7×3.25=22.75, sumber receipt/transfer dan inverse desktop/HP. Local recovery67 pada vendor2d4 dan checker tersedia. Ini tidak sama dengan edit draft5→7.|**Belum exact:**AP browser draft5→7/manual-price, import edit14.25→17.25/validate/finalize/lost-reply; enam HTTP race `IMPORT_SAME_UUID_FINALIZE`, `IMPORT_EDIT_BEFORE_FINALIZE`, `ACCESSORY_COMPETING_STOCK`, `ACCESSORY_SAME_UUID`, `POCKET_BUSY_AND_STALE_RETRY`, `POCKET_PERIOD_BUSY_THEN_RETRY`. P09 receipt22 dan OW06 transfer tidak otomatis menggantikannya. New recovery/source6 CSS tidak mengisi race impor/pocket ini.|
|`cp6-final-boundary-audit.yml` — AI-R2…AN; run38894936507 FAIL, no-merge guard|**Sudah ada:**X142/penerusnya; work peer12/R36/W13/W1; T3 install/inverse; current paged lists, transfer, Auth dan browser punya bukti masing-masing. Original AM evidence mempunyai alamat exact: full run35663140263/artifact10668124130 (ZIP29968405…), bridge transfer8 run35665864959/artifact10669107236 (ZIPa909662a…), diikat `cp6_v2620an_gate.py`.|**Belum dicocokkan per raw ID/source:**AM SQL trial;AN native28/UI15 late PO201/draft101;12 transfer,4 import-draft,12 direct DRAFT BS/WIP schedules;20 maintenance masing-masing AM/AN;controlled-midnight;transfer crossflow8;HTTP role/lifecycle/disposable frontend. Original16 schedules dan work12 **bukan lagi semuanya gap** (lihat R36/W13/W1/return2). Cari raw alamat AM/AN dahulu; source-matched reused evidence dapat menutup scope asal tanpa mererun seluruh workflow. Current generic Auth/owner lists bukan otomatis oracle AN yang sama.|
|`cp6-initial-import-review.yml` — AP proposal pada AN; run38894941618 FAIL, changed-file guard|**Checker cocok:**`check-production-recovery.mjs` sudah dijalankan pada sumber vendor yang diadopsi; receipt vendor-money2d4,67 local tests, typecheck/build. **Sebagian keluarga impor:**AO dan31 import successor pernah terpetakan di T2/AV; bukan keseluruhan usulan AP.|**Belum exact:**`cp6_initial_import_trial.py` beserta seluruh declared RPC proposal/receipt/production/accessory/advance/prepayment/pocket cases pada boundary yang sesuai. Source-nya tersedia; keberadaan nama di manifest bukan bukti dijalankan. Jangan menyebut local recovery sebagai Native import qualification.|

Sumber tabel: isi modul kasus/workflow di repo, bukan sekadar hasil pencarian.
Tiga baris yang hanya meminta transaksi (AF independent, AG residual,
AH independent) sudah mempunyai cakupan perilaku yang terpetakan. Baris lain
tetap parsial sesuai kolom terakhir; review ini tidak menulis12/12 closed.

## Perhitungan yang mencegah tes ulang sia-sia

- **A135:**99 focused terdiri dari12 AH independent,5 AI lifecycle/partial,
  17 AG residual retained,14 AH ordinary/reference,12 AF sale,9 AG draft dan30
  AF/AE. Detector36=AI5+AH8+AG12+AF/AE11; seluruh36 P. Tujuh ID I adalah
  `PARTIAL_WORK`, `AH_REFERENCE_WORK`, `AH_REFERENCE_VENDOR`, `SOURCE_REBIND`,
  `AH_SOURCE_REBIND`, `AH_AG_RETURN_SPLIT`, `AH_AG_RETURN_REBIND_CUSTOMER`.
  C6 memetakan7 ID itu dengan enam kontrak eksplisit. Tiga pertama menuntut
  BLOCKED sebelum payroll sah, bukan mengubah READY lama menjadi PASS.
- **R36:**AF4+AG4+AH8+AI8+peer12=36 unik.22 P retained +12 P W13 +1 P W1
  +1 current return-commit successor=36 perilaku; return-abort sudah ada
  dalam22, jadi dua retur tidak menambah total menjadi37. W13 gagal hanya
  pada helper yang menerima4/6/10 tetapi bukan9; W1 membuktikan9 dan11.25
  tanpa mengganti kuantitas/fungsi child() asli. Tidak ada race13 tersisa
  yang perlu dibuat ulang hanya berdasarkan tabel24 Oktober.
- **X142:**112 P retained +F12(12)+O10(10)+L3(3)=137 perilaku. O10
  mempertahankan tanggal/stock/cost/cent/READY asli dan menguji guard replay
  `AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH`. L3 mempertahankan sumber
  kerja1September, Native payroll2September, cent/inverse/corruption oracle.
  Lima yang belum berhasil persis `DAY:ATTENDANCE:DIRECT:` pada Jakarta,
  UTC, Tokyo, Kiritimati, GMT+12. F12 tidak menyelesaikan18 baseline gagal
  sendirian; O10/L3-lah yang kemudian memetakan13 di antaranya.

## Batas source matching pada ab506

Manifest frozen qualifier dibandingkan langsung dengan byte workspace:
A135 mempunyai405 input `scripts/`/`supabase/` yang tetap sama; R36 mempunyai411
yang tetap sama; O10 mempunyai554 yang tetap sama. W13/W1 masing-masing629/637
input backend, dengan tiga beda pada `check-access-catalog.mjs`,
`check-source-ownership.mjs`, `cp7_ow11_analog_browser.mjs`; kode race, payroll
prerequisite, CP6 oracle dan SQL-nya tidak berubah. Perubahan UI/tooling
lainnya pada manifest penuh tetap diungkap; tidak diklaim manifest historis
seluruhnya sama. C6 mempunyai perubahan UI/tooling yang dideklarasikan juga.

Ini menyelesaikan identitas fungsi/perilaku retained, bukan membuktikan semua
dependensi runtime komposisi terbaru setara. Lapisan baru analisis/factory
memverifikasi katalog aktual sebelum delta; vendor41c mengubah tujuh fungsi
BD vendor yang disebut `cp7_vendor_receivable/native_delta.py`, tanpa mengganti
post_journal, reverse_journal, stock/HPP engine, work posting atau source
opening/sales. Return2 telah diikat ulang ke backend3194. Source6 hanya dua
suffix CSS yang diadopsi. Perbedaan graph final yang benar-benar menyentuh
perilaku tetap memerlukan binding/penerus terarah, bukan edit pin historis.

## Prioritas terkecil yang praktis

1. **Tanpa DB dahulu:** masukkan W13/W1/O10/L3 ke mapping auditor beserta
   raw/hash di atas; cocokkan raw lifecycle AD/AF/AG/AH/AI dan AM/AN ke
   capsule/oracle yang tetap. Tidak ada kebutuhan baru30+11 AF,21 residual,
   race13, atau Crossflow142 penuh yang muncul hanya karena tabel tertinggal.
2. **Candidate Native5 saja:**
   `scripts/current-cp6-attendance-day5-qualification/` memilih lima closure
   Crossflow asli, label dan zona tetap, tanpa menjalankan137 lainnya.
   Offline preflight547 source pins, tiga kontrol penolakan selection dan
   gate raw X142 sudah PASS; **nol DB/runtime case dijalankan**. Runner
   menyiapkan baseline CP6 dan current full vendor41c secara terpisah dengan
   full backup/reset baris/sequence/katalog/roles. Tidak ada workflow baru.
3. **Perhatikan oracle absensi:** sumber asli mem-posting PRESENT melalui
   public attendance RPC, bukan injeksi posted. Kasus sebelumnya sudah
   mencapai pemeriksaan tanggal, lalu AE meminta READY saat absensi baru
   belum payroll: `PAYROLL_ATTENDANCE_UNCOVERED`. Exact replay dapat tetap I.
   Candidate tidak menyisipkan payroll sesudahnya, mengubah nominal/rate/day,
   atau mengganti expected dengan BLOCKED/PASS. Bila diperlukan pengganti
   kontrak, auditor menilai coverage dahulu; raw I tetap dipertahankan.
4. **Sesudah retrieval/source matching:** hanya jalur AP/AN/AM yang memang
   belum punya saksi setara yang mendapat targeted Native/HTTP/browser
   qualifier. Enam AP HTTP race bukan Native SQL dan tidak ditutup dengan
   Native5. Maintenance20 dan rollback8 ditargetkan hanya pada edge yang
   sumber/bukti aslinya belum dapat dicocokkan atau benar-benar berubah.

## Yang menunggu auditor, bukan fitur/tes baru otomatis

- **D13-9c/D13-12:** putusan LENGKAP/TIDAK LENGKAP atas pensiun
  `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`. Legacy31 yang asli sudah
  PASS, termasuk dua P11 helper journeys; putusan bersyarat owner belum
  berubah menjadi penerimaan auditor. Ini terkait bagian helper PCS dari
  ACC-A01/ACC-D09, bukan penutupan seluruh requirement tersebut.
- **P00/P18, R3-08; AUD-T01:** penilaian pemetaan per sumber/behavior yang
  tertera di sini. Tiga baris transaksi yang sudah cocok dan seluruh36
  perilaku race tidak perlu diciptakan ulang untuk memperoleh audit verdict.
  Gap lifecycle/AP/AM/AN dan attendance5 di atas belum boleh disebut hanya
  menunggu tanda tangan.
- **P20/OW15:** penerimaan independen/final candidate dan apakah gabungan
  evidence yang source-scoped mencukupi. `closure_current_20261029.json`
  tetap indeks271 requirement, bukan271 runtime failures atau PASS.
  ACC-D11 juga menuntut pemasangan/inverse/restoration di lingkupnya;
  current vendor11/restore tidak otomatis menutup semua capsule historis.

**21 kegagalan** dalam README r6 adalah21 **run workflow CP6 lama**, dengan
job/step yang sama dengan kandidat sebelumnya. Ini berbeda dari21 kasus
residual AG. **Empat browser baseline** adalah dua READINESS pada tumpukan
CP6 yang tidak memasang dua RPC CP7, serta dua SALES_MANUAL_13 dengan selector
simulasi. Run39396888098/headc512a178 tetap melaporkan104 Native/26 race/9 HTTP P,
27 browser P/4 I. Artifact12253002117 yang dibaca ulang berisi hanya
`AUDITOR_CASES_AFTER.json`104P,247450byte/SHA256
`0ec2738384bb41c651b5d83d6949b7e097f4a3e05bcbd6f5019be34ad166ba57`;
raw browser tidak ada di ZIP itu, sehingga empat status browser diambil dari
receipt/README r6 dan tidak diklaim diverifikasi ulang dari entry tersebut.
Legacy31 successor tidak mengubah status empat baseline ini.

Review dan candidate ini tidak mengubah registry/status bersama, produk,
source/workflow historis, kandidat audit beku, main, Enteng/hosted, legacy,
WA/Drive, CP7C atau cutover. Formal tetap5/16,
`independent_acceptance=false`, `production_go=false`.
