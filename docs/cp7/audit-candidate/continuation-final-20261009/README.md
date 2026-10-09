# Kandidat audit lanjutan CP7 (final) — 9 Okt 2026

Paket ini menggantikan kandidat lanjutan `../continuation-20261008/` (`976f4c43`) untuk **satu kali audit independen**.
Isinya: kandidat lanjutan itu ditambah keputusan owner 9 Okt (hapus data kerja sementara sesudah analisis DONE, jadwal
pembersihan, backup malam). Kandidat lanjutan lama dan kandidat beku `../final-20261008/` (`9d57b7f5` = `cp7/integration`)
**tetap disimpan dan tidak diubah**. Tidak ada push ke `cp7/integration`, `main`, deployment, atau Supabase hosted;
tidak ada jadwal atau backup yang dipasang di database sungguhan.

## Identitas kandidat

- **Commit sumber kandidat: `2e605bb7d9b6b7903919b8df2be1443f1740140b`** di cabang `claude/new-session-deapao`.
- Selisih dari kandidat lanjutan lama `976f4c43` (status, ukuran, SHA-256 sebelum dan sesudah per berkas):
  `SOURCE_DELTA.json` — 26 berkas (16 baru, 10 berubah, 0 dihapus; 16 bukan dokumen).
- Selisih dari kandidat beku `9d57b7f5`: `SOURCE_DELTA_FROM_FROZEN.json` — 141 berkas (95 baru, 46 berubah, 0 dihapus; 102 bukan dokumen).
- Commit dokumentasi sesudah `2e605bb7` tidak mengubah sumber dan tidak otomatis menerima kualifikasi CI dari `2e605bb7`.

## CI pada satu commit (`CI_RECEIPT.json`)

Ke-15 workflow kualifikasi cabang Claude (set yang sama dengan dua kandidat sebelumnya) dijalankan pada `2e605bb7`: yang
terpicu oleh push berjalan sendiri, sisanya dijalankan manual (`workflow_dispatch`) di cabang yang sama tanpa commit baru.
Hasil: **15/15 workflow dan 43/43 job sukses**; tidak ada yang gagal, dibatalkan, atau dilewati. Workflow lama
integrasi (`cp7-*.yml` yang hanya terpicu di `cp7/integration`) tidak dijalankan, karena cabang itu tidak boleh diubah.

Suite baru di workflow `CP7 P19 Analysis Job Transport`: `k3-cleanup-17` (9 Native, 4 balapan dua sesi, 2 HTTP Auth nyata,
2 browser desktop+HP). Semua suite lama (`p19-plan-v2-18`, `p19-report-v2-20`, `p19-reminder-v2-16`, `p19-ai-v2-9`,
`pl5-history-yield-20`, `k2-retention-10`, `p19-staged12`, `p19-transport11`, `p19-scale5`) tetap hijau pada commit yang sama.

## Keputusan owner 9 Okt: enam syarat dan buktinya

Sumber kutipan: `../../OWNER_DECISIONS_20261008.md` (bagian 9 Okt). Deklarasi: `../../k3/K3_CLEANUP.json`.

