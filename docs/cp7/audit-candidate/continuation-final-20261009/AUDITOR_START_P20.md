# Mulai audit independen P20 — CP7 kandidat lanjutan final (sesi terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Owner 8 Okt: "Audit harus memeriksa sendiri seluruh
cakupan, bukan cuma mengulang temuan penulis. Penulis tetap boleh membantu reproduksi dan perbaikan, tetapi tidak
memberi penerimaan independen." Owner 8 Okt juga memutuskan kelanjutan dikerjakan dulu lalu **diaudit sekali**; karena
itu audit ini mencakup seluruh CP7: kandidat beku `9d57b7f5` ditambah semua kelanjutan sampai kandidat ini.

## Paste block untuk membuka sesi auditor

> Kamu auditor independen P20 untuk CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang
> `claude/new-session-deapao`). Kandidat yang diaudit adalah commit sumber
> `2e605bb7d9b6b7903919b8df2be1443f1740140b`, tercatat di
> `docs/cp7/audit-candidate/continuation-final-20261009/CI_RECEIPT.json`. Audit commit itu, bukan HEAD lain; commit
> sesudahnya hanya dokumen — buktikan sendiri dengan `git diff --name-only 2e605bb7 HEAD` (semua harus di bawah `docs/`).
> Baca dulu `docs/AUDIT_PANDUAN_PRO_MAX.md` lengkap, lalu `README.md` dan `AUDITOR_START_P20.md` di folder paket itu.
> Ini audit tunggal untuk seluruh CP7: kandidat beku `9d57b7f5` (= `cp7/integration`) ditambah seluruh kelanjutan
> sampai `2e605bb7`. Periksa sendiri seluruh cakupan di `AUDITOR_START_P20.md`: susun kasus dan oracle-mu sendiri dari
> kontrak dan keputusan owner, jalankan di database sekali pakai/CI, dan laporkan temuan dengan bukti. Hasil dan uji
> writer hanya titik awal, bukan bukti lulus. Batas: jangan mengubah `main`, deployment Cloudflare, Supabase hosted
> Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push
> ke `claude/new-session-deapao` atau `cp7/integration`; jangan memasang jadwal pg_cron atau backup malam di database
> mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan meminta password/token/kunci;
> jangan melonggarkan oracle/guard; simpan log gagal pertama. Keputusan owner yang sudah disahkan tidak dibuka ulang.
> `production_go:false` tetap.

## Sumber aturan

Urutan otoritas dan aturan: `docs/AUDIT_PANDUAN_PRO_MAX.md` §0.1. Kontrak: `docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md`,
`04_BUKTI_DAN_ORACLE.md`, `06_RUSUK_KEBUTUHAN_OWNER.md`; analisis bertahap `docs/cp7/p19/P19_STAGED_5000_20261007.md`
dan versi snapshot `docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md`. Keputusan owner: `docs/cp6-d11-kebijakan-dan-gbd03.md`,
`docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`, `docs/cp7/OWNER_DECISIONS_20261008.md` (termasuk
bagian 9 Okt). Daftar kelanjutan dan statusnya: `docs/cp7/CONTINUATION_AFTER_FREEZE_20261008.md`.

## Cakupan yang wajib diperiksa sendiri

