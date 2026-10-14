# Perbaikan sesudah audit penuh CP1–CP7 — daftar gabungan (penulis)

Kandidat yang diaudit: `0b7049d9203bac52b47a4c89f3e0d75646067a8f` (tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`).
Ketiga laporan sudah dikunci sebelum penulis mulai memperbaiki. Daftar ini disusun penulis per akar masalah, mengikuti
Pro Max §10–§11; ini bukan penyatuan resmi auditor dan bukan penerimaan. `production_go:false`.

| Auditor | Laporan terkunci | Vonis |
|---|---|---|
| Fable | `audit/fable_cp17/AUDIT_FABLE_0b7049d9.md` v1.0 (`746693bf`, koreksi `3b0010e0`) + addendum A1–A3 (`1224901f`, `f24c71b8`, `681dd7a9`), cabang `audit/fable-cp1-7-0b7049d9-20261014` | CP1 dan CP2 lulus dengan syarat (sesudah D14-1), CP3/CP5/CP6 lulus dengan syarat, CP4 lulus dengan syarat, CP7 lulus |
| Astra | `audit/astra_cp17/AUDIT_ASTRA_CP17_0b7049d9.md` (`f70361d5`), lanjutan (`d5dcf4e3`), addendum silang `followup-681dd7a9/` (`d4a83b42`), cabang `audit/astra-cp1-7-0b7049d9-20261014` | TAHAN penerimaan penuh |
| Sol | `audit/sol_cp1_7/AUDIT_REPORT.md`, `FINDINGS.json`, `WRITER_HANDOFF.md` (`10bfe397`), cabang `audit/sol-cp1-7-0b7049d9-20261014` | HOLD |

Keputusan owner yang dipakai: D14-2..D14-5 (`../../OWNER_DECISIONS_20261008.md`, 15 Okt 00:15 WIB).

## A. Cacat yang terbukti saat dijalankan (wajib diperbaiki)

| ID gabungan | Asal | Keparahan tertinggi | Masalah | Rencana penulis |
|---|---|---|---|---|
| R-FIN01 | Fable FABLE-001, Astra FIN01 | S0 (Astra) | Bayar upah (penuh, cicilan final, cicilan sebagian) boleh bertanggal sebelum utang upahnya diakui; utang per tanggal minus, tidak ada alarm | D14-2: tolak di batas Native pembayaran upah dan perintah CP7 PAY/cicilan bila tanggal bayar mendahului akrual sumber yang dilunasi; kasbon tetap jalur tersendiri. Tambah detektor utang upah per mandor per tanggal < 0. Kasus PAY04/05/06/FIN07 + kontrol same-day/later, replay, pembalikan, periode tertutup, browser |
| R-CASH01 | Sol SOL-001 | S1 | Bank saldo 0 bisa membayar supplier; saldo jadi minus | D14-3: penjaga bersama per akun kas, kronologis (tidak ada tanggal ≥ tanggal bayar dengan saldo < 0), dikunci per akun; semua pengeluaran (supplier, laundry, upah, kas lain, uang muka, refund). Race dua pembayaran, backdate, pembalikan, detektor |
| R-FIN02 | Fable FABLE-008, Astra FIN02 | S0 (Astra) | Penyelesaian klaim laundry bertanggal sebelum sumber klaim dan utang vendor; AP vendor per tanggal minus, laba pindah hari | Kapasitas kompensasi dihitung per tanggal pengakuan dan tidak boleh mendahului tanggal klaim; D12 (kredit lintas tagihan) tetap sah. MISSING/STUCK/DAMAGE, same-day/later, replay, race, periode tertutup, browser |
| R-RWK01 | Fable FABLE-006, Astra RWK01 | S1 | Upah rework yang sudah diakui utang hilang dari Nota bila semua hasil di-SCRAP | Kelayakan Nota mengikuti kerja yang sah diakui, bukan label hasil barang. ALL-BS/SCRAP 60 bisa masuk Nota dan dibayar sekali; GOOD, campuran, WRITE_OFF/HOLD, pembalikan, browser |
| R-STK01 | Astra STK01 | S0 (Astra) | Sesudah REOPEN lalu POST ulang potongan bertanggal lama, kartu stok historis menampilkan saldo −10 | Pembaca kartu stok "restated" tidak menghitung pasangan asli/pembalik yang sudah netral sebagai dua pemakaian aktif; riwayat tetap terlihat. Selaraskan dengan mesin biaya; kasus sampai re-POST, variasi jumlah/tanggal, browser |
| R-HPP01 | Astra HPP01 (petunjuk Fable R1-02) | S1 | Kebijakan HPP baru untuk mandor yang sebelumnya tidak ikut membuat pool ACTIVE basi tanpa ditolak | Perubahan kebijakan yang mengubah himpunan peserta pool ACTIVE ditolak atomik (atau lewat pembatalan → pool pengganti). Kasus asli, kontrol tidak relevan, batas tanggal berlaku, race, detektor |

## B. Alur yang belum ada (dari pembacaan kode; wajib dilengkapi)

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-SG01 | Fable FABLE-009, Astra SG-01 | Bagi Potongan (pickup) yang sudah POSTED tidak punya jalur koreksi | Pembalik/pengganti milik Native untuk pickup produksi, dengan penghalang dependency yang menunjuk jalan keluarnya; pengaman immutabilitas tetap. Uji salah mandor/tanggal/batch sebelum dan sesudah jahit/laundry/QC |
| R-SG02 | Fable FABLE-010, Astra SG-02 | Sisa kain hanya "terlapor", tidak bisa masuk stok lagi | D14-4: langkah "kain kembali ke gudang" per roll/lokasi/waktu memakai `post_cutting_material_returns` yang sudah ada; nilai kembali dan biaya PO turun. Pakai lagi, pembalikan, replay, browser |
| R-SG03 | Astra SG-03 | Rewash berbayar tanpa ganti SKU belum punya sumber tagihan | Ditelusuri dulu terhadap kebijakan laundry yang sudah ada (LAU-DEC, D11). Bila belum ada aturan, ditanyakan ke owner; tidak dikarang |
| R-LUSIN | Sol (kebutuhan lama `SALES_MANUAL_13`) | Form penjualan tersambung belum bisa membagi lusin ke satu seri ukuran | D14-5: bagi rata otomatis ke ukuran seri + tampilan balik "x lusin y potong"; bagi tidak rata ditolak dengan pesan jelas. Uji unit, browser desktop/HP, simpan/baca ulang |

## C. Akses

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-ACC01 | Fable FABLE-012; Astra RBAC (2 kasus PASS, 6 penolakan) | Peran `authenticated` punya USAGE skema `erp` dan EXECUTE ke 160 fungsi `erp` (108 bernama penulis). Pemeriksaan peran di dalam fungsi menolak non-owner, tetapi jalur langsung melewati fasad | Inventaris dulu siapa yang memanggil tiap fungsi (fasad SECURITY DEFINER, trigger, pembaca); lalu cabut EXECUTE langsung dari `authenticated` yang tidak dibutuhkan; panggilan langsung → 42501; seluruh suite fasad tetap lulus. Skema yang diekspos API hosted: menunggu jawaban owner atas izin baca untuk auditor |

## D. Alat bukti dan dokumen

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-EV01 | Sol SOL-002 | Artefak BE hanya 4/16 karena impor AV memindahkan folder keluaran global | Folder keluaran tetap per run; gerbang unggah memeriksa himpunan ID, jumlah dan status akhir |
| R-EV02 | Sol SOL-003, OPEN-AZ-FIRST | Pemasang membuang pesan PostgreSQL saat berhenti di AZ; penyebab kegagalan pertama 51/58 belum diketahui | Simpan pesan/konteks/berkas+hash secara privat; telusuri kegagalan pertama tanpa melonggarkan pengaman |
| R-DOC01 | Fable FABLE-002 | Dua salinan migrasi AC berbeda (`supabase/migrations` vs `supabase/release/cp6-t3`) | Tetapkan salinan paket rilis sebagai kanonik untuk pemasangan baru, tambahkan pemeriksaan/penjelasan perbedaan; berkas lama tidak diubah, pengaman tidak dilonggarkan |
| R-DOC02 | Fable FABLE-003 | Manifest T3 masih `rollbacks: NOT_TESTED`, label T3_PREP, komentar jumlah berkas basi | Rujuk bukti rollback yang sudah lulus; betulkan komentar |
| R-DOC03 | Fable FABLE-004; Astra CP1_CP2_CROSSCHECK | Bukti CP1/CP2 tidak ada di pohon kandidat | Bawa skrip/bukti CP1/CP2 (hash, bukan rahasia) ke pohon; restore CP2 di image Supabase asli menjadi bagian CP7C |
| R-DOC04 | Fable FABLE-005 | Rencana 75 C6 + 22 ALL tanpa pemetaan | Sudah dipetakan Astra (`C6_75_ALL22_CROSSWALK`); penulis menautkan dan menjalankan ulang yang belum terpetakan bila ada |
| R-DOC05 | Fable A1 | 4 tabel `erp` di hosted tanpa RLS | Kode final 0 tabel tanpa RLS (Fable A3). Penulis menyebut keempat tabel dari riwayat migrasi tanpa query hosted |

## E. Tidak dikerjakan sebagai bug (dengan alasan)

| ID | Asal | Alasan |
|---|---|---|
| FABLE-007 | Fable (dugaan absensi dobel) | Dibantah Astra pada rute yang diuji (PAY02/PAY03). Penulis menambah satu kasus regresi saja, tanpa mengubah produk |
| FABLE-011 | Fable (lantai tanggal cutover) | Astra: bergantung kontrak; larangan global tanpa keputusan owner tidak dibuat |
| A2 | CP7 lama | Tetap OPEN, bukan penghalang (D13-10) |
| A6, F-OPS-05 | CP7 putaran 2 | Sudah ditutup; tidak dibuka ulang |

## F. Untuk pemegang backup (owner)

Fable melaporkan 40 dari 64 karakter passphrase CP2 tercetak di log sesinya. Kunci CP2 dianggap terpapar dan tidak
dipakai untuk backup baru. Backup CP7C memakai kunci baru (rancangan CP7C sudah memakai kunci tersendiri).
