# Checkpoint writer ERP Hansen — kandidat 2ad56e14

VENI. VIDI. VICI. ERP. Reliable data adalah dewa.
Keuangan, laporan, stok, dan HPP adalah raja.

## Identitas dan batas

- Cabang writer: `astra/d17-14-20261020`.
- Kandidat produk: **2ad56e147a180c3fb2c433aed53cadb6a421f434**.
- Tree seluruh repo: **a640963cb5c8870da07543f1bb62aae7c17bd92e**.
- Parent: `333005edbc052cfba0d0dcdff26f72854849a4fb`.
- Kandidat auditor55c885d1 tetap beku. Tidak ada merge/deploy/hosted/Drive/WA nyata.
- `feature_complete:false`, `audit_complete:false`, `production_go:false`.
- Ini serah-terima writer dan bukti internal; paket auditor eksternal baru belum
  dinyatakan siap. OW-01 masih belum mempunyai pemeriksaan live dan sambungan
  WA untuk kebutuhan aksesori rencana; cakupan forwarding sudah diperintahkan D17-14.

Local commit dan GitHub commit berbeda metadata tetapi **tree identik**;
integrator memeriksa kesamaan sebelum memindahkan ref dengan lease, tanpa force.
Untuk mereproduksi dokumen yang menyebut commit lokal, gunakan padanan GitHub:

| Commit lokal pemeriksaan | Commit GitHub dengan tree sama |
|---|---|
| 5e4554247b5e0a8c6d71d6687d6e77e6c79989b2 | c589b8ccc72bcb866b6c14c3c4fc203c03ad29a1 |
| 155d9dc7c5104cb088a2d77b1c1d325d9fc585ac | eea4248019779799fc16747d0ed5b5c1911ba874 |
| 9d849c176a33e5a687a39dc507d2e6104c325696 | 333005edbc052cfba0d0dcdff26f72854849a4fb |
| 1df3120db8668192c203af0e289f35a88c776ccf | 2ad56e147a180c3fb2c433aed53cadb6a421f434 |

## Mulai ulang tanpa kehilangan posisi

1. Baca CLAUDE.md, docs/ERP_BEST_PRACTICES.md,
   docs/AUDIT_PANDUAN_PRO_MAX.md dan docs/erp-reliability-invariants.md.
2. Baca docs/cp7/OWNER_DECISIONS_20261008.md, docs/cp7/OPEN_WORK_D17_14_20261020.md,
   handoff D17-14 dan docs/cp7/handoff/D17_14_WRITER_PROGRESS_20261020.md. Lingkup16 butir:
   15 D17-14 plus OW-16 D17-15 sebelum OW-15; jangan mengarang nilai kebijakan.
3. Verifikasi branch/ref, tree kandidat dan pekerjaan writer lain sebelum edit.
   Perubahan kandidat2ad sudah aman di GitHub. Catatan/dev compile sesudah
   kandidat tidak mengubah produk; periksa git status, jangan reset pekerjaan.
4. Baca hasil CI **hanya yang head_sha persis2ad56e14 penuh**. Pertahankan
   kegagalan pertama, pisahkan produk/alat/lingkungan, jangan ubah expected agar hijau.

## CI kandidat ini — daftar awal4 workflow

| Run | Workflow | Expected relevan |
|---|---|---|
| 39420750723 | CP7 F04 Native Profile and Baseline Targets | 38 kasus; isian PCS, replay, clear, izin, browser |
| 39420750819 | CP7 F05 Native Frozen Analysis | 154 kasus; termasuk browser langsung dengan96+3 |
| 39420750772 | CP7 P19 Analysis Job Transport | 12 job matriks; K4=32, staged=15; termasuk publikasi laporan kedua jalur |
| 39420750724 | CP7 WA Forward | 65 kasus plus smoke; tujuh domain tambahan tetap tercakup |

