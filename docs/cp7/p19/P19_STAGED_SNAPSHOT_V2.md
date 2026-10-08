# Kontrak v2: hasil analisis bertahap sebagai snapshot berlabel waktu

Status: **DRAF KONTRAK, implementasi berjalan** (8 Okt 2026). Dasar: keputusan owner 8 Okt
(`../OWNER_DECISIONS_20261008.md`, bagian "snapshot berlabel waktu"). Kandidat audit beku `9d57b7f5` tidak diubah;
semua yang di bawah adalah versi kontrak baru di atasnya. `production_go=false`.

Pabrik owner: ±1.200 SKU × 3 ukuran ≈ 3.600 target. Analisis biasa (jalur tunggal) hanya muat ±100–300 target, jadi
untuk pabrik ini rencana produksi, Business Report, pengingat dan AI harus memakai hasil analisis bertahap.

## 0. Aturan dasar (dari kalimat owner)

1. Hasil analisis bertahap adalah **snapshot yang tidak pernah diubah** (job, acuan, header, halaman dan
   `identity_hash` tetap seperti kontrak §10 `P19_STAGED_5000_20261007.md`).
2. ERP **tidak** diwajibkan berhenti berubah. Snapshot boleh dipakai walau sudah ada transaksi baru, dengan label
   "data per tanggal/jam …", status kesegaran, dan daftar perubahan relevan sejak snapshot.
3. Snapshot **tidak pernah disebut "terkini"** kecuali pemeriksaan penuh ("Cek sumber") membuktikan sama.
4. Business Report, pengingat dan AI boleh memakai snapshot **sebagai analisis**. Angka aktual keuangan, stok dan
   HPP tetap dari pembaca otoritatif sesuai tanggal laporan, tidak dari snapshot.
5. Rencana produksi boleh dibuat dan disimpan sebagai draf dari snapshot. Saat **disahkan/dijalankan**, server
   memeriksa ulang dalam transaksi yang sama: stok, bahan, WIP, kebutuhan, kebijakan dan akses yang relevan.
   Kalau tidak valid lagi: tolak dengan alasan jelas, minta tinjau ulang.
6. Pengingat diperiksa ulang ke data sekarang **sebelum dikirim**; kondisi yang sudah selesai tidak ditagih.
7. Jalur tunggal dan kontraknya (`runs`, `serve`, semantic_hash, wajib UNCHANGED) tidak berubah.

## 1. Label dan kesegaran snapshot (fondasi)

- **Label:** `data_as_of` = `captured_at` acuan job, ditampilkan sebagai "Data per <tanggal jam> WIB".
- **Status kesegaran** (`freshness_state`):
  - `CHANGED`: ada perubahan tercatat sesudah `data_as_of` (lihat daftar), atau pemeriksaan penuh terakhir
    menyatakan `ARCHIVED_STALE`.
  - `NO_RECORDED_CHANGE`: tidak ada perubahan tercatat pada kategori yang dipantau; **bukan** "terkini", karena
    belum dibuktikan pemeriksaan penuh.
  - `VERIFIED_SAME`: pemeriksaan penuh (`erp_cp7_check_staged_analysis_source_v1`) pada jam T menyatakan sama dan
    tidak ada perubahan tercatat sesudah T. Hanya status ini yang boleh disebut sama dengan data sekarang (per jam T).
- **Perubahan relevan sejak snapshot** (`changes_since`): per kategori, jumlah baris yang tercatat sesudah
  `data_as_of` (waktu catat sistem, sehingga transaksi mundur tanggal ikut terhitung) dan jam catat terakhir:
  penjualan & retur, gerak stok barang jadi, gerak stok bahan, potong/WIP (kelompok potong, ambil, jahit, QC,
  laundry, BS, rework), PO produksi, produk/SKU/ukuran, pola & resep kain/aksesori, pembelian bahan.
  Batas hitung per kategori 10.000 (di atasnya ditulis "lebih dari 10.000").
- RPC baru `erp_cp7_staged_snapshot_freshness_v1(p_run uuid)` (authenticated, aktor pemilik run, akses diperiksa
  ulang): `{run_id, identity_hash, data_as_of, freshness_state, changes_since[], last_full_check{state, checked_at}}`.
  Harus selesai jauh di bawah 8 dtk pada 5.000 target. Hasil "Cek sumber" disimpan (tabel baru, immutable) supaya
  `VERIFIED_SAME`/`CHANGED` bisa dibaca tanpa mengulang pemeriksaan penuh.

