# Kandidat revisi P20 — perbaikan temuan audit independen 9 Okt 2026

Audit independen P20 (Astra, cabang `audit/astra-p20-2e605bb7-20261009`, laporan `audit/astra_p20/REPORT.md`) atas
kandidat `2e605bb7` memberi putusan **HOLD** dengan lima temuan F01–F05. Paket ini adalah **kandidat revisi** untuk
diuji ulang auditor. Kandidat `2e605bb7` (`../continuation-final-20261009/`), kandidat sebelumnya dan semua bukti kegagalan
tetap disimpan dan tidak diubah. Tidak ada push ke cabang audit, `cp7/integration`, `main`, deployment, atau Supabase
hosted; tidak ada jadwal atau backup yang dipasang di database sungguhan. `production_go:false`.

## Identitas kandidat revisi

- **Commit sumber: `870d4f791bc72159f07ed7bd6a17275c19c5ddc7`**, tree `2248685e0b4e65dac26db7aacc808f2c6da9c51d`, cabang `claude/new-session-deapao`.
- Selisih dari `2e605bb7` per berkas (status, ukuran, SHA-256 sebelum/sesudah): `SOURCE_DELTA.json` — 28 berkas (6 baru, 22 berubah, 0 dihapus; 15 bukan dokumen).
- Commit dokumentasi sesudah `870d4f79` tidak mengubah sumber (`git diff --name-only 870d4f79 HEAD` hanya `docs/`).

## CI pada satu commit (`CI_RECEIPT.json`)

Ke-15 workflow kualifikasi cabang Claude dijalankan pada `870d4f79` (push + `workflow_dispatch` tanpa commit baru):
**15/15 workflow dan 43/43 job sukses**. Ini bukti writer (WRITER_CROSSCHECK), bukan penerimaan auditor.

## Temuan dan perbaikannya

| Temuan | Perbaikan | Bukti writer di `870d4f79` |
|---|---|---|
| **F01 BLOCKER** — v1 APPLY 59 belum commit, v2 APPLY 2 commit lebih dulu → 61 pada kapasitas 60 (AS20-32) | Apply v1 (`scripts/cp7-src/plan-native/commands.sql`) sekarang mengambil kunci `CP7:PLAN_CAPACITY` yang sama dengan v2, di tempat yang sama (permintaan → roll → kapasitas → target → versi). Sesudah kunci, sebelum dan sesudah penulis Native, v1 menghitung kapasitas sisa = kapasitas Original − potong semua rencana lain (v1 atau v2) yang grup Native-nya masih draf; lebih → 40001 `CP7_PLAN_CAPACITY_USED` dengan angka di DETAIL (layar menulis kalimat yang sama dengan v2). Izin sesudah kunci, replay dan larangan dua rencana atas potongan yang sama tidak berubah. | Suite `p19-plan-v2-22` (dari 18): `P19P_V1_V2_SHARED_CAPACITY` (Native: v2 2 lalu v1 59 ditolak dengan angka 60/2/58, v1 58 diterima, total 60), `P19P_RACE_V1_HOLDS_V2_REFUSED` (v1 59 belum commit, v2 2 menunggu kunci lalu ditolak; kontrol 59+1 diterima), `P19P_RACE_V2_HOLDS_V1_REFUSED`, `P19P_RACE_V1_ROLLBACK_FREES_CAPACITY` (rollback pemenang pertama → v2 commit). Ketiga balapan **gagal pada apply v1 lama** (tidak ada tunggu kunci bersama) — dicoba di salinan lokal, bukan bukti CI. Semua kasus v1 lama (`plan39`, `p19-plan-v2` lama) tetap lulus. |
| **F02 MAJOR bersyarat** — install cron database B memindahkan job A (AS20-43) | `scripts/cp7_schedule.py`: nama job pg_cron = `<nama jadwal>@<database>`; install B tidak menyentuh A; install ulang yang sudah cocok tidak mengubah apa pun (id job sama); job bernama sama milik database lain ditolak sebelum ada perubahan; uninstall hanya menghapus job database target. | Suite `k3-cleanup-19` (dari 17): `K3C_RACE_CRON_TWO_DATABASES`; `K3C_RACE_PG_CRON_FIRES` tetap (job sungguhan berjalan dan membersihkan). |
| **F03 MINOR** — percobaan gagal di detik yang sama menimpa receipt valid (AS20-45) | `scripts/cp7_nightly_backup.py`: setiap percobaan punya nama sendiri (detik WIB + token acak); nama yang sudah ada ditolak sebelum menulis apa pun; receipt diklaim dengan pembuatan eksklusif. | `K3C_RACE_BACKUP_RETRY_SAME_SECOND`: backup terverifikasi lalu percobaan gagal di detik yang sama → dump dan receipt lama identik byte; tabrakan nama (token dipaksa sama) ditolak sebelum menulis. `K3C_RACE_NIGHTLY_BACKUP_VERIFIED` tetap. |
| **F04 MINOR/batas detektor** (AS20-39) | Tidak ada perubahan perilaku. `docs/cp7/k3/K3_CLEANUP.json` sekarang menyebut tepat apa yang diperiksa verifier sebelum menghapus (hash header/halaman terhadap isi, jumlah/ukuran halaman, hash identitas, scope ada dan satu baris rencana per target) dan apa yang **tidak** diturunkan ulang dari isi halaman (isi indeks rencana, isi scope, metadata rentang halaman, total header) — dilindungi trigger immutable (`55000 CP7_RUN_IMMUTABLE`), bukan verifier. | Deklarasi; kontrol trigger immutable tetap. |
| **F05 MINOR, gate gagal** — `cp7_probe_evidence_test.py` NameError `p19_plan_v2`; metadata expected basi | Tes membaca semua flag `run()` dari signature probe yang sebenarnya (flag baru tidak bisa hilang lagi); ketujuh kontrol negatif asli tetap. Workflow shell cabang Claude sekarang menjalankan gate bukti yang sama dengan shell integrasi (`cp7_probe_evidence_test.py`, `cp7_p19_browser_latency_test.mjs`, `cp7_integration_originals_test.py`). Metadata: schedule expected 70 → 71, P18 full cycle 1 → `cases.EXPECTED` (2). Tidak ada kasus dikurangi. | `CP7 Shell S0 (Claude branch)` pada `870d4f79`. |

Kesalahan alat/oracle auditor yang menurut handoff auditor tidak perlu diperbaiki (serialisasi timestamptz, operand AP
antara, kode penolakan 5.001, setup fixture, placeholder browser) tidak diubah.

## Kegagalan pertama dan petunjuk uji ulang

- Kegagalan pertama F01–F05 adalah run auditor: `../../evidence/p20-audit-20261009/README.md` (hanya penunjuk; log asli
  di run CI dan cabang audit). Semua 15 workflow di `870d4f79` lulus pada percobaan pertama.
- Petunjuk dan paste block untuk auditor: `AUDITOR_RETEST.md`.

## Yang tetap terbuka (bukan temuan baru)

- Penerimaan area optimasi timeline PR44 oleh auditor lain (konflik kepentingan Astra).
- Pemasangan jadwal dan backup di database sungguhan menunggu penerimaan, izin owner, tujuan backup di luar runner yang
  konkret, dan konfigurasi nyata.
- K4 (langkah analisis berjalan di server saat halaman ditutup), pengiriman WA nyata, delapan konfigurasi operasional.
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.
