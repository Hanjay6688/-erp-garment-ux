# Kontrol pergantian hari alat uji — kualifikasi `af5e3941` (11 Okt 2026)

Perbaikan alat uji untuk OPEN_TOOLING S3 `ATTENTION_WIB_MIDNIGHT_FIXTURE` (uji ulang Sol atas `8116800c`,
`audit/sol-k4-retest-8116800c-20261010`). Bukti writer (WRITER_CROSSCHECK), bukan penerimaan auditor. `production_go:false`.

## Yang berubah (hanya alat uji; kode produk tidak berubah)

- `scripts/cp6_auditor_business_day.py` dan `.mjs`: tanggal WIB dibaca dari database tepat sebelum dan sesudah tiap kasus.
  Kasus yang berjalan pada tanggal lain dari tanggal rencana kelompoknya (atau tanggalnya berganti selama kasus) bukan
  PASS: PASS menjadi INCOMPLETE dengan ketiga tanggal; FAIL/COUNTEREXAMPLE/INCOMPLETE tidak diubah. Kelompok diulang sekali
  dari salinan baru (setup, tanggal, kasus dan fixture baru) hanya bila pergantian hari menjelaskan semua baris yang tidak
  PASS dan kelompoknya selesai bersih; kegagalan pemeriksaan runtime (batas, skema, sesi/kunci bocor), hasil kasus rusak,
  error kelompok, kasus hilang, salinan tertinggal atau cleanup gagal tetap mempertahankan hasil pertama. Percobaan
  pertama disimpan utuh di laporan (`business_day_first_attempt`) dan barisnya tetap di log. Tidak ada assertion, oracle
  atau jam produk yang diubah.
- Dipasang di keempat mode: kelompok savepoint (`cp6_auditor_runner.strict_group`), race dan HTTP
  (`cp6_auditor_modes.strict_rows`), browser (`cp6_auditor_browser_host.mjs`).
- Uji: `scripts/cp6_auditor_business_day_test.py` (aturan; kode kelompok asli dijalankan dengan jawaban database palsu;
  putar ulang kegagalan pertama attention284) dan `scripts/cp6_auditor_business_day_test.mjs` (aturan browser sama dengan
  Python), dijalankan di CP7 Shell S0.
- Selisih dari `8116800c`: `SOURCE_DELTA.json` (16 berkas; 8 bukan dokumen, semuanya alat uji/workflow uji).

## CI pada satu commit (`CI_RECEIPT.json`)

15 workflow kualifikasi dan 44 job sukses pada `af5e3941` (push + `workflow_dispatch` tanpa commit baru). P08 (termasuk
`attention284`, 286 kasus) lulus pada percobaan pertama. P19 `k4-runner-17` lulus pada percobaan kedua (lihat di bawah).
Semua baris `business_day` di log yang diperiksa: tanggal rencana, sebelum dan sesudah sama (11 Okt); tidak ada
pengulangan karena pergantian hari pada run ini.

Workflow tambahan (bukan bagian dari 15, terpicu karena path `cp6_auditor_*`): `CP6 Auditor Scenario` run 38113978868
GAGAL pada 4 kasus browser CP6 yang sama dengan run 37007206187 (2 Okt, sebelum perubahan ini):
`READINESS_BROWSER:{DESKTOP,MOBILE}_NATIVE_POLICY_STATES_FINANCE_NOTE` (layar memanggil
`erp_cp7_get_recost_queue_v1` yang tidak dipasang pada skenario CP6 saja) dan `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`
(`.biz-size-entry input` 0 dari 3). Kasus database 104/104, race 26/26, HTTP 9/9 PASS; self-test runtime PASS. Kegagalan
lama ini terbuka dan tidak diperbaiki di sini.

## Kegagalan / kejadian pertama yang disimpan