Awal pemantauan: semuanya belum selesai. Hasil yang kemudian sudah dibaca:
F04 **38/38 PASS** (job118620792464), K4 **32/32 PASS** (job118620792070),
WA **65/65 PASS** (job118620792072), seluruhnya kandidat2ad, restore/advisor PASS.
Receipt lengkap masing-masing di ow03/CI_39420750723.json,
ow02/CI_39420750772.json dan ow01/CI_39420750724.json.
F05 **154/154 PASS** (job118620792620), staged **15/15 PASS**
(job118620792697), transport **15/15 PASS** (job118620792626); seluruhnya2ad,
restore/advisor PASS dan receipt lengkap di folder ow03. Ini hasil sebelum
penguatan perjalanan tunggal pada bagian follow-up alat uji di bawah.
Matriks memakai maksimal3 job sekaligus;
job skala5.000 dapat lama. Hasil akhir wajib dicatat terpisah dari daftar awal ini.
Nama job legacy `wa-forward-58`, `p19-staged12` dan `p19-transport11` bukan
jumlah kasus aktual; manifest/probe adalah pembatas yang diuji.

Job penting pada pemantauan awal: K4 `118620792070`, staged `118620792697`,
F04 `118620792464`, F05 `118620792620`, WA `118620792072`.
Jangan menyebut empat browser K4 PASS pada333 sebagai32/32 kandidat baru.

## Perubahan dan bukti yang sudah ada

OW-01 pada333: run39411967784/job118591662633 lulus65/65, restore/advisor lulus.
Receipt seluruh kasus `docs/cp7/d17-14/ow01/CI_39411967784.json`.
Ini bukti lama yang dibawa, bukan otomatis hasil2ad. Aksesori kebutuhan rencana
belum mempunyai pemeriksaan live dan sambungan WA; tidak disamarkan sebagai kebutuhan minimum.
Ulang kandidat2ad kemudian lulus65/65 juga; ini bukti runtime baru, bukan warisan333.

OW-02 pada333: run39411967722/job118591662201 **28PASS/4INCOMPLETE**.
Seluruh empat browser lulus; desktop dan HP benar-benar menutup tiga tab
laporan/pengingat/analisis, server menyelesaikan, buka ulang identitas/hash sama.
Satu pembanding keliru menuntut clock baca sama; tiga fixture mencoba mencabut
OWNER terakhir.2ad memperbaiki **alat uji**, mempertahankan seluruh fakta/hash,
izin/rollback/timeout dan Native guard. Receipt awal tersimpan di ow02.
Ulang kandidat2ad kemudian **32/32 PASS**, termasuk keempat kasus awal;
OW-02 selesai pada cakupan aplikasi, pemasangan operasional CP7C tetap HOLD.

OW-03: isian kelipatan PCS per produk/ukuran, kosong berarti belum dipilih;
legacy enam kunci tetap, nilai baru maksimal30digit sebagai string/null.
Helper exact bersama memakai sisa pembagian, hasil ASSUMED dengan rujukan.
Gap/stok/WIP/bahan/kapasitas/kesiapan tidak ditulis ulang. Saran kelipatan bukan
izin produksi atau klaim bahan cukup; rencana tetap mengikuti penjaga yang berlaku.
Tabel dan laporan menyebut saran sebelum pemeriksaan bahan/kapasitas.

Temuan401 bawaan ditemukan dan diperbaiki: tiga jalur pembacaan bertahap kini
menghapus fakta dan generasi respons ketika AUTH_REQUIRED/FORBIDDEN, sebelum
provider login menyegarkan identitas. Tiga kegagalan DOM awal disimpan.

**Bukti lokal kandidat:**125 tes unik PASS pada7 berkas (40profil,17staged,
68consumer); TypeScript PASS; AST Python, Node syntax, kepemilikan sumber/akses/CSS,
pemulihan dan keterjangkauan187 SQL PASS.165 pemeriksaan PGlite memakai penulis
profil/helper SQL asli, tetapi produk/identitas sintetis; bukan Native.
60 fungsi PL/pgSQL juga berhasil dibuat dengan row-type kosong di PGlite;
ini kompilasi tubuh, bukan perencanaan kueri Native atau bukti bisnis.

Reproduksi lokal dari checkout kandidat, setelah npm ci:

```sh
npx vitest run src/nativePlanningProfile.test.ts src/NativePlanningProfilePanel.dom.test.tsx
npx vitest run src/NativeAnalysisPanel.pages.dom.test.tsx
npx vitest run src/nativeAnalysis.test.ts src/NativeAnalysisPanel.dom.test.tsx src/NativeStagedReportsPanel.dom.test.tsx src/NativeStagedRemindersPanel.dom.test.tsx
npx tsc -b
python scripts/cp7_bundle_reachability.py
```

