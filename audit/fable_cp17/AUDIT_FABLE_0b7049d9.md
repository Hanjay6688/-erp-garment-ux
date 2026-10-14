# AUDIT FABLE — commit 0b7049d9203bac52b47a4c89f3e0d75646067a8f tree ce6aed0a… — 2026-10-14 (putaran cp17-20261014, v1.0)

Lingkungan: GitHub Actions ubuntu-24.04; Supabase CLI 2.116.0 dengan PostgreSQL 17.6.1.165 (basis sekali pakai, hosted-faithful G-01 opsi 1); Node 22; Chromium/Playwright untuk grup browser; psycopg 3.2.10; Python 3.12. Tidak ada koneksi ke hosted Supabase Enteng/legacy/produksi; tidak ada SQL ke hosted; tidak ada pemasangan pg_cron/backup di mana pun selain salinan sekali pakai.

Perintah yang dijalankan: `workflow_dispatch` lewat REST untuk 60 run (14 workflow CP7, 41 run CP3–CP6, 5 run Fable) — daftar lengkap dan id job di `REGISTER_RUNS.md` dan `runs/cp17/dispatch_ledger_cp17.jsonl`; pembacaan log per kasus lokal (`case_summary.py`, status dari baris JSON, bukan warna job); tinjauan sumber baca-saja pohon beku (`review/R1..R6`); skenario Fable `audit/fable_cp7/scenarios/fable_cp17_chain{,2,3,4}.py` (run 38557410928, 38558699494, 38559631518, 38560570589) dan `fable_cp7_smoke.py` (run 38522428512) pada `product_ref=0b7049d9` lewat `AUDIT/fable/cp7-native`.

Manifest putaran: `MANIFEST.md` (tree produk, sha panduan 5752e96d…, pernyataan paparan). Register keputusan yang dipakai sebagai oracle: `docs/cp7/OWNER_DECISIONS_20261008.md` (s.d. D13-13), `audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md`, addendum CP6 2026-09-25 (D01–D06), D11/GBD-03.

## Ringkasan
S0: 0, S1: 1 TERBUKTI + 5 DUGAAN, S2: 0 TERBUKTI + 1 DUGAAN, S3: 4 TERBUKTI. DUGAAN = statis dengan rujukan baris, belum diverifikasi native.
Invarian (82): PASS 48, FAIL 2 (INV-P01 per tanggal = FABLE-001; INV-POL03 = FABLE-002), INCOMPLETE 32 (tidak diuji putaran ini atau hanya statis). Rinciannya di matriks.

Inti: regresi runtime CP3–CP7 pada kode final **identik** dengan rujukan beku (T2 r16, paket T3, rollback, probe T1 AW..BE, 26 job CP7). Rantai lintas tahap Fable pada satu kode final lulus untuk keseimbangan jurnal, saldo harian, stok kronologis, dimensi AR/AP/upah, worksheet E01, dan pengakuan di periode terbuka sesudah tutup buku. Satu cacat terbukti native: pembayaran upah boleh bertanggal sebelum utangnya timbul, tanpa detektor.

## Vonis per tahap (diminta HANDOFF_FABLE.md)

| Tahap | Vonis | Alasan singkat |
|---|---|---|
| CP1 (fingerprint/baseline, single writer) | **BELUM DIPERIKSA — TIDAK DAPAT DIVERIFIKASI DARI SESI INI** | Set fingerprint asli hanya ada di dua cabang bukti yang bukan leluhur 0b7049d9; pohon beku hanya memuat pin turunan (`a0c59b96…` dikutip, algoritmanya tidak ada). Auditor tidak boleh query hosted. Paling tinggi REUSED_WRITER_EVIDENCE (`review/R6` §A). FABLE-004. |
| CP2 (backup terenkripsi + restore basis pra-v2.6.10) | **BELUM DIPERIKSA — TIDAK DAPAT DIVERIFIKASI DARI SESI INI** | Arsip, kunci, set restore, dan artefak bukti restore di luar git (artefak Actions kedaluwarsa; klaim Drive/perpustakaan chat); hanya sha256 di repo; tidak ada restore independen; manifest CP2 sendiri menyebut basis **pasca** v2.6.11a (`review/R6` §B, daftar ABSENT 9 butir). FABLE-004. |
| CP3 / CP3.5 (absensi → HPP → payroll) | **LULUS DENGAN SYARAT** | Runtime: T2 identik beku r16; P12 payroll 3 job PASS; rantai Fable PASS. Syarat: FABLE-001 (S1 terbukti) diperbaiki; DUGAAN FABLE-007 (dan R1-01/R1-02 di `review/R1`) dibuktikan atau dibantah native. |
| CP4 / CP4.5 (RBAC, identitas produksi, WIP) | **LULUS (dasar runtime)** | AT 16 + AU 15 + races PASS; AV after PASS; matriks Auth/HTTP di setiap job CP7 PASS; smoke Fable: skema CP7 tidak terjangkau peran publik. Tinjauan sumber RBAC terpisah (R2) **tidak** dilakukan putaran ini — masuk daftar belum diperiksa. |
| CP5 (potong → pickup → WIP → BS/rework/klaim) | **LULUS DENGAN SYARAT** | Runtime: T2 identik, AV after PASS, rantai E01 (potong→pickup→jahit→laundry→QC→FG) PASS. Syarat: DUGAAN FABLE-006, FABLE-008, FABLE-009, FABLE-010 dibuktikan atau dibantah native; workflow snapshot CP5 sendiri adalah gate identitas historis yang tidak menguji 0b7049d9. |
| CP6 (cutover, uang muka, tutup buku, HPP bertanggal, paket T3) | **LULUS DENGAN SYARAT** | T2 identik r16; paket T3 `ALL_STAGES_INSTALLED` (104 + 26 + 9 PASS); rollback 152 objek identik; G-01 `ALIGNED_PER_OBJECT`; probe T1 after 0 merah; tutup buku + pengakuan periode terbuka PASS (run 38560570589). Syarat: FABLE-002, FABLE-003 (S3) dan DUGAAN FABLE-011 (lantai cutover) diputuskan owner. |
| CP7 | **LULUS** (beku D13-13; dikonfirmasi ulang) | 26/26 job berkasus identik multiset dengan putaran sebelumnya; smoke Fable PASS; tidak ada `business_day_retried`. FABLE-001 menyentuh fasad CP7 `PAY` tetapi akar penjaganya di Native CP3/CP6 (`post_payroll_payment`). CP7C di luar lingkup (D13-9a). |