- `01_k4_browser_mobile_silent_first_attempt.log` — `k4-runner-17` percobaan pertama (run 38114007484, job 114395165573):
  kasus native, race, HTTP dan browser desktop PASS, lalu job diam 80 menit 42 detik sebelum kasus browser mobile mencetak
  hasil; writer membatalkan job untuk membaca log. Semua tanggal bisnis di log sama (11 Okt), jadi kontrol pergantian hari
  tidak terpicu. Percobaan kedua (job 114415714726, 07:21–07:29 UTC) 17/17 PASS pada commit yang sama.
  Catatan yang ditulis sesudah kejadian pertama (dugaan tanggal kemudian gugur, lihat penelusuran di bawah):
  **Penyebab belum diketahui (terbuka).** Dugaan, belum bukti: selama diam itu tanggal zona waktu browser mobile
  (America/Los_Angeles) 10 Okt sedangkan WIB 11 Okt; semua run K4 lain (9 Okt ×3, auditor 10 Okt, percobaan kedua ini)
  berjalan saat kedua tanggal sama. Ada `await` tanpa batas waktu di modul uji (badan respons Playwright, penutupan
  context) yang bisa membuat kasus diam alih-alih gagal. Perlu ditelusuri: ulangi K4 browser saat tanggal Los Angeles
  berbeda dari WIB (WIB 00.00–14.00) dan beri batas waktu pada `await` itu tanpa mengubah oracle.
- `02_k4_browser_mobile_silent_second.log` — `k4-runner-17` pada `11633e4c` (run 38122987757, job 114421382536): pola sama,
  kasus desktop PASS lalu diam 21 menit 01 detik sebelum kasus mobile mencetak hasil; dibatalkan writer.

## Penelusuran diam K4 browser mobile (terbuka, alat uji)

- **Dugaan tanggal gugur.** Pada kejadian kedua tanggal Los Angeles dan WIB sama (11 Okt), jadi beda tanggal zona waktu
  browser bukan penyebabnya.
- **Bukan panggilan database atau skrip pembantu yang macet.** Daftar proses yatim saat job dibatalkan (dua kejadian):
  hanya `python` (probe), `node` (host browser) dan `chrome-headless-shell`. Tidak ada `psql` atau skrip fixture Python
  yang masih hidup, padahal keduanya dijalankan sinkron oleh host dan akan tertinggal bila sedang menunggu. Yang tertahan
  adalah `await` di dalam host/Playwright (pembuatan atau penutupan context/halaman, badan respons) yang tidak punya batas
  waktu.
- **Sejak `c04bec8a`** setiap kasus browser punya batas waktu (`AUDITOR_BROWSER_CASE_TIMEOUT_MS`, bawaan 45 menit), badan
  respons dan penutupan context di modul K4 dibatasi 60 detik, dan modul K4 mencetak penanda langkah (`k4r_stage`: LOGGED_IN,
  RUNNER_ON, REQUESTED, SERVER_TEXT_SHOWN, TAB_CLOSED/STOPPED_WATCHING, DONE_BY_SERVER, REOPENED, PAGES_READ, RUNNER_OFF,
  CLOSING, CLOSED). Diam berikutnya menjadi kasus INCOMPLETE `AUDITOR_BROWSER_CASE_TIMEOUT` yang menyebut langkah terakhir,
  bukan job yang diam sampai dibatalkan. Batas ini tidak mengubah oracle apa pun.
- **Upaya mengulang:** sesudah `c04bec8a`, K4 lulus 5 dari 5: run 38123203866 job 114422035596 (`c04bec8a`) dan workflow
  diagnosa sementara run 38126886218 (empat salinan `k4-runner-17` bersamaan pada `c2c2eb5e`, batas kasus 20 menit; job
  114432990332, 114432990297, 114432990309, 114432990196, semuanya 17/17 PASS, kedua kasus browser selesai 10–13 detik dengan
  penanda langkah lengkap). Workflow diagnosa itu sudah dihapus lagi.
- **Status:** penyebab belum ditemukan karena belum terulang sejak ada penanda langkah. Kasus produk K4 (Native, balapan,
  HTTP, browser desktop) PASS di kedua kejadian; yang diam selalu sesudah kasus desktop, sebelum hasil kasus mobile.
  Tercatat sebagai butir alat uji terbuka untuk audit penuh CP7, bukan disembunyikan.
