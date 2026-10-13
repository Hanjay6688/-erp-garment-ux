# Diagnosis selisih pemeriksaan akhir grup — `CP7 Supplier Payment Create`

Permintaan owner, 13 Okt 2026 (instruksi ke penulis no. 1): "Tambahkan diagnosis selisih pemeriksaan akhir, lalu
jalankan workflow bayar supplier tiga kali pada tree yang sama. Laporkan SHA/tree, seluruh hasil termasuk kegagalan,
dan akar penyebabnya. Tiga run hijau saja belum menjelaskan penyebab kegagalan sebelumnya."

**Status: OPEN.** Akar penyebab dua kegagalan (run 38288829388 dan 38330557862) **belum ditemukan**. Dokumen ini
mencatat apa yang sudah dibuktikan, apa yang sudah disingkirkan, dan apa yang terpasang supaya kegagalan berikutnya
langsung menyebut bagian yang berbeda.

## 1. Diagnosis yang ditambahkan (`5b8e9d74`)

`scripts/cp6_auditor_runner.py`. Pembanding tidak diubah: `full_boundary_restored`, `public_schema_unchanged` dan
`complete_boundary_restored` masih dihitung dengan persamaan yang sama.

- `state_difference(...)`: kalau pembanding gagal, laporan dan log menyebut bagian yang berbeda. Isinya tabel `erp`,
  `platform`, `auth`, ACL skema, relasi/fungsi/baris `public`. Untuk daftar fungsi, yang dibedakan adalah
  `ORDER_ONLY` (urutan saja) dan `CONTENT` (isi), dan anggota yang bergeser ikut disebut.
- `catalog_observation(...)`: rencana kueri daftar fungsi dan statistik `pg_proc`/`pg_namespace` di awal dan akhir
  grup. Diambil di dalam savepoint sendiri, jadi kegagalan membaca tidak mengubah apa pun.
- Per kasus: `boundary_difference` ditulis hanya kalau kasus itu tidak memulihkan batasnya.
- Akhir grup: `group_end_difference` ditulis, plus satu baris JSON di log yang memuat `group_end_difference`,
  `catalog_observation_start` dan `catalog_observation_end`, kalau `complete_boundary_restored` salah.
- Uji: `scripts/cp6_auditor_runner_difference_test.py` (5 kasus) di workflow Shell S0.

Selisih tree `7a0b4a90` (`05d4ccd8`) → `5b8e9d74` (`793863ec`) di luar `docs/` hanya tiga berkas:
`scripts/cp6_auditor_runner.py`, `scripts/cp6_auditor_runner_difference_test.py`, dan satu baris di
`.github/workflows/claude-p08-shell.yml`. `supabase/`, `src/` dan `scripts/cp7-src/` tidak berubah. Bundel produk yang
dipasang workflow sama di semua run: `source_sha256` `d64ae6edbd881b5e915647d98138c3b206c25d3fc318044546ba20d7175daa79`.

## 2. Seluruh hasil, termasuk kegagalan

Kecepatan mesin diukur sebagai lama pemasangan paket T3 AS→BF di log yang sama (detik).

| Run / job | Commit (tree) | Native 4 | Race 3 | HTTP 1 | Browser 2 | Akhir grup native | Hasil | AS→BF | Log |
|---|---|---|---|---|---|---|---|---|---|
| 38288829388 / 114943655473 | `7a0b4a90` (`05d4ccd8`) | 4 PASS | 3 PASS | 1 PASS | 2 PASS | **tidak sama** | **INCOMPLETE** | 8,4 | `01_…FIRST_FAILURE.log` |
| 38330557862 / 115079091992 | `5656f072` (`99cca813`, beda dari `7a0b4a90` hanya `docs/`) | 4 PASS | 3 PASS | 1 PASS | 2 PASS | **tidak sama** | **INCOMPLETE** | 8,5 | `02_…SECOND_FAILURE.log` |
| 38355471648 / 115157221861 | `5b8e9d74` (`793863ec`) | 4 PASS | 3 PASS | 1 PASS | 2 PASS | sama | PASS 10/10 | 12,1 | `03_….log` |
| 38355474078 / 115157230584 | `5b8e9d74` (`793863ec`) | 4 PASS | 3 PASS | 1 PASS | 2 PASS | sama | PASS 10/10 | 12,0 | `04_….log` |
| 38355476526 / 115157239535 | `5b8e9d74` (`793863ec`) | 4 PASS | 3 PASS | 1 PASS | 2 PASS | sama | PASS 10/10 | 12,1 | `05_….log` |

