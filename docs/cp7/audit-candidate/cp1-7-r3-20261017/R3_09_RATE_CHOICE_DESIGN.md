# R3-09 — pilihan tarif lama atau baru saat jahit selesai (owner D16-2, D16-3, D16-4)

Keputusan owner persis ada di `docs/cp7/OWNER_DECISIONS_20261008.md` (D16-2, D16-3, D16-4). Berkas ini menjelaskan apa
yang dibuat; kode ada di `scripts/cp7-src/cutting-correction/sewing.sql`, `scripts/cp7_rate_revision_bundle.py`,
`src/SewingCompletionPanel.tsx` dan `src/sewingCompletionContract.ts`; uji di `scripts/cp7_r3_rate_cases.py` dan
`scripts/cp7_r3_rate_browser.mjs`.

## 1. Aturan Native sebelum perubahan

- Upah pertama sebuah PO mengunci tarif per komponen (`erp.ensure_po_work_component_snapshots`): satu baris
  `erp.po_work_component_snapshots` per PO × komponen (× versi SKU untuk potongan wave, `erp.bf_ensure_work_v1`), unik lewat
  indeks `bf_work_snapshot_scope (po_id, work_component_id, bf_sku_version_id) nulls not distinct`.
- Trigger `erp.validate_work_completion` menyalin tarif snapshot ke baris upah; `erp.guard_work_completion_posting_consistency`
  (`AI_WORK_SOURCE_SNAPSHOT_MISMATCH`), pemeriksaan pemasang CP6 dan `erp.run_v268_financial_report_checks` menolak atau
  menghitung rusak baris upah yang tarifnya berbeda dari snapshot yang dirujuknya.

Jadi tarif baru tidak boleh ditulis langsung ke baris upah. Tarif baru dibayar lewat **baris snapshot tambahan (revisi
tarif) PO itu**, sehingga semua penjaga di atas tetap berlaku tanpa diubah.

## 2. Yang dibuat

### 2.1 Aturan pilihan (perintah `erp_cp7_save_sewing_completion_v1`)

- "Tarif lama" = tarif yang dikunci PO (baris snapshot asli). "Tarif baru" = aturan Native pada waktu jahit yang diisi, untuk
  komponen PO yang sama: tarif mandor untuk model dan komponen itu yang berlaku saat itu (`erp.contractor_work_rates`), kalau
  tidak ada maka tarif bawaan item BOM kerja PO itu (komponen dan BOM kerja PO tidak berubah). Untuk SKU wave: versi SKU yang
  berlaku saat itu dan `erp.bf_work_rate_v1`, kalau tidak ada maka tarif dasar menurut aturan tadi.
- Pencatatan pertama PO selalu mengunci tarif pada waktu jahitnya sendiri, jadi tidak pernah ada pilihan.
- Bila tarif baru berbeda dari tarif lama dan PO belum dipindah: `rate_choice` wajib `OLD` atau `NEW`
  (`CP7_SEWING_RATE_CHOICE_REQUIRED`). Bila sama, atau PO sudah dipindah: `rate_choice` ditolak
  (`CP7_SEWING_RATE_CHOICE_UNEXPECTED`). Untuk wave, satu pilihan berlaku untuk semua SKU di permintaan itu.
- Sesudah tombol "Pakai tarif baru seterusnya" (`action = USE_NEW_RATES`, sekali, dengan alasan, tidak bisa dibatalkan,
  tabel `cp7_cutting_correction.po_rate_modes`): setiap pencatatan berikutnya memakai tarif baru tanpa ditanya. Kalau tarif
  baru tidak bisa ditentukan pada waktu itu (misalnya versi SKU tidak ada) pencatatan ditolak
  (`CP7_SEWING_NEW_RATE_UNKNOWN`), bukan diam-diam memakai tarif lama.
- Hanya OWNER/ADMIN (owner D16-4): perintah ini sudah memeriksa peran itu (`sewing_access_now`) untuk semua aksinya.
- Pilihan, mode, dan tarif yang dipakai tercatat di jawaban dan di riwayat (`sewing_history.result` atau
  `sewing_wave_history.result`): `rate_choice`, `rate_mode`, `rate_used` (`LOCKED`/`NEW`), `revised_components`.
- Kunci yang sama dengan penulis tarif Native (`WRATE:` per komponen, `BF:COMMERCIAL_SKUS` untuk wave) diambil sebelum tarif
  dibaca, supaya tarif tidak berubah di tengah perintah. Token tinjauan mencakup garis waktu tarif baru dan status mode.

