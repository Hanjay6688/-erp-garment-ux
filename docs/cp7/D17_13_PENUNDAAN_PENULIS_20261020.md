# D17-13: hal CP7 yang ditunda atau dikecilkan penulis tanpa keputusan owner (20 Okt 2026)

Dasar: keputusan owner D17-13 ("ya", `docs/cp7/OWNER_DECISIONS_20261008.md`). Ini laporan saja; tidak ada yang dibuat atau
diubah sebelum owner memutuskan per butir. Cara periksa: semua dokumen `docs/cp7/` (berkas utama dan subfolder), kode
`scripts/cp7-src/` dan layar `src/`, dicari kata seperti "kelak", "ditunda", "belum", "tidak aktif", "later", "deferred",
"not yet"; setiap temuan dicocokkan dengan keputusan owner yang tercatat dan dengan kode hari ini (yang sudah dibuat belakangan
tidak dimasukkan). Kolom "Dicek ulang" = penulis sendiri membuka kode/berkasnya; "belum" = dari pemeriksaan pembantu, rujukan
berkas ada, belum dibuka ulang penulis.

## Kelompok 1 — tidak sesuai keputusan owner yang sudah ada (kesalahan penulis)

| # | Hal | Bukti | Keputusan yang dilanggar | Dicek ulang |
|---|---|---|---|---|
| 1.1 | WhatsApp hanya meneruskan piutang penjualan dan utang bahan. Tagihan lain yang tampil di Pengingat (piutang/utang saldo awal, upah/payroll, nota aksesori mandor, tagihan laundry, terima laundry belum ditagih) tidak dikirim | `scripts/cp7-src/alerts/alerts.sql:348-367` (`ar_source` hanya `receivable_source`, `ap_source` hanya `payable_source`) dan `:484-485`; Pengingat membaca semua domain di `scripts/cp7-src/reminders/staged-reminders.sql:482-487`. Desain `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md:225` masih menyebut sumbernya "draf", padahal sudah terpasang | D17-5 "semua hal yg masuk ke reminder harus langsung forward wa" | ya |
| 1.2 | Penjalan server (K4) hanya untuk analisis bertahap; Business Report v2, kumpulan kondisi pengingat dan "hitung di latar belakang" tetap berhenti bila halaman ditutup | `docs/cp7/k4/K4_RUNNER.json:62-64` ("stay driven by their page") | Keputusan 8 Okt butir 6: "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup" | ya |
| 1.3 | Dokumen paket menyebut "kemampuan/kelipatan produksi ... diisi owner di aplikasi", padahal tidak ada isian kelipatan produksi; analisis selalu memakai kosong | `docs/cp7/P20_P21_PAKET_CABANG_CLAUDE.md:100`; `scripts/cp7-src/planning/analysis.sql:288`, `analysis-stages.sql:1267` (`rounding_multiple` selalu null); tidak ada isian di `src/` | Bukan keputusan dilanggar, tetapi klaim dokumen salah | ya |

## Kelompok 2 — ditunda/dikecilkan atas pilihan penulis, belum pernah ditanyakan ke owner

### Rencana produksi dan analisis