Kedua kegagalan punya pola yang sama: semua kasus PASS, setiap kasus memulihkan batasnya sendiri, dan yang tidak sama
hanya perbandingan awal grup dengan akhir grup (sesudah rollback). Waktu itu runner belum mencatat bagian mana yang
berbeda. Karena itu, untuk kedua run ini bagian yang berbeda tidak bisa direkonstruksi dan tidak ditebak di sini.

## 3. Uji ulang grup native (diagnosis saja)

Workflow `CP7 Supplier Payment Group-End Diagnosis`, run 38357098820 (commit `0fe350b3`), 3 job. Setiap job memakai
pemasangan yang sama dengan workflow kualifikasi, lalu grup native diulang 20 kali. Di setiap pembacaan `public_state`,
alat `scripts/cp7_group_end_repeat_diagnosis.py` juga mencatat lokasi baris setiap fungsi `public` (`ctid`, `xmin`) di
transaksi yang sama. Race, HTTP dan browser tidak dijalankan, sehingga gerbang T3 di job ini merah sesuai rancangan
(`writer_runtime`). Ringkasan lengkapnya ada di `06_group_end_repeat_diagnosis_run38357098820.json`.

| Hasil | Jumlah |
|---|---|
| Grup dijalankan | 60 (3 × 20) |
| Akhir grup sama dengan awal | 60 |
| Urutan baca daftar fungsi berubah | 0 |
| Baris fungsi berpindah lokasi | 0 |
| `autoanalyze` `pg_proc` terjadi di tengah grup | 2 grup (job 1 dan job 3, pengulangan ke-6), keduanya tetap sama |
| Rencana kueri daftar fungsi | satu bentuk saja: `Hash Join`, `Seq Scan pg_proc` |
| Ukuran `pg_proc` | sekitar 3,4 MB, di bawah ambang pemindaian paralel 8 MB |

Ketiga job ini jalan di mesin yang lebih lambat (AS→BF 12,0–12,5 detik).

## 4. Yang sudah disingkirkan

1. **Perubahan kode.** Bundel produk sama di semua run (`d64ae6ed…`). Di antara alat yang dimuat probe, satu-satunya
   yang berubah antara `5f1506f4` dan `7a0b4a90` adalah `scripts/cp6_auditor_business_day.py`, dan perubahannya hanya
   anotasi GitHub yang tidak dipanggil di run ini karena tanggal tidak berganti. Run 38195132560 (`5f1506f4`) lulus di
   mesin cepat (AS→BF 6,4 detik) dengan bundel yang sama.
2. **Analisis statistik otomatis (`autoanalyze`) yang mengubah rencana kueri.** Terjadi di tengah dua grup, dan
   rencana serta urutan tetap sama. Dugaan awal penulis di sini **tidak terbukti**.
3. **Pemindaian paralel `pg_proc`.** Tabel di bawah ambang 8 MB dan rencana yang terlihat tidak paralel.
4. **Baris fungsi berpindah di tengah grup.** Tidak terjadi dalam 60 grup.

Masih terbuka: kecepatan mesin. Kedua kegagalan jatuh di mesin cepat (8,4–8,5 detik), dan semua run hijau di bagian 2
dan 3 jalan di mesin lambat. Ini korelasi, bukan bukti, karena run 38195132560 juga di mesin cepat dan tetap lulus.

## 5. Kelemahan alat yang tetap benar, apa pun penyebabnya

`PUBLIC_STATE` di runner membentuk daftar fungsi dengan `jsonb_agg(... order by 1)`. Angka `1` di dalam agregat adalah
konstanta, sehingga urutan daftar mengikuti urutan fisik baris `pg_proc`. Ini sudah tercatat sebagai CAT-01
(`docs/cp7/CATALOG_COMPARISON_FINDING_20261006.md`), dan suite F03/F04/F05 membandingkan dengan `exact_public_catalog`
(daftar diurutkan, setiap anggota dan hash tetap dibandingkan). Grup bayar supplier belum memakai pembanding itu.
Dalam 63 grup di atas urutannya tidak pernah berubah, jadi **belum ada bukti** bahwa kelemahan ini penyebab dua
kegagalan tersebut.

## 6. Langkah berikutnya

- Diagnosis tetap terpasang di runner kualifikasi. Kalau kegagalan terjadi lagi, baris `group_end_difference` di log
  langsung menyebut bagian yang berbeda.
- Workflow kualifikasi dijalankan 6 kali lagi untuk memperbesar peluang mendapat mesin cepat (bagian 7).
- Perubahan pembanding (misalnya memakai `exact_public_catalog` di grup ini) **tidak** dilakukan tanpa izin owner,
  karena itu mengubah oracle. Penulis baru akan mengusulkannya kalau bukti menunjukkan selisihnya memang hanya urutan.

## 7. Run tambahan (diagnosis terpasang)

Diisi setelah selesai.
