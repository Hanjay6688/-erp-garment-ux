# FINAL AUDIT CP6 — CP6_HOLD

Checkpoint independen sesudah handoff1ee47b02 tersedia di
[cp6-final-successor-independent.md](cp6-final-successor-independent.md).
Alat audit2a6161ea, produk tetap47671d9:9 kasus residual selesai,6 PASS,
1 gap diagnostik referensi import,2 HOLD tanggal; restore/cleanup PASS.
Nominal dan downstream recovery lulus pada cakupan teruji; CP6 tetap HOLD.
Status dan bukti terbaru pada dokumen tersebut mengungguli status historis di bawah.

## Lanjutan 2026-09-17: nominal claim dan kompensasi

Checkpoint masuk `0c234171fb59dfabc7fa03d4e27904bc2b2f53a7`, tree
`7d9d09590aeaa9b5a5831e1076382b40d7460395`. Branch masih satu writer yang
sama. **CP6_HOLD; production_go:false; CP7 belum dimulai.** Bagian lanjutan
ini mengungguli status arsip dan perubahan frontend pada checkpoint sebelumnya.

**Snapshot yang benar-benar diuji:**
`2c9465994b3827bc3db82af52753dc5eb80df141`, tree
`3fe4f342ea41c987c4a693339d5590db3b486f2a`.
[Native35174491617](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35174491617)
selesai: workflow FAILURE hanya karena BUSINESS mewarisi12 pengamatan tanggal
berstatus HOLD. UI, HTTP, rework, concurrency, maintenance, clock, exact restore
dan cleanup lulus. Gate tidak dilonggarkan. Ini **Writer PASS pada cakupan tersebut,
bukan independent PASS atau CP6_LOCK_READY**.
[CodeQL35174491674](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35174491674)
Actions, JS/TS, Python, dan C/C++ semuanya SUCCESS.

| Cakupan | Bukti terakhir |
| --- | --- |
| Matrix bisnis230 | Fresh pada47671d9:179 PASS +39 CONTROL_PASS +12 DATE_POLICY_REVIEW_REQUIRED;0 incomplete/fail |
| Rework/rewash12 | Fresh12/12 PASS pada2c946599;0 incomplete |
| Business218 selain rework | REUSED_EVIDENCE dari47671d9:206 hasil berhasil +12 pengamatan tanggal; product bytes exact; bukan218 fresh PASS pada2c946599 |
| UI/Auth/HTTP | Fresh43/43 UI asli +58/58 kontrol tambahan;95 assertion HTTP/62 facade-role cases |
| BS/claim role | Fresh96 pasangan action-mask +32 pasangan khusus nominal positif; bukan semua peran di semua modul |
| Concurrency/maintenance/clock | Fresh28 concurrency,20 maintenance,4 controlled-clock cases PASS |
| Rollback | Fresh8 kontrol refusal; AJ -> AI533 fungsi/224 tabel, AI -> AH533/223; full data/owner/ACL boundary exact |
| Cleanup | Auth/app users0, auth sessions0, clone dan container disposable0; PASS |
| Source/build |237 unit/DOM tests, source/access/backend checks, build dan CodeQL PASS |

Artifact terakhir
[10477389132](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35174491617/artifacts/10477389132):
53,577,549 byte,293 entry ZIP; SHA256
`146dc8de156bfbd18060b40d3a5b7af0d33a99e19c95f371ee2ca36dd5f11ee0`.
Byte lokal cocok, CRC valid, path unik/aman, tidak ada symlink. Selected-pattern
scan GitHub token/JWT/private key/sb_secret:0 kecocokan. Arsip diambil dan diperiksa,
bukan hanya membaca digest dari metadata GitHub.

**CP6-CLAIM-MONEY-01 terbukti pada form React asli**: input klaim14.25 dikirim
ke RPC sebagai14; input0,25 menjadi0. Form penggunaan kompensasi juga mengirim14
untuk14.25 dan menonaktifkan posting untuk saldo0.25. Empat counterexample DOM
menggunakan source produk exact checkpoint masuk; transport RPC dimock, sehingga
bukan bukti nominal salah sudah terposting di database. Identitas source dan
hasil sebelum perbaikan ada di `docs/evidence/cp6-claim-money-original-dom.json`.

Kedua kolom sekarang menyimpan input pengguna, menerima titik/koma dan dua angka
desimal, lalu mengirim nominal tanpa pembulatan qty. Input tidak sah atau melebihi
saldo ditolak sebelum submit, tanpa mengganti nominal diam-diam. Tampilan nominal
di halaman yang sama mempertahankan sen. Qty fisik tetap bilangan bulat.
237 unit/DOM tests, pemeriksaan source/access/backend, dan build lokal PASS.

Harness tambahan menguji alur UI/Auth/HTTP asli: kirim10 -> receipt8 Good/2 BS ->
claim14.25 -> settlement -> pemakaian kompensasi -> linked reversal. AP berasal
dari DRAFT invoice70 yang dipost lewat fungsi native existing dengan mapped OWNER;
setup/teardown ini **bukan** bukti antarmuka invoice. Semua32 pasangan action-mask
bernilai positif dan lifecycle UI selesai PASS. Input14,25 tersimpan14.25; settlement
membuat satu jurnal debit/credit14.25 dan menurunkan AP70 ->55.75. Pemakaian pada2 BS
tidak mengkredit AP lagi, replay aktor sama inert, kapasitas habis ditolak HTTP400,
dan reversal claim yang masih dipakai ditolak HTTP409 secara atomic. Linked reversal
mengembalikan AP, lalu koreksi invoice/receipt/delivery mengembalikan saldo awal,
WIP0,FG0,ready10 dan laporan READY. Histori koreksi tetap tercatat.

Karena byte frontend produk berubah, reuse218 AJ3 sebelumnya dibatalkan dan
combined gate menjalankan230 kasus bisnis fresh pada47671d9. Follow-up2c946599 hanya
membetulkan fixture; reuse218 sekarang berasal dari47671d9 yang byte produknya sama.
Seluruh UI/HTTP,12 rework,28 concurrency,20 maintenance,4 clock, rollback dan cleanup
dijalankan fresh pada follow-up. Matrix460 historis tetap historis. Gate tanggal
tetap menahan lock sampai kontraknya selesai.

Aturan owner yang sudah ditemukan kembali: master AD section16.1–16.5 memisahkan
waktu fisik/ekonomi/sistem/posting, mempertahankan histori, mengalirkan koreksi biaya
ke RM/WIP/FG/COGS/AP/GRNI dan laporan, serta melarang READY ketika integritas/recalc
belum selesai. Koreksi periode terbuka bukan otomatis snapshot immutable.
Pengamatan12 tanggal belum boleh dianggap PASS hanya karena total hari ini cocok;
pilihan tanggal jurnal invoice dan recost harus tetap dikualifikasi bersama.
Master section21.1 mewajibkan preview, error per baris, rekonsiliasi, idempotensi dan
pemulihan import. Penempatan UI CSV pada CP6 atau CP7 belum ditemukan secara eksplisit;
parser/upload tetap BELUM TERUJI dan tidak dilabeli N/A.

Arsip AJ5 sudah berhasil diverifikasi ulang secara lokal:52,895,688 byte,
292 entry ZIP unik, path aman, tanpa symlink, CRC valid; SHA256
`30a221e159298fae92304dc871457a74f7891c92590cc75d9e11bcfe975f0127`.
Scan pola GitHub token/JWT/private key/sb_secret tidak menemukan kecocokan.
Ini menutup gap transfer arsip sebelumnya; bukan sertifikasi seluruh kemungkinan
credential. Isinya mengonfirmasi12 rework PASS,95 HTTP,43 UI +51 kontrol tambahan,
96 action-mask,20 maintenance, rollback exact533/224 lalu533/223 dan cleanup.

Writer perbaikan nominal tetap chat ini; independent acceptance masih wajib dari
auditor lain pada repaired snapshot exact. Main/PR/UAT/legacy/hosted DB tidak diubah.

