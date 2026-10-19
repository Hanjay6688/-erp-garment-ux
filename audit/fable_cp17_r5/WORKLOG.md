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

## CP3 — run dibaca per kasus dari baris JSON log
Run Fable (cabang audit, head 6edace8b / 61b26712; FABLE):
| Run | Isi | Hasil |
|---|---|---|
| 39237656752 | `fable_cp17c_cash_basis.py` tanpa perubahan | 1/1 PASS |
| 39237669080 | `fable_r2_cash_both.py` tanpa perubahan | 2/2 PASS |
| 39237680398 / 39237692243 | sensus `fable_r3_screens.mjs` tanpa perubahan, DISPOSABLE / ENTENG | sama dengan r3–r4: 47/47 menu terbuka di 1440 dan 390, satu-satunya tanda pemberitahuan Dashboard (AUDITOR_TOOL), GUDANG 7/7 tanpa Keuangan, tab Tutup Buku ada |
| 39238163462 | `FABLE_R5:READERS_MAPPING_EDITS` | **PASS**: BASE 17 jawaban sama; MULTI_ROW (`compute_po_hpp_gl_book` 8 PO dalam satu query) sama; REMAP diterima untuk 16 dari 17 kunci, tiap keadaan 17 jawaban sama, 0 beda; NULL, DELETE dan RENAME ditolak untuk 17/17 kunci (penjaga Native). REMAP OPENING_EQUITY tidak dicoba: tidak ada akun EQUITY aktif lain, dan kolom kode `erp.chart_accounts` bukan `code` (alat saya). Tiga pembaca ber-uuid tidak punya input di buku dasar (kredit saldo awal, buku periode pocket, HPP siklus penjualan); ketiganya dibandingkan kasus penulis dengan fixture |

Run penulis (ref `claude/new-session-deapao`, head 2766a909, tree produk = kandidat; INDEPENDENT_NATIVE_RERUN):
| Run | Workflow | Hasil |
|---|---|---|
| 39237703474 | CP7 CP17 Fixes | 345/345 PASS + `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER` (Native 165, race 39, HTTP 27, browser 57, Enteng 57). R5-01: kasus Sol PASS, checker lama di sampingnya tetap 0→2 alarm (bukti kasusnya nyata), 167 detektor; kontrol upah borongan lain dan upah hilang tetap terhitung 1. R5-02: 11 pembaca dibandingkan dengan nilai (inputs 1–9 per pembaca, semua `with_value`), review menolak 5 perubahan. Grup Enteng: 1.361 permintaan loopback; 2 catatan `route.fetch: Request context disposed` (jawaban lokal sesudah halaman ditutup, sama dengan kualifikasi r4 penulis) |
| 39237715223 | Pre-freeze UI | 31 PASS + 2 INCOMPLETE `LEGACY_RUNTIME_GAP` lama |
| 39237739029 | F03 Full (8 job) | p09 135, p10 34, p11 64, p12 91, p13 50, cash_installments 61, customer_refund 10, supplier_credit 5: semua PASS |
| 39237751915 / 39237765221 / 39237778532 | F03 cash / misc / payment | 21 / 20 / 23 PASS |
| 39237791246 | P12 (3 job) | 64 / 81 / 43 PASS |
| 39237804091 / 39237816644 / 39237829301 | cutting / P13 / sales chain | 19 / 25 / 25 PASS |
| 39237726903 | P19 Transport (12 job) | semua PASS per kasus (transport 15, ai 9, k2 10, staged 14, pl5 20, plan 22, report 20, reminder 16, k3 25, k4 17, k6 10, scale5 5) |
| 39237840633 | UI phone width | `{"menus":47,"failed":[],"unreadable":[]}` |

Angka kecepatan di runner saya (P19 scale5):
- Tangga SQL 100 target: tanpa angka keuangan 1,15 s; dengan angka keuangan **2,17–2,23 s** (r4: 4,57–4,62 s).
- Tangga SQL 300 target: dengan angka keuangan **6,37–6,47 s** (r4: berhenti di 8 s).
- Browser 100 target: dengan angka keuangan 2,84 / 2,87 / 3,25 s (1/30/100 hari); belum stabil di bawah 3 s.
- Browser 300 target: dengan angka keuangan 1 dan 30 hari selesai 10,4–10,6 s; 100 hari ditolak di 8,1 s dengan pesan.
- Jam mulai tampil 0–74 ms sesudah klik.
Semua sesuai pengungkapan penulis.

## CP4 — kunci
Tree produk sesudah audit (kepala 2766a909): src c3008b5b, scripts 5acd2558, supabase 5d040436, sama dengan kandidat.
`RETEST_FABLE_17fa2507.md`, `FINDINGS.json`, ledger r5 dan `LOCK.md` dikunci dengan commit sebelum membaca pekerjaan auditor
lain putaran r5.
