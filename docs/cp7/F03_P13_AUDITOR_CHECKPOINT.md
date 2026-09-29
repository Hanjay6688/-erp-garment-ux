# Checkpoint writer F03 — laporan, tutup buku, dan hitung ulang HPP

**F03 OPEN. CP6 CLOSED_CONTRACT_SCOPE. independent_acceptance=false; production_go=false. F04 belum dimulai.** Checkpoint ini untuk auditor, bukan penerimaan independen atau rilis produksi.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## Kandidat dan bukti

Kandidat produk `55cb59dd914052f2c5a72dc535960c0aac00d65d`, tree `4f47389d983f37fbb54450fae670c61e84433fdb`. Bukti berikut tumpang tindih dan tidak boleh dijumlahkan. Tiap receipt mempertahankan SHA asli yang benar-benar dijalankan.

| Cakupan | Bukti writer | Batas |
|---|---|---|
| Perbandingan periode dan arus kas | 24 PASS pada 55cb59d; [receipt](evidence/p13-finance/ANALYSIS_FINAL_REGRESSION_RECEIPT.json). | 12 laporan/arsip lama + 12 analisis. Informasi tercatat sekarang, bukan rekonstruksi pengetahuan masa lalu. |
| Tutup/buka periode dan arsip | 25 PASS pada 55cb59d; [receipt](evidence/p13-finance/PERIOD_FINAL_REGRESSION_RECEIPT.json). | Pemeriksaan native, review yang masih berlaku, replay, dan arsip asli. [Visual sebelumnya](evidence/p13-finance/PERIOD_VISUAL_QUALIFIED_RECEIPT.json) tetap terikat sumbernya. |
| Hitung ulang HPP | 25 PASS pada 55cb59d; [receipt dan screenshot](evidence/p13-finance/RECOST_QUALIFIED_RECEIPT.json). | 12 laporan lama + 13 native/race/Auth/browser recost. Antrean selesai tidak otomatis berarti semua biaya final. |
| Komponen gabungan | 22 PASS pada 23f795a; [receipt](evidence/p13-finance/RECOST_MICROSECOND_COMBINED_RECEIPT.json). | 26 role privat. Jalur produk src, scripts/cp7-src dan supabase identik dengan 55cb59d; identitas run tetap 23f795a. Bukan seluruh E01/F03. |

Keempat suite P13 pada 55cb59d masing-masing memiliki 0 FAIL / 0 INCOMPLETE / 0 NOT_RUN. Standalone laporan 12 juga lulus, tetapi sudah termasuk dalam tiga suite lebih besar. Receipt mengikat hash artifact GitHub, laporan asli/gzip, source tree/bundle, setiap status, pemulihan CP6, advisor, pemasangan/backup recovery, serta cleanup Auth/database. Kegagalan lama tetap tersimpan. Screenshot memakai Auth dan database sementara nyata dengan data sintetis.

## Perubahan dan angka untuk auditor

Perbandingan membaca dua laporan native dalam satu snapshot. Penjualan 1000→1200 memberi pertumbuhan 20%; laba kotor 270→288 berarti margin 27%→24%, turun 3 poin persentase. Uang/rasio memakai string desimal; baseline nol menghasilkan N/A. Kesiapan kedua periode tetap terlihat, sehingga biaya belum lengkap tidak menjadi laba final.

Arus kas mencocokkan saldo harian dengan jurnal menurut tanggal pembukuan. Penerimaan 300 dan pembayaran 200 memberi kas bersih +100. Transfer internal 1000 masuk debit dan kredit, tetapi bersih 0; total debit 1300/kredit 1200. COA bersama dihitung sekali, termasuk rekening nonaktif yang memiliki riwayat. Pembalikan mengikuti tanggal pembukuannya. Sumber jurnal dipaginasi lengkap; refresh gagal menghapus angka lama.

