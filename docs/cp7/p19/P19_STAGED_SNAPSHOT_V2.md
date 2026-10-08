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
3. Snapshot **tidak pernah disebut "terkini"**. Pemeriksaan penuh ("Cek sumber") hanya menyatakan perbandingan pada
   jamnya sendiri: "sama dengan data per jam T" atau "sudah berubah (dicek jam T)".
4. Business Report, pengingat dan AI boleh memakai snapshot **sebagai analisis**. Angka aktual keuangan, stok dan
   HPP tetap dari pembaca otoritatif sesuai tanggal laporan, tidak dari snapshot.
5. Rencana produksi boleh dibuat dan disimpan sebagai draf dari snapshot. Saat **disahkan/dijalankan**, server
   memeriksa ulang dalam transaksi yang sama: stok, bahan, WIP, kebutuhan, kebijakan dan akses yang relevan.
   Kalau tidak valid lagi: tolak dengan alasan jelas, minta tinjau ulang.
6. Pengingat diperiksa ulang ke data sekarang **sebelum dikirim**; kondisi yang sudah selesai tidak ditagih.
7. Jalur tunggal dan kontraknya (`runs`, `serve`, semantic_hash, wajib UNCHANGED) tidak berubah.

## 1. Label dan kesegaran snapshot (fondasi) — dibuat

- **Label:** `data_as_of` = `captured_at` acuan job, ditampilkan sebagai "Data per <tanggal jam> WIB".
- **Batas snapshot yang tepat.** Saat acuan dibaca, server menyimpan juga *snapshot database* tempat acuan itu dibaca
  (`cp7_analysis_stage.capture_marks`, satu statement dengan pembacaan acuan). Begitu pula setiap "Cek sumber"
  (`source_checks.source_snapshot`). Sebuah baris dihitung "sesudah batas" bila ditulis atau terakhir diubah oleh transaksi
  yang **belum terlihat** di snapshot itu — jadi transaksi yang masih berjalan saat analisis/cek lalu selesai sesudahnya
  tetap terhitung, walau jam catatnya lebih awal — atau bila jam catat sistemnya sesudah batas (transaksi mundur tanggal
  terhitung). Penghapusan dihitung dari baris `DELETE` jejak audit (`erp.audit_logs`; hanya tabel, aksi, jam dan
  transaksinya yang dibaca). Bila transaksi yang membaca acuan/cek sudah menulis sebelumnya (hanya terjadi di uji satu
  transaksi), snapshot tidak disimpan dan batas dinilai dari jam catat saja (`boundary: RECORDING_TIME`).
- **Status kesegaran** (`freshness_state`):
  - `STALE_VERIFIED`: "Cek sumber" terakhir menemukan sumber sudah berubah ("sudah berubah, dicek jam T").
  - `VERIFIED_SAME`: "Cek sumber" terakhir menemukan sama dan tidak ada perubahan tercatat sesudah cek itu. Ditampilkan
    "sama dengan data per jam T" (`same_as_of` = T); **bukan** "terkini".
  - `CHANGES_RECORDED`: ada perubahan tercatat sesudah snapshot (atau sesudah cek terakhir yang menyatakan sama).
  - `NO_RECORDED_CHANGE`: belum ada perubahan tercatat di kategori yang dipantau dan belum pernah dicek penuh;
    **bukan** "terkini".
- **Perubahan relevan sejak snapshot** (`changes_since`): per kategori `rows` (baru/diubah + dihapus), `deleted`,
  `rows_after_check` (sesudah cek terakhir) dan jam catat terakhir. Kategori dan tabel yang dipantau (daftar tetap,
  `cp7_analysis_stage.change_sources()`): penjualan & retur; gerak stok barang jadi; gerak stok bahan; produksi (kelompok
  potong, ambil potongan, batch distribusi, ambil WIP, jahit, QC, laundry kirim/terima, BS, penyelesaian BS, rework, tanda
  kontrol WIP); PO produksi; data induk (produk, versi SKU, pola, bahan, BOM aksesori, lokasi); pembelian bahan; kebijakan
  perencanaan (kebijakan produksi, profil, rencana jadwal, resep kain, bukti grup habis). Daftar ini adalah "perubahan
  relevan" untuk dibaca owner, bukan seluruh tabel yang dibaca analisis; karena itu kesamaan hanya dinyatakan oleh "Cek sumber".