| # | Hal | Akibat untuk owner | Bukti | Dicek ulang |
|---|---|---|---|---|
| 2.1 | Target produksi hanya "rata-rata jual per hari × hari"; mode tingkat layanan (seperti safety stock) ada di mesin hitung tetapi tidak pernah dipakai | Target produksi tidak punya cadangan untuk penjualan yang naik-turun | `planning/baseline-source.sql:73`, `planning/analysis-stages.sql:399` (`'mode','DAYS'`); mesin `baseline/target.sql:7` mendukung `STATISTICAL` | ya |
| 2.2 | Model peramalan (SES, Holt, Croston/TSB) hanya dinilai di layar, tidak pernah dipakai untuk target; tidak ada evaluasi model terjadwal | Saran produksi selalu dari rata-rata sederhana atau angka manual | `docs/cp7/benchmark-decisions.md:9,54,72`; `planning/baseline-source.sql:100` (`BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN`); `src/NativeModelEvaluationPanel.tsx:34`; `docs/cp7/automation-seam.md:96-99` | sebagian |
| 2.3 | Produk baru tidak bisa meminjam pola penjualan produk yang mirip ("analog") | SKU baru tanpa histori "belum diketahui" kecuali diisi manual | `planning/baseline-source.sql:71`, `analysis-stages.sql:397` (`'analog',null`); mesin `demand/estimate.sql:23-29` mendukung | ya |
| 2.4 | Kelipatan produksi (ukuran batch) tidak bisa diisi (lihat 1.3) | Saran jumlah produksi tidak dibulatkan ke batch pabrik | sama dengan 1.3 | ya |
| 2.5 | Analisis bertahap (skala pabrik ±3.600 target) tanpa angka keuangan/HPP, rincian stok, ruang kerja kain dan arsip | Di skala pabrik, analisis tidak menampilkan bagian-bagian itu | `src/NativeStagedAnalysisView.tsx:61-62`, `planning/analysis-stages.sql:2094` (`'financial_capture','DEFERRED'`) | belum |
| 2.6 | Business Report bertahap tanpa perbandingan periode dan lampiran utang/piutang | Laporan skala pabrik tidak membandingkan dengan periode lalu | `docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md:136-137` | belum |
| 2.7 | Analisis otomatis tidak jalan sebelum owner menjalankan analisis sendiri sekali | Peringatan kekurangan produksi/kain diam sampai analisis pertama | `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md:204-205`; hasil tick `NO_OWNER_ANALYSIS_YET` | ya |
| 2.8 | Yield histori: lebih dari 200 grup dalam satu tingkat = "belum diketahui" | Produk yang paling sering dipotong justru tanpa yield histori | `scripts/cp7-src/plan-native/history-yield.sql:237,282` | ya |
| 2.9 | Saran potong tidak tampil di form Buat/Bagi Potongan (hanya di panel rencana) | Saat membuat potongan, saran SKU/ukuran tidak terlihat di form itu | `docs/cp7/shell-mandate.md:64-65`; `src/ConnectedCuttingPage.tsx` tanpa saran | ya |

### Pengingat dan WhatsApp

| # | Hal | Akibat untuk owner | Bukti | Dicek ulang |
|---|---|---|---|---|
| 2.10 | Pengingat pribadi buatan staf tidak diteruskan ke WA owner | Hanya pengingat milik owner yang sampai ke HP | `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md:63`; `queue_manual` hanya milik owner | ya |
| 2.11 | Angka titik pesan ulang manual lama di Enteng (`erp.stock_policy_versions`) tidak dibaca | Kalau ada, harus diketik ulang di layar baru saat pemasangan | `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md:62-65` | ya |
| 2.12 | Kain berumus tidak masuk daftar Ringkasan Gudang | Kain berumus hanya terlihat di Pengingat, WA dan panel Titik pesan ulang | `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md` bagian D17-10 | ya |

### Transaksi dan keuangan

| # | Hal | Akibat untuk owner | Bukti | Dicek ulang |
|---|---|---|---|---|
| 2.13 | Bayar supplier: satu transfer untuk banyak penerimaan belum bisa; nomor bukti transfer hanya di keterangan | Satu transfer dicatat terpisah per penerimaan | `scripts/cp7-src/invoices/payment-create.sql:43-51` (satu `purchase_id`, `note`); `docs/cp7/SUPPLIER_PAYMENT_CREATE_HANDOFF.md:94-95` | ya |
| 2.14 | Urut dan saring di 8 layar hanya berlaku untuk halaman yang sedang tampil (Nota, kas, stok barang jadi, penyesuaian barang jadi, hitung fisik, aksesori, riwayat bayar, retur invoice) | Daftar panjang tidak tersaring/terurut seluruhnya | `src/RecordTools.tsx:31`; 8 layar `filterScope="PAGE"` | ya |
| 2.15 | Ganti mandor sesudah dijahit ditolak (hanya batal Bagi Potongan sebelum dijahit) | Salah mandor yang baru ketahuan sesudah jahit tidak bisa dibetulkan di aplikasi | `docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/SG01_PICKUP_REVERSAL.md:3-4` | ya |
| 2.16 | Retur atas invoice penjualan yang sudah dibayar ditolak; tidak ada refund/kredit pelanggan. Kebijakannya belum pernah ditanyakan | Retur barang dari pelanggan yang sudah lunas tidak bisa dicatat | `docs/cp7/F03_WRITER_HANDOFF_20261001.md:25`, `docs/cp7/F03_REMAINING_CONTRACT.md:32` | belum |
| 2.17 | Batas umur koreksi HPP/harga ditulis "keputusan owner" tetapi tidak pernah ditanyakan | Koreksi boleh mundur tanpa batas umur | `docs/cp7/NOTE_CORRECTION_PRESENTATION.md:32`, `docs/cp7/CLAUDE_MERGE_NEXT_WRITER.md:21` | belum |
| 2.18 | Jurnal kasbon tidak bisa dibuka dari buku besar ("sumber belum didukung") | Klik sumber jurnal kasbon tidak membuka dokumennya | `docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/KASBON_D14_6.md:51` | belum |
| 2.19 | Piutang ke vendor laundry tidak punya alur (koreksi tagihan turun melebihi utang ke vendor ditolak) | Kelebihan bayar ke laundry tidak tercatat sebagai piutang | `docs/cp7/audit-candidate/cp1-7-full-20261014/README.md:93`; `docs/cp6-d11-kebijakan-dan-gbd03.md:87` | belum (PERLU DICEK apakah tercakup LAU-DEC06) |
| 2.20 | Cuci gagal dengan tarif vendor yang belum diketahui | Mungkin tidak bisa dicatat sebelum tarif diisi | `docs/cp7/P04_WIP_HANDOFF.md:72`, `docs/cp7/P09_PROCUREMENT_HANDOFF.md:31` | belum (PERLU DICEK) |
| 2.21 | Koreksi barang jadi jenis lain di QC tidak didukung | Sebagian koreksi barang jadi tidak bisa dari aplikasi | `docs/cp7/QC_SOURCE_HANDOFF.md:7` | belum (PERLU DICEK) |

