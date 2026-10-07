# P19 — skala aplikasi penuh (sumber Native nyata, Auth nyata, klik sampai tampil)

Status: bukti penulis di cabang `claude/new-session-deapao`; bukan audit independen. `full_P19_acceptance=false`, `production_go=false`. Tidak ada batas yang dinaikkan dan tidak ada data yang dicuplik/dipotong (`limits_raised=false`, `data_sampled_or_truncated=false`). Bukti di sini berjenis `FULL_APPLICATION_NATIVE`; benchmark kernel (`P19_KERNEL_JOB_TRANSPORT_CLAUDE.md`, job Shell `p19-assembly`) **tidak** dipakai sebagai bukti aplikasi.

Suite: `p19-scale5` di workflow `claude-p19-transport.yml` (deklarasi `P19_SCALE.json`, kasus `cp7_p19_scale_cases.py`, browser `cp7_p19_scale_browser.mjs`). Target diisi hanya lewat writer biasa (importer BB, draf/posting penjualan, perintah profil/SKU/kebijakan/kalender publik); waktu pengisian dicatat terpisah dari latensi.

## 1. Run pertama — 37560925773 (head `20da4de4`)

- **Kegagalan pertama (fixture):** batch BB kedua ditolak `brands_brand_name_key` karena semua batch memakai nama merek yang sama. Tangga SQL native dan browser 300/1000/5000 berhenti di pengisian. Diperbaiki di `3eafa83e` (nama master memuat kode batch); aturan ukur/oracle tidak berubah.
- **Ukuran 100 target (98 diisi + 2 yang sudah ada), browser desktop, login Auth nyata — PASS:**

| Riwayat | Tombol | Klik → status pertama | Klik → "Sedang dihitung" | Klik → progres segmen | Klik → hasil tampil | Original |
|---|---|---|---|---|---|---|
| 1 hari | Ambil analisis | 5,2 ms | 3.003 ms | — | **7.742 ms** | 4.203.290 byte |
| 1 hari | Hitung di latar belakang | 4,0 ms | 31,6 ms | 7.609 ms | **8.014 ms** | 3 segmen |
| 30 hari | Ambil analisis | 5,5 ms | 3.003 ms | — | **7.749 ms** | 4.203.448 byte |
| 30 hari | Latar belakang | 5,6 ms | 21,2 ms | 7.584 ms | **7.968 ms** | 3 segmen |
| 100 hari | Ambil analisis | 7,2 ms | 3.003 ms | — | **8.198 ms** | 4.203.547 byte |
| 100 hari | Latar belakang | 5,3 ms | 26,7 ms | 9.558 ms | **9.944 ms** | 3 segmen |

Penilaian terhadap target owner: tanda terima pertama < 1 dtk **terpenuhi**; hasil lengkap ≤ 3 dtk **tidak terpenuhi** (7,7–9,9 dtk). Pada mode latar belakang status "Sedang dihitung sejak jam …" tampil dalam ≤ 32 ms, tetapi job sisi server butuh ±7,5 dtk — sudah dekat batas 8 dtk per request pada **100** target. Pembanding lama (fixture 12 factset): capture backend 940 ms, body 659 KB.

**Kesimpulan sementara:** biaya capture analisis aplikasi penuh ±65–75 ms dan ±42 KB per target. Dengan batas 8 dtk yang tidak diubah dan tanpa worker di luar request, ±100 target adalah kisaran yang masih muat; 300 target diperkirakan berhenti di 8 dtk, dan 5.000 target ditolak oleh batas 1.000 produk per capture. Run berikutnya mengukur 300/1000/5000 dan profil per fase sisi server untuk menamai langkah yang lambat.

## 2. Run ketiga — 37565310513 (head `eb2e0927`; run kedua 37564127281 di `3eafa83e` gagal dengan pola yang sama)

Browser desktop, login Auth nyata, data diisi lewat writer biasa (waktu isi: 100 → 4,1 dtk; 300 → 9,1 dtk; 1000 → 37,9 dtk; tidak termasuk latensi):

| Target | Riwayat | Klik → status pertama | Klik → hasil/penolakan tampil | Keadaan |
|---|---|---|---|---|
| 100 | 1 / 30 / 100 hari | 4,1–5,2 ms | **5.267–5.940 ms** (ambil 5,3–5,6 dtk; latar belakang 5,5–5,9 dtk) | hasil lengkap, Original ±4,2 MB, 3 segmen |
| 300 | 1 / 30 / 100 hari | 2,8–4,8 ms | **8.031–8.061 ms** | **ditolak jujur di batas 8 dtk** (`HONEST_CAP_REFUSAL`) |
| 1000 | 1 / 30 / 100 hari | 4,1–6,5 ms | **8.022–8.063 ms** | **ditolak jujur di batas 8 dtk** |
| 5000 | — | — | — | belum terukur: pengisian gagal (lihat bawah) |