## Temuan

### FABLE-001 — Pembayaran upah (Nota/payroll) boleh bertanggal sebelum utang upahnya timbul; saldo utang mandor negatif per tanggal tanpa terdeteksi
- Keparahan: **S1** (angka per tanggal salah dan tidak ditangkap detektor mana pun; total akhir dan kas benar). Catatan: menurut definisi §8 "salah tanpa ketahuan" bisa dibaca S0; saya pilih S1 karena saldo akhir dan kas tidak salah dan dampaknya terbatas pada laporan per tanggal antara tanggal bayar dan akhir periode Nota. Owner boleh menaikkan ke S0 (lihat pertanyaan 1).
- Invarian/pola: INV-P01 (sisa utang per tanggal tidak boleh negatif tanpa dokumen kredit), INV-P02 (pembayaran pada tanggal ≥ tanggal sumbernya), INV-U04 per tanggal, INV-D01/D03 (tidak ada detektor).
- Lokasi: `supabase/release/cp6-t3/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql:3201-3225` (`erp.post_payroll_payment` hanya menolak tanggal kosong dan masa depan); akrual bertanggal `period_end` (`…20bc…sql:3235`, `review/R1` R1-05); fasad CP7 `scripts/cp7-src/payroll/settlement-write.sql:92,111-118` menerima tanggal kanonik apa pun; cicilan `scripts/cp7-src/payroll/installments.sql:23`.
- Rantai dampak: Nota disetujui (Dr WIP / Cr CONTRACTOR_PAYABLE pada akhir periode) → PAY bertanggal lebih awal (Dr CONTRACTOR_PAYABLE / Cr Kas) → saldo utang upah per mandor negatif dan kas berkurang sebelum kewajibannya ada → neraca/utang upah/arus kas per tanggal di laporan owner dan CP7 finance.
- Skenario (angka nyata, dua kali, dua payroll berbeda): fixture E01 penulis, payroll disetujui dengan akrual 2026-10-12, PAY dengan `payment_date` 2026-10-09 → **diterima** (`COMMITTED_OUTCOME status PAID`); saldo utang upah mandor per hari ekonomi: 10-09 −180.00, 10-12 +180.00 → minimum −180.00 selama 10-09..10-11. `run_v263a_payroll_integrity_checks` 0 isu sebelum dan sesudah; snapshot owner as-of 10-10 `status READY`, `changed_since_filing false`; `period_blockers_v1`/`period_readiness_v1` tidak dapat dipanggil oleh peran owner (42501) sehingga tidak ada jalur aplikasi yang memperlihatkan masalah ini.
- Bukti: **TERBUKTI** — run 38557410928 (job 115829885267) dan 38558699494 (job 115834143256), kasus `OPEN_PAYABLES_BACKDATED_SETTLEMENTS`, sub `R1_05_PAYROLL_PAID_BEFORE_ACCRUAL`.
- Tingkat bukti: NATIVE_QUALIFIED (komposisi CP7 penuh, fasad aplikasi `erp_cp7_save_payroll_v1 PAY`, peran owner).
- Usulan perbaikan: di `erp.post_payroll_payment` (dan pemeriksaan awal CP7 PAY serta cicilan) tolak `payment_date < max(period_end, tanggal persetujuan)` kecuali lewat alur kasbon/uang muka yang terdokumentasi; tambahkan detektor "saldo CONTRACTOR_PAYABLE per mandor per tanggal < 0" ke registri integritas. Uji: PAY bertanggal sebelum akrual harus ditolak (gagal sebelum, lulus sesudah); PAY pada hari akrual diterima (kontrol); detektor naik tepat +1 bila auditor menyuntik satu baris negatif.

