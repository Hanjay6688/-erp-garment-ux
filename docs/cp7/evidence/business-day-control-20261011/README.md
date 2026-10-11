# Kontrol pergantian hari alat uji — kualifikasi `af5e3941` (11 Okt 2026)

Perbaikan alat uji untuk OPEN_TOOLING S3 `ATTENTION_WIB_MIDNIGHT_FIXTURE` (uji ulang Sol atas `8116800c`,
`audit/sol-k4-retest-8116800c-20261010`): `scripts/cp6_auditor_business_day.py` / `.mjs`, dipasang di keempat mode runtime
auditor. Kualifikasi pada satu commit sedang berjalan; hasil lengkap ditambahkan di sini setelah selesai.

## Kegagalan / kejadian pertama yang disimpan

- `01_k4_browser_mobile_silent_first_attempt.log` — `k4-runner-17` percobaan pertama (run 38114007484, job 114395165573):
  17 kasus berjalan sampai kasus browser desktop PASS, lalu job diam 80 menit 42 detik sebelum kasus browser mobile
  mencetak hasil; writer membatalkan job untuk membaca log. Semua tanggal bisnis di log sama (11 Okt), jadi kontrol
  pergantian hari tidak terpicu. Penyebab belum diketahui; selama diam itu tanggal zona waktu browser mobile
  (America/Los_Angeles) 10 Okt sedangkan WIB 11 Okt — semua run K4 sebelumnya berjalan saat kedua tanggal sama. Ini
  dugaan, belum bukti. Job dijalankan ulang sekali pada commit yang sama.
