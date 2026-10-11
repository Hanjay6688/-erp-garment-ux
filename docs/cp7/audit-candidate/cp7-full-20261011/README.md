# Kandidat audit penuh CP7 — 11 Okt 2026

Owner 11 Okt: "Ya selesain semua abis tu full audit cp7." Sisa CP7 (K6, alat uji tengah malam, uji K4 browser mobile)
sudah dikerjakan; paket ini adalah **satu kandidat untuk satu audit penuh CP7**: seluruh CP7 dari kandidat beku
`9d57b7f5` (= `cp7/integration`) sampai commit di bawah. Semua kandidat lama dan bukti kegagalan tetap disimpan dan tidak
diubah. Tidak ada push ke cabang audit, `cp7/integration`, `main`, deployment, atau Supabase hosted; tidak ada jadwal atau
backup yang dipasang di database sungguhan. `production_go:false`.

Untuk auditor: mulai dari `AUDITOR_START.md` (paste block pembuka sesi dan cakupan).

## Identitas kandidat

- **Commit sumber: `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`**, tree `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41`, cabang `claude/new-session-deapao`.
- Selisih per berkas (status, ukuran, SHA-256 sebelum/sesudah):
  - `SOURCE_DELTA.json` — dari `8116800c` (terakhir diuji ulang auditor): 35 berkas (18 baru, 17 berubah, 0 dihapus; 20 bukan dokumen).
  - `SOURCE_DELTA_FROM_P20.json` — dari `2e605bb7` (diaudit P20): 74 berkas (40 baru, 34 berubah, 0 dihapus; 38 bukan dokumen).
  - `SOURCE_DELTA_FROM_FROZEN.json` — dari `9d57b7f5` (kandidat beku): 191 berkas (135 baru, 56 berubah, 0 dihapus; 123 bukan dokumen).
- Commit sesudah `d0b9e9c2` hanya dokumen; buktikan dengan `git diff --name-only d0b9e9c2 HEAD`.

## CI pada satu commit (`CI_RECEIPT.json`)

CI_RECEIPT_PLACEHOLDER

## Riwayat audit menuju kandidat ini (masukan, bukan penerimaan audit ini)

| Kandidat | Audit | Putusan |
|---|---|---|
| `2e605bb7` (lanjutan final) | P20 Astra, `audit/astra-p20-2e605bb7-20261009` | HOLD: F01 (kapasitas rencana v1/v2 61>60), F02 (nama jadwal lintas database), F03 (receipt backup tertimpa), F04 (batas detektor), F05 (gate bukti) |
| `8cc1b081` (F01–F05 + K4) | Sol, `audit/sol-p20-k4-8cc1b081-20261009` | F01–F05 PASS, regresi 71/71, area PR44 235 perbandingan PASS, K4 fungsi utama PASS; HOLD SOL-K4-01 (S2) |
| `8116800c` (perbaikan SOL-K4-01) | Sol uji ulang, `audit/sol-k4-retest-8116800c-20261010` | PASS_RETEST, SOL-K4-01 ditutup, 60/60; terbuka alat uji S3 (tengah malam WIB) |
| `d0b9e9c2` (paket ini) | — | belum diaudit |

## Yang baru sejak uji ulang Sol (`8116800c`)