Untuk PGlite gunakan dependensi alat0.5.10 di luar aplikasi, tentukan
PGLITE_MODULE ke dist/index.js, lalu jalankan local-rounding-check.mjs
atau local-compile-check.mjs pada folder ow03. Opsi `--old` pada rounding
memakai333 dan mempertahankan kegagalan pertama. Rincian/log/hashes ada
di ow03/README.md dan LOCAL_RECEIPT.json.

Native **hanya salinan sekali pakai**: ikuti persis workflow tersebut,
Supabase CLI2.116.0/Postgres17.6.1.165 dan paket runtime yang dipin.
F04 menjalankan cp7_f04_baseline_probe.py; F05 menjalankan
cp7_f05_analysis_probe.py; matriks memanggil fase sesuai nama/argumen
dalam claude-p19-transport.yml. Jangan menjalankan harness ke Enteng.

## Review internal dan sisa pekerjaan

Empat pembantu GPT-6.1 Sol Max, tanpa anak dan tanpa edit produk. Penilaian awal
memakai kandidat sama sebelum bertukar kesimpulan. Temuan diselesaikan melalui
sumber atau uji; persetujuan agen tidak dihitung audit independen.
Temuan halaman0 pada browser diperbaiki dengan penelusuran rentang; expected
kualitas/kesiapan dan dua publikasi Native ditambah sesudah review.
Hasil/limit: INTERNAL_COUNTER_REVIEW_20261020.md. Tidak ada sengketa kebenaran
yang diketahui masih terbuka; runtime/performance masih perlu bukti.

Urutan berikut tetap OPEN_WORK: jalur uang, stok, HPP dan koreksi, lalu
urut/saring, perencanaan/skala, OW-16, dan paket auditor. Sumber/fixture awal
retur lunas, koreksi mandor dan HPP tersimpan di NEXT_MONEY_WORK_SOURCE_REVIEW.md;
belum ada patch produk untuk ketiganya pada2ad.
Target1/2/3detik tetap berlaku sesuai pengecualian owner bernama;125PASS lokal
bukan bukti perjalanan pengguna lengkap atau bukti5.000target memenuhi3detik.

## Follow-up alat uji tanpa perubahan produk

Perjalanan F05 desktop/HP diperkuat: UI mengisi12 pada profil kosong,
menyimpan dan memuat ulang, lalu analisis wajib memakai ID/revisi hasil
simpan tersebut untuk gap93/saran96/tambahan3. Kedua berkas alat uji saja
yang berubah, selain dokumen/bukti. Jadwal yang terikat sumber ditinjau ulang
melalui fixture Native dengan konfigurasi sama; batas ini dinyatakan jelas.
Expected lengkap dan counter-review ada pada ow03/README.md. Ini belum
hasil runtime. F05 perlu dijalankan pada commit follow-up; hasil Native
produk2ad dipakai ulang hanya dengan bukti berkas produk byte-identik.

## Hasil follow-up878 dan posisi berikutnya

Penguatan di atas kemudian **154/154 PASS** pada878e0a9c,
run39423331714/job118629536646. Receipt lengkap ow03/CI_39423331714.json;
hash SQL cocok bundle3c0364ce… dan produk identik terhadap2ad.
OW-02 dan OW-03 selesai pada kontrak aplikasi masing-masing. Kelompok1
belum seluruhnya selesai karena pemeriksaan live dan sambungan WA/aksesori rencana belum ada.

K6job118620792566 kandidat2ad gagal sebelum kualifikasi karena lingkungan
startup/registry; nol kasus produk, receipt ow03/CI_39420750772_K6_ENVIRONMENT.json.
GitHub menolak permintaan ulang satu job saat workflow masih berjalan.
Skala5.000 tetap dipantau. Semua hasil itu tidak memberikan penerimaan audit
independen, SLA, atau production_go. Pekerjaan produk berikutnya: OW-04,
kemudian OW-05/06 dan pemeriksaan HPP sesuai daftar owner.