### FABLE-002 — Repo memuat dua salinan migrasi AC yang berbeda; pemasangan baru menghasilkan definisi view yang berbeda tergantung jalurnya
- Keparahan: S3 (dokumen/bukti; berisiko untuk pemasangan baru CP7C/VPS).
- Invarian/pola: INV-POL03 (satu aturan, satu sumber), INV-M04/M05.
- Lokasi: `supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql` (sha256 7b5690a2…, terakhir diubah f455f612 "normalize effective view ACLs") vs `supabase/release/cp6-t3/20260915031500_…20ac….sql` (sha256 871fb32b…); badan `erp.v_payroll_nota_browser` berbeda teks dan hash.
- Rantai dampak: jalur aligned-install memakai salinan migrations → `AC_VIEW_PREDECESSOR_MISMATCH` (body=f); jalur paket rilis memakai salinan release → `ALL_STAGES_INSTALLED`. Workflow `cp6-t3-aligned-install` tidak pernah hijau sejak 23 Sep dan hanya ditandai "refuses" di komentar skrip.
- Bukti: TERBUKTI (run 38522071779 job 115713835290; hash dihitung dari pohon beku) — `runs/cp17/AC_VIEW_MISMATCH.md`.
- Tingkat bukti: NATIVE_QUALIFIED (penolakan) + STATIC (hash).
- Usulan: nyatakan satu sumber kanonik untuk pemasangan baru dan tambahkan pemeriksaan kesamaan (atau catatan alasan perbedaan) di paket; tandai workflow aligned-install sebagai "diketahui menolak / T3_PREP". Jangan melonggarkan guard predecessor.

### FABLE-003 — Manifest paket rilis T3 menyatakan rollback `NOT_TESTED` dan label `T3_PREP`, padahal siklus rollback sudah lulus; komentar jumlah berkas basi
- Keparahan: S3.
- Invarian/pola: INV-M04, §16.6 (arsip bukti = manifest).
- Lokasi: `supabase/release/cp6-t3/MANIFEST.json` (`rollbacks: "NOT_TESTED"`, `label: T3_PREP`, `release_evidence: false`); literal di `scripts/cp6_t3_release_package.py:28,337`; komentar "24 files"/"29-file" di `.github/workflows/cp6-t3-release-package.yml:74,84` dan `cp6-release-readiness.yml:79,89` (paket berisi 30 berkas).
- Rantai dampak: operator yang membaca manifest tidak tahu rollback sudah teruji; sebaliknya auditor bisa salah menganggap rollback belum ada.
- Bukti: TERBUKTI (isi manifest dibaca; rollback 152 objek PASS di run 38522026931 job 115713691756).
- Usulan: perbarui manifest/producer agar merujuk bukti rollback (run, hash `ROLLBACKS.json`) atau beri status yang jujur; perbaiki komentar jumlah berkas.

### FABLE-004 — Bukti CP1 dan CP2 tidak ada di riwayat kandidat dan tidak dapat direproduksi atau divalidasi independen
- Keparahan: S3.
- Invarian/pola: §2.9 label asal-bukti, §16.6.
- Lokasi: commit bukti CP1/CP2 `41bda0f7`, `c00500f2`, `11e7025d` bukan leluhur 0b7049d9; `docs/evidence/2026-09-01/*`, `scripts/cp1_fingerprint.sql`, `scripts/cp2_*.py`, `cp2-free-local-restore.yml` tidak ada di pohon beku (`review/R6` §A–B).
- Bukti: TERBUKTI (git ls-tree / ancestry, baca-saja).
- Usulan: bawa artefak CP1/CP2 (atau tautan permanen + hash) ke pohon kandidat, atau owner menyatakan CP1/CP2 diterima atas dasar REUSED_WRITER_EVIDENCE; restore independen CP2 menjadi bagian CP7C/VPS.

### FABLE-005 — Rencana "uji gabungan 75 kasus C6 + 22 ALL pada satu head" tidak punya bukti eksekusi satu-ke-satu
- Keparahan: S3.
- Lokasi: rencana di §31.8/§32.9; yang ada: `docs/cp6-combined-release-writer-handoff-20260928.md:77-79` (90 native + 22 contention + 8 HTTP + 27 browser pada add1704a) — tidak memetakan ID LAU/ACC/ALL; `out/gpt_c6_75_case_crosswalk.json` tidak ada di repo (`review/R6` §D).
- Bukti: TERBUKTI (pencarian istilah di pohon beku tidak menemukan eksekusi).
- Usulan: penulis menerbitkan crosswalk 75+22 → kasus/run, atau owner menyatakan rencana itu digantikan oleh suite yang ada.

### FABLE-006 (DUGAAN) — Upah rework yang sudah diakui sebagai utang tidak pernah bisa dibayar bila kasus BS tidak berakhir RESOLVED
- Keparahan hipotesis: S1. Invarian: INV-U04, INV-P01.
- Lokasi: `post_rework_completion` (BE:3617-3636) selalu mengkredit CONTRACTOR_PAYABLE; kelayakan payroll REWORK mensyaratkan `bs_cases.status='RESOLVED'` (AX:615-682, trigger AX:708-719); kasus yang seluruhnya SCRAP menjadi `SCRAPPED` (M19:312-319). Detail `review/R3` R3-01.
- Bukti: DUGAAN (kode). Tingkat: STATIC. Probe native dan kriteria konfirmasi/bantah ada di `review/R3` R3-01.