**Sisa gerbang lock:**12 pengamatan tanggal laporan; parser/upload CSV yang belum
ada dan penempatan scope CP6/CP7 yang belum eksplisit; independent acceptance atas
AJ dan perbaikan nominal. Gap alur positif claim/kompensasi dan verifikasi ZIP sudah
ditutup pada cakupan di atas. Tidak mengklaim seluruh role atau seluruh UI ERP PASS.
Main terakhir diverifikasi
`6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. Integrasi preview Cloudflare existing
berjalan mengikuti push competition; tidak ada deployment manual atau merge.

Commit penutup setelah2c946599 hanya mengubah dokumen ini. Auditor selanjutnya wajib
memeriksa diff/head/tree, membaca arsip exact, dan memakai oracle sendiri. Uji family
yang berubah beserta hubungan antarmodulnya secara terkonsolidasi. Keluarkan
CP6_LOCK_READY, CP6_HOLD, atau INCOMPLETE dengan bukti; `production_go:false`.
Jangan mulai CP7 sebelum independent PASS dan perintah owner.

### Riwayat attempt nominal1 dan koreksi harness

Attempt nominal1: `47671d9ba2cfb8d02658388adb364b2ae6b89e8d`, tree
`46f4f605444c72dc32282025b859ab66375178b3`, Native35173583560. Seluruh230
kasus bisnis dieksekusi fresh:179 PASS +39 CONTROL_PASS +12 DATE_POLICY_REVIEW_REQUIRED,
0 incomplete/fail; semua kontrol rework/import lolos. CodeQL35173583505 empatSUCCESS.
UI klaim14.25 telah mencapai settlement, penggunaan kompensasi,32 pasangan izin,
refusal kapasitas/dependensi, dan reversal dengan saldo AP kembali. Harness lalu
mencoba tombol Tolak claim pada status REJECTED: kontrak asli sudah membatalkan
claim lewat reversal, sehingga tombol itu memang tidak ada. Ini fixture INCOMPLETE,
bukan kerusakan transaksi yang dibuktikan. Grup rework setelahnya juga INCOMPLETE
karena setup money belum dikoreksi sampai akhir, bukan PASS dari attempt lama.

Follow-up hanya menghapus langkah reject yang tidak berlaku dan mengassert status
REJECTED authoritative. Byte frontend/SQL/package produk sama dengan attempt1.
Reuse218 dipindah ke bukti fresh attempt1, dengan head/tree/digest, product diff,
CRC,690-object install dan full boundary tetap diperiksa. Rework12, seluruh UI,
HTTP,28 concurrency,20 maintenance,4 clock dan exact rollback tetap fresh.
Artifact10477942082:53,007,482 byte/292 entry, SHA256
`9d2c1906c3f6bd5c11e46d7baa9740d4eb11d260f6d63c8b88d09bb4950c6abd`,
CRC, path/duplicate/symlink dan selected credential-pattern scan sudah diperiksa
lokal tanpa kecocokan. Dua belas pengamatan tanggal diwariskan sebagai HOLD;
qualified reuse tidak mengubahnya menjadi PASS.

---

## Riwayat checkpoint 0c234171 — digantikan status lanjutan di atas

Checkpoint penutup audit independen dan giliran writer AJ, 2026-09-16 UTC.
Bagian ini adalah status historis. **CP6_HOLD; production_go:false; CP7 belum dimulai.**

Dua perbaikan writer yang diterima dari handoff lolos pemeriksaan ulang pada
cakupan yang diuji. Audit ini menemukan satu bug bisnis nyata pada recovery
rework/rewash dan dua gap diagnostik import, lalu mengambil giliran writer
setelah memastikan branch masih pada SHA yang diharapkan. Perbaikan AJ telah
lulus kontrol perbaikannya; ini **belum independent acceptance atas AJ**.

## Identitas yang harus dipakai

- Handoff masuk: `555d8f29ea2d3f58dc2c7d10e7cd80099cdd3b49`;
  snapshot writer masuk `9a919060b1037fe0747515b6ed3b98aebb41b5b1`.
- Backend predecessor AI-R2:
  `25fa4736329e5148dfdb3572bc169952cba23251`,
  tree `a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d`.
- **Snapshot AJ yang benar-benar diuji**:
  `9173d2f4e05cbdbf01fee616b9826c6c4dbc919a`,
  tree `760806a50cc47dfdedf8cd4deb6945547187620b`.
- Branch satu writer: `competition/cp6-j-closure-20260911`.
- [Native run 35154446764](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35154446764)
  selesai. Kesimpulan workflow FAILURE karena BUSINESS=HOLD untuk 12
  pengamatan tanggal yang masih terbuka; bukan kegagalan 12 kasus rework.
  Gate tidak diubah menjadi hijau.
- [CodeQL 35154446821](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35154446821):
  Actions, JS/TS, Python, C/C++ semuanya SUCCESS.
- Commit checkpoint penutup hanya mengubah dokumen ini. Jangan mengklaim SHA
  checkpoint dokumen sebagai snapshot runtime baru. Periksa diff terhadap SHA
  teruji di atas sebelum menerima atau menggunakan kembali buktinya.

## Temuan dan perubahan

**CP6-BS-REWORK-QC-LOT-01, terbukti pada kode asli.** UI/Auth/HTTP asli mengirim10,
menerima10, lalu QC0 Good/10 BS. Rework mandor5 selesai3 Good/2 BS. Rewash
terpisah5 dari kasus BS yang sama menerima partial, tetapi completion3 Good/2 BS
gagal HTTP409/23505 pada `uq_fg_lots_qc_item`. Kedua recovery mencoba memakai
slot FG unik milik QC asal. Respons gagal ini tidak membuktikan komit saldo salah;
bugnya ialah transaksi recovery normal tidak dapat selesai. Pesan UI juga
keliru menyebut konflik itu sebagai permintaan yang sudah diproses.

Bukti asli: R5 `a2d5a42c5fc2e99249aa73b47d74747bb7aa6dd6`,
Native35145449818, artifact10467267798, SHA256
`dea2228699da1a6174694adc7b3f54ec813fa4fdb41de01f3f92abc146e435cb`.
Ini bukan fungsi produk yang sengaja dibuat salah.

AJ memakai identitas recovery tersendiri sambil mempertahankan hubungan
rework-order -> BS -> QC asal untuk HPP dan biaya cucian gagal. Constraint
output QC asli tetap ada. Pesan UI membedakan konflik data dan identitas
permintaan. Dua gap import—qty bukan angka dan biaya wajib yang hilang—kini
menghasilkan error per baris beserta hitungan akhir, dan input draft bisa
dikoreksi lalu divalidasi ulang. Kontrol juga mencakup angka tidak hingga,
biaya negatif dan biaya tidak numerik. Tidak ada antarmuka CSV baru.

Enam fungsi existing berubah melalui satu migration AJ dan rollback exact.
Byte produk AJ tidak berubah sejak `ce1b05b1719f16e1e6bd3b7c363dca0c71970e54`;
follow-up hanya membetulkan fixture, pengikatan path bukti, dan dokumentasi.
Migration SHA256:
`2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea`.
Rollback SHA256:
`896baab52089adf56c60562cf3161391e01392aec972b48408752fc4e417aed9`.

## Bukti baru dan bukti yang dipakai kembali

| Cakupan | Hasil dan asal bukti |
| --- | --- |
| Dua perbaikan UI masuk: dasar ALL_READY dan nama proses receipt | Pemeriksaan independen pada kandidat asli serta regresi43 UI; tetap lulus pada AJ |
| 12 kasus rework/rewash AJ | Fresh12 PASS,0 incomplete pada SHA9173d2f; Good awal0/4, urutan mandor/laundry, cucian gagal berbayar, receipt bertarif7/11, partial inert, replay, biaya/upah, larangan reverse QC asal dan reverse satu recovery |
| 142 crossflow +23 work +16 invoice +24 calendar +13 import | 218 REUSED_EVIDENCE dari exact AJ attempt3:206 hasil berhasil,12 DATE_POLICY_REVIEW_REQUIRED. Bukan218 fresh PASS |
| Invoice calendar | Semua24 total saat ini cocok; interval31/62/89/92 hari mencakup1–3 bulan kalender dan ujung bulan;12 pengamatan historis periode terbuka tetap ditahan |
| Concurrency | Fresh16 jadwal original +12 kontrol independen, PASS pada AJ; native memakai fixture terpisah dan bukan klaim HTTP |
| Maintenance AJ | Fresh20/20 PASS; assertion matrix lama dipertahankan, sumber migration/rollback diikat ke AJ |
| Transport dan UI | Fresh95 assertion HTTP/62 facade-role cases,43/43 UI, kelompok tambahan UI PASS_REVIEWED_SCOPE serta gate96 pasangan action-mask lengkap; bukan seluruh role di semua modul |
| Batas hari | Fresh4 controlled-clock cases PASS,0 incomplete; waktu hanya di clone disposable |
| Build dan pemeriksaan source | Fresh232 unit tests, pemeriksaan source/access/build dan build selesai |
| Rollback | Fresh8 kontrol penolakan; AJ -> AI533 fungsi/224 tabel, lalu AI -> AH533/223; definisi/owner/ACL/full data boundary exact |
| Cleanup | Auth/app users0, auth clone0, container PostgREST0, database disposable dihapus; cleanup PASS |
| 460 maintenance historis F–AB | REUSED_EVIDENCE historis saja; tidak dihitung sebagai fresh AJ dan tidak diulang untuk menaikkan angka |

Reuse218 dikualifikasi oleh head/tree, ZIP checksum/CRC, installation690,
boundary/catalog/izin yang pulih, identitas daftar kasus dan byte produk
src/SQL/package yang sama. Sumber:
`f1f9e21a1be64ee523b408bcd77282748b3fa215`,
tree `9a66c776949ff1dfa5e7f69ae308100b7c11efed`,
artifact10469682433, SHA256
`9549cec70eb6c63d276afc320d5d6f2ee020184052fdbf51486d9fdb5a026e26`.
Dua belas fixture rework yang sebelumnya terhenti tidak digunakan kembali
sebagai PASS; run terakhir menyelesaikannya melalui facade publik yang sah.

## Yang masih menahan lock

1. **Tanggal laporan.** Dua belas pengamatan historis pada periode terbuka:
   invoice memakai tanggal invoice lama, sedangkan recost/HPP bergerak pada hari
   proses. Posisi material historis bisa -5.25 atau7 dengan raw qty0, sementara
   FG/COGS historis masih nilai lama; total saat ini cocok. Periode terbuka tidak
   otomatis merupakan snapshot laporan yang telah dikunci. Label BUG_PROVEN
   otomatis pada R3 telah ditarik; status tetap DATE_POLICY_REVIEW_REQUIRED,
   bukan PASS. Kualifikasi kontrak tanggal laporan sebelum memilih perbaikan.
   Kontrol closed-through tanggal receipt belum membuktikan semua kemungkinan
   snapshot periode tertutup.
2. **CSV.** Parser/upload dan caller staging/finalize tidak ditemukan di aplikasi.
   Backend13 kontrol import yang lulus tidak membuktikan transport CSV. Master
   section21.1 menetapkan error baris, preview/total, idempotensi dan pemulihan;
   penempatan deliverable UI CSV pada CP6 atau CP7 perlu dipastikan dari aturan
   owner. Tidak diberi PASS atau N/A.
3. **Cakupan role/UI.** Uji positif klaim/kompensasi bernilai uang belum tercakup
   oleh kontrol role bernilai nol;96 pasangan action-mask bukan semua peran pada
   semua modul.
4. **Independensi.** Chat ini sudah menjadi penulis AJ. Auditor lain harus
   menilai exact repaired snapshot memakai oracle sendiri sebelum lock.
5. **Pemeriksaan arsip terbaru.** Hasil run/log/metadata sudah diambil, tetapi
   verifikasi byte ZIP terbaru secara lokal belum selesai, sebagaimana di bawah.

## Arsip dan checkpoint

[Artifact10470692921](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35154446764/artifacts/10470692921)
tersedia pada run terakhir. GitHub melaporkan52,895,688 byte,292 file yang
diunggah, SHA256
`30a221e159298fae92304dc871457a74f7891c92590cc75d9e11bcfe975f0127`.

Workspace lokal sempat diganti setelah push. Checkout dipulihkan dari exact
SHA9173d2f, tree dan semua source pins kembali cocok. Transfer artifact ke
workspace pemulihan mendapat HTTP502/403. Karena itu SHA di paragraf sebelumnya
adalah digest yang dilaporkan GitHub; **CRC, jumlah entry ZIP, dan scan pola
credential artifact terbaru belum diverifikasi lokal**. Jangan menyalin klaim
scan artifact sebelumnya sebagai scan fresh artifact ini. AJ attempt4 sudah
diperiksa lokal sebelum workspace berganti:52,903,311 byte/292 entry, CRC,
path/duplicate/symlink dan selected-pattern scan tanpa kecocokan; SHA256
`3360c12672c65777579065f7bc07bc874c07372492c36ce9ee4a6e0efdad0b4d`.
Log run terakhir membuktikan12 rework PASS,20 maintenance PASS, pemulihan exact
dan cleanup; gap transfer tidak diubah menjadi kegagalan transaksi ERP.

Auditor berikutnya: verifikasi branch/head/tree dan aturan owner; ambil ZIP
terbaru, cocokkan digest dan periksa isinya; audit AJ tanpa menjadikan hasil
writer sebagai oracle; tutup kontrak tanggal, CSV dan cakupan role yang masih
terbuka. Uji family yang berubah beserta hubungan antarmodulnya secara
terkonsolidasi. Perubahan produk membatalkan kualifikasi reuse sebelumnya.
Jika ada bug material, pastikan satu writer sebelum membuat perbaikan.
Keluarkan CP6_LOCK_READY, CP6_HOLD, atau INCOMPLETE beserta batas bukti.

Main terakhir diperiksa tetap
`6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. PR, UAT, legacy dan hosted database
tidak diubah. Integrasi preview Cloudflare existing berjalan pada push
competition; auditor tidak menjalankan deployment manual. Tidak ada merge,
produksi, atau pekerjaan CP7.

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”

