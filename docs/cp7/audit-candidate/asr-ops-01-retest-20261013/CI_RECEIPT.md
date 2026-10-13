# ASR-OPS-01 — hasil CI writer (bukan penerimaan auditor)

| Hal | Nilai |
|---|---|
| Commit / tree | `85e171688de2038dfd8a1ee85cb0e2b143ffea58` / `08f3423a` |
| Workflow / run / job | `CP7 P19 Analysis Job Transport`, run 38373379923 (push, percobaan 1), job 115215590420 `k3-cleanup-24`, 09:28:14–09:38:43 UTC 13 Okt 2026 |
| Suite | `CP7_K3_CLEANUP` **PASS**, `observed_case_count` 24, `cp6_restored: true`, `advisor_gate: true` |
| Pergantian hari WIB | tidak ada (semua kasus `planned=before=after=2026-10-13`) |
| Baris kasus | `k3_cleanup_24_85e17168_run38373379923_job115215590420.log` (41 baris JSON dari log job, tanpa perubahan) |

## Kasus backup

| Kasus | Hasil | Isi yang terukur |
|---|---|---|
| `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` (baru) | PASS | Lihat tabel di bawah. `source_unchanged: true`. |
| `K3C_RACE_NIGHTLY_BACKUP_VERIFIED` | PASS | `restore_verified`, 559 tabel. Malam yang gagal tidak menghapus apa pun. Dua backup terverifikasi terbaru disimpan, yang lebih lama baru dihapus sesudah malam terverifikasi. |
| `K3C_RACE_BACKUP_RETRY_SAME_SECOND` | PASS | Percobaan ulang di detik yang sama memakai nama baru. Tabrakan nama ditolak sebelum menulis. Percobaan gagal tidak menghapus apa pun. |
| `K3C_RACE_BACKUP_SCRATCH_NEVER_DROPS_ANOTHER_DATABASE` | PASS | Database asing ditolak dan tetap ada. Database yang muncul sesudah pemeriksaan tidak dihapus. Nama bebas dipakai lalu dihapus. Sisa milik alat sendiri dibersihkan. |
| `K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES` | PASS | 424 baris ditulis selama backup. Tetap terverifikasi, 560 tabel dibandingkan dengan sumber di snapshot dump. |

### `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` per situasi

| Situasi | Yang dilakukan kasus (DDL admin disisipkan sesudah langkah asli alat) | Hasil |
|---|---|---|
| A — urutan ASR-OPS-01 Astra | Sisa scratch bertanda, lalu sesudah dump diganti database asing bernama sama | Database pengganti **tetap ada** (`FOREIGN_REPLACEMENT`). Error `BACKUP_SCRATCH_REPLACED`, `verified: false`. |
| B — database percobaan diganti sebelum restore | Database percobaan (nama acak) dipindah, lalu nama itu diberi database lain | Pengganti **tetap ada**. Database milik percobaan dihapus lewat OID-nya di nama barunya. Error `BACKUP_SCRATCH_REPLACED` (`after restore`), tidak terverifikasi. Ini batas operasional yang dinyatakan: restore menulis ke database pengganti, tetapi pengganti itu tidak dihapus. |
| C — database percobaan diganti sebelum hapus akhir | Sesudah verifikasi, sebelum `finally` | Pengganti **tetap ada**. Database milik percobaan dihapus lewat OID. Verifikasi sebelumnya tetap sah (`verified: true`), karena hash dibaca dari OID percobaan. |
| D — sisa berpola nama | `<scratch>_<acak>` bertanda sendiri, tanpa tanda, dan bertanda OID lain | Yang bertanda sendiri dihapus. Yang tanpa tanda dan yang tandanya menyebut OID lain **tetap ada**. |

## Batas klaim

- Ini bukti writer (WRITER_CROSSCHECK) di cluster sekali pakai CI, bukan penerimaan auditor. ASR-OPS-01 tetap
  "diperbaiki, menunggu uji ulang auditor".
- Kasus Astra `ASD-B01..B05` belum dijalankan di CI oleh writer. Writer menjalankan logikanya di PG16 lokal sebagai
  kontrol (B05 di alat lama = COUNTEREXAMPLE, di alat baru = PASS), dan itu bukan bukti. Uji ulang dengan oracle Astra
  dilakukan oleh Astra.
- Hosted, `main`, Cloudflare dan produksi tidak disentuh. `production_go:false`.