### FABLE-007 (DUGAAN) — Absensi bisa masuk dua Nota/payroll yang periodenya tumpang tindih; penjaga tumpang tindih payroll tidak ditemukan di pohon
- Keparahan hipotesis: S1 (S0 bila tidak ada pemicu dasar). Invarian: INV-U02, INV-P01.
- Lokasi: `populate_payroll_draft` (`…20bc…sql:2934-2943`) dan `rebuild_nonwork` CP7 memasukkan semua absensi POSTED dalam periode tanpa `not exists` pada payroll lain; `note_header` CP7 membuat header dengan periode Nota sendiri (`CP7/notes.sql:80-81`); klaim "Native payroll period overlap blocks…" di `P12_NOTA_HANDOFF.md` tidak menemukan pemicu pendukung di pohon. Satu-satunya jaring: detektor `PAYROLL_ATTENDANCE_DUPLICATE`. Detail `review/R1` R1-03.
- Bukti: DUGAAN. Tingkat: STATIC. Probe di `review/R1` R1-03.

### FABLE-008 (DUGAAN) — Penyelesaian klaim laundry bisa bertanggal sebelum vendor punya utang; AP vendor dan beban per tanggal salah
- Keparahan hipotesis: S1. Invarian: INV-T03, INV-K02, INV-P03.
- Lokasi: `erp.resolve_laundry_claim` (`supabase/release/cp6-t3/…20ac….sql:6095-6115`) hanya menolak tanggal masa depan dan membandingkan dengan **total** AP vendor saat ini, lalu `post_journal('LAUNDRY_CLAIM_SETTLEMENT', …, v_effective_date …)`; `save_laundry_claim_v2` (`:8485-8605`) menerima `resolution_date` bebas. Penjaga AP vendor di `post_journal` (`:4013-4054`) juga memakai saldo total, bukan per tanggal.
- Bukti: DUGAAN. Probe native Fable **tidak mencapai** penulis (run 38560570589: fixture E01 tidak punya BS sehingga klaim DAMAGE ditolak oleh penjaga konservasi — perilaku benar). Tingkat: STATIC.

### FABLE-009 (DUGAAN) — Pickup (Bagi Potongan) yang sudah POSTED tidak punya jalur koreksi/pembalikan
- Keparahan hipotesis: S1 (alur penting macet tanpa jalan keluar). Invarian: INV-K01/K04, SKN-27.
- Lokasi: `guard_cutting_pickup_lifecycle` M18:253-277; tidak ada penulis yang mengubah `cutting_pickups` sesudah POST; reopen CP7 menolak grup dengan pickup (REOPEN:74-76). Detail `review/R3` R3-06.
- Bukti: DUGAAN. Tingkat: STATIC.

### FABLE-010 (DUGAAN) — Sisa kain sesudah potong tidak bisa dikembalikan ke stok lewat jalur sah apa pun
- Keparahan hipotesis: S1 / pertanyaan owner. Invarian: INV-S01, INV-H02.
- Lokasi: `post_cutting_material_returns` (AC:3472-3516) butuh `qty_physically_returned`, tetapi tidak ada fungsi/UI yang menulis kolom itu; form hanya mencatat `qty_reported_remaining` (`src/ConnectedCuttingPage.tsx:298-299`). Detail `review/R3` R3-09.
- Bukti: DUGAAN. Tingkat: STATIC.

### FABLE-011 (DUGAAN) — Tidak ada lantai tanggal cutover global untuk writer yang memasukkan barang/nilai (pembelian, FG tanpa sumber, penyesuaian, penjualan)
- Keparahan hipotesis: S2 (penjaga kronologis hanya menangkap bila sejarah menjadi negatif). Invarian: INV-M01, INV-M03.
- Lokasi: `review/R4` R4-02 (`erp.post_material_purchase_v2`, `erp.post_fg_unsourced_receipt_v1` R/20ax:326, `erp.post_material_adjustment_v2`, `erp.post_sale_v2`).
- Bukti: DUGAAN. Tingkat: STATIC.

Catatan: FABLE-006..011 adalah dugaan dari tinjauan sumber dengan rujukan baris; tiap butir punya probe native dan kriteria konfirmasi/bantah di berkas `review/`. Mereka dihitung sebagai DUGAAN, bukan TERBUKTI, dan tidak menjadi dasar vonis GAGAL.

### Dugaan yang dibantah putaran ini
- **R3-02** (helper tanggal akuntansi memakai `current_date` UTC): dibantah untuk `erp.resolve_accounting_transaction_date(date)` dan `erp._cp3_r4_reverse_journal_internal(uuid,text)` — badan terpasang tidak memakai `current_date` (run 38557410928, kasus SESSION_TIMEZONE; sesi CI ber-TimeZone UTC). Sejalan dengan bantahan di `review/R4` §D.
- **Koreksi/pembayaran ke periode tertutup**: tidak ada jurnal baru yang diakui pada tanggal ≤ tutup buku; tanggal ekonomi lama ditandai `changed_since_filing` (run 38560570589) — sesuai INV-T02 dan D01 §3.4. Penjaga terpusat: `erp.post_journal` selalu mengisi `transaction_date := erp.resolve_accounting_transaction_date(economic_date)` (`…20ac….sql:4056-4058`).
## Matriks invarian

PASS 48, FAIL 2, INCOMPLETE 32 (total 82). PASS hanya bila putaran ini (atau putaran XC2 pada commit yang sama 0b7049d9) punya bukti per kasus; selain itu INCOMPLETE.