- **RPC** (authenticated, hanya aktor pemilik run, akses diperiksa ulang sebelum dan sesudah):
  - `erp_cp7_staged_snapshot_freshness_v1(p_run uuid)` — baca kesegaran tanpa menulis.
  - `erp_cp7_check_staged_snapshot_v1(p_run uuid)` — "Cek sumber" penuh, hasilnya disimpan sekali (tabel immutable
    `source_checks`); menjawab hanya hasil cek (`cp7.native-analysis-snapshot-check.v1`: `run_id, source_state, checked_at,
    boundary`). Cek sendiri sudah dekat batas 8 dtk pada 5.000 target, jadi hitungan perubahan dibaca sesudahnya lewat RPC
    kesegaran, masing-masing di bawah batasnya sendiri.
  - Jawaban `cp7.native-analysis-snapshot-freshness.v1`: `run_id, identity_hash, data_as_of, evaluated_at, freshness_state,
    capture_boundary, changes_since[], changes_total, last_full_check{source_state, checked_at, boundary,
    changes_after_check} | null, same_as_of, apply_enabled=false, production_go=false`.
- **Uji:** `P19G_SNAPSHOT_FRESHNESS` (Native, satu transaksi: label, keempat status, transaksi mundur tanggal, penghapusan,
  halaman tidak berubah, aktor lain ditolak, cek dan tanda snapshot immutable) dan `P19G_RACE_SNAPSHOT_IN_FLIGHT`
  (transaksi sungguhan: tulis yang masih berjalan saat analisis dan saat cek terhitung sesudah selesai, cek saat tulis
  berjalan tetap "sama", penghapusan oleh transaksi lain terhitung).
- **Batas terbuka:** hitungan membaca seluruh baris tabel yang dipantau (tanpa indeks waktu); waktu pada 5.000 target dan
  pada data bertahun-tahun belum diukur. Penghapusan di tabel tanpa jejak audit (gerak stok, event jahit, ambil WIP, tanda kontrol WIP, versi
  SKU, pola, pembelian, tabel kebijakan CP7) tidak terhitung; tabel-tabel itu dijaga trigger sistem/immutable atau tidak
  punya jalur hapus di aplikasi.

## 2. Akses per target dari snapshot

Indeks per target (tidak dihapus retensi): `target_key → page index, posisi`, plus baris netting per target dan
nilai skenario yang dipakai rencana (status alokasi, kapasitas start baru, status WIP), diambil dari hasil unit yang
sama (bukan dihitung ulang). Dibaca satu target tanpa membuka halaman lain.

## 3. Rencana produksi v2 (`cp7.plan-draft.v2`) — server dibuat (`scripts/cp7-src/plan-native/staged.sql`)

- **Opsi & simpan draf** (`erp_cp7_get_plan_options_v2`, `erp_cp7_save_plan_draft_v2`): dari indeks per target,
  tidak mensyaratkan data tidak berubah. Draf menyimpan `run_id` staged, `identity_hash`, `data_as_of` dan nilai
  snapshot (kebutuhan, stok barang jadi, WIP model+ukuran, kapasitas, status kebijakan, asumsi). Pemeriksaan tingkat
  snapshot dan komposisi Native (PO, pola, lokasi, roll, ukuran) sama dengan v1. Asumsi yang wajib ditinjau: asumsi
  global run (jadwal) + profil permintaan target + kebutuhan kain target (+ perkiraan yield bila diisi).
- **Pratinjau** (`erp_cp7_preview_plan_action_v2`): label snapshot dan hasil pemeriksaan ulang live per butir
  (PRODUCT, POLICY, TARGET_PLANS, LINKED_PLANS, WIP, NEED, CAPACITY), tanpa menulis.
