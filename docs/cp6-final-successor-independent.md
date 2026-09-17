# Audit independen successor CP6 — CP6_HOLD

Audit selesai pada cakupan di bawah. Satu writer alat audit; kode bisnis tidak
diubah. `production_go:false`; CP7 belum dimulai. **CP6 belum layak dikunci.**

## Keputusan yang dapat dipakai

Perbaikan nominal klaim/kompensasi dan hubungan recovery ke penjualan, HPP,
invoice final serta reversal lolos pemeriksaan independen pada cakupan teruji.
AJ belum mendapat penerimaan global: ditemukan gap baru pada diagnostik import,
dan masalah tanggal laporan masih menahan penutupan. CSV/upload tetap belum
teruji dan penempatan kewajiban checkpoint-nya belum jelas.

Alat audit yang benar-benar dieksekusi:
`2a6161ea77074725b4b928f4b7135ba3e0749f45`, tree
`5b6fbd2330f518deb47ff9ab4b0df3a45878fa62`, parent checkpoint masuk1ee47b02.
Commit penutup sesudahnya hanya memperbarui dokumen ini; bukan runtime baru.

[Native35176804544](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35176804544)
selesai FAILURE karena dua grup berstatus HOLD; semua kasus tambahan selesai,
restore dan cleanup PASS. Gate tidak dilonggarkan.
[CodeQL35176804622](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35176804622)
empat bahasa SUCCESS. Keempat ZIP/manifest/SARIF telah diunduh dan diverifikasi:
exact SHA/tree, security-extended, executionSuccessful=true,0 hasil temuan.

Artifact native
[10478726559](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35176804544/artifacts/10478726559):
53.568.149 byte,295 entry. SHA256 byte unduhan lokal:
`e7c3927764be559a5af61af984f5b7e3937f6424d16442d0b3e046a1a55ef223`.
CRC valid, nama entry unik, path aman, tanpa symlink. Scan seluruh entry untuk
pola GitHub token/JWT/private key/sb_secret:0 kecocokan. Ini pemeriksaan pola
terpilih, bukan jaminan semua kemungkinan credential telah terdeteksi.

## Temuan dan batas penerimaan

**CP6-IMPORT-REFERENCE-PREVIEW-01 — GAP_PROVEN, P3 diagnostik.** Case
`MIXED_IMPORT:UNKNOWN_LOCATION` memakai dua baris input biasa dalam batch DRAFT.
Baris2 menunjuk kode gudang yang tidak ada. `validate_migration_batch` memberi
total2/valid2/error0 dan kedua baris VALID tanpa error. Prepare kemudian gagal
P0001: `Opening row 2: unknown location_code ...`. Ledger tetap utuh. Setelah
kode gudang pada draft dikoreksi, preview, replay prepare, posting20 unit senilai25
dan finalisasi lulus. Tidak ada perubahan fungsi/data posted untuk membuat kasus.

Ruang keluarga: validator opening memeriksa kehadiran sebagian kode, sementara
prepare menyelesaikan material/model/contractor/customer/location/supplier/vendor/
cash account dan menolak referensi tidak dikenal. Identitas produk FG sudah
memiliki resolver validasi; MATERIAL_ROLL juga sudah memeriksa gudang serta
sebagian referensi staged. Keberhasilan jalur tersebut tidak menutup gap opening
MATERIAL. Gudang tidak dikenal terbukti native; referensi lain dalam keluarga
ini masih perlu kontrol terarah sebelum perbaikan dianggap lengkap. Belum ada
bukti salah posting atau kerusakan saldo. Temuan ini tidak memakai transport CSV.

**Tanggal laporan — HOLD dipertegas pada tanggal yang sama.** Dua kontrol baru
`HISTORICAL_READY:UTC` dan `HISTORICAL_READY:Pacific/Kiritimati` membaca laporan
as-of2026-09-15 sesudah invoice bertahap untuk10 unit yang sudah diproses:
3×8.25 +7×11.75 =107, dibanding estimate100. Persediaan bahan fisik sudah0.
Laporan historis masih MATERIAL_INVENTORY7, FG51, COGS34; confidence pada
laporan historis itu sendiri READY, critical0, pending0. Pada tahap pertama,
nilai bahan historis -5.25. Total hari proses dan recalc queue sudah cocok.