| Invarian | Status | Bukti singkat |
|---|---|---|
| INV-U01 | PASS | run 38557410928: 21 jurnal seimbang per entri dan per hari ekonomi; P18 `P18_UNBALANCED_JOURNAL` tidak muncul |
| INV-U02 | PASS | P18 replay supplier/vendor/payroll tanpa efek kedua (38521784664); suite koreksi CP7 identik |
| INV-U03 | PASS | koreksi pembayaran supplier: JOURNAL_REVERSAL + jurnal netral/efektif (38560570589); suite note/receipt/supplier-payment correction PASS |
| INV-U04 | PASS | P18 batas B1..B8 GL = subledger; dimensi AR/AP vendor/upah lengkap (38557410928). Per tanggal: lihat INV-P01 |
| INV-U05 | INCOMPLETE | kas negatif tidak diuji putaran ini |
| INV-U06 | INCOMPLETE | tidak ditargetkan; T3 sen per PO = ACCEPTED_BY_DECISION (opsi A) |
| INV-U07 | PASS | P18: kelebihan bayar supplier/vendor ditolak, GL tidak berubah |
| INV-U08 | INCOMPLETE | tidak ditargetkan putaran ini |
| INV-S01 | PASS | roll dan lot FG = jumlah mutasi (38557410928); P18 subledger stok = GL |
| INV-S02 | PASS | saldo berjalan roll/lot tidak pernah negatif (38557410928); AZ/BA T1 after PASS |
| INV-S03 | INCOMPLETE | transfer tidak ada di rantai Fable; suite AM historis tidak dijalankan pada 0b7049d9 |
| INV-S04 | INCOMPLETE | tidak diuji langsung putaran ini |
| INV-S05 | INCOMPLETE | tidak diuji putaran ini |
| INV-S06 | INCOMPLETE | hanya statis (`review/R1` B, `review/R3`) |
| INV-S07 | PASS | E01: FG 60 → jual 20 → retur 5 → 45 pcs, lot konsisten (38557410928, P18) |
| INV-H01 | PASS | P18: nilai bahan/FG = saldo akun (B1..B8) |
| INV-H02 | PASS | P18: bahan → WIP → FG → HPP, WIP akhir 0, worksheet E01 cocok |
| INV-H03 | PASS | AY 8 + AZ 29 T1 after PASS (38522114938, 38522124077) |
| INV-H04 | PASS | P18 E13 harga pemasok terlambat sesudah siklus penuh PASS; AO di T2 identik |
| INV-H05 | INCOMPLETE | propagasi ke semua posisi tidak diuji Fable putaran ini |
| INV-H06 | INCOMPLETE | tidak diuji putaran ini |
| INV-P01 | FAIL | FABLE-001: sisa utang upah per mandor −180 pada 10-09..10-11 (38557410928, 38558699494) |
| INV-P02 | PASS | BA T1 after 61 PASS (kapasitas uang muka per tanggal, D02) |
| INV-P03 | INCOMPLETE | aging tidak diuji; terkait DUGAAN FABLE-008 |
| INV-T01 | PASS | business day WIB tercatat di setiap kasus; helper tanggal tidak memakai current_date (38557410928) |
| INV-T02 | PASS | tutup buku sampai 10-13, posting/koreksi sesudahnya diakui 10-14, `changed_since_filing` true (38560570589) |
| INV-T03 | INCOMPLETE | DUGAAN FABLE-008; tidak tercapai native |
| INV-T04 | INCOMPLETE | tidak diuji putaran ini |
| INV-L01 | PASS | P18: posisi laporan owner berubah persis sesuai GL (B1, final) |
| INV-L02 | PASS | Report v2 publikasi immutable (core Fable XC2 pada 0b7049d9, `REPORT_V2_SEALED_ONCE_IMMUTABLE`) |
| INV-L03 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-L04 | INCOMPLETE | snapshot READY saat utang upah per tanggal negatif (FABLE-001) — bukan komponen "belum pasti", jadi tidak dinilai FAIL |
| INV-L05 | INCOMPLETE | tidak diuji putaran ini |
| INV-L06 | PASS | Tanya AI brief dalam transaksi read-only (core XC2); preview rencana read-only (plan39 P08_PREVIEW_READONLY) |
| INV-L07 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-R01 | PASS | suite analysis152/attention284 identik (INDEPENDENT_NATIVE_RERUN, oracle penulis) |
| INV-R02 | PASS | attention284 identik |
| INV-R03 | PASS | pl-native schedule 71 identik |
| INV-R04 | PASS | pl-native netting 83 identik; astra-timeline-reuse parity 595/595 |
| INV-R05 | PASS | pl-native supply 53 identik |
| INV-R06 | PASS | pl-native model 32 identik; Wilson floor Fable (core XC2) |
| INV-R07 | PASS | p19 AI v2 (XC2 pada 0b7049d9) + AI brief read-only |
| INV-R08 | PASS | plan39 preview read-only + apply lewat command (identik) |
| INV-R09 | PASS | fabric13/fabric-physical21/rule suites identik |
| INV-K01 | PASS | note/receipt/supplier-payment correction suites identik; pembalik Native + pengganti (38560570589) |
| INV-K02 | PASS | koreksi pembayaran supplier: economic_date efektif 10-13, pengakuan 10-14 (38560570589) |
| INV-K03 | PASS | receipt correction 43 kasus identik (lineage per baris) |
| INV-K04 | INCOMPLETE | tulis langsung CP7 ke `payroll_settlements` hanya statis (`review/R1` R1-11) |
| INV-K05 | INCOMPLETE | tidak diuji Fable putaran ini |
| INV-K06 | PASS | NOTE_REPEATED_REVISIONS PASS (38521815079) |
| INV-K07 | INCOMPLETE | `bs_resolutions` dihapus saat pembalikan (statis `review/R3` R3-05), belum diuji native |
| INV-C01 | PASS | P18 replay kunci sama tanpa efek kedua; CP7 suites identik |
| INV-C02 | PASS | P18 `CP7_SUPPLIER_PAYMENT_STALE_REVIEW`; review token di setiap command |
| INV-C03 | PASS | races di semua suite CP7 + T2/T3 races PASS |
| INV-C04 | PASS | NOTE_LATE_FAILURE_ATOMIC dan sejenisnya PASS |
| INV-C05 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-C06 | PASS | runner ketat: session_leaks 0, public tidak berubah, boundary pulih di setiap kasus Fable |
| INV-A01 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-A02 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-A03 | INCOMPLETE | scan rahasia/artefak tidak dijalankan putaran ini |
| INV-A04 | PASS | `advisor_gate: true` di semua SUMMARY CP7 dan run Fable; T3 `security_advisors` true |
| INV-A05 | PASS | smoke Fable: skema CP7 tidak terjangkau peran publik, ops 42501 (38522428512). Paparan skema `erp` di hosted: tidak dapat diverifikasi |
| INV-UI01 | PASS | grup browser semua suite CP7 PASS (angka dari server) |
| INV-UI02 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-UI03 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-UI04 | INCOMPLETE | tidak diuji putaran ini |
| INV-POL01 | PASS | PL5 `PENDING_POLICY_VALUE` (core XC2) |
| INV-POL02 | PASS | `BC_FREE_REQUIRES_POLICY` menolak gratis tanpa kebijakan (T2 AR) |
| INV-POL03 | FAIL | FABLE-002: dua salinan AC berbeda untuk objek yang sama (S3) |
| INV-POL04 | PASS | kasus basi ditandai SUPERSEDED_BY_OWNER_RULE (T2 AR, SALES_MANUAL_13) |
| INV-POL05 | PASS | COUNTEREXAMPLE yang diterima keputusan tetap tercatat (T2 r16, D01, D11) |
| INV-M01 | PASS | BB/BC/BD saldo awal T1 after PASS; imports 31 PASS |
| INV-M02 | PASS | IMPORTS 31 PASS (T2 identik) |
| INV-M03 | INCOMPLETE | cek integritas sesudah cutover tidak dijalankan pada data nyata; DUGAAN FABLE-011 |
| INV-M04 | PASS | paket T3 diuji dari baseline hosted-faithful G-01 `ALIGNED_PER_OBJECT` |
| INV-M05 | PASS | pemasang menolak predecessor berbeda (aligned-install) dan pos-pakai rollback (T3 rollback) |
| INV-N01 | PASS | reminder v2 suite (XC2 pada 0b7049d9) PASS |
| INV-N02 | INCOMPLETE | tidak diuji ulang putaran ini |
| INV-D01 | INCOMPLETE | kontrol positif/negatif detektor tidak dijalankan Fable; FABLE-001 menunjukkan celah detektor |
| INV-D02 | INCOMPLETE | tidak diuji putaran ini |
| INV-D03 | INCOMPLETE | tidak diuji putaran ini |
| INV-D04 | INCOMPLETE | tidak diuji putaran ini |