- **Sahkan** (`erp_cp7_apply_plan_action_v2`), satu transaksi, urutan kunci: permintaan → roll → `CP7:PLAN_CAPACITY`
  → target → versi; pemeriksaan live sebelum dan sesudah penulis Native:
  - produk masih satu baris aktif, model dan ukuran sama; kebijakan produksi sekarang KNOWN dan ACTIVE;
  - rencana lain untuk target yang sama yang tercatat sesudah snapshot → `CP7_PLAN_V2_TARGET_PLANNED`
    ("sesudah" = waktu catat ≥ waktu data, atau transaksinya belum terlihat oleh snapshot); rencana lebih awal
    memakai aturan v1 (grup harus sudah diposting, ada di cakupan produksi snapshot dan terbukti) →
    `CP7_PLAN_LINKED_INTENT_CONFLICT`;
  - stok barang jadi target (grade A/B, seperti analisis) dan WIP perusahaan di pool potong model+ukuran target
    (grup terposting yang tidak terbukti habis saat snapshot, dinormalisasi per 50 grup seperti analisis; >200 grup
    atau grup yang tidak COMPLETE → `CP7_PLAN_V2_WIP_UNKNOWN`);
  - kebutuhan sekarang = kebutuhan snapshot − max(0, (stok + WIP sekarang) − (stok + WIP snapshot)); penurunan tidak
    menambah rencana; potong > batas potong sekarang (atau kebutuhan 0) → `CP7_PLAN_V2_NEED_CHANGED`;
  - kapasitas sekarang = kapasitas snapshot − potong semua rencana lain yang tidak ada di beban snapshot (dicatat
    sesudah snapshot, masih draf Native, atau terposting di luar cakupan snapshot) → `CP7_PLAN_V2_CAPACITY_USED`;
    kalender kapasitas lewat → `CP7_PLAN_V2_CAPACITY_EXPIRED`;
  - bahan/roll dan akses sama seperti v1.
  Penolakan: SQLSTATE 40001, pesan = kode, DETAIL = JSON angka (kebutuhan sekarang, potong dipilih, stok/WIP
  sekarang vs snapshot, kapasitas tersisa), tanpa draf Native atau intent.
- Draf v1 tidak bisa dipakai di RPC v2 dan sebaliknya (`CP7_PLAN_V2_DRAFT_KIND` / `CP7_PLAN_FIELDS`). File v1 tidak berubah.
- Batas yang dicatat: WIP dibandingkan per model+ukuran (warna lain dari model yang sama ikut mengurangi kebutuhan,
  arahnya menolak, tidak meloloskan); kapasitas memakai potong yang tertulis di draf rencana (bukan suntingan draf
  Native sesudahnya); apply v1 tidak memakai kunci kapasitas (dua apply v1 dan v2 bersamaan bisa sama-sama lolos
  kapasitas, sama seperti v1 hari ini); run yang selesai sebelum indeks ada perlu dianalisis ulang
  (`CP7_PLAN_V2_SNAPSHOT_INDEX_MISSING`).

## 4. Business Report v2 — server dibuat (`scripts/cp7-src/planning/report-staged.sql`)

- Satu permintaan = satu job atas run bertahap milik pelaku yang sudah selesai, terikat `identity_hash`
  (bukan semantic_hash). Job disusun satu langkah per panggilan biasa (batas 8 detik tidak dinaikkan):
  ACTUALS → satu SECTION per halaman run → FRESHNESS → SUMMARY, lalu disegel sekali (tabel `report_jobs`,
  `report_reads`, `report_sections`, `report_publications`; isi tidak bisa diubah atau dihapus).
- Label: ringkasan dan setiap bagian menulis "Data analisis per <jam WIB>"; angka analisis disebut keadaan pada
  waktu itu, bukan angka saat ini; kata "terkini" tidak dipakai. Kesegaran saat diterbitkan ditulis dengan kata
  (VERIFIED_SAME dengan jam cek, STALE_VERIFIED, CHANGES_RECORDED dengan jumlah per kategori, NO_RECORDED_CHANGE).
  Laporan tetap boleh diterbitkan walau data sudah berubah sesudah snapshot.
- Angka aktual (ACTUALS, satu pernyataan, satu jam baca): stok barang jadi per produk dengan aturan analisis
  (grade A/B; fisik tanpa reservasi penjualan dan pembaliknya; tersedia sesudah reservasi; waktu fisik dan waktu
  catat tidak sesudah jam baca), dicetak per target di samping angka saat analisis. Keuangan dan HPP hanya bila
  dipilih dan diizinkan: laporan keuangan Native yang sudah diterima untuk tanggal Jakarta jam baca itu (tanggal
  laporan); tanpa itu laporan menulis "Keuangan dan HPP tidak dimasukkan … Tidak ada angka pengganti."
- Akses: hanya run milik sendiri; keuangan hanya OWNER/ADMIN dengan `finance.reports.view` (preflight tutup buku
  hanya dengan `finance.period_close.manage`), dicek saat minta, di ACTUALS, di SUMMARY, dan setiap baca; akses
  berubah di tengah job → job gagal tanpa laporan.
- Seri: revisi mengikuti versi terakhir yang disebut (40001 `CP7_REPORT_REVISION_CHANGED` bila kalah), jenis dan
  periode sama; revisi boleh memakai snapshot yang lebih baru. Satu UUID = satu permintaan di v1 dan v2.
- RPC: `erp_cp7_publish_report_v2`, `erp_cp7_get_report_request_v2`, `erp_cp7_step_report_v2`,
  `erp_cp7_read_report_v2`, `erp_cp7_read_report_section_v2`, `erp_cp7_list_reports_v2`. v1 tidak berubah.