| Syarat owner | Penerapan | Bukti CI |
|---|---|---|
| 1. Hasil final, halaman, hash, waktu, asal data tetap 7 hari; dokumen dan bukti audit dilindungi | Yang dihapus hanya data kerja sementara (`outputs`, `target_rows`, `pair_rows`, `pair_lists`, `fragments`). Yang tetap: job (query, acuan, hash sumber, akses, waktu), unit, header, halaman, identitas halaman, tanda capture, indeks rencana (`plan_targets`, `plan_scope`, `plan_groups`), dokumen, log retensi, log pembersihan (tidak bisa diubah). Sebelum menghapus, server memeriksa ulang hash header dan setiap halaman terhadap isinya, jumlah dan ukuran halaman, hash identitas, dan indeks rencana satu baris per target; gagal periksa = tidak ada yang dihapus. | `K3C_CLEANED_ONLY_TEMPORARY`, `K3C_DOCUMENTS_AND_RETENTION_AFTER_CLEANUP` |
| 2. Business Report, rencana, pengingat, AI, buka ulang DONE tetap jalan | Semua fitur itu membaca header, halaman dan indeks rencana yang tetap; tidak ada yang membaca data kerja sementara. | `K3C_REOPEN_AFTER_CLEANUP`, `K3C_PLAN_V2_AFTER_CLEANUP`, `K3C_REPORT_V2_AFTER_CLEANUP`, `K3C_AI_AND_REMINDERS_AFTER_CLEANUP`, `K3C_HTTP_REOPEN_AFTER_CLEANUP`, `K3C_BROWSER_DESKTOP/MOBILE_REOPEN_AFTER_CLEANUP` |
| 3. Aman diulang, job belum selesai tidak disentuh, gagal = hasil tetap ada dan bisa dicoba lagi | Hanya job DONE yang masih dalam masa simpan; satu log per job (ulang = tidak berubah apa-apa); ditunda selama ada analisis yang berjalan; tunggu kunci paling lama 2 detik lalu dicoba lagi di jadwal berikutnya; semua langkah satu transaksi. | `K3C_FAILED_CLEANUP_KEEPS_RESULT_RETRIED`, `K3C_ONLY_DONE_KEPT_RUNS`, `K3C_RACE_TWO_TICKS_ONE_LOG`, `K3C_RACE_BUSY_TABLE_RETRIED` |
| 4. Uji lama boleh disesuaikan; tambah uji buka ulang sesudah pembersihan | Pembersihan hanya berjalan dari jadwal server, tidak pernah di dalam permintaan pengguna. Karena itu **tidak ada uji lama yang diubah** dan tidak ada pemeriksaan angka, kelengkapan, hash atau asal data yang dilonggarkan. Uji buka ulang sesudah pembersihan ditambahkan di Native, HTTP dan browser. | seluruh suite lama hijau pada `2e605bb7`; kasus buka ulang di baris 2 |
| 5. Ukur penyimpanan langsung pada 5.000 target sebelum dan sesudah | Diukur di CI `p19-scale5` pada `2e605bb7` dengan fungsi pembersih yang sama, ukuran simpan sesudah kompresi TOAST (`pg_column_size`). Tabel di bawah. | `p19-scale5` (`K3_SCALE_CLEANUP.json`) |
| 6. Jadwal pembersihan dan backup malam dibuat dan diuji; pemasangan menunggu audit dan izin | `cp7_ops.schedules()` (pembersihan tiap 5 menit, hapus 7 hari tiap 02:30 WIB) hanya bisa dijalankan peran penjadwal; `scripts/cp7_schedule.py` memasang/memeriksa/mencopot jadwal pg_cron dan **menolak memasang** tanpa `--installation-approved`; `scripts/cp7_nightly_backup.py` membuat backup penuh, memulihkannya ke database terpisah, membandingkan setiap tabel (jumlah baris dan md5), menyimpan 14 malam terverifikasi. Workflow `cp7-nightly-backup.yml` hanya templat, tidak terjadwal. | `K3C_SCHEDULE_DEFINED_PRIVATE`, `K3C_RACE_PG_CRON_FIRES` (job pg_cron sungguhan di salinan uji, lalu dicopot), `K3C_RACE_NIGHTLY_BACKUP_VERIFIED`, `K3C_HTTP_TICK_NOT_REACHABLE` |

## Ukuran simpan terukur (syarat 5)

Satu analisis bertahap, aplikasi penuh di CI, sebelum dan sesudah pembersihan (byte sesudah kompresi TOAST;
1 MB = 1.000.000 byte). Halaman hasil tidak berubah (indeks, ukuran dan hash halaman sama sebelum dan sesudah).

