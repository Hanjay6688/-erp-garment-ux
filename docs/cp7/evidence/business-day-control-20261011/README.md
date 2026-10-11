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
  **Penyebab belum diketahui (terbuka).** Dugaan, belum bukti: selama diam itu tanggal zona waktu browser mobile
  (America/Los_Angeles) 10 Okt sedangkan WIB 11 Okt; semua run K4 lain (9 Okt ×3, auditor 10 Okt, percobaan kedua ini)
  berjalan saat kedua tanggal sama. Ada `await` tanpa batas waktu di modul uji (badan respons Playwright, penutupan
  context) yang bisa membuat kasus diam alih-alih gagal. Perlu ditelusuri: ulangi K4 browser saat tanggal Los Angeles
  berbeda dari WIB (WIB 00.00–14.00) dan beri batas waktu pada `await` itu tanpa mengubah oracle.