## 2. Akses per target dari snapshot

Indeks per target (tidak dihapus retensi): `target_key → page index, posisi`, plus baris netting per target dan
nilai skenario yang dipakai rencana (status alokasi, kapasitas start baru, status WIP), diambil dari hasil unit yang
sama (bukan dihitung ulang). Dibaca satu target tanpa membuka halaman lain.

## 3. Rencana produksi v2 (`cp7.plan-draft.v2`)

- **Opsi & simpan draf** dari snapshot: tidak mensyaratkan data tidak berubah. Draf menyimpan `run_id` staged,
  `identity_hash`, `data_as_of` dan nilai snapshot yang dipakai (kebutuhan, stok, WIP, kapasitas).
- **Pratinjau** menampilkan label snapshot dan hasil pemeriksaan ulang live (tanpa menulis).
- **Sahkan/jalankan (apply)**, dalam satu transaksi, sebelum dan sesudah penulisan Native:
  akses; produk dan kebijakan produksi masih aktif; asumsi tetap ditinjau; bahan/roll (sama seperti v1, live);
  stok barang jadi dan WIP target sekarang dibanding snapshot — kebutuhan sekarang = kebutuhan snapshot dikurangi
  kenaikan stok dan WIP target sejak snapshot (penurunan tidak menambah rencana diam-diam); jumlah potong ≤
  batas potong dari kebutuhan sekarang; kapasitas = kapasitas snapshot dikurangi rencana lain yang disahkan sesudah
  snapshot; tidak ada rencana lain untuk target yang sama sesudah snapshot.
- Penolakan dengan kode dan pesan jelas, contoh: `CP7_PLAN_V2_NEED_CHANGED` ("Kebutuhan sekarang 40 pcs, rencana
  60 pcs. Tinjau ulang."), `CP7_PLAN_V2_CAPACITY_USED`, `CP7_PLAN_V2_POLICY_CHANGED`, ditambah kode bahan v1.

## 4. Business Report v2

- Laporan dari snapshot memakai `identity_hash` (bukan semantic_hash), mencantumkan "Data per …" dan status
  kesegaran saat diterbitkan; diterbitkan walau ada perubahan sesudah snapshot.
- Dibagi per bagian sesuai halaman snapshot (tiap bagian ≤ 8.000.000 byte) plus ringkasan seluruh target.
- Bagian keuangan aktual dibaca dari pembaca keuangan otoritatif untuk tanggal laporan, bukan dari snapshot.

## 5. Pengingat v2

- Kondisi pengingat boleh berasal dari snapshot (dengan label).
- Sebelum dikirim/ditampilkan sebagai tagihan, kondisi diperiksa ulang ke data sekarang; yang sudah selesai
  ditandai selesai dan tidak dikirim.

## 6. AI v2

- AI menerima ringkasan snapshot berbatas (total, target prioritas, perubahan sejak snapshot) dan rincian target
  yang dipilih, dengan label "Data per …"; angka keuangan aktual dari pembaca otoritatif.

## 7. Uji yang diwajibkan per bagian

Native (database sungguhan, CI): label dan setiap status kesegaran; perubahan per kategori termasuk transaksi mundur
tanggal; tidak pernah "terkini" tanpa pemeriksaan penuh; rencana: simpan dari snapshot berubah, apply ditolak per
penyebab (stok naik, WIP naik, kebijakan berhenti, kapasitas terpakai, bahan habis, akses) dan diterima bila masih
valid; laporan/pengingat/AI sesuai bagian masing-masing; jalur tunggal tetap identik. Frontend dan browser:
label dan status tampil, tidak ada kata "terkini" tanpa VERIFIED_SAME.

## 8. Progres

| Bagian | Status |
|---|---|
| 1 Label & kesegaran | dikerjakan |
| 2 Akses per target | belum |
| 3 Rencana v2 | belum |
| 4 Business Report v2 | belum |
| 5 Pengingat v2 | belum |
| 6 AI v2 | belum |