- Batas yang dicatat: biaya ACTUALS dengan keuangan dan FRESHNESS pada 5.000 target belum diukur; stok aktual dibaca
  sekali di awal job (jamnya tertulis), perubahan sesudahnya terhitung di kesegaran; perbandingan laporan dan
  lampiran kewajiban v1 belum tersedia untuk laporan bertahap.

## 5. Pengingat v2 — dibuat (`scripts/cp7-src/reminders/staged-reminders.sql` + panel "Pengingat dari analisis bertahap")

- Kondisi pengingat boleh berasal dari snapshot (dengan label).
- Sebelum dikirim/ditampilkan sebagai tagihan, kondisi diperiksa ulang ke data sekarang; yang sudah selesai
  ditandai selesai dan tidak dikirim.
- Daftar kondisi: job bertahap per run milik sendiri (`erp_cp7_step_reminder_conditions_v2`), satu halaman analisis
  per langkah, lalu segel sekali (jumlah baris sama dengan total halaman, hash kumpulan dari identitas run + hash
  setiap kondisi). Aturan sama dengan v1 (kekurangan produksi per ukuran, kain, aksesori tidak diketahui), tanpa
  aturan "sumber berubah" karena kesegaran sudah ditulis terpisah. Dibaca berhalaman (≤ 50) dengan saringan aturan
  dan keadaan; belum disegel → 40001.
- Periksa ulang (`erp_cp7_recheck_reminder_v2`, tanpa menulis): kebutuhan sekarang = kebutuhan snapshot dikurangi
  barang jadi + WIP model dan ukuran yang bertambah sejak snapshot. Hasil: `RESOLVED_NOW` (sudah selesai sejak
  analisis, tidak ditagih), `CHANGED_REVIEW_REQUIRED` (produk, kebijakan atau rencana lain berubah),
  `UNKNOWN_NOW`, `BELOW_THRESHOLD_NOW`, `STILL_OPEN`, `CONDITION_CHANGED` (kain: bahan bergerak sesudah snapshot).
- Kirim lokal: klaim (`erp_cp7_claim_reminder_v2`) memeriksa ulang di transaksi yang sama dengan kunci episode;
  hanya `STILL_OPEN` yang diklaim, lainnya `NOT_SENT` dengan alasan; jeda/jam tenang ditolak tanpa menulis; satu
  UUID = satu permintaan. Selesai (`erp_cp7_finish_reminder_v2`) memeriksa ulang sekali lagi; berubah → ditahan
  (`SUPPRESSED` dengan alasan). Tujuan tetap pratinjau lokal (tidak ada pesan ke orang lain).
- Piutang/utang (`erp_cp7_get_reminder_obligations_v2`) selalu dibaca dari sumber sekarang, bukan snapshot; yang
  sudah lunas tidak muncul.
- Default yang dipakai: pengingat kain ditahan bila bahan berubah sesudah snapshot; produksi memakai kebutuhan yang
  sudah dikurangi; kebijakan dan tujuan memakai tabel ERP yang sama dengan v1; klaim v2 tidak terlihat oleh v1
  (batas yang dicatat).
- RPC (11): `erp_cp7_step_reminder_conditions_v2`, `erp_cp7_read_reminder_conditions_v2`,
  `erp_cp7_get_reminder_obligations_v2`, `erp_cp7_recheck_reminder_v2`, `erp_cp7_get_reminder_workspace_v2`,
  `erp_cp7_save_reminder_policy_v2`, `erp_cp7_save_reminder_binding_v2`, `erp_cp7_claim_reminder_v2`,
  `erp_cp7_finish_reminder_v2`, `erp_cp7_resolve_reminder_claim_v2`, `erp_cp7_get_reminder_request_v2`. v1 tidak
  berubah dan menolak run bertahap.

## 6. AI v2 — dibuat (`scripts/cp7-src/planning/ai-staged.sql` + panel "Tanya AI dari analisis bertahap")

- Server `erp_cp7_get_staged_ai_brief_v1(run, targets)`: ringkasan berbatas run bertahap milik sendiri dari indeks per
  target (tanpa membaca halaman penuh): identitas, "data per", kesegaran saat ini (kontrak sama dengan RPC
  kesegaran), total seluruh target, paling banyak 25 target dengan kekurangan terbesar (gap bersyarat > 0, terbesar
  dulu) dan paling banyak 20 target pilihan pengguna, masing-masing dengan halamannya. Tidak ada keuangan di
  ringkasan, tidak menulis apa pun, server tidak memanggil AI.