## Yang belum saya periksa (wajib)
1. **CP1 dan CP2**: artefak tidak ada di pohon beku; auditor tidak boleh query hosted (FABLE-004).
2. **Tinjauan sumber CP4/CP4.5 (RBAC, identitas produksi, WIP)**: subagen R2 terputus batas pemakaian dan tidak diulang; vonis CP4/4.5 hanya berdasar regresi runtime.
3. **Tinjauan jahitan lintas tahap (R5) sebagai catatan terpisah**: subagen terputus; diganti oleh rantai native Fable (run 1–4) dan pemeriksaan penjaga periode terpusat di `post_journal`. Writer fisik (mutasi stok) tidak memeriksa `closed_through` (`review/R4` R4-03) — tidak diuji native.
4. **Daftar alert CodeQL**: `code-scanning/alerts` → 403 untuk auditor; hanya "analisis selesai" yang terbukti.
5. **Rencana uji gabungan 75 C6 + 22 ALL** (FABLE-005).
6. **Workflow historis berpin identitas** (CP3-R4, CP4, CP4.5, CP5, cutting-bridge, CP6 full-schema, review-scope, readiness): menolak di 0b7049d9 dan tidak menguji kode final (`runs/cp17/RED_CLASSIFICATION.md`).
7. **CP7C** (backup offsite, restore drill, `ops/backup-repo/`): di luar lingkup per D13-9a — tidak diperiksa, tidak dinyatakan lulus.
8. **Hosted**: `show timezone`, fingerprint hari ini vs CP1/G-01, paparan skema `erp` lewat PostgREST hosted (relevan `review/R3` R3-07) — TIDAK DAPAT DIVERIFIKASI DARI SESI INI.
9. **Dugaan statis tanpa probe native**: FABLE-006..011 dan R1-01, R1-02, R1-04, R1-06..R1-12, R3-04, R3-05, R3-07, R3-08, R3-10..R3-13, R4-03, R4-04 (probe dan kriteria ada di `review/`).
10. **Koreksi penerimaan ke periode tertutup** (sub-percobaan run 38560570589 tidak tercapai karena payload Fable) dan **klaim laundry mundur** (fixture tanpa BS).
11. **Observasi berlabel penulis**: AW after `DISCOVERY:SEED`, AX after `AX:BACKDATED_OBSERVATION` (tanggal fisik tertutup "dicakup iterasi berikut").
12. **Materi auditor lain (Astra)**: tidak dibuka sama sekali sampai laporan ini dikunci.