Sumbernya berurutan: posting invoice/cost correction menggunakan invoice_date;
`refresh_material_purchase_item_cost` mengalirkan recost material ke
`sync_material_cost_revaluation` pada hari proses; queue PO kemudian memanggil
`sync_po_hpp_to_gl` pada hari proses. Snapshot mengambil saldo menurut as-of,
tetapi pemeriksaan integritas utamanya memakai keadaan terkini. Ini belum
diterima sebagai laporan historis yang dapat dikunci. Dua observasi baru bukan
dua belas kasus lama yang diuji ulang seluruhnya. Pilihan kebijakan periode
terbuka tetap perlu dikualifikasi untuk seluruh keluarga, termasuk reversal,
konversi, queue tertunda, serta batas closed period; jangan hanya menambal UI.

**Nominal dan recovery — independent PASS terbatas.** Review kedua input React,
34 parser controls,237 unit/DOM, dan pengulangan layanan asli menegaskan14,25
tersimpan14.25. Bukti UI mencocokkan settlement14.25, AP70→55.75, pemakaian
kompensasi tanpa kredit AP kedua, refusal kapasitas/turunan, dan linked reversal.
Counterexample sebelum perbaikan tetap berkelas DOM dengan transport mock;
tidak dipromosikan menjadi bukti salah nominal pernah terposting pada database.

Empat skenario residual baru melanjutkan dua recovery sampai satu unit terjual,
invoice material final12.75, recost, reversal invoice, reversal sale dan reversal
recovery. FG on hand/COGS masing-masing19.75 setelah recost tanpa failed wash;
dengan paid failed wash masing-masing26.75. Sisa8 unit WIP masing-masing158 atau214.
Reversal invoice mengembalikan estimate; source recovery ditolak selama sale aktif.
Draft sale mengurangi availability sekali, posting tidak mengurangi kedua kali.
Seluruhnya PASS dengan oracle angka tersendiri. Ini native dengan fixture grant,
bukan bukti UI invoice/sales sudah tersambung.

## Cakupan eksekusi dan reuse

| Kelompok | Rencana/selesai | Hasil dan klasifikasi |
| --- | --- | --- |
| Residual independen baru |9/9|6 PASS,1 GAP_PROVEN,2 DATE_POLICY_REVIEW_REQUIRED,0 incomplete; fresh pada2a6161ea |
| Nominal parser |34/34|PASS; parser saja, bukan34 transaksi ERP |
| Unit/DOM |237/237|PASS lokal dan CI; pemeriksaan source/access/backend/build PASS |
| Recovery AJ |12/12|Fresh PASS; product runtime AJ tetap exact |
| Business lama selain recovery |218/218 record|REUSED_EVIDENCE dari47671d9:206 sukses +12 HOLD tanggal; bukan218 fresh PASS |
| Matrix230 sumber reuse |230/230|RECONCILED:179 PASS +39 CONTROL_PASS +12 HOLD pada47671d9; SHA/CRC/case ID/runtime690 cocok |
| UI asli |43/43|Fresh PASS; penulis dua fix UI terdahulu adalah chat auditor ini, penerimaan independennya mengacu audit successor sebelumnya |
| Kontrol UI tambahan |58/58|Fresh PASS; pemakaian source writer sebagai harness dinyatakan, disertai review oracle dan kontrol residual tersendiri |
| HTTP |95/95 assertion;62 record facade-role|Fresh PASS; layanan Auth/PostgREST asli, tanpa perubahan schema ACL |
| Role BS/claim |96+32 pasangan|Fresh PASS;32 khusus nominal positif; bukan semua role di semua modul ERP |
| Dua sesi |16+12 jadwal|Fresh PASS; seluruh clone dihapus |
| Maintenance AJ |20/20|Fresh PASS; assertion asli dipertahankan |
| Batas hari |4/4|Fresh controlled-clock PASS; clock hanya pada clone,0 incomplete |
| Penolakan rollback |8/8|Fresh PASS |
| Restore |AJ→AI533 fungsi/224 tabel; AI→AH533/223|Full data/catalog/owner/ACL/marker exact |
| Matrix historis460 |460 historis|REUSED_EVIDENCE historis; bukan fresh AJ atau460 alur bisnis |
| SQL AI sebelum AJ |6 fungsi berubah|DRIFT untuk dependensi recovery/HPP/import; bukti terdampak diganti gate AJ dan residual baru |
| Parser/upload CSV |0 eksekusi|RERUN_REQUIRED setelah jalur tersedia dan kontrak checkpoint dipastikan; belum PASS/N/A |