| Target | Riwayat | Halaman | Sebelum | Sesudah | Hemat | Waktu pembersihan | Halaman tetap sama |
|---|---|---|---|---|---|---|---|
| 100 | 1 hari | 1 | 2,53 MB | 0,57 MB | 1,97 MB (78%) | 0,01 dtk | ya |
| 100 | 30 hari | 1 | 2,54 MB | 0,57 MB | 1,97 MB (78%) | 0,01 dtk | ya |
| 100 | 100 hari | 1 | 2,58 MB | 0,57 MB | 2,01 MB (78%) | 0,02 dtk | ya |
| 300 | 1 hari | 2 | 7,67 MB | 1,75 MB | 5,92 MB (77%) | 0,02 dtk | ya |
| 300 | 30 hari | 2 | 7,71 MB | 1,75 MB | 5,96 MB (77%) | 0,02 dtk | ya |
| 300 | 100 hari | 2 | 7,81 MB | 1,75 MB | 6,07 MB (78%) | 0,02 dtk | ya |
| 1.000 | 1 hari | 6 | 26,04 MB | 6,03 MB | 20,01 MB (77%) | 0,07 dtk | ya |
| 1.000 | 30 hari | 6 | 26,21 MB | 6,03 MB | 20,18 MB (77%) | 0,05 dtk | ya |
| 1.000 | 100 hari | 6 | 26,57 MB | 6,03 MB | 20,54 MB (77%) | 0,05 dtk | ya |
| 5.000 | 1 hari | 26 | 126,12 MB | 31,14 MB | 94,97 MB (75%) | 1,05 dtk | ya |
| 5.000 | 30 hari | 26 | 127,11 MB | 31,14 MB | 95,97 MB (76%) | 0,31 dtk | ya |
| 5.000 | 100 hari | 26 | 128,90 MB | 31,14 MB | 97,76 MB (76%) | 0,91 dtk | ya |

Perkiraan sebelumnya (±125 MB per run 5.000 target, ±100 MB di antaranya data antara) sekarang **terukur**: pada 5.000 target satu run tersimpan 126,12 MB–128,90 MB sebelum pembersihan dan 31,14 MB sesudahnya; yang dihemat 94,97 MB–97,76 MB per run.

## Kegagalan pertama yang disimpan (tidak diedit)

- `../../evidence/k3-cleanup-20261009/01` — pemeriksaan batas CP6 menolak perubahan `.gitignore` CP5 yang dibekukan
  (kesalahan penulis; baris dikembalikan, pemeriksaan tidak diubah).
- `../../evidence/k3-cleanup-20261009/02` — run pertama `k3-cleanup-17`: 15/17 lulus; dua kasus browser salah skrip
  (panel sudah membuka hasil terakhir sendiri, skrip masih menekan tombol yang sudah hilang).
- `../../evidence/k3-cleanup-20261009/03` — run kedua `k3-cleanup-17`: buka ulang sesudah pembersihan lulus di desktop dan
  HP; satu langkah kemudian skrip memilih gudang sebelum pilihan rencana dimuat (urutan salah skrip).
- `../../evidence/report-v2-20261008/02` — `p19-report-v2-20` HP: skrip membaca jawaban server sebelum tercatat.
- Bukti kandidat sebelumnya tetap: `plan-v2-20261008/`, `report-v2-20261008/01`, `ai-v2-20261008/`,
  `reminder-v2-20261008/`, `pl5-history-yield-20261008/`, `snapshot-v2-20261008/`.

Putaran ini tidak menemukan cacat produk. Tidak ada oracle atau guard lama yang dilonggarkan.

## Pilihan bawaan yang dipakai (bisa diubah, bukan keputusan baru owner)

- Pembersihan berjalan tiap 5 menit dan menunda diri selama ada analisis yang bergerak dalam 10 menit terakhir.
- Hapus hasil kedaluwarsa (7 hari, keputusan 8 Okt) tiap hari 02:30 WIB.
- Backup malam 01:00 WIB, simpan 14 malam terakhir yang terbukti bisa dipulihkan; tempat simpan backup di luar database
  ditentukan saat pemasangan.

## Belum selesai / di luar kandidat

- Pemasangan jadwal pembersihan, hapus 7 hari dan backup malam di database sungguhan: menunggu hasil audit dan izin
  pemasangan dari owner.
- K4: penjalan server untuk langkah analisis bertahap (job tetap lanjut saat halaman ditutup) — belum dikerjakan.
- Audit independen P20 atas kandidat ini; `independent_acceptance=false`, `installed_P21_acceptance=false`,
  `production_go=false`. Hosted Enteng dan ERP lama tidak disentuh.
