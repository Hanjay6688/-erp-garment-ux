# Mulai audit penuh CP7 (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Owner 11 Okt: "Ya selesain semua abis tu full audit cp7."
Owner 8 Okt: "Audit harus memeriksa sendiri seluruh cakupan, bukan cuma mengulang temuan penulis. Penulis tetap boleh
membantu reproduksi dan perbaikan, tetapi tidak memberi penerimaan independen." Audit ini mencakup seluruh CP7: kandidat
beku `9d57b7f5` ditambah semua kelanjutan sampai kandidat ini. Putusan audit sebelumnya (Astra P20, Sol P20+K4, uji ulang
Sol) adalah masukan, bukan penerimaan audit ini.

## Paste block untuk membuka sesi auditor

> Kamu auditor independen untuk audit penuh CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang
> `claude/new-session-deapao`). Kandidat yang diaudit adalah commit sumber `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`
> (tree `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41`), tercatat di
> `docs/cp7/audit-candidate/cp7-full-20261011/CI_RECEIPT.json`. Audit commit itu, bukan HEAD lain; commit sesudahnya
> hanya dokumen — buktikan sendiri dengan `git diff --name-only d0b9e9c2 HEAD` (semua harus di bawah `docs/`). Baca dulu
> `docs/AUDIT_PANDUAN_PRO_MAX.md` lengkap, lalu `README.md` dan `AUDITOR_START.md` di folder paket itu, lalu laporan audit
> sebelumnya: `audit/astra-p20-2e605bb7-20261009` (`audit/astra_p20/REPORT.md`, `WRITER_HANDOFF.md`),
> `audit/sol-p20-k4-8cc1b081-20261009` (`audit/sol_p20_k4/REPORT.md`, `WRITER_HANDOFF.md`, `FINDINGS.json`) dan
> `audit/sol-k4-retest-8116800c-20261010`. Ini audit tunggal untuk seluruh CP7: periksa sendiri seluruh cakupan di
> `AUDITOR_START.md`, susun kasus dan oracle-mu sendiri dari kontrak dan keputusan owner, jalankan di database sekali
> pakai/CI, dan laporkan temuan dengan bukti. Hasil dan uji writer hanya titik awal, bukan bukti lulus. Batas: jangan
> mengubah `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
> (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao`, `cp7/integration` atau
> cabang audit lama (pakai cabang audit baru); jangan memasang jadwal pg_cron atau backup malam di database mana pun selain
> salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan meminta password/token/kunci; jangan melonggarkan
> oracle/guard; simpan log gagal pertama. Keputusan owner yang sudah disahkan tidak dibuka ulang. Area optimasi timeline
> PR44 tidak boleh diterima oleh auditor yang menulisnya. `production_go:false` tetap.

## Sumber aturan

Urutan otoritas: `docs/AUDIT_PANDUAN_PRO_MAX.md` §0.1. Kontrak: `docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md`
(§2 cakupan A–G, BR, Reminder, Integrasi), `04_BUKTI_DAN_ORACLE.md`, `06_RUSUK_KEBUTUHAN_OWNER.md`; analisis bertahap
`docs/cp7/p19/P19_STAGED_5000_20261007.md` dan `P19_STAGED_SNAPSHOT_V2.md`. Keputusan owner:
`docs/cp6-d11-kebijakan-dan-gbd03.md`, `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`,
`docs/cp7/OWNER_DECISIONS_20261008.md` (termasuk bagian 9 Okt). Daftar kelanjutan dan statusnya:
`docs/cp7/CONTINUATION_AFTER_FREEZE_20261008.md`. Deklarasi suite: `docs/cp7/p19/*.json`, `docs/cp7/pl5/`, `k2/`, `k3/`,
`k4/`, `k6/`.

## Cakupan yang wajib diperiksa sendiri