### 2.2 Revisi tarif

- Satu revisi per baris asli per waktu jahit: dipakai ulang oleh pencatatan lain pada waktu jahit yang sama; waktu jahit lain
  mendapat revisinya sendiri. Bila revisi untuk baris dan waktu yang sama sudah ada dengan tarif lain (aturan tarif masa lalu
  berubah sesudahnya), perintah menolak (`CP7_SEWING_RATE_BASIS_CHANGED`); tidak ada yang ditimpa.
- `committed_at` revisi = jam saat revisi ditulis (selalu sesudah baris asli, dan unik di bawah kunci PO). Waktu jahit yang
  dipakai untuk membaca tarif disimpan di `cp7_cutting_correction.rate_revisions.basis_at`.
- Akibat yang disengaja: layar tarif mandor (`scripts/cp7-src/master/rates.sql`) dan penjaga Native versi tarif membaca
  `committed_at` sebagai "terakhir dipakai", jadi sesudah pencatatan bertarif baru, perubahan tarif itu hanya bisa dimulai
  sesudah hari pencatatan (lebih ketat, tidak lebih longgar).
- Perbaikan BS oleh mandor yang sama: aturan Native tetap (tarif mandor yang berlaku dulu; baris snapshot hanya bila tidak
  ada), dengan baris snapshot terbaru PO bila jatuh ke snapshot.
- Baris snapshot dan revisi tidak pernah diubah atau dihapus; tabel revisi dan tabel mode tidak bisa diubah (trigger
  `immutable`) dan tertutup untuk semua peran aplikasi.

### 2.3 Perubahan Native yang dideklarasikan (`scripts/cp7_rate_revision_bundle.py`)

Semua maju dan dipulihkan persis saat uninstall:

| Objek | Perubahan | Alasan |
|---|---|---|
| indeks `bf_work_snapshot_scope` | ditambah `committed_at` | revisi = baris kedua untuk PO × komponen × versi SKU |
| `erp.bf_ensure_work_v1` | SKU yang baru dikunci memakai baris dasar asli saja | tanpa ini SKU baru mendapat baris ganda |
| `erp.prepare_rework_component_line` (cabang SKU) | baris terbaru, `order by committed_at desc, id desc limit 1` | tanpa urutan hasilnya acak bila ada revisi; sama dengan cabang non-SKU |
| `erp.seed_bs_case_component_baseline` | baris terbaru per komponen | menentukan baris yang dirujuk; jumlah yang dicatat tetap sama |

Pemulihan indeks menolak (`CP7_RATE_REVISIONS_IN_USE`) selama revisi ada: data upah bertarif baru tidak boleh dibuang
diam-diam; jalan kembalinya backup sebelum pemasangan CP7. 16 fungsi lain yang membaca tabel snapshot sudah diperiksa:
membaca per `id`, hanya `exists`, atau sudah memilih yang terbaru.

### 2.4 Layar (`src/SewingCompletionPanel.tsx`)

- Bila tarif berbeda pada waktu jahit yang diisi: dua pilihan, masing-masing dengan tarif per komponen dan upah untuk jumlah
  yang diisi. Tinjauan dan simpan tertutup sampai satu dipilih. Mengubah waktu jahit menghapus pilihan.
- Tombol "Pakai tarif baru seterusnya" tampil bila PO sudah mengunci tarifnya, masih terbuka, dan belum dipindah; perlu alasan
  dan centang tinjauan. Sesudahnya layar menulis bahwa PO memakai tarif yang berlaku pada waktu jahit.
- Pesan hasil menyebut "dengan tarif baru" bila tarif baru dipakai. Jawaban server yang tidak cocok dengan pilihan yang dikirim
  tidak diterima.

## 3. Uji

Native (11): tarif sama tanpa pilihan; tarif berubah perlu pilihan; pilih lama; pilih baru lewat revisi (pakai ulang di waktu
yang sama, revisi baru di waktu lain, upah pertama tetap, detektor Native tidak berubah); tombol seterusnya; penolakan tombol
dan peran (D16-4); batal pencatatan bertarif baru; upah baru masuk alur payroll dan detektor; wave per SKU; delta Native dan
pemulihan yang menolak; tabel tidak bisa diubah dan tertutup. Race (2): dua tab memilih baru; tombol dan pencatatan
bersamaan. HTTP Auth nyata (1). Browser desktop dan HP (2): dua tarif tampil, pilih, simpan, tombol, pencatatan berikutnya
tanpa pilihan, tanpa luapan.