Tidak ada alasan menghitung ulang460 maintenance historis sebagai pengganti
tes bisnis. Perubahan6 fungsi AJ sudah memiliki230 source-bound,12 recovery,
28 concurrency,20 maintenance,4 clock serta4 hubungan downstream baru pada
produk final. Gap tanggal/import tetap menahan lock meskipun grup lain lulus.

## Hubungan antarmodul yang ditelusuri

| Hubungan | Producer, consumer dan kontrol | Bukti / batas |
| --- | --- | --- |
| Pembelian→receipt→GRNI→invoice→AP→bayar/retur | purchase items/movements, final invoice, supplier cent events, source allocation, immutable child guard |142 crossflow +16 invoice +24 calendar dalam reuse230; tanggal historis HOLD |
| Roll→cutting→pickup→kerja/upah→payroll | cutting batch/group, rate snapshot, work posting trigger, sewing terminal, entitlement |23 work dalam reuse;28 jadwal fresh; UI payroll belum menjadi bukti CP6 |
| Laundry→partial receipt→QC→GOOD/BS→recovery→FG | facade publik, receipt batch-size, failed-wash facts, recovery lot terpisah, source QC fallback |43+58 UI,12 recovery dan4 downstream baru; no double physical count pada alur teruji |
| FG→draft sale→posting→AR→bayar/return/refund | reservation ledger, sale posting guard, stock allocations, linked correction |142 crossflow reused +4 recovery/sale fresh; UI sales masih scope sambungan CP7 |
| Koreksi/backdate→recalc→WIP/FG/COGS→jurnal→laporan | material recost, PO queue, HPP versions/events, owner financial snapshot |current amounts/queue/reversal PASS teruji; READY historis masih HOLD |

AJ mempertahankan constraint unik QC asli dan memakai recovery lot tersendiri.
Consumer HPP/failed-wash membaca source QC melalui rework_order→BS; work/attendance
tetap mengikuti cutting group/physical output, sales membaca lot dan versi HPP.
Reverse source QC tetap memeriksa downstream BS; reverse recovery memeriksa
downstream FG/payroll. Byte identik saja tidak dijadikan oracle perilaku.

## Pemulihan, keamanan dan kelanjutan

Boundary setiap9 kasus kembali persis. Temporary schema USAGE native dipulihkan;
function catalog tidak berubah. Maintenance menutup admission, drain sessions0,
memulihkan fungsi/owner/ACL exact, menghapus marker/capsule target dan mempertahankan
marker predecessor. Auth users/sessions/identities/refresh tokens0, app users0,
execution context0, unbalanced journals0, in-progress idempotency0. Auth DB clone,
PostgREST, controlled-clock dan container DB disposable dihapus. Browser/proxy/
preview ditutup. Histori posted dipertahankan sampai seluruh clone dibuang.