---

# Riwayat: audit independen -> AJ writer takeover


This top section supersedes the historical status sections below. `CP6_HOLD`.

AJ attempt4 `92d9c561c8bc8cbe4deeb55774f4a25216c93c01`, tree
`c98b4fd815924c15b9c592b32b60869b2cd0c081`, Native35153095661,
CodeQL35153095800 (all four SUCCESS), completes all20 maintenance schedules.
Both exact restores AJ->AI533/224 and AI->AH533/223, disposal,28 concurrency,
95 HTTP,43 original UI,51 additional checks,96 action/role pairs,4 clock cases,
and8 rollback-refusal controls pass. The218 qualified business observations are
REUSED_EVIDENCE from attempt3; they include12 unresolved dated-report reviews.
All12 fresh rework cases reach the source-QC refusal control, then are INCOMPLETE:
the fixture called private erp.reverse_qc directly and received42501. This does
not prove the business refusal. The next fixture uses ordinary OWNER through
public.erp_save_laundry_qc_action_v1(REVERSE_FINAL_SKU), expects the downstream-BS
business refusal, and compares the whole data boundary. Product code is unchanged.
Artifact10470336706:52,903,311 bytes/292 entries, SHA256
`3360c12672c65777579065f7bc07bc874c07372492c36ce9ee4a6e0efdad0b4d`.
Downloaded ZIP CRC, safe/unique/non-symlink entries and selected credential
patterns were checked; no pattern matches.

AJ attempt3 `f1f9e21a1be64ee523b408bcd77282748b3fa215`, tree
`9a66c776949ff1dfa5e7f69ae308100b7c11efed`, Native35151502439,
CodeQL35151502460 (allfour SUCCESS), now restores exact AJ->AI533/224 then
AI->AH533/223 with owner/ACL/full data boundary equality. Disposal passes.
Artifact10469682433:52,919,718 bytes, SHA256
`9549cec70eb6c63d276afc320d5d6f2ee020184052fdbf51486d9fdb5a026e26`,
CRC/entry validation/selected credential-pattern scan checked.
The same206 business controls pass,12 dated-report observations remain open;
12 new rework fixtures are INCOMPLETE because Python serialized timestamps
with a space instead of the facade's required ISO T separator. Maintenance20
reaches the final evidence-recording step but cannot find the migration in the
predecessor checkout; its assertions are not relabeled PASS after that failure.
28 concurrent schedules,95 HTTP,43 original UI and51 additional checks
(including HTTP role controls),96 action/role pairs,4 clock cases and8 refusal
controls still pass. Product SQL remains unchanged.

The next harness follow-up reruns12 rework cases and20 maintenance schedules.
The218 earlier business observations (206 successful controls+12 date reviews)
are eligible only for explicit REUSED_EVIDENCE after exact artifact SHA/CRC,
source head/tree, full runtime690, clean boundaries and byte-identical src/SQL/
package inputs are verified. Any product change requires the full fresh gate.
No prior INCOMPLETE rework result is reused. Concurrency/HTTP/UI/clock and exact
restoration continue fresh. ISO serialization and migration-path binding change
only the fixture/evidence adapter; existing business and maintenance assertions
remain intact.


AJ attempt2 tested `e3d15c8c3edfa0dce740c8ab63111365b58268cb`, tree
`854c81a3c2462e37ff84787a6a1fbbd98d9d5a89`, Native35150118894.
AJ installation/full690 binding PASS. Native230:167 PASS+39 CONTROL_PASS,
12 DATE_POLICY_REVIEW_REQUIRED,12 INCOMPLETE fixture reads,0 proven new bugs.
All13 raw-import/value-recovery controls pass. Original16+independent12
concurrency,95 HTTP,43 original UI,51 additional UI assertions,96 action/role
pairs,4 controlled-clock cases and8 rollback refusal controls pass. Rework3Good
then separate rewash3Good now totals6Good without the original unique-key error.
CodeQL35150118681 allfour SUCCESS. Artifact10469246358,52,745,022 bytes/167
entries, SHA256 `c7588357d63d36fbf6a94a980e7cf4860ba96987d730989f38eec75da011896d`,
CRC/entry validation and selected credential patterns checked.

Two harness corrections are pending rerun, with product SQL unchanged: observer
reads must run before switching to the ordinary OWNER mutation session; reviewed
AJ rollback bytes must be staged inside the executing checkout, as required by
the unchanged controller path and checksum checks. No role/table grants are
added. All20 maintenance cases and exact AJ->AI restoration were unfinished due
to that path refusal. Exact AI->AH restoration was consequently skipped; the
whole disposable database and Auth clone were removed. These are not PASS.

`production_go:false`; no CP7. One writer verified at remote
`a2d5a42c5fc2e99249aa73b47d74747bb7aa6dd6` before starting product repair.

R5 exact snapshot `a2d5a42c5fc2e99249aa73b47d74747bb7aa6dd6`, tree
`55a04fc2adfc53f6b96b62a975c3689940f1f49c`, backend AI-R2
`25fa4736329e5148dfdb3572bc169952cba23251`, Native 35145449818,
CodeQL 35145449707 (all four languages SUCCESS).
Artifact 10467267798: 5,958,072 bytes, 40 entries, SHA-256
`dea2228699da1a6174694adc7b3f54ec813fa4fdb41de01f3f92abc146e435cb`.
Downloaded bytes, CRC, entry paths/duplicates/symlinks and selected credential
patterns were checked; no pattern matches. Exact AH restore 533 functions/223
tables, Auth0/app0 and complete disposable removal passed.

