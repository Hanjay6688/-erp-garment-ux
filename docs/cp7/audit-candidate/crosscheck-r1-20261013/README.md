# Putaran silang 1 CP7 — kandidat untuk Astra dan Fable (13 Okt 2026)

Dasar: arahan owner 13 Okt (kutipan lengkap di `FINDINGS_TRACKER.md`). Kedua auditor menguji kandidat yang sama
secara independen. Masing-masing menerima temuan pesaingnya lewat handoff ini supaya bisa saling memeriksa silang.
Cakupan CP7 saja. `production_go:false`.

## Berkas di folder ini

| Berkas | Untuk |
|---|---|
| `FINDINGS_TRACKER.md` | Daftar gabungan temuan Astra + Fable + catatan writer: status, perbaikan, siapa menguji apa |
| `HANDOFF_ASTRA.md` | Kotak teks yang dikirim owner ke Astra |
| `HANDOFF_FABLE.md` | Kotak teks yang dikirim owner ke Fable |
| `F_PAY_01_BOTH_BRANCHES.md` | Bukti uji tanggal bayar gaji pada jam ketika kedua cabang zona aktif (butir A4) |
| `CI_RECEIPT.json` | Semua workflow dan job writer pada commit kandidat (`scripts/cp7_ci_receipt.py`) |

## Identitas

- **Kandidat: `ae0214ad33184f7c2724783d663fb20fcb13820c`**, tree `0217f5f6740f28c19b7894fcb0181f39d3aea727`, cabang
  `claude/new-session-deapao`. Commit sesudahnya hanya mengubah `docs/`. Buktikan dengan
  `git diff --name-only ae0214ad HEAD -- . ':!docs'`, yang hasilnya harus kosong.
- Kode produk sama dengan `7a0b4a90` (kandidat yang diuji kedua auditor):
  `git diff --name-only 7a0b4a90 ae0214ad -- supabase src scripts/cp7-src` kosong.

## Yang berubah dari `7a0b4a90` di luar `docs/` (12 berkas)

| Berkas | Commit | Isi | Butir |
|---|---|---|---|
| `scripts/cp7_nightly_backup.py` | `85e17168` | Kepemilikan scratch diikat ke OID database | A1 |
| `scripts/cp7_k3_cleanup_cases.py` | `a09b6922`, `85e17168` | Kasus gladi jadwal (ke-23) dan kepemilikan per OID (ke-24) | A1, A3 |
| `scripts/cp7_f05_analysis_probe.py` | `a09b6922`, `85e17168` | Hitungan kasus K3 23 → 24 | A1, A3 |
| `.github/workflows/claude-p19-transport.yml` | `a09b6922`, `85e17168` | Nama suite `k3-cleanup-24` | A1, A3 |
| `.github/workflows/cp7-nightly-backup.yml` | `a09b6922`, `85e17168` | Komentar saja (nama suite); workflow tetap nonaktif | — |
| `scripts/cp6_auditor_runner.py` | `5b8e9d74`, `5e96cbcf` | Diagnosis: mencatat bagian yang berbeda bila pembanding gagal. Pembanding tidak diubah. | A2 |
| `scripts/cp6_auditor_difference.py` | `5e96cbcf` | `state_difference` dipindah tanpa perubahan isi (tanpa pustaka database) | A2, B1 |
| `scripts/cp6_auditor_runner_difference_test.py` | `5b8e9d74`, `5e96cbcf` | 5 uji `state_difference` (Shell S0) | A2 |
| `.github/workflows/claude-p08-shell.yml` | `5b8e9d74` | Satu baris: menjalankan uji di atas | A2 |
| `scripts/cp7_group_end_repeat_diagnosis.py` | `56009c31` | Alat diagnosis ulang grup (bukan kualifikasi) | A2 |
| `.github/workflows/cp7-group-end-diagnosis.yml` | `56009c31`, `0fe350b3` | Workflow alat diagnosis di atas | A2 |
| `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` | `144d0709`, `4dc0f3f0` | Pengganti pemeriksaan `SALES_MANUAL_13` (uji layar) | A6 |

## CI writer pada kandidat

Diisi setelah semua run selesai (`CI_RECEIPT.json`).

## Cara owner mengirim

1. Buka `HANDOFF_ASTRA.md`, salin isi kotaknya, kirim ke sesi Astra.
2. Buka `HANDOFF_FABLE.md`, salin isi kotaknya, kirim ke sesi Fable.
3. Jawaban keduanya diteruskan ke writer. Writer menggabungkannya. Kalau masih ada masalah, putaran 2 disiapkan
   dengan cara yang sama.