| Butir | Isi | Bukti writer |
|---|---|---|
| Alat uji tengah malam (S3 Sol) | Tanggal WIB dibaca dari database sebelum dan sesudah tiap kasus di keempat mode runtime auditor (savepoint, balapan, HTTP, browser). Kasus yang berjalan di tanggal lain bukan PASS; kelompok diulang sekali dari salinan baru hanya bila pergantian hari menjelaskan semua baris yang tidak PASS. Tidak ada oracle atau jam produk yang diubah. | `../../evidence/business-day-control-20261011/` (15/15 workflow, 44/44 job di `af5e3941`); uji `scripts/cp6_auditor_business_day_test.{py,mjs}` di CP7 Shell S0 |
| K6 penjalan bukti PL-8 (keputusan owner 8 Okt butir 8) | Jadwal `cp7-proof-runner` (tiap 10 menit, sampai 20 giliran, batas 8 dtk per giliran) membuktikan riwayat potong terposting per jendela lewat pembukti PL-8 yang sama dan tidak diubah. Bukti terikat isi fakta grup dan versi aturan, jadi koreksi/pembatalan/backdate membuat bukti lama tidak cocok lagi. Penjalan hanya menambah bukti; satu giliran pada satu waktu, giliran lain langsung BUSY tanpa menunggu. Belum dipasang. | suite `k6-proof-runner-10` (4 Native, 4 balapan termasuk pg_cron sungguhan, 2 HTTP Auth nyata); deklarasi `../../k6/K6_PROOF_RUNNER.json`; sumber `scripts/cp7-src/planning/proof-runner.sql`, `scripts/cp7-src/ops/schedule.sql` |
| Batas waktu kasus browser (alat uji) | Kasus browser yang tidak selesai dalam `AUDITOR_BROWSER_CASE_TIMEOUT_MS` (bawaan 45 menit) menjadi INCOMPLETE `AUDITOR_BROWSER_CASE_TIMEOUT`; modul K4 browser mencetak penanda langkah dan membatasi dua penantian yang tidak dibatasi Playwright. Tidak ada assertion yang berubah. | `../../evidence/business-day-control-20261011/README.md` (penelusuran diam K4) |
| Daftar jadwal | `cp7_ops.schedules()` kini empat entri (ditambah `cp7-proof-runner`); deklarasi dan kasus K3 hanya menambah entri itu; probe F05 mendapat flag `k6_proof_runner`. | `docs/cp7/k3/K3_CLEANUP.json`, `scripts/cp7_k3_cleanup_cases.py`, `scripts/cp7_f05_analysis_probe.py` |
| Workflow | `cp7-prefreeze-ui` (oracle browser CP6 di tumpukan CP7 penuh) dan `cp7-f03-full` (komponen F03 yang dipertahankan) kini bisa dijalankan manual di cabang ini; pemicu push dan job tidak berubah. | `.github/workflows/cp7-prefreeze-ui.yml`, `cp7-f03-full.yml` |

## Butir terbuka yang diketahui (bukan temuan baru; boleh diuji)

- **K4 browser mobile sempat diam (alat uji).** Dua kali (run 38114007484 dan 38122987757, sebelum ada batas waktu kasus)
  job diam sesudah kasus browser desktop PASS, sebelum hasil kasus mobile. Sesudah batas waktu dan penanda langkah
  ditambahkan, K4 lulus 5 dari 5. Penyebab belum ditemukan; diam berikutnya berhenti sendiri dan menyebut langkah
  terakhirnya. Rinciannya di `../../evidence/business-day-control-20261011/README.md`.
- **Workflow `CP6 Auditor Scenario`** (bukan bagian dari 15) gagal pada 4 kasus browser CP6 yang sama sejak 2 Okt: layar
  CP7 memanggil RPC CP7 yang tidak dipasang di skenario CP6 saja, dan dua kasus demo `SALES_MANUAL_13` sudah dipensiunkan
  dengan pengganti tersambung (`P11_DRAFT_BROWSER_DESKTOP`, `P11_DRAFT_BROWSER_MOBILE_RECOVERY`;
  `../../PREFREEZE_RUNTIME_MIGRATION_20261006.md`). Oracle browser CP6 yang sama dijalankan di tumpukan CP7 penuh oleh
  `CP7 Pre-freeze UI Regression` (lihat bukti CI di atas).
- **Belum diuji auditor:** 5.000 target seluruhnya lewat penjalan K4, HP fisik/Safari, tab HP yang benar-benar ditutup,
  pemasangan di hosted.
- **Belum dipasang:** jadwal pembersihan, hapus 7 hari, penjalan analisis K4, penjalan bukti K6, dan backup malam.
  Pemasangan menunggu hasil audit dan izin owner (tahap CP7C).
- **K7:** capture 4,4–4,6 dtk diterima sementara sebagai latar (keputusan owner 8 Okt butir 7); 3 dtk tetap sasaran dan
  tidak ditandai tercapai.
- **Bukan bagian kandidat:** PR #45 (UI demo, belum diaudit; saran auditor: audit UI/demo terpisah). Area optimasi timeline
  PR44 tidak boleh diterima oleh auditor yang menulisnya (Astra).
- Pengiriman pengingat masih pratinjau lokal. Delapan pengaturan CP6 nyata diisi di aplikasi saat dipakai.
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

## Sesudah audit ini

Urutan kerja yang sudah ada (owner 11 Okt): audit penuh CP1–CP7, lalu CP7.5 (kode diringkas, perilaku dibuktikan sama,
riwayat lama diarsip), lalu CP7C (backup/restore, jadwal server, uji beban), lalu CP8 (audit/gladi akhir, GO owner).