**CP6-BS-REWORK-QC-LOT-01: qualified ordinary business failure.** Original real
UI sends10, receives10 and posts QC0 Good/10 BS. First contractor rework of5
returns3 Good/2 BS and posts FG3=21/WIP49, with report READY and exact replay.
A separate rewash order of5 accepts cumulative partial1+0 then1+1. Its legitimate
completion3+2 fails HTTP409/23505 on `uq_fg_lots_qc_item`. Both orders inherit
the original QC item's unique FG-lot identity. This is not a deliberately broken
function or a fixture selector failure. The UI wrongly classifies the conflict
as a request that was already processed. The failed response does not itself
prove a wrong-money commit; the material failure is that a valid recovery cannot
finish. R5 has50 completed new assertions,96/96 permission/action pairs and one
unfinished group. The two incoming writer fixes still pass their original43 UI
assertions and the independent receipt10/all-BS controls.

AJ is the writer repair, not independently accepted: new recovery lots use the
existing rework-order→BS→QC lineage without taking the original QC output's
unique slot. HPP and paid failed-wash cost readers follow that lineage. Original
QC uniqueness remains. The shared client message distinguishes data conflicts
from request-identity conflicts. Import validators persist per-row diagnostics
for malformed/nonfinite numbers and missing/invalid cost, report final counts,
and permit correction/revalidation of unposted input. No CSV interface is added.
Six existing function definitions change through a new migration and exact
pre-use rollback capsule; no old migration or posted transaction is rewritten.

The writer gate checks the whole533-function+157-relation runtime, original R5
artifact, inherited142 crossflow/23 work/16 invoice cases,24 calendar cases,
raw staging+recovery controls, original real HTTP/UI,96 granular action/role
pairs, partial rework/rewash and distinct-rate receipt cost lineage. Linked
reversal, failed paid washes, source uniqueness, HPP/WIP conservation, exact
restore and full disposal remain required. Historical460 is not represented as
fresh AJ evidence; changed HPP paths receive current-runtime regression.