Status "Sedang dihitung sejak jam …" pada mode latar belakang tampil dalam 18–37 ms di semua ukuran. Tanda terima pertama < 1 dtk terpenuhi; hasil lengkap ≤ 3 dtk **tidak** terpenuhi bahkan di 100 target.

**Kegagalan harness yang dicatat (bukan perilaku aplikasi):** tangga SQL native dan pengisian 5.000 target berhenti dengan `out of shared memory / max_locks_per_transaction`. Penyebab: fixture memanggil ribuan writer (setiap writer CP7 mengambil `pg_advisory_xact_lock` per request) dalam **satu** transaksi, sedangkan aplikasi nyata menjalankan satu RPC per transaksi. Perbaikan: commit per halaman writer dan tangga SQL + profil fase dijalankan pada salinan ter-commit per ukuran. Setelan lock dan batas aplikasi **tidak** diubah. Kode penolakan sisi server 300/1000 tercatat di dalam `verdict` setiap klik: capture biasa → SQLSTATE `57014` dari `erp_cp7_capture_analysis_v1`; mode latar belakang → `CP7_ANALYSIS_JOB_STOPPED` (SQLSTATE 57014) dari `erp_cp7_run_analysis_job_v1`; batas `STATEMENT_TIMEOUT_8S`. Kini juga ditulis di tingkat atas witness.

**Kesimpulan saat ini:** pada batas 8 dtk yang tidak diubah dan tanpa worker di luar request, alur aplikasi penuh menghasilkan analisis untuk ±100 target; 300 dan 1000 target ditolak jujur di 8 dtk. Langkah yang dominan sedang diukur dengan profil fase. Perbaikan kernel yang sudah masuk sesudah head run ini (PL-8 normalisasi `b001bf4f`, netting `083c90e3`) dan yang sedang dikerjakan (`allocate`) diukur ulang di run berikutnya.


## 3. Run keempat — 37568797220 (head `a634296e`): harness commit per writer, 5.000 target terukur

Suite `p19-scale5` **PASS** (5/5 kasus, `cp6_restored=true`, `advisor_gate=true`). Head ini sudah memuat PL-8 normalisasi (`b001bf4f`) dan netting linear (`083c90e3`), **belum** memuat alokasi linear (`9e3394e3`) dan baseline linear (`2c6884ea`). Data diisi lewat writer biasa, satu RPC per transaksi seperti aplikasi (waktu isi, bukan latensi: 100 → 3,2 dtk; 300 → 7,4 dtk; 1000 → 29,6 dtk; **5000 → 140,3 dtk**). Batas tidak dinaikkan dan data tidak dipotong.

**Browser desktop, login Auth nyata (klik sampai tampil):**

| Target | Riwayat | Ambil analisis (biasa) | Hitung di latar belakang: status → progres segmen → hasil | Sisi server (tangga SQL) |
|---|---|---|---|---|
| 100 | 1 hari | **4.416 ms**, hasil lengkap | 19 ms → 4.295 ms → **4.554 ms** | biasa 3.931 ms; job 2.426 ms |
| 100 | 30 hari | **4.358 ms** | 18 ms → 4.251 ms → **4.499 ms** | biasa 3.894 ms; job 2.524 ms |
| 100 | 100 hari | **4.688 ms** | 19 ms → 4.662 ms → **4.927 ms** | biasa 4.167 ms; job 2.701 ms |
| 300 | 1 hari | ditolak jujur 8.030 ms (57014) | 20 ms → 11.008 ms → **11.820 ms, hasil lengkap** (Original 12,5 MB) | biasa ditolak 8 dtk; job 6.288 ms |
| 300 | 30 hari | ditolak jujur 8.032 ms | 18 ms → 10.765 ms → **11.505 ms, hasil lengkap** | biasa ditolak; job 6.708 ms |
| 300 | 100 hari | ditolak jujur 8.032 ms | 17 ms → ditolak jujur 8.046 ms | biasa ditolak; job 7.769 ms (selesai di tangga SQL, di browser lewat 8 dtk) |
| 1000 | 1 / 30 / 100 hari | ditolak jujur 8.029–8.032 ms | 19–37 ms → ditolak jujur 8.037–8.052 ms | semua ditolak 8 dtk; 101 hari juga kena `HISTORY_GRID_100000` |
| 5000 | 1 / 30 / 100 hari | ditolak jujur 8.029–8.030 ms | 22–31 ms → ditolak jujur 8.045–8.063 ms | semua ditolak 8 dtk; batas struktural `HISTORY_SOURCE_PRODUCTS_1000` (dan grid di 100 hari) juga berlaku |