## Hasil merah yang bukan temuan (wajib)
Semua 26 job merah regresi: `runs/cp17/RED_CLASSIFICATION.md` (25 gate identitas historis/READINESS_SCOPE/merge-commit assert/`source()` trial/AS_SCOPE/AD admission; 1 = `cp6-t3-aligned-install` → `runs/cp17/AC_VIEW_MISMATCH.md`, GUARD_BY_DESIGN; perbedaan salinannya menjadi FABLE-002). Baris non-PASS lain:

| Run / kasus | Status | Klasifikasi §8 | Alasan |
|---|---|---|---|
| T2 AR `ACCESSORY_CONNECTED_ZERO` | INCOMPLETE | SUPERSEDED_BY_OWNER_RULE (D11, ERP-DEC02) | gratis hanya lewat kebijakan Special; identik beku r16 |
| T2 NEW_CASES ×8 + `ADJUSTMENT_DATE:False`, T2_CALENDAR_POLICY ×12, AO_TRIAL ×4, BUSINESS DPRR ×12 | COUNTEREXAMPLE/INCOMPLETE/DPRR | ACCEPTED_BY_DECISION (D01, r16) | disposisi beku; multiset identik |
| T3 release browser READINESS ×2, SALES_MANUAL_13 ×2 | INCOMPLETE | ACCEPTED_BY_DECISION (F-UI-02; D13-9c) | gate installed/primary_unchanged true |
| AV/T1 `*_BEFORE` (AW..BE) | COUNTEREXAMPLE/NO_ROUTE/N/A | GUARD_BY_DESIGN | before = cacat predecessor; after 0 merah |
| S06 close probe ×4 | COUNTEREXAMPLE | LEGACY_RUNTIME_OBSERVATION_ONLY | AUD-S06 pada AU beku, ditutup AW |
| auditor-scenario self-test ×7, p08-shell shell ×6 | INCOMPLETE | AUDITOR_TOOL (uji-diri negatif) | pelanggaran yang disuntik terdeteksi |
| Fable 38557410928 `CLOSE_THEN_BACKDATED_CORRECTIONS` | FAIL | AUDITOR_TOOL | fixture menutup buku "sampai hari ini"; produk menolak dengan benar |
| Fable 38558699494 `CLOSED_PERIOD_RECOGNITION`; 38559631518 kedua kasus | INCOMPLETE | AUDITOR_TOOL | TypeError tanggal; kolom `created_at` tidak ada; peran dipulihkan dalam transaksi gagal |
| Job Fable merah 38557410928/38558699494/38559631518 | gate `writer_runtime` false | GUARD_BY_DESIGN | gate meminta semua kasus PASS; COUNTEREXAMPLE FABLE-001 adalah temuan, sisanya AUDITOR_TOOL |
| AW `DISCOVERY:SEED`, AX `AX:BACKDATED_OBSERVATION` | OBSERVED | observasi berlabel penulis | bukan PASS; masuk daftar belum diperiksa |

## Label asal-bukti per klaim (wajib)
| Klaim | Label §2.9 | Run / commit |
|---|---|---|
| Regresi CP6 T2/T3/rollback/probe/AV/G-01 pada ref 00b0eb24 (produk 0b7049d9) | INDEPENDENT_NATIVE_RERUN | 38522008302, 38522017994, 38522026931, 38522044340, 38522054629, 38522090695..38522171091, 38522248192 |
| Regresi CP7 14 workflow | INDEPENDENT_NATIVE_RERUN (oracle penulis) | 38521746469 … 38521872645 |
| Smoke Fable | FABLE | 38522428512 |
| Rantai lintas tahap (SKN-22), FABLE-001, INV-T02 | FABLE (oracle_origin Fable; fixture_origin E01/P18 penulis; angka worksheet E01 = owner-approved) | 38557410928, 38558699494, 38559631518, 38560570589 |
| CP7 beku v1.2 | FABLE + WRITER_CROSSCHECK | `audit/fable_cp7/AUDIT_FABLE_XC2_0b7049d9_v1.2.md` |
| Tinjauan sumber R1/R3/R4/R6; FABLE-002..011 | INDEPENDENT_SOURCE_REVIEW (STATIC) | `review/*.md`, `runs/cp17/AC_VIEW_MISMATCH.md` |
| CodeQL "nol alert" | WRITER_CROSSCHECK | 38521863082 (auditor hanya melihat analisis selesai) |
| CP1/CP2 | REUSED_WRITER_EVIDENCE / TIDAK DAPAT DIVERIFIKASI | `review/R6` |
| CP7C | NOT_APPLICABLE (D13-9a) | — |

