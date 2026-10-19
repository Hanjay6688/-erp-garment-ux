# Fable r5 — log kerja

## CP1 — kandidat dan persiapan (2026-10-19)
- `git diff --name-only 17fa2507 origin/claude/new-session-deapao` (kepala 2766a909): 9 berkas, semua `docs/`.
- `git diff --name-only 663f6fae 17fa2507 -- src supabase`: kosong. `scripts/cp7-src` sama.
- Cabang `audit/fable-cp1-7-r5-17fa2507-20261019` dari kunci r4 ff6045a9; workflow Fable diarahkan ke kandidat r5.

## CP2a — tinjauan sumber dan oracle baru sebelum run
- **R5-01** (`cp7_payroll_checks_bundle.py`): satu anchor di `erp.run_v263a_payroll_integrity_checks()` diganti. Ada
  tambahan `left join erp.fg_unsourced_repair_wages_v1 fgw on pwi.source_type='FG_REPAIR' and fgw.id=pwi.source_id`, dan
  `coalesce(wce.contractor_id, ro.contractor_id, fgw.contractor_id)`. Baris PRODUCTION/REWORK tidak terpengaruh, karena
  join fgw hanya untuk FG_REPAIR. `ps.status <> 'REVERSED'` tetap. Upah yang hilang atau milik borongan lain tetap
  terhitung (NULL atau beda). Cek lain di fungsi itu tidak disentuh (penggantian anchor tunggal, dihitung =1)
  (INDEPENDENT_SOURCE_REVIEW).
- **R5-02** (`cp7_report_accounts_bundle.py`): 11 pembaca STABLE, setiap `erp.account_id('<KUNCI>')` literal dibungkus
  `(select …)`. Pemasangan menolak bila ke-17 kunci bukan pemetaan inti yang terisi, atau bila jumlah panggilan literal
  per pembaca berbeda. Penulis sendiri mencatat satu beda: kunci tanpa pemetaan ditolak versi lama walau tanpa baris, dan
  versi baru hanya bila ada baris. Klaim "tidak bisa terjadi" bersandar pada penjaga Native yang menolak hapus/ganti nama
  pemetaan inti. Kasus penulis menguji pembaca pada pemetaan tetap dan satu hapus (WIP). Belum ada ubah tujuan akun,
  kosongkan `account_id`, ganti nama, atau banyak baris dalam satu query, padahal keempatnya diminta handoff.
- Oracle baru (ditulis sebelum run): `audit/fable_cp7/scenarios/fable_r5_probes.py`, kasus
  `FABLE_R5:READERS_MAPPING_EDITS`. Salinan "sebelum" dibangun Fable dari teks terpasang dengan regex terbalik sendiri.
  Keadaan: BASE, MULTI_ROW, dan untuk ke-17 kunci REMAP/NULL/DELETE/RENAME lewat tabel dengan trigger aktif. Suntingan
  yang ditolak dicatat; yang diterima dibandingkan. Beda jawaban → COUNTEREXAMPLE.