Tutup buku meninjau tanggal, kesiapan, saldo dan versi kontrol. Sumber yang berubah setelah review wajib diperiksa lagi. Replay lama tidak menutup kembali periode yang sudah dibuka. Arsip awal dan GL hari tertutup tetap utuh setelah koreksi kemudian.

Recost memakai processor native dengan batas 20 pekerjaan eligible per permintaan. Harga susulan mengubah basis HPP output FG yang sudah diproduksi 85→90, nilai sisa FG 51→54 dan COGS 34→36. Nilai 85→90 adalah kolom native hpp_total_cost, bukan seluruh biaya PO termasuk WIP yang belum selesai. Stok fisik tidak bertambah; GL hari tertutup dan arsip asli tetap. Respons hilang dipulihkan dengan UUID/intent semula tanpa memproses batch baru.

Hak actor aktif diperiksa kembali setelah menunggu lock dan sebelum cache. Pembaca tidak memperoleh processor; facade tidak memperoleh DML ERP. Kegagalan tetap FAILED dengan jadwal/limit retry native. Kasus 26 fault jobs mencoba 20, mengembalikan 0 selesai, menyisakan 6 pending dan tidak mengubah GL. Fault MATERIAL berlabel administratif, bukan transaksi bisnis biasa.

Bug frontend yang diperbaiki: Date.parse membuang mikrodetik sehingga retry 1µs di masa depan dapat membuat respons native yang valid ditolak. Perbandingan sekarang memakai integer mikrodetik dengan offset zona waktu. Counterexample gagal sebelumnya; 8 kasus lokal lulus sesudahnya. [Bukti lokal](evidence/p13-finance/RECOST_MICROSECOND_LOCAL_RECEIPT.json). Formula HPP/native tetap.

## Riwayat tes dan visual

Perbaikan setup analisis memakai administrator database sementara dengan claims OWNER untuk primitive jurnal internal tanpa grant aplikasi baru. Buffer hasil lengkap dinaikkan 1→16MiB tanpa membuang boundary. Fixture recost memakai enum yang diterima constraint dan mandor terpisah per browser. Selector error jaringan kini membedakan dua peringatan sah. Expected money, replay, larangan DML serta aturan payroll/database dipertahankan.

Screenshot HPP pada 55cb59d sudah diperiksa: kontrol antrean terbaca pada desktop/mobile. Tabel SKU/lot yang sudah ada memakai scroll horizontal di dalam panel pada layar kecil. Screenshot analisis yang diperiksa dan disimpan berasal dari c8f1ba5; review visual tidak dipindahkan diam-diam ke SHA lain. Riwayat gagal 21/4, 24/1 dan regresi mikrodetik 24/1 tetap tersimpan di receipt masing-masing.

## Sisa F03 sebelum F04

[Ledger keluarga](F03_REMAINING_CONTRACT.md) tetap menjadi daftar kerja. E01 penuh belum terbukti: bahan 100×10, konsumsi 60, produksi 60 GOOD dengan biaya 900/HPP 15; jual 20×25, bayar 200, retur 5 harus berakhir FG 45/nilai 675, COGS 225, omzet 375, AR 175 dan kas 200. Kasus recost 85→90 tidak menggantikan oracle itu.

Lanjutan material/retur sumber lunas, E03 barang pelanggan/refund yang sah, biaya konversi bertingkat/pocket/tanggal historis, exit packet dan audit independen tetap terbuka. [E05](P12_E05_CONTRACT_BOUNDARY.md) memerlukan keputusan yang mengikat makna pembayaran parsial: cicilan kas atas payroll APPROVED atau pemilihan sebagian hak kerja untuk payroll yang dilunasi penuh. Native saat ini membayar net payroll penuh; writer tidak membuat kebijakan baru dari asumsi.

Aturan yang sudah disepakati tetap: laundry boleh UNKNOWN sampai kontra bon; harga komponen/kombinasi bersumber dari vendor; riwayat SKU membantu memilih; kredit pada pihak yang sama dapat bergerak antartagihan sambil tetap bisa memotong tagihan asal dan mempertahankan akuntansi yang tepat.