## Pertanyaan untuk owner, masing-masing dengan rekomendasi auditor (wajib)
1. **Pembayaran upah sebelum akhir periode Nota (FABLE-001)**: apakah boleh? *Rekomendasi: tidak boleh.* Pembayaran sebelum akrual harus lewat kasbon/uang muka yang tercatat; penulis menambah penolakan dan detektor saldo utang upah negatif per tanggal. Bila owner menganggap laporan per tanggal yang salah tanpa tanda itu "bahaya bangkrut", naikkan ke S0.
2. **Salinan AC kanonik (FABLE-002)**: salinan mana yang dipakai untuk pemasangan baru (VPS/CP7C)? *Rekomendasi: salinan paket rilis `supabase/release/cp6-t3/`*, karena itu yang lulus T3 dan rollback; salinan `supabase/migrations/` disamakan atau diberi catatan alasan.
3. **CP1/CP2 (FABLE-004)**: terima atas dasar bukti penulis, atau minta restore independen? *Rekomendasi: terima sebagai REUSED_WRITER_EVIDENCE untuk sekarang, dan jadikan restore independen bagian CP7C/VPS* (basis CP2 sudah jauh tertinggal dari kode final).
4. **Rencana 75 C6 + 22 ALL (FABLE-005)**: masih diwajibkan? *Rekomendasi: penulis cukup menerbitkan crosswalk ID → kasus/run yang sudah ada*; jalankan ulang hanya ID yang tidak terpetakan.
5. **Dugaan statis FABLE-006..011**: *Rekomendasi: penulis menjalankan probe native yang tercantum di `review/` pada salinan sekali pakai sebelum gerbang §12*; yang terkonfirmasi diperbaiki, yang terbantah dicatat. Khusus FABLE-010 (sisa kain): owner memutuskan apakah sisa kain kembali ke gudang atau dibiayakan ke PO.

## Ringkasan untuk owner (bahasa sehari-hari, ≤ 10 kalimat)
Kode final 0b7049d9 sudah saya uji ulang dari CP3 sampai CP7, dan hasil uji lama semuanya sama persis dengan rekaman beku. Saya juga menjalankan satu alur bisnis utuh (beli bahan, potong, jahit, laundry, QC, jual, retur, bayar supplier, bayar laundry, bayar upah, tutup buku) dan jurnal, stok, utang, serta piutangnya cocok. Tutup buku bekerja benar: transaksi bertanggal di periode yang sudah ditutup dicatat di periode terbuka dan laporannya ditandai berubah. Satu masalah nyata: pembayaran upah mandor boleh diberi tanggal sebelum utang upahnya ada, sehingga laporan per tanggal menunjukkan utang upah minus dan tidak ada peringatan. Ada empat catatan dokumen, termasuk dua salinan migrasi AC yang berbeda yang perlu dipilih salah satu sebelum pemasangan baru di VPS. Enam dugaan dari pembacaan kode (upah rework, absensi dobel, klaim laundry mundur, pickup tidak bisa dikoreksi, sisa kain, tanggal cutover) belum terbukti dan perlu diuji penulis. CP1 dan CP2 tidak bisa saya periksa karena buktinya tidak ada di kode ini. Backup CP7C tetap di luar lingkup. Owner perlu memutuskan lima pertanyaan di atas; production tetap belum boleh jalan (`production_go:false`).

## Fokus tambahan yang menurut saya paling berisiko
1. **Tanggal pembayaran vs tanggal kewajiban** di semua jenis utang (upah, laundry, supplier): penjaga Native umumnya hanya menolak "masa depan" dan memakai saldo total, bukan saldo per tanggal (FABLE-001, FABLE-008).
2. **Detektor yang tidak bisa dipanggil owner**: `period_blockers_v1`/`period_readiness_v1` ditolak untuk peran owner (42501); jalur aplikasi hanya melihat ringkasan `READY`.
3. **Jalur koreksi yang tidak ada** (pickup POSTED, sisa kain): bila salah input terjadi di produksi, satu-satunya jalan keluar adalah tulis langsung ke database.
4. **Pemasangan baru di VPS**: pastikan salinan migrasi kanonik (FABLE-002) dan restore drill independen (CP7C) sebelum data nyata dipindah.

## Register run
Lihat `REGISTER_RUNS.md` (B1 regresi CP6, B2 regresi CP7, B3 skenario Fable run 1–4). Log pertama setiap run Fable yang merah disimpan; run 2–4 hanya memperbaiki plumbing/fixture Fable, oracle tidak diubah dan dinyatakan sebelum observasi.

## Pernyataan paparan (§16.7)
Fable hanya membaca pohon beku 0b7049d9 dan cabang penulis `claude/new-session-deapao`; menulis hanya ke cabang `audit/fable-cp1-7-0b7049d9-20261014`; tidak membuka cabang/run/artefak Astra; tidak mengirim pesan ke pihak lain; tidak meminta kredensial; tidak menyentuh hosted/produksi/Cloudflare; `production_go:false`.