Tanda terima pertama tampil dalam 2,8–4,6 ms di semua ukuran (< 1 dtk terpenuhi). Hasil lengkap ≤ 3 dtk **belum** terpenuhi (100 target: 4,4–4,9 dtk). Mode latar belakang menampilkan "Sedang dihitung sejak jam …" dalam 17–37 ms dan kini **menyelesaikan 300 target** (11,5–11,8 dtk klik sampai tampil, 1 dan 30 hari); itu masih di atas 3 dtk, dan apakah pekerjaan latar belakang dengan progres terlihat diterima sebagai pengecualian adalah keputusan owner (`owner_named_background_exception=false`, `owner_latency_acceptance=false`). Dibanding run ketiga: 100 target 5,3–5,9 → 4,4–4,9 dtk; 300 target latar belakang dari ditolak menjadi selesai.

**Lapisan dominan (profil fase server, `PHASE_PROFILE_NOT_APP_LATENCY`, biaya sendiri lapisan):**

| Target | 1 hari | 30 hari | 100 hari | Fase pertama yang berhenti di 8 dtk |
|---|---|---|---|---|
| 100 | netting_build 346 ms | analysis_build_operational 389 ms | history_build 392 ms | — |
| 300 | netting_build 1.028 ms | netting_build 1.021 ms | history_build 1.269 ms | — |
| 1000 | **baseline_build 5.564 ms** | **baseline_build 4.779 ms** | history_build 4.250 ms | netting_build (1, 30 hari); baseline_build (100 hari) |
| 5000 | history_source 315 ms | history_source 310 ms | history_source 375 ms | **financial_source** (sebelum build mana pun) |

**Tindak lanjut yang sudah dikerjakan dari profil ini:** `baseline_build` di 1000 target adalah `cp7_baseline_native.build` yang kuadratik. Lapisan itu dilinearkan byte-identik di `2c6884ea` (lokal, profil dan kebijakan untuk setiap root: biaya sendiri 7,5 → 0,9 dtk). `cp7_baseline.allocate` dilinearkan di `9e3394e3`. Run kelima (37571509670, head `2c6884ea`) mengukur ulang. Kandidat berikutnya: `history_build` (4,25 dtk di 1000 × 100 hari) dan, untuk 5.000 target, `financial_source`. Batas struktural 1.000 produk per capture tetap berlaku; 5.000 target per capture butuh keputusan kapasitas owner, bukan pemotongan data.

**Pengamatan (belum diperbaiki):** di 300 target, job server selesai ±6,3 dtk, tetapi progres segmen pertama baru tampil di browser ±11 dtk. Selisih itu adalah polling job + manifest + transfer 12,5 MB Original, bukan kernel. Rinciannya belum terukur per langkah.

## 4. Run kelima — 37571509670 (head `2c6884ea`, sesudah alokasi dan baseline linear): runner ±2× lebih lambat

Suite `p19-scale5` **PASS** (5/5). **Angka absolut tidak sebanding dengan run keempat:** waktu pengisian lewat writer yang tidak diubah naik ±2× di semua ukuran (100 → 6,4 dtk vs 3,2; 1000 → 47,8 vs 29,6; 5000 → 301 vs 140), dan lapisan sumber yang juga tidak diubah naik sama (`history_source` di 5000: 612 vs 315 ms). Jadi runner kali ini ±2× lebih lambat; kegagalan pertama dan hasil dicatat apa adanya.

| Target | Hasil di runner ini | Lapisan dominan (biaya sendiri) |
|---|---|---|
| 100 | lengkap: biasa 7,3–7,9 dtk klik sampai tampil; latar belakang 7,5–8,1 dtk (server: biasa 6,5–7,2 dtk, job 4,1–4,9 dtk, manifest+segmen ±2,5 dtk) | netting_build 728–764 ms |
| 300 | ditolak jujur 8 dtk (biasa dan latar belakang) | netting_build 2,36–2,39 dtk |
| 1000 | ditolak jujur 8 dtk; 101 hari juga `HISTORY_GRID_100000` | **1 & 30 hari: `analysis_source` 5,0–5,1 dtk** (fingerprint keuangan); 100 hari: history_build 7,7 dtk |
| 5000 | ditolak jujur 8 dtk; batas struktural `HISTORY_SOURCE_PRODUCTS_1000` | history_source 612–645 ms; `financial_source` berhenti di 8 dtk |

**Sinyal yang tidak bergantung pada kecepatan runner:** di 1000 target, `baseline_build` (dominan 4,8–5,6 dtk di run keempat) tidak lagi dominan sesudah `2c6884ea`; yang kini dominan adalah biaya sendiri `analysis_source` = `cp7_analysis_native.financial_source` (laporan keuangan + fingerprint setiap jurnal, baris jurnal, saldo harian, dan kas). Biaya itu mengikuti **ukuran buku besar**, bukan jumlah target, sehingga juga mengenai pabrik dengan sedikit target tetapi riwayat jurnal panjang. Belum diubah: fingerprint ini adalah hash sumber yang dikunci kontrak (perubahan = keputusan kontrak).

Mulai run berikutnya, log memuat biaya sendiri setiap lapisan dan waktu server setiap fase (`own_ms_by_layer`, `server_ms_by_phase`), bukan hanya lapisan dominan, sehingga perbandingan antar run bisa memakai rasio lapisan yang tidak diubah.
