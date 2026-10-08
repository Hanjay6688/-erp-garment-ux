# Kandidat audit CP7 beku — 8 Okt 2026

Owner 8 Okt: "Bekukan kandidat audit sekarang." Kandidat ini tidak diubah lagi. Kebijakan dan fitur yang disetujui
owner pada hari yang sama dikerjakan sebagai kelanjutan terpisah (`../../CONTINUATION_AFTER_FREEZE_20261008.md`).

## Identitas kandidat

- **Commit kandidat: `9d57b7f576eaf4a3535c70003c3d67fdc4c8fcff` = head `cp7/integration`** (fast-forward `ab6f1f97` →
  `720d6f0b` → `9d57b7f5`, tanpa force, `main` tidak disentuh). Receipt CI: `FREEZE_RECEIPT.json`.
- Sumber produk tidak berubah sejak pembekuan pertama `720d6f0b`; antara keduanya hanya berubah dua berkas uji dan satu
  pemicu workflow (lihat bagian CI di bawah). Sumber non-dokumen `720d6f0b` identik byte dengan `dcee3726`.
- Terhadap paket review GPT `../staged-5000-20261008/SOURCE_MANIFEST.json` (source `59d63e46`, 2.098 berkas): di
  `720d6f0b` 2.097 berkas identik, 1 berubah (`.github/workflows/claude-p21-rehearsal.yml`), 1 ditambah
  (`scripts/cp7_p21_full_rehearsal_probe.py`); rincian hash `SOURCE_DELTA.json`. `9d57b7f5` menambah perubahan uji di bawah.
- Kompilasi paket gabungan yang dilatih di P21: `FULL_COMPOSITION_P21.sql.gz`
  (`cp7_obligation_report_bundle.bundle()`, 1.944.792 byte, SHA-256 SQL
  `3ec2cf58beabc5c34352318ee333d9dedab08aeda93fa52aabd3d37aec218f83`, sama dengan hash yang dicetak run `37716123319`).
  Kompilasi lama F03 dan full-rule-source tetap di `../staged-5000-20261008/`.

## CI pada kandidat (`FREEZE_RECEIPT.json`)

- Push ke `cp7/integration` memicu workflow lama integrasi (`cp7/**`) yang belum pernah dijalankan pada kode cabang Claude.
  Di `720d6f0b`: 67 run; tiga workflow lama merah, semuanya uji yang tertinggal, bukan produk. Kegagalan pertama disimpan
  di `../../evidence/freeze-20261008/01..03`:
  1. `cp7-p13-analysis` dan `cp7-f03-full` (p13): pembanding JIT keuangan masih memakai definisi sebelum perbaikan rumus
     F1/F2 (`17ce3f76`). Perbaikan `67f29945`: pendahulu = definisi `17ce3f76` tanpa klausa JIT; definisi sebelum
     `17ce3f76` wajib sama dengan BASE + klausa JIT. Identitas byte penuh tetap diwajibkan.
  2. `cp7-shell`: kontrol emisi probe belum memberi flag mode staged (`p19_staged`). Perbaikan `174da930`.
  3. `cp7-f03-full` tidak terpicu oleh berkas pembanding yang dipakainya; pemicu ditambah (`9d57b7f5`).
- Di `9d57b7f5`: 22 run, termasuk **15/15 workflow kualifikasi** dan lima workflow lama yang terdampak; semuanya hijau.
  `claude-p19-transport` attempt 1 gagal di p19-scale5 (lihat batas terbuka "Cek sumber" di bawah; kegagalan pertama
  `../../evidence/freeze-20261008/04`), attempt 2 hijau pada kode yang sama.
- Keputusan per workflow (66 berkas workflow): 66 hijau. 20 diputuskan pada `9d57b7f5`; 46 workflow lama tanpa pemicu
  manual tetap diputuskan pada `720d6f0b`, karena perbedaan non-dokumen hanya tiga berkas uji/pemicu di atas.

## 1. Fitur selesai (bukti writer, bukan penerimaan auditor)

| Area | Bukti |
|---|---|
| Seluruh 15 workflow kualifikasi CP7 cabang Claude (35 job) | source `59d63e46`, `../../evidence/gpt-staged-5000-20261008/59d63e46-same-source-ci.json`; diulang pada SHA kandidat (receipt) |
| Analisis bertahap 5.000 target (enam RPC v1, sepuluh tabel privat/RLS/immutable, halaman ≤ 8.000.000 byte, identity_hash, 5.001 ditolak) | kontrak `../../p19/P19_STAGED_5000_20261007.md` §10; tangga aplikasi `../../p19/P19_FULL_APP_SCALE.md` §7 |
| Keuangan dimuat saat perlu; tidak dimuat ≠ nol | arahan 7 Okt butir 2; P20/P21 §11 |
| PL-8 bukti grup habis tersimpan, terikat versi sumber | P20/P21 §12 |
| AP-5 pengingat memakai alokasi tercatat | P20/P21 §11 |
| Latensi: pengecualian latar dicatat; 3 dtk tidak ditandai tercapai | P20/P21 §14.5 |
| Gladi P21 komposisi penuh termasuk staged, pemakaian di-commit, backup terpakai → restore, rollback = restore pra-pasang | run `37716123319`, P20/P21 §15 (**gladi**, bukan pemasangan) |

## 2. Batas yang masih terbuka

- Audit independen P20 belum ada. Pemasangan P21 nyata menunggu audit diterima dan izin pemasangan terpisah.
- Keputusan owner 8 Okt yang belum diimplementasikan (sengaja, karena dibekukan): PL-5 B, retensi 7 hari,
  penjalan server staged, urutan downstream staged, penjalan server PL-8. Selama itu sistem tetap
  `PENDING_POLICY_VALUE` / client-driven, sesuai yang diuji.
- Delapan pengaturan nyata CP6 (akun/kategori/perjanjian vendor) diisi owner; LAU-DEC06 yang sudah diputuskan
  masih perlu diterapkan di aplikasi sebelum posting invoice laundry.
- Downstream staged (laporan, pengingat, AI, rincian stok, workspace kain, draf rencana, arsip) belum tersedia
  untuk run bertahap. Keuangan staged DEFERRED, bukan nol.
- Hitung baru 5.000 target 83–110 dtk (latar); 3 dtk tetap sasaran optimasi, tidak tercapai untuk hitung baru.
- **"Cek sumber" (`erp_cp7_check_staged_analysis_source_v1`) pada 5.000 target dekat batas 8 dtk:** satu statement
  menangkap ulang seluruh sumber. Di runner CI ±1,3–1,5× lebih lambat (run `37741354450` attempt 1) ditolak
  `statement timeout`; di runner biasa lulus. Gagal tertutup (penolakan jujur, bukan angka salah), tetapi di server
  yang lebih lambat tombol ini bisa tidak tersedia untuk 5.000 target. Perbaikan = kelanjutan K7, bukan bagian kandidat.
- Tidak ada hosted, `main`, Cloudflare, legacy atau produksi yang disentuh.

## 3. Penerimaan auditor

Belum ada. Writer tidak memberi penerimaan independen. Mulai audit: `AUDITOR_START_P20.md`.

`independent_acceptance=false`, `installed_P21_acceptance=false`, `full_P19_acceptance=false`, `production_go=false`.
