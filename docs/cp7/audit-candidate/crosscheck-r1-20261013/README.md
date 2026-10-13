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
  `claude/new-session-deapao`. Uji dan baca pada commit ini (checkout `ae0214ad`), bukan pada HEAD cabang. Sesudah
  kandidat, writer bisa menambah pekerjaan lain di cabang yang sama (misalnya alat backup versi berikutnya). Pekerjaan
  itu bukan bagian dari putaran ini dan akan diaudit terpisah.
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

`CI_RECEIPT.json` dibuat dengan `scripts/cp7_ci_receipt.py`. **18/18 workflow lulus, 55/55 job**, semuanya pada
percobaan pertama. Tidak ada pengulangan atau hasil pertama yang ditahan karena pergantian hari WIB
(`business_day_reruns: []`, `business_day_kept_first: []`). Ini bukti writer (WRITER_CROSSCHECK), bukan penerimaan
auditor.

| Workflow | Run | Job | Hasil |
|---|---|---|---|
| Build UX | 38378120963 | 1 | success |
| CP6 Candidate CodeQL (T3) | 38378249947 | 4 | success |
| CP7 Astra Timeline Reuse | 38378193505 | 1 | success |
| CP7 F03 Full Retained Components | 38378197156 | 8 | success |
| CP7 Note Correction (Claude branch) | 38378200708 | 1 | success |
| CP7 Owning Receipt Correction | 38378205370 | 1 | success |
| CP7 P08 Physical Fabric | 38378209895 | 5 | success |
| CP7 P12 Payroll (Claude branch) | 38380339961 | 3 | success |
| CP7 P13 Finance (Claude branch) | 38378213570 | 1 | success |
| CP7 P18 Fabric Rule | 38378217652 | 3 | success |
| CP7 P18 Full Cycle | 38378221305 | 1 | success |
| CP7 P19 Analysis Job Transport | 38378224944 | 12 | success |
| CP7 P21 Rehearsal | 38378228621 | 2 | success |
| CP7 PL Native Planning (Claude branch) | 38378232467 | 4 | success |
| CP7 Pre-freeze UI Regression | 38378236418 | 1 | success |
| CP7 Shell S0 (Claude branch) | 38378239743 | 5 | success |
| CP7 Supplier Payment Correction (Claude branch) | 38378243207 | 1 | success |
| CP7 Supplier Payment Create | 38378246722 | 1 | success |

Catatan:

- `CP7 Supplier Payment Create` lulus 10/10 dan pemeriksaan akhir grup sama (butir A2). Status penyebab dua
  kegagalan lama tetap OPEN.
- `CP7 P19 Analysis Job Transport` memuat `k3-cleanup-24` (24/24, butir A1 dan A3).
- `CP7 P12 Payroll` didispatch pukul 17.00 WIB supaya kedua cabang zona aktif (butir A4,
  `F_PAY_01_BOTH_BRANCHES.md`).
- `CP7 Shell S0` hijau, termasuk uji `state_difference` dan uji layar di `tests/cp7/` (butir B1 dan A6).

## Cara owner mengirim

1. Buka `HANDOFF_ASTRA.md`, salin isi kotaknya, kirim ke sesi Astra.
2. Buka `HANDOFF_FABLE.md`, salin isi kotaknya, kirim ke sesi Fable.
3. Jawaban keduanya diteruskan ke writer. Writer menggabungkannya. Kalau masih ada masalah, putaran 2 disiapkan
   dengan cara yang sama.