| Area | Pertanyaan audit minimal |
|---|---|
| Akses dan pemulihan | Hak diperiksa ulang setelah kunci; UUID disimpan sebelum tulis; lintas tab/rute; satu transaksi untuk koreksi/pembalikan; tidak ada jalur langsung Native yang bisa dieksekusi `authenticated` di luar fasad (termasuk skema baru `cp7_ops` dan fungsi pembersih). |
| Keuangan dan laporan | Decimal eksak; laba = pendapatan − HPP − beban; jurnal/neraca seimbang; UNKNOWN tidak menjadi 0; keuangan dimuat saat perlu dan "tidak dimuat" ≠ nol; tanggal ekonomi/WIB. |
| AP/pembelian/bahan | GRNI, invoice terlambat, kredit/retur/pembayaran tanpa hitung ganda; koreksi penerimaan/nota/pembayaran supplier; AP-5. |
| AR/penjualan | Cadangan draf sekali; retur parsial menjaga lot/HPP; koreksi harga baris yang sudah diretur. |
| Stok/HPP/produksi | Konservasi PCS/biaya; root fisik vs SKU komersial; koreksi biaya kronologis; PL-8 bukti grup habis terikat versi sumber. |
| Payroll | Kode pekerja, absensi vs upah, BS/kompensasi, saldo negatif; aturan Afui tidak dikarang. |
| Perencanaan/model | Cutoff as-known; baseline/netting/jadwal/kain/aksesori; yield tidak pernah 100%. **PL-5 B sekarang diimplementasikan** (keputusan owner 8 Okt): kebijakan berversi, 180 hari, ≥5 grup selesai, ≥200 PCS potong, produk+ukuran lalu model yang sama, Wilson satu sisi 90% dibulatkan ke bawah 0,1%, tidak lintas model; tanpa kebijakan tersimpan di aplikasi tetap PENDING; data kurang → A yang ditinjau atau UNKNOWN; bukti yang dibatalkan koreksi/pembatalan/backdate keluar dari histori. |
| Analisis 5.000 target | Kontrak §10 `P19_STAGED_5000_20261007.md`: satu acuan, paritas header+halaman ↔ analisis jalur tunggal, identity_hash, batas 8 dtk/unit dan 8.000.000 byte/halaman, 5.001 ditolak, pause/reload UUID sama, buka DONE tanpa hitung ulang. "Cek sumber" dipercepat (K7a): keluaran harus sama persis dengan sebelum percepatan. |
| Snapshot berlabel waktu (v2) | Label "data per …", status kesegaran, perubahan sejak analisis; tidak pernah disebut "terkini" bila sudah berubah; hasil snapshot tidak berubah. |
| Rencana produksi v2 | Draf boleh dari snapshot; pratinjau melaporkan dan pengesahan memaksakan pemeriksaan ulang live (produk, kebijakan, stok, WIP model+ukuran, kebutuhan, kapasitas, rencana lain, bahan, akses) dalam satu transaksi; tolak 40001 dengan angka. |
| Business Report v2 | Analisis dari snapshot; angka aktual, keuangan dan HPP dari sumber otoritatif untuk tanggal laporan dan hanya untuk yang berhak; laporan disegel sekali, revisi = versi baru. |
| Pengingat v2 | Diperiksa ulang ke data sekarang sebelum klaim dan sebelum selesai di transaksi yang sama; yang sudah beres tidak ditagih; kain ditahan bila bahan berubah sesudah analisis; pengiriman tetap pratinjau lokal. |
| Tanya AI v2 | Ringkasan berbatas berlabel waktu; tanpa keuangan kecuali yang berhak dan dari laporan keuangan ERP; tidak menulis apa pun. |
| Retensi 7 hari (K2) | Hasil disimpan 7 hari sesudah selesai; sesudahnya semua pembaca menolak dengan `CP7_ANALYSIS_RESULT_EXPIRED` dan waktunya; job yang belum selesai tidak pernah kedaluwarsa; penghapus 7 hari hanya membuang data sementara, halaman yang dipakai dokumen tetap; log tidak bisa diubah. |
| Hapus data kerja sesudah DONE (K3b, keputusan 9 Okt) | Periksa keenam syarat owner 9 Okt satu per satu: (1) yang dihapus hanya `outputs`, `target_rows`, `pair_rows`, `pair_lists`, `fragments`; hasil final, halaman, hash, waktu, asal data, indeks rencana, dokumen dan log tetap 7 hari; (2) buka ulang DONE, rencana v2, Business Report v2, pengingat v2, Tanya AI v2 tetap benar sesudah pembersihan; (3) hanya job DONE yang masih disimpan, aman diulang, ditunda selama ada analisis berjalan, gagal = tidak ada yang terhapus dan bisa dicoba lagi; hash header/halaman diperiksa terhadap isinya sebelum menghapus; (4) tidak ada uji lama yang dilonggarkan; (5) ukur sendiri ukuran simpan 5.000 target sebelum/sesudah dan bandingkan dengan `K3_SCALE_CLEANUP.json`; (6) jadwal dan backup lihat baris berikut. Pembersihan tidak pernah berjalan di dalam permintaan pengguna. |
| Jadwal server dan backup malam (CP7C) | `cp7_ops.schedules()` sama dengan deklarasi `docs/cp7/k3/K3_CLEANUP.json`; fungsi jadwal hanya bisa dijalankan peran penjadwal dan tidak terjangkau lewat HTTP; `scripts/cp7_schedule.py install` menolak tanpa `--installation-approved`; job pg_cron sungguhan di salinan sekali pakai benar-benar membersihkan lalu bisa dicopot; `scripts/cp7_nightly_backup.py`: backup dipulihkan ke database terpisah dan setiap tabel dibandingkan (jumlah baris + md5), database sementara tidak pernah sama dengan sumber, malam gagal tidak menghapus apa pun, 14 malam terverifikasi disimpan; workflow `cp7-nightly-backup.yml` tetap templat (tanpa jadwal). **Belum dipasang** di database sungguhan; itu menunggu hasil audit dan izin owner. |
| Integritas uji | Bandingkan skrip uji `976f4c43` → `2e605bb7` (`SOURCE_DELTA.json`): perubahan skrip browser (report v2, K3) tidak melemahkan pemeriksaan; log gagal pertama di `docs/cp7/evidence/` tidak diedit dan sesuai run CI yang disebut. |
| UI | Semua rute dan izin (paket beku: 48 rute, 111 izin — periksa ulang di kandidat ini); mode demo/terhubung jelas; pesan penolakan; tanpa angka palsu saat gagal muat; desktop dan HP tanpa geser samping. |
| P21 (gladi) | `scripts/cp7_p21_full_rehearsal_probe.py`: pasang/rollback/pasang ulang, pakai di-commit, backup terpakai → restore, rollback = restore pra-pasang; periksa apakah gladi memuat skema baru (`cp7_ops`, tabel `cleanups`) dan klasifikasi beda katalog benar-benar sama makna. Ini gladi, bukan pemasangan. |