Remaining holds:12 open-period historical observations need a qualified dated
report contract (R3's automatic BUG_PROVEN classification was withdrawn);
CSV producer/upload is absent and its CP6 deliverable scope is not explicit;
positive-money claim/compensation UI is not covered by zero-money role controls.
Changing product code makes the writer's own repaired result ineligible for
independent acceptance. Branch preview automation runs on competition pushes;
no manual deployment or hosted database access was performed by this auditor.

---

# Independent follow-up — R4 completed; UI continuation pending

R4 `e0d37dfd7a0d92d48f16ab9e126cc334a141f023`, tree
`0856f0a8af37eb35399cb6041bb8161aabe1129e`, Native 35143918467.
Fresh inherited groups: 142/16/23/12 native, 95 HTTP, 43 UI all complete.
New native: 16 PASS, 12 DATE_POLICY_REVIEW_REQUIRED, 2 GAP_PROVEN,
0 BUG_PROVEN, 0 INCOMPLETE. All 24 current invoice totals reconcile.
Four controlled-clock cases pass. All 96 action/permission-mask pairs complete:
48 missing-permission refusals, 16 owner-required refusals and 32 allowed actions.
New UI has 41 completed assertions; the rework group remains INCOMPLETE because
Playwright's exact wrapping-label lookup includes select option text. Bind the
visible caption and its select control for both party and FG-location fields.
No product source is changed. Partial observations now additionally compare
full HPP, reimbursement-entitlement and journal-line row fingerprints.

Exact AH restore (533 functions/223 tables), Auth0/app0 and disposal passed.
CodeQL 35143918796 succeeds in all four languages. Artifact 10466715497 is
5,601,747 bytes, 39 entries, CRC checked, SHA-256
`c100ebae28a9632a576afa818db95dd5922702b81e4186d1ecaf0644da87bd5b`.
The native and combined gates correctly remain failed while gaps are open.
`production_go:false`; CP7 is not started.

---

# Independent follow-up — consolidated observation pending

R3 harness `1efa64ac2ac2d006717520e156c121e96f6cf394`, tree
`7b19ad95637e87339fd319d5ac261dace303b72c`, Native 35142708437,
artifact 10466152140 (3,372,732 bytes; SHA-256
`478aa0b11f85b9398011dfe0a196e841852511204947565fec519219c6bbaeb7`).
All current invoice totals still reconcile, and all invalid staging variants
refuse preparation. The added historical observer found 12 open-period report
changes. **The artifact's automatic BUG_PROVEN label for those 12 is withdrawn:**
it assumed an open period was an immutable filed snapshot, which is not the
owner contract. The observations remain DATE_POLICY_REVIEW_REQUIRED, not PASS:
a dated invoice changes historical MATERIAL/AP/GRNI while recost/HPP events use
today; intermediate historical material value can be -5.25 or 7 with raw qty0.
No accounting-date policy is rewritten merely to satisfy that faulty oracle.
Closed receipt-date controls preserve the compared history. Import retains two
row-diagnostic gaps, with failed preparation and no money/stock effects.
Native UI rework hit Chromium datetime-local normalization at exactly zero
seconds; only the harness string format is corrected. Auth and clone cleanup
and exact restoration still passed. Product source remains unchanged.

R2 harness `f7ca546c561bbe0ad1685823f5b5096824e5ec25`, tree
`547bde2b288a098f76c5df4808e9a7d1815d088b`, ran in Native 35141866592.
All 24 calendar invoices and four raw-staging controls passed. NONNUMERIC_QTY
and MISSING_COST stop batch validation and leave the row PENDING without
persisted row errors: two GAP_PROVEN, zero business BUG_PROVEN, zero incomplete
native cases. Ledger was unchanged. CSV transport is still untested.
The four real controlled-clock cases passed on exact AI-R2. Real UI completed
48 missing-permission pairs, eight allowed create/hold controls and five legacy
BS UI lifecycle controls. Native UI rework stopped on a harness lookup using
POSTED instead of the source's actual SENT delivery status. That lookup and the
inherited delivery-count observer are corrected; assertions are retained.
Exact AH restore and complete Auth/clone/container cleanup passed. CodeQL
35141866598 succeeded in all four languages. Artifact 10466380365 was checked
at 3,371,084 bytes, SHA-256
`d3c2d677b4146475c775efeb2132d00ae87920903d801a0b5964fc46a1f36f1c`.
The next observation additionally checks the report before invoice receipt
and whether invalid staging is refused by prepare; no business code is patched.

R1 audit harness `f963ca28b6ab02e3db9c8a8e3b40aac9d7e94f31` ran in
Native 35140333202. The existing 142/16/23/12 groups and 43 UI assertions
completed. New tests exposed harness errors: the invoice report selected three
days instead of the complete invoice period; staging identifiers exceeded the
schema length; the clock helper imported from the wrong checkout; and an
unhandled browser response wait prevented Auth cleanup. Therefore new groups
and exact restoration were INCOMPLETE. Whole clone/container disposal passed.
No new business defect is established by R1. CodeQL 35140333204 succeeded.
Artifact 10464827882: 5,251,305 bytes, SHA-256
`ee5cd0ab91c47d67951ed16e124d6feb8695ffad3200a7a90691e215e2e43b4f`;
ZIP CRC and bytes were independently checked. The retry changes only harness
observation, identifiers, imports and promise handling; product code stays fixed.

Incoming report checkpoint: `555d8f29ea2d3f58dc2c7d10e7cd80099cdd3b49`, tree
`da665828227a0a4fd5d17452538edb98754738ad`. This wave changes audit tooling only;
all product and backend source remains identical to that checkpoint.

Incoming artifact 10463056747 was independently matched to its SHA-256,
5,243,788-byte size and 32-entry ZIP CRC. Native and four CodeQL jobs were read
from GitHub and are successful. These are verified incoming writer results,
not a new global acceptance.

New execution is planned on the exact AI-R2 engine: 24 calendar-delay invoice
scenarios, six raw PENDING staging validation scenarios, four controlled-clock
long/fresh transaction controls, and original browser rework/permission paths.
The inherited 142/16/23/12/95/43 assertions remain present. Historical 460 is not
rerun without invalidating drift. Each new independent group persists its own
failures and unfinished cases; none is PASS before execution.

Owner master `ERP_GARMENT_MASTER_CONTEXT_2026-09-15_AD.md` section21.1 requires
preview, row errors, totals, idempotency, manifest and recovery for imports.
No application CSV parser/upload was found. Testing raw normalized staging is
therefore explicitly separate from CSV transport. Three calendar months is a
required supported scenario; no 90-day rejection rule is invented.

One writer, competition branch only. Main confirmed at
`6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. No hosted target or CP7 work.
`production_go:false`. Current verdict remains **INCOMPLETE** pending this run
and disposition of any newly proven gaps.

---

# Final audit CP6 — CP6_HOLD setelah perbaikan UI

Bukti akhir: 16 September 2026 UTC / 17 September 2026 WIB.
**Writer PASS pada cakupan yang dijalankan; belum independent PASS.**
`production_go:false`. CP7 belum dimulai.

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”

Bagian ini merupakan status terbaru. Catatan proses di bawah dan laporan
`cp6-final-audit-checkpoint.md` mempertahankan keadaan pada checkpoint lamanya;
pernyataan lama “tidak ada bug baru” atau “UI belum dapat dijalankan” tidak boleh
dipakai sebagai status kandidat sekarang.

## Keputusan dan penghalang penutupan

**CP6_HOLD.** Dua bug material pada UI asli ditemukan melalui transaksi biasa,
diperbaiki, lalu gate gabungan selesai. Karena auditor ini mengambil giliran
penulis, aturan competition owner mewajibkan pemeriksaan chat independen lain
atas successor. Hasil sendiri tidak boleh diangkat menjadi independent PASS.

Kewajiban yang masih terbuka:

- Audit independen kedua perbaikan, seluruh pemanggilnya, serta serangan baru di
  luar daftar writer. Kandidat yang diserahkan dipin di tabel berikut.
- Bukti aplikasi untuk seluruh cabang BS/rework, penyelesaian rework parsial
  kumulatif, dan kombinasi izin yang belum dicakup 62 pasangan facade-role.
  Jalurnya ada; tidak diberi label N/A atau dipindahkan diam-diam ke CP7.
- CSV/import: tidak ditemukan parser/upload atau pemanggil staging-finalize di
  aplikasi. Tes native memulai dari staging yang sudah VALID. Kontrak opening/
  import owner mengikat preview, error per baris, total, idempotensi dan recovery;
  penugasan upload CSV sebagai deliverable CP6 belum tersurat. Scope ini perlu
  dipastikan dan jalur yang menjadi kewajiban harus dibuktikan.
- Batas keterlambatan invoice hingga tiga bulan belum teruji lengkap oleh 16
  kasus tambahan yang memakai keterlambatan beberapa hari. Empat zona sesi dan
  periode tertutup telah diuji; transaksi panjang yang benar-benar melintasi
  tengah malam WIB belum mendapat bukti baru. Tidak mengasumsikan 90 hari selalu
  sama dengan tiga bulan kalender.

Sales/invoice, payroll/Nota, HPP/Finance/report UI yang masih simulasi dipetakan
sesuai master owner 2026-09-15_AD bagian checkpoint: koneksi sisanya dan alur
owner lengkap adalah CP7. Ini tidak mengecualikan konsistensi backend lintas
modul, ledger, HPP dan laporan dari CP6. CP7 tetap tidak dikerjakan di sini.

## Identitas kandidat dan alat

Repo `Hanjay6688/-erp-garment-ux`; satu penulis; hanya branch
`competition/cp6-j-closure-20260911`, fast-forward. Main, PR24/25, hosted UAT,
legacy, production, merge dan deployment tidak dimutasi.

| Objek | SHA | Tree |
| --- | --- | --- |
| Backend bisnis AI-R2, tetap | `25fa4736329e5148dfdb3572bc169952cba23251` | `a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d` |
| Commit terakhir yang mengubah sumber produk UI | `d7a92f00b0779d614478778bd8f1ddd367122ff7` | `71b281da4455296c6f808ef28557bf4ad8f4daa4` |
| Snapshot akhir yang diuji + alat gate gabungan | `9a919060b1037fe0747515b6ed3b98aebb41b5b1` | `a0121c4f4c1ec6d2fd90852afd6c7d3b6c366859` |
| Checkpoint alat masuk dari owner | `2735703114ab52d605aa0d6cd2aa530b074fb5e9` | `16a7caef2949f50f10544c04616026e22647c6be` |
| Main, tetap | `6d4cda118f5d28d1f039cc0ecf318d0866f55c2c` | Tidak ditulis |

Parent snapshot gate adalah `5285a5f3e17b64ac4ae211c1ac5f6a39d57cd161`.
Sumber `src`, `supabase`, dan package sama persis antara commit produk d7a92f0
dan snapshot gate 9a91906. Tidak ada SQL/migrasi/rollback bisnis yang diubah.
31 berkas sumber alat/UI dipin SHA-256. Selain perbandingan sumber, gate
memverifikasi 690 objek runtime AI, izin asli, pemanggil public RPC, transaksi,
dan hasil ledger/laporan. Kesamaan byte sendiri bukan oracle perilaku.
Commit dokumentasi setelah gate hanya menyimpan laporan, bukan eksekusi ulang.

## CI, CodeQL dan paket bukti

- [Gate gabungan 35133830834](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830834): SUCCESS; job 104921105516.
- [CodeQL 35133830900](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830900): SUCCESS, Python, JavaScript/TypeScript, C/C++, Actions.
- [Artifact 10463056747](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830834/artifacts/10463056747): 5.243.788 byte, 32 entry.

SHA-256 ZIP:

```text
1deeeb830baa39c3c4d43d502fa3ba72a40a0aa5e7e45d4a97d5591188cd252b
```

ZIP diunduh ulang; SHA-256 dan CRC semua entry cocok. Pemindaian pola JWT,
token GitHub, private key dan secret key tidak menemukan kecocokan. Ini
pemindaian pola tertentu, bukan jaminan mutlak semua bentuk rahasia. Data uji
sintetis; tidak ada akun/bisnis nyata yang dipakai. CodeQL bukan oracle uang.

| Cakupan pada snapshot akhir | Rencana / selesai | Hasil dan batas |
| --- | --- | --- |
| Gabungan native warisan | 142 / 142 | PASS, termasuk kontrol detektor; bukan 142 alur bisnis baru |
| Invoice bertahap sesudah produksi/penjualan | 16 / 16 | Ekspektasi nominal mandiri; 0 bug, 0 incomplete |
| Kerja/upah, lineage, role, HPP native | 23 / 23 | PASS terbatas; bukan bukti transport UI |
| Jadwal dua sesi | 12 / 12 | Enam konflik kerja × commit/abort sesi pertama |
| Auth/JWT/HTTP asli | 95 / 95 | Lima facade, tujuh aksi, 62 pasangan facade-role; bukan semua kombinasi izin |
| UI asli desktop dan mobile | 43 / 43 | WRITER_PASS; 0 unfinished; layanan dan DB asli disposable |
| Unit | 230 / 230 | PASS; terpisah dari bukti browser nyata |
| Security/source, build, scan bundle | Semua selesai | PASS |
| Pemulihan AI → AH | 533 fungsi, 223 tabel | Definisi, owner/ACL, data, katalog dan marker cocok baseline |
| Cleanup | Selesai | Auth/sesi, antrean/konteks, clone, layanan dan container diperiksa |
| Matrix historis | 460 historis | REUSED_EVIDENCE; tidak dijalankan ulang sebagai matrix runtime akhir |

Native 142 berlangsung 18:23:47–18:24:54 UTC, seluruhnya tanggal bisnis
17 September WIB; tidak ada retry otomatis atau perubahan oracle tanggal.
Runtime: Supabase CLI 2.116.0, PostgreSQL 17.6.1.165, PostgREST 16.1,
Playwright 1.62.1, Chromium, dan smoke login agent-browser 0.38.0.

File utama dalam ZIP: `writer-ai/crossflow.json`, `final-audit/NEW_CROSSFLOW.json`,
`independent-ai/RESULT.json`, `independent-ai/CONCURRENCY.json`,
`final-audit/HTTP.json`, `final-audit/UI.json`, `independent-ai/EXACT_RESTORE.json`.
Semuanya di bawah `candidate/cp6-proof/`. Case ID dan observasi per tahap ada di
file tersebut; jumlah PASS tidak dijumlahkan menjadi klaim keselamatan global.

## Temuan dan cakupan perbaikan

| Temuan | Reproduksi biasa | Perbaikan dan pembuktian |
| --- | --- | --- |
| CP6-UI-QC-READY-BASIS-01 | Kirim 10, terima 8, QC 5 lalu 3. UI memakai sisa seluruh Potongan 5 dan mengirim PARTIAL_SELECTION; server benar meminta ALL_READY karena ready-for-QC habis. Penolakan atomic, FG 35/WIP 35 tetap. | Mode memakai qty siap QC yang terbukti terlihat lengkap. Filter receipt/size atau truncation tidak dianggap seluruh grup. Pemanggil, tes unit/DOM dan checker lama diperbaiki bersama. UI 5+3+2, filter parsial, Good/BS, dua role, ledger dan laporan diuji. |
| CP6-UI-RECEIPT-PROCESS-02 | POST_RECEIPT sah; workspace HTTP 200 berisi nama proses aktual. Parser asli menganggap nama proses sebagai metadata khusus attempt gagal sehingga halaman Laundry menampilkan kegagalan layanan. | Parser bersama menerima nama proses pada receipt fisik. Tiga metadata khusus attempt tetap dilarang di receipt fisik; attempt wajib lengkap. Unit, fixture browser dan UI nyata mencakup posted/reversal, RETRY_AT_VENDOR serta RETURN_UNPROCESSED. |

Bukti asli pertama: run 35129057885, artifact 10460209095,
SHA-256 `d06eebd9d9089c81b3f5d8f627fbfae5a5c8804331cda4d862b83d7947eb4088`.
Gate akhir memverifikasi ZIP/CRC, hash modul asli, penolakan dan keadaan atomic.
Bukti asli kedua: run 35131279236, artifact 10461242981,
SHA-256 `6106756a15a33287b77463e88c345c06547e96893df33a82808731719f9f10f6`;
ZIP/CRC dipastikan lokal. Parser saat bukti kedua masih byte-identik AI-R2.

Kontrol yang sengaja memutus respons dilakukan sesudah server commit nyata;
reload mengirim ulang UUID dan payload yang sama. Kontrol itu membuktikan
recovery transport, bukan bukti transaksi normal semula merusak data.

Aritmetika UI mandiri: 10 potong × 7 = 70. Desktop akhirnya FG 10/nilai 70,
WIP 0. Mobile menghasilkan Good 8 + BS 2: FG 56, WIP 14, accrual -70.
Retry-at-vendor 4 potong menambah biaya 28 tanpa Good/BS/FG palsu.
Full return 10 mempertahankan biaya 70 dan mengembalikan custody; kirim ulang
berdokumen baru menambah estimasi 70. Reversal biaya lama menyisakan 70 dan
tidak mengubah custody kirim baru. Laporan READY cocok pada setiap checkpoint.

Catatan UX nonmaterial yang terlihat: saat antrean QC sudah habis, pesan
“Master Final SKU atau lokasi FG belum lengkap” dan “cakupan antrean belum cukup”
bisa tampil bersama keberhasilan posting. Tidak terbukti ada master hilang atau
ledger salah; teks keadaan kosong perlu ditinjau dalam audit UI berikutnya.
Field diagnostik lama `posted_delivery` di UI.json menghitung literal status
POSTED, bukan jumlah pengiriman aktif. Pembuktian double submit memakai query
terpisah atas satu dokumen non-REVERSED dan waktu fisik; field lama tersebut
bukan oracle saldo atau cleanup.

## Peta antarmodul, reuse dan batas bukti

| Hubungan | Sumber/pemanggil yang dipetakan | Bukti final / klasifikasi | Sisa cakupan |
| --- | --- | --- | --- |
| Beli → penerimaan → GRNI → invoice → AP → bayar/retur | purchase headers/items, material movements, finalize invoice, supplier allocation/reversal | Native 142 + invoice 16, RECONCILED | Durasi tiga bulan, semua transport aplikasi/import |
| Roll → potong/size → pickup → kerja/upah → payroll | yields/distribution, work snapshots/completion, trigger lineage, jurnal | Native 23 + race 12 + invoice crossflow, RECONCILED | Accrual upah bukan pembayaran payroll; koneksi sisanya sesuai CP7 |
| Laundry → parsial → QC → Good/BS → FG | batch-size facts, public facade, parser bersama, QC allocation, FG lots, report, blockers | HTTP 95 + UI 43, RECONCILED pada successor | Semua cabang rework dan kombinasi role belum lengkap |
| FG → draft → posting → AR → bayar → retur/refund | draft reservations satu kali, sales post/allocation, reversal dan retur tertaut | Kelompok native DRAFT/CASH/RETURN pada 142, RECONCILED | UI Sales masih simulasi dan terjadwal CP7; native bukan bukti UI |
| Koreksi/backdate → WIP/FG/COGS → jurnal/laporan | recalc queue, revaluation events, HPP state/events, financial snapshot/checks | Invoice 16, native 142/23 dan laporan UI 43, RECONCILED | Seluruh batas tanggal dan transaksi panjang lintas tengah malam |
| Maintenance historis F..AB | controller/capsule/rollback dan manifest per target historis | 460, REUSED_EVIDENCE | Bukan pengujian baru runtime AI atau pengganti UI/import |
| PASS UI simulasi lama | payload mock berbeda dari payload receipt nyata | DRIFT; tidak diwariskan sebagai PASS aplikasi asli | Digantikan hanya pada 43 kasus yang benar-benar dijalankan |
| CSV dan role/rework yang belum dicakup | belum ada transport CSV; jalur rework nyata ada | RERUN_REQUIRED / kontrak scope CSV belum tegas | Tidak diberi PASS atau N/A |

Tidak perlu mengulang 460 hanya untuk angka: perbaikan ini tidak mengubah SQL,
trigger, izin backend, controller maintenance atau dependensi runtime historis.
Perubahan pembentukan payload/reader UI dibuktikan ulang dengan layanan asli;
backend gabungan dan race dijalankan lagi. Reuse 460 tetap dibatasi target dan
runtime historis, termasuk perubahan controller/capsule yang sudah dicatat pada
rekonsiliasi sebelumnya; tidak pernah berubah menjadi 460 PASS AI terbaru.

Rekonstruksi lama lengkap: `docs/evidence/cp6-final-audit-reconciliation.json`.
T146 CANCELLED meninggalkan 177/300 hasil PASS dan 123 belum selesai; T147
menyelesaikan 300 pada run lain. 460 = 23 target × 5 operasi × 4 jadwal.
Tidak ada manifest sah yang membuktikan “500-an kasus bisnis unik”. Kegagalan
finalizer/fixture/restore dan sesi alat terputus dibedakan dari transaksi ERP.
Penyebab internal penghentian chat/GPT tidak disimpulkan.

## Pemulihan dan serah-terima

Fixture native memberi schema USAGE sementara dan memulihkannya; bukti itu
bukan bukti izin aplikasi. HTTP/UI memakai ACL asli tanpa grant tambahan.
Fixture UUID historis dibuktikan ditolak parser asli, lalu seluruh clone lama
dibuang. ID sintetis diperbaiki sebelum penyemaian clone baru; SQL yang diterima
dan histori posted tidak diedit untuk meloloskan tes.

Restore AI→AH membandingkan 533 definisi fungsi beserta owner/ACL dan seluruh
223 tabel/data, katalog, marker. Marker AI 0, AH 1, capsule AI tidak tersisa,
690 objek terverifikasi sebelum drain, dan sesi setelah drain kosong.
HTTP: auth users/sessions/identities/refresh tokens, execution context,
jurnal tidak seimbang dan idempotency IN_PROGRESS semuanya 0. UI menutup
browser/proxy/preview, menghapus build disposable dan memastikan 0 auth users/
sessions. Dokumen posted tetap ada sampai clone utuh dibuang. Clone cp6_auth,
clone race, PostgREST dan container database dihapus; residue pemeriksaan 0.

Auditor berikutnya harus membaca bagian status terbaru ini, aturan audit
efisien, invariants, handoff AF–AI, dan rekonsiliasi historis; periksa remote head
sebelum bekerja. Verifikasi artifact akhir dan dua counterexample asli.
Cari masalah di luar temuan writer; prioritaskan sisa kewajiban di atas.
Perubahan bisnis berikutnya kembali berstatus Writer sampai audit independen.

```sh
git fetch origin competition/cp6-j-closure-20260911
git show 9a919060b1037fe0747515b6ed3b98aebb41b5b1:docs/evidence/cp6-disposable-ui-source-pins.json
gh run view 35133830834 --repo Hanjay6688/-erp-garment-ux
gh run download 35133830834 --repo Hanjay6688/-erp-garment-ux --name cp6-final-boundary-audit
```

Unduh ZIP melalui artifact API untuk mencocokkan digest ZIP; hasil ekstraksi
`gh run download` bukan ZIP dengan checksum yang sama. Lanjut hanya pada branch
competition, lingkungan disposable, tanpa CP7 atau production go.

---

# Catatan proses dan checkpoint terdahulu

# CP6 — original UI on a disposable target

Owner approved adding the dedicated disposable UI target after the final-audit
checkpoint reported the UI target-guard gap. This is a frontend writer successor,
not an independent acceptance of its own changes. CP7 is not implemented.
`production_go:false`.

Backend candidate remains AI-R2 `25fa4736329e5148dfdb3572bc169952cba23251`, tree
`a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d`. Starting competition head is
`9f884fbb27bdb92d6ee63f60333e007dc36f3f1c`, tree
`b4cf1e5d6c8aff531470af01dcdb4d146b4fca7f`. Source pins and the CI artifact identify
the separate frontend/harness candidate. No SQL migration or function changes.

The build mode `cp6-disposable-test` only accepts page origin
`http://127.0.0.1:4176`, API origin `http://127.0.0.1:54328`, and a local anon key.
Normal build/deploy rejects this runtime. Its output is a separate temporary
directory removed after testing. A transparent loopback proxy forwards Auth to
the local Auth service and RPCs to the disposable clone's original public API.
No business API responses are mocked. Schema permissions are not expanded.

Planned evidence: original login, anonymous/unmapped/inactive/viewer restrictions;
granular operator on desktop and owner on mobile; ten physical pieces at rate 7,
staged receipts of eight and two, QC postings of five, three and two, parent reversal
blocked by posted children, linked reversal back to zero balances, double submit,
and a paid failed-wash commit whose HTTP response is deliberately lost before
page reload and reconciliation with the original persisted UUID. The lost-response control tests transport
recovery; it is not evidence that an ordinary ERP transaction is inconsistent.
Each completed case is persisted before the next one. Unfinished cases stay
INCOMPLETE. Financial arithmetic is independent of the writer's PASS list.

Cleanup closes browser, preview and proxy; deletes temporary Auth users/sessions;
retains posted business history until the whole disposable clone is removed;
then runs the unchanged AI-to-AH restoration comparison and container cleanup.
Credentials, tokens, traces, browser storage, and database dumps are not artifacts.

Scope correction from the restored owner master context
`ERP_GARMENT_MASTER_CONTEXT_2026-09-15_AD.md` (Library version 1, lines 1960–2004):
CP6 is Laundry → QC → exact-size Final SKU/FG. Remaining Sales/invoice,
payroll/Nota, HPP/Finance/reporting connections and full dummy flow through journals
and reports are explicitly CP7 acceptance. The older blanket UI-gap statement
must be read with that contract. This does not remove CP6's backend accounting,
stock, HPP, correction or report-consistency obligations.

Opening/import rules in section 21 require preview, per-row errors, totals
reconciliation, idempotency, manifest and rollback/recovery. Import obligations
need separate source-to-path inventory; this document does not silently relabel
unproven import work as CP7 or N/A.

Run 35123732959 stopped during the source guard, before browser installation or
database startup: adding local output paths to the frozen predecessor `.gitignore`
was rejected. The predecessor file is restored byte-for-byte; the source guard is
unchanged. All 226 unit cases passed before that failure. No UI/business execution
is claimed for that run. Its cleanup-only artifact is 10457879554 (288 bytes),
GitHub-reported SHA-256 `c1abb38719dee9f087cf1a208ffd55620a978780b56c90964f52b0ceca72ebdc`.

Current execution status: CP6_HOLD — two original UI bugs proven; writer repair under test. The earlier native/HTTP audit and historical
460-case reconciliation remain in `docs/cp6-final-audit-checkpoint.md` and
`docs/evidence/cp6-final-audit-reconciliation.json`. No new PASS is claimed here.

Run 35124061446 completed the native combined 142, staged-invoice 16, work 23,
two-session 12 and Auth/HTTP 95 stages. UI stopped at unmapped-account login after
1/28 cases (anonymous login page). UI cleanup, clone disposal and AI→AH restoration
completed. The test proxy omitted Auth's `X-Supabase-Api-Version` CORS header;
this is a harness transport defect, not a qualified ERP posting bug. The header
is now passed through, browser transport failures are recorded without payloads,
and label selectors use the original accessible names. CodeQL run 35124061384
succeeded. Artifact 10459275971 is 2541090 bytes; GitHub-reported SHA-256:
`539e204978506b71c9f5c4bf31132aa80895ddb0d1a22f33147d51601789a7c0`.
The final runner expands the receipt chain to 8+2 and QC to 5+3+2 (36 planned
cases), including browser reload after the deliberately lost response.

Import inventory: `scripts/cp6_ac_independent_audit.py` inserts synthetic
`migration_staging_rows` already marked VALID, then calls
`erp.prepare_migration_opening_balance`, `erp.post_opening_balance`, and
`erp.finalize_migration_batch`. The combined native family retains direct/import
opening cases. No CSV parser, file input, or staging/finalize browser caller was
found in `src` at this candidate. This is a missing executable application path;
native staging evidence does not close CSV transport. Section 21 of the owner
master binds these rules to opening/import and cutover, without assigning a
separate CSV-upload deliverable explicitly to CP6. Preserve that scope question;
do not infer N/A or implement a new import product during this audit.

Run 35125003066 / candidate a4d45ef4742d2b8b14a92c631a6dd0db84b3accb:
the Auth version-header correction alone did not close browser transport. UI
remained 1/36, with `/auth/v1/token` reporting `net::ERR_FAILED`. The proxy also
combined lowercase upstream CORS headers with mixed-case local headers, leaving
duplicate origin values. It now replaces headers consistently and checks the
real Auth health response and preflight before opening the browser. This still
requires a successful browser rerun; it is not an ERP transaction finding.

The same run crossed Jakarta midnight (combined native stage 16:59:15–17:00:34
UTC). It completed 119 PASS and 23 FAIL: 16 explicit
`AA_INVOICE_DAY_CHANGED_REQUIRES_SEPARATE_MIDNIGHT_CASE`, three cash reversal-date
expectations, and four previously-future payment dates that became today's date.
The latter seven expectations use the phase-start date. These are unresolved
rerun/clock-context evidence, not 23 proven business defects. The frozen oracle
is unchanged. Subsequent runs record the real business date before/after and
preserve the original exit code; there is no automatic retry or changed oracle.
The 16 additional invoice cases, 23 work cases, 12 schedules, HTTP 95, exact
AI→AH restoration and cleanup completed. Artifact 10458598039: 2529732 bytes,
SHA-256 `ed3c7e15d5ef8c34167ddf3e621409e326f3baccd409d63dfa8937747693ace5`.
The downloaded bytes and ZIP CRC matched. CodeQL 35125002987 passed four languages.

Run 35126188260 / candidate 0efabcfb8ee717604c32b07f760237416ec498af:
native 142/16/23 and 12 schedules completed; the combined stage stayed on the
same Jakarta business day. HTTP 95 passed. Real browser Auth passed anonymous,
unmapped and inactive cases (3/36). Viewer workspace did not render its form.
The inherited foundation fixture uses non-RFC UUIDs, rejected by the original
frontend parser; the next run records a direct parser qualification before
disposing the complete HTTP clone and seeding a fresh UI clone with canonical
synthetic IDs. This changes fixture IDs before insertion, not posted history,
product parsing, schema permissions, or admitted SQL. Artifact 10459407523,
2541900 bytes, SHA-256
`1a41825ad876c78412fc60ecdddcf9c95399697d30b49528db436a3e9f5d3e99`;
downloaded checksum, ZIP CRC and token/private-key scan passed. CodeQL
35126188318, exact AH restoration and cleanup passed.

Commits explicitly marked `[cp6-ui-focused]` run a focused HTTP/UI diagnostic
gate while the browser harness is being corrected. RUN_SCOPE.json records the
native 142/16/23/12 groups as NOT_RUN_FOCUSED, never PASS. A final unmarked
commit or workflow dispatch must run the entire combined gate after stability.

Focused run 35127566063 stopped before the fixture qualification/browser cases:
the installed TypeScript 7 package does not expose the older transpileModule
API. HTTP 95, restoration and cleanup completed. The diagnostic loader now
uses Node's built-in type stripping, verified locally against the original
parser. Artifact 10460456192 (313170 bytes), GitHub-reported SHA-256
`f4d5daef6b9126c24ad8b2581c5315e6ab4f86940fabc8ee467e2cb7d931426a`.
Native 142/16/23/12 were intentionally NOT_RUN_FOCUSED; no browser PASS.

Focused run 35128108373 on 6d7312100eb6ff7ac0b6ecb68850a9355edf38a1 confirmed
the inherited fixture's UUID rejection with the original parser. The fresh
qualified clone reached 8/36 UI cases: all four access cases, inert form,
one dispatch despite double submit, receipt of eight, and QC of five.
The next ordinary QC of three received a non-200 response. Its exact rejection
and before/after ledger state are being captured before assigning a product
verdict. Artifact 10459529337 (2490968 bytes), GitHub-reported SHA-256
`60433679cf8561f4ba6c9409953ea88db664db195f49f3c4023b55d4b3e787a8`.
HTTP 95 and restore/cleanup completed; native groups stayed NOT_RUN_FOCUSED.

The local executor disconnected with environment_offline after this run.
Source is checkpointed in Git; GitHub/CI remains available for bounded
diagnostics. No internal cause of the disconnection is inferred. The next
diagnostic changes only harness logging, a READY precondition, and evidence;
the business UI and backend remain the same for reproducing the rejection.

## Temuan baru: CP6-UI-QC-READY-BASIS-01

Status: BUG_PROVEN pada UI asli; perbaikan writer sedang diuji. CP6_HOLD.
Run [35129057885](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35129057885)
pada harness `68db9a5387cb993921476433a964b68fa6d08521`, tree
`e16e6e89e334e9da440d624b4957b4dee1513865`, menyelesaikan 8/36 kasus
UI. POST_FINAL_SKU kedua mengirim Good 3, mode PARTIAL_SELECTION,
expected version 5. Server mengembalikan HTTP 400/P0001 karena sisa
barang siap QC setelah posting adalah 0. Dua potong yang masih di Laundry
membuat sisa seluruh Potongan 5; itulah angka keliru yang dipakai UI.

Ini transaksi biasa pada backend AI-R2, bukan injeksi data rusak. Hash SHA-256
modul QC asli: `7d5ed652ce85d287ee5954800e16c2756633f5df37612e831dac978fb485897c`.
Sebelum dan sesudah penolakan: FG 5 pcs/nilai 35, WIP 35, accrual -70,
satu QC, satu pergerakan FG, empat baris jurnal, nol jurnal tidak seimbang,
nol execution context. Server gagal secara atomic; bug menghalangi alur UI
yang sah, tanpa bukti perubahan parsial.

Artifact 10460209095, 2491309 byte, GitHub-reported SHA-256:
`d06eebd9d9089c81b3f5d8f627fbfae5a5c8804331cda4d862b83d7947eb4088`.
Respons penolakan dan state sebelum/sesudah juga dicatat dalam log job
104905208286 dan UI.json. HTTP 95, restore AH dan cleanup selesai.
Pengunduhan ulang/CRC artifact ini masih belum dilakukan karena executor
lokal terputus; digest di atas berasal dari metadata GitHub.

Keluarga perbaikan:
- Producer: Good receipt per batch/ukuran; consumer: formulir QC dan deklarasi
  completion_mode. Sisa seluruh Potongan tetap ditampilkan sebagai informasi,
  tetapi tidak menjadi jumlah barang siap QC.
- Seluruh Good/BS yang dipilih memakai satu mode berdasarkan jumlah siap QC.
  Jika masih ada barang siap yang terlihat tetapi tidak dipilih, mode partial
  dapat dibuktikan walau daftar belum lengkap.
- Memilih seluruh jumlah terlihat hanya menjadi ALL_READY jika antrean tidak
  terpotong dan pencarian kosong atau cocok dengan metadata bersama PO,
  Potongan, atau Model. Filter receipt/vendor/ukuran, wildcard/escape dan
  kolasi yang tidak dapat dibuktikan tidak dianggap sebagai seluruh sumber.
- Server, facade, izin, trigger, perhitungan HPP/laporan dan rollback tidak
  dilonggarkan. Penolakan server terhadap deklarasi yang salah tetap berlaku.
  CP5 rework mempunyai aturan hasil kumulatif per order yang berbeda;
  halaman QC simulasi bukan pemanggil facade ini.
- Tes lama yang menyamakan remaining Potongan dengan ready QC diganti dengan
  angka fisik 10 keluar → 8 kembali → 5+3 QC, disusul 2 kembali/QC.
  Kasus UI diperluas menjadi 38 dengan kontrol filter receipt versus PO.
  Guard scope dan source pins mencakup modul serta tes yang berubah.

Tidak ada SQL yang diterima diubah. Successor ini tetap hasil writer sampai
diperiksa chat independen. Gate penuh wajib menyusul setelah keluarga stabil.

Run 35130093753 pada writer c59b18117f7a0377826bcaa00cbaeb4d6040f48b
menyelesaikan 228/228 unit test. Pemeriksa statis N03/N04 kemudian menolak
karena masih mewajibkan ekspresi `selectedQty === authoritativeRemainingQty`
yang terbukti menghalangi finalisasi 3 pcs. Browser/database belum dijalankan.
Artifact cleanup-only 10461121371, 288 byte, GitHub-reported SHA-256
`5ece36f491eaf64ffefa89c54f6e44a8c6037d077d7e973846341381578e4e1c`.

Inventaris 27 pemeriksa CP6 menemukan tuntutan lama tersebut hanya di
scripts/check-cp6-deep-business-repair.mjs. Bagian N03/N04 kini mewajibkan
basis ready, bukti cakupan antrean, penguncian saat cakupan tidak cukup,
dan tiga kelompok regresi; ekspresi lama ditolak eksplisit. Seluruh bagian
lain, termasuk immutable migration, role, financial/report checks dan rollback,
tetap identik. Source pins/guard turut mencakup perubahan pemeriksa ini.

Run 35130416443 pada 80e5729e095418d1a0c0c6c66c9649f14400eea4
melewati unit/security/build dan menyelesaikan 10/38 kasus UI. Finalisasi 3
yang sebelumnya ditolak kini berhasil; FG menjadi 8 pcs/nilai 56, WIP 14.
Kontrol filter receipt menahan posting tanpa perubahan ledger. Saat kembali
ke Laundry, halaman menampilkan kegagalan workspace. Akar masalah kedua
belum dikualifikasi: pesan UI bersifat umum. Diagnostik berikut membaca
respons asli dengan parser produk asli, merekam error transport/parser dan
hash payload sintetis; tidak mengganti respons bisnis.

Artifact 10460842458, 2491014 byte, GitHub-reported SHA-256
`6606c380fa3132df700462de220629107d07c950d0c516902d5c6c8378f38747`.
HTTP 95, restore dan cleanup selesai. Kelanjutan UI tetap INCOMPLETE.
Counterexample pertama kini juga diverifikasi ulang di CI dari ZIP asli,
termasuk checksum/CRC, pin modul pada AI-R2 dan kesamaan state sebelum/sesudah;
gangguan executor lokal tidak menjadi alasan mengabaikan bukti masuk.

## Temuan baru: CP6-UI-RECEIPT-PROCESS-02

Run 35131279236 pada `17d4bee4bb8c4efede8d2b35cda2cb46117d4610`
(tree `3d7c3ac49253b1b40a95b1cd6aa2b56858b7f47b`) membuktikan masalah
kedua dari transaksi penerimaan biasa, tanpa injeksi data tidak konsisten.
Workspace Laundry HTTP 200 mengembalikan PHYSICAL_RECEIPT, process_name
`CP6 Race Wash`, serta failed_wash_attempt_id/custody_outcome/attempted_qty_pcs
semuanya null. Parser produk asli menolak nama proses yang sah sebagai
metadata attempt gagal. Halaman lalu menampilkan pesan layanan tidak terhubung.
Produser SQL memang mengambil nama dari actual_wash_process_id untuk penerimaan
biasa maupun attempt gagal. Konsumen bersama adalah parseReceiptSummary melalui
parseLaundryQcWorkspace, termasuk pembacaan ulang dan riwayat reversal.

Perbaikan menerima nama proses aktual pada penerimaan fisik, tetap menolak tiga
metadata khusus attempt di penerimaan fisik, dan tetap mewajibkan metadata lengkap
untuk kedua custody attempt gagal. Model, unit test dan fixture browser lama
(disertai proses aktual) diperbaiki bersama; tidak ada perubahan SQL/ACL/trigger.
Tes unit mencakup receipt POSTED/REVERSED, proses null/nama sah, dua custody,
metadata tercampur, metadata hilang, dan tipe proses salah. Bukti UI asli berikutnya
juga menguji Good + BS pada owner mobile: Good saja masuk FG, biaya BS tertinggal
di WIP sampai resolusinya. Ini bukan klaim bahwa rewash/rework telah teruji.

Run tersebut menyelesaikan HTTP 95 dan 10/38 UI; native 142/16/23/12 NOT_RUN_FOCUSED.
QC bertahap 5+3 sudah lolos dengan FG 56/WIP 14, tetapi penerimaan kedua belum
bisa dibuka. Restore 533 fungsi/223 tabel persis AH dan cleanup PASS.
Artifact 10461242981, 2493952 bytes, SHA-256
`6106756a15a33287b77463e88c345c06547e96893df33a82808731719f9f10f6`.
Executor pulih; ZIP diunduh, checksum/CRC dan pemindaian pola JWT lulus.
CI juga memverifikasi ZIP counterexample QC asli 10460209095 beserta hash sumber,
penolakan backend, dan keadaan ledger sebelum/sesudah yang identik.

Kedua perbaikan adalah pekerjaan writer. Belum independent PASS, belum CP6 lock.

Run 35132647407, kandidat frontend `d7a92f00b0779d614478778bd8f1ddd367122ff7`,
tree `71b281da4455296c6f808ef28557bf4ad8f4daa4`: seluruh siklus operator desktop
melewati penerimaan 8+2, QC 5+3+2, laporan, blocker dan reversal kembali ke nol.
Parser penerimaan fisik sudah bekerja pada respons asli. Fase mobile berikutnya
memakai kembali waktu kemarin sesudah reversal fisik barusan; backend benar
menolak pengiriman sebelum barang kembali. Ini kesalahan kronologi fixture,
bukan bug ERP. Ledger sebelum/sesudah penolakan identik, FG/WIP/accrual nol,
ready 10. Tes tetap INCOMPLETE; kasus yang belum dijalankan bukan PASS.
Artifact 10461899223 (2790813 bytes), digest GitHub
`e84ecb3806d7432fd5021889d2f0a154a81c82f651eb645fcb02d2f24932b8bb`.
HTTP 95, restore AH dan cleanup selesai; native tetap NOT_RUN_FOCUSED.

Penerus harness mempertahankan alur pertama dengan backdate dan zona browser
Honolulu. Siklus setelah reversal memakai waktu fisik WIB yang diambil sesudah
koreksi, dengan jeda satu detik karena input produk menerima ketelitian detik.
Tidak ada backdate buatan yang melewati ketersediaan fisik. Tambahan lima kasus
UI menguji RETURN_UNPROCESSED sepuluh potong, biaya 70, pengiriman baru berbiaya
estimasi 70, reversal biaya lama tanpa menghapus custody, dan reversal pengiriman
baru. Total rencana sekarang 43; angka hasil baru menunggu eksekusi.

## Gate fokus selesai; gate gabungan diwajibkan

Run 35133185235 SUCCESS pada `5285a5f3e17b64ac4ae211c1ac5f6a39d57cd161`,
tree `8742b35e9bfc4cdd7987d93461b091bcb3e56a1d`: UI **WRITER_PASS 43/43**,
HTTP 95/95, unit 230, restore 533 fungsi/223 tabel persis AH, cleanup PASS.
Desktop menghasilkan FG 10/nilai 70; mobile dengan 2 BS menghasilkan FG 8/nilai
56 dan WIP 14. Semua koreksi tertaut mengembalikan saldo nol dan ready 10.
Retry-at-vendor empat potong menambah biaya 28, tanpa barang Good/BS/FG baru;
reload setelah respons hilang memakai UUID lama. Return-unprocessed sepuluh
potong memulihkan custody, mempertahankan biaya 70; pengiriman baru menambah
estimasi 70. Reversal biaya lama tidak menghapus perpindahan fisik atau dokumen
kirim baru. Native 142/16/23/12 tidak dijalankan pada run fokus ini.

Artifact 10462935592, 3016663 bytes, digest GitHub
`3a3393c859e2ef7eed5132f3c7c78d0a342a526c1a787b46c16e2344ccef7c8b`.
Gate gabungan berikutnya wajib dijalankan tanpa marker fokus. Sumber produk
frontend tetap sama dengan `d7a92f00b0779d614478778bd8f1ddd367122ff7`;
harness membedakan parser asli AI untuk diagnosis fixture historis dari parser
successor yang dipakai aplikasi saat ini. Perubahan metadata ini bukan perubahan
oracle atau aturan penerimaan. Hasil gabungan masih menunggu eksekusi.
