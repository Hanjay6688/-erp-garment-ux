# Putaran silang 2 CP7 — kandidat `0b7049d9`

Dasar: keputusan owner D13-10..D13-13 (13 Okt 2026). Kandidat yang sama dikirim ke Astra dan Fable (D13-13).
`production_go:false`.

## Identitas

- Commit **`0b7049d9203bac52b47a4c89f3e0d75646067a8f`**, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`, cabang
  `claude/new-session-deapao`.
- Kode produk (`supabase/`, `src/`, `scripts/cp7-src/`) identik dengan `ae0214ad` dan `7a0b4a90`.
- Register D13-10..D13-13 ada di kandidat ini (`docs/cp7/OWNER_DECISIONS_20261008.md`).
- Commit sesudahnya hanya mengubah `docs/` (paket ini).

## Isi paket

| Berkas | Isi |
|---|---|
| `FINDINGS_TRACKER.md` | Butir putaran 2 (R2-A6, R2-F05, R2-REG, R2-D11, A2) dan catatan perubahan kasus |
| `HANDOFF_ASTRA.md` | Kotak teks yang dikirim owner ke Astra |
| `HANDOFF_FABLE.md` | Kotak teks yang dikirim owner ke Fable |
| `CI_RECEIPT.json` | Semua run dan job pada commit kandidat (`scripts/cp7_ci_receipt.py`) |
| `a6_p11_dozen_helper_0b7049d9_run38433059108_job115419948325.log` | Baris kasus P11 desktop dan HP (bukti pertama R2-A6) |
| `f05_k3_cleanup_25_0b7049d9_run38432976212_job115419656388.log` | Baris kasus backup K3 dan ringkasan grup (bukti pertama R2-F05) |

## CI writer pada kandidat (bukti writer, bukan penerimaan auditor)

**20/20 workflow dan 57/57 job hijau**, semuanya pada GitHub attempt pertama. Empat grup dieksekusi ulang karena
pergantian hari (lihat di bawah). Rinciannya:

- 18 workflow kualifikasi, sama dengan putaran 1;
- 2 workflow CP7C yang ikut jalan karena push, hanya untuk diketahui: `CP7 Offsite Backup` dan `CP7 Backup Kit Check`.

| Workflow | Run | Job |
|---|---|---|
| Build UX | 38432976249 | 1 |
| CP6 Candidate CodeQL (T3) | 38432976191 | 4 |
| CP7 Astra Timeline Reuse | 38433016651 | 1 |
| CP7 F03 Full Retained Components | 38433055394 | 8 |
| CP7 Note Correction (Claude branch) | 38433019819 | 1 |
| CP7 Owning Receipt Correction | 38433062900 | 1 |
| CP7 P08 Physical Fabric | 38432976343 | 5 |
| CP7 P12 Payroll (Claude branch) | 38433026015 | 3 |
| CP7 P13 Finance (Claude branch) | 38433029945 | 1 |
| CP7 P18 Fabric Rule | 38433034110 | 3 |
| CP7 P18 Full Cycle | 38433037441 | 1 |
| CP7 P19 Analysis Job Transport (termasuk `k3-cleanup-25`) | 38432976212 | 12 |
| CP7 P21 Rehearsal | 38433040455 | 2 |
| CP7 PL Native Planning (Claude branch) | 38433044128 | 4 |
| CP7 Pre-freeze UI Regression (P11 helper lusin) | 38433059108 | 1 |
| CP7 Shell S0 (Claude branch) | 38433022591 | 5 |
| CP7 Supplier Payment Correction (Claude branch) | 38433047637 | 1 |
| CP7 Supplier Payment Create | 38433051523 | 1 |
| CP7 Offsite Backup (CP7C, diketahui) | 38432976256 | 1 |
| CP7 Backup Kit Check (CP7C, diketahui) | 38432976336 | 1 |

### Pergantian hari WIB (dicatat terbuka)

Run berjalan melewati tengah malam WIB (17.00 UTC). Empat grup otomatis diulang dari salinan baru
(`RERUN_FROM_FRESH_COPY`), sesuai aturan alat uji. Daftarnya ada di `CI_RECEIPT.json` → `business_day_reruns`.

Kalimat yang tepat (dikoreksi atas pemeriksaan Astra, `audit/astra_xc2_20261014/PACKAGE_FOLLOWUP.md` @ `fb24bd92`):
**semua workflow pada GitHub attempt pertama; empat grup dieksekusi ulang karena pergantian hari, mencakup 92 eksekusi
kasus, 41 di antaranya sebelumnya ditandai rollover.**

| Grup | Kasus ditandai rollover | Seluruh kasus grup yang diulang |
|---|---:|---:|
| Note Correction browser (job 115419813235) | 5 | 5 |
| P19 `p19-scale5` browser (job 115419656262) | 3 | 4 |
| PL Native `schedule` (job 115419899697) | 26 | 52 |
| Pre-freeze UI browser (job 115419948325), termasuk dua kasus P11 | 7 | 31 |
| **Total** | **41** | **92** |

Catatan pertama ke-41 kasus itu tetap berstatus INCOMPLETE dengan `status_before_rollover: PASS`. Jadi itu bukan 41
PASS penerimaan pada eksekusi pertama. Kasus lain di empat grup itu PASS pada catatan pertama. Ke-92 eksekusi ulang
PASS. Tidak ada FAIL, dan tidak ada INCOMPLETE dengan alasan lain, yang tertutup oleh ulangan.

## Hasil butir putaran 2 (menurut CI writer)

- **R2-A6:** `P11_DRAFT_BROWSER_DESKTOP` dan `P11_DRAFT_BROWSER_MOBILE_RECOVERY` PASS (job 115419948325).
  - Lima isian tidak sah ditolak dan qty tetap 13.
  - 2 lusin + 1 = 25, baris 2 tidak berubah, total Rp520.
  - Tanpa geser horizontal.
  - Kembali ke 13 lewat helper; dibaca ulang dari server `[2,13]`; form edit membaca 13.
  - Ikut jalan juga di `CP7 F03 Full Retained Components`.
- **R2-F05:** `k3-cleanup-25` 25/25, termasuk `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT` PASS (job
  115419656388).
  - Database asing dengan salinan tanda polos, di nama scratch maupun di pola percobaan, tetap utuh dengan OID dan
    barisnya.
  - `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` (situasi A–D) PASS.
- **A2:** `CP7 Supplier Payment Create` 10/10 di kandidat (run 38433051523).

## Cara owner mengirim

1. Buka `HANDOFF_ASTRA.md`, salin isi kotaknya, kirim ke sesi Astra.
2. Buka `HANDOFF_FABLE.md`, salin isi kotaknya, kirim ke sesi Fable.
3. Jawaban keduanya diteruskan ke writer.
   - Kalau R2-A6 LENGKAP dan F-OPS-05 DITUTUP oleh auditor, pembekuan final CP7 bisa dilakukan (D13-13), dengan A2
     tercantum sebagai keterbatasan terbuka.
   - Kalau masih ada masalah, putaran 3 disiapkan dengan cara yang sama.