| Area | Pertanyaan audit minimal |
|---|---|
| Akses dan pemulihan | Hak diperiksa ulang setelah kunci; UUID disimpan sebelum tulis; lintas tab/rute; satu transaksi untuk koreksi/pembalikan; tidak ada jalur langsung Native yang bisa dijalankan `authenticated`/`service_role` di luar fasad (termasuk skema `cp7_ops`, `cp7_analysis_stage`, `cp7_proof_runner` dan fungsi pembersih). |
| Keuangan dan laporan | Decimal eksak; laba = pendapatan − HPP − beban; jurnal/neraca seimbang; UNKNOWN tidak menjadi 0; keuangan dimuat saat perlu dan "tidak dimuat" ≠ nol; tanggal ekonomi/WIB. |
| AP/pembelian/bahan | GRNI, invoice terlambat, kredit/retur/pembayaran tanpa hitung ganda; koreksi penerimaan/nota/pembayaran supplier; bayar supplier dari aplikasi; AP-5. |
| AR/penjualan | Cadangan draf sekali; retur parsial menjaga lot/HPP; koreksi harga baris yang sudah diretur. |
| Stok/HPP/produksi | Konservasi PCS/biaya; root fisik vs SKU komersial; koreksi biaya kronologis; bukti fisik kain P08; PL-8 bukti grup habis terikat versi sumber. |
| Payroll | Kode pekerja, absensi vs upah, BS/kompensasi, saldo negatif; aturan yang belum diputuskan tidak dikarang. |
| Perencanaan/model | Cutoff as-known; baseline/netting/jadwal/kain/aksesori; yield tidak pernah 100%; PL-5 B: kebijakan berversi, 180 hari, ≥5 grup selesai, ≥200 PCS potong, produk+ukuran lalu model yang sama, Wilson satu sisi 90% dibulatkan ke bawah 0,1%, tidak lintas model; tanpa kebijakan tersimpan tetap PENDING; data kurang → A yang ditinjau atau UNKNOWN. |
| Rencana v1/v2 (F01) | Satu kunci kapasitas untuk pengesahan v1 dan v2: dua pengesahan bersamaan tidak pernah melewati kapasitas (61 dari 60). |
| Analisis 5.000 target | Satu acuan, paritas header+halaman ↔ jalur tunggal, identity_hash, batas 8 dtk/unit dan 8.000.000 byte/halaman, 5.001 ditolak, jeda/muat ulang UUID sama, buka DONE tanpa hitung ulang; "Cek sumber" dipercepat (K7a) dengan keluaran sama persis. |
| Snapshot berlabel waktu (v2) | Label "data per …", status kesegaran, perubahan sejak analisis; tidak pernah disebut "terkini" bila sudah berubah. |
| Rencana v2, Business Report v2, pengingat v2, Tanya AI v2 | Seperti kontrak v2 §3–§6: pengesahan memeriksa ulang live dalam satu transaksi; laporan disegel sekali, keuangan/HPP dari sumber otoritatif dan hanya untuk yang berhak; pengingat diperiksa ulang sebelum klaim dan sebelum selesai; AI berbatas, berlabel waktu, tidak menulis. |
| Retensi 7 hari (K2) dan hapus data kerja sesudah DONE (K3b) | Seperti `AUDITOR_START_P20.md` paket `../continuation-final-20261009/` (enam syarat owner 9 Okt), diperiksa ulang pada kandidat ini; ukur sendiri penyimpanan 5.000 target sebelum/sesudah. |
| K4 penjalan analisis di server | Job selesai tanpa halaman dan hasilnya sama persis dengan jalur halaman; halaman dan server (atau dua giliran) tidak pernah menjalankan/menyimpan unit yang sama; buka ulang = UUID, job dan run yang sama; batas 8 dtk wajib; hak aktor diperiksa ulang tiap unit tanpa sesi login; job yang ditolak tidak menahan job lain; giliran kedua tidak pernah menunggu (SOL-K4-01, termasuk saat pertama kali); tidak terjangkau HTTP; layar menyebut "boleh ditutup" hanya bila penjalan aktif. Deklarasi `docs/cp7/k4/K4_RUNNER.json`. |
| K6 penjalan bukti PL-8 di server | Bukti hanya lewat pembukti yang tidak diubah (`cp7_supply_native.prove_exhausted`), terikat `facts_hash` dan `kernel_version`; sesudah pembatalan, koreksi atau backdate bukti lama tidak dipakai dan grup dibuktikan ulang oleh server; penjalan tidak pernah menghapus/mengubah bukti atau memutus grup sendiri; batas 8 dtk wajib; jendela terhenti tidak menyimpan apa pun, dibagi dua sampai 50, lalu dilewati dan dicatat; satu giliran pada satu waktu tanpa menunggu (BUSY); capture bersamaan tetap benar; istirahat 1 jam antar putaran; tidak terjangkau HTTP; capture publik memakai bukti server. Deklarasi `docs/cp7/k6/K6_PROOF_RUNNER.json`. |
| Jadwal server dan backup malam (F02, F03) | `cp7_ops.schedules()` (empat entri) sama dengan deklarasi `docs/cp7/k3/K3_CLEANUP.json`; nama job pg_cron tidak bertabrakan lintas database; fungsi jadwal hanya bisa dijalankan peran penjadwal; `scripts/cp7_schedule.py install` menolak tanpa `--installation-approved`; `scripts/cp7_nightly_backup.py` memulihkan ke database terpisah dan membandingkan setiap tabel, receipt tidak tertimpa, malam gagal tidak menghapus apa pun. **Belum dipasang.** |
| Integritas uji (F04, F05, alat uji) | Detektor dan gate bukti (`scripts/cp7_f05_analysis_probe.py`) membaca semua flag; kontrol pergantian hari tidak bisa mengubah FAIL menjadi PASS dan tidak mengulang kelompok yang gagal karena hal lain; batas waktu kasus browser tidak mengubah assertion; log gagal pertama di `docs/cp7/evidence/` tidak diedit dan sesuai run CI yang disebut. |
| UI | Semua rute dan izin; mode demo/terhubung jelas; pesan penolakan; tanpa angka palsu saat gagal muat; desktop dan HP tanpa geser samping. PR #45 bukan bagian kandidat ini. |
| P21 (gladi) | `scripts/cp7_p21_full_rehearsal_probe.py`: pasang/rollback/pasang ulang, backup terpakai → restore, rollback = restore pra-pasang; apakah gladi memuat skema baru (`cp7_ops`, `cp7_proof_runner`). Ini gladi, bukan pemasangan. |