Main tetap `6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. Hanya branch competition
ditulis fast-forward. Main/PR24/25/hosted UAT/legacy/production tidak dimutasi;
tidak ada merge atau deployment manual. Data uji sintetis.

Penutupan berikutnya harus menyelesaikan keluarga diagnostik referensi import,
menetapkan kontrak tanggal buku/restatement periode terbuka dan membuktikan seluruh
recost/jurnal/laporan konsisten, serta menetapkan kewajiban CSV berdasarkan kontrak
owner. Belum ada bug nominal/stock/journal baru yang terbukti pada9 kasus; gap
diagnostik dan tanggal tidak diturunkan menjadi PASS. Tidak ada alasan memberi
production go atau memulai implementasi CP7.

Untuk melanjutkan: periksa ulang remote branch dan diff checkpoint; unduh artifact
di atas, cek SHA256/CRC, buka `final-audit/FINAL_INDEPENDENT.json`,
`writer-aj/BUSINESS.json`, `final-audit/INDEPENDENT_GATE.json` dan bukti cleanup.
Workflow `cp6-final-boundary-audit.yml` memasang runtime disposable dari source
pinned; kedua script `cp6_final_independent_acceptance.py` dan
`cp6_final_money_independent.mjs` sudah tersambung. Jangan menjalankan script
native terhadap endpoint selain disposable yang diizinkan.

---

## Rekam persiapan dan bukti masuk

Checkpoint masuk `1ee47b02192a6fb1ccf85c1c12bd5a68a12d4542`, tree
`9a520ab5fe2e0fe87375268c1d437912d73455b7`, parent
`2c9465994b3827bc3db82af52753dc5eb80df141`. Snapshot runtime writer tersebut
ber-tree `3fe4f342ea41c987c4a693339d5590db3b486f2a`.
Produk terakhir berubah pada `47671d9ba2cfb8d02658388adb364b2ae6b89e8d`, tree
`46f4f605444c72dc32282025b859ab66375178b3`; frontend nominal dan backend AJ.
SHA alat audit dibedakan dari SHA produk ini. Byte produk src/SQL/package tetap
sama; pemeriksaan runtime memverifikasi 533 fungsi dan 157 objek relasi.

## Rekonsiliasi masuk

- Native35174491617: FAILURE. Business mewarisi12 pengamatan tanggal HOLD;
  bukan PASS seluruh CP6. CodeQL35174491674: keempat job SUCCESS.
- Artifact10477389132:53577549 byte,293 entry unik, CRC valid. SHA256 byte lokal
  `146dc8de156bfbd18060b40d3a5b7af0d33a99e19c95f371ee2ca36dd5f11ee0` cocok.
- Fresh230 pada47671d9:179 PASS,39 CONTROL_PASS,12 DATE_POLICY_REVIEW_REQUIRED,
  0 incomplete. Case ID unik230, bukan230 alur bisnis biasa yang semuanya PASS.
- Artifact10477942082:53007482 byte,292 entry, CRC valid; SHA256
  `9d2c1906c3f6bd5c11e46d7baa9740d4eb11d260f6d63c8b88d09bb4950c6abd` cocok.
- Attempt pertama berhenti pada fixture tombol reject setelah claim sudah
  REJECTED. Rework setelahnya incomplete. Follow-up membetulkan fixture,
  menjalankan12 rework fresh dan mengikat ulang218 hasil lain ke47671d9.
- Matrix460 adalah23 generasi ×5 operasi ×4 jadwal maintenance/rollback.
  Tetap REUSED_EVIDENCE historis, bukan460 alur bisnis fresh pada AJ.

## Rencana yang telah dieksekusi

Empat alur recovery → draft sale → posting → invoice material final → recost
FG/COGS → reversal invoice → reversal sale → reversal recovery. Angka dasar:
10 unit material×10,10 cucian×7; percobaan gagal berbayar menambah70 bila ada.
Hanya2 barang recovery tersisa sebelum penjualan1. Invoice final10×12.75
menambah27.50 ke biaya sumber. Oracle ditulis dari angka ini.

Tiga batch import campuran memeriksa error per baris, larangan prepare,
koreksi draft, preview ulang, replay prepare dan posting20 unit bernilai25.
Dua pengamatan tanggal membaca confidence pada tanggal historis yang sama,
bukan menempelkan confidence hari ini pada laporan lama.
Pemeriksaan parser nominal34 kasus adalah tes parser saja; UI/HTTP dibuktikan
terpisah oleh alur layanan asli dan review bukti writer.

Hasil native tambahan sekarang tercantum di bagian keputusan di atas.
Native memakai temporary schema USAGE hanya di transaksi fixture; pengembalian
ACL/data/catalog diperiksa. Bukti native tersebut tidak menggantikan role HTTP.

## Aturan tanggal dan CSV yang tetap terbuka

Master owner AD section16.1–16.5 memisahkan tanggal fisik, ekonomi, sistem,
dan buku; melarang READY sebelum recalc/integrity lengkap; late facts di periode
tertutup memakai controlled adjustment di periode terbuka. Tidak ditemukan
pilihan eksplisit tanggal buku untuk seluruh keluarga koreksi pada periode
terbuka. Jangan memilih kebijakan baru atau mengubah HOLD menjadi PASS diam-diam.

Master section21.1 mewajibkan preview, row errors, totals, idempotency dan
recovery import. Parser/upload CSV dan caller aplikasi belum ditemukan; masih
BELUM TERUJI. Section CP7 dan21.2 menempatkan penyambungan UI sales/payroll/
finance serta full dummy flow pada CP7. Penempatan UI CSV belum eksplisit;
belum diberi N/A atau dipindah ke CP7.

Prinsip: “VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”