## Bukti writer yang tersedia (untuk diuji ulang, bukan diterima begitu saja)

- Paket ini: `README.md`, `CI_RECEIPT.json` (15/15 workflow, 43/43 job pada `2e605bb7`), `SOURCE_DELTA.json`
  (dari `976f4c43`), `SOURCE_DELTA_FROM_FROZEN.json` (dari `9d57b7f5`), `K3_SCALE_CLEANUP.json`.
- Paket sebelumnya (tetap disimpan): `../continuation-20261008/`, `../final-20261008/`, `../staged-5000-20261008/`.
- Deklarasi suite: `docs/cp7/p19/P19_PLAN_V2.json`, `P19_REPORT_V2.json`, `P19_REMINDER_V2.json`, `P19_AI_V2.json`,
  `docs/cp7/pl5/PL5_HISTORY_YIELD.json`, `docs/cp7/k2/K2_RETENTION.json`, `docs/cp7/k3/K3_CLEANUP.json`.
- Kegagalan pertama: `docs/cp7/evidence/` — `k3-cleanup-20261009/01..03`, `report-v2-20261008/01..02`,
  `plan-v2-20261008/`, `ai-v2-20261008/`, `reminder-v2-20261008/`, `pl5-history-yield-20261008/`,
  `snapshot-v2-20261008/`, `gpt-staged-5000-20261008/`, `p21-full-20261008/`, `freeze-20261008/`.
- Lain: `docs/cp7/P20_P21_PAKET_CABANG_CLAUDE.md` §1–§15, `docs/cp7/SELF_CHECK_FORMULAS_20261006.md`.

## Batas yang sudah diketahui (bukan temuan baru, tetapi boleh diuji)

- Jadwal pembersihan, hapus 7 hari dan backup malam belum dipasang di database sungguhan; tempat simpan backup di luar
  database dipilih saat pemasangan.
- K4 (langkah analisis bertahap dijalankan server sehingga tetap lanjut saat halaman ditutup) belum dikerjakan.
- Pengiriman pengingat masih pratinjau lokal.
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

## Hasil yang diminta

1. Daftar temuan: ID, area, keparahan (blocker/major/minor), langkah reproduksi, bukti (log/run/Original), dampak ke
   angka/stok/HPP/laporan.
2. Vonis per area di tabel di atas: LULUS / GAGAL / BELUM DIPERIKSA, dengan alasan. Area yang tidak diperiksa tidak
   boleh ditulis lulus.
3. Vonis akhir kandidat dan syaratnya, termasuk apa yang harus dipenuhi sebelum owner memberi izin memasang jadwal
   pembersihan dan backup malam. Hanya auditor yang boleh menulis penerimaan independen.

Writer boleh dimintai reproduksi atau perbaikan; perbaikan writer menjadi kandidat baru yang harus diperiksa ulang.