## Kelompok 3 — HPP kain kantong, aksesori, absen (pertanyaan owner 20 Okt)

Ketiganya sudah ada sejak CP6 dan masuk HPP per pcs lewat hitung ulang HPP per PO (`erp.rebuild_po_hpp`). Rinciannya:

| Bagian | Rumus | Kapan masuk HPP | Batas yang ada |
|---|---|---|---|
| Kain kantong | Semua kain kantong yang keluar dalam satu periode ÷ semua pcs selesai dijahit periode itu (semua mandor, termasuk Afui) × pcs tiap kejadian jahit; sen dibulatkan berurutan | Sesudah Owner/Admin menekan "Bagi ke HPP per periode" di halaman Kain Kantong; sebelum itu tercatat sebagai biaya periode | Satu kolam untuk seluruh pabrik, bukan per model; kain kantong tidak bisa dicatat sebagai kain kedua di potongan; penghalang tutup periode bila belum dibagi: PERLU DICEK |
| Aksesori | Per kategori di BOM aksesori SKU: pcs barang jadi bagus × pemakaian per pcs × harga rata-rata kategori (atau tarif standar) | Otomatis saat barang jadi diterima; barang jadi ditolak bila SKU belum punya BOM aksesori | BOM per kategori (Kancing, Sleting), bukan per warna/ukuran; nota ambil aksesori ke mandor dibebankan ke mandor, tidak ke HPP PO; pertanyaan BOM per warna/ukuran belum dijawab owner (D17-10) |
| Absen | Upah absen (hari dibayar × tarif harian) per periode payroll ÷ pcs selesai dijahit mandor biasa periode itu × pcs tiap kejadian jahit | Sesudah Owner/Admin membuat lalu mengaktifkan pool di halaman HPP & Rekalkulasi; sebelum itu tercatat di WIP tanpa PO | Afui dan mandor khusus tidak ikut; mandor tanpa kebijakan HPP menahan pratinjau; penghalang tutup periode bila pool belum diaktifkan, dan penutupan sisa WIP untuk PO yang sudah selesai saat pool diaktifkan: PERLU DICEK |

Dasar owner: pembagian kain kantong per pcs selesai dijahit termasuk Afui ("ya gas lah tanggung ye", `docs/cp6-initial-import-progress.md:223,259-263`); layar pool HPP (D16-1); HPP final saat PO selesai (D14-14).

## Kelompok 4 — menunggu jawaban owner (sudah ditanyakan)

- Kebutuhan aksesori dari rencana produksi tidak diteruskan ke WA (D17-10 beda (2)): analisis selalu "belum diketahui"
  karena pemakaian aksesori per potong tidak tercatat.
- BOM aksesori per warna/ukuran (A dibuat / B tetap kategori; sleting ikut ukuran celana atau model), laporan aksesori
  mandor (diambil lawan seharusnya terpakai), dan waktunya.

## Sudah diputuskan owner (bukan temuan)

Pemasangan CP7C, jadwal server, backup malam dan WA sungguhan ditahan (D13-3, D13-9a, D17-3, D17-6); pencabutan hak 82
fungsi ditunda ke CP7C (D14-9); aksesori tanpa rumus (D17-10, D17-12); analisis otomatis tiap 240 menit (D17-7); dashboard
terhubung tanpa angka (12 Okt, D13-1); layar uang/absen di mode Enteng (D15-2, D16-1); delapan pengaturan CP6 diisi owner di
aplikasi (8 Okt butir 9); "Tanya AI" tanpa API berbayar (kerangka OWN28-01, PERLU DICEK apakah kata-kata owner).