## Bukti writer yang tersedia (untuk diuji ulang, bukan diterima begitu saja)

- Paket ini: `README.md`, `CI_RECEIPT.json`, `SOURCE_DELTA.json` (dari `8116800c`), `SOURCE_DELTA_FROM_P20.json` (dari
  `2e605bb7`), `SOURCE_DELTA_FROM_FROZEN.json` (dari `9d57b7f5`).
- Paket sebelumnya (tetap disimpan): `../sol-retest-k4-20261009/`, `../final-p20-k4-20261009/`, `../revision-p20-20261009/`,
  `../continuation-final-20261009/`, `../continuation-20261008/`, `../final-20261008/`, `../staged-5000-20261008/`.
- Kegagalan pertama: `docs/cp7/evidence/` — termasuk `business-day-control-20261011/01..02` (K4 browser mobile diam),
  `sol-p20-k4-20261009/`, `p20-audit-20261009/`, `k3-cleanup-20261009/`, `report-v2-20261008/`, `freeze-20261008/`.
- Lain: `docs/cp7/P20_P21_PAKET_CABANG_CLAUDE.md`, `docs/cp7/SELF_CHECK_FORMULAS_20261006.md`.

## Hasil yang diminta

1. Daftar temuan: ID, area, keparahan (blocker/major/minor), langkah reproduksi, bukti (log/run/Original), dampak ke
   angka/stok/HPP/laporan.
2. Vonis per area di tabel di atas: LULUS / GAGAL / BELUM DIPERIKSA, dengan alasan. Area yang tidak diperiksa tidak boleh
   ditulis lulus.
3. Vonis akhir CP7 dan syaratnya, termasuk apa yang harus dipenuhi sebelum owner memberi izin memasang jadwal (pembersihan,
   hapus 7 hari, penjalan analisis, penjalan bukti) dan backup malam. Hanya auditor yang boleh menulis penerimaan
   independen.

Writer boleh dimintai reproduksi atau perbaikan; perbaikan writer menjadi kandidat baru yang harus diperiksa ulang.