- Layar: target dipilih di tabel ("Pilih untuk AI"); panel menyalin teks yang sudah diperiksa: angka analisis
  disebut keadaan per waktu data, bukan angka saat ini, dengan kesegaran dan perubahan sejak data diambil.
  Keuangan dan HPP hanya bila dipilih dan diizinkan: laporan keuangan ERP dibaca saat pertanyaan dibuat dan
  disebut begitu; tanpa itu teks menulis keuangan tidak disertakan.

## 7. Uji yang diwajibkan per bagian

Native (database sungguhan, CI): label dan setiap status kesegaran; perubahan per kategori termasuk transaksi mundur
tanggal; tidak pernah "terkini" tanpa pemeriksaan penuh; rencana: simpan dari snapshot berubah, apply ditolak per
penyebab (stok naik, WIP naik, kebijakan berhenti, kapasitas terpakai, bahan habis, akses) dan diterima bila masih
valid; laporan/pengingat/AI sesuai bagian masing-masing; jalur tunggal tetap identik. Frontend dan browser:
label dan status tampil, tidak ada kata "terkini" tanpa VERIFIED_SAME.

## 8. Progres

| Bagian | Status |
|---|---|
| 1 Label & kesegaran | server, tampilan dan uji dibuat. CI `a96def4d`: p19-staged12 PASS (termasuk `P19G_SNAPSHOT_FRESHNESS` dan `P19G_RACE_SNAPSHOT_IN_FLIGHT`), 10 workflow lain PASS; p19-scale5 attempt 1 gagal pada "Cek sumber" v1 di 5.000 target (log `../evidence/snapshot-v2-20261008/02_...`); sesudah K7a, p19-scale5 PASS di `c7c0b1c6`: sumber analisis 5.000 produk 1,42 dtk server (sebelumnya mendekati 8 dtk). Pada 100 target: cek 66 ms, kesegaran 13 ms; 5.000 target belum terukur |
| 2 Akses per target | indeks per target dibuat (`plan_targets`, `plan_scope`, `plan_groups`, ditulis ANA_TARGETS/ANA_META, tidak ikut dihapus retensi) + pembaca `plan_target`; uji keluarga staged lokal; uji Native menyusul bersama rencana v2 |
| 3 Rencana v2 | server dibuat (`plan-native/staged.sql`, 5 RPC, tabel `staged_drafts`); uji kecil SQL lokal lolos (bukan bukti); 18 kasus CI (`P19_PLAN_V2.json`: 10 Native, 4 balapan, 2 HTTP, 2 browser) di workflow P19 suite `p19-plan-v2-18`; layar dibuat (tombol per target di halaman bertahap, panel rencana jenis STAGED dengan "data per", hasil pemeriksaan ulang dan alasan penolakan; domain pemulihan dan penunjuk terpisah dari v1; pengurai menghitung ulang kebutuhan dan kapasitas) + uji unit/DOM |
| 4 Business Report v2 | server dibuat (`planning/report-staged.sql`, 6 RPC, 4 tabel); uji kecil SQL lokal lolos termasuk jalur keuangan (bukan bukti); 20 kasus CI (`P19_REPORT_V2.json`: 10 Native, 6 balapan, 2 HTTP, 2 browser) di workflow P19 suite `p19-report-v2-20`; layar dibuat (panel "Laporan dari analisis bertahap" di bawah hasil bertahap: buat/lanjutkan/periksa permintaan, progres per langkah, ringkasan dan satu bagian dibaca sesuai pilihan, daftar dan revisi) + uji unit/DOM |
| 5 Pengingat v2 | server dibuat (`reminders/staged-reminders.sql`, 11 RPC, 6 tabel); uji kecil SQL lokal lolos (bukan bukti); 16 kasus CI (`P19_REMINDER_V2.json`: 9 Native, 3 balapan, 2 HTTP, 2 browser) di workflow P19 suite `p19-reminder-v2-16`; layar dibuat (panel "Pengingat dari analisis bertahap": siapkan daftar, saring, periksa ulang, pratinjau lokal, tujuan dan pengaturan) + uji unit/DOM |
| 6 AI v2 | server dibuat (`planning/ai-staged.sql`, 1 RPC); uji kecil SQL lokal lolos (bukan bukti); 9 kasus CI (`P19_AI_V2.json`: 4 Native, 1 balapan, 2 HTTP, 2 browser) di workflow P19 suite `p19-ai-v2-9`; layar dibuat (pilih target di tabel, panel Tanya AI) + uji unit/DOM |
